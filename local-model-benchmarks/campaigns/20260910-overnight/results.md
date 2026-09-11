# Overnight campaign results

Updated: 2026-09-10T23:26:50-06:00

This is a progress report until every worthwhile queued test is complete or the overnight window ends.
Rows remain in queue order, not quality rank. Only terminal records are scored. Raw throughput from invalid comparisons is omitted here and retained in the linked JSON.

| Model / artifact | Run status | Valid throughput, candidate / coder (tok/s) | v2 screen, candidate / coder | Exact checks, candidate / coder |
|---|---|---:|---|---|
| [qwen3.8:27b-mtp-bf16](../../runs/20260910-225905-c6df53d6.json) | valid comparison | 43.24 / 287.38 | v1 pilot; kept separate | 3/3 / 3/3 |
| [muse-glimmer:30b-bf16-dflash](../../runs/20260910-230444-966fe4d6.json) | invalid comparison | — | 15/16 / 12/16 | 3/3 / 3/3 |
| [qwen3.5:122b](../../runs/20260910-230702-17b673fa.json) | valid comparison | 136.24 / 287.34 | 14/16 / 12/16 | 3/3 / 3/3 |
| [qwen3.8:27b-mtp-bf16](../../runs/20260910-230832-3a625ef8.json) | valid comparison | 41.95 / 288.2 | 15/16 / 12/16 | 3/3 / 3/3 |
| [openbmb/MiniCPM5-2B-GGUF<br>MiniCPM5-2B-F16.gguf](../../runs/20260910-231102-eee16b78.json) | valid comparison | 250.36 / 307.33 | 6/16 / 12/16 | 3/3 / 3/3 |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF<br>Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf | running | — | — | — |
| gpt-oss:20b | pending | — | — | — |
| bartowski/LiquidAI_LFM2.5-2.6B-GGUF<br>LiquidAI_LFM2.5-2.6B-bf16.gguf | pending | — | — | — |
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

### installed-qwen38-bf16

Candidate: overnight-screen-v1, 14/16. Failed cases: capacity, string-escape.
Candidate thinking probe: completed. Wall-time ratio to ordinary median: 20.57x. Thinking characters: 17335; answer characters: 646.
Baseline: overnight-screen-v1, 10/16. Failed cases: python-aliasing, python-default, python-boundary, sql-null, capacity, sort-tiebreak.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### installed-muse-bf16

Comparison issue: candidate: output truncated
Candidate: overnight-screen-v2, 15/16. Failed cases: capacity.
Candidate thinking probe: completed. Wall-time ratio to ordinary median: 1.92x. Thinking characters: 3761; answer characters: 697.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### installed-qwen35-122b

Candidate: overnight-screen-v2, 14/16. Failed cases: capacity, sort-tiebreak.
Candidate thinking probe: completed. Wall-time ratio to ordinary median: 15.80x. Thinking characters: 7927; answer characters: 692.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### installed-qwen38-bf16-v2

Candidate: overnight-screen-v2, 15/16. Failed cases: string-escape.
Candidate thinking probe: completed. Wall-time ratio to ordinary median: 20.59x. Thinking characters: 17335; answer characters: 646.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

### minicpm-f16-screen

Candidate: overnight-screen-v2, 6/16. Failed cases: python-aliasing, python-closure, python-default, sql-null, sql-left-join, interval-union, capacity, weighted-rate, extract-active, string-escape.
Candidate thinking probe: completed. Wall-time ratio to ordinary median: 30.66x. Thinking characters: 11606; answer characters: 602.
Baseline: overnight-screen-v2, 12/16. Failed cases: python-boundary, sql-null, sql-left-join, capacity.
Baseline thinking probe: unsupported.
Personal model digests unchanged: True.

Public publishing remains pending the specific approval requested in this thread. Local reports and commits continue independently.
