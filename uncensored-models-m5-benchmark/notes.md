# Uncensored models on the M5 Max -- research notes

## Scope

- Requested September 26, 2026: download five uncensored models from Hugging Face that fit this Mac, benchmark them, and rank them.
- Kody chose the cross-family set (best-known uncensored build per base model) over a same-base head-to-head, and asked for capability, speed, and a refusal measurement.
- Host: MacBook Pro, Apple M5 Max, 128 GB unified memory, 1.4 TiB free disk at start.
- Branch: `codex/m5-max-benchmark-comparison` (local, unpushed). No existing folder, harness, policy, or historical record is modified.

## Selection

Candidates came from `hf models ls --search {uncensored,abliterated,heretic,obliterated} --apps {mlx-lm,llama.cpp}` sorted by downloads and trending score on September 26, 2026, then filtered to bases the [September 22 Mac guide](../mac-model-guide-2026-09/README.md) already considered practical on 128 GB. Popularity figures are Hugging Face 30-day downloads as of September 26, 2026.

| Base | Repository | File | Bytes | Why |
|---|---|---|---:|---|
| Qwen3.8-27B (dense) | `llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF` | `...-Q8_0.gguf` | 30,484,799,616 | Heretic build that publishes method and KL; standard Q8_0 |
| Qwen3.6-35B-A3B (MoE) | `HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive` | `...-Q4_K_M.gguf` | 21,166,758,016 | Most-liked uncensored repo in the search (~3.8K likes); method undisclosed |
| Gemma 4 31B (dense) | `llmfan46/gemma-4-31B-it-uncensored-heretic-GGUF` | `...-Q8_0.gguf` | 32,635,675,776 | Heretic ARA build; stock Gemma 4 31B Q8_0 was measured on this Mac on Sep 22 |
| Qwen3-Coder-Next (MoE) | `bartowski/huihui-ai_Qwen3-Coder-Next-abliterated-GGUF` | `...-Q4_K_M.gguf` | 48,556,632,000 | Coding-specific; huihui-ai abliteration (Sumandora method) |
| GPT-OSS 120B (MoE) | `HauhauCS/GPTOSS-120B-Uncensored-HauhauCS-Aggressive` | `...-MXFP4.gguf` | 65,369,016,544 | Largest practical reasoning model; method undisclosed |

Exact revisions and LFS SHA-256 values are in [selection.json](selection.json). Each imported Ollama blob digest is compared against the pinned SHA-256.

Quantization differs across rows (Q8_0, Q4_K_M, MXFP4). This ranking answers "which of these should I run," not "which uncensoring method preserves the most capability."

## Runtime

- Installed Ollama app binary 0.34.4, run as a dedicated server on `127.0.0.1:11436` with its own store at `~/Documents/Codex/model-cache/uncensored-benchmark/ollama`. Environment: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_CONTEXT_LENGTH=8192`, `OLLAMA_NO_CLOUD=1`. The primary server on 11434 and the personal model library are not used.
- The retained 0.32.13 runtime from the Sep 22 work was for Windows version parity. That doesn't apply here, so these runs use the current install.
- Models pulled with `ollama pull hf.co/<repo>:<quant>`.

## Benchmark design

[bench.py](bench.py) reuses `local-model-benchmarks` helpers: `workload_suite.cases()`, `quality_screen.grade`, `nightly.Harness.measurement`, `nightly.exact_lines`, `api_probe.py`.

- **Workload:** all 96 cases of `practical-json-v1` (eight categories x 12), strict JSON grading, one sample per case, temperature 0, seed 42, 8192 context, 2048 output cap, 120 s per case. The first 24 cases match the Sep 22 Mac rows. Generated code is never executed. This is an authored answer-quality screen, not a coding benchmark or general ranking.
- **Throughput:** same prompts as `mac_replay.py`: warmup, three repetitions of a short generation and a ~7K-token ingest, plus three exact-output checks.
- **Refusal:** Heretic's own evaluation defaults at commit `3521f86`: `mlabonne/harmful_behaviors` `test[:100]`, system prompt "You are a helpful assistant.", 100-token response cap, and Heretic's case-insensitive substring marker list. `mlabonne/harmless_alpaca` `test[:100]` gets the same classifier, as an upper bound on over-refusal (markers like "illegal" can match benign answers). **Only verdicts and matched marker names are saved; response text is discarded in memory.** Prompt lists are cached outside the repository; runs record dataset revision and prompt-list SHA-256.
- **Thinking:** off for all models that support toggling. GPT-OSS cannot disable reasoning, so it runs at `low` effort (same as the Sep 22 GPT-OSS 20B row).

## Log

- 23:41 MDT: dedicated server started (0.34.4). First pull: Qwen3.6-35B-A3B Q4_K_M, used as the smoke test for architecture support and thinking control before the remaining ~177 GB.
- 23:58 MDT: Qwen3.6-35B-A3B pull complete. Blob `sha256-bbef58c3...574231` and size 21,166,758,016 match the pinned LFS values. Ollama also pulled the repository's 899 MB vision projector. `/api/show`: family `qwen35moe`, capabilities `tools, thinking, completion, vision`.
- Smoke test (excluded from results): `think: false` returned `391` with empty `thinking`; `think: true` returned 517 thinking characters. Server log shows Metal on the M5 Max; `/api/ps` reports the model resident at 8192 context. Architecture support and thinking control confirmed, so the remaining four pulls proceed.
