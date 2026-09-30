# Stock Qwen on the M5 Max: research notes

Running log. Times are MDT. Host: MacBook Pro Mac17,6, Apple M5 Max, 18 CPU / 40 GPU cores, 128 GB unified memory, macOS 26.5.

## 2026-09-29

- Kody asked (paraphrase): are there stock (non-uncensored) Qwen models capable of running on this Mac; download and test them; also check what is trending on Hugging Face using the `hf` CLI.
- Prior work on this host: [mac-model-benchmarks](../mac-model-benchmarks/) (Sep 22, stock Qwen3-Coder 30B via Ollama 0.32.13 and MLX) and [uncensored-models-m5-benchmark](../uncensored-models-m5-benchmark/) (Sep 27, Ollama 0.34.4, Heretic Qwen3.8-27B Q8_0 scored 24/24 and 96/96 with thinking on at ~18 tok/s). No stock Qwen3.8 has been run on this host before today.
- Web check (Sep 29): Qwen 4 is not released. Alibaba said at Apsara (Sep 22) it is in training and coming "very soon" ([orcarouter summary](https://www.orcarouter.ai/blog/qwen-4-max-lineup-announced-apsara-2026), [yottalabs](https://www.yottalabs.ai/post/qwen-4-release-date-what-is-known-how-to-prepare-2026)). Qwen3.8-Flash-Next is described by Qwen as the first open-weight release of the Qwen 4 architecture ([Qwen blog](https://qwen.ai/blog?id=qwen3.8-flash-next)).
- Selection: stock `qwen3.8:27b-q8_0` from the Ollama registry (same quant as the Sep 27 Heretic row, so those rows are directly comparable), and `hf.co/unsloth/Qwen3.8-Flash-Next-GGUF:UD-Q3_K_XL` (Unsloth lists 90.0 GB, "90 GB" RAM; the 4-bit tiers are 94-111 GB and too close to 128 GB for KV cache headroom, per [Unsloth's guide](https://unsloth.ai/docs/models/qwen3.8-next)). Ollama's own `qwen3.8-flash-next` tags start at 105 GB (nvfp4/mlx) and 120 GB (q4_K_M), so the Unsloth 3-bit is the only Ollama-loadable tier with real headroom.
- Runtime: installed Ollama app 0.34.4 (same as Sep 27), dedicated server on `127.0.0.1:11436`, store `~/Documents/Codex/model-cache/stock-qwen-benchmark/ollama`, env `OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NO_CLOUD=1`. Primary server on 11434 untouched.
- Runner: [../uncensored-models-m5-benchmark/bench.py](../uncensored-models-m5-benchmark/bench.py) unchanged, with `--modes throughput workload` (no refusal pass; Kody asked about capability, not refusals) and `--case-limit 24`, thinking off and on. Same options as Sep 27: temperature 0, seed 42, top_p 1, top_k 40, 8192 context, 2048 output cap thinking off / 8192 thinking on.
- Pulls started in sequence (27B first, then Flash-Next) at ~840 MB/s.
