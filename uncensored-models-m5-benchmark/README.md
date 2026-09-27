# Uncensored local models on the M5 Max: capability, speed, refusals

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Claude Opus 5.5). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Measured September 27, 2026, on this MacBook Pro: Apple M5 Max, 128 GB unified memory, Ollama 0.34.4 on a dedicated local server. Kody asked for five uncensored models from Hugging Face that fit this Mac, benchmarked and ranked. He chose one well-known uncensored build per base model, and asked for capability, speed, and a refusal measurement.

**RANKING -- TODO after the thinking-on pass and GPT-OSS debugging.**

## Models

Selected from Hugging Face search results for uncensored, abliterated, heretic, and obliterated builds runnable in MLX or llama.cpp, sorted by downloads and trending score on September 26, 2026. Exact revisions, byte sizes, and SHA-256 values are in [selection.json](selection.json); every imported blob matched.

| Base | Build | Quant | File size | How it was uncensored (per its model card) |
|---|---|---|---:|---|
| Qwen3.8-27B (dense) | [llmfan46 Heretic](https://huggingface.co/llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF) | Q8_0 | 30.5 GB | [Heretic](https://github.com/p-e-w/heretic) |
| Qwen3.6-35B-A3B (MoE) | [HauhauCS Aggressive](https://huggingface.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive) | Q4_K_M | 21.2 GB | Not disclosed |
| Gemma 4 31B (dense) | [llmfan46 Heretic](https://huggingface.co/llmfan46/gemma-4-31B-it-uncensored-heretic-GGUF) | Q8_0 | 32.6 GB | Heretic ARA |
| Qwen3-Coder-Next (MoE) | [huihui-ai abliterated, bartowski quants](https://huggingface.co/bartowski/huihui-ai_Qwen3-Coder-Next-abliterated-GGUF) | Q4_K_M | 48.6 GB | [remove-refusals-with-transformers](https://github.com/Sumandora/remove-refusals-with-transformers) |
| GPT-OSS 120B (MoE) | [HauhauCS Aggressive](https://huggingface.co/HauhauCS/GPTOSS-120B-Uncensored-HauhauCS-Aggressive) | MXFP4 | 65.4 GB | Not disclosed |

Quantization differs across rows, so this answers "which of these should I run," not "which uncensoring method preserves the most capability."

## Results: thinking off, 96 cases

The primary protocol, comparable to the repository's earlier rows. Thinking disabled on every model that supports it.

| Model | Workload /96 | First 24 | Gen tok/s | Ingest tok/s | Exact checks | Harmful flagged /100 | Harmless flagged /100 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemma 4 31B Heretic Q8_0 | 36 | 9 | 16.3 | 477 | 3/3 | 14 | 2 |
| Qwen3.8-27B Heretic Q8_0 | 35 | 8 | 17.9 | 639 | 3/3 | 5 | 1 |
| Qwen3-Coder-Next abliterated Q4_K_M | 14 | 4 | 94.6 | 2,402 | 2/3 | **37** | 2 |
| Qwen3.6-35B-A3B HauhauCS Q4_K_M | 13 | 4 | 128.5 | 3,254 | 3/3 | 5 | 1 |
| GPT-OSS 120B HauhauCS MXFP4 | -- | -- | -- | -- | -- | -- | -- |

GPT-OSS: **TODO.** Attempt 1 is invalid (empty responses from Ollama; details below).

Per-category results (12 cases each):

| Model | Ledger | Event state | Scheduling | SQL | Shortest path | Extraction | Python trace | Retrieval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma 4 31B Heretic | 0 | 2 | 2 | 0 | 8 | 12 | 0 | 12 |
| Qwen3.8-27B Heretic | 0 | 4 | 3 | 1 | 3 | 12 | 0 | 12 |
| Qwen3-Coder-Next abliterated | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 12 |
| Qwen3.6-35B-A3B HauhauCS | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 12 |

## Results: thinking on, first 24 cases

**TODO.** Qwen3.6-35B-A3B, Qwen3.8-27B, and Gemma 4 31B with thinking enabled, 8192-token cap, 600 s per case.

## Did uncensoring cost capability?

Stock baselines already in this repository, one sample per case:

| Model | Stock | Uncensored (this run) | Caveat |
|---|---|---|---|
| Qwen3.8-27B, thinking off | 33/96 ([Windows runs](../local-model-benchmarks/runs/20260911-102155-996f70fb.json), BF16) | 35/96 (Q8_0) | Different host, runtime, and quantization |
| Qwen3.8-27B, thinking on | 96/96 (Windows, BF16) | **TODO** (first 24) | Same caveats |
| Gemma 4 31B, thinking off | 10/24 first 24 ([this Mac, Sep 22](../mac-model-benchmarks/runs/20260922-gemma.json), Q8_0, Ollama 0.32.13) | 9/24 | Different Ollama version |

No capability loss is visible for the two Heretic builds on this suite. A one- or two-case difference with one sample per case is not a measured effect in either direction.

## Refusals

Heretic's own evaluation defaults ([config at 3521f86](https://github.com/p-e-w/heretic/blob/3521f8648a0dccf6e12a92666862632235fac7e6/config.default.toml)): 100 prompts from [`mlabonne/harmful_behaviors`](https://huggingface.co/datasets/mlabonne/harmful_behaviors) `test[:100]`, system prompt "You are a helpful assistant.", 100-token responses, and Heretic's case-insensitive keyword list. The same scorer on 100 [`mlabonne/harmless_alpaca`](https://huggingface.co/datasets/mlabonne/harmless_alpaca) prompts bounds false flags. **Only verdicts and matched keywords were saved; no response text was stored.**

The keyword scorer counts disclaimers and topic words ("illegal", "violat") as flags, so the numbers mean different things:

- Qwen3.8 and Qwen3.6 at 5/100: flags on `illegal`, `violat`, `disclaimer` -- mostly answers that mention legality or add a disclaimer.
- Gemma 4 at 14/100: includes explicit `i cannot`. Its model card reports 10/100 with Heretic's own run; this is the same order, not a reproduction.
- Qwen3-Coder-Next at **37/100**: led by `i can'` (16) and `i'm unable` (13). This abliteration leaves real refusals in place.

These numbers are not comparable to model-card claims that use other prompt sets or classifiers (for example HauhauCS's "0/465").

## Method

[bench.py](bench.py) reuses `local-model-benchmarks` helpers: `workload_suite.cases()`, `quality_screen.grade`, `nightly.Harness.measurement`, `nightly.exact_lines`, `api_probe.py`. Settings: temperature 0, seed 42, top_p 1, top_k 40, no repetition penalty, 8192 context, one sample per case.

- **Workload:** `practical-json-v1`, 96 authored cases in eight categories, strict JSON grading, 2048-token cap with thinking off. It is an answer-quality screen, not a coding benchmark or general ranking. Generated code is never executed.
- **Throughput:** warmup, then three repetitions of a short generation and a ~7,000-token ingest, plus three exact-output checks (same prompts as the Sep 22 Mac runs).
- **Runtime:** dedicated Ollama 0.34.4 on `127.0.0.1:11436` with its own model store; the primary server and personal library were not used. Models pulled with `ollama pull hf.co/<repo>:<quant>`.

Full log with timestamps, smoke tests, and every fix: [notes.md](notes.md). Raw records: [runs/](runs/). Summary data: [comparison.json](comparison.json).

## Problems found along the way

- **Gemma 4 thinks by default** through this import even though Ollama does not list a thinking capability. The runner always sends an explicit `think` value.
- **GPT-OSS stop parameters:** the imported model carried stop sequences including `<|channel|>`, which ends every harmony response at its first token. The repository has no Ollama `params` file, so the source is unidentified. The run overrides stops with `<|return|>` and `<|call|>`.
- **GPT-OSS attempt 1 invalid:** 94 of 96 workload responses had empty content and empty reasoning despite 38-89 generated tokens; two requests returned HTTP 500. Server logs show Ollama picking different template paths for the same model across loads. **TODO: diagnosis and outcome.**
- Two launch failures from argument parsing (zsh word splitting and a missing `--think` choice) delayed runs but produced no bad data; see notes.

## Caveats

- One sample per case at temperature 0. Small differences are not significant.
- The workload suite is small and authored. It tests structured reasoning and JSON discipline, not coding, writing, or knowledge.
- The refusal scorer is keyword-based and cannot separate a refusal from a disclaimer.
- Thinking-off results understate hybrid reasoning models: stock Qwen3.8-27B goes from 33/96 to 96/96 with thinking on.
- Interactive desktop host; results are for this Mac and these artifacts.
