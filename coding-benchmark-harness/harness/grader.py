"""Grading: build the in-sandbox job, then compare returned values in this process.

Nothing here executes model output. The sandbox returns type-tagged JSON; `harness.values.decode`
rebuilds native Python values and the comparison below uses real `==`, which is what makes the
result faithful to EvalPlus's in-process `out == exp`.

Source of the comparison rules (fetched 2026-09-30, cited in notes.md):
  evalplus/eval/__init__.py          `unsafe_execute` special-oracle block and the atol fallback
  evalplus/eval/_special_oracle.py   MBPP_OUTPUT_NOT_NONE_TASKS, MBPP_OUTPUT_SET_EQ_TASKS,
                                     _surface_Area, _digit_distance_nums, _poly
  evalplus/config.py                 DEFAULT_MIN_TIME_LIMIT = 1.0, DEFAULT_GT_TIME_LIMIT_FACTOR = 4.0
at evalplus tag v0.3.1, commit e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from . import values
from .sandbox import DEFAULT_CPU_SECONDS, DEFAULT_WALL_SECONDS, SandboxResult, runner_source

# -- ported EvalPlus constants ------------------------------------------------------------------

DEFAULT_ATOL = 1e-6
RTOL = 1e-07  # np.testing.assert_allclose default, set explicitly by EvalPlus
MIN_TIME_LIMIT = 1.0
GT_TIME_LIMIT_FACTOR = 4.0

# evalplus/eval/_special_oracle.py, verbatim task lists.
MBPP_OUTPUT_NOT_NONE_TASKS = ["check_str", "text_match_three", "text_starta_endb"]
MBPP_OUTPUT_SET_EQ_TASKS = [
    "similar_elements",        # Mbpp/2
    "find_char_long",          # Mbpp/7
    "common_in_nested_lists",  # Mbpp/111
    "extract_singly",          # Mbpp/140
    "larg_nnum",               # Mbpp/232
    "intersection_array",      # Mbpp/249
    "find_dissimilar",         # Mbpp/579
    "Diff",                    # Mbpp/769
]

FAILURE_CLASSES = ("none", "no-code", "syntax-error", "runtime-error", "wrong-answer", "timeout",
                   "sandbox-error", "truncated")

STATUS_CHAR = {"pass": ".", "wrong-answer": "x", "exception": "e", "timeout": "t",
               "harness-error": "h", "not-run": "-"}


def _surface_Area(base_edge, height):
    """Oracle for Mbpp/581: treats `height` as the perpendicular base-to-apex distance."""
    slant_height = math.sqrt((base_edge / 2) ** 2 + height ** 2)
    base_area = base_edge ** 2
    lateral_area = 4 * (base_edge * slant_height) / 2
    return round(base_area + lateral_area)


def _digit_distance_nums(num1, num2):
    """Oracle for Mbpp/558: zero-pads both numbers to equal length before summing digit deltas."""
    str_num1, str_num2 = str(num1), str(num2)
    max_length = max(len(str_num1), len(str_num2))
    str_num1, str_num2 = str_num1.zfill(max_length), str_num2.zfill(max_length)
    return sum(abs(int(a) - int(b)) for a, b in zip(str_num1, str_num2))


def _poly(xs: list, x: float):
    """Oracle for HumanEval/32: evaluates the polynomial with coefficients xs at x."""
    return sum(coeff * math.pow(x, index) for index, coeff in enumerate(xs))


# -- generic comparison -------------------------------------------------------------------------


def is_floats(value) -> bool:
    """Port of evalplus.eval.is_floats (the numpy branch is unreachable without numpy)."""
    if isinstance(value, float):
        return True
    if isinstance(value, (list, tuple)) and value:
        return all(isinstance(item, float) for item in value)
    return False


def _equal(actual, expected) -> bool:
    try:
        return bool(actual == expected)
    except Exception:
        return False


def allclose(actual, expected, rtol: float = RTOL, atol: float = DEFAULT_ATOL) -> bool:
    """Stand-in for np.allclose(out, exp, rtol, atol) over scalars and same-length sequences.

    NaN is never close (numpy's equal_nan defaults to False); infinities match only themselves.
    """
    if isinstance(actual, bool) != isinstance(expected, bool):
        return False
    if isinstance(actual, complex) or isinstance(expected, complex):
        if not isinstance(actual, (int, float, complex)) or not isinstance(
                expected, (int, float, complex)):
            return False
        try:
            return abs(actual - expected) <= atol + rtol * abs(expected)
        except (TypeError, OverflowError):
            return False
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if math.isnan(actual) or math.isnan(expected):
            return False
        if math.isinf(actual) or math.isinf(expected):
            return actual == expected
        return abs(actual - expected) <= atol + rtol * abs(expected)
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            allclose(a, e, rtol, atol) for a, e in zip(actual, expected))
    return False


def same(expected, actual, atol: float = 0.0) -> bool:
    """EvalPlus-style equality between an expected and an actual value.

    Exact `==` first (so ints/strings/bools/None/tuples/lists/sets behave exactly as they do in
    EvalPlus's in-process comparison), then the tolerance fallback: when the task sets no tolerance
    but the expected value is float-shaped, 1e-6 is enforced; when a tolerance applies, types must
    match, sequence lengths must match, and values must be within `atol` at `rtol=1e-07`.
    """
    if _equal(actual, expected):
        return True
    tolerance = atol
    if tolerance == 0 and is_floats(expected):
        tolerance = DEFAULT_ATOL
    if tolerance == 0:
        return False
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, (list, tuple)) and len(actual) != len(expected):
        return False
    return allclose(actual, expected, RTOL, tolerance)


def _set_equal(actual, expected) -> bool:
    """set(out) == set(exp) for the eight MBPP+ unordered tasks."""
    try:
        return set(actual) == set(expected)
    except TypeError:
        return False


def compare_output(dataset: str, entry_point: str, raw_input, expected, actual,
                   atol: float = 0.0) -> tuple[bool, str | None]:
    """Apply the task-specific oracle, then the generic comparison. Returns (passed, oracle used).

    `dataset` is "humaneval" or "mbpp". `raw_input` is the argument list as stored in the dataset
    (needed by the three oracles that recompute an alternative answer from the inputs).
    `expected` and `actual` are already-decoded native values.
    """
    args = raw_input if isinstance(raw_input, (list, tuple)) else [raw_input]

    if dataset == "humaneval" and entry_point == "find_zero":
        # EvalPlus ignores the recorded expected value here and checks the root directly.
        try:
            return abs(_poly(list(args[0]), actual)) <= atol, "humaneval:find_zero"
        except Exception:
            return False, "humaneval:find_zero"

    if dataset == "mbpp":
        if entry_point == "are_equivalent":  # Mbpp/164: any answer accepted
            return True, "mbpp:are_equivalent"
        if entry_point == "sum_div":  # Mbpp/295
            if _equal(actual, expected) or _equal(actual, 0):
                return True, "mbpp:sum_div"
        elif entry_point == "surface_Area":  # Mbpp/581
            if _equal(actual, expected):
                return True, "mbpp:surface_Area"
            try:
                if abs(actual - _surface_Area(*args)) <= atol:
                    return True, "mbpp:surface_Area"
            except Exception:
                pass
        elif entry_point == "digit_distance_nums":  # Mbpp/558
            if _equal(actual, expected) or _equal(actual, _digit_distance_nums(*args)):
                return True, "mbpp:digit_distance_nums"
        elif entry_point in MBPP_OUTPUT_SET_EQ_TASKS:
            return _set_equal(actual, expected), "mbpp:set-eq"
        elif entry_point in MBPP_OUTPUT_NOT_NONE_TASKS:
            # The sandbox runner already reduced both sides to booleans (EvalPlus's
            # `exp == (out is not None)` branch, with its isinstance(out, bool) exception).
            return _equal(actual, expected), "mbpp:not-none"

    return same(expected, actual, atol), None


# -- task grading -------------------------------------------------------------------------------


@dataclass
class SetResult:
    """Outcome over one input set (base or plus) for one task."""

    passed: bool = False
    inputs: int = 0
    completed: int = 0
    counts: dict = field(default_factory=dict)
    statuses: str = ""
    stage: str | None = None
    sandbox: dict = field(default_factory=dict)
    first_failure: dict | None = None
    failure_class: str = "none"
    failure_detail: str | None = None

    def as_dict(self) -> dict:
        return {
            "passed": self.passed, "inputs": self.inputs, "completed": self.completed,
            "counts": self.counts, "statuses": self.statuses, "stage": self.stage,
            "sandbox": self.sandbox, "firstFailure": self.first_failure,
            "failureClass": self.failure_class, "failureDetail": self.failure_detail,
        }


def per_input_limits(reference_times: list[float] | None, count: int) -> list[float]:
    """max(1.0 s, 4 x canonical per-input time), per EvalPlus config; 1.0 s when unknown."""
    times = list(reference_times or [])
    limits = []
    for index in range(count):
        reference = times[index] if index < len(times) else 0.0
        limits.append(max(MIN_TIME_LIMIT, GT_TIME_LIMIT_FACTOR * float(reference or 0.0)))
    return limits


def build_job(code: str, entry_point: str, task_id: str, dataset: str, inputs: list,
              per_input_seconds: list[float], not_none_mode: str | None = None,
              record_time: bool = False, exec_seconds: float = 10.0) -> dict:
    return {
        "code": code,
        "entry_point": entry_point,
        "task_id": task_id,
        "inputs": inputs,
        "deserialize": "mbpp" if dataset == "mbpp" else None,
        "not_none_mode": not_none_mode,
        "per_input_seconds": per_input_seconds,
        "record_time": record_time,
        "exec_seconds": exec_seconds,
    }


def not_none_mode_for(dataset: str, entry_point: str, trusted: bool) -> str | None:
    if dataset == "mbpp" and entry_point in MBPP_OUTPUT_NOT_NONE_TASKS:
        return "trusted" if trusted else "candidate"
    return None


def run_in_sandbox(sandbox, job: dict, wall_seconds: float = DEFAULT_WALL_SECONDS,
                   cpu_seconds: int = DEFAULT_CPU_SECONDS):
    """Execute one job. Returns (SandboxResult, meta dict, list of per-input rows)."""
    result: SandboxResult = sandbox.run_python(
        {"sandbox_runner.py": runner_source()}, argv=["sandbox_runner.py"],
        stdin_text=json.dumps(job), timeout=wall_seconds, cpu_seconds=cpu_seconds,
        want=("meta.json", "results.jsonl"))
    try:
        meta = json.loads(result.files.get("meta.json") or "null") or {}
    except json.JSONDecodeError:
        meta = {}
    rows = []
    for line in (result.files.get("results.jsonl") or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            break  # a truncated final line after a hard kill
    return result, meta, rows


def classify_stage(sandbox_result, meta: dict) -> tuple[str, str] | None:
    """Map a whole-run failure (before per-input comparison) to (failureClass, detail)."""
    stage = meta.get("stage")
    if stage == "syntax-error":
        return "syntax-error", meta.get("error") or "syntax error"
    if stage in ("exec-error", "exec-timeout"):
        return "runtime-error", meta.get("error") or f"module-level {stage}"
    if stage == "missing-entry-point":
        return "runtime-error", meta.get("error") or "entry point not defined"
    if stage == "deserialize-error":
        return "sandbox-error", meta.get("error") or "input deserialization failed"
    if stage == "bad-job":
        return "sandbox-error", meta.get("error") or "runner could not parse its job"
    if sandbox_result.status == "sandbox-error":
        return "sandbox-error", (sandbox_result.stderr or "")[-400:] or "sandbox failed to launch"
    if not stage and sandbox_result.timed_out:
        return "timeout", f"killed before starting ({sandbox_result.status})"
    if not stage:
        return "sandbox-error", (sandbox_result.stderr or "")[-400:] or "runner produced no meta"
    return None


def grade_set(dataset: str, entry_point: str, task_id: str, raw_inputs: list,
              expected: list, atol: float, sandbox_result, meta: dict, rows: list) -> SetResult:
    """Compare one input set's returned values against the cached expected outputs."""
    outcome = SetResult(inputs=len(raw_inputs), completed=len(rows), stage=meta.get("stage"),
                        sandbox={"status": sandbox_result.status, "signal": sandbox_result.signal,
                                 "wallMs": sandbox_result.wall_ms})
    stage_failure = classify_stage(sandbox_result, meta)
    if stage_failure is not None:
        outcome.failure_class, outcome.failure_detail = stage_failure
        outcome.statuses = STATUS_CHAR["not-run"] * len(raw_inputs)
        outcome.counts = {"not-run": len(raw_inputs)}
        return outcome

    chars: list[str] = []
    counts: dict[str, int] = {}
    for index in range(len(raw_inputs)):
        row = rows[index] if index < len(rows) else None
        if row is None:
            label = "not-run"
        elif row.get("status") == "ok":
            actual_tagged = row.get("value")
            try:
                actual = values.decode(actual_tagged)
            except values.DecodeError as exc:
                label = "harness-error"
                counts[label] = counts.get(label, 0) + 1
                chars.append(STATUS_CHAR[label])
                if outcome.first_failure is None:
                    outcome.first_failure = {"index": index, "status": label, "error": str(exc)}
                continue
            expected_tagged = expected[index] if index < len(expected) else None
            if values.is_digest(actual_tagged) or values.is_digest(expected_tagged):
                # One side was too large to ship out of the sandbox, so the two canonical forms
                # are compared by hash. Exact equality only: no tolerance, no special oracle.
                matched = values.digest_of(expected_tagged) == values.digest_of(actual_tagged)
                label = "pass" if matched else "wrong-answer"
                if not matched and outcome.first_failure is None:
                    outcome.first_failure = {
                        "index": index, "status": label, "oracle": "digest",
                        "expected": values.brief(expected_tagged),
                        "actual": values.brief(actual_tagged),
                    }
                counts[label] = counts.get(label, 0) + 1
                chars.append(STATUS_CHAR[label])
                continue
            try:
                expected_value = values.decode(expected_tagged)
            except values.DecodeError as exc:
                label = "harness-error"
                counts[label] = counts.get(label, 0) + 1
                chars.append(STATUS_CHAR[label])
                if outcome.first_failure is None:
                    outcome.first_failure = {"index": index, "status": label,
                                             "error": f"bad expected output: {exc}"}
                continue
            passed, oracle = compare_output(dataset, entry_point, raw_inputs[index],
                                            expected_value, actual, atol)
            label = "pass" if passed else "wrong-answer"
            if not passed and outcome.first_failure is None:
                outcome.first_failure = {
                    "index": index, "status": label, "oracle": oracle,
                    "expected": values.brief(expected_tagged),
                    "actual": values.brief(actual_tagged),
                }
        else:
            label = row.get("status") or "harness-error"
            if label not in STATUS_CHAR:
                label = "harness-error"
            if outcome.first_failure is None:
                outcome.first_failure = {"index": index, "status": label,
                                         "error": row.get("error")}
        counts[label] = counts.get(label, 0) + 1
        chars.append(STATUS_CHAR[label])

    outcome.counts = counts
    outcome.statuses = "".join(chars)
    outcome.passed = counts.get("pass", 0) == len(raw_inputs)
    if outcome.passed:
        outcome.failure_class, outcome.failure_detail = "none", None
        return outcome

    status = (outcome.first_failure or {}).get("status", "not-run")
    mapping = {"timeout": "timeout", "exception": "runtime-error", "wrong-answer": "wrong-answer",
               "harness-error": "sandbox-error", "not-run": "timeout"}
    outcome.failure_class = mapping.get(status, "wrong-answer")
    if status == "not-run":
        outcome.failure_class = "timeout" if sandbox_result.timed_out else "sandbox-error"
        outcome.failure_detail = (
            f"only {len(rows)}/{len(raw_inputs)} inputs completed "
            f"(sandbox status {sandbox_result.status})")
    else:
        failure = outcome.first_failure or {}
        if status == "wrong-answer":
            outcome.failure_detail = (f"input {failure.get('index')}: expected "
                                      f"{failure.get('expected')} got {failure.get('actual')}")
        else:
            outcome.failure_detail = f"input {failure.get('index')}: {failure.get('error')}"
    return outcome


def combine_failure_class(base: SetResult, plus: SetResult | None) -> tuple[str, str | None]:
    """Report the base failure when base fails, otherwise the plus failure."""
    if base.failure_class != "none":
        return base.failure_class, base.failure_detail
    if plus is not None and plus.failure_class != "none":
        return plus.failure_class, plus.failure_detail
    return "none", None
