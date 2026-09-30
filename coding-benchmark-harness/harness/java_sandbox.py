"""Compiling and running Java inside the sandbox, plus the five Java self-tests.

Java needs a work directory that survives two commands (`javac` writes class files that `java`
then reads), so this uses `SandboxExec.workspace()` rather than the one-shot `run_python`.

Generated Java is compiled and executed only here. The harness process never runs `javac` or
`java` on model output outside the sandbox; the one unsandboxed use of the JDK is reading
`java -version` for the toolchain record.
"""

from __future__ import annotations

import json
import re
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path

from . import java_toolchain as jt
from .sandbox import JAVA_PROFILE_TEMPLATE, JAVA_PROFILE_TEMPLATE_SHA256, SandboxExec, \
    SandboxUnavailable

CLASSES_DIR = "classes"
# javac diagnostics look like `Main.java:12: error: cannot find symbol`.
DIAGNOSTIC_LINE = re.compile(r"^(?P<file>[\w./$-]+\.java):(?P<line>\d+):\s*(?P<kind>error|warning):",
                             re.MULTILINE)


@dataclass
class CompileResult:
    ok: bool
    seconds: float
    diagnostics: str = ""
    status: str = "ok"
    returncode: int | None = None
    files_with_errors: list[str] = field(default_factory=list)
    error_count: int = 0

    def as_dict(self) -> dict:
        return {"ok": self.ok, "seconds": self.seconds,
                "diagnostics": self.diagnostics[:jt.DIAGNOSTIC_CAP],
                "status": self.status, "returncode": self.returncode,
                "filesWithErrors": self.files_with_errors, "errorCount": self.error_count}


@dataclass
class RunResult:
    exit_code: int | None
    seconds: float
    status: str = "ok"
    stdout_tail: str = ""
    stderr_tail: str = ""
    signal: int | None = None

    def as_dict(self) -> dict:
        return {"exitCode": self.exit_code, "seconds": self.seconds, "status": self.status,
                "stdoutTail": self.stdout_tail[-4096:], "stderrTail": self.stderr_tail[-4096:],
                "signal": self.signal}


def files_with_errors(diagnostics: str) -> tuple[list[str], int]:
    """Which .java files javac reported errors in, and how many errors. Drives signature-mismatch.

    An error located in `Main.java` (the hidden tests, which this harness wrote) means the model
    changed the method contract; an error in `Solution.java` is bad Java in the model's own code.
    """
    names, count = [], 0
    for match in DIAGNOSTIC_LINE.finditer(diagnostics or ""):
        if match.group("kind") != "error":
            continue
        count += 1
        name = Path(match.group("file")).name
        if name not in names:
            names.append(name)
    return names, count


class JavaSandbox:
    """A `SandboxExec` configured with the Java profile and a pinned JDK."""

    def __init__(self, toolchain: jt.Toolchain, sandbox: SandboxExec | None = None):
        self.toolchain = toolchain
        self.sandbox = sandbox or SandboxExec()
        self.sandbox.profile_template = JAVA_PROFILE_TEMPLATE
        self.sandbox.profile_sha256 = JAVA_PROFILE_TEMPLATE_SHA256
        self.sandbox.java_home = str(toolchain.java_home)

    @property
    def profile_sha256(self) -> str:
        return JAVA_PROFILE_TEMPLATE_SHA256

    def describe(self) -> dict:
        return {"javaProfileSha256": self.profile_sha256,
                "javaToolchain": self.toolchain.describe()}

    # -- compile and run ---------------------------------------------------------------------

    def compile_and_run(self, sources: dict[str, str], main_class: str = "Main",
                        compile_seconds: float = jt.COMPILE_WALL_SECONDS,
                        run_seconds: float = jt.RUN_WALL_SECONDS,
                        cpu_seconds: int = jt.JAVA_CPU_SECONDS,
                        keep_workdir: bool = False) -> tuple[CompileResult, RunResult | None]:
        """Compile every source together, then run `main_class`. One fresh work directory.

        `sources` maps file name -> text; all of them go to a single `javac` invocation so that
        diagnostics carry the file they belong to.
        """
        with self.sandbox.workspace(keep=keep_workdir) as space:
            (space.path / CLASSES_DIR).mkdir(exist_ok=True)
            for name, text in sources.items():
                space.write(name, text)
            order = [name for name in ("Check.java", "Solution.java", "Main.java")
                     if name in sources]
            order += [name for name in sources if name not in order]
            compiled = space.run(self.toolchain.javac_argv(order, CLASSES_DIR),
                                 timeout=compile_seconds, cpu_seconds=cpu_seconds)
            diagnostics = (compiled.stderr or "") + (compiled.stdout or "")
            names, count = files_with_errors(diagnostics)
            compile_result = CompileResult(
                ok=compiled.status == "ok" and compiled.returncode == 0,
                seconds=round(compiled.wall_ms / 1000, 3), diagnostics=diagnostics,
                status=compiled.status, returncode=compiled.returncode,
                files_with_errors=names, error_count=count)
            if not compile_result.ok:
                return compile_result, None
            ran = space.run(
                self.toolchain.java_argv(main_class, CLASSES_DIR, workdir=str(space.path)),
                timeout=run_seconds, cpu_seconds=cpu_seconds)
            run_result = RunResult(
                exit_code=ran.returncode, seconds=round(ran.wall_ms / 1000, 3),
                status=ran.status, stdout_tail=ran.stdout, stderr_tail=ran.stderr,
                signal=ran.signal)
            return compile_result, run_result

    # -- self tests --------------------------------------------------------------------------

    def self_test(self) -> dict:
        checks = [
            self._check_hello_world(),
            self._check_network(),
            self._check_write_home(),
            self._check_infinite_loop(),
            self._check_java9plus_rejected(),
        ]
        return {"javaProfileSha256": self.profile_sha256,
                "javaHome": str(self.toolchain.java_home),
                "javaVersion": self.toolchain.record.get("javaVersion"),
                "mode": self.toolchain.mode,
                "checks": checks,
                "passed": all(check["passed"] for check in checks)}

    def _check_hello_world(self) -> dict:
        source = ("import java.util.*;\n"
                  "public class Main {\n"
                  "    public static void main(String[] args) {\n"
                  "        List<Integer> xs = new ArrayList<>(Arrays.asList(3, 1, 2));\n"
                  "        Collections.sort(xs);\n"
                  "        System.out.println(\"SELFTEST-OK \" + xs);\n"
                  "    }\n"
                  "}\n")
        compiled, ran = self.compile_and_run({"Main.java": source})
        ok = (compiled.ok and ran is not None and ran.exit_code == 0
              and "SELFTEST-OK [1, 2, 3]" in (ran.stdout_tail or ""))
        return {"name": "java-hello-world-compiles-and-runs", "passed": ok,
                "compile": compiled.as_dict(),
                "run": ran.as_dict() if ran else None}

    def _check_network(self) -> dict:
        """Prove the JVM cannot reach a real local listener.

        A connect to a dead port would raise regardless of the sandbox, and if the deny rule were
        broken the probe must not be able to reach a model server on 11436.
        """
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        accepted: list[str] = []

        def accept_once():
            try:
                server.settimeout(30)
                conn, _ = server.accept()
                accepted.append("accepted")
                conn.close()
            except Exception:
                pass

        thread = threading.Thread(target=accept_once, daemon=True)
        thread.start()
        source = (
            "import java.net.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        try {\n"
            "            Socket s = new Socket();\n"
            f"            s.connect(new InetSocketAddress(\"127.0.0.1\", {port}), 3000);\n"
            "            s.close();\n"
            "            System.out.println(\"CONNECTED\");\n"
            "        } catch (Throwable t) {\n"
            "            System.out.println(\"BLOCKED \" + t.getClass().getName());\n"
            "        }\n"
            "    }\n"
            "}\n")
        compiled, ran = self.compile_and_run({"Main.java": source})
        server.close()
        thread.join(timeout=2)
        output = (ran.stdout_tail if ran else "") or ""
        ok = (compiled.ok and ran is not None and "BLOCKED" in output
              and "CONNECTED" not in output and not accepted)
        return {"name": "java-network-denied", "passed": ok, "listenerPort": port,
                "listenerAccepted": bool(accepted), "output": output.strip()[:300],
                "detail": None if ok else (ran.as_dict() if ran else compiled.as_dict())}

    def _check_write_home(self) -> dict:
        target = Path(self.sandbox.home) / ".java-sandbox-escape-probe.txt"
        source = (
            "import java.io.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        try {\n"
            f"            FileWriter w = new FileWriter(\"{target}\");\n"
            "            w.write(\"escaped\");\n"
            "            w.close();\n"
            "            System.out.println(\"WROTE\");\n"
            "        } catch (Throwable t) {\n"
            "            System.out.println(\"BLOCKED \" + t.getClass().getName());\n"
            "        }\n"
            "    }\n"
            "}\n")
        compiled, ran = self.compile_and_run({"Main.java": source})
        output = (ran.stdout_tail if ran else "") or ""
        existed = target.exists()
        if existed:  # pragma: no cover - only if the sandbox failed
            target.unlink()
        ok = compiled.ok and "BLOCKED" in output and "WROTE" not in output and not existed
        return {"name": "java-write-outside-workdir-denied", "passed": ok,
                "probePath": str(target), "fileCreated": existed,
                "output": output.strip()[:300]}

    def _check_infinite_loop(self) -> dict:
        source = ("public class Main {\n"
                  "    public static void main(String[] args) {\n"
                  "        long i = 0;\n"
                  "        while (true) { i++; }\n"
                  "    }\n"
                  "}\n")
        compiled, ran = self.compile_and_run({"Main.java": source}, run_seconds=6,
                                             cpu_seconds=4)
        ok = compiled.ok and ran is not None and ran.status in ("timeout", "cpu-timeout")
        return {"name": "java-infinite-loop-killed", "passed": ok,
                "runStatus": ran.status if ran else None,
                "seconds": ran.seconds if ran else None}

    def _check_java9plus_rejected(self) -> dict:
        """`List.of` must not compile on the JDK 8 toolchain, with a recognisable diagnostic."""
        source = ("import java.util.*;\n"
                  "public class Main {\n"
                  "    public static void main(String[] args) {\n"
                  "        List<String> xs = List.of(\"a\", \"b\");\n"
                  "        System.out.println(xs);\n"
                  "    }\n"
                  "}\n")
        compiled, _ran = self.compile_and_run({"Main.java": source})
        diagnostics = compiled.diagnostics or ""
        ok = (not compiled.ok and "cannot find symbol" in diagnostics
              and "method of(" in diagnostics)
        return {"name": "java9plus-rejected-on-jdk8", "passed": ok,
                "compileOk": compiled.ok,
                "diagnostics": diagnostics[:800]}


def load(sandbox: SandboxExec | None = None, verify_hash: bool = True) -> JavaSandbox:
    """Load the pinned toolchain and wrap it in a Java sandbox. Raises if either is unavailable."""
    toolchain = jt.load(verify_hash=verify_hash)
    return JavaSandbox(toolchain, sandbox=sandbox)


def available() -> bool:
    try:
        jt.load(verify_hash=False)
        return True
    except (jt.ToolchainError, OSError):
        return False


def parse_check_json(stdout: str) -> dict | None:
    """The `Check.report()` line is the last non-empty line of stdout. Returns None if absent."""
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        if line.startswith("{") and line.endswith("}"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                return None
            if isinstance(payload, dict) and "passed" in payload and "total" in payload:
                return payload
        return None
    return None
