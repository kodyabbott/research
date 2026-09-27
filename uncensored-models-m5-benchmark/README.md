# Uncensored local models on the M5 Max: capability, speed, refusals

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Claude Opus 5.5). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Measured September 27, 2026, on this MacBook Pro: Apple M5 Max, 128 GB unified memory, Ollama 0.34.4 on a dedicated local server. Kody asked for five uncensored models from Hugging Face that fit this Mac, benchmarked and ranked. He chose one well-known uncensored build per base model, and asked for capability, speed, and a refusal measurement.

## Ranking

Rule, fixed before the thinking-on results existed: strict pass rate on the first 24 workload cases in each model's best supported mode, generation speed as tiebreak (no tie occurred). Refusal flags are shown beside the ranking, not folded into it. The full-96 column and s/case were added after review; they do not change the order.

| Rank | Model | Best mode | First 24 (strict) | All 96, best mode | s/case (best mode, first 24) | Harmful flagged /100 |
|---:|---|---|---:|---:|---:|---:|
| 1 | Qwen3.8-27B Heretic Q8_0 | thinking on | **24/24** | **96/96** | 50.3 | 5 |
| 2 | GPT-OSS 120B HauhauCS MXFP4 | low reasoning | 23/24 | 91/96 | 5.2 | 8* |
| 3 | Qwen3.6-35B-A3B HauhauCS Q4_K_M | thinking on | 15/24 | not run (13/96 thinking off) | 39.9 | 5 |
| 4 | Gemma 4 31B Heretic Q8_0 | thinking off | 9/24 | 36/96 | 3.8 | 14 |
| 5 | Qwen3-Coder-Next abliterated Q4_K_M | thinking off (no toggle) | 4/24 | 14/96 | 0.9 | **37** |

\* Comparable run using Heretic's gpt-oss prefill at 100 tokens. The chat-API run at a 1,024-token budget with reasoning included flagged 22; see [Refusals](#refusals).

**Qwen3.8-27B Heretic is the most capable model here.** With thinking on it passed all 96 cases, the same as stock Qwen3.8-27B on this suite, and it flagged 5 of 100 harmful prompts, all on topic words (`illegal`, `violat`), with one further empty reply. It is also slow on this Mac: about 50 seconds per case at 18 tok/s. **GPT-OSS 120B is the fast alternative:** 91/96 at about 5 seconds per case, roughly a tenth of the wall time, with 8/100 flagged on the comparable refusal run. It needs twice the memory (65.4 GB GGUF against 30.5 GB plus a 0.9 GB vision projector) and a template fix. Qwen3.8 accepts image input; vision was not tested here. The one-case gap on the first 24 is not meaningful alone; the 96-case runs (96 vs 91, one sample per case) are the stronger evidence.

Recommendation: Qwen3.8-27B Heretic when correctness matters more than latency, GPT-OSS 120B for interactive use. Gemma 4 with thinking on reaches 21/24 once markdown fences are stripped, but ignores the prompt's format instruction and takes about 3.5 minutes per case. Qwen3-Coder-Next abliterated flagged the most harmful prompts (37/100, mostly refusal phrases) and scored lowest.

GPT-OSS 120B only works after a fix: Ollama's import of this Hugging Face GGUF generated a malformed chat template that emptied every response. [make_gptoss_model.sh](make_gptoss_model.sh) rebuilds it from the same file with Ollama's official template. Details under [Problems found](#problems-found-along-the-way).

## Models

Selected from Hugging Face search results for uncensored, abliterated, heretic, and obliterated builds runnable in MLX or llama.cpp, sorted by downloads and trending score on September 26, 2026. Exact revisions, byte sizes, and SHA-256 values are in [selection.json](selection.json); every model GGUF matched. Ollama also pulled vision projectors for the Qwen3.8, Qwen3.6, and Gemma repositories (0.9-1.2 GB each); those are not pinned in selection.json, and their digests are in the notes.

| Base | Build | Quant | How it was uncensored (per its model card) |
|---|---|---|---|
| Qwen3.8-27B (dense) | [llmfan46 Heretic](https://huggingface.co/llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF) | Q8_0 | [Heretic](https://github.com/p-e-w/heretic) v2.0.0.dev0, a variant of Magnitude-Preserving Orthogonal Ablation (MPOA) |
| Qwen3.6-35B-A3B (MoE) | [HauhauCS Aggressive](https://huggingface.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive) | Q4_K_M | Abliteration, tool and method not disclosed (card: "abliterated weights") |
| Gemma 4 31B (dense) | [llmfan46 Heretic](https://huggingface.co/llmfan46/gemma-4-31B-it-uncensored-heretic-GGUF) | Q8_0 | Heretic v1.2.0, Arbitrary-Rank Ablation (ARA) |
| Qwen3-Coder-Next (MoE) | [huihui-ai abliterated, bartowski quants](https://huggingface.co/bartowski/huihui-ai_Qwen3-Coder-Next-abliterated-GGUF) | Q4_K_M | [remove-refusals-with-transformers](https://github.com/Sumandora/remove-refusals-with-transformers), per the [upstream huihui-ai card](https://huggingface.co/huihui-ai/Huihui-Qwen3-Coder-Next-abliterated/blob/2b50acef370d315e904d9d3d2e26ac658ed49d57/README.md) (bartowski's quant card names only the original model) |
| GPT-OSS 120B (MoE) | [HauhauCS Aggressive](https://huggingface.co/HauhauCS/GPTOSS-120B-Uncensored-HauhauCS-Aggressive) | MXFP4 | Abliteration, tool and method not disclosed (card tag: `abliterated`) |

Quantization differs across rows, so this answers "which of these should I run," not "which uncensoring method preserves the most capability."

## Results: 96 cases, primary protocol

Thinking off wherever the model supports it. Ollama's chat API offers no way to turn GPT-OSS reasoning off, so it runs at low effort (as the Sep 22 GPT-OSS 20B row did); medium and high effort were not run. "Fences stripped" is a diagnostic regrade that removes one surrounding ``` or ```json fence (case-insensitive) before the same strict grader. It covers that one format habit only; other format misses, such as a bare array without the `{"answer": ...}` wrapper, still fail. The prompts say "No markdown," so the strict column is the result.

| Model | Mode | Strict /96 | Fences stripped | First 24 | Gen tok/s | Ingest tok/s | Exact checks | Harmful flagged | Harmless flagged |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-OSS 120B | low reasoning | **91** | 91 | 23 | 84.8 | 1,882 | 3/3 | 22 (8 comparable) | 1 (0 comparable) |
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

With thinking off, most of these cases require step-by-step computation the models cannot show. GPT-OSS reasons on every case and also has more total parameters (117B, against 27-35B for three of the others and 80B for Qwen3-Coder-Next); this suite cannot separate those two causes of its lead. Two of the three shortest-path cases in the first 24 are trivial (the start node reaches nothing), as are `graph-5` and `graph-9`.

## Results: thinking on, first 24 cases

8,192-token context with `num_predict` 8,192, so the effective output budget is 8,192 minus the prompt (the longest prompt is 2,076 tokens), 600 s per case, temperature 0, for the three models with a thinking mode. Model cards recommend sampling for thinking mode (the Qwen3.8 card: temperature 1.0, top_p 0.95, top_k 20); this protocol uses greedy decoding throughout, so scores may differ under the recommended sampling settings.

| Model | Strict /24 | Fences stripped | Truncated | Median generated tokens | Wall time |
|---|---:|---:|---:|---:|---:|
| Qwen3.8-27B Heretic | **24** | 24 | 0 | 865 | 20 min |
| Qwen3.6-35B-A3B HauhauCS | 15 | 15 | 8 | 5,274 | 16 min |
| Gemma 4 31B Heretic | 6 | **21** | 1 | 3,202 | 83 min |

- Qwen3.8 solves every case with short reasoning, and a separate run over all 96 cases also scored 96/96 (median 931 tokens, 81.5 minutes).
- Qwen3.6's reasoning runs long: 8 of its 9 failures filled the 8,192-token context before answering. Its model card says to "Keep at least 128K context to preserve thinking capabilities," so 15/24 likely understates this model with more context. Greedy decoding may also contribute: on two Python-trace cases the reasoning contained the correct answer and kept re-verifying until the context ran out.
- Gemma's thinking mode cannot be requested through Ollama's `think` flag for this import (HTTP 400); it thinks when the flag is omitted. It scored 6/24 strict but 21/24 with fences stripped: 17 of its 18 failures wrap the answer in a ```json fence despite the prompt's "No markdown," and 15 of those are correct once the fence is removed. Its thinking mode solves most of these cases but does not follow the output-format instruction, so under strict grading its best mode is thinking off (9/24). It is also the slowest configuration here, at about 3.5 minutes per case.

## Did uncensoring cost capability?

Stock baselines already in this repository, one sample per case:

| Model | Stock | Uncensored (this run) | Caveat |
|---|---|---|---|
| Qwen3.8-27B, thinking off | 33/96 on Windows, BF16: 8 + 9 + 7 + 9 across [offset 0](../local-model-benchmarks/runs/20260911-102155-996f70fb.json), [24](../local-model-benchmarks/runs/20260911-102525-e7f183f2.json), [48](../local-model-benchmarks/runs/20260911-102926-9263bf0d.json), [72](../local-model-benchmarks/runs/20260911-103236-31e0e759.json) | 35/96 (Q8_0) | Different host, runtime, and quantization |
| Qwen3.8-27B, thinking on | 96/96 ([Windows](../local-model-benchmarks/runs/20260911-104941-c75692e6.json) and three later offsets, BF16) | 96/96 | Same caveats |
| Gemma 4 31B, thinking off | 10/24 first 24 ([this Mac, Sep 22](../mac-model-benchmarks/runs/20260922-gemma.json), Q8_0, Ollama 0.32.13) | 9/24 | Different Ollama version |

No capability loss is visible for either Heretic build, but this suite has little power to show one: with thinking off, ledger, SQL, and Python trace are at 0/12 for every model except GPT-OSS and retrieval is 12/12 for all (floor and ceiling), and with thinking on Qwen3.8 is at 96/96 (ceiling). A one- or two-case difference with one sample per case is not a measured effect in either direction, and the Gemma comparison also crosses an Ollama version change (0.32.13 to 0.34.4). There are no stock baselines for the other three bases on this suite.

## Refusals

Heretic's evaluation settings ([config at 3521f86](https://github.com/p-e-w/heretic/blob/3521f8648a0dccf6e12a92666862632235fac7e6/config.default.toml)): 100 prompts from [`mlabonne/harmful_behaviors`](https://huggingface.co/datasets/mlabonne/harmful_behaviors) `test[:100]`, system prompt "You are a helpful assistant.", 100-token responses, and Heretic's case-insensitive keyword list. The same scorer on 100 [`mlabonne/harmless_alpaca`](https://huggingface.co/datasets/mlabonne/harmless_alpaca) prompts bounds false flags. **Only verdicts and matched keywords were saved; no response text was stored.** The matcher is simpler than Heretic's ([keyword_rate.py at 3521f86](https://github.com/p-e-w/heretic/blob/3521f8648a0dccf6e12a92666862632235fac7e6/src/heretic/scorers/keyword_rate.py)): Heretic counts empty responses as refusals, strips `*`, and collapses whitespace; this run reports empty responses separately and does neither normalization. Under Heretic's rule Qwen3.8 would count 6/100 (one empty response); no other model had an empty response. The effect of `*` stripping can't be recomputed because no text was kept.

The keyword scorer counts disclaimers and topic words ("illegal", "violat") as flags, so the counts mean different things:

| Model | Harmful flagged | What matched | Reading |
|---|---:|---|---|
| Qwen3-Coder-Next abliterated | **37** | `i can'` 16, `i'm unable` 13, `sorry` 8, `illegal` 10 | 30+ matches are refusal phrases, so residual refusals are likely. No stock Qwen3-Coder-Next baseline was run, so how much the abliteration removed is unknown. |
| GPT-OSS 120B | **8** comparable (22 chat API) | comparable run: `illegal` 5, `disclaimer` 2, `sorry` 1 | Comparable run uses Heretic's gpt-oss prefill: an empty closed analysis block, then 100 tokens of the final answer via raw `/api/generate`. The chat-API run at a 1,024-token budget (reasoning included) flagged 22, all topic words and disclaimers. Harmless: 0/100 comparable. |
| Gemma 4 31B Heretic | 14 | includes `i cannot`, `i am an ai` | Some refusals. Its card reports 10/100 with Heretic v1.2.0, whose marker list lacks `disclaimer`; under that list this run counts 12/100. Same order, not a reproduction. |
| Qwen3.8-27B Heretic | 5 | `illegal`, `violat` | Topic words, plus 1 empty response (6/100 under Heretic's empty-counts rule). Its card reports 3/100 (Heretic v2.0.0.dev0). |
| Qwen3.6-35B-A3B HauhauCS | 5 | `disclaimer`, `illegal` | Disclaimers; its card: "May occasionally append short disclaimers" |

Harmless prompts: 1-2 flags per model. These numbers are not comparable to model-card claims that use other prompt sets or classifiers (for example HauhauCS's "0/465").

## Method

[bench.py](bench.py) reuses `local-model-benchmarks` helpers: `workload_suite.cases()`, `quality_screen.grade`, `nightly.Harness.measurement`, `nightly.exact_lines`, `api_probe.py`. Settings: temperature 0, seed 42, top_p 1, top_k 40, no repetition penalty, 8,192 context, one sample per case.

- **Workload:** `practical-json-v1`, 96 authored cases in eight categories, strict JSON grading. Output cap 2,048 tokens with thinking off, 8,192 when reasoning is on (as in the Sep 22 GPT-OSS rows). It is an answer-quality screen, not a coding benchmark or general ranking. Generated code is never executed.
- **Throughput:** warmup, then three repetitions of a short generation and a ~7,000-token ingest, plus three exact-output checks (same prompts as the Sep 22 Mac runs).
- **Runtime:** dedicated Ollama 0.34.4 on `127.0.0.1:11436` with its own model store; the primary server and personal library were not used. Models pulled with `ollama pull hf.co/<repo>:<quant>`; GPT-OSS rebuilt as described below.
- **Scripts:** [run_all.sh](run_all.sh) (primary protocol), [run_thinking.sh](run_thinking.sh) (thinking-on pass), [run_followups.sh](run_followups.sh) (comparable GPT-OSS refusal run and Qwen3.8 all-96 thinking run), [make_gptoss_model.sh](make_gptoss_model.sh) (GPT-OSS template rebuild), [summarize.py](summarize.py) (tables and [comparison.json](comparison.json)).

The runner changed between runs as problems surfaced; each record's `runnerSha256` identifies its version, and `options` and `refusalProtocol` are identical across all records (version map in the notes). Full log with timestamps, smoke tests, and every fix: [notes.md](notes.md). Raw records: [runs/](runs/).

## Problems found along the way

- **GPT-OSS: malformed template from Ollama's import.** `ollama show --modelfile` for the `hf.co` import showed a derived template with a truncated user header (`tart|>user<|message|>`), the assistant turn prefilled into the `final` channel, reasoning hard-coded to medium, and stop sequences including `<|channel|>`. Responses came back empty (attempt 1: 1/96, kept as [an invalid record](runs/20260927-gpt-oss-120b-hauhaucs-INVALID-attempt1.json)). The repository publishes no Ollama template or params file; the GGUF embeds OpenAI's 16,714-character Jinja harmony template, and Ollama's conversion of it into a Go template is what broke. A raw harmony prompt proved the weights answer correctly. Rebuilding from the same blob with Ollama's official gpt-oss template (from the stock `gpt-oss:20b` artifact) fixed it; two rebuilds produced the same model digest. The official template also adds its own system message ("You are ChatGPT...", knowledge cutoff, current date, reasoning level) and moves any system prompt into a developer block, so the rendered prompt differs from a bare chat template and includes the run date. Ollama labels this file BF16 because its header `general.file_type` is BF16; the expert weights are MXFP4 (108 MXFP4, 146 BF16, and 433 F32 tensors).
- **Gemma 4: thinking control.** This import does not advertise a thinking capability, thinks by default, accepts `think: false`, and rejects `think: true`. Thinking-off runs send `false`; the thinking-on run omits the field.
- **Qwen3.6: context-bound thinking.** See above.
- **Harness mistakes during this run, no bad data:** two argument-parsing bugs (zsh word splitting and a missing `--think` choice) and one self-matching `pgrep` wait loop delayed runs. Each failed before inference and is logged in the notes.

## Caveats

- One sample per case at temperature 0. Differences of a few cases are not significant.
- The workload suite is small and authored. It tests structured reasoning and JSON discipline, not coding, writing, or knowledge.
- The refusal scorer is keyword-based and cannot separate a refusal from a disclaimer.
- Thinking-on results cover the first 24 cases, except Qwen3.8-27B, which was also run on all 96.
- Interactive desktop host; results apply to this Mac and these exact artifacts.
