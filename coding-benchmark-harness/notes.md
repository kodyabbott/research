# Coding benchmark harness -- implementation log

Running log kept while implementing [DESIGN.md](DESIGN.md). Newest entries at the bottom of each
section. Times are Mountain Daylight Time (America/Denver).

Design by Claude Fable 5.1; implementation by Claude Opus (Anthropic) via Claude Code, directed by
Kody Abbott.

## Environment

Captured 2026-09-29 23:59 MDT. Host values below are what `harness/record.py::host_snapshot()`
actually reported on this machine, not what I assumed (see the correction entry of 2026-09-30 01:35):

| Item | Value |
| --- | --- |
| host | `Mac17,6`, Apple M5 Max, 128 GB, AC power |
| macOS | 27.0 (build 26A428), `Darwin 27.0.0` |
| python3 | 3.14.7, `/opt/homebrew/opt/python@3.14/bin/python3.14` (`which python3` -> `/opt/homebrew/bin/python3`) |
| python3 realpath | `/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14` |
| `sandbox-exec` | present at `/usr/bin/sandbox-exec` |
| repo | `~/repos/research`, branch/commit recorded per commit below |
| datasets + work dirs | `~/Documents/Codex/model-cache/coding-benchmark/` (outside the repo) |

Standard library only; no pip packages are used or required.

**No model server was contacted during implementation.** Per DESIGN.md "Revisions after review" item 1,
ports 11434 and 11436 were off limits: a separate benchmark had the GPU. Every backend test uses a fake
`urlopen`. Acceptance item 4 (live Ollama run) is not part of this work.

## Log

### 2026-09-29 23:59 MDT -- start

- Read DESIGN.md in full including "Revisions after review", repo `CLAUDE.md`, and
  `.claude/rules/{research-workflow,source-rules}.md`.
- Read the reference implementations: `uncensored-models-m5-benchmark/bench.py` (raw-record style,
  Ollama request handling, `think` mapping, refuse-to-overwrite, unload confirmation via `/api/ps`),
  `local-model-benchmarks/coding_screen.py` (extraction + sandbox-runner call shape, truncation
  handling), `local-model-benchmarks/quality_screen.py` (`_same` comparison helper). Ideas reused,
  nothing imported across folders.
- Created the folder skeleton: `harness/`, `tests/fixtures/`, `runs/`.

### 2026-09-30 00:20 MDT -- sandbox profile discovery

Goal: a `(deny default)` `sandbox-exec` profile that the stock Homebrew python3 3.14.7 can start
under. Discovery was empirical, starting permissive and tightening one rule at a time.

**What did not work, and why**

1. `(trace "...")` in the profile produced no trace file (macOS 27 appears to have dropped or
   restricted profile tracing), so trace-driven generation was not available.
2. `/usr/bin/log show --predicate 'eventMessage CONTAINS "deny"'` showed denials from *other*
   processes (`mds`, `logd_helper`) but never from the sandboxed python. Kernel sandbox denials for
   this process were not logged, so the log-reading loop the design assumed was not usable either.
   The productive signal was the process exit status: `134` (SIGABRT) for a failure during
   interpreter startup, and an actual error string once enough was allowed for python to reach its
   own error reporting.
3. The first breakthrough came from adding `(literal "/")` to `file-read*`, which turned the silent
   SIGABRT into `python3.14: realpath: /opt/homebrew/Cellar/python@3.14/.../bin/: Operation not
   permitted`. The interpreter calls `realpath()` on its own executable at startup, which requires
   **`file-read*` (not merely `file-read-metadata`) on every ancestor directory** of the binary.
   `(allow file-read-metadata (literal "/") (literal "/opt") ...)` and `(path-ancestors ...)` both
   still failed; only full `file-read*` on `/` and `/opt` worked.
4. macOS firmlinks matter. `/opt`, `/Users`, and `/private/tmp` live on the Data volume and the
   kernel also sees them as `/System/Volumes/Data/opt`, `/System/Volumes/Data/Users`, etc. A write
   rule for `/tmp/...` silently failed until the path was `os.path.realpath()`-ed to
   `/private/tmp/...` **and** mirrored under `/System/Volumes/Data`. Every path-based rule in the
   profile is therefore emitted twice: bare and `/System/Volumes/Data`-prefixed.
5. `(allow process-exec (literal <python3.14>))` alone failed with
   `posix_spawn: .../Resources/Python.app/Contents/MacOS/Python: Undefined error: 0`. Homebrew's
   `python3.14` re-execs itself through the framework's `Python.app` binary, so both literals are
   needed. `sandbox.py::_python_app_binary` locates it by walking the parents of the resolved
   interpreter path.

**Empirically minimal read set.** An automated drop-one-at-a-time minimizer over 11 candidate rules
reduced the required `file-read*` set to exactly three entries for this interpreter:
`(subpath "/opt/homebrew")`, `(literal "/")`, `(literal "/opt")`. `/usr/lib` and `/System/Library`
are *not* needed because `libSystem` and `CoreFoundation` come from the kernel-mapped dyld shared
cache rather than from disk.

**Every rule in `harness/sandbox.py::PROFILE_TEMPLATE`, and its justification**

| Rule | Why it is there |
| --- | --- |
| `(version 1)` | Required profile header. |
| `(deny default)` | Deny-default posture: nothing is permitted unless listed below. |
| `(allow sysctl-read)` | Read-only system information. The interpreter starts without it, but `numpy` calls `os.uname()` during import and fails with `EPERM` otherwise. DESIGN.md's sandbox section lists this rule, and granting it means a candidate that imports numpy behaves as it would in EvalPlus's reference environment. It grants no file, network or process access. |
| `(deny network*)` | Hard requirement. Verified by self-test against a live local listener (EPERM, listener accepted nothing). Redundant with `deny default`, kept explicit so the intent survives edits. |
| `(allow process-exec (literal @PYTHON@) (literal @PYTHON_APP@) + Data-volume mirrors)` | The interpreter binary and the `Python.app` binary it re-execs. Narrow literals, not `process-exec*`. `process-fork` is **not** allowed, so the sandboxed process cannot spawn helpers -- verified: `subprocess.run(["/bin/echo"])` raises `PermissionError`. |
| `(allow file-read* (subpath @PYTHON_PREFIX@) + mirror)` | The interpreter, its framework `Python` dylib, and the standard library. `@PYTHON_PREFIX@` is `/opt/homebrew` here, derived from the resolved interpreter path. |
| `(allow file-read* (subpath "/usr/lib") (subpath "/usr/share") (subpath "/System/Library"))` | Not strictly required with the dyld shared cache (see minimizer result above), kept as defensive breadth so the profile also works with `/usr/bin/python3` or a python that loads on-disk system dylibs, ICU data, or zoneinfo. All are outside `$HOME`, so they do not weaken the `$HOME` read denial. |
| `(allow file-read* (subpath "/private/var/db/dyld") + mirror)` | dyld shared-cache metadata; same defensive rationale. |
| `(allow file-read* (literal "/") (literal "/opt") (literal "/System/Volumes") (literal DATA) (literal DATA/opt))` | Ancestor-directory reads required by the interpreter's startup `realpath()` (finding 3). Directory entries only -- `literal`, not `subpath`, so this grants nothing recursive. |
| `(deny file-read* (subpath @HOME@) + mirror)` | The desirable-but-optional requirement from the design revisions: no reads anywhere under `$HOME`. Placed **after** the system allows and **before** the WORKDIR allow, because later rules win. Verified against two files that actually exist (`DESIGN.md` in the repo and a temp file created under `$HOME`), both `PermissionError:EPERM` -- ENOENT would not have proved denial. |
| `(allow file-read* (subpath @WORKDIR@) + mirror)` | The per-task work directory, which is itself under `$HOME` (`~/Documents/Codex/model-cache/coding-benchmark/work/task-*`). This is the only readable location inside `$HOME`. |
| `(allow file-write* (subpath @WORKDIR@) + mirror)` | The only writable location anywhere. Hard requirement, verified: writes to `/private/tmp` and to `$HOME` both return `PermissionError:EPERM` and no file is created. |

Rules that turned out to be **unnecessary and were left out**: `mach-lookup`, `signal`,
`process-fork`, `file-read-metadata`, and any `/dev` access. (`sysctl-read` is also unnecessary for
startup but is granted deliberately -- see the correction entry of 2026-09-30 01:35.) Python 3.14.7 starts and runs
the whole standard library without them. `signal.setitimer(ITIMER_REAL, ...)` and SIGALRM delivery
work with no `signal` rule (kernel-delivered), which is what the per-input timeout relies on --
`setitimer`, not `signal.alarm`, because the per-input limits are fractional seconds.

**Process limits.** `preexec_fn` sets `RLIMIT_CPU` (default 60 s per task per the design
revisions), `RLIMIT_NOFILE` 64, `RLIMIT_FSIZE` 16 MiB. Verified: CPU spin is killed by SIGXCPU
(signal 24) at the limit; an over-large write raises `OSError 27 File too large`; the 65th open file
raises `OSError 24`. Wall timeout is `subprocess.run(timeout=...)`, verified independently.

**Environment.** Scrubbed to `PATH=/usr/bin:/bin`, `HOME=WORKDIR`, `TMPDIR=WORKDIR`,
`WORKDIR=<workdir>`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`. Setting
`HOME` and `TMPDIR` into WORKDIR means `os.path.expanduser()` and `tempfile` never need an allow
rule (design revisions item 3). The interpreter is launched **without** `-I`/`-E`, because those
would discard `PYTHONHASHSEED=0` and with it the determinism of set/dict iteration order.

**Third-party packages in the sandbox.** *Superseded by the correction entry of
2026-09-30 01:35: numpy 2.5.3, Pillow 12.3.0 and certifi are all importable once `sysctl-read` is
granted, because the interpreter's own site-packages sit inside the readable prefix. The claim
originally recorded here -- that nothing third-party was reachable, and that numpy failed because it
lives under `$HOME` -- was wrong on both counts.*

**Known fidelity limit.** Candidate code shares the interpreter with the per-input timer, so it
could in principle reinstall the SIGALRM handler or call `signal.setitimer(..., 0)` and evade the
per-input timeout. EvalPlus has the same exposure with its `time_limit` context manager. The outer
`RLIMIT_CPU` and wall-clock timeout are the backstop and cannot be evaded from inside.

Sandbox self-tests: all five pass (`normal-program-returns-json`, `network-denied`,
`write-outside-workdir-denied`, `read-home-and-repo-denied`, `infinite-loop-killed`). Profile
template SHA-256 is recorded in each run record as `sandboxProfileSha256`.

### 2026-09-30 00:45 MDT -- extraction and grading

**EvalPlus source pinned for the grading rules.** All comparison behaviour is ported from
EvalPlus tag **v0.3.1**, commit **e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2** (the current release;
`main` was at `26d6d00bb1fd0fa37f39c99d5290da67891d1c5e`, 2025-10-02, which does not touch these
files). Files read:

- `evalplus/eval/__init__.py` -- `unsafe_execute()`: the special-oracle block and the `atol` /
  `np.allclose(rtol=1e-07)` fallback.
- `evalplus/eval/_special_oracle.py` -- `MBPP_OUTPUT_NOT_NONE_TASKS`, `MBPP_OUTPUT_SET_EQ_TASKS`,
  `_surface_Area` (Mbpp/581), `_digit_distance_nums` (Mbpp/558), `_poly` (HumanEval/32).
- `evalplus/config.py` -- `DEFAULT_MIN_TIME_LIMIT = 1.0`, `DEFAULT_GT_TIME_LIMIT_FACTOR = 4.0`.
- `evalplus/data/mbpp.py` -- `MBPP_PLUS_VERSION = "v0.2.0"`, `mbpp_deserialize_inputs()`.
- `evalplus/data/humaneval.py` -- `HUMANEVAL_PLUS_VERSION = "v0.1.10"`.
- `evalplus/data/utils.py` -- `get_dataset_metadata()`, which is where the release URL shape comes
  from, and `completeness_check()`, which lists the required task fields.
- `evalplus/gen/util/__init__.py` -- `trusted_exec()`: `deepcopy` of each input, per-input timing,
  and the `output_not_none` transform.
- `evalplus/evaluate.py` -- `get_groundtruth()`: expected outputs come from
  `prompt + canonical_solution` (the `contract` field is *not* included), computed once per task.

**Oracles implemented** (`harness/grader.py::compare_output`), in EvalPlus's own order:
`are_equivalent` (Mbpp/164, any answer accepted), `sum_div` (Mbpp/295, also accepts 0),
`surface_Area` (Mbpp/581, alternate oracle within atol), `digit_distance_nums` (Mbpp/558, alternate
oracle), the 8 `MBPP_OUTPUT_SET_EQ_TASKS` (compared as sets), the 3 `MBPP_OUTPUT_NOT_NONE_TASKS`
(both sides reduced to booleans), and HumanEval `find_zero` (checks `abs(_poly(xs, out)) <= atol`
and ignores the recorded expected value).

**Deliberate divergences from the EvalPlus code, with reasons:**

1. *No loop-carried `atol`.* EvalPlus's `unsafe_execute` does `atol = 1e-6` inside the per-input
   loop when `atol == 0 and is_floats(exp)`, which leaves the tolerance in place for every later
   input of that task even when those expected values are not floats. `same()` recomputes the
   tolerance per input instead. This is stricter and, I believe, the intended behaviour; it can
   only change a verdict for a task with mixed float/non-float expected values.
2. *Values cross a process boundary.* EvalPlus compares live Python objects; this harness compares
   values that were serialized in the sandbox and rebuilt here. Faithful for every JSON-shaped
   type plus tuples, sets, frozensets, complex, bytes and big ints. Objects with no serializable
   form (`re.Match`, generators, custom classes) become an `Opaque` carrying the class name and
   `repr`, which only equals an identical `Opaque`. The only tasks where EvalPlus relies on such
   objects are the three not-None tasks, and those are reduced to booleans inside the sandbox
   before encoding -- exactly as `trusted_exec(output_not_none=True)` and the
   `isinstance(out, bool)` branch of `unsafe_execute` do -- so no fidelity is lost there.
3. *`set(out) == set(exp)` on rebuilt values.* Decoded tuples/scalars are hashable, so the eight
   set-equality tasks behave as in EvalPlus. If a candidate returned unhashable members, EvalPlus
   would raise (counted as a failure) and this harness returns `False` (also a failure).
4. *`np.allclose` is reimplemented* as `abs(a - b) <= atol + 1e-07 * abs(b)`, elementwise over
   same-length sequences, NaN never close, infinities equal only to themselves. This matches
   numpy's documented formula and its `equal_nan=False` default. numpy is not available (standard
   library only, and it is not importable inside the sandbox).
5. *`missing-entry-point` is classified as `runtime-error`*, not `no-code`: code was produced and
   executed, it simply never defined the required function. `no-code` is reserved for extraction
   failures.

**Extraction** (`harness/extract.py`) implements DESIGN.md's five rules literally, including the
consequence that unfenced content containing a *foreign* `def` but not the entry point falls
through to `empty` (rule 3 requires the entry point, rule 4 requires no `def` at all). Additions
beyond the design, all tested: `~~~` fences and indented fence markers are recognised, and an
unterminated final fence is still extracted (truncated answers otherwise become spurious `no-code`
failures). When the completion prefix is applied to a bare body, the body is indented so that
`prompt + body` compiles.

**Run-record size.** HumanEval+ carries up to 1000 plus-inputs per task (median 972 across 164
tasks); MBPP+ up to 147 (median 105 across 378). Storing every input's expected and actual value
would put a single run far past the 2 MB the design budgets for a run record. Per-input detail is
therefore kept compact: a one-character-per-input status string (`.` pass, `x` wrong answer,
`e` exception, `t` timeout, `h` harness error, `-` not run), status counts, and the first failing
input with truncated `repr`s of expected and actual. Full expected outputs stay in the
out-of-repository prepare cache. **Deviation from DESIGN.md's `base: {passed, results}`**, recorded
here as required.

**Results leave the sandbox in files, not on stdout** (`$WORKDIR/results.jsonl`, one JSON object per
input, flushed after each; summary in `$WORKDIR/meta.json`). A candidate's stray `print()` would
otherwise corrupt a stdout payload -- EvalPlus wraps execution in `swallow_io` for the same reason
-- and a hard kill (SIGXCPU) still leaves the completed rows on disk, which is how partial progress
is reported. `sys.stdout`/`sys.stderr` are additionally redirected to a discarding sink around
`exec` and every call. **Deviation from DESIGN.md's "writes JSON to stdout".**

### 2026-09-30 01:20 MDT -- datasets, suites, prepare

**Dataset provenance.** The EvalPlus *code* repository's GitHub releases contain only pre-generated
LLM samples, not the datasets. The datasets live in two separate release repositories, and the URL
shape is built by `evalplus/data/utils.py::get_dataset_metadata`:
`https://github.com/evalplus/<name lowercased>_release/releases/download/<version>/<Name>.jsonl.gz`.
Versions are pinned in the EvalPlus source, not chosen by me:
`HUMANEVAL_PLUS_VERSION = "v0.1.10"` (`evalplus/data/humaneval.py`) and
`MBPP_PLUS_VERSION = "v0.2.0"` (`evalplus/data/mbpp.py`). Resolved URLs:

- <https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz>
- <https://github.com/evalplus/mbppplus_release/releases/download/v0.2.0/MbppPlus.jsonl.gz>

Neither release publishes a checksum, and EvalPlus itself only hashes the file after download
(`get_human_eval_plus_hash` md5s the decompressed jsonl at runtime). `datasets.json` therefore
records the SHA-256 of the first download as the pin, plus the decompressed jsonl's SHA-256 and md5
(the latter in EvalPlus's own scheme), and says so explicitly in a `checksumProvenance` field.
Independent cross-checks that the files are the right ones: the gzip sizes match the sizes the
GitHub releases API reports (925932 and 336032 bytes), and the record counts match the EvalPlus
README, which states for the 2024-04-17 pre-`v0.3.0` entry: "MBPP+ is upgraded to `v0.2.0` by
removing some broken tasks (399 -> 378 tasks)". Observed: 164 HumanEval+ tasks, 378 MBPP+ tasks.

**Field adaptations.** HumanEval+ records have exactly the fields the design assumed. MBPP+ has no
`text` field. Its `prompt` is `"""<statement>\nassert <one call>\n"""` -- verified uniform
across all 378 records (every prompt is a triple-quoted block containing exactly one `assert`, and
it is always the last line). The MBPP+ template therefore uses the statement as `{text}` and the
prompt's own assertion as the example test. That assertion is the *curated* one: for the eight
set-equality tasks it is written as `assert set(f(...)) == set(...)`, whereas the first line of the
separate `assertion` field is the raw `== (4, 5)` form, which would tell the model to return an
ordered tuple for a task graded as a set. Design's open question ("all three assertions or only the
first?") is answered with: the single curated assertion the dataset itself puts in the prompt.

**prepare.py results -- HumanEval+ (v0.1.10):**

| | |
| --- | --- |
| tasks in dataset | 164 |
| expected outputs computed | 164 |
| **tasks skipped** | **0** |
| base inputs | 1570 (mean 9.6 per task) |
| plus inputs | 122683 (mean 748.1 per task) |
| suite digest | `6413ed5c20cf5adbe678c75fff3bcd0a1a839692aaab9d6efced63a4fa376cb5` |
| wall time | 38.2s |

**prepare.py results -- MBPP+ (v0.2.0):**

| | |
| --- | --- |
| tasks in dataset | 378 |
| expected outputs computed | 378 |
| **tasks skipped** | **0** |
| base inputs | 1174 (mean 3.1 per task) |
| plus inputs | 39841 (mean 105.4 per task) |
| suite digest | `e3679496ade19f79acc0e170d100bda97d9686da312057576e9bc69bfd083f24` |
| wall time | 269.5s |

Input counts match `datasets.json` exactly in both cases. Slowest canonical solutions (total across
all of a task's inputs, which is what sets that task's per-input candidate limits): HumanEval+
`HumanEval/130` 6.006s, `HumanEval/139` 3.185s, `HumanEval/83` 1.712s, `HumanEval/15` 1.082s, `HumanEval/36` 0.652s; MBPP+ `Mbpp/255` 199.325s, `Mbpp/599` 6.41s, `Mbpp/271` 1.657s, `Mbpp/630` 1.653s, `Mbpp/603` 1.652s. `Mbpp/255` alone accounts for roughly 200 of MBPP+'s 270 seconds.

**Three bugs and one Python-version difference found by the first prepare run.** The first attempt
skipped 7 HumanEval+ tasks. All seven were my problem, not the dataset's:

1. *Result files were being read through the 1 MiB stdout cap.* `HumanEval/14` (`all_prefixes`) and
   `HumanEval/96` (`count_up_to`) write more than 1 MiB of results across their ~900 and ~180 plus
   inputs, so the harness parsed a truncated `results.jsonl` and reported "completed 330/903
   inputs". Fixed: `want` files get their own 192 MiB read cap; stdout/stderr keep the 1 MiB cap.
2. *`RLIMIT_FSIZE` of 16 MiB was too small for ground truth.* `HumanEval/15` (`string_sequence`,
   called with n up to 1000011 -- a ~7 MB string), `HumanEval/100` (`make_a_pile(1000000)`) and
   `HumanEval/130` (`tri(1000004)`) crashed the runner mid-write. Raised to 128 MiB.
   **Deviation from DESIGN.md's 16 MiB**, recorded here; it is still a hard cap and still applies
   only inside the per-task work directory, which is deleted immediately afterwards.
3. *Python 3.11+ limits int-to-str conversion to 4300 digits.* `HumanEval/83`
   (`starts_one_ends(1000002)`) and `HumanEval/139` (`special_factorial(505)`) legitimately build
   far larger integers, and their canonical solutions stringify them. EvalPlus's reference
   environment predates the cap. The runner now calls `sys.set_int_max_str_digits(0)`.
   **Deviation from stock interpreter behaviour**, deliberate, so these two tasks are scoreable.
4. *Extreme values are compared by digest.* Even with the larger caps, shipping
   `make_a_pile(1000000)`-sized values out of the sandbox for ~100 inputs would mean
   hundreds of megabytes per task. Values whose canonical JSON exceeds 64 KiB are therefore
   reported as `{"t": "digest", "v": sha256, "bytes": n}`, and the grader compares those inputs by
   hash: exact equality only, no tolerance and no special oracle. The digest is byte-identical
   whether it was streamed (never materialized) or taken over the materialized form, because
   `json.dumps(..., separators=(",", ":"))` is compositional over the tagged encoding.
   **In practice this path is almost never taken: 74 of 124,253 HumanEval+ expected values (0.06%)
   and 94 of 41,015 MBPP+ values (0.23%).** None of the affected tasks has a special oracle, and
   all have `atol == 0`, so nothing is lost. **Deviation from DESIGN.md**, recorded here.

After those four changes, **both suites prepare with 0 skipped tasks**. The expected-output cache is
18.9 MB for HumanEval+ and 8.8 MB for MBPP+, stored under
`~/Documents/Codex/model-cache/coding-benchmark/expected/<suite>/` -- outside the repository, as
required.

**Fixture suite.** `tests/fixtures/FixtureSuite-v1.jsonl.gz` holds three synthetic tasks in the
HumanEval+ record shape (`add_two`, `min_max` returning a tuple, `mean_of` returning a float).
Regenerated deterministically by `tests/fixtures/make_fixture.py` (gzip `mtime=0`), sha256 pinned in
`datasets.json`. It is registered as a suite with `localPath` instead of `url`, so `prepare.py
--suite fixture` and `run.py --suite fixture` work through exactly the same code paths as the real
suites.

### 2026-09-30 00:40 MDT -- backends, record, run, summarizer, end-to-end

**Backends.** All three are implemented; only `replay` was ever exercised against real traffic.
`OllamaBackend` posts one non-streaming `/api/chat` per task with `options.num_ctx` set explicitly
(design revisions item 4), `keep_alive: "10m"`, and `think` sent unless the mode is `default` --
`{'false': False, 'true': True}.get(mode, mode)`, copied from `bench.py`, because at least one
import (Gemma) rejects the field with HTTP 400. `preflight()` refuses to start when `/api/ps`
already shows a loaded model, and `verify_context()` aborts when the loaded `context_length` differs
from the requested one. `unload()` posts `keep_alive: 0` and polls `/api/ps` for up to 60 s.
`OpenAIBackend` posts `/v1/chat/completions` with `temperature 0, seed 42, top_p 1, max_tokens`,
records `usage`, leaves server timings `null`, and reports `verified: false` with a caveat for the
context check because the API exposes no context length.

Every HTTP call in the package goes through the single module-level function
`harness.backends._urlopen`, which the tests replace with a `FakeServer` that records each request.
**No request was made to 11434 or 11436 at any point during implementation** (hard rule 1). The 38
backend tests assert on the exact bytes that would go over the wire: the full Ollama options dict,
`num_ctx` at three context sizes, each `think` mode, the absence of a system message, the
`keep_alive: 0` unload body, the context-mismatch abort, and the bearer header for the OpenAI path.

**End-to-end replay run.** `runs/20260929-replay-fixture.json`: 3 tasks, 2/3 pass@1, status
`completed`, `protocolValid: true`, sandbox self-test recorded and passing, 11 KB. The three canned
responses were chosen to exercise three different extraction rules and the one comparison a naive
grader gets wrong: `Fixture/0` passes from a fenced block (`fence-entry`), `Fixture/1` returns
`[min, max]` where a tuple is required and is correctly graded `wrong-answer`
(`expected (1, 3) got [1, 3]`), `Fixture/2` passes through `raw-body` with `completionPrefixed:
true`. Summarized into `RESULTS.md` and `comparison.json` with no warnings.

Test suite: **188 tests, 1 skipped** (the non-macOS refusal path, which cannot be exercised on
macOS), `OK`.

## Deviations from DESIGN.md

Collected in one place. Each is explained in the log entry above it.

1. **Results leave the sandbox in files, not on stdout.** `$WORKDIR/results.jsonl` (one JSON object
   per input, flushed after each) plus `$WORKDIR/meta.json`. A candidate's stray `print()` would
   corrupt a stdout payload, and a hard kill still leaves the completed rows on disk, which is how
   partial progress gets reported. `sys.stdout`/`sys.stderr` are also redirected to a discarding
   sink around `exec` and every call.
2. **Per-input results in the run record are compact,** not a list of values: a one-character status
   per input, status counts, and the first failing input with truncated `repr`s of expected and
   actual. Dumping ~123,000 plus-input values per HumanEval+ run would blow far past the 2 MB the
   design budgets for a record. Full expected values live in the out-of-repo prepare cache.
3. **`RLIMIT_FSIZE` is 128 MiB, not 16 MiB.** Three HumanEval+ canonical solutions legitimately
   write more than 16 MiB of results across their plus inputs. Still a hard cap, still only inside
   the per-task work directory, which is deleted immediately afterwards.
4. **Per-task CPU and wall ceilings are scaled from the canonical solution's measured cost**
   (`max(--cpu-seconds, 4 x canonical sandbox wall seconds)`), because for three tasks this
   harness's serialization of very large values costs far more than the solutions themselves and a
   fixed 60 s ceiling would mis-score a correct answer as a timeout. The floor is the design's
   value and the effective budget is recorded per task. Same `4x` philosophy EvalPlus applies to
   per-input limits.
5. **One-sided digests are a mismatch by construction**, not a cross-representation hash
   comparison: equal values have identical canonical forms, hence identical sizes, hence the same
   side of the size threshold.
6. **`(allow sysctl-read)` is granted**, which DESIGN.md's sandbox section lists but which the
   interpreter does not need to start. It is what makes numpy importable, matching EvalPlus's
   reference environment more closely.
7. **`RLIMIT_CPU` defaults to 60 s** per grading invocation (this is design revisions item 2b, not a
   deviation) and `prepare.py` uses a far larger budget (600 s wall, 300 s CPU) because computing
   ground truth is a one-time trusted operation; `Mbpp/255` alone needs about 200 s.
8. **Oversized values are compared by SHA-256 of their canonical form.** Threshold 64 KiB per value;
   exact equality only, no tolerance and no special oracle on that path. Used for 0.1% of values.
9. **`sys.set_int_max_str_digits(0)` inside the sandbox**, so two HumanEval+ tasks that build
   >4300-digit integers remain scoreable on Python 3.11+.
10. **`atol` is not loop-carried.** EvalPlus mutates its local `atol` inside the per-input loop; this
   harness recomputes per input. Stricter; can only differ for a task with mixed float/non-float
   expected values.
11. **`missing-entry-point` is classified `runtime-error`, not `no-code`.** Code was produced and
   executed; it just never defined the required function. `no-code` is reserved for extraction
   failures.
12. **Values are compared after a serialize/rebuild round trip,** not as live objects. Faithful for
   every type the suites actually use; objects with no serializable form become an `Opaque` keyed on
   class name and `repr`. The only tasks where EvalPlus depends on such objects are the three
   not-None tasks, and those are reduced to booleans inside the sandbox first, so nothing is lost.
13. **MBPP+ has no `text` field.** The statement and the example assertion are both split out of the
    dataset's `prompt` docstring, and the assertion used is the *curated* one the dataset puts there
    (set-form for the set-equality tasks) rather than the first line of the separate `assertion`
    field. This also settles the design's open question: one assertion, the curated one.
14. **Extraction adds three tolerances the design did not list:** `~~~` fences, indented fence
    markers, and an unterminated final fence (truncated answers would otherwise be misreported as
    `no-code`). The design's literal rule ordering is otherwise preserved, including the
    consequence that unfenced content with a *foreign* `def` falls through to `empty`.
15. **`prepare.py` also accepts a local `fixture` suite** registered with `localPath` instead of
    `url`, so the tests and the end-to-end replay run go through exactly the same loader, sandbox
    and grading code as the real suites.
16. **Sandbox self-test rigour.** The design's network check
    (`socket.create_connection(("127.0.0.1", 11436), 1)` raises) would pass whether or not the
    sandbox works, since nothing need be listening -- and if the deny rule were broken it would
    complete a TCP connect to the live model server. Replaced with: the harness opens its own
    ephemeral listener, and the check requires `EPERM` **and** that the listener accepted nothing.
    The read/write checks likewise target files that exist, so `ENOENT` cannot be mistaken for
    denial.
17. **Per-input timeouts use `signal.setitimer(ITIMER_REAL, ...)`, not `signal.alarm`,** because the
    limits are fractional seconds (`max(1.0, 4 x t)`).

**Not implemented, as scoped out by DESIGN.md:** Docker sandbox (interface stub only), JavaScript and
repository-editing suites, pass@k, cloud reference models, Windows support.

**Not done, and out of scope for this work:** acceptance item 4, the live Ollama run. Ports 11434 and
11436 were off limits throughout (design revisions item 1). The exact command for the first live run
is in the handoff and in README.md.

### 2026-09-30 01:35 MDT -- corrections found in review

Five issues, all found by review rather than by a failing test. Four change recorded numbers, so
everything was recomputed; the earlier tables are left in place and superseded by the table at the
end of this entry.

**Correction: the Environment table named the wrong machine.** It said "2023 MacBook Pro 16" (M2
Max, 64 GB)". That was copied from my assumption about the workspace, not measured. `host_snapshot()`
reports `Mac17,6`, `Apple M5 Max`, `memory_gb: 128`. Corrected in place above, with a pointer here.
I should have read the snapshot my own code produces before writing the table -- the repository's
source rules require a source for every factual claim, and "the user's machine list" is not a source
for what this machine is.

1. **Per-input reference times included serialization cost.** `row["seconds"]` was computed after
   `encode_or_digest(value)` ran, so for large values the recorded time was mostly my encoder rather
   than the canonical solution. That made the cached `times` not what the record claims they are and
   inflated the derived candidate limits (`max(1.0 s, 4 x t)`). The clock is now read immediately
   after `function(*args)` returns and nowhere else, matching `trusted_exec`, which times only the
   call. `Mbpp/255`'s "199 s" in the previous entry was an artifact of this bug.

2. **The encoder's cost counted against the candidate's CPU limit.** A correct candidate returning
   a million-element list would have been killed by `RLIMIT_CPU` while my encoder materialized a
   million-node tagged structure -- where EvalPlus does one `==`. `encode_or_digest` now switches to
   the streaming digest above `STREAM_NODES = 8192` nodes instead of 2,000,000. The threshold is
   safe by construction: the smallest tagged node (`{"t":"none"}`) is 12 bytes, so anything past
   `MAX_VALUE_BYTES // 12` (5462) nodes is certain to be digested on either path, and the two paths
   were already proven to emit identical bytes. `MAX_NODES` stays as `encode`'s overflow guard.

3. **Digests were order-sensitive for sets and dicts.** Decoded sets compare by membership, but a
   *digested* set hashed its iteration order, and two equal sets can iterate differently depending
   on insertion history even with `PYTHONHASHSEED=0`. Fixed at the source: `encode` now sorts set
   members, and dict pairs, by their own canonical form. Since sorting cannot be done without
   materializing, `canonical_chunks` no longer streams sets or dicts and delegates them to `encode`,
   which keeps the two paths byte-identical by construction. Dict and set equality ignore order in
   Python, so sorting changes no verdict. Tested directly: equal sets built in opposite orders now
   produce one digest, and streaming and materializing agree byte for byte across six shapes
   including nested sets and dicts.

4. **numpy is importable inside the sandbox after all, and now is.** The earlier note claimed no
   third-party package was reachable. That was wrong: `/opt/homebrew/lib/python3.14/site-packages`
   is inside `@PYTHON_PREFIX@` and is on `sys.path`, and `PIL` 12.3.0 and `certifi` import fine
   there. numpy alone failed, and not because of the path -- it calls `os.uname()` during import,
   which needs `sysctl-read`. Adding `(allow sysctl-read)` -- which DESIGN.md's sandbox section
   explicitly lists -- makes `numpy 2.5.3` import and `numpy.allclose` work. I had dropped the rule
   because the interpreter starts without it. Keeping it is the better call: EvalPlus's reference
   environment has numpy, so a candidate that imports it now behaves as it would there. `mach-lookup`
   is still not needed and is still not granted. Reachable inside the sandbox:
   numpy 2.5.3, Pillow 12.3.0, certifi, pybind11, pip, wheel. Not installed anywhere: scipy, sympy,
   pandas.

5. Adding the profile rule changes `sandboxProfileSha256`, and fixing the timing changes
   `sandboxRunnerSha256`; both are embedded in every expected-output file, so all three suite
   digests change. Full recompute below.

**Recompute after the corrections.** All expected outputs regenerated from scratch
(`prepare.py --recompute`), the replay run redone, the summarizer rerun, and the full test suite
green at **203 tests, 1 skipped**. New hashes: sandbox profile `130725dd62edac6f75294223a380fc8eb63c43c4611968bffa85b43135a3bdcc`,
sandbox runner `6f72bfb5636d7d9c027462e26a1a073ca97c9c4ca348912c294367362d48da22`.

| suite | tasks | skipped | base inputs | plus inputs | suite digest | prepare wall |
| --- | --- | --- | --- | --- | --- | --- |
| humaneval-plus (v0.1.10) | 164/164 | **0** | 1570 | 122683 | `ba4c53edbcd325af92eae08c010cbc88ee321969fc98bb9ce3e9472ac6acd6ef` | 41.6s |
| mbpp-plus (v0.2.0) | 378/378 | **0** | 1174 | 39841 | `463f84ce53806efd921297f7966635fe86cfb75fd651c33f3aff4f60a68c3fc9` | 252.3s |
| fixture (fixture-v1) | 3/3 | **0** | 6 | 10 | `0eb532889f5aaaa9d2ab183700146f366610fe23050159d8dc07d734d028f8aa` | 0.3s |

Input counts are unchanged and still match `datasets.json` exactly. Still 0 skipped in every suite.

**Corrected canonical timings.** These are now the function calls alone, and they are much smaller
than what the buggy version reported. Slowest tasks by summed per-input canonical time: HumanEval+
`HumanEval/139` 2.633s, `HumanEval/83` 0.82s, `HumanEval/15` 0.732s, `HumanEval/36` 0.643s; MBPP+ `Mbpp/599` 6.031s, `Mbpp/603` 1.546s, `Mbpp/271` 1.476s, `Mbpp/392` 1.143s. `Mbpp/255`, previously reported as the worst at 199 s, actually spends
**0.669 s** in `combinations_colors` across its 109 plus inputs and no longer appears in the top ten.
`HumanEval/130` went from 6.006 s to 0.486 s. Total function time across all 545 prepared tasks is
**22.5 s**; total sandbox wall time is **281.9 s**, so 92% of prepare's cost is this harness's
serialization, not the solutions.

**A real remaining cost, measured and handled.** `Mbpp/255` returns one value whose canonical form is
**3.0 GB** (3.66 GB across 18 digested values in that task); streaming a SHA-256 over it takes ~193 s.
`HumanEval/130` is 314 MB / 13.8 s and `Mbpp/630` 73 MB / 4.3 s. EvalPlus compares such values with a
single C-speed `==`; this harness serializes them, which is roughly two orders of magnitude slower.
Left as-is, a **correct** candidate for `Mbpp/255` would have been killed by the default 60 s
`RLIMIT_CPU` and mis-scored as `timeout` -- a failure caused by the grader, not the model. Fixed by
scaling the per-task ceiling from the measured canonical cost, the same way EvalPlus scales per-input
limits: `cpu_seconds = max(--cpu-seconds, 4 x canonical sandbox wall seconds)` and
`wall = max(--grade-wall-seconds, 4 x canonical + 30 s)`. For `Mbpp/255` that is 773 s CPU / 802 s
wall; for the overwhelming majority of tasks the floor applies unchanged. The effective budget and
the canonical reference time are recorded per task under `base.sandbox` / `plus.sandbox`, so the
numbers are auditable rather than magic.

**Simplified digest comparison.** When exactly one side of an input is digested, the values cannot be
equal: the encoding is deterministic and (after the set/dict sorting fix) order-insensitive, so equal
values have identical canonical forms and therefore identical sizes, and would both fall on the same
side of the 64 KiB threshold. That case is now a mismatch by construction rather than a hash
comparison across representations.

## Java 8 extension (DESIGN-JAVA.md)

Design by Claude Fable 5.1; implementation by Claude Opus (Anthropic) via Claude Code, directed by
Kody Abbott. Same hard rule as the Python work: **the implementing agent never contacted a model
server.** A live Python smoke run was in progress on 127.0.0.1:11436 during this work; no HTTP
request was made to it and no `ollama` command was run.

### 2026-09-30 01:50 MDT -- live-run bug: big integers killed the harness process

**Reported from the first full live HumanEval+ run**, which ended with status `error` at
HumanEval/83: `ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has
9876 digits`.

I fixed the *sandbox* side of this cap during the Python work (`sys.set_int_max_str_digits(0)` in
`sandbox_runner.py`, so HumanEval/83 and /139 could produce their large integers) and wrote in
notes.md that the issue was handled. It was only half handled. **The cap applies in both
directions**, and the harness process converts too:

- `values.decode` does `int(tagged["v"])` -- string to integer, also capped;
- `values.brief` does `repr(decode(...))` -- integer to string.

So the value crossed the sandbox boundary fine and then blew up while being decoded for comparison.
Worse, it raised out of `grade_set` into `run.py`'s catch-all, which marked the **whole run**
`error` instead of scoring that one task.

Fix: `sys.set_int_max_str_digits(0)` in `harness/__init__.py`, so every entry point that imports
the package gets it -- `run.py`, `prepare.py`, `summarize.py` and the tests -- rather than
repeating it per script. Verified in a fresh subprocess that `import run` leaves the limit at 0.

Regression tests added (`tests/test_grader.py::BigIntegerCase`): decoding a 10,000-digit integer,
comparing two of them, rendering one through `values.brief`, and grading both a matching and a
mismatching big-integer result through `grade_set` without raising. Plus an assertion that
importing `harness` lifts the interpreter limit, so a future edit that drops the line fails a test
rather than a live run.

**`--resume` after `status: "error"`** was also checked, since that is the state the live run left
behind. It already worked -- `record.RunRecord._load_for_resume` gates on schema version and
protocol/model/sandbox identity, never on status, and resets status to `running` while keeping the
completed tasks. It was untested, so it is now locked in by
`tests/test_record.py::test_resume_accepts_a_record_whose_status_is_error` (and the `incomplete`
case), which builds an errored record, resumes it, and checks the earlier tasks survive and the
run can finish `completed`.

Lesson for my own notes: "fixed the int-digit cap" was too coarse a claim. The cap had two sides
and I verified only the one I had just edited.

### 2026-09-30 01:10 MDT -- toolchain and Java sandbox

**Not breaking the in-flight Python run.** `grader.run_in_sandbox` re-reads
`harness/sandbox_runner.py` from disk on *every task*, so editing that file mid-run would change
the behaviour of a running benchmark. It was left untouched; Java needs no in-sandbox Python runner
because `javac`/`java` are invoked directly. Every other module is imported once at process start,
so additive edits are safe. Java also got its **own** profile template rather than an extension of
the Python one, which keeps `PROFILE_TEMPLATE_SHA256` at
`130725dd62edac6f75294223a380fc8eb63c43c4611968bffa85b43135a3bdcc` -- the value embedded in all 545
prepared Python expected-output files. A test asserts that hash so a future edit cannot move it
silently.

**Toolchain: Azul Zulu 8.96.0.205 (`jdk8.0.504`), macOS aarch64.**

| | |
| --- | --- |
| file | `zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz` |
| url | <https://cdn.azul.com/zulu/bin/zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz> |
| sha256 | `58bb3c08f2aa63d9743cf31899fa4b8c6c9effefce9479e7288c26621c3bb21b` |
| hash source | <https://api.azul.com/metadata/v1/zulu/packages/16811ca3-e48b-459d-abc4-f6b273023a54> |
| `java -version` | `openjdk version "1.8.0_504"` / Zulu 8.96.0.205-CA-macos-aarch64 |
| mode | `jdk8` |

The published SHA-256 was read from Azul's **per-package detail** endpoint and compared against the
value pinned in `java_toolchain.ZULU8` *before* downloading; `prepare.py --jdk` aborts if Azul ever
publishes a different hash for this package rather than silently drifting. Trust-on-first-download
exists only behind `--allow-unpinned-jdk` and was not used. The design's `release8-on-21` Temurin
fallback was not needed and is **not implemented**; `mode` is always `"jdk8"`.

*One adaptation:* Azul's metadata advertises `size: 103714000` but the file is 103,714,410 bytes.
The published SHA-256 matched exactly, so the hash is treated as the authority and the size
difference is recorded (`advertisedSizeMismatch`) rather than fatal. A size check that overrides a
matching cryptographic hash would be worse than useless.

**Java sandbox profile -- what the discovery loop found.** Two failures that a hand-written profile
would not have anticipated:

1. **The `$HOME` deny killed the JDK.** `JAVA_HOME` lives under
   `~/Documents/Codex/model-cache/coding-benchmark/jdk/`, i.e. inside the very tree the profile
   denies. Because later rules win, the `(deny file-read* (subpath "@HOME@"))` line silently
   revoked the JDK allow that came before it, and the launcher reported
   `Error: Could not find Java SE Runtime Environment.` The JDK and WORKDIR allows now come
   **after** the deny.
2. **`realpath()` on ancestors, again.** Even with the JDK re-allowed, `java` could not load a
   class that demonstrably existed (`Could not find or load main class Main`). Both the launcher
   and classpath resolution `realpath()` their arguments, which stats every ancestor directory --
   and all of those are under `$HOME`. Fixed with `(allow file-read-metadata ...)` on the ancestor
   directories of `JAVA_HOME` **and** `WORKDIR`. **Metadata only:** unlike the Python case, full
   `file-read*` was not required here, so no directory under `$HOME` becomes listable and no file
   contents become readable. The literals are generated per invocation by
   `SandboxExec.ancestor_literals()`, so the profile *template* hash stays stable.

Every rule in `sandbox.py::JAVA_PROFILE_TEMPLATE`:

| Rule | Why |
| --- | --- |
| `(deny default)` | Deny-default posture. |
| `(deny network*)` | Hard requirement; verified against a live local listener. |
| `(allow sysctl-read)` | The JVM calls `os.uname()`-equivalent sysctls during startup, as numpy does on the Python side. |
| `(allow process-fork)` | The `java`/`javac` launchers fork. Note this is **more** permissive than the Python profile, which denies fork -- but `process-exec` is restricted to the JDK subtree, so nothing else can be launched. Verified: `Runtime.exec("/bin/echo")` is blocked. |
| `(allow process-exec (subpath "@JAVA_HOME@"))` | `bin/javac`, `bin/java` and the JDK's own helper binaries. Subpath rather than literals because `javac` execs `java` internally. |
| `(allow file-read* ...)` for `/usr/lib`, `/usr/share`, `/System/Library`, `/private/var/db/dyld` | The launchers link `Cocoa`, `Security` and `ApplicationServices` (confirmed with `otool -L`), plus the dyld cache. `/System/Library` reads were expected per the design's handoff note. |
| `(allow file-read* (literal "/dev/urandom") (literal "/dev/random"))` | `SecureRandom` seeding, reached by `UUID.randomUUID()` and some `HashMap` seeding. |
| `(allow file-read* (literal "/dev/null"))` + `(allow file-write-data (literal "/dev/null"))` | The JVM opens `/dev/null`. Write-**data** only, not `file-write*`. |
| `(allow file-read* (literal "/") (literal "/opt") (literal "/Library") (literal "/System/Volumes") ...)` | Ancestor directory reads for the same `realpath()` reason as the Python profile; `literal`, so nothing recursive. |
| `(deny file-read* (subpath "@HOME@") + Data mirror)` | No reads under `$HOME`, including this repository. |
| `(allow file-read-metadata @ANCESTORS@)` | Finding 2. Metadata only. |
| `(allow file-read* (subpath "@JAVA_HOME@"))` | The JDK, re-allowed after the `$HOME` deny (finding 1). |
| `(allow file-read*/file-write* (subpath "@WORKDIR@"))` | The per-task work directory; the only writable location. |

Rules deliberately **not** granted: `mach-lookup`, `signal`, and any `/Library/Java` read (the
`java_home` lookup path -- the pinned JDK is addressed by absolute path, so it is never consulted).
`-XX:-UsePerfData` is required, not cosmetic: JDK 8 writes `/tmp/hsperfdata_<user>/<pid>`
regardless of `-Djava.io.tmpdir`, which would fail against the write-denied `/private/tmp`.

Java profile template SHA-256: `2cce26979b251f2af7d7a87ea0185b1cfcb783456a642c2408ae44fcc7098d49`.

**The five Java self-tests all pass** (7.4 s total):

| Check | Result |
| --- | --- |
| `java-hello-world-compiles-and-runs` | pass -- compiles and prints a sorted list |
| `java-network-denied` | pass -- `BLOCKED java.net.ConnectException`, and a **real listener on an ephemeral port accepted nothing** |
| `java-write-outside-workdir-denied` | pass -- `BLOCKED java.io.FileNotFoundException`, no file created under `$HOME` |
| `java-infinite-loop-killed` | pass -- `cpu-timeout` after 4.0 s |
| `java9plus-rejected-on-jdk8` | pass -- `List.of` fails with `cannot find symbol` / `symbol: method of(String,String)` / `location: interface List` |

The network check uses the ephemeral-listener pattern from the Python work rather than the design's
`connect to 127.0.0.1:11436`: connecting to a dead port raises regardless of the sandbox (a vacuous
test), and a broken deny rule must not let the JVM reach a model server while a live run is going.

**java9plus patterns are read off JDK 8's own output, not guessed.**
`tests/fixtures/java9plus/capture.py` compiles 21 single-file cases on the pinned Zulu 8 and checks
in each one's raw `javac` output. All 18 Java 9+ cases fail to compile; the diagnostics are mostly
generic, which is the whole point:

| Feature | Since | JDK 8 says |
| --- | --- | --- |
| `var` | 10 | `cannot find symbol` / `symbol: class var` |
| records | 16 | `cannot find symbol` / `symbol: class record` |
| text blocks | 15 | `unclosed string literal` |
| switch expressions | 14 | `illegal start of expression` |
| `List.of` / `Map.of` / `Set.of` | 9 | `symbol: method of(...)` / `location: interface List\|Map\|Set` |
| `String.isBlank` / `strip` / `repeat` / `lines` | 11 | `symbol: method isBlank()` etc. / `location: class String` |
| `Stream.toList` | 16 | `symbol: method toList()` / `location: interface Stream` |
| `Optional.isEmpty` | 11 | `symbol: method isEmpty()` / `location: class Optional` |
| `Optional.orElseThrow()` no-arg | 10 | `cannot be applied to given types` / `found: no arguments` |
| `Collectors.teeing` | 12 | `symbol: method teeing(...)` |
| private interface methods | 9 | `modifier private not allowed here` |
| try-with-resources on a variable | 9 | `<identifier> expected` |
| diamond with anonymous class | 9 | `cannot use '<>' with anonymous inner classes` |

Because `cannot find symbol` is also what an ordinary typo produces, **every API pattern requires
the `symbol:`/`location:` detail lines** and the syntax patterns require corroborating source text
(`"""` for text blocks, `switch (` plus `->` for switch expressions). Three control fixtures --
`control-typo` (`xs.addd(...)`), `control-missing-import`, `control-type-mismatch` -- are ordinary
Java 8 mistakes kept as false-positive tests. Verified: all 18 features detected, all 3 controls
detected as nothing, and every pattern is exercised by the fixture it cites.

### 2026-09-30 02:10 MDT -- humaneval-x-java

**Dataset.** `zai-org/humaneval-x` (formerly `THUDM/humaneval-x`), file
`data/java/data/humaneval.jsonl`, pinned at revision
`62c78627f3072a1454fa0cb0184737cafe5e4198`, sha256
`2157a77a6ff808020adc20142228b4ff698048c0696b33110786400c47c5d79c`, 474,987 bytes, 164 records.
Hugging Face publishes no checksum for the file, so this is the first-download hash, pinned the same
way the EvalPlus datasets are. Fields present and used: `task_id`, `prompt`, `declaration`,
`canonical_solution`, `test`, `example_test`, plus an unused `text`. Every field the design expected
exists -- no renaming needed.

**Two field adaptations, both verified across all 164 records:**

1. **No trailing brace.** DESIGN-JAVA.md says to compile `prompt + canonical_solution + "}"`.
   `canonical_solution` already closes both the method and the class: brace balance of
   `prompt + canonical_solution` is exactly 0 for every record, and every `canonical_solution` ends
   with a closing brace pair. The extra brace would not parse. A test asserts the balance for all
   164 tasks.
2. **The hidden tests have no imports.** All 164 `test` values declare `public class Main` and
   **none** contains an `import` line, while using `List`, `Arrays` and friends. Upstream
   HumanEval-X concatenates prompt + solution + test into one `Main.java`, so the scaffold's imports
   cover the test. This harness compiles **two files** instead (`Solution.java` + `Main.java`) and
   copies each task's own import block into `Main.java`.

   Two reasons, both load-bearing. First, DESIGN-JAVA.md revisions item 1 requires knowing *which
   file* an error landed in to tell `signature-mismatch` from bad Java; in a single concatenated
   file every diagnostic says `Main.java` and that distinction is impossible. Second, the
   concatenated form makes a model writing `public class Solution` fail with "class Solution is
   public, should be declared in a file named Solution.java" -- a file-layout artifact, not a Java
   mistake. Import blocks are not uniform (159 tasks use `java.util.*` + `java.lang.*`, 4 add
   `java.util.stream.Collectors`, 1 adds `java.math.BigInteger` + `java.security.*`), so the block
   is copied per task. **Deviation from DESIGN-JAVA.md**, recorded here.

**prepare.py --suite humaneval-x-java:**

| | |
| --- | --- |
| tasks in dataset | 164 |
| canonical compiles and passes on JDK 8 | **99** |
| **skipped** | **65** |
| suite digest | `2dc561c5ada4b60b928a087b4952eb7012483e8e1ef4a8399466bb22152729df` |
| wall time | 45.5s |

**Every one of the 65 skips is `java9plus-usage`** -- after the classifier fixes below there
are no unexplained compile errors left. That is a finding about the dataset, not about any model:
**HumanEval-X Java is only 99/164 (60%) usable on a real JDK 8.** Features found:

| Feature | Tasks |
| --- | --- |
| `List.of` | 52 |
| `arrow labels in a switch statement` | 3 |
| `Optional.isEmpty` | 3 |
| `the `\s` escape in a string literal` | 3 |
| `pattern matching for instanceof` | 2 |
| `String.repeat` | 2 |
| `Map.of` | 1 |
| `static members in inner classes` | 1 |
| `String.strip` | 1 |
| `Stream.toList` | 1 |

The location matters too: **47 of the 65 skips have Java 9+ code only in the dataset's own
hidden `Main.java`, not in the canonical solution** (18 involve `Solution.java`). The dominant
cause is `List.of` in the *tests*: 55 of the 164 `test` values contain it, against 6 canonical
solutions. Those tasks are unscoreable on JDK 8 no matter what a model writes, because the hidden
test itself will not compile. Each per-task record keeps `java9plusInSolution`, so the two cases
stay separable in analysis, and the summarizer can report them apart.

**Two classifier bugs the real dataset exposed** that the synthetic fixtures alone had not:

1. **`location:` names the receiver, not the declaring type.** My patterns required
   `location: class String`, which is what javac prints for `" x ".strip()`. For `date.strip()` it
   prints `location: variable date of type String`. That silently hid `String.strip` in Java/124 and
   `Optional.isEmpty` on variables -- they were landing in the generic `compile-error` bucket and
   under-counting the headline java9plus number. Fixed with a `_location()` helper matching both
   forms, plus new fixtures `string-strip-on-variable` and `optional-isempty-on-variable` captured
   for both shapes.
2. **Four missing markers,** each now captured as its own fixture: arrow labels in a statement
   `switch` (Java 14, `: expected`), pattern matching for `instanceof` (Java 16, `')' expected`),
   static members in inner classes (Java 16, `Illegal static declaration in inner class`), and the
   `\s` escape in a string literal (Java 15, `illegal escape character`). The last is worth
   calling out: three canonical solutions write `"[.?!]\s*"` with a single backslash, which is only
   legal from Java 15.

The fixture set is now 27 cases (22 features plus 5 controls and receiver variants) against 22
patterns; every pattern is exercised by the fixture it cites and the three control fixtures are
still detected as nothing.

One dataset quirk worth recording: **Java/153's method is named `StrongestExtension`** with a
capital S. My first test asserted every entry point starts lowercase and failed on it; the parser was
right and the assertion was wrong. The test now pins it as a known exception.

## Live runs (Claude Fable 5.1, designing session; Sep 30, 2026, MDT)

Run from a frozen copy of the harness at commit `192da50` (plus the one-line digit-cap fix, later committed as `a3b7c37`), against the dedicated Ollama 0.34.4 server on 127.0.0.1:11436 with its own store; the implementer never touched that server. Records are in `runs/`, committed as they completed.

- 00:59: `qwen3.8:27b-q8_0`, humaneval-plus, thinking off, `--limit 5`: 5/5. Sandbox self-test recorded, `num_ctx` 16384 honored (`/api/ps` context 16384), unload confirmed. Record `20260930-qwen3.8-27b-q8_0-off-smoke.json`.
- 01:00-01:44: same model, full 164 tasks, thinking off: **149/164 pass@1 (90.9%), base 160/164 (97.6%)**, 13 wrong-answer, 2 timeout, median 18.44 tok/s, median 198.5 generated tokens, median 11.3 s per task. The run died at task 84 (HumanEval/83, 9,876-digit answers) on the harness-process `int` string-conversion cap; resumed with `--resume` after the fix and completed. Record `20260930-qwen3.8-27b-q8_0-humaneval-plus-off.json`.
- 01:15-02:00 (with the same crash and resume at task 10): `qwen3.8-flash-next-ud-q3kxl:latest` (Unsloth UD-Q3_K_XL), humaneval-plus, thinking off: **152/164 pass@1 (92.7%), base 159/164 (97.0%)**, 10 wrong-answer, 2 timeout, median 49.28 tok/s, median 202 generated tokens, median 4.5 s per task. Record `20260930-qwen3.8-flash-next-ud-q3kxl-humaneval-plus-off.json`.
- Failure overlap: both models fail HumanEval/32, 39, 76, 91, 116, 132, 145, 151, 163. The two shared timeouts are the model code, not the budget: on HumanEval/39 both wrote trial-division `is_prime` over Fibonacci numbers (canonical wall 0.075 s for the two plus inputs; the candidates exceed the 1.0 s per-input floor on the second); on HumanEval/163 both iterate `range(min(a,b), max(a,b)+1)` and the plus inputs include very large `a`, `b` (59 of 457 attempted inputs timed out before the task was cut off). EvalPlus's rule (`max(1 s, 4 x reference)`) fails these the same way.
- HumanEval/32 (`find_zero`) is a suspected grading artifact in both records: the 27B row reads "expected 17.3124550475086 got 17.3124550475086" and the Flash-Next row "expected -1.0 got 1.0" (a different root of the same polynomial). EvalPlus grades this task by checking that the polynomial evaluates to about zero at the returned root, not by root equality. Reported to the implementer; if the grader changes, both records need this task re-graded, which would move both scores up by one. **TODO** until resolved.
- 12:41: overnight chain started from the same frozen copy: mbpp-plus thinking off for both models, then humaneval-plus thinking on for both (16,384-token cap). Records will be committed as they land.
