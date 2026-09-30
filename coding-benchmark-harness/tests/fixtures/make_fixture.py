"""Regenerate the synthetic fixture suite.

Three tasks in the HumanEval+ record shape, small enough to grade in under a second. The fixture is
not a benchmark: it exists so the suite loader, the sandbox grading path, the replay backend, and
the summarizer can be exercised end to end without downloading the real datasets.

    python3 coding-benchmark-harness/tests/fixtures/make_fixture.py

The gzip member is written with mtime=0 so the output is byte-reproducible.
"""

import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "FixtureSuite-v1.jsonl.gz"

TASKS = [
    {
        "task_id": "Fixture/0",
        "entry_point": "add_two",
        "prompt": (
            "def add_two(a: int, b: int) -> int:\n"
            '    """ Return the sum of a and b.\n'
            "    >>> add_two(1, 2)\n"
            "    3\n"
            '    """\n'
        ),
        "contract": "\n    assert isinstance(a, int), \"invalid inputs\" # $_CONTRACT_$\n",
        "canonical_solution": "    return a + b\n",
        "base_input": [[1, 2], [3, 4]],
        "plus_input": [[0, 0], [-5, 5], [10 ** 9, 1], [-3, -4]],
        "atol": 0,
    },
    {
        "task_id": "Fixture/1",
        "entry_point": "min_max",
        "prompt": (
            "from typing import List, Tuple\n"
            "\n"
            "\n"
            "def min_max(numbers: List[int]) -> Tuple[int, int]:\n"
            '    """ Return a tuple of the smallest and largest value in numbers.\n'
            "    >>> min_max([3, 1, 2])\n"
            "    (1, 3)\n"
            '    """\n'
        ),
        "contract": "\n    assert len(numbers) > 0, \"invalid inputs\" # $_CONTRACT_$\n",
        "canonical_solution": "    return (min(numbers), max(numbers))\n",
        "base_input": [[[3, 1, 2]], [[5]]],
        "plus_input": [[[-1, -9, 4]], [[0, 0, 0]], [[7, 7, 1]]],
        "atol": 0,
    },
    {
        "task_id": "Fixture/2",
        "entry_point": "mean_of",
        "prompt": (
            "from typing import List\n"
            "\n"
            "\n"
            "def mean_of(numbers: List[float]) -> float:\n"
            '    """ Return the arithmetic mean of numbers.\n'
            "    >>> mean_of([1.0, 2.0])\n"
            "    1.5\n"
            '    """\n'
        ),
        "contract": "\n    assert len(numbers) > 0, \"invalid inputs\" # $_CONTRACT_$\n",
        "canonical_solution": "    return sum(numbers) / len(numbers)\n",
        "base_input": [[[1.0, 2.0]], [[4.0]]],
        "plus_input": [[[0.1, 0.2, 0.3]], [[-1.5, 1.5]], [[1e-8, 3e-8]]],
        "atol": 0,
    },
]


def main() -> None:
    payload = "".join(json.dumps(task, sort_keys=True) + "\n" for task in TASKS).encode()
    with TARGET.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write(payload)
    data = TARGET.read_bytes()
    print(f"wrote {TARGET} ({len(data)} bytes)")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
