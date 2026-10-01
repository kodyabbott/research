"""Suite definitions and loaders for HumanEval+, MBPP+, and the synthetic test fixture.

A `Suite` pairs the dataset tasks with the expected outputs that `prepare.py` computed in the
sandbox. `Suite.digest` covers the ordered task ids, rendered prompts, entry points, and the hash
of every expected-output file, so two run records are only comparable when their digests match.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
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

# Java prompt templates from DESIGN-JAVA.md. The Java 8 constraint is stated by default, because
# that is how the constraint reaches a model in real use; `--no-java8-hint` flips to the second
# template so default habits can be measured separately (design open question, default taken).
JAVA_TEMPLATE = (
    "Complete the following Java class. Target Java 8: do not use var, records, text blocks, "
    "switch expressions, List.of/Map.of/Set.of, or any API newer than Java 8. Return the complete "
    "Solution class (imports, class, and the finished method) in a single ```java code block and "
    "nothing else.\n"
    "\n"
    "{prompt}"
)
JAVA_TEMPLATE_NO_HINT = (
    "Complete the following Java class. Return the complete Solution class (imports, class, and "
    "the finished method) in a single ```java code block and nothing else.\n"
    "\n"
    "{prompt}"
)

# Fields `evalplus.data.utils.completeness_check` requires of every task record.
REQUIRED_FIELDS = ("prompt", "contract", "canonical_solution", "base_input", "plus_input", "atol")
# HumanEval-X Java, verified against data/java/data/humaneval.jsonl at the pinned revision.
JAVA_REQUIRED_FIELDS = ("task_id", "prompt", "declaration", "canonical_solution", "test")

# Trailing `throws ...` is optional: Java/162 (`stringToMd5`) declares one.
_JAVA_METHOD = re.compile(
    r"(?:public|protected|private)?\s*(?:static\s+)?[\w<>\[\],.?\s]+?\s+(\w+)\s*\([^)]*\)"
    r"(?:\s*throws\s[\w.,\s]+)?\s*\{?\s*$")


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
    language: str = "python"
    # Java only:
    declaration: str = ""        # imports + class + signature, without the Javadoc
    test: str = ""              # the hidden `Main` class
    example_test: str = ""      # the visible `Main` from the dataset, not used for scoring
    import_block: str = ""      # the scaffold's own imports, prepended to the hidden Main
    files: dict = field(default_factory=dict)  # authored suites: file name -> text
    metadata: dict = field(default_factory=dict)  # authored suites: task.json contents

    @property
    def canonical_program(self) -> str:
        """What EvalPlus executes to produce ground truth: prompt + canonical_solution."""
        return self.source_prompt + self.canonical_solution

    @property
    def allow_body_completion(self) -> bool:
        """Only HumanEval+ prompts are function-signature continuations."""
        return self.language == "python" and self.dataset == "humaneval"

    @property
    def is_java(self) -> bool:
        return self.language == "java"

    def java_sources(self, solution_code: str) -> dict:
        """The files handed to `javac`: the model's Solution plus the hidden tests.

        Two files, not one. The upstream HumanEval-X harness concatenates prompt, solution and
        test into a single `Main.java`; that makes every diagnostic point at `Main.java`, which
        would make DESIGN-JAVA.md's `signature-mismatch` classification impossible, and it turns a
        model writing `public class Solution` into a spurious "class Solution is public, should be
        declared in Solution.java" error. Splitting them needs the scaffold's import block copied
        into the hidden `Main`, because none of the 164 dataset `test` values carry imports of
        their own.
        """
        if self.files:
            sources = dict(self.files)
            sources["Solution.java"] = solution_code
            return sources
        return {
            "Solution.java": solution_code,
            "Main.java": self.import_block + self.test,
        }

    @property
    def canonical_java(self) -> str:
        """The canonical program to compile as `Solution.java`.

        Authored tasks ship a complete `Solution.java`, so it is used as-is. For HumanEval-X it is
        `prompt + canonical_solution` with **no** trailing brace: `canonical_solution` already
        closes both the method and the class in all 164 records (brace balance is exactly 0).
        """
        if self.files:
            return self.canonical_solution
        return self.source_prompt + self.canonical_solution

    def expected_for(self, which: str) -> list:
        return (self.expected.get(which) or {}).get("expected") or []

    def times_for(self, which: str) -> list:
        return (self.expected.get(which) or {}).get("times") or []

    def reference_wall_seconds(self, which: str) -> float:
        """Wall time the canonical solution needed for this whole input set, at prepare time.

        Includes the harness's own serialization cost, which for a handful of tasks dwarfs the
        function calls (Mbpp/255 returns a single value whose canonical form is ~3 GB). Candidate
        budgets are scaled from this so a correct answer is not killed by the grader's own work.
        """
        return float((self.expected.get(which) or {}).get("sandboxWallMs") or 0.0) / 1000.0


@dataclass
class Suite:
    name: str
    dataset: str
    tasks: list[Task]
    dataset_sha256: str
    evalplus_version: str
    prompt_template: str
    digest: str = ""
    raw_file_digest: str = ""   # over the expected files verbatim; forensics only, not stable
    skipped: dict = field(default_factory=dict)
    total_tasks: int = 0
    language: str = "python"

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
            "language": self.language,
            # Hash of the expected files verbatim. Not stable across `prepare.py --recompute`
            # (it includes timestamps and measured timings), so it is never used to decide
            # comparability -- recorded only so a record can be traced to a specific cache.
            "suiteDigestRawFiles": self.raw_file_digest,
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
    if not entry.get("localName"):
        return Path(__file__).resolve().parents[1] / "suites" / suite_name
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


def java_import_block(prompt: str) -> str:
    """The scaffold's own import lines, copied into the hidden Main so it can compile alone."""
    lines = []
    for line in prompt.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") and stripped.endswith(";"):
            lines.append(stripped)
        elif stripped.startswith(("class ", "public class ", "interface ", "abstract class ")):
            break
    return ("\n".join(lines) + "\n\n") if lines else ""


def java_entry_point(declaration: str) -> str:
    """Method name from the trailing signature of a HumanEval-X Java declaration."""
    for line in reversed((declaration or "").strip().splitlines()):
        match = _JAVA_METHOD.match(line.strip())
        if match:
            return match.group(1)
    return "solve"


def render_java_prompt(record: dict, java8_hint: bool = True) -> str:
    template = JAVA_TEMPLATE if java8_hint else JAVA_TEMPLATE_NO_HINT
    return template.format(prompt=record["prompt"])


def render_prompt(dataset: str, record: dict) -> tuple[str, str | None, str | None]:
    """Return (rendered prompt, mbpp statement or None, mbpp assertion or None)."""
    if dataset == "humaneval":
        return HUMANEVAL_TEMPLATE.format(prompt=record["prompt"]), None, None
    text, assertion = split_mbpp_prompt(record["prompt"])
    rendered = MBPP_TEMPLATE.format(text=text, entry_point=record["entry_point"],
                                    assertion=assertion)
    return rendered, text, assertion


def build_java_tasks(suite_name: str, java8_hint: bool = True) -> list[Task]:
    """Parse HumanEval-X Java into Task objects."""
    entry = entry_for(suite_name)
    path = dataset_path(suite_name)
    if not path.exists():
        raise SuiteError(f"dataset missing: {path}. Run prepare.py --suite {suite_name} first.")
    tasks: list[Task] = []
    for record in read_jsonl(path):
        missing = [name for name in JAVA_REQUIRED_FIELDS if name not in record]
        if missing:
            raise SuiteError(f"{suite_name} {record.get('task_id')!r} lacks {missing}")
        tasks.append(Task(
            task_id=record["task_id"],
            dataset=entry["dataset"],
            language="java",
            entry_point=java_entry_point(record["declaration"]),
            prompt=render_java_prompt(record, java8_hint),
            source_prompt=record["prompt"],
            canonical_solution=record["canonical_solution"],
            base_input=[], plus_input=[], atol=0.0,
            declaration=record["declaration"],
            test=record["test"],
            example_test=record.get("example_test", ""),
            import_block=java_import_block(record["prompt"]),
        ))
    return tasks


def read_jsonl(path: Path) -> list[dict]:
    """Read .jsonl or .jsonl.gz."""
    if str(path).endswith(".gz"):
        return read_jsonl_gz(path)
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_tasks(suite_name: str, java8_hint: bool = True) -> list[Task]:
    """Parse the dataset into Task objects without touching the expected-output cache."""
    entry = entry_for(suite_name)
    if entry.get("language") == "java":
        if entry.get("authored"):
            from . import java_authored
            return java_authored.build_tasks(suite_name, java8_hint=java8_hint)
        return build_java_tasks(suite_name, java8_hint=java8_hint)
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


def expected_fingerprint(payload: dict) -> str:
    """Hash of the parts of an expected-output file that define the benchmark.

    Deliberately excludes `computedAt`, the measured per-input `times`, and the sandbox/toolchain
    block. Those change on every recompute, and hashing the raw file made a harmless `--recompute`
    change the suite digest -- which would wrongly mark two runs of the same benchmark as
    incomparable. What remains is the task identity, its tolerance, and the expected values.
    """
    material = {
        "taskId": payload.get("taskId"),
        "entryPoint": payload.get("entryPoint"),
        "atol": payload.get("atol"),
        "notNoneMode": payload.get("notNoneMode"),
        "language": payload.get("language"),
        "canonicalPassesOnJdk8": payload.get("canonicalPassesOnJdk8"),
        "checkTotal": (payload.get("checks") or {}).get("total"),
    }
    for which in ("base", "plus"):
        block = payload.get(which) or {}
        material[which] = {"inputs": block.get("inputs"), "expected": block.get("expected")}
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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


AUTHORED_FILES = ("task.json", "prompt.java", "Solution.java", "Main.java")


def authored_root(suite_name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "suites" / suite_name


def authored_task_dirs(suite_name: str) -> list[Path]:
    root = authored_root(suite_name)
    if not root.exists():
        raise SuiteError(f"authored suite missing: {root}")
    return sorted(path for path in root.iterdir()
                  if path.is_dir() and (path / "task.json").exists())


def authored_digest(suite_name: str) -> str:
    """SHA-256 over Check.java plus all four files of every task, in task-id order.

    DESIGN-JAVA.md: "Suite digest = SHA-256 over all four files per task in id order." The shared
    `Check.java` is folded in too, since changing it changes what every task is graded against.
    """
    from . import java_authored
    return java_authored.digest(suite_name)


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
         require_expected: bool = True, java8_hint: bool = True) -> Suite:
    """Load a suite with its cached expected outputs.

    Tasks that `prepare.py` recorded as skipped are excluded (they are not scoreable). `limit` and
    `ids` narrow the task list *after* the digest is computed over the full suite, so a smoke run's
    digest still identifies the suite it was drawn from.
    """
    entry = entry_for(suite_name)
    all_tasks = build_tasks(suite_name, java8_hint=java8_hint)
    skipped = load_skipped(suite_name)
    directory = expected_dir(suite_name)
    if entry.get("authored"):
        # No dataset file: the authored files themselves are the pinned artifact.
        dataset_sha = authored_digest(suite_name)
    else:
        dataset_sha = sha256_file(dataset_path(suite_name))
        if entry.get("sha256") and dataset_sha != entry["sha256"]:
            raise SuiteError(f"{suite_name} dataset SHA-256 mismatch: expected "
                             f"{entry['sha256']}, got {dataset_sha}")

    expected_hashes: dict[str, str] = {}
    raw_hashes: dict[str, str] = {}
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
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        expected_hashes[task.task_id] = expected_fingerprint(payload)
        raw_hashes[task.task_id] = sha256_file(path)
        if payload.get("datasetSha256") != dataset_sha:
            raise SuiteError(
                f"expected outputs for {task.task_id} were computed from dataset "
                f"{payload.get('datasetSha256')}, not {dataset_sha}. Re-run prepare.py.")
        task.expected = {"base": payload.get("base") or {}, "plus": payload.get("plus") or {}}
        scoreable.append(task)

    if entry.get("language") == "java":
        template = JAVA_TEMPLATE if java8_hint else JAVA_TEMPLATE_NO_HINT
    elif entry["dataset"] == "humaneval":
        template = HUMANEVAL_TEMPLATE
    else:
        template = MBPP_TEMPLATE
    suite = Suite(name=suite_name, dataset=entry["dataset"], tasks=scoreable,
                  dataset_sha256=dataset_sha, evalplus_version=entry.get("version", "local"),
                  prompt_template=template, skipped=skipped, total_tasks=len(all_tasks),
                  language=entry.get("language", "python"))
    suite.digest = compute_digest(scoreable, expected_hashes)
    suite.raw_file_digest = compute_digest(scoreable, raw_hashes)

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
