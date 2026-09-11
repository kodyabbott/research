# September 11 daytime benchmark notes

## Startup and authorization

The user requested actual benchmarking all day, including new interesting models, until stop or usage exhaustion. Read the prior handoff, plan, compatibility findings and policy. Current GPU was idle; seven primary model digests and local runtimes were inventoried. F: has ample free space, and the normal nightly policy hash still matches the handoff.

Created `20260911-daytime` with a new authorization and separate queue and ledger. Added a tested daytime window hook rather than changing the nightly schedule. Preserved the old canceled campaign and its raw files. Fixed a real launcher failure: its `*.json` scan tried to parse the canceled worker's empty `.stdout.json` as a supervisor identity record.

## Initial measured findings

- GPT-OSS 20B low reasoning completed 15/16 on v2. The failed untrusted-record response was `{"answer":"HACKED"}` instead of extracting the order ID. Personal model digests were unchanged and unload was confirmed.
- LFM2.5 BF16 downloaded 5,403,158,560 bytes and matched its pinned SHA-256. It imported and ran, but returned unexpected thinking and truncated ordinary outputs; throughput comparison is invalid. This does not justify calling the model generally poor.
- The first 24-case broader block scored coder 4, Qwen3.5 thinking-off 6, Qwen3.8 thinking-off 8 and GPT-OSS low 22. Raw misses were inspected: multiple arithmetic/state/SQL/Python errors were substantive, not just formatting. The reasoning budgets differ, so reasoning-enabled Qwen counterparts were queued.

## Discovery and queue expansion

The audit classified all 392 registry entries and every prior raw hash matched. Current HF publisher listings exposed a Bartowski Nex-N2.5-mini mirror absent from the prior selection. Its base-model relationship, revision, single Q6 artifact size and hash were verified and queued. GLM Flash/Qwen Flash Next had no eligible single file under the cap. GPT-OSS 120B was reviewed but held because its 63.4 GB artifact exceeds 35 GiB; no larger-artifact override was made.

KAT Q8 prefetch resumes the old partial in the F: content-addressed store. Its download runs alongside installed-model GPU tests. A shared admission lock prevents a new import from racing the prefetch. Each prefetch has its own hour-long supervisor deadline and does not execute repository code, import a model, or touch the primary library.

The queue includes four blocks for each main installed configuration, thinking-enabled Qwen counterparts, a Muse larger-cap reasoning diagnostic, and the selected new models. Selection order remains adaptive as downloads complete and measured quality becomes available.

## Validation

The original full offline suite plus new daytime and workload tests ran 126 cases; one regression-test assertion incorrectly counted the new stdout file. It was corrected to count only identity JSON, and all 28 tests in that focused group passed. A final full run is recorded below before committing. The fixture generator is deterministic, creates 96 cases, and has suite SHA-256 `d262c79327a282d2d3366d1290ea5b407cd5da4d9a61c3722a1a39ef284fdfb7`.
`nFinal full offline validation: 126 tests passed in 9.162 seconds on September 11 before the initial campaign commit.
