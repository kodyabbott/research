# Coding benchmark harness: HumanEval+ / MBPP+ for local models, graded in a sandbox

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Kody directed the work; the harness was designed by Claude Fable 5.1 and implemented by Claude Opus (Anthropic) via Claude Code. For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

> [!IMPORTANT]
> **This harness has not yet been run against a live model.** Every component is implemented and
> tested, both datasets are prepared, and an end-to-end run works against the replay backend. The
> Ollama and OpenAI-compatible backends were exercised only with a fake `urlopen`, because a
> separate benchmark held the GPU during implementation. The only results in this repository come
> from the synthetic fixture suite and a canned model response; there are no model scores here.

A runner that asks a locally hosted model to write Python functions, then grades the answers by
executing EvalPlus's hidden tests inside a deny-default macOS sandbox. One greedy sample per task,
pass@1, with the full prompt, response, timings and per-input outcome kept in a raw JSON record.

[DESIGN.md](DESIGN.md) is the specification. [notes.md](notes.md) is the implementation log,
including every sandbox rule, every deviation from the design, and the EvalPlus sources the grading
rules were ported from.

## What is measured

| | |
| --- | --- |
| Suites | **HumanEval+** (EvalPlus `v0.1.10`, 164 tasks) and **MBPP+** (EvalPlus `v0.2.0`, 378 tasks), pinned by URL and SHA-256 in [datasets.json](datasets.json) |
| Test inputs | 1570 base + 122,683 plus inputs for HumanEval+; 1174 base + 39,841 plus for MBPP+ |
| Metric | **pass@1** with one sample per task. A task counts as passed only when **every base input and every plus input** matches. The base-only rate is reported alongside |
| Sampling | greedy: `temperature 0, seed 42, top_p 1, top_k 40, repeat_penalty 1.0` (`samplingProfile: greedy-v1`) |
| Prompting | one user message, no system prompt, no few-shot examples; the rendered prompt is stored per task and the template's SHA-256 in the record |
| Thinking | `--think false\|true\|low\|medium\|high\|default`. Thinking text is stored separately and **never parsed for code**. A run is flagged `unexpectedThinking` if reasoning appears with `--think false` |
| Timings | `genTokPerSec = eval_count / eval_duration` from the server (Ollama). The OpenAI-compatible backend records `usage` and wall time and leaves server timings `null` |
| Failure classes | `none`, `no-code`, `syntax-error`, `runtime-error`, `wrong-answer`, `timeout`, `sandbox-error`, `truncated` |

**What it is not.** Not a repository-editing agent evaluation (no SWE-bench-style tasks), not pass@k,
not a JavaScript or Java suite, and not a general intelligence score. Function-level Python only.

## Usage

Standard library only, Python 3.11+. No pip packages are required or used.

```bash
# 1. Download and verify the datasets, then compute expected outputs in the sandbox (once).
python3 coding-benchmark-harness/prepare.py --suite humaneval-plus --suite mbpp-plus

# 2. Run a model. --endpoint is required and port 11434 (the personal Ollama server) is refused.
python3 coding-benchmark-harness/run.py --backend ollama \
    --endpoint http://127.0.0.1:11436 --model qwen3.8:27b-q8_0 \
    --suite humaneval-plus --think false --label qwen3.8-27b-q8_0-off

# Smoke path: five tasks.
python3 coding-benchmark-harness/run.py --backend ollama \
    --endpoint http://127.0.0.1:11436 --model qwen3.8:27b-q8_0 \
    --suite humaneval-plus --think false --limit 5 --label smoke

# 3. Summarize.
python3 coding-benchmark-harness/summarize.py coding-benchmark-harness/runs/*.json \
    --markdown coding-benchmark-harness/RESULTS.md \
    --json coding-benchmark-harness/comparison.json

# Tests.
python3 -m unittest discover -s coding-benchmark-harness/tests -v
```

Useful flags: `--limit N`, `--ids HumanEval/0,HumanEval/1`, `--context 16384`, `--output-cap`,
`--task-seconds`, `--cpu-seconds`, `--grade-wall-seconds`, `--resume`, `--keep-loaded`,
`--sandbox-python`, `--stop-on-base-failure`.

`prepare.py` writes datasets and expected outputs under
`~/Documents/Codex/model-cache/coding-benchmark/`, never into this repository. Only code, tests,
notes, the README and run records are committed.

### Run hygiene

- `run.py` refuses to overwrite an existing record. `--resume` continues one, and only if the suite
  digest, dataset SHA-256, prompt-template SHA-256, model name and digest, sandbox profile hash, and
  every sampling option match exactly.
- The record is rewritten atomically (temp file + rename) after every task.
- The model is unloaded at the end via `keep_alive: 0` and the unload is confirmed through
  `/api/ps`.
- `run.py` aborts if the server already has a model loaded, or if the loaded context length does not
  equal the requested `options.num_ctx`.
- Host snapshots contain no serial numbers, hardware UUID, UDID or MAC addresses.
- `suiteDigest` covers the ordered task ids, rendered prompts, entry points and expected-output
  hashes. Two runs are comparable only when their digests match; `summarize.py` refuses to present
  mixed digests without a `mixedSuites: true` flag and a printed warning.

## The sandbox

Generated code is executed **only** inside `sandbox-exec`, through `harness/sandbox_runner.py`,
which is copied standalone into a fresh per-task work directory. The harness process never calls
`exec` or `eval` on model output; it reads type-tagged JSON back out of the work directory and
compares values. **There is no unsandboxed fallback flag.** If `sandbox-exec` is missing or any
self-test fails, the run refuses to start.

The profile is `(version 1) (deny default)`. Verified properties, re-checked at the start of every
run and stored in the record as `runtime.sandboxSelfTest`:

| Check | How it is verified |
| --- | --- |
| **Network denied** | The harness opens a real listener on `127.0.0.1`, the sandboxed probe tries to connect, and the check requires `PermissionError`/`EPERM` *and* that the listener accepted nothing. A connect to a dead port would prove nothing. |
| **Writes outside the work directory denied** | Writes to `/private/tmp` and to `$HOME` both return `EPERM`, and no file appears. |
| **Reads outside the work directory denied** | `$HOME` is denied, including this repository. Probes target files that actually exist so `ENOENT` cannot be mistaken for denial. |
| **Runaway code is killed** | An infinite loop is killed by `RLIMIT_CPU` (SIGXCPU) or the wall-clock timeout and is reported as `timeout`. |
| **A normal program returns its JSON** | Sanity check that the profile is not so tight that nothing runs. |

Also enforced: no `process-fork`, so the sandboxed process cannot spawn helpers
(`subprocess.run(["/bin/echo"])` raises `PermissionError`); `RLIMIT_NOFILE` 64; `RLIMIT_FSIZE`
128 MiB; a scrubbed environment with `HOME` and `TMPDIR` pointing into the work directory; a
per-input `setitimer` timeout of `max(1.0 s, 4 x canonical per-input time)`; and a per-task
`RLIMIT_CPU` of at least 60 s (scaled up from the canonical solution's measured cost where that is
larger) plus a wall-clock timeout. Work directories are deleted after each task. The
profile template's SHA-256 is recorded in every run.

Every allow rule and the empirical process that produced it -- including the macOS firmlink and
ancestor-`realpath()` findings that make a naive profile fail with a silent `SIGABRT` -- is
documented in [notes.md](notes.md).

## Grading fidelity to EvalPlus

Expected outputs are produced once, at prepare time, by running each canonical solution
(`prompt + canonical_solution`, exactly as `evalplus.evaluate.get_groundtruth` does) over the base
and plus inputs **inside the same sandbox**, recording per-input wall times at the same time (the
call only, as `trusted_exec` does). **Both suites prepare with 0 skipped tasks: 164/164 and
378/378.**

Ported from EvalPlus tag `v0.3.1`, commit `e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2` (files and
line-level citations in [notes.md](notes.md)):

- `mbpp_deserialize_inputs` -- MBPP+ stores tuples, sets and complex numbers as JSON lists and
  strings; without the task-id-keyed reconstruction the canonical solutions receive wrong types.
- The eight `MBPP_OUTPUT_SET_EQ_TASKS` (compared as sets, order and duplicates ignored).
- The three `MBPP_OUTPUT_NOT_NONE_TASKS` (graded on "returned something", both sides reduced to
  booleans inside the sandbox, including EvalPlus's `isinstance(out, bool)` exception).
- `are_equivalent` (Mbpp/164), `sum_div` (Mbpp/295), `surface_Area` (Mbpp/581),
  `digit_distance_nums` (Mbpp/558), and HumanEval `find_zero` (checks the polynomial root, not the
  recorded value).
- The float rule: `atol == 0` with a float-shaped expected value enforces `1e-6`; when a tolerance
  applies, types and lengths must match and values must be within `atol` at `rtol = 1e-07`.
- `DEFAULT_MIN_TIME_LIMIT = 1.0` and `DEFAULT_GT_TIME_LIMIT_FACTOR = 4.0` for per-input timeouts.
- `deepcopy` of every input before the call, because some solutions mutate their arguments.

Values cross the sandbox boundary through a type-tagged encoding and are rebuilt as native Python
objects before comparison, so `(1, 2) != [1, 2]`, sets compare by membership, NaN never matches, and
big integers, complex numbers and bytes survive intact.

## Limitations

- **Never run against a live model.** See the note at the top.
- **macOS only.** `sandbox-exec` is a macOS facility, and it is formally deprecated by Apple even
  though it works on macOS 27. The Docker sandbox in the design is an interface stub, not an
  implementation. There is no Windows or Linux path.
- **Only the interpreter's own site-packages are importable inside the sandbox.** numpy 2.5.3,
  Pillow 12.3.0, certifi, pybind11, pip and wheel are reachable (they live under the readable
  interpreter prefix); scipy, sympy and pandas are not installed on this machine at all, and
  anything in the user site-packages under `$HOME` is unreadable by design. numpy needed
  `(allow sysctl-read)` -- which DESIGN.md's sandbox section lists -- because it calls `os.uname()`
  during import.
- **Per-input timeouts are evadable from inside.** Candidate code shares the interpreter with the
  `setitimer` timer and could reinstall the handler. EvalPlus has the same exposure. The per-task
  `RLIMIT_CPU` and wall-clock timeout are the backstop and cannot be evaded.
- **Oversized values are compared by hash.** About 0.1% of expected values (74 of 124,253 in
  HumanEval+, 94 of 41,015 in MBPP+) are too large to ship out of the sandbox and are compared by
  SHA-256 of their canonical form: exact equality only, no tolerance and no special oracle. None of
  the affected tasks has a special oracle and all have `atol == 0`.
- **Serialization, not the solutions, dominates grading cost on a few tasks.** EvalPlus compares
  large values with one C-speed `==`; this harness serializes them, which is about two orders of
  magnitude slower. `Mbpp/255` returns a single value whose canonical form is 3.0 GB and takes
  ~193 s to hash, against 0.669 s of actual function time. The per-task CPU and wall ceilings are
  therefore scaled from the canonical solution's own measured cost
  (`max(--cpu-seconds, 4 x canonical sandbox wall seconds)`), so a correct answer is not mis-scored
  as a `timeout`; the effective budget is recorded per task. Three tasks need this: `Mbpp/255`
  (~193 s), `HumanEval/130` (~14 s) and `Mbpp/630` (~4 s).
- **Per-input detail in records is compact,** not a full value dump: a one-character status per
  input, status counts, and the first failing input with truncated `repr`s. A full dump of
  HumanEval+'s ~123,000 plus inputs would not fit the repository's run-record budget.
- **`sys.set_int_max_str_digits(0)`** is set inside the sandbox. Python 3.11+ caps int-to-str
  conversion at 4300 digits; two HumanEval+ tasks legitimately exceed that and EvalPlus's reference
  environment predates the cap.
- **Not a dedicated host.** Runs happen on an interactive desktop, which the record states as a
  caveat. Thermal and power state are captured before and after.
- **`atol` is recomputed per input** rather than reusing EvalPlus's loop-carried value; see
  notes.md. This is stricter and can only differ for a task with mixed float/non-float expected
  values.

## Layout

```
DESIGN.md        the specification (and DESIGN-JAVA.md, a separate Java effort)
notes.md         implementation log: sandbox rules, EvalPlus citations, deviations
datasets.json    pinned dataset URLs, versions, SHA-256, record and input counts
prepare.py       download + verify + compute expected outputs and canonical timings
run.py           generate and grade one model on one suite -> runs/<name>.json
summarize.py     runs/*.json -> RESULTS.md + comparison.json
harness/         suites, backends, extract, grader, sandbox, sandbox_runner, values, record
tests/           unittest suite; fixtures/ holds the 3-task synthetic suite and replay responses
runs/            raw run records (currently one fixture/replay run, no model scores)
```

`runs/20260929-replay-fixture.json` is a **fixture/replay** record: three synthetic tasks answered
with canned text, kept so the end-to-end path and the summarizer have something real to act on. It
is not a model measurement.
