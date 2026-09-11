# Model benchmark campaign results

Updated: 2026-09-11T10:23:17-06:00

This is a progress report until every worthwhile queued test is complete or its authorization ends.
Rows remain in queue order, not quality rank. Only terminal records are scored. Raw throughput from invalid comparisons is omitted here and retained in the linked JSON.

| Model / artifact | Run status | Valid throughput, candidate / coder (tok/s) | v2 screen, candidate / coder | Exact checks, candidate / coder |
|---|---|---:|---|---|
| [gpt-oss:20b](../../runs/20260911-101617-efac0182.json) | reasoning-only screen | — | 15/16 (low reasoning; unpaired) | — |
| [bartowski/LiquidAI_LFM2.5-2.6B-GGUF<br>LiquidAI_LFM2.5-2.6B-bf16.gguf](../../runs/20260911-101720-6660d412.json) | invalid comparison | — | skipped / 12/16 | 2/3 / 3/3 |
| [qwen3-coder:30b](../../runs/20260911-102013-bde53f62.json) | workload screen | — | 4/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-102055-f62e9dfc.json) | workload screen | — | 6/24 (practical-json-v1, separate) | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-102155-996f70fb.json) | workload screen | — | 8/24 (practical-json-v1, separate) | — |
| gpt-oss:20b | running | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf | pending | — | — | — |
| bartowski/Ornith-1.5-35B-A3B-GGUF<br>Ornith-1.5-35B-A3B-Q6_K.gguf | pending | — | — | — |
| unsloth/gemma-4-31B-it-GGUF<br>gemma-4-31B-it-Q8_0.gguf | pending | — | — | — |
| bartowski/granite-4.2-30b-GGUF<br>granite-4.2-30b-Q8_0.gguf | pending | — | — | — |
| unsloth/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF<br>NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf | pending | — | — | — |
| ggml-org/Qwen3.8-27B-GGUF<br>Qwen3.8-27B-Q8_0.gguf | pending | — | — | — |
| bartowski/apodex_Apodex-1.1-mini-GGUF<br>apodex_Apodex-1.1-mini-Q6_K.gguf | pending | — | — | — |

## Limits and failed cases

The 16-item screen measures exact structured answers, code comprehension, small reasoning problems and evidence handling. It does not execute generated code or test a production coding agent. One item changes the score by 6.25 percentage points; differences are descriptive and have no statistical significance claim. V1 pilot and V2 main-sweep scores are not pooled.

A valid throughput comparison does not certify model quality. A completed quality screen is reported separately when throughput is invalid; truncation counts as a failed screen case, and unexpected returned thinking is explicitly marked. Stored BF16/MTP/DFlash configurations include custom settings and cannot isolate quantization effects.

The separate GPT-OSS low-reasoning screen allows 8192 generated tokens per case versus 512 in the main sweep. It is unpaired and is not an equal-budget quality ranking. Thinking probes below are single exploratory trials excluded from throughput medians; ratios against an invalid ordinary comparison are diagnostic only.

### gpt-oss20-low

Candidate: overnight-screen-v2, 15/16. Failed cases: untrusted-record.
Personal model digests unchanged: True.

### lfm26-bf16

Comparison issue: candidate: output truncated; candidate: unexpected thinking in ordinary responses
Candidate: overnight-screen-v2, skipped. Failed cases: none recorded.
Candidate quality screen issue: Ordinary responses did not establish thinking-off behavior.
Candidate thinking probe: skipped. Ordinary responses returned thinking; a thinking-off reference was not established.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### workload-coder-part1

Personal model digests unchanged: True.

### workload-qwen35-part1

Personal model digests unchanged: True.

### workload-qwen38-part1

Personal model digests unchanged: True.

Public publishing remains pending the specific approval requested in this thread. Local reports and commits continue independently.
