# Local AI model guide for the M5 Max, 128 GB

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Kody directed the work; Codex (OpenAI) researched the sources and prepared the recommendations.
<!-- /AI-ASSISTED-NOTE -->

Researched September 22, 2026. Target: this MacBook Pro, Apple M5 Max, 40-core GPU and 128 GB unified memory. Hardware and existing measurements come from the [completed Mac benchmark report](../mac-model-benchmarks/README.md).

**My first choice is Qwen3.8-27B at 8-bit for demanding everyday work, paired with Qwen3.6-35B-A3B at 4-bit for faster interaction. Add Qwen3-Coder-Next for a coding-specific comparison.** These are recommendations from published evidence and available Mac conversions, not winners established by tests on this host. The choice balances capability, headroom, deployment support and likely responsiveness.

## Recommended models by category

Weight sizes below are actual summed `.safetensors` file sizes from the public Hugging Face API on the research date, in decimal GB. They exclude KV cache, activations, temporary buffers, macOS, other apps and some ancillary files. They are **not measured peak RAM**. The [artifact table](ARTIFACTS.md) lists GiB as well. Exact revisions, file sizes and unsuccessful lookups are saved in [artifact metadata](artifact-metadata.json).

| Category | First model to evaluate | Mac configuration and weight size | Why this choice / limits |
|---|---|---|---|
| General assistant, professional work, technical research | **Qwen3.8-27B** | MLX 8-bit: **29.5 GB**; 4-bit comparison: **16.1 GB** | Broad text and visual capability with ample memory headroom. My strongest practical default; [official model](https://huggingface.co/Qwen/Qwen3.8-27B), [8-bit conversion](https://huggingface.co/mlx-community/Qwen3.8-27B-8bit). |
| Coding agents and repository changes | **Qwen3-Coder-Next** alongside Qwen3.8 | LM Studio MLX 4-bit: **44.8 GB** | 80B total / 3B active, specifically trained for coding agents. Prefer it as the speed-oriented coding challenger; don't infer coding quality from our old JSON screen. [Model](https://huggingface.co/Qwen/Qwen3-Coder-Next), [conversion](https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-4bit). |
| Math, science and quantitative problem solving | **Qwen3.8-27B**, with **GPT-OSS 120B** as a second reasoning model | Qwen as above; GPT-OSS MXFP4-Q8: **63.4 GB** | Qwen is the first practical choice. GPT-OSS provides a larger, different reasoning architecture for comparison and configurable effort. The 120B model has not been tested here. [GPT-OSS card](https://huggingface.co/openai/gpt-oss-120b), [conversion](https://huggingface.co/mlx-community/gpt-oss-120b-MXFP4-Q8). |
| Formal mathematics and verified proofs | **Leanstral 1.5 119B-A6B** | Community MLX 4-bit: **68.6 GB** | Purpose-built Lean 4 agent. Judge it by proofs accepted by Lean, not persuasive explanations. Runtime/harness integration still needs validation. [Model](https://huggingface.co/mistralai/Leanstral-1.5-119B-A6B), [conversion](https://huggingface.co/mvid/Leanstral-1.5-119B-A6B-MLX-4bit). |
| Writing, editing and long-document synthesis | **Mistral Small 4**, compared with Qwen3.8 | MLX 4-bit: **67.8 GB** | Worth a blind comparison as another model family for drafting and editing. This is a preference-sensitive recommendation, not a verified creative-writing champion. [Release](https://mistral.ai/news/mistral-small-4/), [conversion](https://huggingface.co/mlx-community/Mistral-Small-4-119B-2603-4bit). |
| Images, charts, screenshots, scanned documents | **Qwen3.8-27B**; **Gemma 4 31B** as an alternative | Qwen MLX-VLM 8-bit; use a vision-enabled runtime | Qwen supports image/video understanding. Gemma supplies another multimodal model family; our Gemma Q8 text test is not a vision evaluation. [Qwen MLX-VLM artifact](https://huggingface.co/mlx-community/Qwen3.8-27B-8bit), [Gemma card](https://huggingface.co/google/gemma-4-31B). |
| Fast general chat and tool use | **Qwen3.6-35B-A3B** | MLX 4-bit **20.4 GB** or 8-bit **37.7 GB** | Sparse 3B-active architecture makes it a sensible speed candidate; its M5 Max tok/s remains unmeasured. [Model](https://huggingface.co/Qwen/Qwen3.6-35B-A3B), [4-bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit). |
| Translation | **TranslateGemma 27B** | MLX 8-bit **28.7 GB** | A dedicated translation candidate; validate your language pair, terminology and formatting. Uses the Gemma license and its translation-specific template. [Model](https://huggingface.co/google/translategemma-27b-it), [conversion](https://huggingface.co/mlx-community/translategemma-27b-it-8bit). |
| Searching a local research/document library | **Qwen3-Embedding**, plus a Qwen3 reranker | Practical MLX entry: 4B 4-bit **2.3 GB**; quality candidate: official 8B GGUF | Retrieve passages before asking the assistant to synthesize with citations. For scanned pages, evaluate the newer Qwen3-VL embedding/reranker family supported by MLX-Embeddings. Reranking requires its scoring interface, not ordinary chat. No corpus-specific retrieval winner established. [Embedding family](https://github.com/QwenLM/Qwen3-Embedding), [MLX implementation](https://github.com/Blaizzy/mlx-embeddings), [8B GGUF](https://huggingface.co/Qwen/Qwen3-Embedding-8B-GGUF). |

For legal, medical, finance, history, education and cybersecurity **research**, I would start with the general/vision model and a source-grounded retrieval pipeline, then evaluate on the user's actual materials. This survey does not establish a separate domain-specific winner for each profession. A broad exam score cannot establish reliable professional judgment.

The independent [Artificial Analysis Qwen3.8 evaluation](https://artificialanalysis.ai/models/qwen3-8-27b) places its xhigh configuration first in the page's small open-weight comparison class, while also flagging high verbosity. Its current index is version 4.3.2; older launch scores should not be mixed with the current index. Those measurements concern the evaluated service/configuration, not this Mac's quantized model. The Qwen vendor reports 89.2 GPQA Diamond and 61.7 SWE-bench Pro, with its own stated evaluation setup; these are useful selection signals, not local reproduction results.

## Speech and creative media

| Category | Recommended shortlist | Mac route / qualification |
|---|---|---|
| Meeting transcription and dictation | **Parakeet TDT 0.6B v3** for a lightweight baseline; **Qwen3-ASR 1.7B** for a multilingual comparison | MLX-Audio supports both. Verified weight sizes: Parakeet **2.5 GB**, Qwen bf16 **4.1 GB**. Measure word error rate and audio-seconds processed per second. [NVIDIA model](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), [Qwen report](https://arxiv.org/abs/2601.21337), [runtime](https://github.com/Blaizzy/mlx-audio). |
| Speech generation | **Qwen3-TTS 1.7B** as the practical default; **Higgs TTS 3 4B** for expressive speech | Qwen CustomVoice 8-bit artifact is **3.1 GB**; verified Higgs upstream tensors are **9.3 GB**, not a measured MLX runtime footprint. MLX-Audio lists both. Higgs has research/non-commercial terms plus a creator-use grant; Qwen is Apache-2.0. [Qwen runtime guide](https://github.com/Blaizzy/mlx-audio/blob/main/docs/models/tts/qwen3-tts.md), [Higgs card](https://huggingface.co/bosonai/higgs-tts-3-4b). |
| Photographic and artistic image generation | **Krea 2 Turbo** | MFLUX has a native MLX implementation. My creative-exploration candidate, under Krea's community license. Total pipeline memory and seconds/image still need measurement. [Model](https://huggingface.co/krea/Krea-2-Turbo), [Mac implementation](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/krea2/README.md). |
| Posters, design and readable text in images | **Ideogram 4** | Native MFLUX support, structured JSON captions, gated/non-commercial weights. MFLUX can use local JSON captions without the hosted prompt-expansion service. [Model](https://huggingface.co/ideogram-ai/ideogram-4-fp8), [Mac implementation](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/ideogram4/README.md). |
| Fast image creation and editing | **FLUX.2 klein 4B**; compare **9B** for quality | Native MFLUX route. 4B is Apache-2.0; 9B has a non-commercial license. Useful smaller pipelines to benchmark before the largest image models. [Official implementation/license table](https://github.com/black-forest-labs/flux2), [Mac implementation](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/flux2/README.md). |
| Video generation | **LTX-2.3**, experimental Mac evaluation | Open weights and community MLX ports exist. Treat as a separate project: resolution, duration, audio, quantization and port maturity determine feasibility. No host speed or complete pipeline memory verified. [Upstream](https://huggingface.co/Lightricks/LTX-2.3), [community Mac port](https://github.com/sw30labs/ltx-2.3-mlx). |

These media choices are candidates matched to documented capabilities and Mac implementations; this research did not run comparative listening or image-preference trials. Audio and image/video generation should not be ranked using LLM text tok/s.

## Large models: experiments, not first installs

| Candidate | Verified weight files | Assessment for this 128 GB Mac |
|---|---:|---|
| Step 3.7 Flash oQ3e | **84.9 GB** | Interesting larger multimodal agent candidate. Aggressive quantization and loaded-memory behavior need testing. Its 4-bit conversion is **110.8 GB**. [Base model](https://huggingface.co/stepfun-ai/Step-3.7-Flash-FP8), [conversion](https://huggingface.co/mlx-community/Step-3.7-Flash-oQ3e). |
| Inkling-Small 2-bit | **88.4 GB** | Strong published coding evidence, but low-bit quality retention and Mac integration are unverified. The 3-bit conversion is **120.9 GB**, leaving little practical headroom. [Release/evaluation](https://thinkingmachines.ai/news/inkling-small/), [2-bit conversion](https://huggingface.co/mlx-community/Inkling-Small-mlx-2bit). |
| DeepSeek V4 Flash 0731, mixed 2.4-bit | **92.8 GB** | A high-capability experiment with a substantial compression tradeoff. The publisher requires **oMLX 0.5.7+**, rather than stock MLX-LM, and reports tests on an M5 Max 128 GB / 40 GPU configuration. [Conversion and measurements](https://huggingface.co/mlx-community/DeepSeek-V4-Flash-0731-2.4bit-mixed). |
| Qwen3.8 Flash-Next 4-bit | **111.5 GB** | Too close to capacity for my first daily-use recommendation. Official architecture has 125B backbone parameters plus 51B n-gram embeddings and 4B MTP; “125B” alone understates storage. [Model](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [conversion](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-4bit). |

For the DeepSeek mixed-2.4-bit artifact, its publisher reports **36.1 generation tok/s at 1K context** and **31.5 tok/s at 32K**, but approximately **97 seconds to first token at 32K**, using 128 output tokens and no speculative decoding. These are external measurements on matching hardware, not our reproduction, and do not establish quantized quality parity. [Publisher benchmark](https://huggingface.co/mlx-community/DeepSeek-V4-Flash-0731-2.4bit-mixed).

These are disk-weight figures, not proof of full GPU residency. **MoE active parameter count primarily describes per-token work; all retained weights still need storage or explicit offloading.** My planning preference is roughly 20–70 GB of model weights for routine use, leaving room for context and applications. This is a conservative operating target, not an Apple-enforced memory limit.

DeepSeek V4.1 Flash is a different, 552B-backbone model. The reported multi-M5 setup is not evidence for one 128 GB laptop. I did not establish a validated, comfortably fitting Mac configuration for GLM-5.3-Flash during this survey; lower-bit/offloaded possibilities need a separate validation. [DeepSeek model](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash), [multi-Mac experiment](https://github.com/ml-explore/mlx/discussions/4491), [GLM model](https://huggingface.co/zai-org/GLM-5.3-Flash).

## What we know about speed on this host

From the completed 24-case workload, median generation throughput was:

| Already measured model | Mac Ollama | Mac MLX |
|---|---:|---:|
| Qwen3-Coder 30B | 136.1 tok/s | 137.1 tok/s |
| GPT-OSS 20B, low reasoning | 107.8 tok/s | 131.0 tok/s |
| Gemma 4 31B Q8 | 16.3 tok/s | Not tested |

The new recommendations have **no measured tok/s on this host yet**. Qwen3.8 is dense; it should not be assigned the old sparse Qwen3-Coder's 137 tok/s. We also cannot transfer a hosted API's speed to this laptop. GPT-OSS counts include reasoning tokens; runtime and quantization differences remain relevant. [Raw measurements and methodology](../mac-model-benchmarks/README.md).

I would run the next comparison in this order: **Qwen3.8-27B 8-bit and 4-bit; Qwen3-Coder-Next 4-bit; Qwen3.6-35B-A3B 4-bit; GPT-OSS 120B MXFP4-Q8**. Use representative coding tasks with test outcomes, mathematical problems with checked answers, document extraction with citations, and blind writing judgments. Preserve the old nightly screen for continuity, but do not use its 24 cases as an overall model ranking.

Record prompt ingest tok/s, generation tok/s, time to first token, total time to a correct answer, peak memory, swap, reasoning/output tokens and context length. Start at 8K and 32K before extending context. Compare fixed prompts/settings for reproducibility and a separately labeled pass using model-recommended settings. LM Studio can expose MLX models conveniently; direct MLX-LM/MLX-VLM gives a scriptable benchmark route. Architecture support must be checked against the installed runtime. [LM Studio's engine design](https://lmstudio.ai/blog/unified-mlx-engine).

No new model weights were downloaded and no benchmark runtime was changed during this survey.
