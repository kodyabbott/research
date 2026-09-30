# Coding benchmark harness: design

Status: design, September 29, 2026. Implementation is delegated to a coding agent; this document is the spec. Keep it updated when the implementation diverges, with the reason.

## Why a new harness

The repository's existing coding checks are narrow by design: `local-model-benchmarks/coding_screen.py` runs eight authored JavaScript tasks and `humaneval_screen.py` runs pinned HumanEval-X JavaScript continuations, both inside a QuickJS WebAssembly guest. The 96-case `practical-json-v1` suite used by every M5 Max report never executes generated code. None of these measure Python coding ability against a standardized, test-backed suite, and none run on this Mac today (the JS screens depend on the Windows campaign harness).

Goal: one runner that generates code from a local model and grades it by executing hidden tests in a sandbox, producing raw records in the same evidentiary style as `uncensored-models-m5-benchmark/bench.py` (host state, model identity, every prompt and response, timings, refuse-to-overwrite).

## Scope for version 1

In:
- Python function-level suites: **HumanEval+** and **MBPP+** from EvalPlus, pinned by download URL and SHA-256, with base and plus (extended) test inputs graded separately.
- Two model backends: Ollama native `/api/chat` and OpenAI-compatible `/v1/chat/completions` (LM Studio, llama-server, `mlx_lm.server`). Plus a `replay` backend for tests that returns canned responses.
- Sandboxed execution on macOS via `sandbox-exec` with a deny-default profile, plus subprocess timeouts and CPU limits. A `docker` sandbox is a stub interface only; not implemented in v1.
- Thinking on/off/level control, greedy decoding, pass@1 with one sample per task.
- Resume of an interrupted run, refusal to overwrite, per-run JSON record, and a summarizer that emits Markdown tables and `comparison.json`.
- Unit tests, standard library only.

Out (design hooks only): JavaScript suites, repository-editing agent tasks (SWE-bench style), pass@k sampling, cloud reference models, Docker sandbox, Windows support.

## Constraints

- Python 3.11+ **standard library only** for the harness, tests, and summarizer (repository convention: "No pip packages are required"). Reading `.jsonl.gz` uses `gzip` + `json`.
- Generated code is executed **only** inside the sandbox. No path may `exec`/`eval` model output in the harness process. Expected outputs for the plus inputs are produced by running the canonical solution, also inside the sandbox, once at prepare time.
- The runner refuses endpoint port `11434` (the personal Ollama server) and requires an explicit `--endpoint`. Default is `http://127.0.0.1:11436`.
- Never modify the personal model library. Unload the model at the end of a run (`keep_alive: 0`) and confirm via `/api/ps`.
- Hardware serials and identifiers are excluded from saved host snapshots (same as the prior reports).
- Datasets and sandbox work directories live under `~/Documents/Codex/model-cache/coding-benchmark/`, never in the repository. Only code, tests, notes, README, and run records (JSON, typically under 2 MB each) are committed.

## Layout

```
coding-benchmark-harness/
  DESIGN.md              this file
  notes.md               implementation log (timestamped; what was tried, what failed)
  README.md              usage + results once runs exist (AI-ASSISTED-NOTE banner from CLAUDE.md)
  datasets.json          pinned dataset URLs, SHA-256, record counts, EvalPlus version
  prepare.py             download + verify datasets; compute and cache expected outputs in the sandbox
  run.py                 CLI: generate + grade one model on one suite; writes runs/<name>.json
  summarize.py           runs/*.json -> comparison.json + Markdown tables
  harness/
    __init__.py
    suites.py            Suite/Task dataclasses; loaders for humaneval-plus and mbpp-plus; suite digest
    backends.py          OllamaBackend, OpenAIBackend, ReplayBackend; common ChatResult
    extract.py           code extraction rules (pure functions)
    sandbox.py           SandboxExec (macOS) + interface; run_python(files, argv, timeout, cpu_seconds)
    grader.py            builds the in-sandbox test program; compares outputs; classifies failures
    record.py            run record schema, atomic save, resume, overwrite refusal, host snapshot
    sandbox_runner.py    the program executed INSIDE the sandbox (reads JSON from stdin, writes JSON to stdout)
  tests/
    test_extract.py test_grader.py test_sandbox.py test_record.py test_backends.py test_suites.py
  runs/                  raw run records (committed)
```

## Suites and datasets

Source: EvalPlus release assets (`HumanEvalPlus-v0.1.10.jsonl.gz`, `MbppPlus-v0.2.0.jsonl.gz` or whatever the current pinned versions are; the implementer records exact URLs, versions, and SHA-256 in `datasets.json` after verifying them against the EvalPlus GitHub release page and README). Each task record supplies `task_id`, `prompt`, `entry_point`, `canonical_solution`, `base_input`, `plus_input`, `atol`, and (MBPP+) `test` / assertion style. If a field name differs in the pinned version, the loader adapts and `notes.md` says so.

`prepare.py`:
1. Download to `~/Documents/Codex/model-cache/coding-benchmark/datasets/`, verify SHA-256 against `datasets.json`; refuse on mismatch.
2. For each task, run the canonical solution over base and plus inputs **inside the sandbox** and cache expected outputs as `expected/<suite>/<task_id>.json` with the dataset SHA-256 embedded. Tasks whose canonical solution fails or times out are recorded in `expected/<suite>/_skipped.json` with the reason and are excluded from scoring (count reported).
3. Print a summary: tasks, inputs per task, skipped.

`suites.py` exposes `load(suite_name, limit=None, ids=None) -> Suite` where `Suite.digest` is the SHA-256 of the ordered task ids + prompts + entry points + expected-output file hashes. The run record stores this digest so two runs are comparable only when digests match.

## Prompting

One user message, no system prompt, deterministic template per suite (store the rendered prompt in the record):

HumanEval+:
```
Complete the following Python function. Return the complete function (signature, docstring, and body) in a single ```python code block and nothing else.

{prompt}
```

MBPP+:
```
{text}

Write a Python function named `{entry_point}` that solves this. Return one ```python code block containing the complete function and nothing else. Example test: {first assertion}
```

Options: `temperature 0, seed 42, top_p 1, top_k 40, repeat_penalty 1.0` (Ollama); OpenAI backend sends `temperature 0, seed 42, top_p 1`. `num_predict`/`max_tokens`: 4096 thinking off, 16384 thinking on (both configurable). Context: 16384 default; the runner verifies via `/api/ps` that the loaded context matches and aborts otherwise.

Thinking control mirrors `bench.py`: `--think false|true|low|medium|high|default`. `default` omits the field (for imports that reject it). Record `unexpectedThinking` when thinking text appears with `--think false`.

## Code extraction (`extract.py`, pure, tested)

Input: assistant `content` (thinking is stored separately and never parsed for code). Rules, applied in order, and the rule name is saved with the record:
1. `fence-entry`: among ```python / ``` fenced blocks, choose the first whose text contains `def {entry_point}(`.
2. `fence-last`: otherwise the last fenced block.
3. `raw-entry`: no fences; content contains `def {entry_point}(`; use the whole content.
4. `raw-body`: content has no `def` at all; treat as a body continuation: indent and append to the suite prompt (HumanEval only).
5. `empty`: nothing usable; task fails with `failureClass: no-code`.

After extraction: if the code does not define `entry_point` but the suite prompt does, prepend the prompt (`completion-prefixed: true`). Strip leading `>>>` REPL noise. Never strip other content. Size cap 128 KiB.

## Sandbox (`sandbox.py`)

`SandboxExec` runs `/usr/bin/sandbox-exec -f <profile> -D WORKDIR=<dir> <python3> sandbox_runner.py` with:
- Profile: `(version 1) (deny default)`; allow `process-exec` for the chosen Python binary and its dyld dependencies; allow `file-read*` for system paths, the Python installation, and `WORKDIR`; **deny** `file-read*` under `$HOME` except `WORKDIR` (prevents reading the repository or personal data); allow `file-write*` only under `WORKDIR` and `/private/tmp/<run>`; `(deny network*)`; allow `sysctl-read` and the minimal `mach-lookup` set Python needs to start. The implementer discovers the minimal allow list empirically and documents each entry in `notes.md`.
- Fresh temporary `WORKDIR` per task, deleted afterward.
- `preexec_fn` sets `RLIMIT_CPU` (default 10 s per task), `RLIMIT_NOFILE 64`, `RLIMIT_FSIZE 16 MiB`; wall timeout default 30 s (`subprocess.run(timeout=...)`), stdout capped at 1 MiB, environment scrubbed to `PATH`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`.
- The Python used inside the sandbox is the same interpreter that runs the harness unless `--sandbox-python` is given; its path and version go in the record.

Required sandbox self-tests (run in `tests/test_sandbox.py`, and also at the start of every real run as `sandboxSelfTest` in the record; abort if any fails):
- network denied (`socket.create_connection(("127.0.0.1", 11436), 1)` raises),
- write outside WORKDIR denied,
- read of `$HOME/.ssh` and of the repository path denied,
- infinite loop is killed by CPU limit or wall timeout and reported as `timeout`,
- normal program returns its JSON.

If `sandbox-exec` is unavailable or a self-test fails, the runner refuses to execute model code. There is no "unsandboxed" fallback flag.

## Grading (`grader.py`, `sandbox_runner.py`)

`sandbox_runner.py` receives JSON on stdin: `{"code": str, "entry_point": str, "inputs": [[args...]...], "expected": [...] | null, "atol": float, "per_input_seconds": float}`. It `exec`s the code in a fresh module namespace with builtins only, resolves `entry_point`, and for each input calls the function with a per-input `signal.alarm`-based timeout, capturing the return value serialized through a deterministic encoder (handles tuples vs lists, sets, floats with `atol`, NaN, nested structures, non-serializable objects => `repr`). Output per input: `{"status": "ok"|"exception"|"timeout", "value": ..., "error": str}`. It never imports anything from the harness package (it is copied standalone into WORKDIR).

Comparison semantics (in the harness process, on the returned JSON, never executing anything): EvalPlus-style equality: exact for ints/strings/bools/None; tuples and lists compared as sequences; floats within `atol` (default 1e-6 when the task sets none); sets by membership. Implement as `same(expected, actual, atol)` with unit tests covering these cases.

Per-task outcome: `basePassed` (all base inputs ok and equal), `plusPassed` (all plus inputs), `failureClass` one of `none | no-code | syntax-error | runtime-error | wrong-answer | timeout | sandbox-error | truncated`, with the first failing input index and message. A task counts as passed for pass@1 only when both base and plus pass (`plusPassed`); `basePassed` is reported alongside.

## Run record (`record.py`)

`runs/<YYYYMMDD>-<label>.json`, atomic write (temp + rename) after every task. Refuse to overwrite an existing file unless `--resume`, in which case the protocol digest, suite digest, model digest, and options must match exactly and completed tasks are kept. Fields:

```
schemaVersion, label, startedAt, finishedAt, status (running|completed|incomplete|error), error
host: {model_identifier, chip, cpu_cores, gpu_cores, memory_gb, os_version, power_source}  (no serials)
runtime: {backend, endpoint, version, sandboxPython, sandboxProfileSha256, sandboxSelfTest}
model: {name, digest, details, capabilities, parameters, templateSha256, loadedContext, sizeVram}
protocol: {suite, suiteDigest, datasetSha256, promptTemplateSha256, think, options, outputCap, context, taskSeconds, cpuSeconds, samplingProfile: "greedy-v1", codeExecution: "sandbox-exec deny-default, see sandboxProfileSha256"}
tasks: [{id, prompt, response: {content, thinking, done_reason, eval_count, eval_duration, prompt_eval_count, prompt_eval_duration, total_duration, load_duration}, wallMs, code, extractionRule, completionPrefixed, truncated, unexpectedThinking, base: {passed, results}, plus: {passed, results}, failureClass, failureDetail}]
summary: {tasksTotal, tasksAttempted, basePass, plusPass, passAt1 (=plusPass/tasksTotal), failureClasses: {...counts}, medianWallMs, medianGenTokPerSec, medianGeneratedTokens, medianThinkingChars, truncated, unexpectedThinking, protocolValid}
unload: {confirmed, ...}
```

Timing: `genTokPerSec = eval_count / eval_duration` from the server where available (Ollama); the OpenAI backend records `usage` and wall time and leaves server timings null. Wall time is the HTTP round trip.

## CLI

```
python3 coding-benchmark-harness/prepare.py --suite humaneval-plus [--suite mbpp-plus]
python3 coding-benchmark-harness/run.py --backend ollama --endpoint http://127.0.0.1:11436 \
    --model qwen3.8:27b-q8_0 --suite humaneval-plus --think false --label qwen3.8-27b-q8_0-off \
    [--limit 20] [--ids HumanEval/0,HumanEval/1] [--context 16384] [--output-cap 4096] \
    [--task-seconds 300] [--cpu-seconds 10] [--resume]
python3 coding-benchmark-harness/summarize.py coding-benchmark-harness/runs/*.json \
    --markdown coding-benchmark-harness/RESULTS.md --json coding-benchmark-harness/comparison.json
python3 -m unittest discover -s coding-benchmark-harness/tests -v
```

`run.py` prints one line per task: `id  base=ok/fail  plus=ok/fail  class  gen_tok/s  wall_s`, and a final summary line. Non-zero exit on error/incomplete. `--limit 3` is the smoke path.

## Summarizer

Table columns: model, suite, think, tasks, base pass, plus pass (pass@1), no-code, syntax, runtime, wrong, timeout, truncated, median gen tok/s, median wall s, median generated tokens. One row per run; sorted by suite then pass@1 descending. `comparison.json` mirrors the rows with run file paths and digests. Refuse to combine runs with different suite digests in one table without a `mixedSuites: true` flag in the output and a warning line.

## Tests (standard library `unittest`)

- `test_extract.py`: each rule, fence language variants, multiple blocks, REPL noise, size cap, completion prefixing.
- `test_grader.py`: `same()` semantics; failure classification from runner outputs; a syntax error sample; per-input timeout sample (uses the real sandbox with a tiny program).
- `test_sandbox.py`: the five self-tests above; skipped with a clear message when not on macOS.
- `test_record.py`: atomic save, overwrite refusal, resume with matching/mismatching digests.
- `test_backends.py`: `ReplayBackend`; Ollama/OpenAI request bodies built correctly (think mapping, options) without network, using a fake `urlopen`.
- `test_suites.py`: loader on a 3-task fixture in `tests/fixtures/` (tiny synthetic jsonl.gz, not the real dataset), digest stability.

## Acceptance for v1

1. `python3 -m unittest discover -s coding-benchmark-harness/tests` passes on this Mac.
2. `prepare.py --suite humaneval-plus` downloads, verifies, computes expected outputs; reports skipped tasks (expected: 0 or a handful).
3. `run.py --backend replay` on the fixture suite produces a valid record and summary.
4. `run.py --backend ollama --model qwen3.8:27b-q8_0 --suite humaneval-plus --limit 5 --think false` against the dedicated 11436 server completes, with at least one pass, the sandbox self-test recorded, and the model unloaded afterward. (Only run this if no other benchmark is using the GPU; check `OLLAMA_HOST=127.0.0.1:11436 ollama ps` first and wait if a model is loaded by another process.)
5. `notes.md` documents every sandbox profile entry, every deviation from this design, and any dataset-field adaptation. `README.md` has the banner and usage; no results claims beyond what was run.

## Open questions for Kody (do not block on these; note the default taken)

- Should MBPP+ prompts include all three provided assertions (as in the EvalPlus paper) or only the first? Default: first assertion only, to keep the model from pattern-matching all tests.
- Thinking-on output cap of 16384 makes a 164-task run slow on dense 27B models (roughly 3-6 s per 100 tokens at 18 tok/s). Default stays 16384; `--limit` is the knob.
