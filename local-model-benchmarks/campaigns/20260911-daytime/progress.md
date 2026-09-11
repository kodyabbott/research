# RTX PRO 6000 benchmark progress

Updated: 2026-09-11T10:25:01.337300-06:00

The September 11 campaign is active. Results below are measured locally; scores from different reasoning budgets are separate.

Running: workload-qwen35-part2. Pending queue entries: 27.

## Broader workload results

The deterministic 96-case suite covers ledger replay, event-state reconstruction, dependency scheduling, SQL, shortest paths, record extraction, Python tracing, and retrieval. Completed blocks are accumulated below. Model-generated code is never executed. These are authored workload checks, not a standardized coding benchmark.

| Model | Thinking | Correct / attempted | Median response seconds | Truncated |
|---|---|---:|---:|---:|
| qwen3-coder:30b | False | 7/48 | 0.45 | 0 |
| qwen3.5:122b | False | 6/24 | 1.00 | 0 |
| qwen3.8:27b-mtp-bf16 | False | 8/24 | 1.48 | 0 |
| gpt-oss:20b | low | 22/24 | 1.82 | 0 |

Thinking-off jobs allow 2,048 output tokens; reasoning jobs allow 8,192. All use an 8,192-token context. Raw answers, runtime versions, model digests, and exact prompts are preserved in the research repository. Partial totals should not be read as a final ranking.

## Initial candidate screens

- GPT-OSS 20B: 15/16 on the separate low-reasoning v2 screen. It followed an instruction embedded inside a data field on the failed extraction case.
- LFM2.5 2.6B BF16: downloaded and hash-verified, imported, and tested. Its ordinary responses returned unexpected thinking and hit the token cap, so the ordinary throughput comparison is invalid. This is a protocol compatibility finding, not an overall model-quality verdict.
- KAT-Coder Q8: downloading in a separate supervised prefetch while installed-model GPU tests run.
- Nex-N2.5-mini Q6: a newly published Bartowski mirror was verified and added to the queue. Text-only evaluation will not test its advertised computer-use or vision capabilities.

## Resource and stop behavior

One GPU inference job runs at a time. Model downloads use the existing F: benchmark store. Each worker has a one-hour hard deadline. The original nightly policy and canceled September 10 campaign remain preserved. This campaign stops when requested, when usage is exhausted, or at its current authorization cutoff.
