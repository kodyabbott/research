# Stock Qwen on the M5 Max: Qwen3.8-27B and Qwen3.8-Flash-Next

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Claude Fable 5.1). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Measured September 29-30, 2026 (MDT), on this MacBook Pro: Apple M5 Max, 18 CPU / 40 GPU cores, 128 GB unified memory, macOS 27.0 (26A428), Ollama 0.34.4 on a dedicated local server. Kody asked whether stock (not uncensored) Qwen models are capable on this Mac, and to download and test them. Earlier reports here covered stock Qwen3-Coder 30B ([Sep 22](../mac-model-benchmarks/)) and five uncensored builds ([Sep 27](../uncensored-models-m5-benchmark/)); this is the first stock Qwen3.8 run on this host.

**What was measured.** With thinking on, both stock models solved all 24 cases (one 27B case finished 4.7 s inside the 120 s deadline, see Method). With thinking off, Flash-Next scored 9/24 and the 27B 8/24. On the thinking-on pass Flash-Next generated at 46.8 tok/s against the 27B's 18.2 (2.57x) and finished in 8.7 minutes against 19.2 (2.2x); the standalone throughput battery gives 49 vs 18 tok/s. The 24-case suite is at its ceiling with thinking on and cannot rank these models; the thinking-off scores are low for both because most cases need step-by-step computation the models cannot show without thinking.

**Stock vs Heretic.** The stock 27B and the Sep 27 Heretic Q8_0 build both scored 8/24 thinking off and 24/24 thinking on, but the 8/24 rows are not the same eight cases: stock passed shortest-path 2/3 and extraction 2/3, Heretic 1/3 and 3/3. Two single-case flips in opposite directions is what one-sample noise looks like; the totals matching is not evidence that the builds behave identically, only that this suite detects no difference between them.

**Mac Q8_0 vs Windows BF16.** The stronger evidence for the quantization is case-level: against the Sep 11 Windows run of `qwen3.8:27b-mtp-bf16` (same prompts, greedy decoding, Ollama 0.32.13, RTX PRO 6000), the Mac Q8_0 thinking-on pass produced **23 of 24 byte-identical final answers** (the 24th differs only in JSON whitespace) and **17 of 24 byte-identical reasoning traces**, including the full 2,949-character trace on `ledger-0`. Greedy decoding followed the same trajectory across Q8_0/BF16, Ollama 0.34.4/0.32.13, and Metal/CUDA for most cases. Recomputed from the two records' `cases[]` arrays.

**Tradeoffs, not a verdict.** Flash-Next is faster at equal score on this suite. Against that: it needs 90 GB on disk and about 119 GB resident (Metal plus the CPU-mapped embedding table) versus 29 GB for the 27B, it runs at 3-bit versus Q8_0, its GGUF declares `requires 0.35.0` while this server is 0.34.4, and this suite is not a coding or writing benchmark. A coding harness is being built separately ([coding-benchmark-harness](../coding-benchmark-harness/)).

## Results

Same 24 cases, one sample each, strict JSON grading. Category columns are passed/3. Wall time is the workload's 24-case total (`workloadSummary.totalWallMs`), excluding model load, warmup, and the throughput battery.

| Model | Mode | Passed | Ledger | Event | Sched | SQL | Path | Extract | Trace | Retrieve | Median gen tokens | Wall time |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B Q8_0 (stock) | off | 8/24 | 0 | 0 | 1 | 0 | 2 | 2 | 0 | 3 | 63.5 | 118 s |
| Qwen3.8-27B Q8_0 (stock) | on | **24/24** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 903 | 19.2 min |
| Qwen3.8-Flash-Next UD-Q3_K_XL | off | 9/24 | 0 | 0 | 1 | 0 | 2 | 3 | 0 | 3 | 34.5 | 41 s |
| Qwen3.8-Flash-Next UD-Q3_K_XL | on | **24/24** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 747 | 8.7 min |

Throughput battery (three warmed repetitions; short 100-word generation with a 512-token cap, and a ~7,000-token ingest):

| Model | Mode | Gen tok/s (median) | Ingest tok/s | Short response s | Exact checks |
|---|---|---:|---:|---:|---:|
| Qwen3.8-27B Q8_0 | off | 18.83 | 557 | 7.6 | 3/3 |
| Qwen3.8-27B Q8_0 | on | 18.04 | 578 | 28.7* | 3/3 |
| Qwen3.8-Flash-Next UD-Q3_K_XL | off | 50.05 | 978 | 3.0 | 3/3 |
| Qwen3.8-Flash-Next UD-Q3_K_XL | on | 49.05 | 897 | 10.7* | 3/3 |

\* Thinking consumes the 512-token cap, so the short trials are truncated with thinking on; the wall time then measures 512 tokens of mostly reasoning, not a finished answer. Generation rates are runtime-reported (`eval_count / eval_duration`).

## Comparison with earlier runs on this host and on Windows

| Qwen3.8-27B build | Mode | First 24 | Median gen tokens | Source |
|---|---|---:|---:|---|
| Stock Q8_0, this Mac, Ollama 0.34.4 | off / on | 8 / 24 | 63.5 / 903 | this report |
| Heretic Q8_0 (llmfan46), this Mac, Ollama 0.34.4 | off / on | 8 / 24 | -- / 865 | [Sep 27](../uncensored-models-m5-benchmark/) |
| Stock `qwen3.8:27b-mtp-bf16` (BF16 with MTP draft, `draft_num_predict 4`), Windows RTX PRO 6000, Ollama 0.32.13 | on | 24 | 946.5 | [Sep 11 run](../local-model-benchmarks/runs/20260911-104941-c75692e6.json) |

Thinking on is at the suite ceiling for all three, so this suite cannot rank them. The thinking-off totals match for stock and Heretic but on different cases (see above). The byte-identical outputs against the Windows BF16 run are the evidence that Q8_0 changed little here; for the Heretic ablation the suite only fails to detect a difference.

## Caveats

- Flash-Next's GGUF declares `requires 0.35.0`; the server is Ollama 0.34.4 (0.35.0 shipped Sep 28, five days after 0.34.4). The [0.35.0 release notes](https://github.com/ollama/ollama/releases/tag/v0.35.0) list decision models, a settings fix, an update-menu fix, stalled MLX downloads, and `typical_p` handling; nothing about `qwen4exp`, so I cannot say what the requirement is for. The model loaded, answered correctly, and honored thinking control in both directions. These numbers are for Ollama 0.34.4.
- Flash-Next loaded as 47,668 + 38,139 MiB Metal buffers (50.0 + 40.0 GB, byte-for-byte the sizes of shards 2 and 3) plus a 27,466 MiB (28.8 GB) CPU-mapped buffer ([server log excerpt](server-log-excerpt.txt); the full log is outside the repository at `~/Documents/Codex/model-cache/stock-qwen-benchmark/logs/server.log`). The log names that buffer: `add: tensor per_layer_token_embd.weight (size = 27465 MiB) lazy read enabled`, so the per-layer token embedding table lives in host memory with lazy reads; that it is the 51B n-gram embedding is an inference from the name and size (51B at ~4.5 bits per weight is about 28.7 GB), not a confirmed mapping. `ollama ps` reported the model at 40 GB, which matches none of these; I did not use that figure.
- Flash-Next used the GGUF's embedded Jinja chat template (`template selection … selected=gguf_chat_template`, [excerpt](server-log-excerpt.txt)); `ollama show --modelfile` shows only a passthrough `TEMPLATE {{ .Prompt }}`, which is misleading but not what the server used. The vision projector was not attached.
- Thinking on used greedy decoding at 8,192 context; model cards recommend sampling (temperature 1.0, top_p 0.95, top_k 20) for thinking. The 24-case screen is an answer-quality check, not a coding benchmark or a general ranking; a coding harness is being built separately ([coding-benchmark-harness](../coding-benchmark-harness/)).
- One interactive desktop session; no energy, thermal-throttling, or long-context measurements. `pmset -g therm` recorded no thermal or performance warnings before or after each pass.

## Models

| Model | Source | Quant | Size on disk | Notes |
|---|---|---|---:|---|
| Qwen3.8-27B (dense; Hub repo created Aug 5, last modified Aug 14, 2026) | Ollama registry `qwen3.8:27b-q8_0` | Q8_0 | 29 GB + 931 MB vision projector | Same quant as the Sep 27 Heretic row, so those two rows compare directly |
| Qwen3.8-Flash-Next (125B MoE, 6B active, released Aug 24, 2026 per the Hub `created_at`) | [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/38bb39ee97821de2c9009abb7e93950eec396e66) `UD-Q3_K_XL` | 3-bit dynamic | 90.0 GB decimal (89,986,353,824 B over three shards; Ollama lists it as 89 GB) | Qwen's model card calls it "this experimental preview of the architecture that will underpin Qwen4" ([card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)); 125B with 6B activated, plus 51B n-gram embedding and 4B MTP, license qwen-community-1.0. Ollama cannot pull sharded GGUFs from hf.co; imported with `ollama create` from the shard directory |

Why 3-bit for Flash-Next: Unsloth's 4-bit tiers are 94-111 GB and Ollama's own [`qwen3.8-flash-next` tags](https://ollama.com/library/qwen3.8-flash-next/tags) start at 105 GB (nvfp4, mlx) and 120 GB (q4_K_M), which leaves too little of the 128 GB for KV cache; UD-Q3_K_XL at 90 GB is the largest tier with real headroom ([Unsloth guide](https://unsloth.ai/docs/models/qwen3.8-next)). Low-bit quality loss is one of the things this run measures.

## Method

Same runner as the Sep 27 report ([bench.py](../uncensored-models-m5-benchmark/bench.py) as committed, `runnerSha256 3c45e7cc…` in all four records) and the same options, with one difference: bench.py's default per-case deadline is 120 s and I did not raise it, while the Sep 27 thinking-on comparison rows used 600 s (and an earlier runner revision, `177c3fbe…`). The 27B thinking-on pass came within 4.7 s of that deadline on `ledger-0` (115.3 s server time); had it timed out, the row would read 23/24. The comparison to the Sep 27 rows is on the identical case slice (`caseSliceSha256 bbd9fc96…`), but the records mark `first24Comparable: false` for any thinking mode by harness convention; I compare them here on the basis of identical prompts, grader, and options, with the deadline difference disclosed. 24-case `practical-json-v1` workload (three cases each of ledger replay, event reconstruction, scheduling, SQL, shortest paths, extraction, Python tracing, retrieval), strict JSON grading, generated code never executed; throughput battery of three warmed repetitions of a short generation and a ~7,000-token ingest. Temperature 0, seed 42, top_p 1, top_k 40, 8,192 context, 2,048-token output cap with thinking off and 8,192 with thinking on. The refusal pass was not run. Each model runs thinking off and thinking on.

Dedicated server: `OLLAMA_HOST=127.0.0.1:11436`, own model store, `OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NO_CLOUD=1`. One model loaded at a time; smoke tests are excluded from timing; no download or import ran during a timed pass (the first 27B pass started 6-13 s after the Flash-Next import wrote its manifest).

## Artifacts verified

All three Flash-Next shards match the LFS SHA-256 values in the pinned Hugging Face tree (digests in [notes.md](notes.md)); Ollama names blobs by SHA-256 and the store manifest carries the same three digests. The 27B is Ollama registry `qwen3.8:27b-q8_0`, model blob `2bb22714…`.

## Reproduce

Requirements: Ollama 0.34.4 app, Python 3.11+ (standard library only), `hf` CLI 2.x, about 210 GB free at peak (the 90 GB of shards are downloaded and then copied into the Ollama blob store; delete the download afterward to get back to 120 GB), this repository.

```sh
S=~/Documents/Codex/model-cache/stock-qwen-benchmark
OLLAMA_HOST=127.0.0.1:11436 OLLAMA_MODELS=$S/ollama OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
  OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NO_CLOUD=1 /Applications/Ollama.app/Contents/Resources/ollama serve &
export OLLAMA_HOST=127.0.0.1:11436
ollama pull qwen3.8:27b-q8_0
# Ollama cannot pull sharded GGUFs from hf.co; download the shards and import from the directory.
hf download unsloth/Qwen3.8-Flash-Next-GGUF \
  UD-Q3_K_XL/Qwen3.8-Flash-Next-UD-Q3_K_XL-00001-of-00003.gguf \
  UD-Q3_K_XL/Qwen3.8-Flash-Next-UD-Q3_K_XL-00002-of-00003.gguf \
  UD-Q3_K_XL/Qwen3.8-Flash-Next-UD-Q3_K_XL-00003-of-00003.gguf \
  --revision 38bb39ee97821de2c9009abb7e93950eec396e66 --local-dir $S/hf/Qwen3.8-Flash-Next-GGUF
printf 'FROM %s\n' "$S/hf/Qwen3.8-Flash-Next-GGUF/UD-Q3_K_XL" > $S/Modelfile.flash-next   # FROM <first shard> fails
ollama create qwen3.8-flash-next-ud-q3kxl -f $S/Modelfile.flash-next
# From the repository root; bench.py needs the full tag for created models, and refuses to start if a model is loaded.
python3 uncensored-models-m5-benchmark/bench.py --repo "$PWD" --label 27b-off --model qwen3.8:27b-q8_0 --think false \
  --modes throughput workload --case-limit 24 --output stock-qwen-m5-benchmark/runs/NEW-27b-off.json
python3 uncensored-models-m5-benchmark/bench.py --repo "$PWD" --label 27b-on --model qwen3.8:27b-q8_0 --think true \
  --modes throughput workload --case-limit 24 --output stock-qwen-m5-benchmark/runs/NEW-27b-on.json
python3 uncensored-models-m5-benchmark/bench.py --repo "$PWD" --label flash-off --model qwen3.8-flash-next-ud-q3kxl:latest --think false \
  --modes throughput workload --case-limit 24 --output stock-qwen-m5-benchmark/runs/NEW-flash-off.json
python3 uncensored-models-m5-benchmark/bench.py --repo "$PWD" --label flash-on --model qwen3.8-flash-next-ud-q3kxl:latest --think true \
  --modes throughput workload --case-limit 24 --output stock-qwen-m5-benchmark/runs/NEW-flash-on.json
```

## Evidence

- [notes.md](notes.md): timestamped log, digests, smoke tests, failures
- [runs/](runs/): one raw JSON record per pass
