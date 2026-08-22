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

## 2026-08-15 — landscape check, and a correction to this project's framing

Ran a survey before investing further. It contradicted the premise this folder was built on, so the
README has been corrected rather than defended.

**The format is saturated.** r/LocalLLaMA carried 249 unique benchmark posts in 30 days — about 58 a
week. 36% scored under 10 points; 62% under 50. Twelve separate Qwen3.8 benchmark posts appeared
within 24 hours of release, scoring between 0 and 47. On Hacker News, "I benchmarked local LLMs"
submissions consistently sit at 1–3 points, including two separate submissions of Simon Willison's
own `smevals`.

**A well-funded incumbent is entering.** [Artificial Analysis](https://artificialanalysis.ai/benchmarks/hardware)
lists a "Workstation — Coming late 2026" tier: *"Compare consumer- and prosumer-tier system
performance for running open models at your desk."* Building a generic prosumer speed leaderboard
means colliding with them.

**Claims removed from README.md as unsupported:**
- ~~"this column is rarely reported anywhere"~~ — Artificial Analysis reports reasoning tokens per
  model. Narrowed to the local-GGUF-quant intersection, which does appear uncovered.
- ~~"several of the [prompt-ingest] figures circulating for these models"~~ — `[REMOVED — no
  supporting source found]`. Never verified that specific figures circulate; the real finding is that
  `llama-bench` supports `-d` and the *convention* ignores it.
- Framing implying novelty — replaced with an explicit prior-art section.

**What the survey says the differentiator actually is.** The most rigorous work in this space
([Rakuen Software](https://rakuensoftware.com/blog/synthesis-model-selection)) runs on a **$900 24 GB
AMD card**. Their advantage is paired bootstrap confidence intervals over 10,000 resamples, reporting
null results as headlines, publishing corrections with audit trails, and disclosing their own
confounds unprompted. Statistical discipline, not VRAM.

**Sustainability warning.** dubesor.de/benchtable covered 347 models from 02/2024 to 04/2026, then
was **retired because manual upkeep became infeasible**. Any sweep goes stale in 6–8 weeks. Fully
automated or it doesn't survive the year.

### TODO

- Re-run every model through `bench.ps1` so the table is methodologically uniform
- Fit triage for GGUF repos via file-size parsing
- Decide whether to auto-download; currently discovery is strictly read-only
- Add a llama.cpp benchmark path so GGUF models aren't Ollama-only

## 2026-08-21 — nightly discovery (automated run)

First scheduled run of the nightly task. Discovery only — no downloads, no battery. The
auto-download question is still open (see TODO above), so the agent's rule tonight was:
benchmark only if a new trending model is already installed. None were.

`bench.ps1 -Discover`: 150 trending models across six pipeline tags, **25 new** since the
2026-08-15 seeding run. New text-generation models that fit this box:

| Model | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|
| OBLITERATUS/Qwen3.8-27B-OBLITERATED | 27.8B | 51.7 GB | fits-bf16 | 398 | 123,956 |
| ornith-ai/Ornith-1.5-35B-A3B | 36B | 67 GB | fits-bf16 | 276 | 9,165 |
| ornith-ai/Ornith-1.5-9B | 9.4B | 17.5 GB | fits-bf16 | 143 | 10,304 |
| EschaLabs/Qwen3.8-27B-Escha-W2 | 6.3B | 11.8 GB | fits-bf16 | 100 | 561 |
| tencent/UI-Mate-27B (vision) | 27.4B | 51 GB | fits-bf16 | 67 | 284 |
| gittensor-model-hub/Qwen3.8-27B-NVFP4-RTX5090 | 15B | 27.9 GB | fits-bf16 | 73 | 75,859 |
| superwhisper/s1-mini | 0.8B | 1.4 GB | fits-bf16 | 184 | 1,136 |

Also new: `ornith-ai/Ornith-1.5-397B` (396.8B, fits-with-cpu-offload — same territory as the
DeepSeek-V4-Flash run), and GGUF mirrors of both smaller Ornith models charting with ~115–123K
downloads each but reporting `unknown` fit — the known GGUF blind spot, again on exactly the
repos most worth running.

**Observations, unverified beyond the API response:**

- The Ornith-1.5 family (35B-A3B, 9B, 397B, plus GGUF mirrors) is the interesting cluster — a
  model family new to the trending list occupying four of the top slots. The `-A3B` suffix
  usually denotes ~3B active params (MoE), which would make the 35B fast here, but I have not
  verified that against the model card. Strongest benchmark candidate from tonight's crop.
- EschaLabs/Qwen3.8-27B-Escha-W2 is named 27B but the safetensors index reports 6.3B — a prune
  or distill, or a mislabeled repo. Worth a model-card read before trusting either number.
- The NVFP4-RTX5090 repo charts under `image-text-to-text` with 15B reported params against a
  27B name — quantized multimodal repack; fit arithmetic for it is not reliable.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored). Next action when a
human is driving: pick from the table above — `ornith-ai/Ornith-1.5-35B-A3B` first.

## 2026-08-21 — nightly discovery, second run (automated)

Second automated run of the same date — the earlier entry above was the run that seeded most of
today's diff, so tonight only **3 new** models appeared out of 150 trending. Discovery only:
nothing new is installed in Ollama, and auto-download remains an open TODO, so no battery ran.

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| orcarouter/Qwen3.8-27B-Uncensored | image-text-to-text | 27.8B | 51.7 GB | fits-bf16 | 62 | 5,591 |
| empero-ai/Qwen3.8-2B-Distill-GGUF | text-generation | unknown | — | unknown | 60 | 35,147 |
| UntMods/Krea2_Chars_LoRA | text-to-image | unknown | — | unknown | 6 | 0 |

**Observations, unverified beyond the API response:**

- The orcarouter repo shares a base with the installed `qwen3.8:27b-mtp-bf16`, but it is a
  community finetune, not the same weights — it does not qualify as "already installed" for the
  benchmark rule. It also charts under `image-text-to-text` despite the name suggesting a text
  finetune; I have not read the model card to resolve that.
- empero-ai/Qwen3.8-2B-Distill-GGUF is the GGUF fit-triage blind spot again (no safetensors
  index, so `paramsB` is null) — third consecutive entry where the most-downloaded runnable repo
  in the diff reports `unknown`. The file-size-parsing fix in the TODO keeps earning its slot.
- Krea2_Chars_LoRA trends with 0 downloads and 18 likes — either a very fresh upload or an
  artifact of how HF computes trending; not investigated. Out of scope for this box's battery
  (text-to-image LoRA) regardless.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).
