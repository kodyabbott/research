# Research notes — September 22, 2026

Scope: practical local models on one M5 Max / 40 GPU cores / 128 GB unified-memory MacBook. Balanced coverage assumed after an optional focus question. This is selection research, not a new measured benchmark campaign.

Method: broad search for discovery, official model cards and inference implementation sources for claims, direct public Hugging Face API metadata for revisions and tensor sizes. Read local benchmark report for host measurements. Memory only guided continuity with the prior Mac setup; hardware/runtime statements rely on current-session artifacts.

Short primary-source anchors (each below is a verbatim excerpt; no more than 25 quoted words from any one page):

- Qwen3.8-27B: “Scientific reasoning GPQA Diamond” and “89.2”; table and evaluation qualifications in https://huggingface.co/Qwen/Qwen3.8-27B . Recommendation is an inference combining capability and size, not a locally reproduced score.
- Qwen3-Coder-Next: “coding agents and local development” — https://huggingface.co/Qwen/Qwen3-Coder-Next .
- Leanstral 1.5: “an open-source code agent model designed for” — https://huggingface.co/mistralai/Leanstral-1.5-119B-A6B . The named proof assistant is Lean 4.
- Qwen3.8 Flash-Next: “125B with 6B activated, plus 51B n-gram embedding and 4B MTP” — https://huggingface.co/Qwen/Qwen3.8-Flash-Next .
- MFLUX Ideogram implementation: “mflux does not call the hosted API” — https://github.com/mflux-community/mflux/blob/main/src/mflux/models/ideogram4/README.md .
- Higgs TTS 3: “Released for research and non-commercial use” — https://huggingface.co/bosonai/higgs-tts-3-4b . Card additionally defines a creator-use grant; do not collapse that nuance into a blanket commercial prohibition.
- DeepSeek OptiQ artifact: “~2.5 tok/s on an M3 Max, SSD-bound” — https://huggingface.co/mlx-community/DeepSeek-V4-Flash-0731-OptiQ-2bit . This is a different artifact/runtime from the mixed-2.4-bit candidate, and is not evidence of M5 Max full-resident throughput.
- Artificial Analysis current index: “Artificial Analysis Intelligence Index v4.3.2” — https://artificialanalysis.ai/models/qwen3-8-27b . Search results included older launch scores; not mixed with the current index. The first-place label is a small-open-model class, not all models.

Verified API metadata is in artifact-metadata.json. Each successful record preserves the exact revision and per-file bytes. Summed safetensors include every such file in the repository: audio tokenizers/MTP/auxiliary weights may be included. No files were actually downloaded. Decimal GB and GiB must not be interchanged.

Rejected or narrowed claims:

- [REMOVED -- no supporting source found] A single definitive best model for every discipline. Use category recommendations with explicit confidence limits instead.
- [REMOVED -- no supporting source found] Current leaderboard performance survives all 2-bit or 4-bit conversions unchanged.
- [REMOVED -- no supporting source found] Qwen3.8 runs at the old Qwen3-Coder 30B's measured speed.
- API lookup failures for guessed mlx-community/GLM-5.3-Flash-4bit and some embedding/reranker IDs are retained in metadata. HTTP 401 from those public endpoints does not prove gated existence; these IDs are not download recommendations.
- Official and MFLUX image model names are not proofs of measured complete-pipeline memory fit; media recommendations retain that limitation.
- DeepSeek V4.1 has a larger backbone than V4 Flash. Do not silently exchange their results or download requirements.
- Treat published vendor evaluations as vendor-reported, dependent on harness, sampling and reasoning budget. Writing preference and domain-specific corpus quality remain unmeasured.

TODOs for follow-up benchmarking: model-specific runtime compatibility, quality of aggressive quantization, actual peak RAM at 8K/32K context, retrieval/reranking integration, language-pair translation quality, real-time audio factors, image preference trials, and video pipeline memory/latency. No installation or benchmark claims are made for this survey.

Final source check: 44 distinct report URLs returned successful HTTP responses; redirects recorded in source-checks.json. Local links and tensor-size sums verified. Self-review caught a missing DeepSeek runtime distinction: the selected mixed-2.4-bit artifact requires oMLX and provides external matching-hardware results, now explicitly separated from our measurements.

Source review narrowed the Mistral writing recommendation to a subjective comparison candidate and removed a GLM parameter/memory calculation that was not recoverable in the opened primary-source page. No broad leaderboard or writing-quality winner is claimed.
