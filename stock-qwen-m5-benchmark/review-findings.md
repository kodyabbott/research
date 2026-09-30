# Adversarial review: stock-qwen-m5-benchmark

Reviewed 2026-09-30 by the adversarial-reviewer agent (Claude Code, Opus 5).

**Files read.** `README.md` (103 lines, md5 `ed2e2954e96fa37368e480859f1c4602`), `notes.md` (42 lines),
`runs/*.json` (4 records), `../CLAUDE.md`, `.claude/rules/{research-workflow,source-rules}.md`,
`../uncensored-models-m5-benchmark/{README.md,bench.py,run_thinking.sh,runs/*.json}` (11 records),
`../mac-model-benchmarks/README.md`, `../local-model-benchmarks/{nightly.py,policy.json,runs/20260911-104941-c75692e6.json}`,
the repo `README.md`, and the private server log at
`~/Documents/Codex/model-cache/stock-qwen-benchmark/logs/server.log`.

**Method.** Every number in both Results tables and the comparison table was recomputed from the raw
`cases[]` arrays, not read from the summary blocks. Four external URLs were fetched to check cited
claims. Line numbers below refer to the README as of the md5 above.

**Note on timing.** The README and notes.md were revised on disk during this review. Several findings
from my first pass were fixed by that revision; they are recorded in "Already fixed" at the bottom so
the fixes do not get re-opened. Everything in Critical / Important / Minor is against the current file.

No research file was modified. Nothing was committed. No request was sent to 127.0.0.1:11434 or :11436.
`../coding-benchmark-harness/` was not touched (existence checked only, for the link at line 49).

---

## Critical -- fix before publishing

### C1. "matched the Sep 27 Heretic build exactly" is false at case level (line 10)

> "The stock 27B matched the Sep 27 Heretic build exactly in both modes (8/24 and 24/24)"

The totals match. The cases do not. Recomputed from the first 24 entries of
`../uncensored-models-m5-benchmark/runs/20260927-qwen3.8-27b-heretic-llmfan46.json` against
`runs/20260929-qwen3.8-27b-q8_0-stock-off.json`:

| Category (thinking off, first 24) | Heretic Q8_0 | Stock Q8_0 |
|---|---:|---:|
| shortest-path | 1/3 | **2/3** |
| record-extraction | 3/3 | **2/3** |
| other six | identical | identical |

Two cases flipped in opposite directions and cancelled to 8. Anyone who opens both records finds this in
two minutes, and "exactly" is the word that makes it a catch rather than a footnote. Line 42 already has
the right phrasing available ("the thinking-off score is unchanged"); use that in the headline, or state
the two-case difference.

This also cuts against the inference in the same sentence. Two cases moving in opposite directions
between builds is the signature of noise, which is the honest reading -- and it is the reading the Sep 27
sibling committed to in print: *"A one- or two-case difference with one sample per case is not a measured
effect in either direction"* (`../uncensored-models-m5-benchmark/README.md`, "Did uncensoring cost
capability?").

### C2. The headline states three conclusions the evidence cannot carry (line 10)

> "**Result: both stock models are capable here, and Flash-Next is the better pick.** … so on this suite
> the uncensoring cost nothing and there is no reason to prefer the uncensored build for capability."

- **"capable"** is never defined anywhere in the report. The measured thinking-off scores are 8/24 (33%)
  and 9/24 (38%). The word rests entirely on the thinking-on rows, which sit at the suite ceiling -- and
  line 42 concedes *"thinking on is at the suite ceiling for all three, so this suite cannot rank them."*
  A conclusion drawn from a saturated metric is not a measurement. State what was measured: both models
  solve all 24 cases with thinking on, and the suite has no headroom above that.
- **"the better pick"** is a purchase recommendation resting on speed alone, in a report that says at
  line 49 the screen "is not a coding benchmark or a general ranking." It also drops everything on the
  other side of the ledger, all of it present in this report's own text: 90 GB vs 29 GB on disk, 3-bit vs
  Q8_0, a GGUF that declares `requires 0.35.0` against a 0.34.4 server, a manual sharded import because
  `ollama pull` returns HTTP 400, and ~110 GiB of resident buffers on a 128 GiB machine. If a "pick" is
  wanted, condition it: faster for interactive use, at 3-bit and on an unsupported runtime version.
- **"the uncensoring cost nothing"** is absence of evidence presented as evidence of absence, and C1
  shows the underlying match is not even exact. Line 42's *"it does show no capability loss … at this
  resolution"* has the same problem in softer form: at 0/3 floors and 3/3 ceilings the suite cannot
  *show* no loss, only fail to detect one.

Aggravating: line 63 now discloses that the 27B thinking-on pass finished `ledger-0` 4.7 s inside the
120 s deadline and that a timeout would have made the row 23/24. A headline that says two models "both
solved all 24 cases" and "matched exactly" while the Method section says the result was 4.7 seconds from
23/24 is a report arguing with itself. The fragility belongs in the headline paragraph, not only at
line 63.

Related, same root cause -- **line 59: "Low-bit quality loss is one of the things this run measures."**
It does not. Both modes are at floor or ceiling, and line 42 says so explicitly. This run established
that 3-bit Flash-Next is not *catastrophically* degraded on 24 easy-with-reasoning cases. Say that.

---

## Important -- should fix

### I1. The headline tok/s figure is from a different workload than the sentence it sits in (line 10)

> "Flash-Next did it in 8.7 minutes at about 49 tok/s; the dense 27B took 19.2 minutes at about 18 tok/s,
> so Flash-Next generates 2.7x faster"

The wall times are the workload's `totalWallMs` (correct). The rates are from the throughput battery, a
different workload. The workload's own rates are in the records and in notes line 37:

| Run | `workloadSummary.medianGenTokPerSec` | `throughput.summary.medianGenTokPerSec` |
|---|---:|---:|
| Flash-Next, thinking on | **46.85** | 49.05 |
| 27B Q8_0, thinking on | **18.20** | 18.04 |

Same-basis ratios: workload/workload = 46.85 / 18.20 = **2.57x**; battery/battery = 49.05 / 18.04 =
**2.72x**. The README quotes the higher ratio while describing the pass that produced the lower one.
notes line 37 records 46.8 correctly, so the report already knows. The 2.2x wall-time ratio is right
(1,154,935.7 / 520,170.4 = 2.220). Fix: say "2.6x on the pass" or attribute 2.7x to the battery. Note
that the repo `README.md` line 29 already advertises "Flash-Next 2.7x faster" and inherits whichever
number you land on.

### I2. "same as the Sep 27 thinking-on rows" (line 32) points at rows that do not exist

The footnote normalizes the truncated short-generation trials by citing precedent. There is none. Across
all eleven Sep 27 records, `throughput.summary` is `null` for every run with a thinking mode
(`…-27b-heretic-llmfan46-think.json`, `…-think96.json`, `…qwen3.6-35b-a3b-hauhaucs-think.json`,
`…gemma4-31b-heretic-llmfan46-think.json`) because `run_thinking.sh` line 12 passes `--modes workload`
only. The Sep 27 README's thinking-on table has no tok/s or short-response columns at all. The only
Sep 27 record anywhere with `anyTruncated: true` is
`20260927-gpt-oss-120b-hauhaucs-INVALID-attempt1.json`, which that report discarded as invalid; the valid
GPT-OSS low-reasoning run has `anyTruncated: false`.

Citing a nonexistent prior result to make an anomaly look routine is more corrosive than the anomaly.
Replace it with the mechanism, which is real and documented: thinking tokens count against `num_predict`
(`bench.py` line 110 comment).

### I3. The Windows comparison row is mislabelled (line 40)

> "Stock BF16, Windows RTX PRO 6000, Ollama 0.32.13 | on | 24 | 946.5"

`../local-model-benchmarks/runs/20260911-104941-c75692e6.json`, `benchmarks[0]`:
`model` = **`qwen3.8:27b-mtp-bf16`**, `details.parent_model` = `qwen3.8:27b-bf16`, and `modelParameters`
includes `draft_num_predict 4`. This is a locally derived MTP / speculative-decoding variant, not the
plain registry BF16 tag. "Stock BF16" hides that. Add the tag.

Verified correct in that row: `passed` 24/24, `first24` 24, median `eval_count` **946.5**,
`protocol.suiteSha256` `d262c793…` (same suite), `caseDeadlineSeconds` 120 (same as today),
`runtime.version` 0.32.13. Sampling is also matched, though not by the record -- the record stores no
per-case options; `nightly.py` lines 530-532 build them from `policy.json` (`temperature 0`, `seed 42`,
`numCtx 8192`) plus hardcoded `top_p=1, top_k=40, repeat_penalty=1.0`, with `sampling_profile` defaulting
to `None`. See V8 below for the empirical confirmation, which is stronger than the code.

### I4. notes.md line 33 understates the Flash-Next KV cache by 8x

notes line 33: *"KV cache 24 MiB for 8192 cells over 12 attention layers plus a 112.6 MiB recurrent state
over 48 layers."*

`server.log` lines 5531-5539 show three separate allocations:

```
llama_kv_cache:       MTL0 KV buffer size =   192.00 MiB
llama_kv_cache: size =  192.00 MiB ( 8192 cells, 12 layers, 1/1 seqs), K (f16): 96.00 MiB, V (f16): 96.00 MiB
llama_memory_recurrent:       MTL0 RS buffer size =   112.57 MiB
operator(): creating indexer KV cache, size = 8192 cells
llama_kv_cache:       MTL0 KV buffer size =    24.00 MiB
```

The 24 MiB figure is the **indexer** KV cache. The main KV cache is **192 MiB**, and the notes omit it.
Actual KV-side total is ~329 MiB, not ~137 MiB. This is the datum behind the quantization choice at
line 59 ("leaves too little of the 128 GB for KV cache"), so the trail should have it right even though
the README does not quote a KV number.

### I5. Reproduce underestimates peak disk by ~90 GB (line 73)

> "about 120 GB free"

Lines 82-88 download the three shards to `$S/hf/…` (89,986,353,824 B ≈ 90 GB) and then `ollama create`
copies them into the dedicated blob store (`artifact.size` in the records = 89,986,353,967 B). Nothing in
the block removes the HF download. Add the 29 GB 27B pull and peak requirement is roughly **210 GB**.
notes line 38 corroborates the store side alone at "about 118 GB." Either raise the figure or add an
`rm -rf $S/hf/Qwen3.8-Flash-Next-GGUF` after the create.

### I6. "no download or import overlapped a timed pass" is asserted, not shown (line 65)

`runs/20260929-qwen3.8-27b-q8_0-stock-off.json`: `startedAt` = `2026-09-29T23:51:06-06:00`. The manifest
for the 90 GB Flash-Next import, `artifact.modified_at`, is
`2026-09-29T23:51:06.780143156-06:00` -- the same second. First inference was 6 s later (warmup
`created_at` `05:51:12Z`) and the first throughput trial 13 s later (`05:51:19Z`). So the true separation
between a 90 GB copy completing and the first timed token is **6-13 seconds**, with SSD writeback
plausibly still in flight. That pass produced the 118 s wall time and the 18.83 tok/s figure the entire
speed comparison is anchored to. State the separation instead of asserting none; notes line 21's "after
the create finished, so no download or copy overlaps the timed passes" needs the same treatment.

### I7. The load-buffer and template evidence is not reachable by a reader (lines 47-48)

Both caveats cite "the server log" with no path. That log lives at
`~/Documents/Codex/model-cache/stock-qwen-benchmark/logs/server.log`, outside the repository, and is the
*only* evidence in the report that a published reader cannot check -- everything else resolves to a run
record, a repo file, or a URL. I read it and both claims verify exactly (see V6, V7). Per
`.claude/rules/source-rules.md` every claim needs "a URL, file path with line number, or paper citation."
Quote the path and line numbers in notes.md, or commit the ~15-line load excerpt (well inside the 2 MB
binary limit in `../CLAUDE.md`).

---

## Minor -- nice to fix

- **M1. The "--" at line 39 is fillable.** Heretic thinking-off median `eval_count` over the first 24
  cases is **49.0** (its 96-case summary reports 50.0). A dash in a column where the other rows carry
  63.5 and 946.5 invites "why is this one missing?"
- **M2. Precision inconsistency in the same column** (line 39). Heretic's
  `workloadSummary.medianOutputTokens` is **864.5**, printed as "865", beside cells printed as 63.5 and
  946.5. Use 864.5.
- **M3. "off / on" beside "8 / 24"** (lines 38-39) under a column headed "First 24" reads as "8 out of
  24" on first pass. Split the rows.
- **M4. Quote truncated mid-sentence without an ellipsis** (line 57). The card reads *"This experimental
  preview of the architecture that will underpin Qwen4 is built around a fundamental rethinking of how
  the core components of modern large language models (LLMs) interact at scale."* The README renders
  `"this experimental preview of the architecture that will underpin Qwen4"` -- lowercased initial, no
  ellipsis. Content is faithful; `source-rules.md` wants verbatim.
- **M5. "model cards recommend sampling" is uncited and pluralized** (line 49). It is true -- the
  Flash-Next card lists temperature 1.0 / top_p 0.95 / top_k 20 / min_p 0.0, and the 27B record's
  `parameters` field shows `temperature 1, top_k 20, top_p 0.95` -- but the Sep 27 sibling cited it
  properly ("the Qwen3.8 card: …"). Name one card.
- **M6. Host core counts are uncited** (line 8, notes line 3): "18 CPU / 40 GPU cores". The records only
  capture `hostBefore.chip` = `Apple M5 Max`; `memoryBytes` = 137,438,953,472 supports the memory figure.
  The core counts match `../mac-model-benchmarks/README.md` line 8, which looks like the actual source.
- **M7. Line 47 omits one of the four load buffers.** `server.log` line 5500 also shows
  `CPU_Mapped model buffer size = 644.14 MiB`. Small, but the sentence reads as an exhaustive list.
- **M8. The effective output budget caveat was dropped.** Line 63 says "8,192 context … 8,192 with
  thinking on"; prompts reach 2,069 tokens (27B) and 2,109 (Flash-Next), so real generation headroom is
  ~6,100. The Sep 27 report spelled this out: "the effective output budget is 8,192 minus the prompt."
- **M9. Banner deviates from the template.** `../CLAUDE.md` line 21 specifies "Claude Fable 5"; line 5
  says "Claude Fable 5.1". Repo-wide the string is already inconsistent (root README line 7 "currently
  Claude Fable 5"; Sep 27 report "Claude Opus 5.5"; Sep 22 report names "Codex (OpenAI)" and drops the
  template sentence). Out of scope here, but template and reports should converge.
- **M10. No `session-urls.md` in this folder.** `research-workflow.md` step 7 runs the url-auditor and
  the Sep 27 sibling ships one. This report cites nine external URLs and has no coverage file.
- **M11. notes.md date heading mismatch.** The `## 2026-09-30` heading (line 27) is followed immediately
  by entries timestamped "23:51-23:54 MDT (Sep 29)" (line 29) and "23:54-00:15" (line 30).
- **M12. notes.md line 37 still mixes wall-time bases** -- "8.7 minutes total (27B Q8_0: 21.6 minutes)"
  compares workload-only against a full-run span. Line 39 corrects it for the README but leaves the
  parenthetical standing.
- **M13. Pre-empt the `eval_count` = 2048 question.** `ledger-0` in the 27B thinking-on run reports
  exactly 2048 with `done_reason: "stop"` and `truncated: false`, under a `num_predict` of 8192. It is
  not a hidden cap, and V8 below explains it -- but it is the first thing a skeptic will accuse you of,
  and one sentence closes it.

---

## Verified correct -- recomputed from the raw records, do not re-litigate

- **V1. Pass counts and all 32 category cells** (lines 18-21): 8/24, 24/24, 9/24, 24/24 reproduce from
  `cases[]` and match `workloadSummary.byCategory`.
- **V2. Median generated tokens**: 63.5 / 903 / 34.5 / 747 from `eval_count` medians. Flash-Next
  thinking-on min 146 / max 2,473, matching notes line 37.
- **V3. Wall times**: 118,128.3 ms → 118 s; 1,154,935.7 → 19.2 min; 40,922.0 → 41 s; 520,170.4 →
  8.7 min. Each equals the sum of per-case `supervisedWallMs`, so line 14's definition is accurate. The
  "21.6 minutes" in notes line 30 is the `startedAt`→`finishedAt` span (23:54:12 → 00:15:51), correctly
  reconciled in notes line 39.
- **V4. Throughput battery** (lines 27-30): 18.83 / 18.04 / 50.05 / 49.05 gen tok/s, 557 / 578 / 978 /
  897 ingest tok/s, 7.6 / 28.7 / 3.0 / 10.7 s short response, 3/3 exact checks -- all match
  `throughput.summary`. The min/max ranges in notes lines 29, 36, 37 also match. Line 32's
  `eval_count / eval_duration` basis reproduces the per-case medians (18.302, 18.197, 50.168, 46.846).
- **V5. Protocol and integrity**: `options` = `{num_ctx 8192, temperature 0, seed 42, top_p 1, top_k 40,
  repeat_penalty 1.0}` with `num_predict` 2048 (off) / 8192 (on), `optionOverrides: {}`;
  `truncated: 0`, `errors: 0`, `unexpectedThinking: 0`, `done_reason: "stop"` on all 96 cases;
  `unload.confirmed: true` on all four; `runtime.version` = `0.34.4` throughout. `caseSliceSha256`
  `bbd9fc96…` equals the Sep 27 thinking-on record's `suiteSha256`, and `suiteSha256` `d262c793…` is
  shared with the Sep 27 96-case runs and the Sep 11 Windows run, so the case slice is identical.
  `sourceHashes` are byte-identical across all seven records (`quality_screen.py` `4a2ee19b…`,
  `workload_suite.py` `73dc9cdf…`, `nightly.py` `15a2c000…`, `api_probe.py` `903d9f51…`), so grading did
  not drift. `shasum -a 256` of `bench.py` = `3c45e7cc…`, matching `runnerSha256` in all four records and
  the claim at line 63.
- **V6. Line 47 verified against `server.log`.** Lines 5496-5503:
  `add: tensor per_layer_token_embd.weight (size = 27465 MiB) lazy read enabled`;
  `offloaded 49/49 layers to GPU`; `MTL0_Mapped … 47667.72 MiB`; `MTL0_Mapped … 38139.44 MiB`;
  `CPU_Mapped … 27465.95 MiB`. The two Metal buffers are byte-for-byte shards 2 and 3
  (49,983,253,824 B = 47,667.9 MiB; 39,992,153,376 B = 38,138.6 MiB), exactly as line 47 now says, and
  the arithmetic check holds: 27,465.95 MiB = 28.80 GB, and 51B weights at 4.5 bpw = 28.69 GB. The
  hedge ("an inference from the name and size … not a confirmed mapping") is correctly placed. To
  confirm it outright, `llama-gguf` on shard 2 would give the per-tensor listing -- llama.cpp is already
  installed per notes line 23.
- **V7. Line 48 verified against `server.log`** lines 5590 / 5954 / 8365: `msg="template selection"
  model=…qwen3.8-flash-next-ud-q3kxl:latest selected=gguf_chat_template renderer="" parser=""`. The 27B
  by contrast logs `selected=renderer_parser renderer=qwen3.8 parser=qwen3.5` (lines 337, 734, 3015),
  matching notes line 15.
- **V8. Q8_0 reproduces BF16 token-for-token -- the report's strongest unused evidence.** Comparing the
  27B thinking-on run against the Sep 11 Windows record case by case: **23 of 24 final answers are
  byte-identical** (the one exception, `ledger-2`, differs only in JSON whitespace and carries the same
  values), and **17 of 24 reasoning traces are byte-identical**, including `ledger-0`'s full 2,949
  characters at exactly 2,048 `eval_count` on both hosts. That is deterministic greedy decoding
  reproducing the same trajectory across Q8_0 and BF16, Ollama 0.34.4 and 0.32.13, Metal and Blackwell.
  It also empirically settles the sampling question in I3, and it explains M13. This is a far stronger
  argument that Q8_0 costs nothing than the ceiling-saturated pass counts at line 42, and the report
  does not use it.
- **V9. "Artifacts verified" (line 69) confirmed independently.** I fetched
  `https://huggingface.co/api/models/unsloth/Qwen3.8-Flash-Next-GGUF/tree/38bb39ee97821de2c9009abb7e93950eec396e66/UD-Q3_K_XL`;
  all three LFS sha256 oids and byte sizes match notes line 40 exactly (`f2ef4328…` 10,946,624 B;
  `7d230e7c…` 49,983,253,824 B; `21d4f90f…` 39,992,153,376 B). This is the best-sourced section of the
  report.
- **V10. The 0.35.0 caveat (line 46) confirmed.** The release page exists, is dated Sep 28, and lists
  exactly decision models via `/v1/systemone`, the settings-without-model-discovery fix, the macOS
  update-menu/icon fix, stalled MLX downloads, and deprecated `typical_p` now warning instead of failing.
  `qwen4exp` is not mentioned. "I cannot say what the requirement is for" is the right call.
- **V11. Model-card claims (line 57) confirmed** against
  `https://huggingface.co/Qwen/Qwen3.8-Flash-Next/raw/main/README.md`: "Number of Parameters: 125B with
  6B activated, plus 51B n-gram embedding and 4B MTP", license `qwen-community-1.0`, and
  "N-gram Embedding: 20,000,000 (bigrams/trigrams at layer 2)". Hub `createdAt` for that repo is
  `2026-08-24T08:24:59.000Z`, matching line 57; for `Qwen/Qwen3.8-27B` it is `2026-08-05T08:22:59.000Z`,
  matching line 56's revised "created Aug 5".
- **V12. Host state**: `memoryBytes` 137,438,953,472 (128 GiB); `os` `ProductVersion 27.0 /
  BuildVersion 26A428`; AC power, battery 100%, and no thermal or performance warning recorded, before
  and after all four passes. Swap was `total = 0.00M used = 0.00M` at all eight capture points -- worth
  surfacing in the README, since it is the strongest direct evidence for the "real headroom" claim at
  line 59 and is currently unused. One nuance on line 50: `pmset -g therm` also reports "No CPU power
  status has been recorded," i.e. it had no data, which is weaker than an observation of no throttling.
- **V13. Links**: `../mac-model-benchmarks/`, `../uncensored-models-m5-benchmark/`,
  `../uncensored-models-m5-benchmark/bench.py`, `../coding-benchmark-harness/`,
  `../local-model-benchmarks/runs/20260911-104941-c75692e6.json`, `notes.md`, `runs/` all resolve.
- **V14. Voice**: no em dashes (`--` used throughout), no "the ask", no "I'd recommend", no corporate
  filler. First-person ownership is present and placed where it belongs ("I cannot say," "I did not use
  that figure," "I did not raise it," "not a confirmed mapping"). The hedges are specific rather than
  decorative. This does not read as generated filler. The failure mode here is not LLM voice; it is a
  confident summary paragraph sitting on top of carefully caveated body text.

---

## Already fixed during this review (recorded so it does not get re-opened)

The revision that landed mid-review resolved five findings from my first pass. All re-verified against
the current file:

1. **macOS version.** Previously "macOS 26.5" in README line 8 and notes line 3, contradicted by
   `hostBefore.os` in all four records (`ProductVersion 27.0 / BuildVersion 26A428`) and traceable to
   `../mac-model-benchmarks/README.md` line 8. Both now read "macOS 27.0 (26A428)". Correct.
2. **"Same runner and settings … unchanged."** Line 63 now discloses the 120 s vs 600 s per-case deadline
   (`workloadProtocol.caseDeadlineSeconds` 120 today vs 600 from `run_thinking.sh --case-seconds 600`),
   names the earlier runner revision `177c3fbe…`, reports the 4.7 s margin on `ledger-0` at 115.3 s, and
   flags `first24Comparable: false`. For the record, the counterfactual is worse than stated: the Sep 27
   Heretic run's own `ledger-0` took **135.8 s**, so under today's 120 s deadline that build would have
   scored **23/24** (`bench.py` lines 133-135, 146-149 make it a hard timeout; line 213 records the case
   as `passed: False`). Worth one clause at line 63, and it is the substance behind C1/C2.
3. **Load-buffer units and the n-gram hypothesis.** Previously "47.7 + 38.1 GB … 27.5 GB", which divided
   MiB by 1000. Line 47 now quotes MiB with correct decimal-GB conversions, names the actual tensor from
   the log, and drops the earlier use of `qwen4exp.ple.ngram_size = 3` as evidence for "3-bit" (that
   field is trigram order; the card's "bigrams/trigrams" line settles it). Verified in V6. My first-pass
   claim that the Metal buffers refute the hypothesis was wrong -- `CPU_Mapped`/`MTL0_Mapped` are mmap
   spans per file and backend, and the log names the tensor directly.
4. **Release dates.** Line 56 previously said "Aug 14, 2026" with no source, against a Hub `createdAt` of
   Aug 5. Now "Hub repo created Aug 5, last modified Aug 14, 2026". Verified in V11.
5. **89 GB vs 90 GB** for the same artifact in lines 57 and 59, and the missing URL for Ollama's library
   tag sizes at line 59. Both fixed. Also `notes.md` line 9 now carries an inline pointer to the 00:50
   correction, which is what `source-rules.md` asks for.

---

## What a skeptic goes after first, in order

1. **"Matched exactly" does not survive opening both records** (C1). Two categories differ; the totals
   cancel.
2. **"Capable" and "better pick" from a ceiling-saturated 24-case screen** (C2), in a report that says
   two lines later that the suite cannot rank the models.
3. **The headline says "both solved all 24 cases"; the Method section says it was 4.7 seconds from
   23/24** (C2). Those are the same document.
4. **"about 49 tok/s" for a pass that ran at 46.85** (I1), with your own notes file recording 46.8.
5. **"same as the Sep 27 thinking-on rows"** (I2) -- there are no such rows, and the only truncated
   Sep 27 battery is in a file that report marked INVALID.

The underlying decision worth defending in the text: `bench.py --case-limit` defaults to 96, the Sep 27
report had already shown this suite hits 24/24 and 96/96 with thinking on, and this run chose 24. That
guaranteed a ceiling result before the first token was generated. Either run the 96 and rank on something,
or say plainly that the capability question was answered at the ceiling and the only discriminating
measurement here is speed. V8 is the one place this run has real discriminating evidence, and it is
currently unreported.
