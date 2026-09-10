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

## 2026-08-22 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **9 new** since yesterday's second run. No new
trending model is installed in Ollama (checked against `ollama list`), and auto-download
remains an open TODO, so no battery ran.

New models that fit (all non-text pipelines — none are candidates for this harness's battery,
which is text-generation only):

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| Tongyi-MAI/Z-Image | text-to-image | 6.2B | 11.5 GB | fits-bf16 | 6 | 34,444 |
| canopylabs/orpheus-3b-0.1-ft | text-to-speech | 3.8B | 7 GB | fits-bf16 | 5 | 83,944 |
| stabilityai/stable-audio-open-small | text-to-audio | 0.5B | 0.9 GB | fits-bf16 | 2 | 2,059 |

The other six report `unknown` fit: outsourc-e/Qwen3.8-27B-Unleashed-GGUF (text-generation,
trend 73), guillaume127/MiniMax-Music-3-Turbo-FP8, wikeeyang/Flux2-Klein-9B-True-V2,
Claquasse/Anima-Control-Pose, vantagewithai/LTX-2.5-GGUF, leejet/MiniMax-H3-GGUF.

**Observations, unverified beyond the API response:**

- The only new text-generation model, Qwen3.8-27B-Unleashed-GGUF, shares a base with the
  installed `qwen3.8:27b-mtp-bf16` but is a community repack, not the same weights — same
  ruling as orcarouter's Uncensored variant yesterday: does not qualify as "already
  installed." It is also the GGUF fit-triage blind spot again (fourth consecutive diff where
  the top text-gen newcomer reports `unknown`).
- Three of the six `unknown` verdicts are GGUF/FP8 repos in *non-text* pipelines (LTX-2.5,
  MiniMax-H3, MiniMax-Music) — the blind spot is not text-specific, though those pipelines
  are out of scope for the battery anyway.
- wikeeyang/Flux2-Klein-9B-True-V2 shows 771,909 downloads against trend score 6 and 189
  likes — downloads wildly out of proportion to engagement. Possibly a default weight in a
  popular ComfyUI workflow; not investigated.
- Tonight's crop is entirely image/audio/video aside from the one GGUF repack — first diff
  since seeding with zero net-new text-generation candidates for the battery.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-08-24 — OBLITERATED V3 downloaded and benchmarked (user-requested)

Ad-hoc, not the nightly sweep. Kody asked to download `OBLITERATUS/Qwen3.8-27B-OBLITERATED`,
test it, and confirm it is V3. First actual download since the harness was built — the
auto-download TODO is still open for the *nightly* routine, but this was an explicit request.

**V3 confirmed.** The repo has a single `main` branch (no version branches/tags), and the model
card header is "🆕 V3: Deep Liberation" (iterative refinement on V2, self-reported MMLU 82.3%,
-2.1pp vs stock Qwen3.8-27B). Pulling `main` gets V3 — there is nothing else to select.
Apache-2.0, base `Qwen/Qwen3.8-27B`, repo sha `af34629` (lastModified 2026-08-23).

**What was pulled.** `ollama pull hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q8_0` — the Q8_0 GGUF
(27.1 GB on HF, 29 GB as an Ollama blob). Picked Q8_0 for near-lossless quality with room to
spare on 96 GB. `ollama show`: arch `qwen35`, 27.3B params, max context **262144**, vision-capable
(bundled CLIP projector, 460.73M). So this is a multimodal repack, not a text-only model.

**Transient load crash, once.** First battery attempt died with
`CUDA error: shared object initialization failed` / stack-based buffer overrun from llama-server.
A known-good model (`gpt-oss:20b`) loaded and answered immediately afterward, so the driver/Ollama
stack was healthy — the crash did not repeat on retry. Filed as a transient CUDA init race, not a
model defect. Driver 610.88, Ollama 0.32.13.

**The real finding: default context is the throughput determinant here.** Ollama loaded the model
at its full **262144** context because neither the harness nor the request pins `num_ctx`. That
256K KV cache, on top of ~54 GB already held by other apps on this live workstation
(Discord/Chrome/VS Code/Elgato/etc.), pushed VRAM to **97.1 / 97.9 GB** — right at the ceiling —
and gen throughput collapsed:

| Context | Model footprint | VRAM total | Gen tok/s | Prompt ingest tok/s |
|---|---|---|---|---|
| 262144 (Ollama default) | 45 GB | 97.1 GB (pegged) | **16.5** | 83.5 |
| 8192 (pinned via Modelfile) | 28 GB | 82.9 GB | **47.6** | **2867.3** |

Same model, same box, ~3x gen and ~34x prompt-ingest difference — entirely a context/KV-cache
artifact. This is a concrete instance of README known-limitation #3 ("fit triage ignores context
length, KV cache"): fit arithmetic said 51.7 GB BF16 / this Q8_0 at 29 GB fits comfortably, and it
does — until the default 256K context is allocated.

**Clean battery — Q8_0, num_ctx 8192, 100% GPU** (via a pinned variant `obliterated-v3-q8-8k`,
`FROM hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q8_0` + `PARAMETER num_ctx 8192`):

```
loadMs               143   (warm)
genTokPerSec          47.6
tokensFor100Words   2587
promptTokens        7021
promptTokPerSec     2867.3
codeWritten         "1..5 | % { $_ }"
codeExecutes         true
```

**Comparison caveat — do not put this next to the 08-15 Qwen3.8-27B row uncritically.** That
baseline row (87.8 tok/s) is BF16 *and* an MTP (multi-token-prediction) build (`qwen3.8:27b-mtp-bf16`);
MTP inflates the tok/s figure by emitting multiple tokens per step. A standard Q8_0 at 47.6 tok/s
is not slower "because Q8_0 is slower than BF16" — if anything Q8_0 should win on bandwidth. The
gap is MTP vs non-MTP plus the shared-VRAM headroom on this box, not a like-for-like model result.
Prompt ingest (2867 vs baseline 2555) and reasoning overhead (2587 tokens vs baseline 7034, V3
defaulting thinking-off) are the more honest cross-model signals.

**Settings caveat.** Ran with Ollama's default template/sampling, not the model card's V3
recommendations (temp 0, repetition_penalty 1.15, empty system prompt, thinking off, `--jinja`
with the bundled template). The battery measures throughput and one functional code task, so
defaults are acceptable — but these numbers are not the card's tuned-optimal configuration.

**Not verified beyond running it:** the model card's liberation/MMLU claims (82.3% MMLU, 20/20 code
tasks) are self-reported and were not re-measured; only the harness battery above was run. README
results table left untouched — it is a dated 08-15 snapshot and this is an ad-hoc uncensored-variant
test, better kept in this log than promoted to the headline table.

### TODO (new)

- **Pin `num_ctx` in `bench.ps1`.** Tonight proved the Ollama default context can be the single
  biggest throughput variable (3x here). Add a `-NumCtx` parameter (default something honest like
  8192) so battery rows are comparable and don't silently inherit a model's 256K max.

## 2026-08-23 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **7 new** since yesterday. Checked against
`ollama list` — no new trending model is already installed, and auto-download remains an open
TODO, so no battery ran.

New models that fit:

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| orcarouter/Qwen3.8-27B-Uncensored-NVFP4 | image-text-to-text | 21.2B | 39.5 GB | fits-bf16 | 45 | 16,490 |
| HeartMuLa/HeartMuLa-oss-3B-happy-new-year | text-to-audio | 3.9B | 7.3 GB | fits-bf16 | 2 | 2,652 |
| SonexaAI/Sonexa-Music-v0.1-Beta | text-to-audio | 2.4B | 4.5 GB | fits-bf16 | 2 | 17 |

The other four report `unknown` fit: oron1208/OOO_ANIMA-29B-V10 (text-to-image),
realrebelai/SenseNova-U1.5-8B_GGUFs (text-to-image), ResembleAI/chatterbox-turbo
(text-to-speech), facebook/musicgen-medium (text-to-audio).

**Observations, unverified beyond the API response:**

- The orcarouter NVFP4 repo is a quant repack of the same Uncensored finetune that charted on
  08-21. Same ruling as then: shares a base with the installed `qwen3.8:27b-mtp-bf16` but is
  not the same weights — does not qualify as "already installed." Reported params (21.2B
  against a 27B name) are quant metadata, so the fit arithmetic is unreliable — same pattern
  as the gittensor NVFP4 repack on 08-21.
- realrebelai/SenseNova-U1.5-8B_GGUFs is the GGUF fit-triage blind spot again, and it charts
  under `text-to-image` despite a name shaped like an LLM. Not investigated.
- ResembleAI/chatterbox-turbo shows 681 likes against 0 downloads — likely the download
  counter not tracking for that repo layout rather than a real zero. Not investigated.
- facebook/musicgen-medium (1.95M downloads, trend score 1) is a 2023-era model surfacing as
  "new" only because it entered the trending window — a diff artifact, not a new release.
- Second consecutive night with zero net-new text-generation candidates for the battery —
  tonight's crop is entirely image/audio aside from the NVFP4 repack.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-08-24 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **11 new** since yesterday. Checked against
`ollama list` — no new trending model is already installed, and auto-download remains an open
TODO, so no battery ran. (The OBLITERATED V3 pulled earlier today was the ad-hoc user-requested
run logged above; it had already been seen by discovery on 08-21 and is not in tonight's diff.)

New models with a known fit verdict — none are text-generation, so none are battery candidates:

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| tencent/HunyuanImage-3.0 | text-to-image | 83B | 154.6 GB | fits-quantized | 6 | 13,107 |
| ideogram-ai/ideogram-4-nf4 | text-to-image | 4.8B | 8.9 GB | fits-bf16 | 6 | 1,924 |
| pnnbao-ump/VieNeu-TTS-v3-Turbo | text-to-speech | 0.1B | 0.2 GB | fits-bf16 | 5 | 375,394 |
| stabilityai/stable-video-diffusion-img2vid-xt | image-to-video | 1.5B | 2.8 GB | fits-bf16 | 3 | 146,482 |

The other seven report `unknown` fit: AtomicChat/Ornith-1.5-35B-A3B-GGUF (trend 46),
peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF (trend 44), AtomicChat/Ornith-1.5-9B-GGUF (trend 41),
chimingw/Qwen3.8-27B-Uncensored-OrcaRouter-GGUF (trend 39), ethanfel/H3_Cinematic_Multishot_Coverage,
RuneXX/LTX-2.5-Workflows, QuantStack/Wan2.2-I2V-A14B-GGUF.

**Observations, unverified beyond the API response:**

- The top four newcomers by trend score are all GGUF repos reporting `unknown` fit — the
  fit-triage blind spot now owns the entire top of the diff. Fifth consecutive night; the
  file-size-parsing fix in the 08-15 TODO is overdue.
- AtomicChat's Ornith-1.5 GGUFs look like yet more mirrors of the Ornith family that charted
  08-21 (a different org's mirrors were noted then). If the pattern from the safetensors
  originals holds, the 35B-A3B (~67 GB BF16) and 9B (~17.5 GB) both fit this box, but I have
  not verified AtomicChat's files against the originals.
- chimingw/Qwen3.8-27B-Uncensored-OrcaRouter-GGUF appears to be a GGUF of the orcarouter
  Uncensored finetune from 08-21/08-23. Same ruling again: shares a base with installed
  models (`qwen3.8:27b-mtp-bf16`, the OBLITERATED Q8_0) but is not the same weights — does
  not qualify as "already installed."
- All four top GGUFs chart under `image-text-to-text`, including Tiel-Coder-35B whose name
  suggests a code model — recurring pipeline-tag oddity, not investigated.
- stable-video-diffusion-img2vid-xt (Nov 2023 release, 3,385 likes) surfacing as "new" is a
  trending-window diff artifact, same as facebook/musicgen-medium on 08-23.
- peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF trends at 44 with 0 downloads — either very fresh
  or the download counter not tracking; not investigated.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-08-25 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **13 new** since yesterday. Checked against
`ollama list` — no new trending model is already installed, and auto-download remains an open
TODO, so no battery ran.

New models with a known fit verdict:

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| apodex/Apodex-1.1-mini | text-generation | 36B | 67 GB | fits-bf16 | 62 | 484 |
| Jiunsong/SuperQwen3.8-27b-abliterated | image-text-to-text | 27.8B | 51.7 GB | fits-bf16 | 38 | 193 |
| BreezeBlue/Breeze-TTS-2 | text-to-speech | 3.5B | 6.5 GB | fits-bf16 | 9 | 0 |
| data-archetype/canter | text-to-image | 2.1B | 3.8 GB | fits-bf16 | 7 | 6,271 |
| stabilityai/stable-video-diffusion-img2vid | image-to-video | 1.5B | 2.8 GB | fits-bf16 | 2 | 32,127 |

The other eight report `unknown` fit: peculiar-ragdoll/Dirk-Qwen3.8-27B-GGUF (trend 38, 24,168
downloads), Audio8/audio8-TTS-0.1B-ONNX-INT8, ifmylove2011/girlslike-krea2,
Beidouqixing/minimax-h3-4step-lora-flashgen, ResembleAI/chatterbox-flash, suno/bark,
FX-FeiHou/MiniMax-H3-Remix, city96/Wan2.1-I2V-14B-720P-gguf.

**Observations, unverified beyond the API response:**

- apodex/Apodex-1.1-mini is the only net-new text-generation model and tops the diff at trend
  62 — first genuine battery candidate to chart since 08-21. Not installed, so it did not run.
  Its reported 36B / 67 GB matches Ornith-1.5-35B-A3B's numbers from 08-21 exactly; whether
  that is a shared base or coincidence is unchecked (model card not read). "mini" against 36B
  reported params is also unexplained.
- Jiunsong/SuperQwen3.8-27b-abliterated shares a base with the installed OBLITERATED Q8_0 and
  `qwen3.8:27b-mtp-bf16`, but it is a different org's finetune, not the same weights — same
  ruling as the orcarouter/chimingw variants on 08-21/08-23/08-24: does not qualify as
  "already installed." Yet another abliteration of the same 27B base charting; that base now
  accounts for at least five distinct uncensored variants in ten days of diffs.
- peculiar-ragdoll/Dirk-Qwen3.8-27B-GGUF is the GGUF fit-triage blind spot again — sixth
  consecutive night the highest-download runnable text-model repo in the diff reports
  `unknown`. Same org as yesterday's Tiel-Coder GGUF; charts under `image-text-to-text`, the
  recurring pipeline-tag oddity.
- suno/bark (2023, 1,559 likes), stable-video-diffusion-img2vid (Nov 2023), and
  city96/Wan2.1-I2V-14B-720P-gguf are trending-window diff artifacts, not new releases — same
  pattern as musicgen-medium on 08-23 and img2vid-xt on 08-24.
- Three repos show 0 downloads against nonzero likes (Audio8, Breeze-TTS-2, chatterbox-flash —
  the third ResembleAI repo in five nights with this signature); consistent with the download
  counter not tracking certain repo layouts rather than real zeros. Not investigated.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-08-26 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **17 new** since yesterday — the biggest diff since
seeding. Checked against `ollama list` — no new trending model is already installed (the two new
Qwen3.8-27B community variants are different repos than the installed 27B builds), and
auto-download remains an open TODO, so no battery ran.

New models with a known fit verdict:

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| Qwen/Qwen3.8-Flash-Next | image-text-to-text | 180B | 335.3 GB | fits-quantized | 3617 | 2,551 |
| zai-org/GLM-5.3-Flash | text-generation | 321.3B | 598.5 GB | fits-with-cpu-offload | 906 | 0 |
| thomsonreuters/Thomson-1.0-Small | image-text-to-text | 35.1B | 65.4 GB | fits-bf16 | 108 | 214 |
| Qwen/Qwen3.8-Flash-Next-FP8 | image-text-to-text | 180B | 335.3 GB | fits-quantized | 98 | 451 |
| ibm-granite/granite-4.2-30b | text-generation | 29.3B | 54.5 GB | fits-bf16 | 70 | 995 |
| DavidAU/Qwen3.8-27B-Cold-Fable-Fusion-GAIN-V1.1-732-Heretic-Uncensored-stage1 | image-text-to-text | 27.8B | 51.7 GB | fits-bf16 | 44 | 3 |
| briaai/Fibo-1.5 | text-to-image | 8.3B | 15.4 GB | fits-bf16 | 16 | 370 |
| HeartMuLa/HeartMuLa-oss-3B | text-to-audio | 3.9B | 7.3 GB | fits-bf16 | 1 | 854 |

The other nine report `unknown` fit: unsloth/Qwen3.8-Flash-Next-GGUF (trend 356),
unsloth/GLM-5.3-Flash-GGUF (trend 123), jcbtc/Qwen3.8-27B-IU4-Kairic-Edge (trend 43, 2,262
downloads), mrjackspade/Ideogram4-Natural-Language-Text-Encoder,
LAXMAYDAY/NOOB2-Project-Character-Reference-Bypass-Injector-Research (text-to-image),
seedleap/zing-0.5, onnx-community/higgs-audio-v3-tts-4b, declare-lab/mustango,
appautomaton/openmoss-sound-effect-mlx.

**Observations, unverified beyond the API response:**

- Major-release night: Qwen3.8-Flash-Next tops the diff at trend **3617** — nearly 10x anything
  seen since seeding — and GLM-5.3-Flash lands at 906 with 0 downloads / 926 likes (fresh-upload
  signature). Both arrived with same-day unsloth GGUF mirrors, which report `unknown` — the GGUF
  fit-triage blind spot now on its seventh consecutive night, this time on the two biggest
  releases in the log. The file-size-parsing fix is overdue.
- Neither flagship is a battery candidate as-is: Flash-Next (180B, charts multimodal) only fits
  quantized, and GLM-5.3-Flash at 321.3B is cpu-offload territory — same class as the
  DeepSeek-V4-Flash run on 08-15, which needed llama.cpp's `--n-cpu-moe`, a path the harness
  still lacks (open TODO). The FP8 repack's 335.3 GB figure is BF16 arithmetic applied to an
  FP8 repo, so its fit math is not meaningful — same caveat as earlier NVFP4 repacks.
- ibm-granite/granite-4.2-30b is the night's one clean battery candidate: text-generation,
  29.3B / 54.5 GB, fits-bf16, from a first-party org. Not installed, so it did not run.
- The DavidAU "Heretic-Uncensored" repo is yet another uncensored finetune of the Qwen3.8-27B
  base (3 downloads, trend 44 — likes-driven). Same ruling as the orcarouter / chimingw /
  Jiunsong variants: shares a base with installed models but is not the same weights — does not
  qualify as "already installed." That base is now at least six distinct uncensored variants in
  eleven days of diffs.
- jcbtc/Qwen3.8-27B-IU4-Kairic-Edge charts under `text-generation` with real downloads (2,262)
  but a null param count — name suggests a quant repack (IU4?); not investigated.
- declare-lab/mustango (3,640 downloads, trend 1) looks like another trending-window diff
  artifact of an older release, same pattern as musicgen-medium and suno/bark — not verified.
- HeartMuLa/HeartMuLa-oss-3B is the base repo of the "-happy-new-year" variant that charted
  08-23; likely the same model family surfacing twice, not checked.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-08-27 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **8 new** since yesterday. Checked against
`ollama list` — no new trending model is already installed, and auto-download remains an open
TODO, so no battery ran.

New models with a known fit verdict:

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| pipecat-ai/phonellm-alpha-1 | text-generation | 31.6B | 58.8 GB | fits-bf16 | 48 | 64 |
| ibm-granite/granite-4.2-8b | text-generation | 8.8B | 16.4 GB | fits-bf16 | 47 | 2,604 |
| ibm-granite/granite-4.2-3b | text-generation | 3.7B | 6.8 GB | fits-bf16 | 47 | 3,069 |
| RadixArk/Qwen3.8-Flash-Next-NVFP4 | image-text-to-text | 119.6B | 222.8 GB | fits-quantized | 45 | 2,297 |
| nvidia/Cosmos3-Super-Image2Video | image-to-video | 64.6B | 120.3 GB | fits-quantized | 3 | 75,183 |

The other three report `unknown` fit: Vaelico/Wulver (text-to-image, trend 18),
jdopensource/JoyAI-Echo (image-to-video, trend 3), GuGai/text_to_speech_G (text-to-audio,
trend 1).

**Observations, unverified beyond the API response:**

- Three net-new text-generation models that fit in BF16 — the best battery-candidate crop
  since seeding. The two granite-4.2 repos (8B, 3B) are smaller siblings of
  ibm-granite/granite-4.2-30b, which charted 08-26 as that night's clean candidate; the 30B
  remains the more interesting battery target of the family. None are installed, so none ran.
- pipecat-ai/phonellm-alpha-1 tops the diff at trend 48 with only 64 downloads — likes-driven,
  fresh-alpha signature. Name suggests a voice/telephony-oriented LLM (pipecat is a voice-agent
  framework), but the model card was not read.
- RadixArk/Qwen3.8-Flash-Next-NVFP4 is a community NVFP4 repack of Qwen3.8-Flash-Next, the
  08-26 flagship (trend 3617 that night). Reported 119.6B against the original's 180B is quant
  metadata, so the 222.8 GB BF16 arithmetic is not meaningful — same caveat as every NVFP4/FP8
  repack in this log. Even so, "fits-quantized" is directionally right: an NVFP4 of a 180B
  model lands roughly in the 90–100 GB range, which is edge-of-VRAM territory on this box.
- First diff since 08-21 with **zero GGUF repos** — the fit-triage blind spot finally gets a
  night off, by absence rather than by the overdue file-size fix.
- Vaelico/Wulver trends at 18 with 0 downloads / 19 likes — fresh-upload signature, same
  pattern as GLM-5.3-Flash on 08-26 and Krea2_Chars_LoRA on 08-21. Not investigated.
- nvidia/Cosmos3-Super-Image2Video has the diff's only heavyweight download count (75,183) but
  trend 3 — an established release drifting into the trending window rather than a launch;
  out of scope for the battery (image-to-video) regardless.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-09-10 — nightly discovery (automated run)

First logged run since 08-28 — a 13-day gap (why the schedule skipped is not determinable from
this session), so the diff is inflated accordingly: 150 trending models polled, **70 new**, by
far the biggest diff in the log. Checked against `ollama list` — no new trending model is
already installed, and auto-download remains an open TODO, so no battery ran.

New text-generation models that fit — the best battery-candidate crop since seeding
(11 candidates; excludes trending-window artifacts, see observations):

| Model | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|
| openbmb/MiniCPM5-2B | 2.5B | 4.7 GB | fits-bf16 | 915 | 42,289 |
| XHToken/Spark-X2.5-4B | 4.1B | 7.7 GB | fits-bf16 | 738 | 15,930 |
| nex-agi/Nex-N2.5-mini | 35.1B | 65.4 GB | fits-bf16 | 497 | 2,444 |
| IFM/K2-Horizon-MoVA-36B-A4B | 37.4B | 69.7 GB | fits-bf16 | 193 | 4,488 |
| IFM/K2-Horizon-7B | 9B | 16.8 GB | fits-bf16 | 75 | 4,313 |
| TokenRhythm/NeoHorse-1-4B | 4.2B | 7.8 GB | fits-bf16 | 69 | 5,329 |
| nvidia/Qwen3.8-27B-NVFP4 | 18.2B | 33.8 GB | fits-bf16 | 64 | 10,488 |
| XHToken/Spark-X2.5-1.7B | 1.7B | 3.2 GB | fits-bf16 | 62 | 4,362 |
| medismera/Qwen3.8-27B-OBLITERATED-Mythos-Class-Agentic | 27.8B | 51.7 GB | fits-bf16 | 54 | 2,177 |
| Edge0/Edge0-35B-A3B-preview | 34.7B | 64.6 GB | fits-bf16 | 49 | 329 |
| IFM/K2-Horizon-0.9B | 1.1B | 2 GB | fits-bf16 | 45 | 11,955 |

Also new with known verdicts, outside the battery's scope: deepseek-ai/DeepSeek-V4.1-Flash
(763.2B, api-only, trend **1228** — the night's flagship, 6 downloads / 1,277 likes),
deepseek-ai/DeepSeek-V4-Flash-Vision-Exp (304.6B, fits-with-cpu-offload, 400,892 downloads),
dealignai/GLM-5.3-CYBERSECURITY-FP8 (753.3B, api-only), nvidia NVFP4 repacks of
Qwen3.8-Flash-Next and GLM-5.3-Flash (both fits-quantized), inclusionAI's Ling-3.0-flash pair
(both fits-quantized), Jackrong/Qwopus3.8-27B-Flash (27.8B fits-bf16 but charts
`image-text-to-text`), Qwen/Qwen-Drive-1.0-4B (vision), and a spread of TTS/audio/image models.

**Observations, unverified beyond the API response:**

- 43 of the 70 new entries report `unknown` fit — the GGUF blind spot now owns the majority of
  a large diff, and tonight includes its two biggest-download cases yet:
  ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF (trend 532, **614,850** downloads) and DavidAU's
  TURBO-Fable-Cold-Fusion MTP GGUF (trend 287, 517,644 downloads). The file-size-parsing fix
  from the 08-15 TODO remains the single highest-value harness improvement.
- medismera/Qwen3.8-27B-OBLITERATED-Mythos-Class-Agentic reuses OBLITERATUS's exact
  "OBLITERATED" branding on the same 27B base that is installed here as the Q8_0 — but it is a
  different org's repo, not the same weights. Same ruling as every prior variant: does not
  qualify as "already installed." That 27B base is now at least eight distinct
  uncensored/agentic variants across the log.
- DeepSeek-V4.1-Flash has the fresh-upload signature (6 downloads / 1,277 likes) and charts
  under `image-text-to-text`. Its Vision-Exp sibling at 304.6B is the same cpu-offload class as
  the 08-15 DeepSeek-V4-Flash run, which needed llama.cpp `--n-cpu-moe` — a path the harness
  still lacks (open TODO).
- Three new model families cluster the diff: IFM's K2-Horizon (four repos: 36B-A4B MoE + GGUF,
  7B, 0.9B), XHToken's Spark-X2.5 (4B, 1.7B, + GGUF), and inclusionAI's Ling/LLaDA line (six
  repos). The K2-Horizon MoVA 36B-A4B (~4B active, if the A4B suffix reads like Ornith's A3B
  did) plus MiniCPM5-2B at trend 915 / 42K downloads look like the strongest battery targets.
- The 13-day gap pulls established repos into the diff as trending-window artifacts:
  openai-community/gpt2 (14.98M downloads), meta-llama/Llama-3.1-8B-Instruct (5.6M),
  RunDiffusion/Juggernaut-XL-v9 (851K), cagliostrolab/animagine-xl-4.0 (329K), and
  stable-video-diffusion-img2vid-xt-1-1. None are new releases; all excluded from the
  candidate table.
- dealignai/GLM-5.3-CYBERSECURITY-FP8 is a full-size (753.3B) GLM-5.3 repack with a
  domain-specific name and 24,303 downloads. Model card not read; api-only for this box
  regardless.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).

## 2026-08-28 — nightly discovery (automated run)

Discovery only: 150 trending models polled, **14 new** since yesterday. Checked against
`ollama list` — no new trending model is already installed (the trending
`orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF` shares a naming family with installed Qwen3.8
builds but is a finetune of a different base — Flash-Next, not the 27B — so it does not qualify),
and auto-download remains an open TODO, so no battery ran.

New models with a known fit verdict:

| Model | Pipeline | Params | BF16 | Verdict | Trend | Downloads |
|---|---|---|---|---|---|---|
| zai-org/GLM-5.3 | text-generation | 753.3B | 1403.2 GB | api-only | 1104 | 0 |
| tencent/Hy4-preview | text-generation | 780B | 1452.8 GB | api-only | 245 | 0 |
| incoai/GLM-5.3-Flash-DFlash2 | text-generation | 1.2B | 2.2 GB | fits-bf16 | 80 | 0 |
| Qwen/Qwen3-TTS-12Hz-0.6B-Base | text-to-speech | 0.9B | 1.7 GB | fits-bf16 | 5 | 482,655 |
| Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice | text-to-speech | 0.9B | 1.7 GB | fits-bf16 | 5 | 1,229,264 |
| OpenMOSS-Team/MOSS-TTS-v1.5 | text-to-speech | 8.5B | 15.8 GB | fits-bf16 | 5 | 372,105 |
| OpenMOSS-Team/MOSS-SoundEffect | text-to-audio | 8.4B | 15.6 GB | fits-bf16 | 1 | 767 |

The other seven report `unknown` fit: orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF (trend 71),
unsloth/GLM-5.3-GGUF (trend 49), sakils123/Anima-Control-Pose, RuneXX/Minimax-H3-Workflows,
Zyphra/ZONOS2, Boombaaa/PORNHUBAI, tencent/HunyuanVideo-Foley.

**Observations, unverified beyond the API response:**

- Second flagship night in three days: zai-org/GLM-5.3 tops the diff at trend 1104 — the full
  successor to GLM-5.3-Flash, which charted 08-26 at 906. At 753.3B it is api-only for this box,
  a class above even the cpu-offload tier. 0 downloads / 1,137 likes is the fresh-upload
  signature. Its same-day unsloth GGUF mirror reports `unknown` — the GGUF fit-triage blind spot,
  again on the night's biggest release, same as Flash-Next and GLM-5.3-Flash on 08-26.
- tencent/Hy4-preview (780B, api-only, 0 downloads / 247 likes) is a second frontier-scale fresh
  upload the same night. Neither flagship is runnable here at any quant that exists today.
- incoai/GLM-5.3-Flash-DFlash2 is the night's only text-generation model that fits — but at 1.2B
  with a "DFlash2" suffix it looks like a speculative-decoding draft model for GLM-5.3-Flash
  (same naming pattern as the installed `muse-glimmer:30b-bf16-dflash`), not a standalone chat
  model. Model card not read; if that reading is right, benchmarking it alone would be
  meaningless — it only matters paired with a GLM-5.3-Flash quant this box can't hold in VRAM.
- orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF extends orcarouter's uncensored line (27B
  variants on 08-21/08-23) to the Flash-Next flagship from 08-26. GGUF blind spot again, and it
  charts under `image-text-to-text`, the recurring pipeline-tag oddity.
- The two Qwen3-TTS-12Hz repos (1.2M and 482K downloads against trend 5) and likely
  HunyuanVideo-Foley are established releases drifting into the trending window, not launches —
  same diff-artifact pattern as musicgen-medium (08-23) and suno/bark (08-25).
- sakils123/Anima-Control-Pose repeats the exact repo name of Claquasse/Anima-Control-Pose
  (charted 08-22) under a different user — looks like a re-upload/copy; not investigated.
- Zero net-new battery candidates tonight once the DFlash2 draft-model reading is applied: the
  fits-bf16 crop is otherwise entirely TTS/audio, out of scope for the text-generation battery.

Nothing pulled, nothing benchmarked, `state/seen.json` updated (gitignored).
