"""Suite definitions and loaders for HumanEval+, MBPP+, and the synthetic test fixture.

A `Suite` pairs the dataset tasks with the expected outputs that `prepare.py` computed in the
sandbox. `Suite.digest` covers the ordered task ids, rendered prompts, entry points, and the hash
of every expected-output file, so two run records are only comparable when their digests match.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

CACHE_ROOT = Path.home() / "Documents/Codex/model-cache/coding-benchmark"
DATASET_DIR = CACHE_ROOT / "datasets"
EXPECTED_DIR = CACHE_ROOT / "expected"
DATASETS_JSON = Path(__file__).resolve().parents[1] / "datasets.json"

# Prompt templates from DESIGN.md. One user message, no system prompt, no few-shot examples.
HUMANEVAL_TEMPLATE = (
    "Complete the following Python function. Return the complete function (signature, docstring, "
    "and body) in a single ```python code block and nothing else.\n"
    "\n"
    "{prompt}"
)
MBPP_TEMPLATE = (
    "{text}\n"
    "\n"
    "Write a Python function named `{entry_point}` that solves this. Return one ```python code "
    "block containing the complete function and nothing else. Example test: {assertion}"
)

# Fields `evalplus.data.utils.completeness_check` requires of every task record.
REQUIRED_FIELDS = ("prompt", "contract", "canonical_solution", "base_input", "plus_input", "atol")


class SuiteError(RuntimeError):
    pass


@dataclass
class Task:
    task_id: str
    dataset: str                 # "humaneval" or "mbpp": selects the special-oracle family
    entry_point: str
    prompt: str                  # the rendered model prompt
    source_prompt: str           # the dataset `prompt` field, used for completion prefixing
    canonical_solution: str
    base_input: list
    plus_input: list
    atol: float
    text: str | None = None      # MBPP+ problem statement without its assertion
    assertion: str | None = None  # the single curated assertion from the MBPP+ docstring
    expected: dict = field(default_factory=dict)  # {"base": {...}, "plus": {...}} once loaded

    @property
    def canonical_program(self) -> str:
        """What EvalPlus executes to produce ground truth: prompt + canonical_solution."""
        return self.source_prompt + self.canonical_solution

    @property
    def allow_body_completion(self) -> bool:
        """Only HumanEval+ prompts are function-signature continuations."""
        return self.dataset == "humaneval"

    def expected_for(self, which: str) -> list:
        return (self.expected.get(which) or {}).get("expected") or []

    def times_for(self, which: str) -> list:
        return (self.expected.get(which) or {}).get("times") or []


@dataclass
class Suite:
    name: str
    dataset: str
    tasks: list[Task]
    dataset_sha256: str
    evalplus_version: str
    prompt_template: str
    digest: str = ""
    skipped: dict = field(default_factory=dict)
    total_tasks: int = 0

    @property
    def prompt_template_sha256(self) -> str:
        return hashlib.sha256(self.prompt_template.encode()).hexdigest()

    def protocol(self) -> dict:
        return {
            "suite": self.name,
            "suiteDigest": self.digest,
            "datasetSha256": self.dataset_sha256,
            "evalplusVersion": self.evalplus_version,
            "promptTemplateSha256": self.prompt_template_sha256,
            "tasks": len(self.tasks),
            "tasksInSuite": self.total_tasks,
            "skippedAtPrepare": len(self.skipped),
        }


def registry() -> dict:
    with DATASETS_JSON.open(encoding="utf-8") as handle:
        return json.load(handle)


def suite_names() -> list[str]:
    return sorted(registry()["suites"])


def entry_for(suite_name: str) -> dict:
    suites = registry()["suites"]
    if suite_name not in suites:
        raise SuiteError(f"unknown suite {suite_name!r}; known: {', '.join(sorted(suites))}")
    return suites[suite_name]


def dataset_path(suite_name: str) -> Path:
    entry = entry_for(suite_name)
    if entry.get("localPath"):
        return Path(__file__).resolve().parents[1] / entry["localPath"]
    return DATASET_DIR / entry["localName"]


def expected_dir(suite_name: str) -> Path:
    return EXPECTED_DIR / suite_name


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def split_mbpp_prompt(prompt: str) -> tuple[str, str]:
    """Split MBPP+'s docstring prompt into (statement, curated assertion).

    The dataset `prompt` is `\"\"\"\\n<statement lines>\\nassert <one call>\\n\"\"\"\\n`. The
    trailing assertion is the *curated* one -- for the set-equality tasks it is written in
    `set(f(...)) == set(...)` form, which the separate `assertion` field is not. Using the
    docstring's own line keeps the prompt consistent with how the task is graded.
    """
    inner = prompt.strip()
    if inner.startswith('"""'):
        inner = inner[3:]
    if inner.endswith('"""'):
        inner = inner[:-3]
    lines = [line for line in inner.strip("\n").split("\n")]
    assertion_index = None
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip().startswith("assert"):
            assertion_index = index
            break
    if assertion_index is None:
        return "\n".join(lines).strip(), ""
    assertion = lines[assertion_index].strip()
    statement = "\n".join(lines[:assertion_index] + lines[assertion_index + 1:]).strip()
    return statement, assertion


def render_prompt(dataset: str, record: dict) -> tuple[str, str | None, str | None]:
    """Return (rendered prompt, mbpp statement or None, mbpp assertion or None)."""
    if dataset == "humaneval":
        return HUMANEVAL_TEMPLATE.format(prompt=record["prompt"]), None, None
    text, assertion = split_mbpp_prompt(record["prompt"])
    rendered = MBPP_TEMPLATE.format(text=text, entry_point=record["entry_point"],
                                    assertion=assertion)
    return rendered, text, assertion


def build_tasks(suite_name: str) -> list[Task]:
    """Parse the dataset into Task objects without touching the expected-output cache."""
    entry = entry_for(suite_name)
    dataset = entry["dataset"]
    path = dataset_path(suite_name)
    if not path.exists():
        raise SuiteError(f"dataset missing: {path}. Run prepare.py --suite {suite_name} first.")
    tasks: list[Task] = []
    for record in read_jsonl_gz(path):
        missing = [name for name in REQUIRED_FIELDS if name not in record]
        if missing:
            raise SuiteError(f"{suite_name} {record.get('task_id')!r} lacks {missing}")
        rendered, text, assertion = render_prompt(dataset, record)
        tasks.append(Task(
            task_id=record["task_id"],
            dataset=dataset,
            entry_point=record["entry_point"],
            prompt=rendered,
            source_prompt=record["prompt"],
            canonical_solution=record["canonical_solution"],
            base_input=record["base_input"],
            plus_input=record["plus_input"],
            atol=float(record.get("atol") or 0.0),
            text=text,
            assertion=assertion,
        ))
    return tasks


def compute_digest(tasks: list[Task], expected_hashes: dict[str, str]) -> str:
    """SHA-256 over ordered task ids, rendered prompts, entry points, and expected-file hashes."""
    digest = hashlib.sha256()
    for task in tasks:
        digest.update(task.task_id.encode())
        digest.update(b"\x00")
        digest.update(task.prompt.encode())
        digest.update(b"\x00")
        digest.update(task.entry_point.encode())
        digest.update(b"\x00")
        digest.update(expected_hashes.get(task.task_id, "").encode())
        digest.update(b"\x1e")
    return digest.hexdigest()


def safe_id(task_id: str) -> str:
    return task_id.replace("/", "_")


def load_skipped(suite_name: str) -> dict:
    path = expected_dir(suite_name) / "_skipped.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("tasks") or {}


def load(suite_name: str, limit: int | None = None, ids: list[str] | None = None,
         require_expected: bool = True) -> Suite:
    """Load a suite with its cached expected outputs.

    Tasks that `prepare.py` recorded as skipped are excluded (they are not scoreable). `limit` and
    `ids` narrow the task list *after* the digest is computed over the full suite, so a smoke run's
    digest still identifies the suite it was drawn from.
    """
    entry = entry_for(suite_name)
    all_tasks = build_tasks(suite_name)
    skipped = load_skipped(suite_name)
    directory = expected_dir(suite_name)
    dataset_sha = sha256_file(dataset_path(suite_name))
    if entry.get("sha256") and dataset_sha != entry["sha256"]:
        raise SuiteError(
            f"{suite_name} dataset SHA-256 mismatch: expected {entry['sha256']}, got {dataset_sha}")

    expected_hashes: dict[str, str] = {}
    scoreable: list[Task] = []
    for task in all_tasks:
        if task.task_id in skipped:
            continue
        path = directory / f"{safe_id(task.task_id)}.json"
        if not path.exists():
            if require_expected:
                raise SuiteError(
                    f"expected outputs missing for {task.task_id} ({path}). "
                    f"Run prepare.py --suite {suite_name}.")
            continue
        expected_hashes[task.task_id] = sha256_file(path)
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("datasetSha256") != dataset_sha:
            raise SuiteError(
                f"expected outputs for {task.task_id} were computed from dataset "
                f"{payload.get('datasetSha256')}, not {dataset_sha}. Re-run prepare.py.")
        task.expected = {"base": payload.get("base") or {}, "plus": payload.get("plus") or {}}
        scoreable.append(task)

    template = HUMANEVAL_TEMPLATE if entry["dataset"] == "humaneval" else MBPP_TEMPLATE
    suite = Suite(name=suite_name, dataset=entry["dataset"], tasks=scoreable,
                  dataset_sha256=dataset_sha, evalplus_version=entry.get("version", "local"),
                  prompt_template=template, skipped=skipped, total_tasks=len(all_tasks))
    suite.digest = compute_digest(scoreable, expected_hashes)

    if ids:
        wanted = [value.strip() for value in ids if value.strip()]
        found = {task.task_id: task for task in scoreable}
        unknown = [value for value in wanted if value not in found]
        if unknown:
            raise SuiteError(f"unknown or skipped task ids: {', '.join(unknown)}")
        suite.tasks = [found[value] for value in wanted]
    if limit is not None:
        suite.tasks = suite.tasks[:limit]
    return suite
