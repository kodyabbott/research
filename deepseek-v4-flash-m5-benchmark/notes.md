# Research and execution notes

## Scope and artifacts

The user requested a DeepSeek V4 Flash test and additional models that may excel on this M5 Max. After requesting a stop, the user resumed the work and asked about temperature/fan monitoring. The completed earlier speed trials and chat screen are retained; the resumed run adds thinking-mode evaluation and telemetry.

- Model: `mlx-community/DeepSeek-V4-Flash-0731-2.4bit-mixed` at `10001e0065f8394e03e968e652cbbe7cd2ca122c`.
- Weight tensors: 92,831,787,464 bytes; 24 downloaded files verified against LFS SHA256 or Git blob SHA1. The manifest also records SHA256 hashes.
- The cache is `/Users/kody/Documents/Codex/model-cache/mac-benchmarks/mlx/DeepSeek-V4-Flash-0731-2.4bit-mixed`.
- The [conversion card](https://huggingface.co/mlx-community/DeepSeek-V4-Flash-0731-2.4bit-mixed) specifies "oMLX 0.5.7 or newer." This is the relevant deployment constraint; Hugging Face's generic auto-generated MLX snippet is not sufficient.
- Initially inspected oMLX source at `8288884d9b4f6db7b547633a94d36794c6b1d52d`. It was installed in an isolated source environment but was not used for reported inference.
- The source-only installation lacks compiled native indexer kernels without the full Metal toolchain. This host has Command Line Tools, not full Xcode. Used the [official oMLX v0.6.4 release](https://github.com/jundot/omlx/releases/tag/v0.6.4) Python 3.12 wheel instead.
- Release wheel SHA256: `f13d92900bf6c7e925e9a6d5525b4465c615c404ee796d328ffc5d4d379ddb0b`, matching the GitHub release asset digest.
- The actual release environment uses MLX 0.32.0 and MLX-LM 0.31.3 at `ab1806e8f5d6aa035973af194a1b9198ab4754dc`. This differs from the source checkout's dependencies and from the earlier MLX comparison environment. Full dependency pins are retained.
- Both `dsa_indexer_scores` and `dsa_topk_indices` were confirmed available before running inference. No speculative decoding, model-generated code execution, or cross-request prefix cache was used.

## Protocol and changes

1. Reused the exact first 24 `practical-json-v1` cases and strict JSON grader from the cloned research repo. The runner asserts equality with the saved GPT-OSS reference prompts and expected answers. Categories are ledger, event state, scheduling, SQL, graph paths, extraction, Python traces, and retrieval.
2. Temperature 0, seed 42, top_p 1, top_k 40; chat cap 2048 and thinking cap 8192. Native architecture caches and 2048-token prefill steps. Different cache architecture, conversion, tokenizer, and runtime preclude a runtime-only comparison.
3. Completed warmup and three short/ingest speed trials: 100-word Rocky Mountains prompt and a 7018-token repeated-text input. Completed all 24 chat cases: 5 passed; one hit the token cap.
4. User requested stopping. Processes were terminated and the original record marked `stopped_by_user`. Only fully saved responses are represented. These results are preserved separately from later work.
5. On resume, installed `macmon` 0.8.2 and checked actual CPU/GPU temperature readings and both fan RPM values. Logged one-second JSON records during a thinking-only run. No fan control or background service was enabled.
6. The first greedy thinking case (`ledger-0`) entered a repetitive output loop, hit 8192 tokens, and returned no final answer. It took 242.36 seconds at a reported 33.98 generation tok/s. Ended the second in-flight case to investigate sampling; retained the first complete diagnostic and its telemetry separately.
7. [DeepSeek's official card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731#how-to-run-locally) recommends "temperature = 1.0" and "top_p = 1.0" for local non-agentic scenarios. Started a separately labeled 24-case thinking pass with those sampling settings, unrestricted top_k, low reasoning effort, seed 42, and the same 8192-token output cap. This is not the same protocol as the old nightly baseline and must not be pooled with it. A 300-second per-case timeout is recorded as incomplete output if reached.

The `sql-0` response in the sampled thinking pass illustrates an output-protocol failure: it emitted two closing thinking delimiters, an earlier incorrect answer, and later the correct SQL result. The runner requires one unambiguous closing delimiter and grades only the final channel; it does not salvage a correct answer from contradictory earlier output. This case is therefore a strict protocol/format failure, not evidence that its last numerical answer was wrong. Raw output is retained for inspection.

The `sql-2` final answer contained the expected values but one extra closing bracket, so it was invalid JSON. This is also counted as a strict failure. Neither response was repaired before scoring.

## Monitoring

[macmon's documented capabilities](https://github.com/vladkens/macmon) include "Average CPU / GPU temperature" and JSON output. It uses macOS sensor APIs without requiring root. `powermetrics` exists on this host but requires superuser access and its listed thermal sampler reports pressure; it was not used for these temperature/RPM traces.

The initial preflight at 16:47 local was approximately 38°C CPU, 39°C GPU, and both fans at 0 RPM. Under the resumed greedy diagnostic, both fans increased through roughly 1500 RPM to about 5350/5780 RPM as the GPU warmed. These changing readings establish functioning sensors on this host. Temperature values are sensor averages, not calibrated hottest-die measurements. GPU clock and power are software estimates. A high temperature by itself does not establish thermal throttling.

The sampler records baseline, loading, warmup, inference, and brief post-run cleanup. Per-case timestamps permit approximate alignment to one-second samples. The original speed/chat run predates monitoring; its temperatures cannot be reconstructed from later measurements. The sampled thinking pass starts after an earlier load, not from a controlled cold state. Monitor overhead was not measured separately.

For a live terminal view, use `macmon`. For a finite reusable log, use `macmon pipe -i 1000 -s 600 > thermal.jsonl`. This logs ten minutes and exits. No startup automation was configured.

## Additional models and source checks

The [additional-model report](OTHER-MODELS.md) lists purpose-specific candidates with pinned artifact byte totals. These are recommendations for evaluation, not locally established category winners. [Candidate metadata](candidate-metadata.json) records revisions and byte totals; weight files were not downloaded for these candidates.

Primary evidence supporting selection:

- [Muse Glimmer](https://huggingface.co/meta-models/Muse-Glimmer-30B): "purpose-built for autonomous agentic tasks on consumer hardware". The official M5 Max speed table uses K-Quant-17GB plus DFlash, not the linked MLX 8-bit artifact. The [conversion card](https://huggingface.co/pipenetwork/Muse-Glimmer-30B-MLX-8bit) requires a supporting runtime; stock loading is not assumed.
- [Nemotron 3 Super](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16): "Agentic workflows, long-context reasoning". The MLX conversion card identifies its upstream base and MLX-LM conversion version.
- [Qwen3.5-122B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B): model architecture and text/vision support establish it as a larger alternative. No claim that it beats newer Qwen3.8 is made.
- [Devstral Small 2](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512): "Agentic Coding"; the card's benchmark table reports 68.0 SWE-bench Verified. Framework and quantization differences prevent direct transfer to this host.
- [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash): "30B-A3B MoE model". The LM Studio community artifact provides a documented 8-bit Apple Silicon conversion.
- [LFM2-24B](https://huggingface.co/LiquidAI/LFM2-24B-A2B): "We don't recommend using it for coding". This narrows the recommendation to fast chat, tool use, and retrieval-assisted answers.
- [MiniMax M2.7](https://huggingface.co/MiniMaxAI/MiniMax-M2.7): "Professional Software Engineering". Its 3-bit weight total is ~100 GB; local quality and loaded-memory behavior remain untested.
- [Granite 4.2](https://huggingface.co/ibm-granite/granite-4.2-3b-q4-mlx): "structured JSON output". The official MLX artifact supports consideration as a small extraction/RAG baseline.
- [VISTA](https://huggingface.co/inclusionAI/VISTA-9B) specializes in GUI grounding. However, the checked [MLX conversion](https://huggingface.co/pipenetwork/VISTA-9B-MLX-8bit) says "Text-only build of the backbone." Removed it from the install shortlist because that artifact does not establish image input support.
- [Nemotron TwoTower port](https://huggingface.co/pipenetwork/Nemotron-Labs-TwoTower-30B-A3B-mlx-4bit) requires its custom diffusion entry point. Its published M3 Ultra measurements are not evidence of high M5 Max throughput; it remains a research curiosity here.

Remaining scope limits: no sustained power-mode comparison, no energy-efficiency ranking, no native full-precision quality control, no tool-execution or full software-engineering benchmark, and no additional model downloads during this survey. Claims about quantization causing errors remain hypotheses because no higher-precision DeepSeek control was measured.
