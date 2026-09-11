# Model benchmark campaign results

Updated: 2026-09-11T12:29:47-06:00

This is a progress report until every worthwhile queued test is complete or its authorization ends.
Rows remain in queue order, not quality rank. Only terminal records are scored. Raw throughput from invalid comparisons is omitted here and retained in the linked JSON.

| Model / artifact | Run status | Valid throughput, candidate / coder (tok/s) | Quality screen (protocol shown) | Exact checks, candidate / coder |
|---|---|---:|---|---|
| [gpt-oss:20b](../../runs/20260911-101617-efac0182.json) | reasoning-only screen | — | 15/16 (low reasoning; unpaired) | — |
| [bartowski/LiquidAI_LFM2.5-2.6B-GGUF<br>LiquidAI_LFM2.5-2.6B-bf16.gguf](../../runs/20260911-101720-6660d412.json) | invalid comparison | — | skipped / 12/16 | 2/3 / 3/3 |
| [qwen3-coder:30b](../../runs/20260911-102013-bde53f62.json) | workload screen | — | 4/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-102055-f62e9dfc.json) | workload screen | — | 6/24 (practical-json-v1, separate) | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-102155-996f70fb.json) | workload screen | — | 8/24 (practical-json-v1, separate) | — |
| [gpt-oss:20b](../../runs/20260911-102255-5507f7e0.json) | workload screen | — | 22/24 (practical-json-v1, separate) | — |
| [qwen3-coder:30b](../../runs/20260911-102405-2cce7ecf.json) | workload screen | — | 3/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-102425-01db054f.json) | workload screen | — | 6/24 (practical-json-v1, separate) | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-102525-e7f183f2.json) | workload screen | — | 9/24 (practical-json-v1, separate) | — |
| [gpt-oss:20b](../../runs/20260911-102626-7bca806d.json) | workload screen | — | 18/24 (practical-json-v1, separate) | — |
| [qwen3-coder:30b](../../runs/20260911-102806-f54b95b7.json) | workload screen | — | 3/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-102826-59d0534b.json) | workload screen | — | 4/24 (practical-json-v1, separate) | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-102926-9263bf0d.json) | workload screen | — | 7/24 (practical-json-v1, separate) | — |
| [gpt-oss:20b](../../runs/20260911-103026-1e31d196.json) | workload screen | — | 20/24 (practical-json-v1, separate) | — |
| [qwen3-coder:30b](../../runs/20260911-103126-3d212e50.json) | workload screen | — | 5/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-103146-feb0f9a7.json) | workload screen | — | 6/24 (practical-json-v1, separate) | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-103236-31e0e759.json) | workload screen | — | 9/24 (practical-json-v1, separate) | — |
| [gpt-oss:20b](../../runs/20260911-103338-0fcf9c1e.json) | workload screen | — | 19/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-103508-a46f93d0.json) | workload screen | — | 22/24 (practical-json-v1, separate) | — |
| [qwen3-coder:30b](../../runs/20260911-105432-b971404d.json) | code-writing screen | — | 5/8 tasks; 90/99 tests (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-105452-c9ab841c.json) | valid comparison | 212.29 / 296.28 | 13/16 / 12/16 | 3/3 / 3/3 |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-105852-8da350a1.json) | code-writing screen | — | 7/8 tasks; 98/99 tests (separate) | — |
| [qwen3.5:122b](../../runs/20260911-110242-57e2c942.json) | code-writing screen | — | 5/8 tasks; 61/99 tests (separate) | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-111102-51d22ad9.json) | code-writing screen | — | 5/8 tasks; 86/99 tests (separate) | — |
| [qwen3.5:122b](../../runs/20260911-111212-57060e08.json) | code-writing screen | — | 5/8 tasks; 90/99 tests (separate) | — |
| [gpt-oss:20b](../../runs/20260911-111302-18389fd1.json) | code-writing screen | — | 4/8 tasks; 93/99 tests (separate) | — |
| [qwen3-coder:30b](../../runs/20260911-112823-5a23bb5e.json) | HumanEval-X adapted screen | — | 6/20 tasks (separate) | — |
| [bartowski/LiquidAI_LFM2.5-2.6B-GGUF<br>LiquidAI_LFM2.5-2.6B-bf16.gguf](../../runs/20260911-112843-c253a8a0.json) | workload screen | — | 4/8 (practical-json-v1, separate) | — |
| [qwen3-coder:30b](../../runs/20260911-113043-d7d489e0.json) | HumanEval-X adapted screen | — | 20/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-113103-136b79b8.json) | workload screen | — | 7/24 (practical-json-v1, separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-113143-340b6af6.json) | workload screen | — | 6/24 (practical-json-v1, separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-113303-2ab9d3f3.json) | code-writing screen | — | 5/8 tasks; 85/99 tests (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-113423-8a1d3d93.json) | code-writing screen | — | 4/8 tasks; 92/99 tests (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-113454-7f755f04.json) | HumanEval-X adapted screen | — | 15/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-113524-ffcc5c7b.json) | HumanEval-X adapted screen | — | 19/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-113554-75062ded.json) | invalid comparison | — | skipped / 12/16 | 3/3 / 3/3 |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-113914-4de43549.json) | workload screen | — | 22/24 (practical-json-v1, separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-114044-48316ea1.json) | workload screen | — | 22/24 (practical-json-v1, separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-114214-b78fc0f1.json) | code-writing screen | — | 2/8 tasks; 24/99 tests (separate) | — |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf | deferred | — | — | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-114634-49e72c10.json) | HumanEval-X adapted screen | — | 19/20 tasks (separate) | — |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf | deferred | — | — | — |
| [qwen3.8:27b-mtp-bf16](../../runs/20260911-104941-c75692e6.json) | workload screen | — | 24/24 (practical-json-v1, separate) | — |
| [qwen3.5:122b](../../runs/20260911-111333-466f7755.json) | workload screen | — | 21/24 (practical-json-v1, separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-114724-988f220f.json) | workload screen | — | 22/24 (practical-json-v1, separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-114844-7ccf6425.json) | workload screen | — | 21/24 (practical-json-v1, separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-115025-e5b6d628.json) | workload screen | — | 21/24 (practical-json-v1, separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-115145-28f3491b.json) | HumanEval-X adapted screen | — | 15/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-115515-901ee87b.json) | HumanEval-X adapted screen | — | 17/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-115735-5b09f278.json) | HumanEval-X adapted screen | — | 16/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-120035-c58cb298.json) | HumanEval-X adapted screen | — | 14/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-120335-51c1db24.json) | HumanEval-X adapted screen | — | 15/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-120625-53b77c4d.json) | HumanEval-X adapted screen | — | 16/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-120926-20e0741b.json) | HumanEval-X adapted screen | — | 15/20 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-121146-6948e502.json) | HumanEval-X adapted screen | — | 2/3 tasks (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-121246-58946ddf.json) | code-writing screen | — | 2/8 tasks; 24/99 tests (separate) | — |
| [bartowski/nex-agi_Nex-N2.5-mini-GGUF<br>nex-agi_Nex-N2.5-mini-Q6_K.gguf](../../runs/20260911-122106-443aea0b.json) | code-writing screen | — | 4/8 tasks; 51/99 tests (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122426-ec8a5357.json) | HumanEval-X adapted screen | — | 16/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122506-99b54548.json) | HumanEval-X adapted screen | — | 16/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122536-20e7c4f8.json) | HumanEval-X adapted screen | — | 19/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122606-5e372f97.json) | HumanEval-X adapted screen | — | 16/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122646-d05efa04.json) | HumanEval-X adapted screen | — | 18/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122726-7099ff82.json) | HumanEval-X adapted screen | — | 14/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122807-c6c59bf6.json) | HumanEval-X adapted screen | — | 17/20 tasks (separate) | — |
| [bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf](../../runs/20260911-122847-fb776302.json) | HumanEval-X adapted screen | — | 1/3 tasks (separate) | — |
| bartowski/Ornith-1.5-35B-A3B-GGUF<br>Ornith-1.5-35B-A3B-Q6_K.gguf | running | — | — | — |
| bartowski/Ornith-1.5-35B-A3B-GGUF<br>Ornith-1.5-35B-A3B-Q6_K.gguf | pending | — | — | — |
| bartowski/Ornith-1.5-35B-A3B-GGUF<br>Ornith-1.5-35B-A3B-Q6_K.gguf | pending | — | — | — |
| bartowski/Ornith-1.5-35B-A3B-GGUF<br>Ornith-1.5-35B-A3B-Q6_K.gguf | pending | — | — | — |
| unsloth/gemma-4-31B-it-GGUF<br>gemma-4-31B-it-Q8_0.gguf | pending | — | — | — |
| unsloth/gemma-4-31B-it-GGUF<br>gemma-4-31B-it-Q8_0.gguf | pending | — | — | — |
| unsloth/gemma-4-31B-it-GGUF<br>gemma-4-31B-it-Q8_0.gguf | pending | — | — | — |
| unsloth/gemma-4-31B-it-GGUF<br>gemma-4-31B-it-Q8_0.gguf | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3-coder:30b | pending | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.8:27b-mtp-bf16 | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| qwen3.5:122b | pending | — | — | — |
| muse-glimmer:30b-bf16-dflash | pending | — | — | — |
| bartowski/granite-4.2-30b-GGUF<br>granite-4.2-30b-Q8_0.gguf | pending | — | — | — |
| unsloth/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF<br>NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf | pending | — | — | — |
| ggml-org/Qwen3.8-27B-GGUF<br>Qwen3.8-27B-Q8_0.gguf | pending | — | — | — |
| bartowski/apodex_Apodex-1.1-mini-GGUF<br>apodex_Apodex-1.1-mini-Q6_K.gguf | pending | — | — | — |

## Limits and failed cases

The separate function-writing screen executes eight generated functions against 99 hidden checks in QuickJS WASM; it uses 16384 context and is not pooled with the answer-only screens. The practical JSON suite uses 96 authored checks in 24-case blocks. The 16-item v2 screen measures exact structured answers, code comprehension, small reasoning problems and evidence handling. It does not execute generated code or test a production coding agent. One item changes the score by 6.25 percentage points; differences are descriptive and have no statistical significance claim. V1 pilot and V2 main-sweep scores are not pooled.

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

### workload-gptoss-low-part1

Personal model digests unchanged: True.

### workload-coder-part2

Personal model digests unchanged: True.

### workload-qwen35-part2

Personal model digests unchanged: True.

### workload-qwen38-part2

Personal model digests unchanged: True.

### workload-gptoss-low-part2

Personal model digests unchanged: True.

### workload-coder-part3

Personal model digests unchanged: True.

### workload-qwen35-part3

Personal model digests unchanged: True.

### workload-qwen38-part3

Personal model digests unchanged: True.

### workload-gptoss-low-part3

Personal model digests unchanged: True.

### workload-coder-part4

Personal model digests unchanged: True.

### workload-qwen35-part4

Personal model digests unchanged: True.

### workload-qwen38-part4

Personal model digests unchanged: True.

### workload-gptoss-low-part4

Personal model digests unchanged: True.

### workload-qwen35-think-part1

Personal model digests unchanged: True.

### coding-coder-pilot

Personal model digests unchanged: True.

### kat-coder-q8

Candidate: overnight-screen-v2, 13/16. Failed cases: sql-null, capacity, sort-tiebreak.
Candidate thinking probe: completed. Wall-time ratio to ordinary median: 1.20x. Thinking characters: 62; answer characters: 643.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### coding-qwen38-think

Personal model digests unchanged: True.

### coding-qwen35-think

Personal model digests unchanged: True.

### coding-qwen38-off

Personal model digests unchanged: True.

### coding-qwen35-off

Personal model digests unchanged: True.

### coding-gptoss-low

Personal model digests unchanged: True.

### humaneval-coder-pilot

Personal model digests unchanged: True.

### workload-lfm-implicit-part1

Personal model digests unchanged: True.

### humaneval-coder-chat-pilot

Personal model digests unchanged: True.

### workload-kat-off-part1

Personal model digests unchanged: True.

### workload-kat-think-part1

Personal model digests unchanged: True.

### coding-kat-think

Personal model digests unchanged: True.

### coding-kat-off

Personal model digests unchanged: True.

### humaneval-chat-kat-think-pilot

Personal model digests unchanged: True.

### humaneval-chat-kat-off-pilot

Personal model digests unchanged: True.

### nex-mini-q6

Comparison issue: candidate: output truncated; candidate: unexpected thinking in ordinary responses
Candidate: overnight-screen-v2, skipped. Failed cases: none recorded.
Candidate quality screen issue: Ordinary responses did not establish thinking-off behavior.
Candidate thinking probe: skipped. Ordinary responses returned thinking; a thinking-off reference was not established.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### workload-nex-off-part1

Personal model digests unchanged: True.

### workload-nex-think-part1

Personal model digests unchanged: True.

### coding-nex-think

Personal model digests unchanged: True.

### humaneval-chat-nex-think-pilot

Personal model digests unchanged: True.

### workload-qwen38-think-part1

Personal model digests unchanged: True.

### workload-qwen35-think-part2

Personal model digests unchanged: True.

### workload-nex-think-part2

Personal model digests unchanged: True.

### workload-nex-think-part3

Personal model digests unchanged: True.

### workload-nex-think-part4

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part2

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part3

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part4

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part5

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part6

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part7

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part8

Personal model digests unchanged: True.

### humaneval-chat-nex-think-part9

Personal model digests unchanged: True.

### coding-nex-think-16k-output

Personal model digests unchanged: True.

### coding-nex-think-recommended-sampling

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part2

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part3

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part4

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part5

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part6

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part7

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part8

Personal model digests unchanged: True.

### humaneval-chat-kat-off-part9

Personal model digests unchanged: True.

Public publishing remains pending the specific approval requested in this thread. Local reports and commits continue independently.
