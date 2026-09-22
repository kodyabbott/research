# Mac comparison research notes

## Scope and source state

- Requested September 22, 2026: clone Kody's GitHub research repository, inspect the nightly benchmarks, and run some of the same models on the new MacBook.
- Cloned `https://github.com/kodyabbott/research` to `/Users/kody/repos/research`. The fetched tip was `db7b8bc` (September 11). These are the latest committed results available in this clone, not proof that the Windows scheduler has produced nothing since then.
- New local branch: `codex/m5-max-benchmark-comparison`. Original Windows policy, canceled campaigns, historical raw records, and scheduler are unchanged. No push was requested.
- Initial selection: Qwen3-Coder 30B Q4_K_M, GPT-OSS 20B MXFP4 with low reasoning, and Gemma 4 31B Q8_0 with thinking off. The first two provide an exact registry-artifact match; Gemma provides the pinned dense-model comparison.

## Verified preparation

- Live `system_profiler`: Mac17,6 MacBook Pro, M5 Max, 18 CPU cores, 40 GPU cores, 128 GB memory, macOS 26.5 (25F71). Hardware serials and identifiers are excluded from saved research evidence.
- AC power connected, battery 100%; `pmset -g custom` reported `powermode 2`. No power settings were changed.
- Installed Ollama client was 0.34.2. Downloaded the standalone official 0.32.13 Darwin archive so the comparison uses the historical Windows version without replacing the installed app.
- [Release](https://github.com/ollama/ollama/releases/tag/v0.32.13), [archive](https://github.com/ollama/ollama/releases/download/v0.32.13/ollama-darwin.tgz), [published checksum](https://github.com/ollama/ollama/releases/download/v0.32.13/sha256sum.txt). Verified archive SHA-256: `71efd44f3b5f2019f42bae17ae58eb3de8bd25ce3ca3bc89aea58e53e5d091d1`.
- Qwen registry manifest: `06c1097efce0431c2045fe7b2e5108366e43bee1b4603a7aded8f21689e90bca`; GPT-OSS: `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`. Ollama pull completed and reported both exact historical digests.
- Gemma source: [pinned Hugging Face repository](https://huggingface.co/unsloth/gemma-4-31B-it-GGUF/tree/c1ac76e99d5513b141e8adde7288b85c3f9c32ec), `gemma-4-31B-it-Q8_0.gguf`, 32,635,677,632 bytes, SHA-256 `d5808e5874e660a85ab45b2da00c9e3b4a003621249a333772232d1a703e4d67`. Metadata was checked at the pinned revision before download; the complete file is verified before import.
- Dedicated server on `127.0.0.1:11436`. Store: `/Users/kody/Documents/Codex/model-cache/mac-benchmarks/ollama`. Process environment: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_CONTEXT_LENGTH=8192`, `OLLAMA_NO_CLOUD=1`. No personal model library or existing server was used.
- A two-token Qwen smoke response returned `ready`. Server log confirmed Metal and 49/49 layers offloaded. This smoke check overlapped downloads and is excluded from all timed results.
- Source snapshots, prompts, raw responses, identity checks, actual loaded model/context, host state, timing fields, and unload verification are retained in each replay record.

## Measurement and validation decisions

- Reused the checked-in `workload_suite.py`, `quality_screen.grade`, `nightly.Harness.measurement`, `nightly.exact_lines`, and `api_probe.py`. No generated code is executed by this screen.
- Every saved case and expected answer must match the checked-in suite. The first 24 cases cover three examples from each of eight categories; all models receive the same saved prompts.
- Four new offline tests verify historical score reconstruction, refusal before inference on identity mismatch, cleanup and evidence preservation after request failure, and parameter ordering normalization. Nine existing workload regression tests also passed.
- An initial metadata comparison found identical parameter values printed in different group order. The runner now compares named parameter groups while preserving repeated values. This is serialization normalization; no inference settings were changed.
- Standard throughput uses three warmed repetitions. Workload accuracy uses one sample per case. Full 96-case sweeps, JavaScript function generation, HumanEval-X, MLX, and optimized current-runtime comparisons remain outside this initial run.
- GPT-OSS cannot supply a matched thinking-off throughput row. Its low-reasoning workload is compared to the saved low-reasoning Windows result with the same output cap.
- The original Windows primary server environment is unknown. Historical Gemma private-server performance overrides were unset. The Mac has an explicit one-request, one-model server configuration; this and backend differences limit hardware-only attribution.

## Reproduction

Python 3.11 or later is needed for the replay runner; it uses the standard library and the repository's existing helpers. No pip packages are required. On this Mac, start the retained runtime in a separate terminal:

```sh
OLLAMA_HOST=127.0.0.1:11436 \
OLLAMA_MODELS=/Users/kody/Documents/Codex/model-cache/mac-benchmarks/ollama \
OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NO_CLOUD=1 \
/Users/kody/Documents/Codex/2026-09-22/le/work/ollama-0.32.13/ollama serve
```

Then run from the repository root:

```sh
python3 -m unittest discover -s mac-model-benchmarks -p 'test_*.py' -v
python3 mac-model-benchmarks/mac_replay.py --repo "$PWD" --model qwen3-coder:30b --output mac-model-benchmarks/runs/NEW-qwen.json
python3 mac-model-benchmarks/mac_replay.py --repo "$PWD" --model gpt-oss:20b --output mac-model-benchmarks/runs/NEW-gpt-oss.json
python3 mac-model-benchmarks/mac_replay.py --repo "$PWD" --model nightly-bench-d5808e5874e660a8:latest --output mac-model-benchmarks/runs/NEW-gemma.json
```

Use unique filenames: the runner refuses to overwrite an existing raw run. It defaults to the dedicated localhost port 11436 and refuses port 11434. Confirm no model is loaded before starting; the runner unloads each target after measurement. Shut down the task-owned server after the replay.

API timing semantics and thinking options were checked against the [Ollama chat reference](https://docs.ollama.com/api/chat); server configuration and loaded GPU placement against the [Ollama FAQ](https://docs.ollama.com/faq). `load_duration` is not time to first token. Generation throughput is `eval_count / eval_duration`; prompt throughput follows the existing harness's reported-token convention.

## Results and completion

Final observations, raw-run links, and caveats appear in [README.md](README.md). Completion and artifact-import evidence will be recorded alongside the runs.

## Native MLX extension and final findings

The user selected the Mac-focused option: find strong local performance with MLX or LM Studio, with runtime differences labeled. MLX was used directly. This extends the initial matched-Ollama run; the original Windows measurements remain the historical reference.

Installed an isolated Python 3.12.14 environment at `/Users/kody/Documents/Codex/2026-09-22/le/work/mlx-venv`, with MLX 0.32.2 and MLX-LM 0.31.3. All 34 package versions are recorded in `requirements-mlx.txt`. No existing system Python environment or installed Ollama application was replaced. A sandbox restriction prevented `uv pip freeze` from opening its default cache; the completed dependency snapshot was read directly from installed package metadata instead.

Pinned, downloaded, and verified every model file:

- `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`, revision `6e302ea604ad9ab206367e2c501d1571023e7b6d`, about 17.20 GB.
- `mlx-community/gpt-oss-20b-MXFP4-Q8`, revision `773a7da77e569019bb0fd17a554b263738d669a3`, about 12.10 GB.

These native conversions have different weight formats, quantization, and chat templates from the GGUF runs. The MLX requests use fresh KV caches and an 8192-token rotating-cache limit. Complete prompts, rendered templates, generated token IDs, raw channel text, timing, and peak MLX memory are saved. Native per-request latency is measured in-process; compare to the Ollama HTTP latency with that overhead difference disclosed.

The first GPT-OSS warmup exposed a bug in the new parser: this artifact uses `<|start|>`, `<|channel|>`, and `<|message|>` spellings. The parser initially recognized the older alias spellings only. The zero-case diagnostic is preserved, a regression test was added from its actual response, and the corrected run completed all 24 cases. This was a harness correction, not a model failure. Only the final channel is graded; reasoning text is retained separately.

Activation quantization was inspected in installed `mlx_lm/utils.py`; it requires nvfp4 or mxfp8 and does not apply to these affine/mxfp4 artifacts. Instead, Qwen's prefill batch was increased from 2048 to 8192 for a separately labeled repeat. No additional model download was needed.

Final native observations:

- Qwen, prefill 2048: 3/24, 0.481 s median, 139.68 generation tok/s and 4780.08 ingest tok/s in the short battery.
- Qwen, prefill 8192: 3/24, 0.473 s median, 136.44 generation tok/s and 5801.65 ingest tok/s.
- GPT-OSS low reasoning: 20/24, 3.001 s median, 131.02 median generation tok/s across workload responses. This last rate is a workload statistic, not the short-battery metric.

Qwen's larger prefill is the strongest long-prompt result among tested settings; its generation speed did not materially improve. Both MLX model conversions had lower observed median latency and one fewer correct case than the Mac GGUF rows. One pass is insufficient to establish a stable quality difference or a general model ranking. The 24-case screen is not a coding benchmark.

### Native rerun commands

From the repository root, with the retained model cache and pinned environment:

```sh
HF_HUB_OFFLINE=1 /Users/kody/Documents/Codex/2026-09-22/le/work/mlx-venv/bin/python mac-model-benchmarks/mlx_replay.py --repo "$PWD" --selection mac-model-benchmarks/native-artifacts/Qwen3-Coder-30B-A3B-Instruct-4bit-verified.json --prefill-step-size 8192 --output mac-model-benchmarks/native-runs/NEW-qwen-mlx.json
HF_HUB_OFFLINE=1 /Users/kody/Documents/Codex/2026-09-22/le/work/mlx-venv/bin/python mac-model-benchmarks/mlx_replay.py --repo "$PWD" --selection mac-model-benchmarks/native-artifacts/gpt-oss-20b-MXFP4-Q8-verified.json --output mac-model-benchmarks/native-runs/NEW-gpt-oss-mlx.json
```

The model process has a 30-minute outer deadline; each generation has a 120-second alarm. The new native worker exits after the run and releases its model allocation. Timed native runs began after downloads completed and after the dedicated Ollama server was stopped. Small metadata/documentation checks ran during portions of the interactive experiment; the desktop was not isolated.

### Completion verification

- Six successful configurations, each with 24 cases: three matched Ollama rows and three native MLX rows. All 144 saved case scores were independently regraded from raw final answers.
- Eight new harness tests and nine existing workload tests passed. No final successful row had a truncated response, unexpected thinking, channel parse error, or native context-budget overflow.
- Dedicated Ollama port 11436 is closed. All benchmark workers and their temporary keep-awake processes exited. Native model release left only 8 or 24 bytes of active MLX bookkeeping allocations before process exit; swap usage was zero in saved snapshots.
- Original `local-model-benchmarks` files have zero diff from cloned commit `db7b8bc`. No scheduled task was created or changed, and nothing was pushed.
- The task model cache occupies about 149 GiB, including retained GGUF source/import copies and the native models. The small standalone runtime and Python environment are retained for reruns. Weights and environments are outside the Git repository.

See `completion.json`, `server-provenance.json`, `gemma-import.json`, and `native-artifacts/` for the verification records. The final report is `README.md`; the exact-artifact system comparison is `OLLAMA-COMPARISON.md`.
