# Local Model Benchmarks

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Opus 4.6). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Same-day benchmarks of trending open models, run on one known machine, with methodology stated so the numbers can be argued with.

A fixed battery, a fixed machine, and every measurement traceable to a command anyone can re-run.

> [!IMPORTANT]
> **Prior art, checked before claiming novelty.** Local-model throughput benchmarking is a crowded field and this project is not new work. [LocalScore](https://www.localscore.ai/) has ~4,000 submissions. The [llama.cpp CUDA scoreboard](https://github.com/ggml-org/llama.cpp/discussions/15013) is community-maintained and active. [MLPerf Client](https://mlcommons.org/benchmarks/client/) has the strongest methodology. [oobabooga's LocalBench](https://localbench.substack.com/) covers quantization quality via KL-divergence across 72+ quants, and `llama-perplexity --kl-divergence` ships free inside llama.cpp. [Artificial Analysis](https://artificialanalysis.ai/benchmarks/hardware) has announced a workstation-tier hardware leaderboard for late 2026.
>
> What follows is a personal instrument for one machine, kept because same-day numbers on identical hardware are useful to its owner. Treat any framing of it as novel with suspicion.

## Active daytime benchmark campaign - September 11

A fresh user request authorized sustained daytime benchmarking. See the [daytime campaign](campaigns/20260911-daytime/README.md) and [current progress](campaigns/20260911-daytime/progress.md). Its separate authorization exempts daytime starts and candidate count, while preserving the normal nightly policy and prior cancellation history.

## Paused benchmark campaign - September 10-11

The campaign was canceled at user request on September 10 at 23:28 MDT, with five
completed runs preserved. All campaign work and its heartbeat are stopped; the normal
8:15 PM task remains unchanged. Read the [Codex/Astra morning handoff](campaigns/20260910-overnight/handoff.md)
before resuming: the old authorization is revoked, and daytime candidate admission
remains gated by the overnight window.
See the [selection plan](campaigns/20260910-overnight/README.md),
[dated results](campaigns/20260910-overnight/results.md), and
[runtime compatibility findings](campaigns/20260910-overnight/compatibility.md).
The main sweep adds a 16-case authored answer-quality screen; GPT-OSS uses a separately labeled
reasoning-enabled protocol. This does not establish a general coding-quality leaderboard.

## Autonomous routine — updated 2026-09-10

Kody authorized autonomous model selection, downloads, and benchmarks within
[policy.json](policy.json). [scheduled-task.md](scheduled-task.md) is the versioned copy of
the Claude task instructions. The daily schedule is 20:15 local; benchmark starts are
limited to 20:15–05:59 with minute precision. Daytime catch-up runs collect candidates only.

Limits: one candidate attempt per day, 35 GiB per artifact, 240 GiB of task storage including
temporary copies and orphaned import blobs, 25 GiB free disk, and a 60-minute worker deadline.
Partial downloads resume and the complete file is rehashed. Slow runs may take multiple
nights; the larger cap does not guarantee completion in one night.

The harness starts a private Ollama child on `127.0.0.1:11435` with models and downloads under
`F:\models\nightly-benchmark`. An unverified pre-existing listener causes a refusal. A recorded
orphan can be reclaimed only under the operation lock with matching PID, exact OS process
creation time, executable, and listening port. Imports and eligible
cache deletions use only that child. The original Ollama server on port 11434 supplies the
installed baseline; its model library is not moved. Candidate unload and VRAM recovery are
confirmed before the baseline starts. The child exits at the end, including timeout handling.

The cache retains the two latest eligible completed imports. Eviction requires a matching
recorded digest, task prefix, completed raw result, and an unloaded secondary server. A verified
failed import is also removable when a terminal error result pins the same name and digest.
Environmental, timeout, and baseline interruptions do not trigger failed-model eviction.
The harness reclaims a successful import's original uploaded blob only after verifying its full
SHA-256 and size, the matching owned-store marker and imported manifest, and absence of that hash
from every private manifest. Unknown blobs remain for manual review. Admission reserves three
possible copies: download, upload, and Ollama's rewritten model layer.
Verified GGUFs survive failed imports so another attempt need not download them again. Deletions
are journaled and reservations released. Storage admission counts actual directory bytes,
including failed-import orphan blobs; old reservations do not accumulate into a permanent
charge after files are removed. Unknown/orphan files are charged and require manual review.
Busy workloads get a bounded five-minute wait, then the candidate is deferred.

Run mode launches a detached supervisor and returns a run ID immediately, avoiding the
scheduled agent's shell timeout. `-WaitRun` polls for up to 55 seconds per call; `-StatusRun`
checks once. The result remains running until bookkeeping and child shutdown finish.
Cleanup failures are recorded separately and do not erase completed measurements.

Discovery keeps unfinished candidates queued even after they leave the trending window.
Each invocation allows 100 detail lookups, favors text pipelines while draining legacy IDs,
and caps stale-revision refresh at 20. Revision changes are detected in detail responses;
the trending list does not supply a commit SHA. Discovery has an eight-minute request budget
so it can return partial results before the scheduled shell's ten-minute limit.
GGUF sizes/hashes come from repository metadata. Pending lookups, failed requests, and
unavailable metadata are distinguished. Existing `state/seen.json` is preserved and migrated
to `state/candidates.json` on the first successful discovery. Raw records go in tracked
`runs/`; queues, ledgers, import provenance, and child logs stay in ignored `state/`.
Weights and resumable partial files live on F:.

**The August 15 results below are historical and predate the standardized harness.**

## The machine

| | |
|---|---|
| GPU | NVIDIA RTX PRO 6000 Blackwell Max-Q, 96 GB |
| CPU | AMD Ryzen 9 9950X, 16C/32T |
| RAM | 128 GB DDR5-5200 |
| OS | Windows 11 Pro 25H2 |
| Runtimes | Ollama 0.32.13, llama.cpp b10430 (CUDA 13.3) |

## Results — 2026-08-15

| Model | Quant | Runtime | Gen tok/s | Tokens for a 100-word request |
|---|---|---|---|---|
| qwen3-coder:30b | Q4 | Ollama | 259.5 | 100 |
| qwen3.5:122b | Q4 | Ollama | 124.3 | 5,849 |
| Qwen3.8-27B | BF16 | Ollama | 87.8 | 7,034 |
| Muse-Glimmer-30B | BF16 | Ollama | 62.0 | 858 |
| DeepSeek-V4-Flash-0731 | UD-IQ3_XXS | llama.cpp | 40.1 | — |

> [!WARNING]
> Only the Qwen3.8-27B row was produced by `bench.ps1`. The others were measured by hand through `ollama run --verbose`, which adds terminal rendering overhead — the same model measured 81 tok/s that way versus 87.8 through the API. Cross-row comparisons are approximate until every model is re-run through the harness. See [notes.md](notes.md).

## What the second column is, and why it matters more than it looks

"Tokens for a 100-word request" is the historical total generated for a short request.
These totals include answer text and, for applicable models, thinking. They do not isolate
reasoning tokens. The old runs did not use the standardized settings now enforced below.

The spread is the story. `qwen3-coder:30b` answered in 100 tokens. `Qwen3.8-27B` took 7,034 — seventy
times as many — to answer the same question. At 87.8 tok/s that is about 80 seconds of wall clock,
while the coder model finished in under half a second at 259 tok/s.

So the model that looks three times slower on the headline number is, for a short factual request,
closer to a hundred and fifty times slower in practice. Throughput alone will mislead you about
which model feels fast.

The earlier claim that this measurement is uncovered by other benchmarks is unverified.
The purpose here is a reproducible local comparison, not a novelty claim. The historical
cross-model spread is not a controlled measurement of reasoning overhead.

## Prompt ingest needs a real prompt

Early hand-testing measured prompt ingest between 2.3 and 446 tok/s for the same model across runs.
Those numbers were noise: the prompts were ~20 tokens, so fixed overhead dominated entirely.

Measured properly with a ~7,000-token prompt, Qwen3.8-27B ingests at **2,555 tok/s**.

To be precise about whose fault this is: `llama-bench` supports depth via `-d/--n-depth` and has for
some time. The problem is convention, not tooling — the canonical hardware tables standardize on
`pp512/tg128` against **Llama 2 7B**, a dense model from 2023 at a 512-token prompt, which says
little about a 96 GB card running a large MoE at long context.

## The current battery

The PowerShell entry point delegates to [nightly.py](nightly.py), using Python 3.10+ and only
the standard library. The wrapper prefers `NIGHTLY_BENCH_PYTHON`, then a standard per-user
Python installation, then PATH, and finally the Codex cache. Raw runs identify the interpreter
and flag a cache fallback. A user-owned Python installation avoids depending on Codex updates.
The scheduled task never installs software or packages.

Each candidate and the installed `qwen3-coder:30b` baseline use an 8192-token context,
temperature 0, seed 42, 512-token output cap, and three repetitions after warmup. Thinking
is disabled where supported. Results retain model digest, template hash, parameters,
runtime/GPU state, raw responses, medians/range, latency, and output truncation. Both runtime
versions must match. Child performance variables are captured through a small allowlist;
the primary's environment remains an explicit unknown. Loaded-model metadata records actual
VRAM allocation and context. This is a local comparison with those limits, not laboratory isolation.

Thinking capability metadata is not treated as proof of response behavior. The harness checks
warmup, timed trials, and exact-output checks for nonempty returned `message.thinking` text.
`thinkingControl` records advertised support, the requested setting, and the affected responses
with raw thinking/answer character counts. Unexpected thinking in either model invalidates the
comparison even when no output was truncated. This detects exposed thinking text; it cannot
establish whether a model performed unexposed internal reasoning.

A separate thinking-enabled trial repeats the short prompt with an 8192-token cap and a
180-second subprocess deadline. It reports total generated tokens, separate thinking/answer
character counts, raw fields, truncation, and latency relative to the thinking-off median.
The probe never enters throughput medians. HTTP latency excludes subprocess startup, which is
also recorded separately. Vision is explicitly unmeasured; projector support remains future work.
If ordinary responses already contain thinking, the separate probe is skipped with a reason
because a thinking-off reference was not established. Historical raw run files are preserved.

The battery measures generation throughput and prompt ingest, then checks exact number
sequencing, arithmetic, and extraction. It never executes generated code. These are small
instruction-following checks, not a coding-quality benchmark. The comparisons normalize newline styles
and trim outer whitespace only: trailing spaces on individual lines, extra text, duplicates,
and reordering fail the exact-output check. `loadMs` is model-loading
duration, not time to first token. Output tokens are not isolated reasoning tokens.

## Running it

```powershell
.\bench.ps1 -Discover
.\bench.ps1 -Pending

# Fill state/selection.json from selection.example.json using a verified pinned source.
.\bench.ps1 -ValidateCandidate .\state\selection.json
.\bench.ps1 -RunCandidate .\state\selection.json
# Use the runId returned above; repeat WaitRun until a terminal status.
.\bench.ps1 -WaitRun "YYYYMMDD-HHMMSS-xxxxxxxx"

# Human-driven validation only; not the scheduled admission path.
.\bench.ps1 -Benchmark "qwen3-coder:30b"
```

Discovery never downloads weights. The scheduled path enforces publisher, file/hash, daily,
disk, GPU, and runtime limits. It imports only single-file GGUFs into `nightly-bench-*` names.
Existing selections pin their current Ollama digest. It never changes existing model tags.
Hash verification establishes artifact identity, not model quality or runtime security.

Offline regression tests (no downloads or inference):

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m unittest -v test_nightly.py
```

## Known limitations

- Ollama only. Split GGUFs, extra projectors, adapters, custom loaders, and runtime upgrades
  require a separate decision.
- File sizes describe weights. Admission reserves 12 GiB of live GPU headroom, but actual
  KV-cache/activation needs still vary by architecture.
- A human can run `acceptance.py --fixture state/acceptance-selection.json` for a <=2 GiB
  plumbing fixture outside the overnight window. It uses the same admission transaction and
  a separate ledger for up to three distinct fixtures per day, leaving the nightly slot available.
  `acceptance.py --deadline-smoke` deliberately stalls a worker with that fixture loaded to
  verify process-tree termination. These are never scheduled task modes.
- Manual validation and setup entry points are separated by task instructions, not an OS
  permission boundary. The scheduled agent is forbidden to use them to bypass admission.
- Work has a one-minute shutdown margin before the one-hour tree-kill deadline. Unload gets
  a bounded share of that margin. Hard-kill verification may take another 35 seconds.
  Interrupted imports may leave orphaned blobs; those bytes stay charged until reconciled.
- Templates and tokenizers differ across models. Three repetitions describe local variability;
  they do not establish a broad leaderboard.
- Claude's local scheduler requires its app open and the computer awake; catch-up cannot
  reconstruct missed trending snapshots.

## Implementation references

- [Ollama chat API](https://docs.ollama.com/api/chat): options, thinking, cache and timing fields.
- [Ollama usage](https://docs.ollama.com/api/usage): load/evaluation timing semantics.
- [Ollama configuration](https://docs.ollama.com/faq): host, model directory, and keep-alive.
- [Ollama deletion API](https://docs.ollama.com/api/delete): cache model deletion.
- [Python 3.14.7 release](https://www.python.org/downloads/release/python-3147/): signed Windows runtime installer and published SHA-256.
- [Hugging Face Hub API](https://huggingface.co/docs/hub/api): revisions and file metadata.
- [Claude scheduling](https://code.claude.com/docs/en/desktop-scheduled-tasks): local execution and catch-up.
