# Morning handoff: Codex with Astra

Prepared September 11, 2026, shortly after midnight MDT. Kody asked to stop and
document the findings, then resume benchmarks manually with Codex and Astra in
the morning. This document does not schedule a restart or change the model of
the existing Claude task.

## Current state

- The September 10 campaign was canceled at 23:28:52 MDT. Its authorization's
  latest-start cutoff is revoked, the remaining queue is canceled, and the Codex
  heartbeat `overnight-model-benchmark-campaign` is **PAUSED**. See
  [cancellation.json](cancellation.json) and [authorization.json](authorization.json).
- A fresh check at **00:13:10 MDT on September 11** found no benchmark Python,
  controller, supervisor, worker, or private Ollama processes. The personal Ollama
  tray/server remained running on loopback port 11434 with **no loaded models**;
  port 11435 had no listener. GPU utilization was 0%, with 96,188 MiB free.
  The local verification record is in `state/handoffs/20260911/stop-verification.json`.
- All seven personal model digests were unchanged at the original shutdown check.
  That inventory comparison was not repeated during this documentation-only turn.
- The regular **8:15 PM Claude/Fable task was not modified or paused**. Its
  versioned and deployed prompt files still match, SHA-256
  `13522bdcd19c26618e172755fc35fdacc62e77dfdb4f3b7badb03570c0764c14`.
  This checks prompt bytes, not the scheduler's enabled state or saved model field.
- The normal policy still permits one candidate/day, a 35 GiB artifact, 240 GiB
  task storage, 25 GiB free disk, and a one-hour supervisor limit. Its SHA-256 is
  `15fe141fe58693c96aa6d1d4591e650121d3dc5dd3fad4497d81ed0e21e9f9b1`.
  Weights/downloads use the private F: store; the personal model library was not moved.

## Results worth keeping

Five campaign runs completed, representing four distinct candidate configurations
and a separate v1 pilot. Raw records, failed cases, thinking probes, and cleanup
details are linked from [results.md](results.md).

| Configuration | v2 screen, candidate / coder | Valid generation speed, candidate / coder | Practical interpretation |
|---|---:|---:|---|
| Qwen3.5 122B Q4 | 14/16 / 12/16 | 136.24 / 287.34 tok/s | Useful next candidate for realistic coding tasks: better on this small screen with less slowdown than Qwen3.8. |
| Installed Qwen3.8 27B BF16/MTP | 15/16 / 12/16 | 41.95 / 288.20 tok/s | Worth deeper quality testing when latency is acceptable; this configuration did not reproduce the old speed claim. |
| Installed Muse 30B BF16/DFlash | 15/16 / 12/16 | Invalid comparison | Promising screen answers, but every short throughput trial hit the 512-token cap. Diagnose before ranking its speed. |
| MiniCPM5 2B F16 | 6/16 / 12/16 | 250.36 / 307.33 tok/s | Low priority for the requested coding/general assistant work under this protocol. |

The first Qwen3.8 run was a **v1 pilot**: 14/16 versus 10/16, with valid generation
rates of 43.24 versus 287.38 tok/s. Two baseline misses exposed ambiguous answer
types in the original prompts. V2 clarifies the types; do not pool the versions.
All five completed pairs passed the three small exact-output checks.

These are 16 authored questions, not executed coding tasks or a production agent
evaluation. One item changes the score by 6.25 percentage points. There is no
statistical significance claim or basis to replace the coder baseline yet. Stored
MTP/DFlash settings and templates also prevent isolating quantization effects.

Separate single thinking-enabled probes showed approximately 15.80x ordinary
latency for Qwen3.5, 20.59x for Qwen3.8 v2, and 30.66x for MiniCPM. They remain
exploratory and outside throughput medians. Muse's 1.92x ratio has an invalid
ordinary reference and is diagnostic only. Character counts are not reasoning-token counts.

## Compatibility and harness findings

- Muse BF16/DFlash's roughly 2.46 GB `/api/ps` report is misleading. Startup logs
  show the intended main model and a separate draft model. Ollama 0.32.13's
  allocation parser lets draft entries replace matching main entries; replaying
  those entries reproduces the small reported total. This explains accounting,
  not the unresolved short-output/truncation behavior. See
  [compatibility.md](compatibility.md) and [muse-memory-evidence.json](muse-memory-evidence.json).
- The earlier bare Muse Q8 import returned thinking even though capability metadata
  omitted it. The harness now detects unexpected returned thinking throughout the
  battery, invalidates the comparison, and skips an unsupported thinking-off reference.
  Repeating the same Muse configuration unchanged is low value.
- GPT-OSS ignores boolean thinking controls in this Ollama version. Its prepared
  protocol uses explicit **low** reasoning and 8192 output tokens per case; it is
  unpaired and must not be ranked as equal-budget against the 512-token v2 screen.
  No GPT-OSS campaign inference completed before cancellation.
- Earlier review concerns about C: download storage, cache exhaustion, the 20 GiB
  cap, missing thinking probes, Python availability, metadata limits, and untested
  import/cleanup were addressed in the deployed harness. The private F: runtime,
  two-import retention policy, three-copy storage accounting, bounded idle/unload,
  and live acceptance evidence are described in [validation.md](../../validation.md),
  [peer-review.md](../../peer-review.md), and the [project README](../../README.md).
- Python **3.14.7** exists at the configured per-user `Python314` path and ran
  successfully during this handoff check. The proposed alternate HF downloader was
  not installed: the earlier attempt found no `pip` module. No downloader adapter
  or packages were added. Do not assume `huggingface_hub`/`hf_xet` are available.
- The last recorded full offline suite passed **92 tests** in 8.771 seconds before
  the later report-rendering adjustment. That adjustment received its own saved-record
  fixture check. No tests, model inference, or downloads were rerun for this handoff.
- Vision remains unmeasured. Metadata failures and missing approved mirrors are
  coverage/compatibility gaps, not evidence that a model is poor.

## Unfinished selections and download evidence

KAT-Coder Q8 was canceled during download, before import or inference. The retained
partial is **950,603,057 bytes**, rechecked after cancellation; the expected complete
artifact is 36,914,690,464 bytes. Its content-addressed `.part` file remains in the
policy's F: download directory. The pinned revision, filename, size, and SHA-256 are
in [selections/kat-coder-q8.json](selections/kat-coder-q8.json). Resume must retain
full-file hash verification. A partial file is not a verified model.

The artifact publisher is **Bartowski**, which is approved in policy; the upstream
developer is **Kwaipilot**. Publisher approval is not an upstream-vendor endorsement.
All eight selected GGUF sources, including that distinction, are recorded in
[candidate-sources.json](candidate-sources.json) and the [selection plan](README.md).

The untested selections remaining when stopped were GPT-OSS 20B (already installed),
LFM2.5 2.6B BF16, Ornith 35B Q6, Gemma 31B Q8, Granite 30B Q8, Nemotron 30B Q8,
stock Qwen3.8 Q8, and Apodex mini Q6, plus the interrupted KAT Q8. The controller had
moved GPT-OSS and small LFM ahead of the remaining large downloads. Nex, K2-Horizon,
Spark, NeoHorse, and Edge0 still lack a verified approved mirror in this research;
Ling compatibility remains unresolved. See the plan for the original selection rationale.

Four small range probes against pinned KAT/Gemma artifacts returned HTTP 206 at
roughly **0.07-0.26 MB/s**; no 429 occurred in those probes. Their cause is unresolved.
The source-specific slow rates do not establish that the household WAN was saturated.
Windows directory enumeration also temporarily reported a zero-byte open partial;
a fresh read handle correctly showed progress. See
[download-observations.json](download-observations.json). Do not mistake these probes
for an internet speed test or evidence that a download accelerator will fix streaming.

## TV streaming and router investigation

Kody reported possible interference with Crunchyroll on a Samsung 7 Series TV.
The goal is to give the TV enough bandwidth when it needs it and leave spare
capacity for the PC, without a blanket PC cap. Causation was not established.

The GFiber GR6EXX0C router, firmware 1.6.1, exposes a real internal HTTP API at
`/ubus`. The local page was observed calling `data_repo.webinfo.system`,
`op-mode.get`, and `data_repo.webinfo.devices`. Its loaded JavaScript also contains
configuration setters, so it would be incorrect to call the API read-only.

Neither the inspected local/cloud settings nor the two inspected frontend bundles
exposed QoS, SQM, traffic shaping, or bandwidth-limit controls. The inspected Samsung
detail page offered reserved IP, DMZ, and port forwarding; those do not implement
streaming priority. No supported/public QoS API was found. This is **not** an exhaustive
backend enumeration or proof that hidden firmware support cannot exist.

Two Samsung TVs were connected on different bands, one 5 GHz and one 2.4 GHz.
It remains unknown which is the 7 Series and whether it connects through the extender.
Identifying that TV and testing a stronger wireless link or Ethernet are useful next
diagnostics before blaming PC traffic. No router, firewall, DNS, radio, DMZ, or
remote-assistance settings were changed. Browser network observation was stopped.

WMM prioritizes traffic classes within Wi-Fi; it does not automatically make every
Wi-Fi device outrank Ethernet at the internet bottleneck. The desired policy would
require suitable per-device/class QoS and queuing at the constrained link. A router
replacement is only a possible future option, with QoS throughput verified at the
household's actual multi-gig service rate, not inferred from its port labels.

Primary references checked during the investigation:

- [Cisco: WMM and wireless QoS](https://www.cisco.com/c/en/us/support/docs/wireless/catalyst-9800-series-wireless-controllers/221906-understand-troubleshoot-qos-over-wirel.html).
- [GFiber: advanced network settings](https://gfiber.com/support/en/answer/1858/).
- [GFiber: using your own router](https://gfiber.com/support/en/answer/1816/).
- [Crunchyroll: available video quality](https://help.crunchyroll.com/hc/en-us/articles/36816426440980-What-video-quality-options-do-I-have).

Detailed local device identifiers, account-plan observations, API method inventory,
and evidence limits are saved in `state/handoffs/20260911/network-observations.md`.
That directory is ignored by Git and stays local to this workstation. No credentials,
cookies, request headers, or full router responses were saved.

## Morning continuation

1. Wait for Kody's new resume request in Codex with Astra. Read this handoff,
   `results.md`, `compatibility.md`, and the local network note. Inspect current Git,
   process, queue, policy, disk, and GPU state before any launch.
2. **Do not simply restart the old controller.** Its queue is canceled and its
   authorization cutoff is revoked. In addition, `nightly.py` only admits ordinary
   candidate starts from 20:15 to 05:59; `CampaignHarness` currently exempts the count,
   not that clock window. An after-06:00 request requires an explicitly bounded
   human-run path with appropriate tests, or scheduling for the next allowed window.
   Preserve the standing nightly policy and the canceled audit records.
3. If another campaign is requested, give it a new ID, authorization, queue/ledger,
   and report destination. `campaign_queue.py` and `campaign_report.py` currently
   contain September 10-specific paths; parameterize or adapt those deliberately.
   Do not overwrite the five results or turn canceled rows back into history-free work.
4. Prefer useful work without downloads first: the installed GPT-OSS low-reasoning
   screen, a carefully scoped Muse compatibility diagnosis, or a stronger realistic
   coding evaluation for Qwen3.5/Qwen3.8 against the coder baseline. Keep distinct
   protocols labeled. Resume KAT/new downloads only within the new request and with
   the streaming concern considered. No network prioritization solution was implemented.
5. Run relevant offline tests after any harness/protocol changes, then run one
   supervised candidate at a time and review terminal raw JSON before scaling up.
   Retain pinned sources, publisher admission, ownership checks, resource limits,
   deadlines, unload verification, and separate normal/campaign quota accounting.

For offline verification only, from the project directory:

```powershell
$benchPython = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
& $benchPython -B -m unittest -q test_nightly.py test_campaign.py test_campaign_queue.py test_reasoning_screen.py
```

`campaign_report.py` can rebuild the old report without inference, but it writes
the September 10 report from the local queue. It is not a new-campaign launcher.

## Repository handoff

Before this documentation change, `main` was clean at `200a97e` and 15 commits ahead
of the locally recorded `origin/main` (`143df65`); no fetch was performed. The work
is local. Earlier automatic approval review blocked publishing the pending campaign
code, selections, and reports to the public repository and requested specific approval
for that payload. No new push was attempted during shutdown/documentation.

Read repo instructions before further changes. Prior campaign source/URL/adversarial
reviews are recorded in `notes.md`; this pause did not restart reviewers. Any later
public push must also exclude the ignored private network observations.
