# Stock Qwen on the M5 Max: Qwen3.8-27B and Qwen3.8-Flash-Next

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Claude Fable 5.1). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Measured September 29-30, 2026 (MDT), on this MacBook Pro: Apple M5 Max, 18 CPU / 40 GPU cores, 128 GB unified memory, macOS 26.5, Ollama 0.34.4 on a dedicated local server. Kody asked whether stock (not uncensored) Qwen models are capable on this Mac, and to download and test them. Earlier reports here covered stock Qwen3-Coder 30B ([Sep 22](../mac-model-benchmarks/)) and five uncensored builds ([Sep 27](../uncensored-models-m5-benchmark/)); this is the first stock Qwen3.8 run on this host.

**Result: both stock models are capable here, and Flash-Next is the better pick.** With thinking on, stock Qwen3.8-27B Q8_0 and Qwen3.8-Flash-Next at 3-bit both solved all 24 cases. Flash-Next did it in 8.7 minutes at about 49 tok/s; the dense 27B took 19.2 minutes at about 18 tok/s, so Flash-Next generates 2.7x faster and finishes the 24-case pass 2.2x sooner. With thinking off, Flash-Next scored 9/24 and the 27B 8/24, and Flash-Next's 24-case wall time was 41 s against 118 s. The stock 27B matched the Sep 27 Heretic build exactly in both modes (8/24 and 24/24), so on this suite the uncensoring cost nothing and there is no reason to prefer the uncensored build for capability.

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

\* Thinking consumes the 512-token cap, so the short trials are truncated with thinking on (same as the Sep 27 thinking-on rows). Generation rates are runtime-reported (`eval_count / eval_duration`).

## Comparison with earlier runs on this host and on Windows

| Qwen3.8-27B build | Mode | First 24 | Median gen tokens | Source |
|---|---|---:|---:|---|
| Stock Q8_0, this Mac, Ollama 0.34.4 | off / on | 8 / 24 | 63.5 / 903 | this report |
| Heretic Q8_0 (llmfan46), this Mac, Ollama 0.34.4 | off / on | 8 / 24 | -- / 865 | [Sep 27](../uncensored-models-m5-benchmark/) |
| Stock BF16, Windows RTX PRO 6000, Ollama 0.32.13 | on | 24 | 946.5 | [Sep 11 run](../local-model-benchmarks/runs/20260911-104941-c75692e6.json) |

The thinking-off score is unchanged across the stock and Heretic builds, and thinking on is at the suite ceiling for all three, so this suite cannot rank them; it does show no capability loss from either the Heretic ablation or the Mac Q8_0 quantization at this resolution.

## Caveats

- Flash-Next's GGUF declares `requires 0.35.0`; the server is Ollama 0.34.4. It loaded, answered correctly, and honored thinking control in both directions, but some architecture feature may be unsupported in 0.34.4. These numbers are for this Ollama version.
- Flash-Next loaded as 47.7 + 38.1 GB Metal buffers plus a 27.5 GB CPU-mapped buffer (server log). I believe the CPU buffer is the 3-bit n-gram embedding table (`qwen4exp.ple.ngram_size = 3`) but have not confirmed which tensors it holds. `ollama ps` reported the model at 40 GB, which does not match the loaded buffers; I did not use that figure.
- Flash-Next used the GGUF's embedded Jinja chat template (`template selection … selected=gguf_chat_template`); `ollama show --modelfile` shows only a passthrough `TEMPLATE {{ .Prompt }}`, which is misleading but not what the server used. The vision projector was not attached.
- Thinking on used greedy decoding at 8,192 context; model cards recommend sampling (temperature 1.0, top_p 0.95, top_k 20) for thinking. The 24-case screen is an answer-quality check, not a coding benchmark or a general ranking; a coding harness is being built separately ([coding-benchmark-harness](../coding-benchmark-harness/)).
- One interactive desktop session; no energy, thermal-throttling, or long-context measurements. `pmset -g therm` recorded no thermal or performance warnings before or after each pass.

## Models

| Model | Source | Quant | Size on disk | Notes |
|---|---|---|---:|---|
| Qwen3.8-27B (dense, Aug 14, 2026) | Ollama registry `qwen3.8:27b-q8_0` | Q8_0 | 29 GB + 931 MB vision projector | Same quant as the Sep 27 Heretic row, so those two rows compare directly |
| Qwen3.8-Flash-Next (125B MoE, 6B active, Aug 24, 2026) | [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/38bb39ee97821de2c9009abb7e93950eec396e66) `UD-Q3_K_XL` | 3-bit dynamic | 89 GB (three shards) | Qwen calls this the first open-weight release of the Qwen 4 architecture. Ollama cannot pull sharded GGUFs from hf.co; imported with `ollama create` from the shard directory |

Why 3-bit for Flash-Next: Unsloth's 4-bit tiers are 94-111 GB and Ollama's own tags start at 105 GB, which leaves too little of the 128 GB for KV cache; UD-Q3_K_XL at 90 GB is the largest tier with real headroom ([Unsloth guide](https://unsloth.ai/docs/models/qwen3.8-next)). Low-bit quality loss is one of the things this run measures.

## Method

Same runner and settings as the Sep 27 report ([bench.py](../uncensored-models-m5-benchmark/bench.py), unchanged): 24-case `practical-json-v1` workload (three cases each of ledger replay, event reconstruction, scheduling, SQL, shortest paths, extraction, Python tracing, retrieval), strict JSON grading, generated code never executed; throughput battery of three warmed repetitions of a short generation and a ~7,000-token ingest. Temperature 0, seed 42, top_p 1, top_k 40, 8,192 context, 2,048-token output cap with thinking off and 8,192 with thinking on. The refusal pass was not run. Each model runs thinking off and thinking on.

Dedicated server: `OLLAMA_HOST=127.0.0.1:11436`, own model store, `OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NO_CLOUD=1`. One model loaded at a time; smoke tests are excluded from timing; no download or import overlapped a timed pass.

## Evidence

- [notes.md](notes.md): timestamped log, digests, smoke tests, failures
- [runs/](runs/): one raw JSON record per pass
