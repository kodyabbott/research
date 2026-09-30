"""Code extraction from an assistant message. Pure functions, no I/O, no execution.

Only the `content` of a response is ever parsed. Thinking text is stored separately in the run
record and is never searched for code -- a model that reasons about a wrong approach and then
writes the right one must not be graded on its scratch work.

Rules are applied in the order given in DESIGN.md and the winning rule name is saved with the task
so a later reader can tell how a given sample was interpreted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CODE_BYTES = 128 * 1024

_FENCE = re.compile(r"^[ \t]*(?:```+|~~~+)[ \t]*([A-Za-z0-9_+.-]*)[ \t]*$", re.MULTILINE)
_DEF_LINE = re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]", re.MULTILINE)
_REPL_LINE = re.compile(r"^[ \t]*(?:>>>|\.\.\.)[ \t]?")

RULES = ("fence-entry", "fence-last", "raw-entry", "raw-body", "empty", "too-large")


@dataclass
class Extraction:
    code: str
    rule: str
    completion_prefixed: bool = False
    blocks: int = 0
    detail: str | None = None

    @property
    def usable(self) -> bool:
        return bool(self.code.strip()) and self.rule not in ("empty", "too-large")


def fenced_blocks(text: str) -> list[tuple[str, str]]:
    """Return (language, body) for each fenced block. An unterminated final fence still counts.

    Models truncated mid-answer routinely leave the closing fence off; dropping those blocks would
    turn a nearly-correct sample into `no-code` and misattribute the failure.
    """
    blocks: list[tuple[str, str]] = []
    marks = list(_FENCE.finditer(text))
    index = 0
    while index < len(marks):
        opening = marks[index]
        language = (opening.group(1) or "").lower()
        body_start = opening.end() + 1 if opening.end() < len(text) else opening.end()
        if index + 1 < len(marks):
            closing = marks[index + 1]
            body = text[body_start:closing.start()]
            index += 2
        else:
            body = text[body_start:]
            index += 1
        if body.strip():
            blocks.append((language, body.rstrip("\n")))
    return blocks


def strip_repl_noise(code: str) -> str:
    """Drop leading interactive-prompt lines (`>>> `, `... `) that some models emit."""
    lines = code.splitlines()
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or not _REPL_LINE.match(lines[start]):
        return code
    cleaned = []
    for line in lines[start:]:
        if _REPL_LINE.match(line):
            cleaned.append(_REPL_LINE.sub("", line, count=1))
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def indent_body(body: str, spaces: int = 4) -> str:
    """Indent a bare function body so it can be appended to a HumanEval prompt."""
    lines = body.splitlines()
    first = next((line for line in lines if line.strip()), "")
    if first[:1] in (" ", "\t"):
        return body
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in lines)


def extract(content: str | None, entry_point: str, prompt: str = "",
            allow_body_completion: bool = True) -> Extraction:
    """Pick the code for `entry_point` out of an assistant message."""
    text = content or ""
    if len(text.encode("utf-8", "replace")) > MAX_CODE_BYTES:
        return Extraction("", "too-large", detail=f"content exceeds {MAX_CODE_BYTES} bytes")
    marker_patterns = (f"def {entry_point}(", f"def {entry_point} (")
    blocks = fenced_blocks(text)

    code, rule = "", "empty"
    if blocks:
        bodies = [body for _language, body in blocks]
        chosen = next((body for body in bodies
                       if any(mark in body for mark in marker_patterns)), None)
        if chosen is not None:
            code, rule = chosen, "fence-entry"
        else:
            code, rule = bodies[-1], "fence-last"
    elif any(mark in text for mark in marker_patterns):
        code, rule = text, "raw-entry"
    elif text.strip() and not _DEF_LINE.search(text) and allow_body_completion:
        code, rule = text, "raw-body"

    if rule == "empty" or not code.strip():
        return Extraction("", "empty", blocks=len(blocks),
                          detail="no fenced block or entry-point definition found")

    code = strip_repl_noise(code).rstrip() + "\n"
    completion_prefixed = False
    defines_entry = any(mark in code for mark in marker_patterns)
    if not defines_entry and any(mark in prompt for mark in marker_patterns):
        if _DEF_LINE.search(code):
            # Helper functions only: put the prompt in front so the entry point at least exists.
            code = prompt.rstrip("\n") + "\n\n" + code
        else:
            code = prompt.rstrip("\n") + "\n" + indent_body(code) + "\n"
        completion_prefixed = True
    elif rule == "raw-body":
        code = prompt.rstrip("\n") + "\n" + indent_body(code) + "\n"
        completion_prefixed = True

    if len(code.encode("utf-8", "replace")) > MAX_CODE_BYTES:
        return Extraction("", "too-large", blocks=len(blocks),
                          detail=f"extracted code exceeds {MAX_CODE_BYTES} bytes")
    return Extraction(code, rule, completion_prefixed, blocks=len(blocks))


# -- Java ---------------------------------------------------------------------------------------

MAX_JAVA_BYTES = 256 * 1024
_PACKAGE_LINE = re.compile(r"^[ \t]*package[ \t]+[\w.]+[ \t]*;[ \t]*\r?\n?", re.MULTILINE)
_SOLUTION_CLASS = re.compile(r"\b(?:class|interface|enum)\s+Solution\b")

JAVA_RULES = ("fence-solution", "fence-last", "raw-solution", "wrong-class", "empty", "too-large")


@dataclass
class JavaExtraction:
    code: str
    rule: str
    package_stripped: bool = False
    blocks: int = 0
    detail: str | None = None

    @property
    def usable(self) -> bool:
        return bool(self.code.strip()) and self.rule not in ("empty", "too-large", "wrong-class")


def extract_java(content: str | None) -> JavaExtraction:
    """Pick the `Solution` class out of an assistant message.

    Rules, in order: the first fenced block declaring `Solution`; otherwise the last fenced block;
    otherwise raw content that declares `Solution`. A `package ...;` line is stripped (Java files
    here are compiled in the default package) and nothing else is modified. Content that has no
    `Solution` declaration after that is `wrong-class` -- which, per DESIGN-JAVA.md, is also where
    a body-only reply lands: the prompt asks for the complete class, so a bare method body is an
    instruction-following miss rather than a Java failure.
    """
    text = content or ""
    if len(text.encode("utf-8", "replace")) > MAX_JAVA_BYTES:
        return JavaExtraction("", "too-large", detail=f"content exceeds {MAX_JAVA_BYTES} bytes")
    blocks = fenced_blocks(text)

    code, rule = "", "empty"
    if blocks:
        bodies = [body for _language, body in blocks]
        chosen = next((body for body in bodies if _SOLUTION_CLASS.search(body)), None)
        if chosen is not None:
            code, rule = chosen, "fence-solution"
        else:
            code, rule = bodies[-1], "fence-last"
    elif _SOLUTION_CLASS.search(text):
        code, rule = text, "raw-solution"
    elif text.strip():
        code, rule = text, "wrong-class"

    if not code.strip():
        return JavaExtraction("", "empty", blocks=len(blocks),
                              detail="no fenced block or Solution declaration found")

    stripped = _PACKAGE_LINE.sub("", code, count=1)
    package_stripped = stripped != code
    code = stripped.rstrip() + "\n"

    if not _SOLUTION_CLASS.search(code):
        return JavaExtraction(code, "wrong-class", package_stripped, blocks=len(blocks),
                              detail="no `class Solution` declaration in the extracted code")
    if len(code.encode("utf-8", "replace")) > MAX_JAVA_BYTES:
        return JavaExtraction("", "too-large", blocks=len(blocks),
                              detail=f"extracted code exceeds {MAX_JAVA_BYTES} bytes")
    return JavaExtraction(code, rule, package_stripped, blocks=len(blocks))
