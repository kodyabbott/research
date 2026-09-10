# Peer review of the nightly benchmark harness

Status: proposed changes on codex/nightly-peer-review; live acceptance and deployment are pending.

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
