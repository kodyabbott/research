# Harness validation - 2026-09-10

The approved revision is deployed in the scheduled research checkout. Python 3.14.7 is
installed per user, all 58 regression tests pass, and live download/import, retention,
admission-refusal, and deadline checks have completed. Final peer acceptance is pending.

## Live evidence

| Check | Result and raw evidence |
| --- | --- |
| Full new-model transaction | [Qwen3 Q8](runs/20260910-180727-aa184d4f.json): verified 804,753,632 bytes and SHA-256, F: import, three repetitions, separate thinking probe, candidate unload, primary baseline, child shutdown, and unchanged primary digests. Comparison valid. |
| Duplicate refusal | [Repeat fixture](runs/acceptance-20260910-final-duplicate.json): exit 1, no download, identical artifact inventory and ledger, classified as an admission failure. Failed attempts continue to consume the daily slot. |
| Unrelated listener | [Occupied 11435](runs/acceptance-20260910-port.json): admission refused; the test listener remained owned and reachable until the test closed it. |
| Three real imports | [SmolLM2 Q8](runs/20260910-184818-ab6a4fc4.json) and [Q4_K_M](runs/20260910-185031-51e74d87.json) completed. The third import deleted only the oldest Qwen fixture and released its reservation. |
| Hard deadline with model loaded | [Final retest](runs/20260910-190628-cd33e998.json): expected exit 124, recorded loaded model, portFree=true, vramRecovered=true, ownedProcessExited=true, and a recorded shutdown time/reason. |
| Post-run cache audit | [Ordinary Windows process audit](runs/acceptance-20260910-cache.json): exactly two matching retained imports, oldest absent, downloads empty, primary unchanged, child exited, private port free, and no nightly quota used. Before orphan reconciliation the cache charge was 500,533,570 bytes. |
| Verified upload cleanup | [Live reconciliation](runs/acceptance-20260910-upload-cleanup.json): deleted exactly two known, unreferenced uploads (250,265,792 bytes), journaled both, preserved both model digests and the primary library, and reported no errors. Final cache charge: 250,267,778 bytes. |
| Runtime and deployment | [Deployment evidence](runs/acceptance-20260910-deployment.json): normal Windows and Claude see the user-owned runtime, repo/F: state is visible outside app virtualization, prompt hashes match, and the task editor shows Fable 5.1 with the research folder and daily 9 PM schedule. |

The first deadline report is preserved as [failed acceptance evidence](runs/20260910-185239-04f5464a.json).
It sampled the port immediately after taskkill and reported portFree=false. A direct follow-up
found the child gone and only TCP TIME_WAIT entries. Commit 541ec15 now polls both port release
and VRAM within the existing bounded recovery window. The regression suite and live retest pass. Commit d66e72b additionally records the owned process exit and final shutdown state; the final retest above exercises that version.

The acceptance fixtures use a separate ledger allowing three distinct artifacts no larger than
2 GiB. These runs did not consume the one nightly candidate slot. The two SmolLM files replaced
the larger proposed Qwen Q4/BF16 retention fixtures to reduce transfer cost; those larger files
were never downloaded. Model cards and pinned file metadata were read before admission.

## Measurement limits and interpretation

These are plumbing fixtures, not recommendations for Kody's daily use. Qwen passed 1/3 exact
checks and each SmolLM variant passed 0/3; the installed coder baseline passed 3/3 in all three
transactions. SmolLM Q4_K_M hit the output cap during one ingest trial. Its comparison is
correctly invalid, while its completed import and eviction remain valid retention evidence.
Do not publish that run as a clean performance comparison.

The Qwen thinking-enabled probe completed separately: 273 total generated tokens, 724 thinking
characters, 608 answer characters, and 558.3 ms client time (1.66 times its thinking-off median).
Characters are not token counts and this is one trial. The primary Ollama environment is not
verified identical to the private child's allowlisted environment. Templates/tokenizers differ;
three repetitions do not establish a leaderboard. Both servers reported Ollama 0.32.13 and
loaded-model metadata recorded context 8192 and GPU allocation. Vision remains unmeasured.

No model weights were stored on C: by the harness. C: free-space deltas also reflect other
Windows processes, and the small run/state logs remain in the research repo. The private Ollama
store can rewrite a GGUF during import. Admission reserves download, uploaded source, and rewritten
layer copies. The narrowly verified cleanup removes only an unreferenced uploaded source whose
ownership, size, hash and manifest checks pass. Other orphan blobs remain charged for manual review. The existing personal model library was not moved.

## Runtime setup and reproduction

The Python Software Foundation-signed 3.14.7 installer matched its published SHA-256. Setup
completed from an ordinary hidden Windows PowerShell process after the packaged-app invocation
failed because Windows Installer could not see its redirected payload. No app permissions or
Windows Installer security settings were changed. The successful test summary is written to
stderr by unittest, so setup captures both streams and checks the process exit code before
setting NIGHTLY_BENCH_PYTHON. Python reports 3.14.7 from the per-user Python314 path.

From this directory, use the configured interpreter for `-m unittest -q test_nightly.py`.
The human acceptance commands are `acceptance.py --fixture <selection.json>` and
`acceptance.py --deadline-smoke`; the latter intentionally returns 124. Selection contents,
exact source URLs, revisions, hashes, parameters and raw outputs are in the linked run files.
The refusal evidence describes its before/after checks; the occupied-port fixture used a
separate local socket on 11435 and the deployed `--validate-candidate` command. The cache audit
opened only the harness-owned secondary host and compared tags/digests with recorded imports.

## Earlier validation, before peer review

The earlier implementation passed 27 offline tests, metadata-only admission, and a manual
[baseline battery](runs/20260910-162636-63916c19.json). A [150-model discovery](runs/20260910-163056-170607ea.json)
enriched 40 entries and left 348 pending. Those results do not establish live import or eviction;
the evidence above supplies those checks for the deployed peer-reviewed revision.

## Sources for the acceptance fixtures

- [Qwen GGUF repository](https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF) and [upstream model](https://huggingface.co/Qwen/Qwen3-0.6B).
- [SmolLM quantizer's pinned card](https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/blob/09816acd5d99df7be770d85ea30822623dab342c/README.md) and [upstream model](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct).
- [Python 3.14.7 release](https://www.python.org/downloads/release/python-3147/).
- [Microsoft MSIX runtime explanation](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes): background on app-data virtualization.
## Deployed discovery sweep

The [final discovery sweep](runs/20260910-185636-50c64731.json) ran through the PowerShell 5.1
wrapper with Python 3.14.7 and no cache fallback. All six trending sources succeeded; it saw
150 entries and attempted 100 detail lookups. Four detail requests returned HTTP 429, so the
run correctly reported partial and retained 253 pending entries. No retry loop ran. This is
preserved partial-coverage evidence, not a claim that the metadata backlog is drained.