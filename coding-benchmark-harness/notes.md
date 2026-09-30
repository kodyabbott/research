# Coding benchmark harness -- implementation log

Running log kept while implementing [DESIGN.md](DESIGN.md). Newest entries at the bottom of each
section. Times are Mountain Daylight Time (America/Denver).

Design by Claude Fable 5.1; implementation by Claude Opus (Anthropic) via Claude Code, directed by
Kody Abbott.

## Environment

Captured 2026-09-29 23:59 MDT on the 2023 MacBook Pro 16" (M2 Max, 64 GB):

| Item | Value |
| --- | --- |
| macOS | 27.0 (build 26A428), `Darwin 27.0.0` |
| python3 | 3.14.7, `/opt/homebrew/opt/python@3.14/bin/python3.14` (`which python3` -> `/opt/homebrew/bin/python3`) |
| python3 realpath | `/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14` |
| `sandbox-exec` | present at `/usr/bin/sandbox-exec` |
| repo | `~/repos/research`, branch/commit recorded per commit below |
| datasets + work dirs | `~/Documents/Codex/model-cache/coding-benchmark/` (outside the repo) |

Standard library only; no pip packages are used or required.

**No model server was contacted during implementation.** Per DESIGN.md "Revisions after review" item 1,
ports 11434 and 11436 were off limits: a separate benchmark had the GPU. Every backend test uses a fake
`urlopen`. Acceptance item 4 (live Ollama run) is not part of this work.

## Log

### 2026-09-29 23:59 MDT -- start

- Read DESIGN.md in full including "Revisions after review", repo `CLAUDE.md`, and
  `.claude/rules/{research-workflow,source-rules}.md`.
- Read the reference implementations: `uncensored-models-m5-benchmark/bench.py` (raw-record style,
  Ollama request handling, `think` mapping, refuse-to-overwrite, unload confirmation via `/api/ps`),
  `local-model-benchmarks/coding_screen.py` (extraction + sandbox-runner call shape, truncation
  handling), `local-model-benchmarks/quality_screen.py` (`_same` comparison helper). Ideas reused,
  nothing imported across folders.
- Created the folder skeleton: `harness/`, `tests/fixtures/`, `runs/`.

### 2026-09-30 00:20 MDT -- sandbox profile discovery

Goal: a `(deny default)` `sandbox-exec` profile that the stock Homebrew python3 3.14.7 can start
under. Discovery was empirical, starting permissive and tightening one rule at a time.

**What did not work, and why**

1. `(trace "...")` in the profile produced no trace file (macOS 27 appears to have dropped or
   restricted profile tracing), so trace-driven generation was not available.
2. `/usr/bin/log show --predicate 'eventMessage CONTAINS "deny"'` showed denials from *other*
   processes (`mds`, `logd_helper`) but never from the sandboxed python. Kernel sandbox denials for
   this process were not logged, so the log-reading loop the design assumed was not usable either.
   The productive signal was the process exit status: `134` (SIGABRT) for a failure during
   interpreter startup, and an actual error string once enough was allowed for python to reach its
   own error reporting.
3. The first breakthrough came from adding `(literal "/")` to `file-read*`, which turned the silent
   SIGABRT into `python3.14: realpath: /opt/homebrew/Cellar/python@3.14/.../bin/: Operation not
   permitted`. The interpreter calls `realpath()` on its own executable at startup, which requires
   **`file-read*` (not merely `file-read-metadata`) on every ancestor directory** of the binary.
   `(allow file-read-metadata (literal "/") (literal "/opt") ...)` and `(path-ancestors ...)` both
   still failed; only full `file-read*` on `/` and `/opt` worked.
4. macOS firmlinks matter. `/opt`, `/Users`, and `/private/tmp` live on the Data volume and the
   kernel also sees them as `/System/Volumes/Data/opt`, `/System/Volumes/Data/Users`, etc. A write
   rule for `/tmp/...` silently failed until the path was `os.path.realpath()`-ed to
   `/private/tmp/...` **and** mirrored under `/System/Volumes/Data`. Every path-based rule in the
   profile is therefore emitted twice: bare and `/System/Volumes/Data`-prefixed.
5. `(allow process-exec (literal <python3.14>))` alone failed with
   `posix_spawn: .../Resources/Python.app/Contents/MacOS/Python: Undefined error: 0`. Homebrew's
   `python3.14` re-execs itself through the framework's `Python.app` binary, so both literals are
   needed. `sandbox.py::_python_app_binary` locates it by walking the parents of the resolved
   interpreter path.

**Empirically minimal read set.** An automated drop-one-at-a-time minimizer over 11 candidate rules
reduced the required `file-read*` set to exactly three entries for this interpreter:
`(subpath "/opt/homebrew")`, `(literal "/")`, `(literal "/opt")`. `/usr/lib` and `/System/Library`
are *not* needed because `libSystem` and `CoreFoundation` come from the kernel-mapped dyld shared
cache rather than from disk.

**Every rule in `harness/sandbox.py::PROFILE_TEMPLATE`, and its justification**

| Rule | Why it is there |
| --- | --- |
| `(version 1)` | Required profile header. |
| `(deny default)` | Deny-default posture: nothing is permitted unless listed below. |
| `(deny network*)` | Hard requirement. Verified by self-test against a live local listener (EPERM, listener accepted nothing). Redundant with `deny default`, kept explicit so the intent survives edits. |
| `(allow process-exec (literal @PYTHON@) (literal @PYTHON_APP@) + Data-volume mirrors)` | The interpreter binary and the `Python.app` binary it re-execs. Narrow literals, not `process-exec*`. `process-fork` is **not** allowed, so the sandboxed process cannot spawn helpers -- verified: `subprocess.run(["/bin/echo"])` raises `PermissionError`. |
| `(allow file-read* (subpath @PYTHON_PREFIX@) + mirror)` | The interpreter, its framework `Python` dylib, and the standard library. `@PYTHON_PREFIX@` is `/opt/homebrew` here, derived from the resolved interpreter path. |
| `(allow file-read* (subpath "/usr/lib") (subpath "/usr/share") (subpath "/System/Library"))` | Not strictly required with the dyld shared cache (see minimizer result above), kept as defensive breadth so the profile also works with `/usr/bin/python3` or a python that loads on-disk system dylibs, ICU data, or zoneinfo. All are outside `$HOME`, so they do not weaken the `$HOME` read denial. |
| `(allow file-read* (subpath "/private/var/db/dyld") + mirror)` | dyld shared-cache metadata; same defensive rationale. |
| `(allow file-read* (literal "/") (literal "/opt") (literal "/System/Volumes") (literal DATA) (literal DATA/opt))` | Ancestor-directory reads required by the interpreter's startup `realpath()` (finding 3). Directory entries only -- `literal`, not `subpath`, so this grants nothing recursive. |
| `(deny file-read* (subpath @HOME@) + mirror)` | The desirable-but-optional requirement from the design revisions: no reads anywhere under `$HOME`. Placed **after** the system allows and **before** the WORKDIR allow, because later rules win. Verified against two files that actually exist (`DESIGN.md` in the repo and a temp file created under `$HOME`), both `PermissionError:EPERM` -- ENOENT would not have proved denial. |
| `(allow file-read* (subpath @WORKDIR@) + mirror)` | The per-task work directory, which is itself under `$HOME` (`~/Documents/Codex/model-cache/coding-benchmark/work/task-*`). This is the only readable location inside `$HOME`. |
| `(allow file-write* (subpath @WORKDIR@) + mirror)` | The only writable location anywhere. Hard requirement, verified: writes to `/private/tmp` and to `$HOME` both return `PermissionError:EPERM` and no file is created. |

Rules that turned out to be **unnecessary and were left out**: `sysctl-read`, `mach-lookup`,
`signal`, `process-fork`, `file-read-metadata`, and any `/dev` access. Python 3.14.7 starts and runs
the whole standard library without them. `signal.setitimer(ITIMER_REAL, ...)` and SIGALRM delivery
work with no `signal` rule (kernel-delivered), which is what the per-input timeout relies on --
`setitimer`, not `signal.alarm`, because the per-input limits are fractional seconds.

**Process limits.** `preexec_fn` sets `RLIMIT_CPU` (default 60 s per task per the design
revisions), `RLIMIT_NOFILE` 64, `RLIMIT_FSIZE` 16 MiB. Verified: CPU spin is killed by SIGXCPU
(signal 24) at the limit; an over-large write raises `OSError 27 File too large`; the 65th open file
raises `OSError 24`. Wall timeout is `subprocess.run(timeout=...)`, verified independently.

**Environment.** Scrubbed to `PATH=/usr/bin:/bin`, `HOME=WORKDIR`, `TMPDIR=WORKDIR`,
`WORKDIR=<workdir>`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`. Setting
`HOME` and `TMPDIR` into WORKDIR means `os.path.expanduser()` and `tempfile` never need an allow
rule (design revisions item 3). The interpreter is launched **without** `-I`/`-E`, because those
would discard `PYTHONHASHSEED=0` and with it the determinism of set/dict iteration order.

**Third-party packages are not importable in the sandbox.** `import numpy` raises
`PermissionError` (its install lives under `$HOME`); scipy/sympy/pandas are not installed at all.
EvalPlus's own reference environment has numpy. This affects only *candidate* code that tries to
import it (scored as a runtime error); the HumanEval+/MBPP+ canonical solutions are pure standard
library, so expected outputs are unaffected. Noted in README limitations.

**Known fidelity limit.** Candidate code shares the interpreter with the per-input timer, so it
could in principle reinstall the SIGALRM handler or call `signal.setitimer(..., 0)` and evade the
per-input timeout. EvalPlus has the same exposure with its `time_limit` context manager. The outer
`RLIMIT_CPU` and wall-clock timeout are the backstop and cannot be evaded from inside.

Sandbox self-tests: all five pass (`normal-program-returns-json`, `network-denied`,
`write-outside-workdir-denied`, `read-home-and-repo-denied`, `infinite-loop-killed`). Profile
template SHA-256 is recorded in each run record as `sandboxProfileSha256`.
