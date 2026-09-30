"""macOS `sandbox-exec` wrapper: the only place model-generated code is ever executed.

Every allow rule in PROFILE_TEMPLATE was discovered empirically on this Mac and is documented in
../notes.md. The harness process never calls exec()/eval() on model output; it only reads the JSON
the sandboxed runner leaves behind in its work directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
DATA_VOLUME = "/System/Volumes/Data"
CACHE_ROOT = Path.home() / "Documents/Codex/model-cache/coding-benchmark"
WORK_ROOT = CACHE_ROOT / "work"

DEFAULT_WALL_SECONDS = 30.0
DEFAULT_CPU_SECONDS = 60
DEFAULT_NOFILE = 64
# The design specified 16 MiB. Raised because a canonical HumanEval+ solution over its ~1000 plus
# inputs can legitimately write tens of megabytes of results (see notes.md); still a hard cap, and
# still only writable inside the per-task work directory.
DEFAULT_FSIZE = 128 * 1024 * 1024
OUTPUT_READ_CAP = 1024 * 1024          # stdout/stderr, which should stay near-empty
RESULT_READ_CAP = 192 * 1024 * 1024    # results.jsonl / meta.json requested via `want`

# Deny-default profile. Placeholders are substituted per invocation; the SHA-256 recorded in run
# records is of this template, so it is stable across work directories.
#
# Rule-by-rule justification is in notes.md. Ordering matters: later rules win, so the $HOME deny
# sits between the system allow and the WORKDIR allow.
PROFILE_TEMPLATE = """(version 1)
(deny default)
(deny network*)
(allow sysctl-read)
(allow process-exec
  (literal "@PYTHON@")
  (literal "@PYTHON_APP@")
  (literal "@DATA@@PYTHON@")
  (literal "@DATA@@PYTHON_APP@"))
(allow file-read*
  (subpath "@PYTHON_PREFIX@")
  (subpath "@DATA@@PYTHON_PREFIX@")
  (subpath "/usr/lib")
  (subpath "/usr/share")
  (subpath "/System/Library")
  (subpath "/private/var/db/dyld")
  (subpath "@DATA@/private/var/db/dyld")
  (literal "/")
  (literal "/opt")
  (literal "/System/Volumes")
  (literal "@DATA@")
  (literal "@DATA@/opt"))
(deny file-read* (subpath "@HOME@") (subpath "@DATA@@HOME@"))
(allow file-read* (subpath "@WORKDIR@") (subpath "@DATA@@WORKDIR@"))
(allow file-write* (subpath "@WORKDIR@") (subpath "@DATA@@WORKDIR@"))
"""

PROFILE_TEMPLATE_SHA256 = hashlib.sha256(PROFILE_TEMPLATE.encode()).hexdigest()


class SandboxUnavailable(RuntimeError):
    """Raised when sandbox-exec is missing or a self-test fails. There is no unsandboxed fallback."""


@dataclass
class SandboxResult:
    status: str  # ok | timeout | cpu-timeout | crashed | sandbox-error
    returncode: int | None = None
    signal: int | None = None
    wall_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""
    files: dict = field(default_factory=dict)  # requested output files, decoded as text

    @property
    def timed_out(self) -> bool:
        return self.status in ("timeout", "cpu-timeout")


def _python_app_binary(python: str) -> str:
    """Homebrew's python3 re-execs itself through Python.app; both binaries need process-exec."""
    candidate = Path(python).resolve()
    # .../Versions/3.14/bin/python3.14 -> .../Versions/3.14/Resources/Python.app/Contents/MacOS/Python
    for parent in candidate.parents:
        app = parent / "Resources/Python.app/Contents/MacOS/Python"
        if app.exists():
            return str(app)
    return str(candidate)


def _python_prefix(python: str) -> str:
    """Directory tree that must be readable for the interpreter and its stdlib to load."""
    real = Path(python).resolve()
    for parent in real.parents:
        # /opt/homebrew/Cellar/python@3.14/... -> /opt/homebrew ; /usr/bin/python3 -> /usr
        if parent.name in ("homebrew", "local", "usr", "opt") or str(parent) == "/":
            return str(parent)
    return str(real.parent)


class SandboxExec:
    """Runs a standalone Python program under a deny-default sandbox-exec profile."""

    kind = "sandbox-exec"

    def __init__(self, python: str | None = None, work_root: Path | None = None,
                 home: str | None = None):
        if sys.platform != "darwin":
            raise SandboxUnavailable("sandbox-exec is macOS only; no fallback exists")
        if not os.path.exists(SANDBOX_EXEC):
            raise SandboxUnavailable(f"{SANDBOX_EXEC} not found; refusing to execute model code")
        self.python = str(Path(python or sys.executable).resolve())
        self.python_app = _python_app_binary(self.python)
        self.python_prefix = _python_prefix(self.python)
        self.home = os.path.realpath(home or os.path.expanduser("~"))
        self.work_root = Path(work_root or WORK_ROOT)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.profile_sha256 = PROFILE_TEMPLATE_SHA256

    def describe(self) -> dict:
        return {
            "kind": self.kind,
            "sandboxExec": SANDBOX_EXEC,
            "python": self.python,
            "pythonApp": self.python_app,
            "pythonPrefix": self.python_prefix,
            "pythonVersion": self.python_version(),
            "workRoot": str(self.work_root),
            "homeDenied": self.home,
            "profileSha256": self.profile_sha256,
        }

    def python_version(self) -> str:
        try:
            out = subprocess.run([self.python, "-c", "import sys;print(sys.version.split()[0])"],
                                 capture_output=True, text=True, timeout=30)
            return out.stdout.strip()
        except Exception as exc:  # pragma: no cover - diagnostic only
            return f"unknown ({exc!r})"

    def profile_text(self, workdir: str) -> str:
        return (PROFILE_TEMPLATE
                .replace("@PYTHON_APP@", self.python_app)
                .replace("@PYTHON_PREFIX@", self.python_prefix)
                .replace("@PYTHON@", self.python)
                .replace("@DATA@", DATA_VOLUME)
                .replace("@HOME@", self.home)
                .replace("@WORKDIR@", os.path.realpath(workdir)))

    # -- execution ---------------------------------------------------------------------------

    def run_python(self, files: dict[str, str], argv: list[str] | None = None,
                   stdin_text: str = "", timeout: float = DEFAULT_WALL_SECONDS,
                   cpu_seconds: int = DEFAULT_CPU_SECONDS, want: tuple[str, ...] = (),
                   keep_workdir: bool = False) -> SandboxResult:
        """Write `files` into a fresh work directory, run `argv` under the profile, collect `want`.

        `files` maps relative path -> text. `argv[0]` is the script name inside the work directory.
        Nothing from `files` is imported or executed by this process.
        """
        argv = list(argv or ["main.py"])
        workdir = Path(tempfile.mkdtemp(prefix="task-", dir=self.work_root))
        real = Path(os.path.realpath(workdir))
        try:
            for name, text in files.items():
                target = real / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            profile = real / "profile.sb"
            profile.write_text(self.profile_text(str(real)), encoding="utf-8")

            env = {
                "PATH": "/usr/bin:/bin",
                # HOME and TMPDIR point into WORKDIR so expanduser()/tempfile never need a rule.
                "HOME": str(real),
                "TMPDIR": str(real),
                "WORKDIR": str(real),
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            }
            # No -I/-E: those would discard PYTHONHASHSEED=0, which we rely on for determinism.
            command = [SANDBOX_EXEC, "-f", str(profile), self.python, *argv]
            out_path, err_path = real / "_stdout.txt", real / "_stderr.txt"
            started = time.monotonic()
            status, returncode, signum = "ok", None, None
            with out_path.open("wb") as out_fh, err_path.open("wb") as err_fh:
                try:
                    proc = subprocess.run(
                        command, cwd=str(real), env=env,
                        stdout=out_fh, stderr=err_fh, timeout=timeout,
                        preexec_fn=_limit_setter(cpu_seconds),
                        input=stdin_text.encode("utf-8"),
                    )
                    returncode = proc.returncode
                except subprocess.TimeoutExpired:
                    status = "timeout"
                except OSError as exc:
                    status = "sandbox-error"
                    err_fh.write(f"\nharness OSError: {exc!r}\n".encode())
            wall_ms = round((time.monotonic() - started) * 1000, 2)
            if returncode is not None and returncode < 0:
                signum = -returncode
                # SIGXCPU (24) is the RLIMIT_CPU soft limit; SIGKILL follows the hard limit.
                status = "cpu-timeout" if signum in (resource.RLIM_INFINITY, 24, 9) else "crashed"
            elif returncode:
                status = "crashed" if status == "ok" else status

            result = SandboxResult(
                status=status, returncode=returncode, signal=signum, wall_ms=wall_ms,
                stdout=_read_capped(out_path), stderr=_read_capped(err_path),
                files={name: _read_capped(real / name, RESULT_READ_CAP)
                       for name in want},
            )
            return result
        finally:
            if keep_workdir:  # pragma: no cover - debugging aid
                print(f"sandbox workdir kept: {real}", file=sys.stderr)
            else:
                shutil.rmtree(workdir, ignore_errors=True)

    # -- self tests --------------------------------------------------------------------------

    def self_test(self) -> dict:
        """The five required checks from DESIGN.md. Every one must pass before model code runs."""
        checks: list[dict] = []
        checks.append(self._check_normal())
        checks.append(self._check_network())
        checks.append(self._check_write_outside())
        checks.append(self._check_read_outside())
        checks.append(self._check_timeout())
        return {
            "profileSha256": self.profile_sha256,
            "python": self.python,
            "pythonVersion": self.python_version(),
            "checks": checks,
            "passed": all(c["passed"] for c in checks),
            "ranAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    def _check_normal(self) -> dict:
        program = (
            "import json, os, sys\n"
            "open(os.path.join(os.environ['WORKDIR'], 'out.json'), 'w')"
            ".write(json.dumps({'ok': True, 'sum': sum(range(10))}))\n"
        )
        res = self.run_python({"main.py": program}, want=("out.json",), timeout=30, cpu_seconds=10)
        try:
            payload = json.loads(res.files.get("out.json") or "null")
        except json.JSONDecodeError:
            payload = None
        ok = res.status == "ok" and payload == {"ok": True, "sum": 45}
        return {"name": "normal-program-returns-json", "passed": ok, "status": res.status,
                "detail": None if ok else f"payload={payload!r} stderr={res.stderr[-400:]}"}

    def _check_network(self) -> dict:
        """Open a real listener, prove the sandboxed process cannot reach it (EPERM, no accept).

        A bare connect to a dead port would raise ConnectionRefused whether or not the sandbox
        works, so the check would be vacuous; and a broken deny rule must not let the probe reach
        a live model server.
        """
        import socket
        import threading

        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        accepted: list[str] = []

        def accept_once():
            try:
                server.settimeout(20)
                conn, _ = server.accept()
                accepted.append("accepted")
                conn.close()
            except Exception:
                pass

        thread = threading.Thread(target=accept_once, daemon=True)
        thread.start()
        program = (
            "import errno, json, os, socket\n"
            "out = {}\n"
            "try:\n"
            f"    socket.create_connection(('127.0.0.1', {port}), 3).close()\n"
            "    out['result'] = 'CONNECTED'\n"
            "except OSError as exc:\n"
            "    out['result'] = errno.errorcode.get(exc.errno, str(exc.errno))\n"
            "    out['type'] = type(exc).__name__\n"
            "open(os.path.join(os.environ['WORKDIR'], 'out.json'), 'w').write(json.dumps(out))\n"
        )
        res = self.run_python({"main.py": program}, want=("out.json",), timeout=30, cpu_seconds=10)
        try:
            payload = json.loads(res.files.get("out.json") or "null") or {}
        except json.JSONDecodeError:
            payload = {}
        server.close()
        thread.join(timeout=2)
        ok = (payload.get("result") == "EPERM" and payload.get("type") == "PermissionError"
              and not accepted)
        return {"name": "network-denied", "passed": ok, "probe": payload,
                "listenerAccepted": bool(accepted), "listenerPort": port,
                "detail": None if ok else f"status={res.status} stderr={res.stderr[-400:]}"}

    def _check_write_outside(self) -> dict:
        marker = Path(tempfile.gettempdir()) / f"sandbox-escape-{os.getpid()}.txt"
        home_marker = Path(self.home) / f".sandbox-escape-{os.getpid()}.txt"
        program = (
            "import errno, json, os\n"
            "out = {}\n"
            f"for name, path in (('tmp', {str(marker)!r}), ('home', {str(home_marker)!r})):\n"
            "    try:\n"
            "        open(path, 'w').write('escaped')\n"
            "        out[name] = 'WROTE'\n"
            "    except OSError as exc:\n"
            "        out[name] = f'{type(exc).__name__}:{errno.errorcode.get(exc.errno, exc.errno)}'\n"
            "open(os.path.join(os.environ['WORKDIR'], 'out.json'), 'w').write(json.dumps(out))\n"
        )
        res = self.run_python({"main.py": program}, want=("out.json",), timeout=30, cpu_seconds=10)
        try:
            payload = json.loads(res.files.get("out.json") or "null") or {}
        except json.JSONDecodeError:
            payload = {}
        existed = marker.exists() or home_marker.exists()
        ok = (payload.get("tmp") == "PermissionError:EPERM"
              and payload.get("home") == "PermissionError:EPERM" and not existed)
        for path in (marker, home_marker):  # pragma: no cover - only if the sandbox failed
            if path.exists():
                path.unlink()
        return {"name": "write-outside-workdir-denied", "passed": ok, "probe": payload,
                "filesCreated": existed,
                "detail": None if ok else f"status={res.status} stderr={res.stderr[-400:]}"}

    def _check_read_outside(self) -> dict:
        """Read denial for $HOME outside WORKDIR: ~/.ssh (or a temp stand-in) and the repository."""
        repo_file = Path(__file__).resolve().parents[1] / "DESIGN.md"
        ssh_dir = Path(self.home) / ".ssh"
        created = None
        if ssh_dir.exists():
            targets = sorted(p for p in ssh_dir.iterdir() if p.is_file())
            ssh_target = str(targets[0]) if targets else str(ssh_dir)
        else:
            # ~/.ssh is absent on this machine; use a real file under $HOME so ENOENT cannot be
            # mistaken for denial.
            created = Path(self.home) / f".sandbox-read-probe-{os.getpid()}.txt"
            created.write_text("probe\n", encoding="utf-8")
            ssh_target = str(created)
        program = (
            "import errno, json, os\n"
            "out = {}\n"
            f"for name, path in (('home', {ssh_target!r}), ('repo', {str(repo_file)!r})):\n"
            "    try:\n"
            "        with open(path, 'rb') as handle:\n"
            "            handle.read(16)\n"
            "        out[name] = 'READ'\n"
            "    except OSError as exc:\n"
            "        out[name] = f'{type(exc).__name__}:{errno.errorcode.get(exc.errno, exc.errno)}'\n"
            "open(os.path.join(os.environ['WORKDIR'], 'out.json'), 'w').write(json.dumps(out))\n"
        )
        try:
            res = self.run_python({"main.py": program}, want=("out.json",), timeout=30,
                                  cpu_seconds=10)
        finally:
            if created is not None:
                created.unlink(missing_ok=True)
        try:
            payload = json.loads(res.files.get("out.json") or "null") or {}
        except json.JSONDecodeError:
            payload = {}
        ok = (payload.get("home") == "PermissionError:EPERM"
              and payload.get("repo") == "PermissionError:EPERM")
        return {"name": "read-home-and-repo-denied", "passed": ok, "probe": payload,
                "homeProbePath": ssh_target, "repoProbePath": str(repo_file),
                "detail": None if ok else f"status={res.status} stderr={res.stderr[-400:]}"}

    def _check_timeout(self) -> dict:
        program = "i = 0\nwhile True:\n    i += 1\n"
        res = self.run_python({"main.py": program}, timeout=8, cpu_seconds=2)
        ok = res.timed_out
        return {"name": "infinite-loop-killed", "passed": ok, "status": res.status,
                "signal": res.signal, "wallMs": res.wall_ms,
                "detail": None if ok else f"stderr={res.stderr[-400:]}"}


def _limit_setter(cpu_seconds: int):
    def apply_limits():  # pragma: no cover - runs in the forked child
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_NOFILE, (DEFAULT_NOFILE, DEFAULT_NOFILE))
        resource.setrlimit(resource.RLIMIT_FSIZE, (DEFAULT_FSIZE, DEFAULT_FSIZE))
    return apply_limits


def _read_capped(path: Path, cap: int = OUTPUT_READ_CAP) -> str:
    try:
        with path.open("rb") as handle:
            data = handle.read(cap + 1)
    except OSError:
        return ""
    truncated = len(data) > cap
    text = data[:cap].decode("utf-8", "replace")
    return text + "\n[truncated]" if truncated else text


def runner_source() -> str:
    """Source of sandbox_runner.py, copied standalone into the work directory."""
    return (Path(__file__).resolve().parent / "sandbox_runner.py").read_text(encoding="utf-8")


def runner_sha256() -> str:
    return hashlib.sha256(runner_source().encode()).hexdigest()
