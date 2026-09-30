# Adversarial review: stock-qwen-m5-benchmark

Reviewed 2026-09-30 by the adversarial-reviewer agent (Claude Code, Opus 5). Files read fresh from disk:
`README.md` (103 lines), `notes.md` (42 lines), `runs/*.json` (4 records), plus `../CLAUDE.md`,
`.claude/rules/*.md`, `../uncensored-models-m5-benchmark/{README.md,bench.py,run_thinking.sh,runs/*.json}`,
`../mac-model-benchmarks/README.md`, `../local-model-benchmarks/runs/20260911-104941-c75692e6.json`,
and the repo `README.md`. Every number in both Results tables was recomputed from the raw case arrays.

No research file was modified. Nothing was committed. No request was sent to 127.0.0.1:11434 or :11436.
`../coding-benchmark-harness/` was not touched (existence checked only, for the link in README line 49).

---

## Critical -- fix before publishing

### C1. "matched the Sep 27 Heretic build exactly" is false at case level (README line 10)

README line 10: *"The stock 27B matched the Sep 27 Heretic build exactly in both modes (8/24 and 24/24)."*

The totals match. The cases do not. Recomputed from the first 24 cases of
`../uncensored-models-m5-benchmark/runs/20260927-qwen3.8-27b-heretic-llmfan46.json` against
`runs/20260929-qwen3.8-27b-q8_0-stock-off.json`:

| Category (thinking off, first 24) | Heretic Q8_0 | Stock Q8_0 |
|---|---:|---:|
| shortest-path | 1/3 | **2/3** |
| record-extraction | 3/3 | **2/3** |
| all six others | identical | identical |

Two cases flipped in opposite directions and cancelled. "Exactly" is the wrong word, and a skeptic who
opens both records finds it in two minutes. Either report the per-category comparison or say "scored the
same total, with two cases differing."

### C2. The headline's three load-bearing claims outrun the evidence (README line 10)

*"Result: both stock models are capable here, and Flash-Next is the better pick."*

- **"capable"** is never defined. The measured thinking-off scores are 8/24 (33%) and 9/24 (38%). The
  claim rests entirely on the thinking-on rows, which are at the suite ceiling -- and README line 42
  concedes *"this suite cannot rank them."* A conclusion drawn from a saturated metric is not a
  measurement. Say what was measured: both models solve all 24 cases with thinking on; the suite has no
  headroom above that.
- **"the better pick"** is a purchase recommendation built on speed alone, in a report whose own Caveats
  section says the screen "is not a coding benchmark or a general ranking" (line 49). It also silently
  discards everything on the other side of the ledger, all of it in this report's own text: 89 GB vs
  29 GB on disk, 3-bit vs Q8_0, a GGUF that declares `requires 0.35.0` against a 0.34.4 server, a manual
  sharded-GGUF import because `ollama pull` fails, and ~110 GiB of resident buffers on a 128 GiB machine.
- **"the uncensoring cost nothing"** is absence of evidence stated as evidence of absence. The Sep 27
  sibling report got this right in its own words: *"No capability loss is visible for either Heretic
  build, but this suite has little power to show one... A one- or two-case difference with one sample per
  case is not a measured effect in either direction"*
  (`../uncensored-models-m5-benchmark/README.md`, "Did uncensoring cost capability?"). This report
  regressed from a standard it had already met. Line 42 partly walks it back ("at this resolution"), but
  the bolded headline is what gets read and quoted -- and it is what the repo README line 29 now
  propagates.

### C3. "Same runner and settings as the Sep 27 report ... unchanged" is false (README line 63)

Two independent contradictions, both from the run records:

**(a) Per-case deadline differs 5x.** All four of today's runs carry
`workloadProtocol.caseDeadlineSeconds: 120` (bench.py default). The Sep 27 Heretic thinking-on run
carries `600`, set explicitly by `../uncensored-models-m5-benchmark/run_thinking.sh` line 12
(`--case-seconds 600`); the Sep 27 README states "600 s per case" in its thinking-on section. `bench.py`
lines 133-135 and 146-149 make this a hard timeout: a case that exceeds it raises, and line 213 records
it as `passed: False`.

This has teeth, not just pedantry:

| Case | Run | Wall | Deadline |
|---|---|---:|---:|
| `ledger-0` | stock 27B, thinking on (today) | **115.3 s** | 120 s |
| `ledger-0` | Heretic 27B, thinking on (Sep 27) | **135.8 s** | 600 s |

The stock 27B's 24/24 survived by 4.7 seconds on one case. Under today's own 120 s protocol the Heretic
build would have scored **23/24**, because its `ledger-0` took 135.8 s. So the report's comparison is
between a 24/24 earned under a tight deadline and a 24/24 earned under a loose one, presented as an exact
match (see C1) and used to conclude that uncensoring cost nothing (C2). Any rerun that lands 5% slower
turns the headline into 23/24. The Reproduce block (lines 90-97) omits `--case-seconds`, so it faithfully
reproduces today's 120 s -- and therefore cannot reproduce the Sep 27 row it is being compared to.

**(b) The runner binary is not the one that produced the compared rows.** `runnerSha256` per record:

| Run | runnerSha256 |
|---|---|
| Today, all four | `3c45e7cc1f99…` |
| Sep 27 Heretic, thinking off (the "8/24" row) | `96ec016a0a9d…` |
| Sep 27 Heretic, thinking on 24 (the "24/24" row) | `177c3fbeb61f…` |
| Sep 27 Heretic, thinking on 96 | `3c45e7cc1f99…` |

`shasum -a 256 ../uncensored-models-m5-benchmark/bench.py` = `3c45e7cc…`, so "unchanged" is true of the
file as it sits today, and false of the two Sep 27 rows in the comparison table (line 39). Proof the
logic actually changed: the Sep 27 thinking-on record has `first24Comparable: true` under `think=true`,
which the current code at bench.py line 117 cannot produce.

**Mitigating (state this, don't hide it):** the grader and suite did not drift. `sourceHashes` are
byte-identical across all seven records -- `quality_screen.py` `4a2ee19b…`, `workload_suite.py`
`73dc9cdf…`, `nightly.py` `15a2c000…`, `api_probe.py` `903d9f51…`. And `caseSliceSha256` `bbd9fc96…` in
today's records equals the `suiteSha256` field of the Sep 27 thinking-on record, confirming the same
24-case slice. So the scoring is comparable; the runner metadata and the deadline are not.

### C4. macOS version contradicts every run record (README line 8, notes line 3)

Both state **macOS 26.5**. All four records, `hostBefore.os.stdout` and `hostAfter.os.stdout`:

```
ProductName:		macOS
ProductVersion:		27.0
BuildVersion:		26A428
```

The report cites no source for 26.5. The string "macOS 26.5" appears verbatim in
`../mac-model-benchmarks/README.md` line 10 (Sep 22), which is where it looks like it came from. Either
the host OS changed between Sep 22 and Sep 29 and the report copied a stale figure, or `sw_vers` is
reporting something the author did not read. Either way the report contradicts its own primary evidence
on the very first line of the Results context. This is the single easiest thing for a skeptic to check
and the most damaging to find.

---

## Important -- should fix

### I1. Headline tok/s is the wrong measurement for the sentence it sits in (README line 10)

*"Flash-Next did it in 8.7 minutes at about 49 tok/s; the dense 27B took 19.2 minutes at about 18 tok/s,
so Flash-Next generates 2.7x faster."*

The wall times are the workload's `totalWallMs` (correct). The rates are from the throughput battery, a
different workload. The workload's own rates are in the records and in notes line 37:

| Run | `workloadSummary.medianGenTokPerSec` | `throughput.summary.medianGenTokPerSec` |
|---|---:|---:|
| Flash-Next, on | **46.85** | 49.05 |
| 27B Q8_0, on | **18.20** | 18.04 |

Same-basis ratios: workload/workload = 46.85 / 18.20 = **2.57x**. Battery/battery = 49.05 / 18.04 =
**2.72x**. The README quotes the higher one while describing the pass that produced the lower one. Notes
line 37 records 46.8 correctly, so the report knows better. Wall-time ratio 1,154,935.7 / 520,170.4 =
2.220 → "2.2x" is correct. Fix: either say "2.6x on the pass" or state that 2.7x is the battery figure.
The repo README line 29 already carries "2.7x faster" and inherits the same problem.

### I2. "same as the Sep 27 thinking-on rows" cites rows that do not exist (README line 32; notes line 30)

The footnote normalizes the truncated short-generation trials by pointing at prior results. There are
none. Across all eleven Sep 27 records, `throughput.summary` is `null` for every run with a thinking mode
(`20260927-qwen3.8-27b-heretic-llmfan46-think.json`, `-think96.json`,
`20260927-qwen3.6-35b-a3b-hauhaucs-think.json`, `20260927-gemma4-31b-heretic-llmfan46-think.json`) --
`run_thinking.sh` line 12 passes `--modes workload` only. The Sep 27 README's thinking-on table has no
tok/s or short-response columns at all. The only Sep 27 record with `anyTruncated: true` is
`20260927-gpt-oss-120b-hauhaucs-INVALID-attempt1.json`, which that report discarded as invalid; the valid
GPT-OSS low-reasoning run has `anyTruncated: false`. Citing a nonexistent precedent to make an anomaly
look routine is the kind of thing that destroys trust in the rest of the numbers. Drop the parenthetical
or replace it with the mechanism (thinking tokens count against `num_predict`, bench.py line 110).

### I3. Buffer sizes are wrong by ~7%, and the arithmetic refutes the stated hypothesis (README line 47)

*"Flash-Next loaded as 47.7 + 38.1 GB Metal buffers plus a 27.5 GB CPU-mapped buffer (server log). I
believe the CPU buffer is the 3-bit n-gram embedding table (`qwen4exp.ple.ngram_size = 3`)…"*

notes line 33 records the log values as **MiB**: 47,668 MiB + 38,139 MiB + 27,466 MiB. The README divided
by 1000 and relabelled them GB. Correct conversions:

| Log value | README | GiB | GB (decimal) |
|---|---|---:|---:|
| 47,668 MiB | 47.7 GB | 46.55 | **49.98** |
| 38,139 MiB | 38.1 GB | 37.24 | **39.99** |
| 27,466 MiB | 27.5 GB | 26.82 | **28.80** |

A reader also spots the internal inconsistency unaided: 47.7 + 38.1 = 85.8 "GB" for a model the same
README calls 89 GB (line 57) and 90 GB (line 59).

Worse, the corrected numbers kill the hypothesis. The two Metal buffers are **exactly** shards 2 and 3 of
the GGUF: 49,983,253,824 B = 47,667.9 MiB and 39,992,153,376 B = 38,138.6 MiB (digests and sizes in
notes line 40, independently confirmed against the pinned HF tree below). Combined with the same log
line's `offloaded 49/49 layers to GPU`, every weight tensor -- n-gram embedding table included, since it
lives inside those shards -- is resident on the GPU. The 27 GiB CPU-mapped buffer therefore cannot be the
n-gram table without double-counting it. The hedge ("I have not confirmed which tensors it holds") keeps
this out of Critical, but the report should either drop the guess or note that the Metal buffers already
account for the whole file.

Second problem in the same sentence: `qwen4exp.ple.ngram_size = 3` is the **n-gram order**, not a bit
width. The Qwen model card confirms it: *"N-gram Embedding: 20,000,000 (bigrams/trigrams at layer 2)."*
Citing a trigram-order field as evidence for a "3-bit" table is a metadata misreading used as a source.

### I4. Qwen3.8-27B release date is unsourced and wrong (README line 56)

*"Qwen3.8-27B (dense, Aug 14, 2026)"*. `notes.md` contains no record of checking this date. The Hub API
for `Qwen/Qwen3.8-27B` returns `createdAt` **2026-08-05T08:22:59.000Z** (fetched during this review). The
Flash-Next date on the same line is fine: the card's repo returns `createdAt`
2026-08-24T08:24:59.000Z, matching the README's "Aug 24, 2026 per the Hub `created_at`" -- though that
check is likewise absent from notes.md, so the trail does not support either date. Per
`.claude/rules/source-rules.md` both need a URL or a record field.

### I5. The Windows comparison row is mislabelled and not settings-matched (README line 40)

Row: *"Stock BF16, Windows RTX PRO 6000, Ollama 0.32.13 | on | 24 | 946.5."*

From `../local-model-benchmarks/runs/20260911-104941-c75692e6.json`:

- `benchmarks[0].model` = **`qwen3.8:27b-mtp-bf16`**, `details.parent_model` = `qwen3.8:27b-bf16`,
  `modelParameters` includes `draft_num_predict 4`. This is a locally derived MTP/speculative-decoding
  variant, not the plain registry BF16 tag. Calling it "Stock BF16" hides that.
- The record stores **no per-case request options** -- no `temperature`, `seed`, `top_p`, `top_k` appears
  anywhere in the file. `modelParameters` shows the model's own defaults as `temperature 1, top_k 20,
  top_p 0.95`. So the report cannot establish that this row used the greedy temperature-0 decoding of
  today's runs. Given README line 49 explicitly warns that greedy decoding departs from the recommended
  sampling settings, a row that may have used sampling is not comparable on median token counts.

Verified correct: `passed` 24/24, `first24` 24, median `eval_count` **946.5**, `protocol.suiteSha256`
`d262c793…` (same suite), `protocol.caseDeadlineSeconds` 120, `runtime.version` 0.32.13. Add the MTP
label and a settings caveat; the numbers themselves hold.

### I6. Reproduce underestimates disk by ~90 GB (README line 73)

*"Requirements: … about 120 GB free."* The procedure in lines 82-88 downloads the three shards to
`$S/hf/…` (89,986,353,824 B ≈ 90 GB) and then `ollama create` copies them into the dedicated blob store
(notes line 20: the created model is 89 GB; `artifact.size` in the records is 89,986,353,967 B). Nothing
in the block deletes the HF download. Add the 29 GB 27B pull and the peak requirement is roughly
**210 GB**, not 120. notes line 38 corroborates: the store alone "holds both models (about 118 GB)."
Either raise the figure or add an `rm -rf $S/hf/…` step after the create.

### I7. Timed pass starts in the same second the 90 GB import finished (README line 65)

*"no download or import overlapped a timed pass."* From `runs/20260929-qwen3.8-27b-q8_0-stock-off.json`:
`startedAt` = `2026-09-29T23:51:06-06:00`, and `artifact.modified_at` for the Flash-Next model created
minutes earlier = `2026-09-29T23:51:06.780143156-06:00`. The manifest for the 90 GB import was written in
the same second the first timed pass began. notes line 21 asserts the create "finished" first, but at
this resolution the ordering is unresolvable and SSD writeback from a 90 GB copy plausibly continued into
the pass. That pass produced the 118 s wall time and the 18.83 tok/s baseline that the whole speed
comparison is anchored to. State the actual separation instead of asserting none.

### I8. notes.md line 9 cites a source it could not read

*"Qwen3.8-Flash-Next is described by Qwen as the first open-weight release of the Qwen 4 architecture
([Qwen blog](https://qwen.ai/blog?id=qwen3.8-flash-next))."* notes line 42 later retracts exactly this:
*"that wording came from a search-result summary, and the Qwen blog page did not render for me."* A
running log may keep its history, but `.claude/rules/source-rules.md` requires unverified claims to be
marked **TODO** at the point of the claim. As written, line 9 presents a blog URL as the source of a
paraphrase that was never read there, and the correction is 33 lines away. Add an inline pointer at
line 9. Same line: "Qwen 4 is not released… coming very soon" is sourced only to two third-party blogs
(orcarouter, yottalabs) for an Alibaba statement -- the rules call for the primary source or an explicit
"secondary" label.

---

## Minor -- nice to fix

- **M1. 89 GB vs 90 GB for the same artifact** (README line 57 "89 GB (three shards)" vs line 59
  "UD-Q3_K_XL at 90 GB"). `artifact.size` = 89,986,353,967 B = 90.0 GB decimal = 83.8 GiB. Pick one unit
  convention and use it in both places.
- **M2. The "--" in the comparison table is fillable** (README line 39). Heretic thinking-off median
  `eval_count` over the first 24 cases is **49.0** (the 96-case summary reports 50.0). Leaving a dash in a
  column where the other rows carry 63.5 and 946.5 invites the question "why is this one missing?"
- **M3. Precision inconsistency in the same column** (README line 39): Heretic median is **864.5** in
  `workloadSummary.medianOutputTokens`, printed as "865", while the neighbouring cells print 63.5 and
  946.5 to the half-token. Use 864.5.
- **M4. "off / on" and "8 / 24" in adjacent cells** (README lines 38-40) under a column headed "First 24"
  reads like "8 out of 24" on first pass. Split the rows or relabel.
- **M5. Quote is truncated mid-sentence without an ellipsis and with an altered initial capital**
  (README line 57). The card reads: *"This experimental preview of the architecture that will underpin
  Qwen4 is built around a fundamental rethinking of how the core components of modern large language
  models (LLMs) interact at scale."* The README renders `"this experimental preview of the architecture
  that will underpin Qwen4"`. Verified against
  `https://huggingface.co/Qwen/Qwen3.8-Flash-Next/raw/main/README.md` during this review. Content is
  faithful; `.claude/rules/source-rules.md` wants verbatim, so add the ellipsis.
- **M6. "model cards recommend sampling"** (README line 49) is uncited and pluralized. It is true --
  the Flash-Next card lists temperature 1.0 / top_p 0.95 / top_k 20 / min_p 0.0, and the 27B record's
  `parameters` field shows `temperature 1, top_k 20, top_p 0.95` -- but the Sep 27 sibling cited it
  properly ("the Qwen3.8 card: …"). Cite at least one card.
- **M7. Ollama library tag sizes have no source** (README line 59, notes line 10): "Ollama's own tags
  start at 105 GB (nvfp4/mlx) and 120 GB (q4_K_M)". No URL for the `qwen3.8-flash-next` library page.
- **M8. Host core counts are uncited** (README line 8, notes line 3): "18 CPU / 40 GPU cores". The
  records only capture `hostBefore.chip` = `Apple M5 Max`; `memoryBytes` = 137,438,953,472 (128 GiB)
  supports the memory figure. The core counts appear to be carried over from
  `../mac-model-benchmarks/README.md` line 10.
- **M9. Date heading mismatch in notes.md**: the `## 2026-09-30` heading (line 27) is immediately
  followed by entries timestamped "23:51-23:54 MDT (Sep 29)" (line 29) and "23:54-00:15" (line 30).
- **M10. notes line 37's parenthetical is the figure line 39 corrected**: "8.7 minutes total (27B Q8_0:
  21.6 minutes)" compares a workload-only wall time to a full-run span. Line 39 fixes it for the README
  but leaves line 37 mixing the two bases.
- **M11. `ledger-0` in the 27B thinking-on run reports `eval_count` exactly 2048 with
  `done_reason: "stop"` and `truncated: false`.** The request's `num_predict` was 8192, so this is a
  coincidence, not a hidden cap -- but it is the first thing a skeptic will accuse you of, and the same
  case hit exactly 2048 in the Sep 11 Windows run. One sentence pre-empts it.
- **M12. The effective output budget caveat was dropped.** README line 63 says "8,192 context, …8,192
  with thinking on"; prompts run to 2,069 tokens (27B) and 2,109 (Flash-Next), so the real generation
  headroom is ~6,100 tokens. The Sep 27 report spelled this out ("the effective output budget is 8,192
  minus the prompt").
- **M13. Banner deviates from the CLAUDE.md template.** `../CLAUDE.md` line 21 specifies "Claude
  Fable 5"; README line 5 says "Claude Fable 5.1". Repo-wide the string is already inconsistent (root
  README line 7 "currently Claude Fable 5"; Sep 27 report "Claude Opus 5.5"; Sep 22 report names
  "Codex (OpenAI)" and drops the template sentence entirely) -- out of scope here, but the template and
  the reports should converge.
- **M14. No `session-urls.md` in this folder.** `.claude/rules/research-workflow.md` step 7 runs the
  url-auditor and the Sep 27 sibling ships `session-urls.md`. This folder has none, and the report cites
  eight external URLs. Note also that `../README.md` line 29 is already updated for this project and
  repeats the 2.7x figure from I1.

---

## Verified correct (recomputed from the raw records -- do not re-litigate)

Every cell of both Results tables reproduces. Recount of `cases[]` in each record:

- **Pass counts and category breakdowns**: 8/24, 24/24, 9/24, 24/24 and all 32 category cells match
  `workloadSummary.byCategory` and the README table (lines 18-21).
- **Median generated tokens**: 63.5 / 903 / 34.5 / 747 from `eval_count` medians. Flash-Next thinking-on
  min 146 / max 2,473, matching notes line 37.
- **Wall times**: `totalWallMs` 118,128.3 ms → 118 s; 1,154,935.7 → 19.2 min; 40,922.0 → 41 s;
  520,170.4 → 8.7 min. All four equal the sum of per-case `supervisedWallMs`, so README line 14's
  definition is accurate. 21.6 min for the 27B (notes line 30) is the `startedAt`→`finishedAt` span
  (23:54:12 → 00:15:51), correctly reconciled in notes line 39.
- **Throughput battery**: 18.83 / 18.04 / 50.05 / 49.05 gen tok/s, 557 / 578 / 978 / 897 ingest tok/s,
  7.6 / 28.7 / 3.0 / 10.7 s short response, 3/3 exact checks -- all match
  `throughput.summary.{medianGenTokPerSec,medianPromptTokPerSec,medianShortWallMs,checksPassed}`. Min/max
  ranges in notes lines 29/36/37 also match.
- **Rate basis**: README line 32's `eval_count / eval_duration` claim reproduces the per-case medians
  (18.302, 18.197, 50.168, 46.846).
- **Truncation and errors**: `truncated: 0`, `errors: 0`, `unexpectedThinking: 0`, `done_reason: "stop"`
  on all 96 cases across the four runs; `unload.confirmed: true` on all four.
- **Options**: `{num_ctx 8192, temperature 0, seed 42, top_p 1, top_k 40, repeat_penalty 1.0}` with
  `num_predict` 2048 (off) / 8192 (on) and `optionOverrides: {}` -- README line 63 is accurate.
- **Runtime**: `runtime.version` = `0.34.4` in all four records.
- **Memory**: `hostBefore.memoryBytes` = 137,438,953,472 (128 GiB). Swap was
  `total = 0.00M used = 0.00M` before and after every pass -- worth surfacing, since it is the strongest
  evidence for the "real headroom" claim at line 59 and it is currently unused.
- **Thermals/power**: `pmset -g therm` shows no thermal or performance warning recorded, AC power,
  battery 100%, before and after all four passes (README line 50). One nuance: the field also says "No
  CPU power status has been recorded," i.e. pmset had no data, which is weaker than an observation of no
  throttling.
- **Artifacts verified (README line 69) -- confirmed independently.** I fetched
  `https://huggingface.co/api/models/unsloth/Qwen3.8-Flash-Next-GGUF/tree/38bb39ee97821de2c9009abb7e93950eec396e66/UD-Q3_K_XL`
  and all three LFS sha256 oids and byte sizes match notes line 40 exactly (`f2ef4328…` 10,946,624 B;
  `7d230e7c…` 49,983,253,824 B; `21d4f90f…` 39,992,153,376 B). This section is the strongest part of
  the report.
- **Ollama 0.35.0 caveat (README line 46) -- confirmed.** The release page exists, is dated Sep 28, and
  lists exactly decision models via `/v1/systemone`, the settings-without-model-discovery fix, the macOS
  update-menu/icon fix, stalled MLX downloads, and deprecated `typical_p` now warning instead of failing.
  `qwen4exp` is not mentioned. The README's characterization is accurate and the "I cannot say what the
  requirement is for" hedge is the right call.
- **Same 24 cases as the Sep 27 comparison.** `caseSliceSha256` `bbd9fc96…` in today's records equals
  the `suiteSha256` recorded by `20260927-qwen3.8-27b-heretic-llmfan46-think.json`, and `suiteSha256`
  `d262c793…` is shared with the Sep 27 96-case runs and the Sep 11 Windows run. Grader hashes
  (`quality_screen.py` `4a2ee19b…`, `workload_suite.py` `73dc9cdf…`) are identical across all seven
  records, so scoring did not drift (see C3 for what did).
- **Links**: `../mac-model-benchmarks/`, `../uncensored-models-m5-benchmark/`,
  `../uncensored-models-m5-benchmark/bench.py`, `../coding-benchmark-harness/`,
  `../local-model-benchmarks/runs/20260911-104941-c75692e6.json`, `notes.md`, `runs/` all resolve.
  `bench.py`'s on-disk sha256 matches the `runnerSha256` in all four of today's records.
- **Voice**: no em dashes, no "the ask", no "I'd recommend", no corporate filler. First-person ownership
  is present and used where it belongs ("I cannot say," "I did not use that figure," "I have not
  confirmed"). The hedges are specific rather than decorative. This does not read as generated filler.
  The failure mode here is not LLM voice -- it is a confident summary paragraph sitting on top of
  carefully caveated body text.

---

## What a skeptic goes after first, in order

1. **`sw_vers` says 27.0, your report says 26.5** (C4). One grep, and now every other host fact is
   suspect.
2. **"Matched exactly" doesn't survive opening both records** (C1). Two categories differ.
3. **"Same settings, unchanged" is refutable from the records themselves** (C3), and the 115.3 s case
   against a 120 s deadline means the headline 24/24 is one bad rerun away from 23/24.
4. **47.7 + 38.1 = 85.8, but you said the model is 89-90 GB** (I3). The unit error is visible without any
   external checking, and correcting it dismantles the n-gram-table hypothesis in the same paragraph.
5. **"about 49 tok/s" for a pass that ran at 46.85** (I1), with your own notes file recording 46.8.
6. **"capable" and "better pick" from a ceiling-saturated 24-case screen** (C2), in a report that admits
   two lines later that the suite cannot rank the models.

The underlying decision worth defending in the text: `bench.py --case-limit` defaults to 96, the Sep 27
report had already shown this suite hits 24/24 and 96/96 with thinking on, and this run chose 24. That
guaranteed a ceiling result before the first token was generated. Either run the 96 and rank on
something, or say plainly that the capability question was answered at the ceiling and the only
discriminating measurement here is speed.
