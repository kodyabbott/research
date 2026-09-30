# Source verification: stock-qwen-m5-benchmark

Run by the `source-verifier` agent (`.claude/agents/source-verifier.md`) against `README.md` and `notes.md` as read from disk on 2026-09-30. No research file was modified; this file is the only output.

Symbols follow the agent definition. ⚠️ is used for a quote or claim whose strength, scope, or units do not match the source, in addition to paraphrase-as-quote.

Primary sources used: the four records in `runs/`, the Sep 27 records in `../uncensored-models-m5-benchmark/runs/`, `../local-model-benchmarks/runs/20260911-104941-c75692e6.json`, the Ollama model store at `~/Documents/Codex/model-cache/stock-qwen-benchmark/` (manifests, config blobs, `logs/server.log`, `logs/pull.log`, smoke JSON), the Hugging Face tree and model APIs, the GitHub releases API, `ollama.com`, `unsloth.ai`, and the live host (`sw_vers`, `sysctl`, `df`, `hf version`).

Counts (one per bullet below; several ✅ bullets bundle related figures from the same record): ✅ 68 · ⚠️ 9 · ❌ 2 · 🔍 5

---

## ❌ Claims that don't match their source

**❌ macOS version.** README line 8 and notes line 3 both say the host ran **macOS 26.5**. Every one of the four run records reports `hostBefore.os.stdout` / `hostAfter.os.stdout` as `ProductName: macOS / ProductVersion: 27.0 / BuildVersion: 26A428`, and the live host confirms it (`sw_vers` → `27.0`, build `26A428`). All eleven Sep 27 records in `../uncensored-models-m5-benchmark/runs/` also say 27.0, so the host was already on 27.0 before this session. "macOS 26.5" is correct only for the Sep 22 report (`../mac-model-benchmarks/README.md`), which appears to be where it was carried over from.

**❌ Flash-Next buffer sizes are MiB divided by 1000 and labelled GB.** README line 47: "Flash-Next loaded as 47.7 + 38.1 GB Metal buffers plus a 27.5 GB CPU-mapped buffer (server log)." The server log for that load reads:

```
load_tensors:  MTL0_Mapped model buffer size = 47667.72 MiB
load_tensors:  MTL0_Mapped model buffer size = 38139.44 MiB
load_tensors:   CPU_Mapped model buffer size = 27465.95 MiB
```

47,667.72 MiB is 46.6 GiB / 50.0 GB, not 47.7 GB; 38,139.44 MiB is 37.3 GiB / 40.0 GB; 27,465.95 MiB is 26.8 GiB / 28.8 GB. Each figure is the MiB value divided by 1,000, so all three understate the buffers by about 7%. notes line 33 states them correctly in MiB (`47,668 MiB + 38,139 MiB`, `27,466 MiB`), so this is a README-only conversion error.

The log's MiB values are provably the ground truth: 47,667.72 MiB × 1,048,576 = 49,983,227,166 B and 38,139.44 MiB × 1,048,576 = 39,992,101,437 B, which land on shards 2 and 3 of the GGUF (49,983,253,824 and 39,992,153,376 B) to within the log's two-decimal rounding. The two Metal buffers *are* those two shards byte-for-byte, so 47.7 and 38.1 cannot be GB.

---

## ⚠️ Claims whose strength, scope, or attribution does not match the source

**⚠️ "Same runner and settings as the Sep 27 report (bench.py, unchanged)" (README line 63) — the per-case deadline differs.** The four stock records carry `workloadProtocol.caseDeadlineSeconds: 120`. The Sep 27 Heretic thinking-on record (`20260927-qwen3.8-27b-heretic-llmfan46-think.json`), which supplies the comparison row, carries `600`, and the Sep 27 README states "600 s per case" for its thinking-on table. The deadline is not listed among the settings README enumerates, so a reader cannot see the difference.

**⚠️ The Sep 27 comparison row was produced by a different bench.py revision.** `bench.py` on disk hashes to `3c45e7cc1f9949a6d4fd5eca5e1cefb25802472f3491f78a486d15ee729bb156`, which matches `runnerSha256` in all four stock records ✅. But the Sep 27 Heretic thinking-on run records `runnerSha256: 177c3fbeb61f1fb81e64b09199ad46c0b5f16ba52ea3f06bcdbcf16da50c8e9f` and the Heretic thinking-off run records `96ec016a0a9d…`. Only the Sep 27 96-case thinking run used `3c45e7cc…`. "Unchanged" is true of the file as committed, not of the runner that produced the 8/24 and 24/24 + 865-token numbers being compared against.

**⚠️ The 27B thinking-on 24/24 finished 4.7 s inside the 120 s per-case deadline.** Case `ledger-0` took 115.3 s (`response.clientWallMs` 115,304; `eval_count` 2048, `done_reason` `stop`). No case errored or truncated, so the 24/24 stands, but it sits close to a timeout that the Sep 27 run it is compared with did not have (600 s there). Worth a caveat line given the report leans on the exact match.

**⚠️ `first24Comparable` is `false` in both thinking-on records, yet the "First 24" table uses thinking-on rows.** `runs/20260929-qwen3.8-27b-q8_0-stock-on.json` and `…-flash-next-ud-q3kxl-on.json` both set `workloadProtocol.first24Comparable: false`. Per `bench.py` line 117 the harness sets that flag from `args.think in ('false','low') and args.case_seconds == CASE_SECONDS`, so it is false for any thinking-on run regardless of case identity. The 24-case slice itself is provably identical across reports (stock `caseSliceSha256` `bbd9fc9628e3…` equals the Sep 27 thinking-on run's `suiteSha256` `bbd9fc9628e3…` ✅), so the comparison is sound — but the README table's "First 24" column conflicts with a flag in its own raw records and should say why.

**⚠️ Qwen3.8-27B "(dense, Aug 14, 2026)" (README line 56) has no matching source.** `https://huggingface.co/api/models/Qwen/Qwen3.8-27B` reports `createdAt: 2026-08-05T08:22:59.000Z` and `lastModified: 2026-08-14T15:00:01.000Z`. Aug 14 matches `lastModified`, not `createdAt`. I am not claiming Aug 5 is the release date — HF `createdAt` is frequently private-repo creation rather than public release, and I can't distinguish the two from the API. The point is that the `per the Hub created_at` qualifier in the same table applies only to the Flash-Next row, so this date is presented with no source behind it. (The Flash-Next date is correct — see ✅ below.)

**⚠️ 89 GB and 90 GB are given for the same three files.** README line 57 says "89 GB (three shards)"; README line 59 says "UD-Q3_K_XL at 90 GB". Both are traceable — the shards total 89,986,353,824 B, which Ollama truncates to "89 GB" in its own output, while Unsloth's table lists "90.0" — but as written the report contradicts itself within two lines.

**⚠️ notes line 9 attribution to Qwen is unsupported by its cited URL; corrected at line 42 but not amended in place.** This one is a convention question rather than a source failure — a timestamped running log with a dated correction entry is exactly what `.claude/rules/research-workflow.md` asks for, and retroactively rewriting an earlier entry would arguably be worse practice. Flagging it only so the claim isn't reused. Line 9 reads "Qwen3.8-Flash-Next is described by Qwen as the first open-weight release of the Qwen 4 architecture ([Qwen blog](https://qwen.ai/blog?id=qwen3.8-flash-next))". That URL returns HTTP 200 but serves a JavaScript-only shell — a non-JS fetch yields the single word "Qwen" and no article text, so the page supports nothing. notes line 42 records exactly this and moves the claim to the model card, which is the right fix; line 9 was left as-is, so the running log carries an unsupported attribution.

**⚠️ notes line 19 "roughly 700 MB/s" for the shard download is unsourced and low.** `logs/hfdl2.log` brackets the command at 23:46:03 → 23:47:45 (102 s) for 89,986,353,824 B, which is about 880 MB/s. The log records no rate of its own. (The separate "~840 MB/s" pull figure at notes line 13 **is** in the log — see ✅.)

**⚠️ README line 47's hedge understates the evidence in its own log.** The report says "I believe the CPU buffer is the 3-bit n-gram embedding table (`qwen4exp.ple.ngram_size = 3`) but have not confirmed which tensors it holds", and notes line 33 carries it as a **TODO**. The server log names the tensor directly, six lines above the buffer sizes: `add: tensor per_layer_token_embd.weight (size = 27465 MiB) lazy read enabled`. That settles *which tensor* occupies the buffer. It does not fully settle the interpretation: the tensor is a per-layer token embedding and the card describes "N-gram Embedding" as a 51B component, so calling it "the 3-bit n-gram embedding table" is still an inference. One consistency check in its favour, offered as consistency and not proof: 51B parameters at roughly 4.5 bits per weight — a plausible effective rate for embedding-class tensors under the UD-Q3_K_XL mix — comes to about 28.7 GB, which lands on the 28.8 GB this buffer actually occupies. Recommend citing the log line and narrowing the open question to whether that tensor is the n-gram table.

---

## 🔍 Could not be verified

**🔍 The 27B smoke test (notes line 15).** "`think: false` on '17 * 23' returned `391` with empty thinking (4 tokens); `think: true` returned `391` with 115 thinking characters. `ollama ps`: 29 GB, 100% GPU, context 8192." The store's `logs/` holds `flash-smoke-off.json` and `flash-smoke-on.json` but no 27B equivalent, and `server.log` has no request entries for the 23:45 window. Partial corroboration only: `throughput.loadedModel` in both 27B records shows `size` 29,886,313,921 with `size_vram` equal to it (100% GPU) and `context_length` 8192 ✅. The `391`, the 4 tokens, and the 115 thinking characters rest on the note alone.

**🔍 Trending scores (notes line 24).** The HF API serves no historical snapshot for a Sep 29 23:50 reading. Current top-40 values (Sep 30) sit within a point or two of most figures given: `prism-ml/Ternary-Bonsai-2-27B-gguf` 346 vs 344, `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF` 217 vs 219, `…Flash-Next-GSQ-RCO-GGUF` 142 vs 142, `…-Coder-GGUF` 136 vs 136, `ukisai/Swift-1.5-…` 149 vs 148, `deepseek-ai/DeepSeek-V4.1-Flash` 176 vs 177. One is further off: `XingChen-AGI/Xing4.0-29B-A4B` reads 364 now against the 374 stated. The three below-top-40 figures (87, 72, 33) are not readable from the public list. Every repo named exists and matches the library/date attributes given ✅, and the one hard number — `~3.58M downloads` for Ternary-Bonsai — matches exactly (3,581,027) ✅.

**🔍 `qwen.ai/blog?id=qwen3.8-flash-next`** resolves (HTTP 200) but returns no article text to a server-side fetch, so nothing on it can be verified either way. Already self-flagged at notes line 42.

**🔍 The Flash-Next `ollama ps` 40 GB / loaded-buffer mismatch is recorded but unexplained.** `throughput.loadedModel[0].size` is 40,379,822,898 B in both Flash-Next records ✅, and the loaded buffers total far more, so the report's statement that the two do not match is correct and its decision not to use the figure is sound. Why Ollama reports 40 GB is not established by any source I could reach; the report does not claim to know, which is the right posture.

**🔍 `pmset -g therm` "before and after each pass" (README line 50).** Verified for the four timed passes via `hostBefore`/`hostAfter` ✅ (both read "No thermal warning level has been recorded / No performance warning level has been recorded" in all four records). No separate `pmset` capture exists for the smoke tests or the import, so "each pass" is verified only for the passes that produced records.

---

## ✅ Verified

### URLs (all resolve; content checked)

- ✅ `https://huggingface.co/Qwen/Qwen3.8-Flash-Next` — HTTP 200, is the Flash-Next card, supports the quote and parameter line cited from it.
- ✅ `https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/38bb39ee97821de2c9009abb7e93950eec396e66` — HTTP 200, pinned revision exists and holds the `UD-Q3_K_XL` directory.
- ✅ `https://unsloth.ai/docs/models/qwen3.8-next` — HTTP 200, carries the quant-size and hardware tables cited.
- ✅ `https://github.com/ollama/ollama/releases/tag/v0.35.0` — HTTP 200, content matches the caveat (below).
- ✅ `https://github.com/ollama/ollama/issues/5245` — HTTP 200, "Allow importing multi-file GGUF models", open, created 2024-06-23. Its own workaround block (`hf download` then `ollama create` from the directory) is the same route the report took, so the pointer is apt.
- ✅ `https://ollama.com/library/qwen3.8-flash-next/tags` — HTTP 200, supports the 105 GB / 120 GB figures (below).
- ✅ `https://www.orcarouter.ai/blog/qwen-4-max-lineup-announced-apsara-2026` — HTTP 200, dated Sep 22 2026, supports "Qwen 4 is not released" and the Apsara announcement.
- ✅ `https://www.yottalabs.ai/post/qwen-4-release-date-what-is-known-how-to-prepare-2026` — HTTP 200, contains "very soon" verbatim (below).
- ✅ `https://github.com/kodyabbott/research` — HTTP 200 (AI-ASSISTED banner link).
- ✅ Relative links all resolve on disk: `../mac-model-benchmarks/`, `../uncensored-models-m5-benchmark/`, `../uncensored-models-m5-benchmark/bench.py`, `../coding-benchmark-harness/`, `../coding-benchmark-harness/DESIGN.md` (confirmed present with `test -f`; the directory was not otherwise touched), `../local-model-benchmarks/runs/20260911-104941-c75692e6.json`, `runs/`, `notes.md`, and all four named run files.

### Quotes (verbatim)

- ✅ **Qwen model card.** README line 57 quotes "this experimental preview of the architecture that will underpin Qwen4". Card line 26: "This experimental preview of the architecture that will underpin Qwen4 is built around a fundamental rethinking of how the core components of modern large language models (LLMs) interact at scale." Verbatim fragment; only the leading `T` is lowercased to embed it mid-sentence, which is standard. notes line 42 quotes it with the capital `T` — also verbatim. (The Ollama library page carries the identical sentence as its description, independently.)
- ✅ **Card parameter line.** notes line 42 quotes "Number of Parameters: 125B with 6B activated, plus 51B n-gram embedding and 4B MTP". Card line 46, verbatim.
- ✅ **License.** `qwen-community-1.0` — card front matter `license_name: qwen-community-1.0`; the Unsloth repo's `cardData` reports the same.
- ✅ **Ollama sharded-GGUF error.** notes line 16 quotes "This repository only contains sharded GGUF files. Ollama does not yet support pulling sharded GGUF via the registry". `logs/pull.log` records, verbatim: `Error: pull model manifest: 400: {"error":"This repository only contains sharded GGUF files. Ollama does not yet support pulling sharded GGUF via the registry; please download the shards and merge them locally with \`ollama create\` (workaround detailed at https://github.com/ollama/ollama/issues/5245), or use a repository with single-file quantizations."}`. The quote is an exact prefix, and the issue number the note attributes to it is in the same string.
- ✅ **Split-GGUF create failure.** notes line 20: "invalid split GGUF … has 1 shards, expected 3". Log: `Error: invalid split GGUF: split GGUF "Qwen3.8-Flash-Next-UD-Q3_K_XL-00001-of-00003.gguf" has 1 shards, expected 3`.
- ✅ **Template selection.** README line 48 and notes line 32 quote `template selection … selected=gguf_chat_template`. `server.log`: `msg="template selection" model=registry.ollama.ai/library/qwen3.8-flash-next-ud-q3kxl:latest selected=gguf_chat_template renderer="" parser="" …`, on all three Flash-Next loads.
- ✅ **Passthrough template.** `TEMPLATE {{ .Prompt }}` — `logs/flash-modelfile.txt` contains exactly that line plus `ollama show`'s comment header. "Shows only a passthrough" is accurate.
- ✅ **Layer offload.** notes line 33: `offloaded 49/49 layers to GPU`. Log, verbatim.
- ✅ **Runner guards.** notes line 21 quotes "Refusing to overwrite an existing raw run" (`bench.py` line 106, verbatim; reproduced in `run_27b-attempt2-failed.log`) and describes the empty-`/api/ps` assertion — `bench.py` line 279, `assert not self.api('ps')['models'], 'Dedicated server already has a loaded model'`, which fired twice in `run_27b-attempt1-failed.log`. The notes line 35 `KeyError` is in `run_flash2-attempt1-failed.log`: `KeyError: 'qwen3.8-flash-next-ud-q3kxl'` raised from `installed[self.args.model]`, confirming the full-tag requirement.
- ✅ **"very soon".** notes line 9 puts "very soon" in quotes and cites two summaries. The yottalabs page carries it verbatim ("Qwen 4 is in training on a new-generation architecture and will be released 'very soon'", attributed to Qwen project lead Liu Dayiheng at the Sep 22 Apsara keynote). The orcarouter page supports the not-released/in-training half but says "would arrive soon" — the quote rests on yottalabs, which is one of the two cited, so the citation holds.
- ✅ **`requires` flags.** Store config blobs, read directly. Flash-Next: `{"model_format":"gguf","model_family":"qwen4exp","model_families":["qwen4exp"],"model_type":"176.9B","file_type":"Q3_K_M","requires":"0.35.0"}`. 27B: `…"renderer":"qwen3.8","parser":"qwen3.5","requires":"0.32.12"…`. Both `requires` values, the `renderer=qwen3.8 parser=qwen3.5` pair at notes line 15, and the absence of a renderer on Flash-Next (consistent with `selected=gguf_chat_template`) check out.
- ✅ **Thinking-mode sampling recommendation.** README line 49: "model cards recommend sampling (temperature 1.0, top_p 0.95, top_k 20) for thinking." Card line 342: "Thinking Mode: `temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0.0`, `presence_penalty=0.0`, `repetition_penalty=1.0`".

### Ollama v0.35.0 release notes and dates

- ✅ Release body lists exactly what README line 46 says and nothing else substantive: decision models via `/v1/systemone`; "Settings now opens without waiting for model discovery"; "Fixed the macOS update menu and icon not reflecting an available update at startup"; "Fixed stalled MLX model downloads hanging indefinitely"; "Requests containing the deprecated `typical_p` parameter now log a warning instead of failing."
- ✅ No occurrence of `qwen4exp` anywhere in the body, so "nothing about `qwen4exp`, so I cannot say what the requirement is for" is accurate and appropriately hedged.
- ✅ Dates (GitHub releases API): `v0.35.0` published `2026-09-28T21:23:22Z`; `v0.34.4` published `2026-09-23T02:24:43Z` — five days, as README line 46 and notes line 41 state. `v0.35.1-rc0` published `2026-09-29T20:14:22Z` ✅. The installed app reports `ollama version is 0.34.4` ✅, matching `runtime.version` in all four records.

### Numbers attributed to this report's runs

All read from `workloadSummary`, `throughput.summary`, `unload`, `artifact`, and per-case `response` objects in `runs/`.

- ✅ 27B off: `passed` 8, `first24Passed` 8; `byCategory` ledger 0/3, event-state 0/3, scheduling 1/3, SQL 0/3, shortest-path 2/3, extraction 2/3, python-trace 0/3, retrieval 3/3 — matches README row and notes line 29 exactly. `medianOutputTokens` 63.5; `totalWallMs` 118,128.3 → 118 s. Throughput 18.83 (18.14–18.91), 557.11 ingest, 7,026 ingest tokens, `medianShortWallMs` 7,619.6 → 7.6 s, checks 3/3, `anyTruncated` false, `unexpectedThinking` 0.
- ✅ 27B on: 24/24, all eight categories 3/3; `medianOutputTokens` 903; `totalWallMs` 1,154,935.7 → 19.2 min (README) and `startedAt` 23:54:12 → `finishedAt` 00:15:51 = 21.65 min (notes line 30's "21.6 minutes total"), and notes line 39 explains precisely this distinction ✅. Workload `medianGenTokPerSec` 18.1966 → notes' 18.20. Throughput 18.04 (18.03–18.04), 578.43 ingest, `medianShortWallMs` 28,679.4 → 28.7 s, `anyTruncated` true, checks 3/3.
- ✅ Flash-Next off: 9/24; categories 0/0/1/0/2/**3**/0/3 — the one-case extraction gain over the 27B is real. `medianOutputTokens` 34.5; `totalWallMs` 40,922.0 → 41 s. Throughput 50.05 (50.01–50.19), 977.5 → 978 ingest, 7,026 tokens, 2,983.7 ms → 3.0 s, checks 3/3, no truncation.
- ✅ Flash-Next on: 24/24, all categories 3/3; `medianOutputTokens` 747; per-case `eval_count` min 146 / median 747 / max 2,473 — notes line 37 exact. Workload median 46.8456 → 46.8. `totalWallMs` 520,170.4 → 8.7 min. Throughput 49.05 (48.17–49.13), 897.04 → 897, 7,066 ingest tokens, 10,685.0 ms → 10.7 s, checks 3/3, `anyTruncated` true.
- ✅ Derived ratios (README line 10): 49.05 / 18.04 = 2.72 → "2.7x faster" on generation; 1,154,935.7 / 520,170.4 = 2.220 → "2.2x sooner" on the 24-case pass. Both correct, and notes line 39 states the same two bases. Worth noting, though not an error: the same sentence says Flash-Next "did it in 8.7 minutes at about 49 tok/s", pairing a workload wall time with the throughput-battery median — the workload's own median was 46.8 tok/s. notes line 39 keeps the two bases distinct; the README prose blurs them.
- ✅ Truncation footnote (README line 32). Trial records show the short generation ending with `doneReason: "length"`, `outputTokens: 512`, `truncated: true` on both thinking-on runs and `truncated: false` on both thinking-off runs.
- ✅ Throughput protocol as described: `bench.py` lines 180–193 issue one warmup plus three trials, each a short generation (`'Write a 100 word description of the Rocky Mountains.'`, `num_predict` 512) and an ingest; records show `trials: 3` and ingest prompts of 7,026–7,066 tokens → "~7,000-token ingest".
- ✅ Method settings (README line 63): `options` in every record is `{"num_ctx": 8192, "temperature": 0, "seed": 42, "top_p": 1, "top_k": 40, "repeat_penalty": 1.0}`; `optionOverrides` empty; `outputCap` 2048 thinking-off and 8192 thinking-on; `samplesPerCase` 1; `suite` `practical-json-v1`; `generatedCodeExecution: "disabled"`; `refusalProtocol` present but no refusal results, consistent with "the refusal pass was not run".
- ✅ Unload confirmed on all four: `unload.confirmed: true` at 23:54:12, 00:15:51, 00:19:52, 00:29:39, each equal to that run's `finishedAt` and to the next run's `startedAt` — the four passes chain with no overlap, supporting "one model loaded at a time" and "no download or import overlapped a timed pass".
- ✅ Host facts in the records: `chip` "Apple M5 Max"; `memoryBytes` 137,438,953,472 = 128 GiB; `power` "Now drawing from 'AC Power' … 100%; charged"; `swap` total 0.00M. Live host confirms 18 CPU cores (`hw.ncpu`, 6 + 12 across perf levels) and 40 GPU cores (`system_profiler`), matching README line 8.
- ✅ `startedAt`/`finishedAt` for all four passes match every timestamp in notes lines 29, 30, 36, 37 (23:51:06–23:54:12, 23:54:12–00:15:51, 00:18:35–00:19:52, 00:19:52–00:29:39).
- ✅ `sourceCommit` on each record (`3c594d7f…`, `8563bd2b…`, `dea069c6…` ×2) all exist as commits in the repo.

### Artifact digests

- ✅ HF tree API at the pinned revision (`/api/models/unsloth/Qwen3.8-Flash-Next-GGUF/tree/38bb39ee…/UD-Q3_K_XL`) returns exactly the three LFS OIDs and sizes notes line 40 lists: `f2ef4328929d8b8c8930e2856eef52128dd4ce3425302f04bc3c657431cc4c49` / 10,946,624; `7d230e7c9421d868b89eebaf23033af0ea1a4e046956df00fb156814fb62346e` / 49,983,253,824; `21d4f90f9cd7b7c3a1582667c20cb22f7b03de895b88a23bb20aaeaa44f2c199` / 39,992,153,376.
- ✅ The store manifest `manifests/registry.ollama.ai/library/qwen3.8-flash-next-ud-q3kxl/latest` carries those same three digests and sizes as its three `application/vnd.ollama.image.model` layers, and `blobs/` holds files named `sha256-<each digest>` at those exact byte counts. The "byte-identical to the pinned upload" claim in notes line 40 and the README "Artifacts verified" section hold.
- ✅ 27B: manifest layers are projector `ac3714bfdddeca31351f2752bf1a63f266f4df87c0b68c895e44945ca704448e` / 931,146,016 B (→ "931 MB", README line 56) and model `2bb22714289826d7b9e0ba376c3ce47d08bce39abe598745857c44d88c09bdbf` / 29,047,084,384 B (→ "29 GB"). Both digests match notes line 40 and the short form `2bb22714…` in the README.
- ✅ Run-record artifact digests: `8f5fb6b71ea00052cbe8545738c55ce61112c4e571cb60ca4dad00b131766039` (27B, notes line 31) and `ea16de1a7bee5588bccc3bc604a6ffc679d8d4dae4497cebf93b35f85fe61ad6` (Flash-Next, notes line 36) appear in both of each model's records. Flash-Next `artifact.size` 89,986,353,967 B → Ollama's truncated "89 GB" (notes line 20).
- ✅ `throughput.loadedModel[0].size` for Flash-Next is 40,379,822,898 B, the exact figure notes line 36 attributes to `/api/ps`, with `context_length` 8192 and full GPU residency.

### Cross-report claims

- ✅ **Sep 27 Heretic, thinking off, 8/24.** `20260927-qwen3.8-27b-heretic-llmfan46.json` → `first24Passed: 8` (of a 96-case pass, `passed: 35`). Matches the Sep 27 README's "First 24 | 8" row and the stock report's comparison row. `first24Comparable: true`.
- ✅ **Sep 27 Heretic, thinking on, 24/24 / median 865 / 20 min.** `…-heretic-llmfan46-think.json` → `passed: 24`, `attempted: 24`, all categories 3/3, `truncated: 0`; `medianOutputTokens: 864.5`, which the Sep 27 README publishes as 865 and which the stock report cites as 865 — a correct round of the raw value, worth knowing is 864.5; `totalWallMs: 1,206,161.8` = 20.1 min → "20 min". `runtime.version` 0.34.4 and `artifact.details.quantization_level` Q8_0 ✅, so "same quant as the Sep 27 Heretic row, so those two rows compare directly" (README line 56) is supported.
- ✅ **Identical 24-case slice.** The Sep 27 thinking-on run's `suiteSha256` is `bbd9fc9628e3b994abb551e67b5af92f8b30aa735caa64fff8bffc778ba451bf`, byte-equal to `caseSliceSha256` in all four stock records. The 96-case suite digest `d262c79327a2…` is shared by the Sep 27 96-case runs and the Sep 11 Windows run. So the cases really are the same cases across all three reports.
- ✅ **Sep 11 Windows, 24/24, median 946.5.** `../local-model-benchmarks/runs/20260911-104941-c75692e6.json` → `benchmarks[0].summary.passed: 24`, `attempted: 24`, `truncated: 0`, `protocolValid: true`; per-case `eval_count` median exactly 946.5 (min 145, max 2048). `runtime.version: "0.32.13"` ✅, `details.quantization_level: "BF16"` ✅, `protocol.thinking: true`, `caseCount: 24`, `caseDeadlineSeconds: 120` (the same deadline as the stock runs, unlike Sep 27), `unloadConfirmed` present. Model tag is `qwen3.8:27b-mtp-bf16` (parent `qwen3.8:27b-bf16`) — stock, as the row says.
- ✅ **Windows RTX PRO 6000 host.** `../local-model-benchmarks/README.md` lines 90–94: "NVIDIA RTX PRO 6000 Blackwell Max-Q, 96 GB", "Windows 11 Pro 25H2", "Ollama 0.32.13". The run's `gpuBefore.totalGiB` 95.59 corroborates the 96 GB card, and its `created_at` stamps are UTC six hours ahead of the MDT `startedAt`, consistent with a separate machine.
- ✅ **Sep 22 reference.** `../mac-model-benchmarks/README.md` is dated September 22, 2026 and reports stock Qwen3-Coder 30B under both Ollama and MLX at Ollama 0.32.13 — matching README line 8 and notes line 8.
- ✅ **Sep 27 summary in notes line 8.** "Heretic Qwen3.8-27B Q8_0 scored 24/24 and 96/96 with thinking on at ~18 tok/s": the 24-case run is 24/24 at `medianGenTokPerSec` 18.00 and the 96-case run (`…-think96.json`) is `passed: 96` at 17.98 ✅.
- ✅ **README line 42's restraint is warranted.** With thinking off both builds score 8 (stock) and 8 (Heretic), and all three thinking-on rows are at 24/24, so "this suite cannot rank them" is the correct reading of the data rather than an overclaim.

### Model-selection numbers

- ✅ **Unsloth quant tiers.** The guide's table lists `UD-Q3_K_XL 90.0`, `UD-IQ4_XS 93.7`, `UD-Q4_K_XL 111.3` (GB). So "Unsloth lists 90.0 GB" (notes line 10), "UD-Q3_K_XL at 90 GB", and "the 4-bit tiers are 94-111 GB" all check out. The guide's separate hardware table gives "3-bit 90 GB" and "4-bit 96-114 GB", supporting notes line 10's "'90 GB' RAM".
- ✅ **Ollama's own tags.** `ollama.com/library/qwen3.8-flash-next/tags` lists `125b-a6b-nvfp4` (MLX) 105GB, `125b-mlx` 105GB, `125b-a6b-q4_K_M` 120GB, `125b-a6b-q8_0` 189GB, `125b-a6b-bf16` 355GB, `125b-a6b-mlx-bf16` 360GB. "Tags start at 105 GB (nvfp4, mlx) and 120 GB (q4_K_M)" is exact, and "the only Ollama-loadable tier with real headroom" follows.
- ✅ **Flash-Next release date.** `https://huggingface.co/api/models/Qwen/Qwen3.8-Flash-Next` → `createdAt: 2026-08-24T08:24:59.000Z`, so "released Aug 24, 2026 per the Hub `created_at`" is correct and correctly qualified.
- ✅ **Shard sizes surveyed.** notes line 16's "Unsloth UD-Q3_K_XL: 10.9 MB + 50.0 GB + 40.0 GB" matches the tree API (10,946,624 / 49,983,253,824 / 39,992,153,376), and "ISTA-DASLab GSQ-RCO IQ3_S: 54.8 + 28.8 GB" matches that repo's tree exactly (54,817,524,224 and 28,800,138,432).
- ✅ **GGUF metadata.** notes line 16's "architecture `qwen4exp`, context 262144, license `qwen-community-1.0`" — records show `general.architecture` `qwen4exp`, `qwen4exp.context_length` 262144, and the repo `cardData` license as above. `general.parameter_count` 176,943,899,520 → the `176.9B` in `ollama show` (notes line 32); `qwen4exp.ple.ngram_size` is 3, as quoted in README line 47.
- ✅ **Every Flash-Next GGUF repo checked is sharded** (notes line 16) — both repos it names are multi-file in their trees, consistent with the 400 from the registry.

### Server-log details in notes

- ✅ `CPU_Mapped model buffer size = 27465.95 MiB` → notes' "27,466 MiB"; `MTL0_Mapped … 47667.72` and `38139.44 MiB` → notes' "47,668 MiB + 38,139 MiB". (notes' MiB figures are right; the README's GB restatement is the ❌ above.)
- ✅ `llama_kv_cache: size = 24.00 MiB ( 8192 cells, 12 layers, 1/1 seqs)` → notes line 33's "KV cache 24 MiB for 8192 cells over 12 attention layers".
- ✅ `llama_memory_recurrent: size = 112.57 MiB ( 1 cells, 48 layers, …)` → notes' "112.6 MiB recurrent state over 48 layers".
- ✅ `Metal` / `Apple M5 Max` backend line present (notes line 15).
- ✅ **Flash-Next smoke test** (notes line 32), fully corroborated by `logs/flash-smoke-off.json` and `-on.json`: content `391` in both; thinking-off `eval_count` 4 with no `thinking` field; `load_duration` 15,402,715,875 ns = 15.4 s first load; thinking-on `thinking` string is exactly 123 characters; `eval_count` 49 over `eval_duration` 962,201,000 ns = 0.96 s → 50.9 tok/s ("~51 tok/s").

### Tooling and environment

- ✅ `hf version` → `2.0.0`, supporting notes line 24 and README's "`hf` CLI 2.x".
- ✅ `hf models ls --help` exposes `--filter` but no `--library` flag, confirming notes line 24.
- ✅ `logs/brew-llamacpp.log` records `Pouring llama.cpp--0.5.0.arm64_golden_gate.bottle.tar.gz` → `/opt/homebrew/Cellar/llama.cpp/0.5.0`, so "installed `llama.cpp` 0.5.0 via Homebrew" (notes line 23) is right.
- ✅ `logs/pull.log` contains `840 MB/s`, supporting notes line 13's "~840 MB/s".
- ✅ `df` → 1.1 Ti available on a 1.8 Ti volume, consistent with notes line 17's "1.2 TB free on a 1.8 TB volume" (1.1 TiB ≈ 1.21 TB).
- ✅ `Modelfile.flash-next` is a single line, `FROM /Users/kody/Documents/Codex/model-cache/stock-qwen-benchmark/hf/Qwen3.8-Flash-Next-GGUF/UD-Q3_K_XL`, matching the Reproduce block's directory-not-shard instruction and the `FROM <first shard> fails` comment.
- ✅ Dedicated-server settings as described: `endpoint` is `http://127.0.0.1:11436` in all four records, and `hostBefore.caveat` records "Interactive desktop host; dedicated-host isolation is not established", which README line 50 reflects honestly as "One interactive desktop session".

---

## Suggested fixes, in priority order

1. README line 8 and notes line 3: macOS 26.5 → macOS 27.0 (build 26A428).
2. README line 47: restate the buffers in the units the log uses — 47,668 + 38,139 MiB Metal and 27,466 MiB CPU-mapped (about 50.0 + 40.0 GB and 28.8 GB) — and cite `add: tensor per_layer_token_embd.weight (size = 27465 MiB)` while narrowing the open question to whether that tensor is the n-gram table.
3. README line 63: state the per-case deadline (120 s) and note that the Sep 27 thinking-on comparison run used 600 s and a different `runnerSha256`; add that the 27B's slowest thinking-on case took 115.3 s of the 120 s budget.
4. README line 56: the "Aug 14, 2026" date for the 27B is unsourced — Hub `createdAt` is Aug 5 and `lastModified` is Aug 14. HF `createdAt` is often private-repo creation rather than public release, so I can't say from here which is the release date; cite whichever the author meant, or drop the date.
5. Reconcile "89 GB" and "90 GB" for the Flash-Next shards, or label each with its source.
6. Add one line to the comparison table's note explaining that the thinking-on records carry `first24Comparable: false` by harness convention while the case slice digest is identical across reports.
7. notes line 9: amend in place to point at the model card, matching the correction already recorded at line 42, and replace the "roughly 700 MB/s" at line 19 with the log-derived rate or drop it.
