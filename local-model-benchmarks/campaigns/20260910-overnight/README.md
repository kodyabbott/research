# Overnight benchmark campaign: September 10-11, 2026

Kody asked to review every past nightly run and test as many worthwhile models as possible
overnight, with quality ahead of quantity and no further input required. This is a temporary
count exemption, not a permanent change to the 8:15 PM Fable task or its one-model daily limit.

## Evidence and selection

The historical review covers every nightly entry in [notes.md](../../notes.md), from August 15
through September 10, and every saved JSON record inventoried in `history-audit.json`. The older
nights were mostly discovery-only; the raw standardized runs distinguish actual benchmarks,
plumbing fixtures, deliberate deadline tests, admissions, and metadata snapshots. Missing older
raw measurements are not reconstructed from narrative notes. The legacy queue contains 392 IDs:
335 ready metadata records, 53 pending, and four failed requests. Those failures are not model
quality verdicts.

First remeasure the installed Qwen3.8 BF16/MTP, Muse BF16/DFlash, and Qwen3.5 122B builds against
the same coder baseline. This closes the historical comparison gap without downloading weights.
Their stored custom parameters and templates remain part of the measured configuration; these
are not controlled quantization-only comparisons. Do not duplicate the two installed OBLITERATED
tags, or present their earlier context-confounded observations as current evidence.

Then prioritize these independently verified upstream/mirror pairs. This order reflects
experiment value, not an established quality ranking. Exact revisions, filenames, bytes, and
SHA-256 values must be recorded in the selection files before each launch.

| Priority | Model and purpose | Approved GGUF publisher |
|---|---|---|
| 1 | [KAT-Coder-V2.5-Dev](https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev): coding specialist | [Bartowski](https://huggingface.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF), Q8 |
| 2 | [Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B): revisit the August 21 recommendation | [Bartowski](https://huggingface.co/bartowski/Ornith-1.5-35B-A3B-GGUF), Q6; Q8 exceeds the cap |
| 3 | [Gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it): distinct dense family | [Unsloth](https://huggingface.co/unsloth/gemma-4-31B-it-GGUF), Q8 |
| 4 | [Granite-4.2-30B](https://huggingface.co/ibm-granite/granite-4.2-30b): revisit August 26-27 | [Bartowski](https://huggingface.co/bartowski/granite-4.2-30b-GGUF), Q8 |
| 5 | [Nemotron-3.5-Lightning-30B-A3B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16): hybrid architecture comparison | [Unsloth](https://huggingface.co/unsloth/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF), Q8 |
| 6 | [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B): stock Q8 reference | [ggml-org](https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF), Q8 |
| 7 | [LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B): small extraction/instruction assistant | [Bartowski](https://huggingface.co/bartowski/LiquidAI_LFM2.5-2.6B-GGUF), BF16 |
| 8 | [Apodex-1.1-mini](https://huggingface.co/apodex/Apodex-1.1-mini): structured-work finetune | [Bartowski](https://huggingface.co/bartowski/apodex_Apodex-1.1-mini-GGUF), Q6 |

Several candidates derive from Qwen; model-line diversity is not base-architecture diversity.
LFM's upstream card discourages agentic coding and knowledge-heavy tasks. Apodex's headline
claims depend on an Agent Team scaffold that this harness does not reproduce. Mirror publisher
approval identifies the artifact distributor; the upstream vendor is recorded separately.

Hold Nex, K2-Horizon, Spark, NeoHorse, and Edge0 until an approved mirror is verified. Targeted
searches did not find one; this is not proof none exists. Hold Ling-3.0-tiny pending Windows
Ollama compatibility confirmation: its [upstream instructions](https://huggingface.co/inclusionAI/Ling-3.0-tiny)
describe a source PR and MLX/Apple Silicon support. Do not spend downloads on draft-only,
split, oversized, image, audio, or video artifacts. Muse Q8's unchanged configuration already
produced an invalid comparison; repeating it unchanged adds little evidence.

## Method and operation

[campaign.py](../../campaign.py) uses the existing supervised candidate transaction. It
validates an expiring authorization and the original policy hash at launch and again at
reservation. Under the normal operation lock, only that reservation may exceed the daily
count. The in-memory value is immediately restored; `policy.json` is never written. Every
attempt appears in a separate campaign ledger, including hard-deadline failures. Normal
calendar-day quota stays available for the next evening scheduled run. Publisher, hash, file, storage, GPU, ownership,
private-runtime, idle/unload, and one-hour process limits remain active. A new candidate cannot
start at or after 04:58 MDT; the full hour plus shutdown verification fits before 06:00.

The throughput battery is unchanged. While each model is loaded, the campaign adds
[quality_screen.py](../../quality_screen.py): 16 authored, deterministic cases covering code
comprehension, algorithms, SQL/data reasoning, structured output, missing evidence, and treating
embedded instructions as data. Candidate and baseline receive the same cases and 512-token cap.
Each case has a 45-second subprocess deadline within the shared one-hour run budget. The grader
parses exactly one JSON object, rejects duplicate keys and nonstandard numbers, and requires
the expected JSON value and type, accepting equivalent finite numbers such as 40 and 40.0
while keeping booleans distinct from numbers. It never executes generated code. These are a small screen,
not coding-task execution, a production agent evaluation, or a general intelligence score.
No confidence intervals or broad ranking are inferred from 16 items.

The main sweep uses `overnight-screen-v2`, which explicitly states the required JSON value
type for every case. The first v1 comparison is retained as a pilot: two baseline answers
encoded correct arrays as strings, exposing ambiguity in the original prompts. V1 and v2
quality scores must not be pooled. The installed Qwen3.8 build is queued again for v2.

Quality results are separate from throughput medians. A truncated answer fails its case;
unexpected thinking marks the thinking-off screen invalid. If the ordinary battery already
returns unexpected thinking, the extra screen is skipped. Interrupted screens preserve partial
responses and are labeled incomplete. Historical raw results remain unchanged.

Validation before live use: all 81 offline tests passed in 8.736 seconds after review fixes, comprising the existing
69 harness tests and 12 campaign/screen tests. These verify expiry, time zones, deadline
margin, changed-policy refusal, reservation/restoration behavior, unchanged normal daily quota,
JSON grading, persistence, and partial/contaminated screens. No live result is implied by tests.

The thread heartbeat checks progress every 20 minutes and expires on the morning of September
11. Its recorded ID is `overnight-model-benchmark-campaign`. Keep the app open and workstation
awake for thread follow-ups; local job state and raw results are retained on disk. See the
[official scheduled-task documentation](https://learn.chatgpt.com/docs/automations?surface=app).

## Results

Pilot [20260910-225905-c6df53d6](../../runs/20260910-225905-c6df53d6.json) completed: installed
Qwen3.8 BF16/MTP generated at median 43.24 tok/s versus 287.38 for the coder baseline; the
standard comparison was valid and both passed 3/3 exact checks. V1 screen scores were 14/16
and 10/16, respectively. These are pilot scores with the format ambiguity described above.
Both models unloaded, and all seven personal model digests stayed unchanged. This installed
configuration does not reproduce the historical hand-measured or MTP speed claim.

Populate main-sweep results only from terminal raw records and retain failures and invalid comparisons.
