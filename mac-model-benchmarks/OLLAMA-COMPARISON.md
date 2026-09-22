# M5 Max versus RTX PRO 6000: matched local-model comparison

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Kody directed the work; Codex (OpenAI) prepared and ran the local measurements.
<!-- /AI-ASSISTED-NOTE -->

Measured on September 22, 2026, against saved September 11 Windows runs. This is a system-level comparison: Apple Metal on an M5 Max versus CUDA on an RTX PRO 6000 Blackwell Max-Q. Model digests, quantization, template hashes, model parameters, Ollama 0.32.13, prompts, and request settings match. Operating systems, GPU backends, and host conditions differ.

The Mac is a MacBook Pro with an M5 Max, 18 CPU cores, 40 GPU cores, and 128 GB unified memory, running macOS 26.5 (25F71) on AC power. The historical workstation has an RTX PRO 6000 Blackwell Max-Q with 96 GB VRAM, Ryzen 9 9950X, and 128 GB RAM. See [the original report](../local-model-benchmarks/README.md) and the raw host snapshots in each run.

## Matched 24-case workload

| Model | Mode | Mac correct | RTX correct | Mac median s | RTX median s | Mac / RTX latency |
|---|---|---:|---:|---:|---:|---:|
| Qwen3-Coder 30B Q4_K_M | thinking off | 4/24 | 4/24 | 0.631 | 0.444 | 1.42× |
| GPT-OSS 20B MXFP4 | low reasoning | 21/24 | 22/24 | 3.737 | 1.822 | 2.05× |
| Gemma 4 31B Q8_0 | thinking off | 10/24 | 10/24 | 3.811 | 1.856 | 2.05× |

Each row replays the exact first 24 `practical-json-v1` cases: three each for ledger replay, event-state reconstruction, dependency scheduling, SQL analysis, shortest paths, record extraction, Python tracing, and retrieval. One deterministic sample is generated per case. Correctness uses the existing strict JSON grader; generated code is never executed.

Settings: context 8192, temperature 0, seed 42, top_p 1, top_k 40, repeat penalty 1.0. Qwen and Gemma receive a 2048-token output cap; GPT-OSS retains its historical low-reasoning mode and 8192-token cap. These modes are not an equal-budget cross-model quality comparison.

Latency is the median supervised response wall time, including Python subprocess startup; raw records also preserve HTTP round-trip and server timings. Model load and warmup are excluded. A ratio above 1 means the Mac took longer. Same-seed outputs can differ between Metal and CUDA, so score changes are observations from one pass, not evidence that hardware improves model capability.

## Short generation and prompt ingest

| Model | Mac generation tok/s | RTX generation tok/s | Mac / RTX throughput | Mac ingest tok/s | RTX ingest tok/s |
|---|---:|---:|---:|---:|---:|
| Qwen3-Coder 30B Q4_K_M | 136.32 | 302.25 | 0.45× | 2032.8 | 10950.8 |
| Gemma 4 31B Q8_0 | 15.79 | 40.47 | 0.39× | 466.9 | 2529.7 |

Three repetitions after warmup reuse the historical 100-word Rocky Mountains request and roughly 7000-token ingest prompt, with a 512-token output cap. Prompt rates use the runtime-reported token counts; cache-split telemetry is unavailable in these records. These API numbers are not time to first token. GPT-OSS has no thinking-off throughput row because its matched workload uses reasoning.

## Integrity and limitations

- The runner refuses model digest, template, parameter, quantization, or runtime-version mismatches. Parameter group ordering is normalized because Ollama prints map entries in varying order; values and repeated stop sequences must still match.
- Historical Windows files and the nightly policy remain unchanged. This is a separately requested manual Mac run; the canceled Windows campaign is not resumed.
- Each request has a 120-second deadline and each model replay a 30-minute deadline. Failure preserves partial records and attempts model unload.
- One model is loaded at a time. The host is an interactive desktop, not an isolated laboratory machine. GPU utilization is not continuously sampled; operating-system work and thermal conditions are uncontrolled.
- This appendix measures the pinned Ollama configuration. The separate MLX experiment is in README.md; LM Studio, current Ollama, long-context behavior, full coding suites, and energy consumption are not measured.

## Evidence

- Qwen3-Coder 30B Q4_K_M: [Mac raw run](runs/20260922-qwen.json); [Windows workload source](../local-model-benchmarks/runs/20260911-102013-bde53f62.json).
- GPT-OSS 20B MXFP4: [Mac raw run](runs/20260922-gpt-oss.json); [Windows workload source](../local-model-benchmarks/runs/20260911-102255-5507f7e0.json).
- Gemma 4 31B Q8_0: [Mac raw run](runs/20260922-gemma.json); [Windows workload source](../local-model-benchmarks/runs/20260911-130939-8525ec43.json).

See [notes and reproduction steps](notes.md), [replay runner](mac_replay.py), and [comparison data](comparison.json).
