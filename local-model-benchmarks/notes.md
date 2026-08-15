# Notes — local model benchmarks

Running log. Raw numbers, methodology changes, and things that turned out to be wrong.

## 2026-08-15 — first harness run

Built `bench.ps1` with two modes: `-Discover` (poll HF trending, diff, triage by fit) and
`-Benchmark <ollama-tag>` (the battery).

### Discovery works, with one known blind spot

150 models across six pipeline tags. Fit triage is accurate where parameter counts exist:

| Model | Reported params | Verdict |
|---|---|---|
| Qwen/Qwen3.8-27B | 27.8B | fits-bf16 |
| meta-models/Muse-Glimmer-30B | 29.8B | fits-bf16 |
| deepseek-ai/DeepSeek-V4-Flash-0731 | 304.2B | fits-with-cpu-offload |
| deepseek-ai/DeepSeek-V4-Pro-0813 | 1650.5B | api-only |
| Qwen/Qwen3.8-2.4T-A95B | 2446.2B | api-only |
| moonshotai/Kimi-K3 | 2779.9B | api-only |

**Blind spot:** GGUF-only repos (`unsloth/*-GGUF`, `Abiray/*-GGUF`) report `unknown`. They publish no
safetensors index, which is where the parameter count comes from. Since GGUF repos are often the
*most* runnable option locally, this is backwards and worth fixing — probably by parsing the quant
file sizes in the repo tree instead.

**API gotcha:** the list endpoint omits `safetensors` even with `full=true`. Parameter counts require
a per-model request. Detail lookups are capped at 40 per run so a first run can't balloon.

**Bug found and fixed:** first version did `Sort-Object modelId -Unique` for dedup, which silently
re-sorted everything alphabetically and destroyed trending rank. Now re-sorts on `trendingScore`.

### Benchmark battery — Qwen3.8-27B BF16 (first full run)

```
loadMs               22922
genTokPerSec          87.8
tokensFor100Words     7034
promptTokens          7021
promptTokPerSec     2555.4
codeExecutes          true    ("1..5 | % { $_ }")
```

Two things this measured that earlier manual testing got wrong:

**Prompt ingest was unmeasurable before.** Hand-testing used ~20-token prompts and produced numbers
between 2.3 and 446 tok/s across runs — pure noise, dominated by fixed overhead. The battery now
sends ~7K tokens of filler, which yields a stable 2555 tok/s. Any prompt-ingest figure taken from a
short prompt should be treated as meaningless.

**Reasoning overhead is enormous and worth publishing.** 7,034 tokens generated to satisfy a
100-word request. Nearly nobody reports this, and it dominates real-world latency far more than the
headline tok/s figure. Comparable earlier observation: qwen3.5:122b spent 5,849 tokens on the same
prompt.

### Methodology caveat on today's comparison table

Only the Qwen3.8-27B row came from `bench.ps1`. The others were measured earlier by hand via
`ollama run --verbose` with the same prompt. That path adds terminal rendering overhead — the manual
Qwen3.8 figure was 81 tok/s versus 87.8 through the API. **Treat cross-row comparisons in the first
report as approximate until every model has been re-run through the harness.**

The DeepSeek row is different again: llama.cpp's `llama-server`, not Ollama, since it needs
`--n-cpu-moe` to split experts across VRAM and system RAM. Ollama has no equivalent flag.

### TODO

- Re-run every model through `bench.ps1` so the table is methodologically uniform
- Fit triage for GGUF repos via file-size parsing
- Decide whether to auto-download; currently discovery is strictly read-only
- Add a llama.cpp benchmark path so GGUF models aren't Ollama-only
