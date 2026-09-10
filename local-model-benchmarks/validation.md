# Harness validation — 2026-09-10

- 27 offline tests passed, covering deferred/failed metadata, legacy migration, complete and
  partial outages, exact-output grading, publisher/revision/file/hash admission, download size
  limits, installed digests/provenance, persistent daily limits, disk/storage reserves, busy
  workloads, fixed generation settings, cached prompt metrics, runtime expiration, daytime
  deferral, a complete candidate/baseline transaction, real Windows process locking, hard
  timeout termination, and JSON output forwarding to the calling shell.
- Live discovery checked 12 trending entries (top two per pipeline), enriched four, and
  retained eight pending lookups. This was a staging validation, not a full nightly sweep.
- Live admission accepted the exact size and SHA-256 for
  `ggml-org/Qwen3-0.6B-GGUF`, revision `b5f37287796e5be0ea3dab2e7430873fb3f73e49`,
  file `Qwen3-0.6B-Q8_0.gguf`. No weights were downloaded or imported.
- The already installed `qwen3-coder:30b` completed the revised battery: three repetitions,
  median generation 288.11 tokens/second (range 284.69–310.28), median short-request client
  time 687 ms, all three exact-output checks passed, and no truncation. Its own model was
  unloaded afterward; `ollama ps` was empty. See
  [raw baseline validation](runs/20260910-162636-63916c19.json).

Download streaming and import admission are covered by offline fixtures; a real new-model
download/import remains for the next eligible scheduled run. No claims about a new model's
performance are made by this implementation validation. The old README table remains dated.

This work used Codex for implementation and verification. Task selection/reporting is
configured for Claude Fable 5.1. Existing documents and task settings were backed up before
deployment; the repository history also preserves the original implementation.

Deployment check: the installed wrapper completed a full 150-model discovery with no source or detail failures. It migrated 388 legacy IDs, enriched 40, and retained 348 pending metadata lookups. See runs/20260910-163056-170607ea.json. The deployed task prompt and versioned prompt have matching SHA-256 hashes; the saved task remains enabled at 21:00 and specifies claude-fable-5-1. Claude caches task metadata in memory, so a running app must reload before the saved model/cwd take effect; the prompt also includes a next-run model synchronization instruction.

## Peer-review revision - staged, not yet deployed

51 offline tests pass under Python 3.12.14. This includes real process and local HTTP tests;
model loading, import, eviction, and the model-loaded deadline test remain live acceptance
requirements. See peer-review.md. The revised code is on codex/nightly-peer-review and does
not yet alter the scheduled checkout. Python 3.14.7 installation, the 35 GiB artifact cap,
and the 240 GiB cache await Kody's approval. Do not read the test count as a live-run sign-off.
