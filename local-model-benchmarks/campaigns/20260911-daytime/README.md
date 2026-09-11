# September 11 daytime local-model benchmarks

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Kody directed the work; Codex (OpenAI) implemented and ran the local measurements.
<!-- /AI-ASSISTED-NOTE -->

The user explicitly requested sustained daytime GPU benchmarking, including worthwhile historical candidates and newly discovered models, until stopped or Codex usage is exhausted. This is a fresh campaign. The canceled September 10 authorization, queue and results remain preserved.

**Completed September 11 at 15:47 MDT.** At the user’s request, the campaign finished the current Granite checks, Nemotron, stock Qwen3.8 Q8, and Apodex, then stopped. There were 130 completed queue entries across 13 tested artifacts/configurations, three incomplete attempts, and 25 deferred entries (23 deferred for wrap-up and two invalid-mode follow-ups). Installed-model public coding sweeps therefore stop at 100 tasks, while the KAT, Nex, Ornith, and Gemma sweeps cover all 163 supported tasks.

[Shutdown verification](completion.json) confirms that the controller and owned workers exited, port 11435 closed, no primary model remained loaded, and all seven personal model digests were unchanged. Campaign authorization is revoked and supervision is closed. The GPU returned to its unloaded desktop baseline. The fixed finish line is recorded in [the wrap-up request](wrap-up-request.json).

Read [current progress](progress.md), [standardized screens](results.md), and [aggregated workload results](workload-results.json). Raw run IDs link each observation to saved prompts, responses, runtime metadata, model digests and cleanup evidence.

## Authorization and controls

[authorization.json](authorization.json) permits daytime starts and multiple candidates in a separate campaign ledger. The original policy file and nightly scheduler are unchanged. The authorized start cutoff was 22:58 MDT and expiry was 23:59 MDT, leaving the original hour-long worker deadline plus cleanup margin. Explicit cancellation takes precedence over those times.

The 35 GiB artifact, 240 GiB task storage, 25 GiB disk reserve and 12 GiB GPU headroom checks remain. There is one GPU job at a time. A separately supervised prefetch may download a pinned GGUF while an installed-model job runs, but imports wait for prefetch completion. Every complete artifact is hash-checked, and partial files remain resumable. Only task-owned cache artifacts can be removed.

## Historical review and new selection

[candidate-audit.json](candidate-audit.json) categorizes all 392 saved registry entries and rechecks every raw-file hash in the prior historical audit. Every old raw hash matched. The registry includes 213 entries outside this text protocol, 91 needing approved mirrors, 29 without an eligible single GGUF, 57 unresolved metadata entries, and two entries marked previously measured. Registry status is not a complete count of installed-model runs or later mirror selections.

The prior campaign's source-reviewed untested selections are retained: KAT-Coder, Ornith, Gemma, Granite, Nemotron, stock Qwen3.8, Apodex and LFM. The installed GPT-OSS screen was run first. Live public HF discovery found an approved [Bartowski Nex-N2.5-mini mirror](https://huggingface.co/bartowski/nex-agi_Nex-N2.5-mini-GGUF), closing a previously recorded mirror gap. Its Q6 file is pinned in [the selection](selections/nex-mini-q6.json). The [upstream model card](https://huggingface.co/nex-agi/Nex-N2.5-mini) describes agentic and multimodal capabilities; this text-only protocol does not measure those capabilities.

GLM-5.3-Flash and Qwen3.8-Flash-Next had no eligible root-level single GGUF within the standing cap in this metadata check. Pantheon is a lower-priority creative-writing/reasoning finetune. GPT-OSS 120B was investigated after the strong 20B result, but its pinned 63.4 GB MXFP4 artifact exceeds the standing 35 GiB cap and is not authorized by this campaign's exceptions. Its proposal is retained for later consideration, not queued or downloaded.

## Methods and evidence limits

The initial candidate sweep retains the existing 8,192 context, temperature 0, seed 42, 512 output-token cap and three-repetition throughput battery, plus the 16-case v2 screen. GPT-OSS uses the separately labeled low-reasoning protocol with an 8,192 output-token cap. LFM's unexpected thinking and truncated outputs invalidate its ordinary comparison.

The broader `practical-json-v1` suite has 96 deterministic authored cases: 12 each for ledger replay, event reconstruction, dependency scheduling, SQL analysis, shortest paths, extraction, Python tracing and retrieval. [workload_suite.py](../../workload_suite.py) creates the fixtures; [workload_screen.py](../../workload_screen.py) saves and grades exact JSON responses. The JSON-answer suite never executes generated model code. Trusted SQL fixtures are computed with SQLite; trusted Python tracing fixtures have an independent execution check.

Workload runs use the same 8,192 context, temperature 0 and seed 42. Thinking-off requests allow 2,048 generated tokens. Reasoning-enabled requests allow 8,192 generated tokens. Each case has a 120-second client deadline within the shared worker deadline. Four separately recorded blocks cover the 96 cases. Thinking modes and different suites are not pooled, and partial blocks are not presented as completed scores. Latency includes response generation and the local client round trip; model load/warmup is saved separately.

This is not a standardized coding benchmark, repository-editing evaluation, statistically established model ranking, or a claim about production agent quality. It is a reproducible personal workload screen. MTP/DFlash and custom model templates remain part of the installed configurations.

## Implementation and validation

- Normal `Harness.window_open()` preserves the overnight rule; only fresh daytime `CampaignHarness` authorization overrides it.
- Launchers ignore stdout JSON when scanning supervisor records, fixing an empty canceled-output file that blocked the first launch.
- Queue and report tools accept a campaign identifier while retaining old defaults. Canceled queues refuse advancement.
- Prefetch and GPU launch admission share a lock; prefetch never imports models or starts inference.
- Relevant offline tests cover authorization, changed policy/refusal, normal quota preservation, queue progression, the stdout regression, deterministic fixtures, exact grading, truncation/mismatch and cleanup. The full validation result is recorded in notes.

No public push or publication is part of this request. Results and commits remain local.

The launch authorization now references a small supervision record. The agent renews a 30-minute lease after checking available usage; expiry or zero recorded usage refuses new starts. Existing workers retain their hard deadline and cleanup. `stop_campaign.py --campaign 20260911-daytime --reason "User requested stop"` revokes authorization and stops only identity-verified campaign processes. Its `--dry-run` mode is read-only. `daytime_progress.py --output-dir PATH` rebuilds the readable progress snapshot and samples GPU telemetry.

## Separate function-writing screen

`javascript-functions-v1` asks for eight JavaScript functions and checks 99 hidden deterministic inputs. These cover deduplicated ledgers, versioned state, interval merging, topological ordering, TTL caches, JSON pointers, CSV parsing, and recursive redaction. All trusted reference solutions passed all 99 fixtures before the model pilot.

Generated functions execute only in QuickJS WebAssembly through quickjs-emscripten 0.32.0. No host functions or module loader are exposed. Every hidden test gets a fresh guest runtime with 64 MiB memory, a 512 KiB stack, and a 300 ms interrupt deadline. Host-access probes and infinite-loop interruption passed. A dependency lock is saved alongside this report.

This screen requests 16384 context, temperature 0, seed 42, and 4096 output tokens with thinking off or 8192 with reasoning. Each generation has a 240-second deadline and each grading subprocess a 30-second deadline within the original one-hour worker limit. A whole Markdown code fence may be removed and is recorded. Input mutation, truncation, wrong output types, and functional mismatches fail. A task passes only when all its hidden checks pass; correlated checks are not independent evidence.

The Qwen3-Coder pilot completed with 5/8 fully correct functions and 90/99 checks, 0.961 seconds median generation response, no truncation, and verified unloading and unchanged personal model digests. This is distinct from its JSON mental-computation results. Follow-ups compare GPT-OSS, Qwen3.5, Qwen3.8, KAT, and Nex with reasoning modes kept separate. The full harness regression suite passed 145 tests after this addition.


## Published coding dataset extension

[HumanEval-X source and adaptations](../../fixtures/humaneval-x/README.md) document the pinned Apache-licensed 164-task JavaScript set, the 163 tasks supported in the isolated WASM runtime, three repaired upstream test invocations, seeded test randomness, and reference validation. A continuation pilot exposed formatting failures and is preserved separately from the subsequent complete-program chat protocol. These results are kept separate from the eight authored functions and the JSON-answer workload, with public-dataset training overlap noted as an evidence limit.


## Budget sensitivity and observed runtime controls

Nex returned exactly identical message objects across all 24 first-block workload cases with think:false and think:true. Its ordinary comparison is therefore invalid as a thinking-off comparison; explicit reasoning results are kept, and additional thinking-off coding follow-ups are deferred. The valid explicit-reasoning run completed all 96 workload cases at 86/96 without truncation. Its initial eight-function screen was much weaker (2/8 tasks, six truncated responses), so published-task scores and authored-task reliability remain separate.

Nex and Qwen3.5 have separately queued repeats of the same eight authored functions with 32768 context and a 16384 output-token allowance after multiple 8192-token truncations. These are different configurations, not equal-budget comparisons. The generation deadline remains 240 seconds per task within the original one-hour worker deadline. Budget validation, actual request settings, context restoration, and unloading are tested.

Host conditions were not held constant: metadata downloads, report generation, reference-fixture tests, and brief browser QA with GPU rendering disabled overlapped some GPU runs. Latency is descriptive for this workstation session; no statistical-significance or dedicated-host claim is made.


## Nex sampling diagnostic

The [publisher model card](https://huggingface.co/nex-agi/Nex-N2.5-mini) recommends temperature 0.7, top_p 0.95 and top_k 40. Saved greedy failures include long repeated paragraphs and repeated zero sequences, so a separately labeled eight-function repeat uses those settings at the original 16384 context and 8192 output cap. Seed 42 and repeat_penalty 1.0 remain fixed. The native Ollama think boolean did not disable reasoning in the paired observations; its imported Jinja template branches on reasoning_effort. This is a runtime/template compatibility limitation, not a conclusion that the model cannot disable thinking. Ninety-nine focused regression tests passed after the sampler addition.
