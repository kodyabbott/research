# Coding benchmark harness -- implementation log

Running log kept while implementing [DESIGN.md](DESIGN.md). Newest entries at the bottom of each
section. Times are Mountain Daylight Time (America/Denver).

Design by Claude Fable 5.1; implementation by Claude Opus (Anthropic) via Claude Code, directed by
Kody Abbott.

## Environment

Captured 2026-09-29 23:59 MDT on the 2023 MacBook Pro 16" (M2 Max, 64 GB):

| Item | Value |
| --- | --- |
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
| `(deny network*)` | Hard requirement. Verified by self-test against a live local listener (EPERM, listener accepted nothing). Redundant with `deny default`, kept explicit so the intent survives edits. |
| `(allow process-exec (literal @PYTHON@) (literal @PYTHON_APP@) + Data-volume mirrors)` | The interpreter binary and the `Python.app` binary it re-execs. Narrow literals, not `process-exec*`. `process-fork` is **not** allowed, so the sandboxed process cannot spawn helpers -- verified: `subprocess.run(["/bin/echo"])` raises `PermissionError`. |
| `(allow file-read* (subpath @PYTHON_PREFIX@) + mirror)` | The interpreter, its framework `Python` dylib, and the standard library. `@PYTHON_PREFIX@` is `/opt/homebrew` here, derived from the resolved interpreter path. |
| `(allow file-read* (subpath "/usr/lib") (subpath "/usr/share") (subpath "/System/Library"))` | Not strictly required with the dyld shared cache (see minimizer result above), kept as defensive breadth so the profile also works with `/usr/bin/python3` or a python that loads on-disk system dylibs, ICU data, or zoneinfo. All are outside `$HOME`, so they do not weaken the `$HOME` read denial. |
| `(allow file-read* (subpath "/private/var/db/dyld") + mirror)` | dyld shared-cache metadata; same defensive rationale. |
| `(allow file-read* (literal "/") (literal "/opt") (literal "/System/Volumes") (literal DATA) (literal DATA/opt))` | Ancestor-directory reads required by the interpreter's startup `realpath()` (finding 3). Directory entries only -- `literal`, not `subpath`, so this grants nothing recursive. |
| `(deny file-read* (subpath @HOME@) + mirror)` | The desirable-but-optional requirement from the design revisions: no reads anywhere under `$HOME`. Placed **after** the system allows and **before** the WORKDIR allow, because later rules win. Verified against two files that actually exist (`DESIGN.md` in the repo and a temp file created under `$HOME`), both `PermissionError:EPERM` -- ENOENT would not have proved denial. |
| `(allow file-read* (subpath @WORKDIR@) + mirror)` | The per-task work directory, which is itself under `$HOME` (`~/Documents/Codex/model-cache/coding-benchmark/work/task-*`). This is the only readable location inside `$HOME`. |
| `(allow file-write* (subpath @WORKDIR@) + mirror)` | The only writable location anywhere. Hard requirement, verified: writes to `/private/tmp` and to `$HOME` both return `PermissionError:EPERM` and no file is created. |

Rules that turned out to be **unnecessary and were left out**: `sysctl-read`, `mach-lookup`,
`signal`, `process-fork`, `file-read-metadata`, and any `/dev` access. Python 3.14.7 starts and runs
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

**Third-party packages are not importable in the sandbox.** `import numpy` raises
`PermissionError` (its install lives under `$HOME`); scipy/sympy/pandas are not installed at all.
EvalPlus's own reference environment has numpy. This affects only *candidate* code that tries to
import it (scored as a runtime error); the HumanEval+/MBPP+ canonical solutions are pure standard
library, so expected outputs are unaffected. Noted in README limitations.

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
