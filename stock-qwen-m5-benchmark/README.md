# Stock Qwen on the M5 Max: Qwen3.8-27B and Qwen3.8-Flash-Next

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Claude Fable 5.1). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

Measured September 29-30, 2026, on this MacBook Pro: Apple M5 Max, 18 CPU / 40 GPU cores, 128 GB unified memory, macOS 26.5, Ollama 0.34.4 on a dedicated local server. Kody asked whether stock (not uncensored) Qwen models are capable on this Mac, and to download and test them. Earlier reports here covered stock Qwen3-Coder 30B ([Sep 22](../mac-model-benchmarks/)) and five uncensored builds ([Sep 27](../uncensored-models-m5-benchmark/)); this is the first stock Qwen3.8 run on this host.

**Results: pending.** Runs are in progress; this file is updated when they finish. See [notes.md](notes.md) for the live log.

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
