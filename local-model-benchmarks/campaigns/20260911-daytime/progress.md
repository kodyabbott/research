# RTX PRO 6000 benchmark progress

Updated: 2026-09-11T13:24:33.622408-06:00

September 11 campaign status: active. Results below are measured locally; scores from different reasoning budgets are separate.

Running: coding-gemma-think-pilot. Pending queue entries: 63.

Tested model artifacts or installed configurations: 9. This includes completed compatibility diagnostics; it does not mean every configuration produced a valid ordinary comparison. Downloads alone are excluded. The JSON companion links each tested artifact to its source model, protocols and raw runs.

## Matched 24-case workload comparison

Every row below covers exactly the same first 24 authored cases. Thinking-off output caps are 2048 tokens; reasoning caps are 8192. Diagnostic pilots with fewer than 24 completed cases are excluded from this matched table. These are workload answers, not generated-code execution scores.

| Model | Thinking | Correct / 24 | Median response seconds | Truncated | Protocol note |
|---|---|---:|---:|---:|---|
| qwen3-coder:30b | False | 4/24 | 0.44 | 0 | none |
| qwen3.5:122b | False | 6/24 | 1.00 | 0 | none |
| qwen3.8:27b-mtp-bf16 | False | 8/24 | 1.48 | 0 | none |
| gpt-oss:20b | low | 22/24 | 1.82 | 0 | none |
| qwen3.5:122b | True | 22/24 | 40.27 | 2 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF / Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf | False | 7/24 | 0.65 | 0 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF / Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf | True | 6/24 | 3.11 | 0 | none |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF / nex-agi_Nex-N2.5-mini-Q6_K.gguf | False | 22/24 | 2.40 | 0 | unexpected thinking |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF / nex-agi_Nex-N2.5-mini-Q6_K.gguf | True | 22/24 | 2.41 | 0 | none |
| qwen3.8:27b-mtp-bf16 | True | 24/24 | 11.77 | 0 | none |
| bartowski/Ornith-1.5-35B-A3B-GGUF / Ornith-1.5-35B-A3B-Q6_K.gguf | implicit | 21/24 | 4.67 | 0 | none |
| bartowski/Ornith-1.5-35B-A3B-GGUF / Ornith-1.5-35B-A3B-Q6_K.gguf | False | 4/24 | 0.60 | 0 | none |
| unsloth/gemma-4-31B-it-GGUF / gemma-4-31B-it-Q8_0.gguf | False | 10/24 | 1.86 | 0 | none |

## Broader workload results

The deterministic 96-case suite covers ledger replay, event-state reconstruction, dependency scheduling, SQL, shortest paths, record extraction, Python tracing, and retrieval. Completed blocks are accumulated below. In this JSON-answer suite, model-generated code is never executed. These are authored workload checks, not a standardized coding benchmark.

| Model | Thinking | Context | Correct / attempted | Median response seconds | Truncated | Protocol note |
|---|---|---:|---:|---:|---:|---|
| qwen3-coder:30b | False | 8192 | 15/96 | 0.45 | 0 | none |
| qwen3.5:122b | False | 8192 | 22/96 | 1.01 | 0 | none |
| qwen3.8:27b-mtp-bf16 | False | 8192 | 33/96 | 1.48 | 0 | none |
| gpt-oss:20b | low | 8192 | 79/96 | 2.12 | 0 | none |
| qwen3.5:122b | True | 8192 | 43/48 | 40.73 | 5 | none |
| bartowski/LiquidAI_LFM2.5-2.6B-GGUF / LiquidAI_LFM2.5-2.6B-bf16.gguf | implicit | 8192 | 4/8 | 7.71 | 1 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF / Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf | False | 8192 | 7/24 | 0.65 | 0 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF / Kwaipilot_KAT-Coder-V2.5-Dev-Q8_0.gguf | True | 8192 | 6/24 | 3.11 | 0 | none |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF / nex-agi_Nex-N2.5-mini-Q6_K.gguf | False | 8192 | 22/24 | 2.40 | 0 | unexpected thinking |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF / nex-agi_Nex-N2.5-mini-Q6_K.gguf | True | 8192 | 86/96 | 2.45 | 0 | none |
| qwen3.8:27b-mtp-bf16 | True | 8192 | 24/24 | 11.77 | 0 | none |
| bartowski/Ornith-1.5-35B-A3B-GGUF / Ornith-1.5-35B-A3B-Q6_K.gguf | implicit | 8192 | 89/96 | 5.18 | 0 | none |
| bartowski/Ornith-1.5-35B-A3B-GGUF / Ornith-1.5-35B-A3B-Q6_K.gguf | False | 8192 | 4/24 | 0.60 | 0 | none |
| unsloth/gemma-4-31B-it-GGUF / gemma-4-31B-it-Q8_0.gguf | False | 8192 | 10/24 | 1.86 | 0 | none |

Thinking-off jobs allow 2,048 output tokens; reasoning jobs allow 8,192. All use an 8,192-token context. Raw answers, runtime versions, model digests, and exact prompts are preserved in the research repository. Partial totals should not be read as a final ranking. Rows marked unexpected thinking violate their requested mode and must not be used as valid thinking-off comparisons.

## Standard candidate comparisons

The short throughput battery uses 8192 context and a 512-token output cap. Valid rows show candidate / Qwen3-Coder median generation tokens per second. The separate v2 answer screen has 16 authored cases; it does not execute code.

| Candidate | Throughput status | Tokens/second, candidate / coder | v2 answers, candidate / coder | Issue |
|---|---|---:|---|---|
| bartowski/LiquidAI_LFM2.5-2.6B-GGUF | invalid | not comparable | not scored / 12/16 | candidate: output truncated; candidate: unexpected thinking in ordinary responses |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF | valid | 212.29 / 296.28 | 13/16 / 12/16 | none |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF | invalid | not comparable | not scored / 12/16 | candidate: output truncated; candidate: unexpected thinking in ordinary responses |
| bartowski/Ornith-1.5-35B-A3B-GGUF | valid | 223.67 / 296.5 | 12/16 / 12/16 | none |
| unsloth/gemma-4-31B-it-GGUF | valid | 40.47 / 302.25 | 14/16 / 12/16 | none |

## Initial candidate screens

- GPT-OSS 20B: 15/16 on the separate low-reasoning v2 screen. It followed an instruction embedded inside a data field on the failed extraction case.
- LFM2.5 2.6B BF16: downloaded and hash-verified, imported, and tested. Its ordinary responses returned unexpected thinking and hit the token cap, so the ordinary throughput comparison is invalid. This is a protocol compatibility finding, not an overall model-quality verdict.
- Nex-N2.5-mini Q6: a newly found Bartowski mirror was verified and added to the queue. Text-only evaluation will not test its advertised computer-use or vision capabilities.

## Function-writing results

Eight authored JavaScript tasks, 99 hidden checks, and input immutability. Generated functions execute only inside an isolated QuickJS WebAssembly guest, with no host functions or module loader. This is a small function-writing screen, not a standardized coding leaderboard or repository agent evaluation.

| Model | Thinking / sampler | Context / output cap | Functions fully correct | Hidden checks passed | Median generation seconds | Issues |
|---|---|---:|---:|---:|---:|---|
| qwen3-coder:30b | False / greedy-v1 | 16384 / 4096 | 5/8 | 90/99 | 0.96 | none |
| qwen3.8:27b-mtp-bf16 | True / greedy-v1 | 16384 / 8192 | 7/8 | 98/99 | 22.45 | none |
| qwen3.5:122b | True / greedy-v1 | 16384 / 8192 | 5/8 | 61/99 | 65.14 | 3 truncated |
| qwen3.8:27b-mtp-bf16 | False / greedy-v1 | 16384 / 4096 | 5/8 | 86/99 | 4.34 | none |
| qwen3.5:122b | False / greedy-v1 | 16384 / 4096 | 5/8 | 90/99 | 2.47 | none |
| gpt-oss:20b | low / greedy-v1 | 16384 / 8192 | 4/8 | 93/99 | 1.75 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF | True / greedy-v1 | 16384 / 8192 | 5/8 | 85/99 | 3.59 | 1 truncated |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF | False / greedy-v1 | 16384 / 4096 | 4/8 | 92/99 | 1.40 | none |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF | True / greedy-v1 | 16384 / 8192 | 2/8 | 24/99 | 38.97 | 6 truncated |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF | True / greedy-v1 | 32768 / 16384 | 2/8 | 24/99 | 78.38 | 6 truncated |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF | True / nex-recommended-v1 | 16384 / 8192 | 4/8 | 51/99 | 27.81 | 4 truncated |
| bartowski/Ornith-1.5-35B-A3B-GGUF | implicit / greedy-v1 | 16384 / 8192 | 7/8 | 87/99 | 17.80 | 1 truncated |
| bartowski/Ornith-1.5-35B-A3B-GGUF | False / greedy-v1 | 16384 / 4096 | 4/8 | 72/99 | 1.62 | none |
| unsloth/gemma-4-31B-it-GGUF | False / greedy-v1 | 16384 / 4096 | 7/8 | 98/99 | 5.39 | none |

Initial runs use 16,384 context and 4,096 output tokens with thinking off or 8,192 with reasoning. Larger-budget rows use 32,768 context and 16,384 output tokens; they are separate configurations, not equal-budget comparisons. The separately labeled nex-recommended-v1 sampler uses temperature 0.7, top_p 0.95, top_k 40 and seed 42; the original greedy sampler stays unchanged. Hidden-test counts are correlated within each function; passing a function requires all its checks. Prompts, generated code, sandbox dependency lock, and every observed result are saved.

## HumanEval-X JavaScript, adapted WASM evaluation

One greedy sample per task from the [published dataset](https://huggingface.co/datasets/zai-org/humaneval-x). The supported set is 163 of 164 tasks: Node crypto task 162 is excluded. Missing test invocations in tasks 32, 119, and 151 are explicitly added, and test randomness uses seed 42. All 163 reference solutions passed this runner. This is an adapted evaluation, not the original 200-sample leaderboard protocol; this longstanding public dataset may appear in model training data.

| Model | Prompt style | Thinking | Correct / attempted | Median generation seconds | Total generation minutes | Truncated | Protocol note |
|---|---|---|---:|---:|---:|---:|---|
| qwen3-coder:30b | continuation | False | 6/20 | 0.51 | 0.17 | 0 | none |
| qwen3-coder:30b | full-program | False | 20/20 | 0.53 | 0.19 | 0 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF | full-program | True | 15/20 | 0.76 | 0.25 | 0 | none |
| bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF | full-program | False | 136/163 | 0.79 | 2.26 | 0 | none |
| bartowski/nex-agi_Nex-N2.5-mini-GGUF | full-program | True | 129/163 | 2.21 | 19.21 | 21 | none |
| bartowski/Ornith-1.5-35B-A3B-GGUF | full-program | implicit | 148/163 | 3.31 | 13.81 | 2 | none |
| bartowski/Ornith-1.5-35B-A3B-GGUF | full-program | False | 17/20 | 0.75 | 0.27 | 0 | none |
| unsloth/gemma-4-31B-it-GGUF | full-program | False | 19/20 | 2.55 | 0.95 | 0 | none |

These HumanEval-X runs use 16384 context and 4096 output tokens with thinking off or 8192 with reasoning. Partial totals cover completed blocks only. Total generation time sums task response times, including failed and truncated attempts, and excludes model import, load, warmup, grading and between-block overhead. Source data, transformations, reference validation, prompts, raw continuations, and test outcomes are saved.

## Background model downloads

- bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF: completed; 36.91 / 36.91 GB; complete-file hash verified: True.
- bartowski/nex-agi_Nex-N2.5-mini-GGUF: completed; 29.37 / 29.37 GB; complete-file hash verified: True.
- bartowski/Ornith-1.5-35B-A3B-GGUF: completed; 30.53 / 30.53 GB; complete-file hash verified: True.
- unsloth/gemma-4-31B-it-GGUF: completed; 32.64 / 32.64 GB; complete-file hash verified: True.

## Resource and stop behavior

One GPU inference job runs at a time. Model downloads use the existing F: benchmark store. Each worker has a one-hour hard deadline. The original nightly policy and canceled September 10 campaign remain preserved. New launches require a current agent-supervision lease and remaining usage; already authorized workers retain their deadline and cleanup. A user stop request revokes the campaign and terminates its identity-verified processes.

The workstation thermal state is not held constant. Downloads, report generation, reference-fixture tests, and brief browser QA with GPU rendering disabled overlapped some runs. Latency is descriptive for this machine and run; different model configurations and reasoning budgets are recorded separately. If a case was repeated under the same configuration, the latest completed result is counted once.

## Incomplete runs

These attempts produced no complete score and are excluded from aggregate accuracy tables. Full error details and any partial responses remain in the raw records.

- workload-gemma-think-pilot (20260911-131310-ae09b0ba): Request exceeded 120 seconds.
