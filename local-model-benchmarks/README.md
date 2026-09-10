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

## Autonomous routine — updated 2026-09-10

Kody authorized autonomous model selection, downloads, and benchmarks within
[policy.json](policy.json). [scheduled-task.md](scheduled-task.md) is the versioned copy of
the Claude task instructions. The daily schedule remains 21:00 local; benchmark starts are
limited to 21:00–05:59. Daytime catch-up runs collect candidates only.

Limits: one candidate attempt per day, 20 GiB per download, 60 GiB of task storage including
temporary import copies and failed-import reservations, 25 GiB free disk, and a 60-minute
process deadline. No model-library cleanup is automatic. Busy GPU/Ollama cases defer.

Discovery keeps unfinished candidates queued even after they leave the trending window.
GGUF sizes/hashes come from repository metadata. Pending lookups, failed requests, and
unavailable metadata are distinguished. Existing `state/seen.json` is preserved and migrated
to `state/candidates.json` on the first successful discovery. Raw records go in tracked
`runs/`; queues, daily ledger, import provenance, and temporary downloads stay in ignored `state/`.

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

"Tokens for a 100-word request" is the total the model generated to satisfy a prompt asking for
roughly 130 tokens of output. Everything above that is reasoning overhead.

The spread is the story. `qwen3-coder:30b` answered in 100 tokens. `Qwen3.8-27B` took 7,034 — seventy
times as many — to answer the same question. At 87.8 tok/s that is about 80 seconds of wall clock,
while the coder model finished in under half a second at 259 tok/s.

So the model that looks three times slower on the headline number is, for a short factual request,
closer to a hundred and fifty times slower in practice. Throughput alone will mislead you about
which model feels fast.

**How well-covered is this?** [Artificial Analysis tracks average reasoning tokens per model](https://artificialanalysis.ai/methodology) and prices them into cost-to-run — but only for **hosted API endpoints**. Two 2026 papers ([arXiv 2606.25519](https://arxiv.org/html/2606.25519v1), [arXiv 2606.00206](https://arxiv.org/abs/2606.00206)) show quantization inflates chain-of-thought length by +4.7% to +292%, which means hosted-API figures are **provably not a valid proxy for a local quant** — but both papers ran vLLM on H100s with research quants, not GGUF K-quants on consumer hardware. That specific intersection is the part that appears genuinely uncovered.

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
the standard library. The wrapper finds the existing Codex-bundled Python on this machine;
`NIGHTLY_BENCH_PYTHON` can point to another installed interpreter. No packages are installed.

Each candidate and the installed `qwen3-coder:30b` baseline use an 8192-token context,
temperature 0, seed 42, 512-token output cap, and three repetitions after warmup. Thinking
is disabled where supported. Results retain model digest, template hash, parameters,
runtime/GPU state, raw responses, medians/range, latency, and output truncation.

The battery measures generation throughput and prompt ingest, then checks exact number
sequencing, arithmetic, and extraction. It never executes generated code. These are small
instruction-following checks, not a coding-quality benchmark. `loadMs` is model-loading
duration, not time to first token. Output tokens are not isolated reasoning tokens.

## Running it

```powershell
.\bench.ps1 -Discover
.\bench.ps1 -Pending

# Fill state/selection.json from selection.example.json using a verified pinned source.
.\bench.ps1 -ValidateCandidate .\state\selection.json
.\bench.ps1 -RunCandidate .\state\selection.json

# Human-driven validation only; not the scheduled admission path.
.\bench.ps1 -Benchmark "qwen3-coder:30b"
```

Discovery never downloads weights. The scheduled path enforces publisher, file/hash, daily,
disk, GPU, and runtime limits. It imports only single-file GGUFs into `nightly-bench-*` names.
Existing selections pin their current Ollama digest. It never changes existing model tags.
Hash verification establishes artifact identity, not model quality or runtime security.

Offline regression tests (no downloads or inference):

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest -v test_nightly.py
```

## Known limitations

- Ollama only. Split GGUFs, extra projectors, adapters, custom loaders, and runtime upgrades
  require a separate decision.
- File sizes describe weights. Admission reserves 12 GiB of live GPU headroom, but actual
  KV-cache/activation needs still vary by architecture.
- Failed import reservations stay charged until manually reconciled, accounting conservatively
  for possible orphaned Ollama blobs. Models are never automatically deleted.
- Templates and tokenizers differ across models. Three repetitions describe local variability;
  they do not establish a broad leaderboard.
- Claude's local scheduler requires its app open and the computer awake; catch-up cannot
  reconstruct missed trending snapshots.

## Implementation references

- [Ollama chat API](https://docs.ollama.com/api/chat): options, thinking, cache and timing fields.
- [Ollama usage](https://docs.ollama.com/api/usage): load/evaluation timing semantics.
- [Hugging Face Hub API](https://huggingface.co/docs/hub/api): revisions and file metadata.
- [Claude scheduling](https://code.claude.com/docs/en/desktop-scheduled-tasks): local execution and catch-up.
