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

## The battery

Five measurements per model, identical every run:

1. **Cold load time** from disk to first token
2. **Generation throughput** on a fixed prompt
3. **Reasoning overhead** — total tokens spent on that prompt
4. **Prompt ingest** at ~7K tokens, long enough to be meaningful
5. **Functional code test** — the model writes a PowerShell one-liner, the harness *executes* it and checks the output. Pass or fail, not a judgement call.

Vision models additionally get an image described. The file is copied to a neutral name first, because
a path like `C:\Windows\Web\Wallpaper\...` lets a model infer the answer without looking at the pixels.

## Running it

```powershell
# What's newly trending, and what fits this box
.\bench.ps1 -Discover

# Full battery against an installed Ollama model
.\bench.ps1 -Benchmark "qwen3.8:27b-mtp-bf16" -ImagePath .\neutral.jpg
```

Discovery is read-only. It never downloads, and never deletes.

## Known limitations

- **GGUF-only repos report `unknown` fit.** Parameter counts come from the safetensors index, which GGUF repos don't publish. Since GGUF is often the most locally-runnable format, this gets the triage backwards for exactly the repos that matter most.
- **Ollama only.** llama.cpp models are benchmarked by hand; the harness has no path for them yet.
- **Fit triage is arithmetic, not reality.** It estimates from parameter count and ignores context length, KV cache, and activation memory, all of which consume real VRAM.
