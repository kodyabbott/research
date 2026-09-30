"""Java grading: classify compile/run outcomes and read the `Check` JSON summary.

`java9plus-usage` is the headline "Java 8 discipline" signal, so its patterns are derived from
JDK 8's *own* diagnostics rather than guessed. Every pattern below cites the fixture in
`tests/fixtures/java9plus/` it was read off, captured by compiling one file per feature on the
pinned Zulu 8 (see that directory's `capture.py`).

JDK 8 javac does not know what `var`, a record, a text block or a switch expression is, so it
reports generic parse errors. A pattern that matched only the first diagnostic line
(`cannot find symbol`) would classify an ordinary typo as a Java 9+ leak, so every API pattern
requires the `symbol:`/`location:` detail lines, and the syntax patterns require corroborating
source text. `tests/fixtures/java9plus/control-*.txt` are ordinary Java 8 mistakes kept as
false-positive tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import java_sandbox
from .java_toolchain import DIAGNOSTIC_CAP

JAVA_FAILURE_CLASSES = (
    "none", "no-code", "wrong-class", "compile-error", "java9plus-usage", "signature-mismatch",
    "runtime-exception", "assertion-failed", "wrong-answer", "timeout", "sandbox-error",
    "truncated",
)


@dataclass(frozen=True)
class Java9Pattern:
    """One evidence-backed signature of post-Java-8 code."""

    name: str
    feature: str
    since: str
    fixture: str
    primary: str                      # regex that must match the diagnostics
    corroborating: tuple = ()         # additional regexes that must also match

    def matches(self, diagnostics: str) -> bool:
        if not re.search(self.primary, diagnostics, re.MULTILINE):
            return False
        return all(re.search(extra, diagnostics, re.MULTILINE)
                   for extra in self.corroborating)


# Every `primary` below is a literal read out of the named fixture's captured javac output.
JAVA9PLUS_PATTERNS = (
    Java9Pattern("var", "local-variable type inference (`var`)", "Java 10", "var-local.txt",
                 r"^\s*symbol:\s+class var\b"),
    Java9Pattern("record", "records", "Java 16", "record-declaration.txt",
                 r"^\s*symbol:\s+class record\b"),
    Java9Pattern("text-block", "text blocks", "Java 15", "text-block.txt",
                 r"error: unclosed string literal", (r'"""',)),
    Java9Pattern("switch-expression", "switch expressions", "Java 14", "switch-expression.txt",
                 r"error: illegal start of expression", (r"switch\s*\(", r"->",)),
    Java9Pattern("list-of", "List.of", "Java 9", "list-of.txt",
                 r"^\s*symbol:\s+method of\(", (r"^\s*location:\s+interface List\b",)),
    Java9Pattern("map-of", "Map.of", "Java 9", "map-of.txt",
                 r"^\s*symbol:\s+method of\(", (r"^\s*location:\s+interface Map\b",)),
    Java9Pattern("set-of", "Set.of", "Java 9", "set-of.txt",
                 r"^\s*symbol:\s+method of\(", (r"^\s*location:\s+interface Set\b",)),
    Java9Pattern("string-isblank", "String.isBlank", "Java 11", "string-isblank.txt",
                 r"^\s*symbol:\s+method isBlank\(\)",
                 (r"^\s*location:\s+class String\b",)),
    Java9Pattern("string-strip", "String.strip", "Java 11", "string-strip.txt",
                 r"^\s*symbol:\s+method strip\(\)", (r"^\s*location:\s+class String\b",)),
    Java9Pattern("string-repeat", "String.repeat", "Java 11", "string-repeat.txt",
                 r"^\s*symbol:\s+method repeat\(", (r"^\s*location:\s+class String\b",)),
    Java9Pattern("string-lines", "String.lines", "Java 11", "string-lines.txt",
                 r"^\s*symbol:\s+method lines\(\)", (r"^\s*location:\s+class String\b",)),
    Java9Pattern("stream-tolist", "Stream.toList", "Java 16", "stream-tolist.txt",
                 r"^\s*symbol:\s+method toList\(\)",
                 (r"^\s*location:\s+interface Stream\b",)),
    Java9Pattern("optional-isempty", "Optional.isEmpty", "Java 11", "optional-isempty.txt",
                 r"^\s*symbol:\s+method isEmpty\(\)",
                 (r"^\s*location:\s+class Optional\b",)),
    Java9Pattern("optional-orelsethrow", "Optional.orElseThrow() with no argument", "Java 10",
                 "optional-orelsethrow.txt",
                 r"error: method orElseThrow in class Optional<T> cannot be applied",
                 (r"found:\s+no arguments",)),
    Java9Pattern("collectors-teeing", "Collectors.teeing", "Java 12", "collectors-teeing.txt",
                 r"^\s*symbol:\s+method teeing\(",
                 (r"^\s*location:\s+class Collectors\b",)),
    Java9Pattern("private-interface-method", "private interface methods", "Java 9",
                 "private-interface-method.txt",
                 r"error: modifier private not allowed here",
                 (r"error: interface abstract methods cannot have body",)),
    Java9Pattern("twr-effectively-final",
                 "try-with-resources on an existing variable", "Java 9",
                 "twr-effectively-final.txt",
                 r"error: <identifier> expected", (r"try\s*\(\s*\w+\s*\)",)),
    Java9Pattern("diamond-anonymous", "diamond operator with anonymous classes", "Java 9",
                 "diamond-anonymous.txt",
                 r"reason: cannot use '<>' with anonymous inner classes"),
)


def detect_java9plus(diagnostics: str) -> list[dict]:
    """Which post-Java-8 features the diagnostics show evidence of. Empty means none."""
    found = []
    for pattern in JAVA9PLUS_PATTERNS:
        if pattern.matches(diagnostics or ""):
            found.append({"name": pattern.name, "feature": pattern.feature,
                          "since": pattern.since, "fixture": pattern.fixture})
    return found


@dataclass
class JavaOutcome:
    """Grading result for one Java task."""

    passed: bool = False
    failure_class: str = "none"
    failure_detail: str | None = None
    compile: dict = field(default_factory=dict)
    run: dict | None = None
    checks: dict | None = None
    java9plus: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"passed": self.passed, "failureClass": self.failure_class,
                "failureDetail": self.failure_detail, "compile": self.compile,
                "run": self.run, "checks": self.checks, "java9plus": self.java9plus}

    def as_set_result(self) -> dict:
        """`base`/`plus` shape so `record.summarize` and `summarize.py` need no Java special case.

        HumanEval-X Java and java8-idioms have no base/plus split: a task either passes or not,
        so DESIGN-JAVA.md specifies `basePassed == plusPassed == passed`.
        """
        total = (self.checks or {}).get("total")
        passed_checks = (self.checks or {}).get("passed")
        return {"passed": self.passed, "inputs": total, "completed": passed_checks,
                "counts": {}, "statuses": "", "stage": None,
                "sandbox": {"status": (self.run or {}).get("status")
                            if self.run else self.compile.get("status"),
                            "compileSeconds": self.compile.get("seconds"),
                            "runSeconds": (self.run or {}).get("seconds")},
                "firstFailure": ((self.checks or {}).get("failures") or [None])[0],
                "failureClass": self.failure_class, "failureDetail": self.failure_detail}


def classify_compile_failure(compile_result, solution_file: str = "Solution.java") -> JavaOutcome:
    """Turn a failed compile into a class: java9plus-usage, signature-mismatch or compile-error.

    Per DESIGN-JAVA.md revisions item 1, *where* the error landed matters. Errors only in the
    hidden test file mean the model changed the method contract (`signature-mismatch`); errors in
    the model's own file are bad Java. java9plus evidence wins over both, since that is the
    measurement this suite exists for.
    """
    diagnostics = compile_result.diagnostics or ""
    outcome = JavaOutcome(passed=False, compile=compile_result.as_dict())
    outcome.java9plus = detect_java9plus(diagnostics)
    if compile_result.status in ("timeout", "cpu-timeout"):
        outcome.failure_class = "timeout"
        outcome.failure_detail = f"javac did not finish ({compile_result.status})"
        return outcome
    if compile_result.status == "sandbox-error":
        outcome.failure_class = "sandbox-error"
        outcome.failure_detail = diagnostics[-400:] or "javac could not be launched"
        return outcome
    if outcome.java9plus:
        names = ", ".join(item["feature"] for item in outcome.java9plus)
        outcome.failure_class = "java9plus-usage"
        outcome.failure_detail = f"uses post-Java-8 features: {names}"
        return outcome
    files = compile_result.files_with_errors or []
    if files and solution_file not in files:
        outcome.failure_class = "signature-mismatch"
        outcome.failure_detail = (
            f"compile errors only in {', '.join(files)}, not in {solution_file}: the hidden tests "
            f"could not call the submitted method. First error: {_first_error(diagnostics)}")
        return outcome
    outcome.failure_class = "compile-error"
    outcome.failure_detail = _first_error(diagnostics)
    return outcome


def _first_error(diagnostics: str) -> str:
    for line in (diagnostics or "").splitlines():
        if ": error:" in line:
            return line.strip()[:400]
    return (diagnostics or "").strip()[:400] or "javac failed without a diagnostic"


def grade_humaneval_x(compile_result, run_result) -> JavaOutcome:
    """HumanEval-X Java: pass = compiles and `Main` exits 0 with no AssertionError."""
    if not compile_result.ok:
        return classify_compile_failure(compile_result)
    outcome = JavaOutcome(compile=compile_result.as_dict(),
                          run=run_result.as_dict() if run_result else None)
    if run_result is None:  # pragma: no cover - only if compile_and_run changed shape
        outcome.failure_class = "sandbox-error"
        outcome.failure_detail = "compile succeeded but no run result was produced"
        return outcome
    if run_result.status in ("timeout", "cpu-timeout"):
        outcome.failure_class = "timeout"
        outcome.failure_detail = f"Main did not finish ({run_result.status})"
        return outcome
    if run_result.status == "sandbox-error":
        outcome.failure_class = "sandbox-error"
        outcome.failure_detail = (run_result.stderr_tail or "")[-400:]
        return outcome
    stderr = run_result.stderr_tail or ""
    if run_result.exit_code == 0:
        outcome.passed = True
        outcome.failure_class = "none"
        return outcome
    if "AssertionError" in stderr:
        outcome.failure_class = "assertion-failed"
        outcome.failure_detail = _exception_line(stderr) or "AssertionError from the hidden tests"
        return outcome
    outcome.failure_class = "runtime-exception"
    outcome.failure_detail = (_exception_line(stderr)
                              or f"Main exited {run_result.exit_code} with no exception line")
    return outcome


def grade_checked(compile_result, run_result) -> JavaOutcome:
    """java8-idioms: pass = every `Check` assertion passed and the JSON summary was produced."""
    if not compile_result.ok:
        return classify_compile_failure(compile_result)
    outcome = JavaOutcome(compile=compile_result.as_dict(),
                          run=run_result.as_dict() if run_result else None)
    if run_result is None:  # pragma: no cover
        outcome.failure_class = "sandbox-error"
        outcome.failure_detail = "compile succeeded but no run result was produced"
        return outcome
    if run_result.status in ("timeout", "cpu-timeout"):
        outcome.failure_class = "timeout"
        outcome.failure_detail = f"Main did not finish ({run_result.status})"
        return outcome
    if run_result.status == "sandbox-error":
        outcome.failure_class = "sandbox-error"
        outcome.failure_detail = (run_result.stderr_tail or "")[-400:]
        return outcome
    report = java_sandbox.parse_check_json(run_result.stdout_tail or "")
    outcome.checks = report
    stderr = run_result.stderr_tail or ""
    if report is None:
        # No summary line: the program died before Check.report(), or printed something else.
        if "AssertionError" in stderr:
            outcome.failure_class = "assertion-failed"
            outcome.failure_detail = _exception_line(stderr)
        elif stderr.strip():
            outcome.failure_class = "runtime-exception"
            outcome.failure_detail = _exception_line(stderr) or stderr.strip()[-400:]
        else:
            outcome.failure_class = "runtime-exception"
            outcome.failure_detail = (
                f"no Check summary on stdout (exit {run_result.exit_code}); "
                f"last line was {((run_result.stdout_tail or '').strip().splitlines() or [''])[-1][:200]!r}")
        return outcome
    total, passed_checks = report.get("total", 0), report.get("passed", 0)
    if total and passed_checks == total:
        outcome.passed = True
        outcome.failure_class = "none"
        return outcome
    outcome.failure_class = "wrong-answer"
    failures = report.get("failures") or []
    first = failures[0] if failures else {}
    outcome.failure_detail = (
        f"{passed_checks}/{total} checks passed; first failure "
        f"{first.get('name')!r}: expected {str(first.get('expected'))[:120]} "
        f"got {str(first.get('actual'))[:120]}")
    return outcome


def _exception_line(stderr: str) -> str | None:
    for line in (stderr or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("Exception in thread") or re.match(
                r"^(java|javax)?\.?[\w.$]*(Error|Exception)\b", stripped):
            return stripped[:400]
    return None


def truncate_diagnostics(text: str) -> str:
    return (text or "")[:DIAGNOSTIC_CAP]
