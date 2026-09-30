#!/usr/bin/env python3
"""Turn run records into a Markdown table and comparison.json.

    python3 coding-benchmark-harness/summarize.py coding-benchmark-harness/runs/*.json \\
        --markdown coding-benchmark-harness/RESULTS.md \\
        --json coding-benchmark-harness/comparison.json

Rows are sorted by suite, then pass@1 descending. Runs whose suite digests differ cannot be
compared directly: the output is marked `mixedSuites` and a warning is printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.record import now  # noqa: E402

COLUMNS = [
    ("model", "model"),
    ("suite", "suite"),
    ("think", "think"),
    ("tasks", "tasks"),
    ("basePass", "base pass"),
    ("plusPass", "plus pass (pass@1)"),
    ("noCode", "no-code"),
    ("syntaxError", "syntax"),
    ("runtimeError", "runtime"),
    ("wrongAnswer", "wrong"),
    ("timeout", "timeout"),
    ("truncated", "truncated"),
    ("medianGenTokPerSec", "median gen tok/s"),
    ("medianWallSeconds", "median wall s"),
    ("medianGeneratedTokens", "median gen tokens"),
]
CLASS_COLUMNS = {
    "no-code": "noCode", "syntax-error": "syntaxError", "runtime-error": "runtimeError",
    "wrong-answer": "wrongAnswer", "timeout": "timeout", "truncated": "truncated",
    "sandbox-error": "sandboxError",
}


def row_for(path: Path, payload: dict) -> dict:
    summary = payload.get("summary") or {}
    protocol = payload.get("protocol") or {}
    model = payload.get("model") or {}
    classes = summary.get("failureClasses") or {}
    tasks_total = summary.get("tasksTotal") or 0
    plus_pass = summary.get("plusPass") or 0
    wall = summary.get("medianWallMs")
    row = {
        "runFile": str(path),
        "label": payload.get("label"),
        "status": payload.get("status"),
        "model": model.get("name") or payload.get("label"),
        "modelDigest": model.get("digest"),
        "suite": protocol.get("suite"),
        "suiteDigest": protocol.get("suiteDigest"),
        "datasetSha256": protocol.get("datasetSha256"),
        "promptTemplateSha256": protocol.get("promptTemplateSha256"),
        "evalplusVersion": protocol.get("evalplusVersion"),
        "think": protocol.get("think"),
        "context": protocol.get("context"),
        "outputCap": protocol.get("outputCap"),
        "backend": (payload.get("runtime") or {}).get("backend"),
        "sandboxProfileSha256": (payload.get("runtime") or {}).get("sandboxProfileSha256"),
        "sandboxSelfTestPassed": ((payload.get("runtime") or {}).get("sandboxSelfTest")
                                  or {}).get("passed"),
        "tasks": tasks_total,
        "tasksAttempted": summary.get("tasksAttempted"),
        "basePass": summary.get("basePass"),
        "plusPass": plus_pass,
        "passAt1": summary.get("passAt1"),
        "basePassAt1": summary.get("basePassAt1"),
        "medianGenTokPerSec": summary.get("medianGenTokPerSec"),
        "medianWallSeconds": round(wall / 1000, 2) if isinstance(wall, (int, float)) else None,
        "medianGeneratedTokens": summary.get("medianGeneratedTokens"),
        "medianThinkingChars": summary.get("medianThinkingChars"),
        "unexpectedThinking": summary.get("unexpectedThinking"),
        "protocolValid": summary.get("protocolValid"),
        "unloadConfirmed": (payload.get("unload") or {}).get("confirmed"),
    }
    for label, column in CLASS_COLUMNS.items():
        row[column] = classes.get(label, 0)
    row["truncated"] = summary.get("truncated", row.get("truncated", 0))
    return row


def cell(row: dict, key: str) -> str:
    value = row.get(key)
    if value is None:
        return "--"
    if key in ("basePass", "plusPass"):
        total = row.get("tasks") or 0
        share = f" ({value / total:.1%})" if total else ""
        return f"{value}/{total}{share}"
    if isinstance(value, float):
        return f"{value:.1f}" if value >= 1 else f"{value:.3f}"
    return str(value)


def markdown_table(rows: list[dict]) -> str:
    header = "| " + " | ".join(title for _key, title in COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in COLUMNS) + " |"
    lines = [header, divider]
    for row in rows:
        lines.append("| " + " | ".join(cell(row, key) for key, _title in COLUMNS) + " |")
    return "\n".join(lines)


def build(paths: list[Path]) -> tuple[dict, list[str]]:
    rows, warnings = [], []
    for path in paths:
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"skipping {path}: {exc}")
            continue
        row = row_for(path, payload)
        if row["status"] != "completed":
            warnings.append(f"{path.name}: status is {row['status']!r}; treat its numbers as "
                            f"partial")
        if row["protocolValid"] is False:
            warnings.append(f"{path.name}: protocolValid is false")
        if row["sandboxSelfTestPassed"] is not True:
            warnings.append(f"{path.name}: sandbox self-test did not pass")
        rows.append(row)
    rows.sort(key=lambda item: (item["suite"] or "", -(item["passAt1"] or 0),
                                item["label"] or ""))
    by_suite: dict[str, set] = {}
    for row in rows:
        by_suite.setdefault(row["suite"] or "?", set()).add(row["suiteDigest"])
    mixed = {suite: sorted(digests) for suite, digests in by_suite.items() if len(digests) > 1}
    if mixed:
        for suite, digests in mixed.items():
            warnings.append(
                f"suite {suite!r} appears with {len(digests)} different suite digests; those runs "
                f"are NOT directly comparable (different tasks, prompts or expected outputs)")
    payload = {
        "generatedAt": now(),
        "runs": len(rows),
        "mixedSuites": bool(mixed),
        "suiteDigests": {suite: sorted(digests) for suite, digests in by_suite.items()},
        "warnings": warnings,
        "columns": [key for key, _title in COLUMNS],
        "rows": rows,
    }
    return payload, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--title", default="Coding benchmark results")
    args = parser.parse_args(argv)

    paths = [path for path in args.runs if path.is_file()]
    if not paths:
        print("no run records found", file=sys.stderr)
        return 2
    payload, warnings = build(paths)
    if not payload["rows"]:
        print("no readable run records", file=sys.stderr)
        return 2

    table = markdown_table(payload["rows"])
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    document = [f"# {args.title}", ""]
    if payload["mixedSuites"]:
        document += ["> [!WARNING]",
                     "> Runs in this table do not all share a suite digest, so their pass rates "
                     "are not directly comparable.", ""]
    document += [table, "", "Generated by `summarize.py` at " + payload["generatedAt"] + ".", ""]
    if warnings:
        document += ["## Warnings", ""] + [f"- {warning}" for warning in warnings] + [""]
    document += ["## Run records", ""]
    for row in payload["rows"]:
        document.append(
            f"- `{Path(row['runFile']).name}` -- {row['model']} on {row['suite']} "
            f"(think={row['think']}, backend={row['backend']}, status={row['status']}, "
            f"suite digest `{(row['suiteDigest'] or '')[:16]}...`)")
    text = "\n".join(document) + "\n"

    if args.markdown:
        args.markdown.write_text(text, encoding="utf-8")
        print(f"markdown written to {args.markdown}")
    else:
        print(text)
    if args.json_path:
        args.json_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        print(f"json written to {args.json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
