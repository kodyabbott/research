# Peer review of the nightly benchmark harness

Status: accepted by Codex and the original Claude Fable 5.1 reviewer for the authorized bounded nightly experiment. The approved revision is deployed, 58 tests pass, and live acceptance is complete. Historical entries below record earlier gates; see validation.md for the evidence.

Kody requested collaboration with the existing Claude Fable 5.1 session
`68591a9a-964d-4e81-88ff-e4934174c051`. Codex sent peer messages to that session through
Claude Code's authenticated local message router and read the responses in the same
session transcript. This was not a replacement reviewer session.

## Review decisions on 2026-09-10

- Use a dedicated Ollama child and model cache on F:, leaving the primary library in place.
- Measure actual cache bytes, including orphaned blobs; journal removals and release
  reservations rather than accumulating historical reservations indefinitely.
- Resume interrupted GGUF downloads and verify the entire artifact's size and SHA-256.
- Keep throughput trials fixed and put a capped thinking trial outside their medians.
- Capture only an allowlist of performance environment variables. The primary environment
  remains an explicit comparison limitation. Do not record credentials.
- Treat the small Qwen fixture as a plumbing test, not a utility recommendation.
- Treat novelty claims and historical reasoning-token interpretations as unverified.
- Keep optional vision work outside acceptance for this text benchmark.

Fable's code review found lifecycle defects beyond the initial design review: shell timeout
exposure, orphaned child recovery, failed-model retention, and cleanup invalidating completed
measurements. The staged revision addresses these with detached execution and polling,
exact process-identity checks, terminal-failure eviction, and separate cleanup error fields.

## Verification so far

51 offline tests pass under the existing Python 3.12 runtime. They include actual Windows
processes for detached execution, file locking, deadline termination, an HTTP stall, and
birth-time ownership checks, environmental-abort retention, and graceful cleanup after the
work deadline. Fable independently verified that the detached child survives a Claude Desktop
shell tool call. Cleanup tests simulate three completed imports and failed
imports against a constrained secondary endpoint; they are not yet live Ollama eviction tests.

The Python 3.14.7 installer was downloaded from the official release, matched the published
SHA-256, and had a valid Python Software Foundation Authenticode signature. Installation
has not been performed. The scheduled checkout and task remain unchanged.

## Remaining acceptance evidence

1. Run the suite under the approved user-owned Python with no Codex runtime dependency.
2. Perform a real pinned GGUF download to F:, import through the secondary host, candidate
   battery, unload/VRAM recovery, primary baseline, child shutdown, and primary digest check.
3. Demonstrate duplicate/daily admission refusal without a new download.
4. Exercise live eviction with three small fixture imports and verify only the oldest goes.
5. Kill a deliberately stalled worker with a real model loaded and verify the port and VRAM.
6. Verify the deployed/versioned prompt hashes and app-side scheduled model activation.
7. Obtain Fable's review of the final diff and raw live evidence; record any remaining limits.

The proposed 35 GiB artifact cap, 240 GiB cache, and Python installation are awaiting Kody's
approval under the existing task's explicit boundary for limit expansions and new software.

Fable verified that the current Desktop task update tool does not expose a model field.
The staged prompt therefore reports model mismatches for correction in the UI instead of
requesting an unsupported tool update. The saved on-disk model was already set to Fable 5.1
in the earlier deployment; active in-memory task selection has not been verified here.

## Final code review, 2026-09-10 17:50 MDT

Fable's conclusion was: "No code blocker remains before the live acceptance sequence."
It explicitly withheld project acceptance pending live evidence and Kody's approval.
Fable reran all 51 tests, confirmed the final lifecycle and eviction fixes, and accepted
the correction about text-retry ordering and the limits of the scheduler-gap evidence.

A final focused offline check also expired the discovery budget after one successful detail
lookup. The result was partial and the successful lookup remained in the saved registry.
The existing per-row exception handler already handles that timeout; no further code change
was needed. Untyped/non-text backlog entries can still wait behind new candidates.

The tested source is preserved in local commit 36a54c6 on codex/nightly-peer-review; the
review documentation is committed separately. The scheduled checkout remains at dfd44e8.
Nothing has been pushed, installed, downloaded as model weights, or activated in this round.

## Approved activation, 2026-09-10 18:06 MDT

Kody approved proceeding with the 35 GiB artifact limit, 240 GiB F: cache retaining two
completed models, per-user Python 3.14.7, and live acceptance. The signed installer initially
failed under the app's package identity: its MSI payload was redirected into the private
AppData cache and Windows Installer reported path-not-found. Running the same setup script
in a hidden, ordinary Windows PowerShell process created through Win32_Process resolved
that installation failure without changing app permissions or Windows Installer settings.

The initial captured setup output also exposed PowerShell 5.1 treating unittest's successful
stderr summary as NativeCommandError. Setup now captures the test process's stdout/stderr
in files and checks its exit code. The corrected setup completed, all 51 tests passed in
8.136 seconds under Python 3.14.7 with Codex runtime directories removed from PATH, and the
normal Windows process set NIGHTLY_BENCH_PYTHON to the per-user installation. Live benchmark
acceptance remains pending at this point. Run installation from an ordinary Windows shell,
not a packaged app shell, if repeating setup on another machine.
### Live deadline finding, 2026-09-10 18:53 MDT

The first deliberately stalled live worker was terminated, and VRAM recovered, but raw
run 20260910-185239-04f5464a recorded portFree=false. A direct follow-up found no listening
socket or surviving owned Ollama process; only TCP TIME_WAIT entries remained. The supervisor
sampled the port immediately after taskkill and never refreshed that sample while checking
GPU recovery. It now polls both port release and VRAM in the existing bounded recovery
window. A regression test reproduces delayed port release after VRAM is already free.
All 52 tests pass under Python 3.14.7 (8.399 seconds). The failed acceptance report is retained;
a fresh live deadline run is required before closing this finding.
## Live acceptance follow-up

The final deployed source includes the deadline port-polling fix (541ec15), durable shutdown
record finalization (d66e72b), verified upload-orphan cleanup and three-copy admission (1a4c038),
admission failure classification (e5c0ad1), invalid-comparison reasons (7deb6ab), and explicit
whitespace grading documentation (4176afa). All 58 tests pass under Python 3.14.7.

Fable reviewed the cleanup code against the real store and reported no blockers to live
verification. It independently confirmed that the recorded Ollama digests equal the SHA-256
of the corresponding manifests. Live reconciliation then removed precisely the two known
unreferenced uploads, 250,265,792 bytes, on its first cleanup pass with no cleanup errors.
Both retained model digests and all seven primary digests were unchanged. The final loaded
worker deadline test records portFree, vramRecovered and ownedProcessExited as true, with
stoppedAt and hard-runtime-limit as the stop reason. No candidate quota was reset or bypassed.

The full, current evidence is indexed in validation.md. The active routine's editor/model menu
was visually inspected by Codex and showed Fable 5.1 and daily 9 PM in the research folder.
The redundant UI Save was rejected by automatic review, so the dialog was canceled and no
UI settings were changed. The already-correct settings were verified read-only; the subsequent
prompt deployment only synchronized the separately reviewed versioned instructions.

A peer-message approval rejection was resolved by verifying that the live session UUID matched
the user's quoted original review and narrowing the message to benchmark commit IDs and a
review request. The authorized existing session received the update. No unrelated session was
contacted, and no credentials or unrestricted environment dump was shared.

The primary runtime environment remains an explicit comparison caveat. The final discovery
sweep was partial after four HTTP 429s, with 253 metadata entries still pending. These limits
are documented, and neither is represented as successful coverage or laboratory isolation.
The final project sign-off below closes this evidence review.
## Final project acceptance - 2026-09-10 19:11 MDT

The original Fable 5.1 session (68591a9a-964d-4e81-88ff-e4934174c051) gave this verdict after
reviewing commit 4da97ba and independently rerunning the suite and inspecting the live store:

> Verdict: adequate for the authorized bounded nightly experiment. I agree. No remaining concrete blocker.

Fable confirmed all 58 tests under Python 3.14.7, exact removal and journaling of the two
unreferenced uploaded blobs, unchanged retained and primary model digests, final loaded-worker
deadline recovery and shutdown metadata, explicit admission failure classification, and a clean
checkout. Codex agrees with that verdict. The code did not change after this final review.

The acceptance is for this local text-benchmark harness and its bounded routine. It is not a
model-quality endorsement. Large downloads may need multiple nights within the one-hour budget;
real multi-night resume timing remains to be observed. The next scheduled run's JSON should be
read with the same care as this acceptance batch. Metadata coverage remains partial, the primary
performance environment is not fully matched to the child, and optional vision is not measured.
The task's Fable 5.1 field was verified visually by Codex; Fable did not independently inspect UI.

All changes remain committed locally. No push, primary-library migration, or global Ollama
configuration change was performed. The old review worktree is retained as a non-active checkout.