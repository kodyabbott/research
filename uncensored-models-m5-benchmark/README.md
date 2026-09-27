# Uncensored local models on the M5 Max: capability, speed, refusals

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Claude Opus 5.5). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Measured September 27, 2026, on this MacBook Pro: Apple M5 Max, 128 GB unified memory, Ollama 0.34.4 on a dedicated local server. Kody asked for five uncensored models from Hugging Face that fit this Mac, benchmarked and ranked. He chose one well-known uncensored build per base model, and asked for capability, speed, and a refusal measurement.

## Ranking

Rule, fixed before the thinking-on results existed: strict pass rate on the first 24 workload cases in each model's best supported mode, generation speed as tiebreak. Refusal flags are shown beside the ranking, not folded into it.

| Rank | Model | Best mode | First 24 (strict) | Full 96 | Gen tok/s | Weights | Harmful flagged /100 |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Qwen3.8-27B Heretic Q8_0 | thinking on | **24/24** | 35/96 thinking off | 17.9 | 30.5 GB | 5 |
| 2 | GPT-OSS 120B HauhauCS MXFP4 | low reasoning | **23/24** | **91/96** | 84.8 | 65.4 GB | 22* |
| 3 | Qwen3.6-35B-A3B HauhauCS Q4_K_M | thinking on | 15/24 | 13/96 thinking off | 128.5 | 21.2 GB | 5 |
| 4 | Gemma 4 31B Heretic Q8_0 | **TODO** | **TODO** | 36/96 thinking off | 16.3 | 32.6 GB | 14 |
| 5 | Qwen3-Coder-Next abliterated Q4_K_M | thinking off (no toggle) | 4/24 | 14/96 | 94.6 | 48.6 GB | **37** |

\* GPT-OSS had a 1,024-token refusal budget (reasoning included) against 100 tokens for the others, and its flags are all topic words and disclaimers; see [Refusals](#refusals).

**The top two are a capability tie.** One case on 24, with one sample per case, is not a measured difference. GPT-OSS 120B was also measured on all 96 cases (91/96) and generates about 4.7 times faster. I recommend **GPT-OSS 120B** as the daily model on this Mac. Pick **Qwen3.8-27B Heretic** when you need image input or want to leave more memory free; it matched stock Qwen3.8-27B exactly.

GPT-OSS 120B only works after a fix: Ollama's import of this Hugging Face GGUF generated a malformed chat template that emptied every response. [make_gptoss_model.sh](make_gptoss_model.sh) rebuilds it from the same file with Ollama's official template. Details under [Problems found](#problems-found-along-the-way).

## Models

Selected from Hugging Face search results for uncensored, abliterated, heretic, and obliterated builds runnable in MLX or llama.cpp, sorted by downloads and trending score on September 26, 2026. Exact revisions, byte sizes, and SHA-256 values are in [selection.json](selection.json); every imported blob matched.

| Base | Build | Quant | How it was uncensored (per its model card) |
|---|---|---|---|
| Qwen3.8-27B (dense) | [llmfan46 Heretic](https://huggingface.co/llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF) | Q8_0 | [Heretic](https://github.com/p-e-w/heretic) |
| Qwen3.6-35B-A3B (MoE) | [HauhauCS Aggressive](https://huggingface.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive) | Q4_K_M | Abliteration, tool and method not disclosed (card: "abliterated weights") |
| Gemma 4 31B (dense) | [llmfan46 Heretic](https://huggingface.co/llmfan46/gemma-4-31B-it-uncensored-heretic-GGUF) | Q8_0 | Heretic ARA |
| Qwen3-Coder-Next (MoE) | [huihui-ai abliterated, bartowski quants](https://huggingface.co/bartowski/huihui-ai_Qwen3-Coder-Next-abliterated-GGUF) | Q4_K_M | [remove-refusals-with-transformers](https://github.com/Sumandora/remove-refusals-with-transformers), per the [upstream huihui-ai card](https://huggingface.co/huihui-ai/Huihui-Qwen3-Coder-Next-abliterated/blob/2b50acef370d315e904d9d3d2e26ac658ed49d57/README.md) (bartowski's quant card names only the original model) |
| GPT-OSS 120B (MoE) | [HauhauCS Aggressive](https://huggingface.co/HauhauCS/GPTOSS-120B-Uncensored-HauhauCS-Aggressive) | MXFP4 | Abliteration, tool and method not disclosed (card tag: `abliterated`) |

Quantization differs across rows, so this answers "which of these should I run," not "which uncensoring method preserves the most capability."

## Results: 96 cases, primary protocol

Thinking off wherever the model supports it; GPT-OSS cannot disable reasoning and runs at low effort (as the Sep 22 GPT-OSS 20B row did). "Fences stripped" is a diagnostic regrade that removes a surrounding ```json fence before the same strict grader; the prompts say "No markdown," so the strict column is the result.

| Model | Mode | Strict /96 | Fences stripped | First 24 | Gen tok/s | Ingest tok/s | Exact checks | Harmful flagged | Harmless flagged |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-OSS 120B | low reasoning | **91** | 91 | 23 | 84.8 | 1,882 | 3/3 | 22* | 1 |
| Gemma 4 31B Heretic | off | 36 | 38 | 9 | 16.3 | 477 | 3/3 | 14 | 2 |
| Qwen3.8-27B Heretic | off | 35 | 35 | 8 | 17.9 | 639 | 3/3 | 5 | 1 |
| Qwen3-Coder-Next abliterated | off | 14 | 15 | 4 | 94.6 | 2,402 | 2/3 | **37** | 2 |
| Qwen3.6-35B-A3B HauhauCS | off | 13 | 13 | 4 | 128.5 | 3,254 | 3/3 | 5 | 1 |

Per category (12 cases each):

| Model | Ledger | Event state | Scheduling | SQL | Shortest path | Extraction | Python trace | Retrieval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-OSS 120B (low reasoning) | 12 | 11 | 12 | 9 | 11 | 12 | 12 | 12 |
| Gemma 4 31B Heretic | 0 | 2 | 2 | 0 | 8 | 12 | 0 | 12 |
| Qwen3.8-27B Heretic | 0 | 4 | 3 | 1 | 3 | 12 | 0 | 12 |
| Qwen3-Coder-Next abliterated | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 12 |
| Qwen3.6-35B-A3B HauhauCS | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 12 |

With thinking off, most of these cases require step-by-step computation the models cannot show, which is why GPT-OSS (always reasoning) leads by a wide margin here.

## Results: thinking on, first 24 cases

8,192-token cap and context, 600 s per case, for the three models with a thinking mode.

| Model | Strict /24 | Fences stripped | Truncated | Median generated tokens | Wall time |
|---|---:|---:|---:|---:|---:|
| Qwen3.8-27B Heretic | **24** | 24 | 0 | 865 | 20 min |
| Qwen3.6-35B-A3B HauhauCS | 15 | 15 | 8 | 5,274 | 16 min |
| Gemma 4 31B Heretic | **TODO** | **TODO** | **TODO** | **TODO** | **TODO** |

- Qwen3.8 solves every case with short reasoning.
- Qwen3.6's reasoning runs long: 8 of its 9 failures filled the 8,192-token context before answering. Its model card says to "Keep at least 128K context to preserve thinking capabilities," so 15/24 is a lower bound for this model with more context.
- Gemma's thinking mode cannot be requested through Ollama's `think` flag for this import (HTTP 400); it thinks when the flag is omitted. Its answers so far are correct but wrapped in markdown fences, which the strict grader rejects. **TODO: final numbers.**

## Did uncensoring cost capability?

Stock baselines already in this repository, one sample per case:

| Model | Stock | Uncensored (this run) | Caveat |
|---|---|---|---|
| Qwen3.8-27B, thinking off | 33/96 ([Windows](../local-model-benchmarks/runs/20260911-102155-996f70fb.json), BF16) | 35/96 (Q8_0) | Different host, runtime, and quantization |
| Qwen3.8-27B, thinking on | 24/24 first 24 ([Windows](../local-model-benchmarks/runs/20260911-104941-c75692e6.json), BF16) | 24/24 | Same caveats |
| Gemma 4 31B, thinking off | 10/24 first 24 ([this Mac, Sep 22](../mac-model-benchmarks/runs/20260922-gemma.json), Q8_0, Ollama 0.32.13) | 9/24 | Different Ollama version |

No capability loss is visible for either Heretic build on this suite. A one- or two-case difference with one sample per case is not a measured effect in either direction. There are no stock baselines for the other three bases on this suite.

## Refusals

Heretic's own evaluation defaults ([config at 3521f86](https://github.com/p-e-w/heretic/blob/3521f8648a0dccf6e12a92666862632235fac7e6/config.default.toml)): 100 prompts from [`mlabonne/harmful_behaviors`](https://huggingface.co/datasets/mlabonne/harmful_behaviors) `test[:100]`, system prompt "You are a helpful assistant.", 100-token responses, and Heretic's case-insensitive keyword list. The same scorer on 100 [`mlabonne/harmless_alpaca`](https://huggingface.co/datasets/mlabonne/harmless_alpaca) prompts bounds false flags. **Only verdicts and matched keywords were saved; no response text was stored.**

The keyword scorer counts disclaimers and topic words ("illegal", "violat") as flags, so the counts mean different things:

| Model | Harmful flagged | What matched | Reading |
|---|---:|---|---|
| Qwen3-Coder-Next abliterated | **37** | `i can'` 16, `i'm unable` 13, `sorry` 8, `illegal` 10 | Real refusals remain. This abliteration is incomplete. |
| GPT-OSS 120B | 22* | `disclaimer` 12, `illegal` 9, `violat` 3 | No refusal phrases. 1,024-token budget, so not comparable. |
| Gemma 4 31B Heretic | 14 | includes `i cannot`, `i am an ai` | Some refusals. Its card reports 10/100 with Heretic's own run: same order, not a reproduction. |
| Qwen3.8-27B Heretic | 5 | `illegal`, `violat` | Topic words, plus 1 empty response |
| Qwen3.6-35B-A3B HauhauCS | 5 | `disclaimer`, `illegal` | Disclaimers; its card: "May occasionally append short disclaimers" |

Harmless prompts: 1-2 flags per model. These numbers are not comparable to model-card claims that use other prompt sets or classifiers (for example HauhauCS's "0/465").

## Method

[bench.py](bench.py) reuses `local-model-benchmarks` helpers: `workload_suite.cases()`, `quality_screen.grade`, `nightly.Harness.measurement`, `nightly.exact_lines`, `api_probe.py`. Settings: temperature 0, seed 42, top_p 1, top_k 40, no repetition penalty, 8,192 context, one sample per case.

- **Workload:** `practical-json-v1`, 96 authored cases in eight categories, strict JSON grading. Output cap 2,048 tokens with thinking off, 8,192 when reasoning is on (as in the Sep 22 GPT-OSS rows). It is an answer-quality screen, not a coding benchmark or general ranking. Generated code is never executed.
- **Throughput:** warmup, then three repetitions of a short generation and a ~7,000-token ingest, plus three exact-output checks (same prompts as the Sep 22 Mac runs).
- **Runtime:** dedicated Ollama 0.34.4 on `127.0.0.1:11436` with its own model store; the primary server and personal library were not used. Models pulled with `ollama pull hf.co/<repo>:<quant>`; GPT-OSS rebuilt as described below.
- **Scripts:** [run_all.sh](run_all.sh) (primary protocol), [run_thinking.sh](run_thinking.sh) (thinking-on pass), [summarize.py](summarize.py) (tables and [comparison.json](comparison.json)).

Full log with timestamps, smoke tests, and every fix: [notes.md](notes.md). Raw records: [runs/](runs/).

## Problems found along the way

- **GPT-OSS: malformed template from Ollama's import.** `ollama show --modelfile` for the `hf.co` import showed a derived template with a truncated user header (`tart|>user<|message|>`), the assistant turn prefilled into the `final` channel, reasoning hard-coded to medium, and stop sequences including `<|channel|>`. Responses came back empty (attempt 1: 1/96, kept as [an invalid record](runs/20260927-gpt-oss-120b-hauhaucs-INVALID-attempt1.json)). The repository publishes no template or params file. A raw harmony prompt proved the weights answer correctly. Rebuilding from the same blob with Ollama's official gpt-oss template (from the stock `gpt-oss:20b` artifact) fixed it; two rebuilds produced the same model digest.
- **Gemma 4: thinking control.** This import does not advertise a thinking capability, thinks by default, accepts `think: false`, and rejects `think: true`. Thinking-off runs send `false`; the thinking-on run omits the field.
- **Qwen3.6: context-bound thinking.** See above.
- **Harness mistakes (mine), no bad data:** two argument-parsing bugs (zsh word splitting and a missing `--think` choice) and one self-matching `pgrep` wait loop delayed runs. Each failed before inference and is logged in the notes.

## Caveats

- One sample per case at temperature 0. Differences of a few cases are not significant.
- The workload suite is small and authored. It tests structured reasoning and JSON discipline, not coding, writing, or knowledge.
- The refusal scorer is keyword-based and cannot separate a refusal from a disclaimer.
- Thinking-on results cover 24 cases, not 96.
- Interactive desktop host; results apply to this Mac and these exact artifacts.
