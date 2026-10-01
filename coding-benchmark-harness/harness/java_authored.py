"""Loader for the authored `java8-idioms-v1` suite.

Each task is a directory holding four files: `task.json` (metadata and the full contract),
`prompt.java` (the skeleton the model sees), `Solution.java` (the canonical answer) and `Main.java`
(the hidden tests). `Check.java` is shared by every task and is never sent to the model.

Kept separate from `suites.py` because the shapes differ: there is no dataset file, the "dataset
hash" is a digest over the authored files, and the graded sources are three files rather than two.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import suites

CHECK_FILE = "Check.java"


def suite_root(suite_name: str) -> Path:
    entry = suites.entry_for(suite_name)
    return (Path(__file__).resolve().parents[1] / "suites"
            / entry.get("directory", suite_name))


def check_source(suite_name: str) -> str:
    return (suite_root(suite_name) / CHECK_FILE).read_text(encoding="utf-8")


def task_dirs(suite_name: str) -> list[Path]:
    root = suite_root(suite_name)
    if not root.exists():
        raise suites.SuiteError(f"authored suite missing: {root}")
    return sorted(path for path in root.iterdir()
                  if path.is_dir() and (path / "task.json").exists())


def digest(suite_name: str) -> str:
    """SHA-256 over Check.java plus all four files of every task, in task-id order."""
    import hashlib

    out = hashlib.sha256()
    out.update(b"Check.java\x00")
    out.update((suite_root(suite_name) / CHECK_FILE).read_bytes())
    out.update(b"\x1e")
    for directory in task_dirs(suite_name):
        for name in suites.AUTHORED_FILES:
            path = directory / name
            if not path.exists():
                raise suites.SuiteError(f"{directory.name} is missing {name}")
            out.update(f"{directory.name}/{name}".encode())
            out.update(b"\x00")
            out.update(path.read_bytes())
            out.update(b"\x1e")
    return out.hexdigest()


def build_tasks(suite_name: str, java8_hint: bool = True) -> list[suites.Task]:
    entry = suites.entry_for(suite_name)
    check = check_source(suite_name)
    tasks: list[suites.Task] = []
    for directory in task_dirs(suite_name):
        with (directory / "task.json").open(encoding="utf-8") as handle:
            meta = json.load(handle)
        skeleton = (directory / "prompt.java").read_text(encoding="utf-8")
        canonical = (directory / "Solution.java").read_text(encoding="utf-8")
        hidden = (directory / "Main.java").read_text(encoding="utf-8")
        task = suites.Task(
            task_id=meta.get("id", directory.name),
            dataset=entry["dataset"],
            language="java",
            entry_point=meta.get("id", directory.name),
            prompt=suites.render_java_prompt({"prompt": skeleton}, java8_hint),
            source_prompt=skeleton,
            canonical_solution=canonical,
            base_input=[], plus_input=[], atol=0.0,
            declaration=skeleton,
            test=hidden,
            files={CHECK_FILE: check, "Main.java": hidden},
        )
        task.metadata = meta
        tasks.append(task)
    return tasks


def categories(tasks: list[suites.Task]) -> dict:
    """Category -> task ids, for the summarizer's per-category table."""
    grouped: dict[str, list[str]] = {}
    for task in tasks:
        category = getattr(task, "metadata", {}).get("category", "uncategorized")
        grouped.setdefault(category, []).append(task.task_id)
    return {name: sorted(ids) for name, ids in sorted(grouped.items())}
