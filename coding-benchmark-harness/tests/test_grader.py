"""Grading: `same()` semantics, the ported EvalPlus oracles, and failure classification.

The timeout and syntax-error cases use the real sandbox with tiny programs, as DESIGN.md requires.
"""

import os
import sys
import unittest

import context  # noqa: F401

from harness import grader, values
from harness.grader import SetResult, allclose, compare_output, grade_set, is_floats, \
    per_input_limits, same
from harness.sandbox import SANDBOX_EXEC, SandboxExec, SandboxResult
from harness.sandbox_runner import encode

MAC = sys.platform == "darwin" and os.path.exists(SANDBOX_EXEC)


def tag(value):
    """Encode a native value exactly as the sandbox runner would."""
    return encode(value)


class SameCase(unittest.TestCase):
    def test_exact_scalars(self):
        self.assertTrue(same(1, 1))
        self.assertTrue(same("a", "a"))
        self.assertTrue(same(True, True))
        self.assertTrue(same(None, None))
        self.assertFalse(same(1, 2))
        self.assertFalse(same("a", "A"))
        self.assertFalse(same(None, 0))

    def test_python_equality_quirks_are_preserved(self):
        # EvalPlus compares with plain `==`, so these hold there too.
        self.assertTrue(same(1, 1.0))
        self.assertTrue(same(1, True))
        self.assertTrue(same(0, False))

    def test_tuples_and_lists_are_not_interchangeable(self):
        self.assertTrue(same((1, 2), (1, 2)))
        self.assertTrue(same([1, 2], [1, 2]))
        self.assertFalse(same((1, 2), [1, 2]))
        self.assertFalse(same([1, 2], (1, 2)))

    def test_nested_sequences(self):
        self.assertTrue(same([[1, (2, 3)]], [[1, (2, 3)]]))
        self.assertFalse(same([[1, (2, 3)]], [[1, [2, 3]]]))

    def test_sets_compare_by_membership_not_order(self):
        self.assertTrue(same({1, 2, 3}, {3, 2, 1}))
        self.assertFalse(same({1, 2}, {1, 2, 3}))

    def test_dicts(self):
        self.assertTrue(same({"a": 1, "b": 2}, {"b": 2, "a": 1}))
        self.assertFalse(same({"a": 1}, {"a": 2}))

    def test_float_tolerance_defaults_to_1e_6_when_task_sets_none(self):
        self.assertTrue(same(1.0, 1.0 + 1e-9))
        self.assertFalse(same(1.0, 1.01))
        self.assertTrue(same([1.0, 2.0], [1.0 + 1e-9, 2.0]))

    def test_explicit_atol(self):
        self.assertTrue(same(1.0, 1.005, atol=1e-2))
        self.assertFalse(same(1.0, 1.05, atol=1e-2))

    def test_atol_requires_matching_types_and_lengths(self):
        self.assertFalse(same([1.0, 2.0], (1.0, 2.0), atol=1e-2))
        self.assertFalse(same([1.0, 2.0], [1.0], atol=1e-2))

    def test_integers_do_not_get_a_free_tolerance(self):
        self.assertFalse(same(10, 11))
        self.assertFalse(is_floats(10))
        self.assertFalse(is_floats([]))
        self.assertTrue(is_floats([1.0, 2.0]))

    def test_nan_never_matches(self):
        self.assertFalse(same(float("nan"), float("nan")))
        # Decoding always builds fresh float objects, so CPython's identity short-circuit inside
        # list comparison never fires -- the same as EvalPlus, where expected and actual come from
        # two separate executions.
        left = values.decode(tag([float("nan")]))
        right = values.decode(tag([float("nan")]))
        self.assertFalse(same(left, right))
        self.assertIsNot(left[0], right[0])

    def test_infinities_match_themselves(self):
        self.assertTrue(same(float("inf"), float("inf")))
        self.assertFalse(same(float("inf"), float("-inf")))

    def test_allclose_rejects_non_numeric(self):
        self.assertFalse(allclose("a", "a"))
        self.assertFalse(allclose(True, 1.0))

    def test_opaque_values_only_match_identical_reprs(self):
        left = values.decode({"t": "repr", "cls": "Match", "v": "<re.Match object; span=(0, 1)>"})
        right = values.decode({"t": "repr", "cls": "Match", "v": "<re.Match object; span=(0, 1)>"})
        other = values.decode({"t": "repr", "cls": "Match", "v": "<re.Match object; span=(0, 2)>"})
        self.assertTrue(same(left, right))
        self.assertFalse(same(left, other))

    def test_overflow_never_matches(self):
        overflow = values.decode({"t": "overflow"})
        self.assertFalse(same(overflow, overflow))
        self.assertFalse(same([1], overflow))


class BigIntegerCase(unittest.TestCase):
    """Regression for the bug the first full live run hit at HumanEval/83.

    Python 3.11+ caps integer<->string conversion at 4300 digits in both directions. The sandbox
    runner lifts it for executed code, but the harness process also converts when decoding a
    result (`int(tagged["v"])`) and when rendering a failure detail (`repr`). Before the fix, a
    task returning a big integer raised ValueError out of `grade_set` and ended the run with
    status `error` rather than scoring that one task.
    """

    HUGE = int("9" * 10000)

    def test_decoding_a_10000_digit_integer_works(self):
        decoded = values.decode(tag(self.HUGE))
        self.assertEqual(decoded, self.HUGE)
        self.assertEqual(len(str(decoded)), 10000)

    def test_same_compares_big_integers(self):
        self.assertTrue(same(self.HUGE, int("9" * 10000)))
        self.assertFalse(same(self.HUGE, self.HUGE + 1))

    def test_brief_renders_a_big_integer_without_raising(self):
        rendered = values.brief(tag(self.HUGE))
        self.assertTrue(rendered.endswith("..."))
        self.assertLessEqual(len(rendered), 260)

    def test_grade_set_scores_a_big_integer_result(self):
        rows = [{"i": 0, "status": "ok", "value": tag(self.HUGE)}]
        outcome = grade_set("humaneval", "f", "HumanEval/83", [[1]], [tag(self.HUGE)], 0.0,
                            fake_sandbox_result(), {"stage": "done"}, rows)
        self.assertTrue(outcome.passed, outcome.as_dict())

    def test_grade_set_reports_a_big_integer_mismatch_without_raising(self):
        rows = [{"i": 0, "status": "ok", "value": tag(self.HUGE)}]
        outcome = grade_set("humaneval", "f", "HumanEval/83", [[1]],
                            [tag(int("8" * 10000))], 0.0, fake_sandbox_result(),
                            {"stage": "done"}, rows)
        self.assertEqual(outcome.failure_class, "wrong-answer")
        self.assertIsInstance(outcome.failure_detail, str)

    def test_the_interpreter_limit_is_lifted_by_importing_harness(self):
        self.assertEqual(sys.get_int_max_str_digits(), 0)


class OracleCase(unittest.TestCase):
    """Ported from evalplus/eval/__init__.py and evalplus/eval/_special_oracle.py at v0.3.1."""

    def test_humaneval_find_zero_checks_the_root_not_the_recorded_value(self):
        # 2 + 3x == 0 at x = -2/3; the recorded expected value is deliberately different.
        passed, oracle = compare_output("humaneval", "find_zero", [[2, 3]], -1.0,
                                        -2.0 / 3.0, atol=1e-4)
        self.assertTrue(passed)
        self.assertEqual(oracle, "humaneval:find_zero")
        passed, _ = compare_output("humaneval", "find_zero", [[2, 3]], -1.0, 5.0, atol=1e-4)
        self.assertFalse(passed)

    def test_mbpp_are_equivalent_accepts_anything(self):
        passed, oracle = compare_output("mbpp", "are_equivalent", [1, 2], True, "nonsense")
        self.assertTrue(passed)
        self.assertEqual(oracle, "mbpp:are_equivalent")

    def test_mbpp_sum_div_also_accepts_zero(self):
        self.assertTrue(compare_output("mbpp", "sum_div", [8], 7, 0)[0])
        self.assertTrue(compare_output("mbpp", "sum_div", [8], 7, 7)[0])
        self.assertFalse(compare_output("mbpp", "sum_div", [8], 7, 3)[0])

    def test_mbpp_surface_area_alternate_oracle(self):
        alternate = grader._surface_Area(3, 4)
        self.assertTrue(compare_output("mbpp", "surface_Area", [3, 4], 33, alternate)[0])
        self.assertTrue(compare_output("mbpp", "surface_Area", [3, 4], 33, 33)[0])
        self.assertFalse(compare_output("mbpp", "surface_Area", [3, 4], 33, 1)[0])

    def test_mbpp_digit_distance_alternate_oracle(self):
        self.assertEqual(grader._digit_distance_nums(1, 2), 1)
        self.assertEqual(grader._digit_distance_nums(23, 56), 6)
        self.assertTrue(compare_output("mbpp", "digit_distance_nums", [23, 56], 99, 6)[0])
        self.assertFalse(compare_output("mbpp", "digit_distance_nums", [23, 56], 99, 7)[0])

    def test_mbpp_set_equality_tasks_ignore_order_and_duplicates(self):
        for entry_point in grader.MBPP_OUTPUT_SET_EQ_TASKS:
            with self.subTest(entry_point=entry_point):
                passed, oracle = compare_output("mbpp", entry_point, [[1], [1]], (4, 5), [5, 4])
                self.assertTrue(passed)
                self.assertEqual(oracle, "mbpp:set-eq")
        self.assertFalse(compare_output("mbpp", "similar_elements", [[1], [1]], (4, 5), [4])[0])

    def test_mbpp_not_none_tasks_compare_booleans(self):
        for entry_point in grader.MBPP_OUTPUT_NOT_NONE_TASKS:
            with self.subTest(entry_point=entry_point):
                passed, oracle = compare_output("mbpp", entry_point, ["abc"], True, True)
                self.assertTrue(passed)
                self.assertEqual(oracle, "mbpp:not-none")
                self.assertFalse(compare_output("mbpp", entry_point, ["abc"], True, False)[0])

    def test_oracles_do_not_leak_across_datasets(self):
        # `find_zero` is a HumanEval oracle only; under mbpp it falls through to `same()`.
        passed, oracle = compare_output("mbpp", "find_zero", [[2, 3]], -1.0, -2.0 / 3.0)
        self.assertFalse(passed)
        self.assertIsNone(oracle)
        # `sum_div` is an MBPP oracle only.
        self.assertFalse(compare_output("humaneval", "sum_div", [8], 7, 0)[0])

    def test_poly_matches_evalplus(self):
        self.assertAlmostEqual(grader._poly([1, 2, 3], 2.0), 1 + 4 + 12)


class PerInputLimitCase(unittest.TestCase):
    def test_min_one_second_and_four_times_reference(self):
        self.assertEqual(per_input_limits([0.1, 0.5, 2.0], 3), [1.0, 2.0, 8.0])

    def test_missing_reference_times_fall_back_to_the_minimum(self):
        self.assertEqual(per_input_limits(None, 2), [1.0, 1.0])
        self.assertEqual(per_input_limits([], 1), [1.0])
        self.assertEqual(per_input_limits([0.0], 1), [1.0])


class TaskBudgetCase(unittest.TestCase):
    """Per-task budgets scale from the canonical solution's measured cost."""

    def test_floor_applies_for_cheap_tasks(self):
        self.assertEqual(grader.task_budget(0.04, 60, 300.0), (60, 300.0))
        self.assertEqual(grader.task_budget(0.0, 60, 300.0), (60, 300.0))

    def test_expensive_tasks_get_four_times_the_canonical_cost(self):
        # Mbpp/255's canonical run needed ~193 s of sandbox wall time, nearly all of it the
        # harness's own serialization of a ~3 GB canonical value.
        cpu, wall = grader.task_budget(193.0, 60, 300.0)
        self.assertEqual(cpu, 773)
        self.assertAlmostEqual(wall, 802.0)

    def test_budget_never_drops_below_the_configured_floor(self):
        for reference in (0.0, 1.0, 10.0, 14.9):
            with self.subTest(reference=reference):
                cpu, wall = grader.task_budget(reference, 60, 300.0)
                self.assertGreaterEqual(cpu, 60)
                self.assertGreaterEqual(wall, 300.0)

    def test_negative_reference_is_ignored(self):
        self.assertEqual(grader.task_budget(-5.0, 60, 300.0), (60, 300.0))


class DigestComparisonCase(unittest.TestCase):
    def digest_tag(self, seed="a", size=100000):
        return {"t": "digest", "v": seed * 64, "bytes": size}

    def test_equal_digests_pass(self):
        expected = actual = self.digest_tag()
        outcome = grade_set("humaneval", "f", "T/0", [[1]], [expected], 0.0,
                            fake_sandbox_result(), {"stage": "done"},
                            [{"i": 0, "status": "ok", "value": actual}])
        self.assertTrue(outcome.passed)

    def test_different_digests_fail(self):
        outcome = grade_set("humaneval", "f", "T/0", [[1]], [self.digest_tag("a")], 0.0,
                            fake_sandbox_result(), {"stage": "done"},
                            [{"i": 0, "status": "ok", "value": self.digest_tag("b")}])
        self.assertEqual(outcome.failure_class, "wrong-answer")
        self.assertEqual(outcome.first_failure["oracle"], "digest")

    def test_one_sided_digest_is_a_mismatch(self):
        # A digested value is over the size threshold and a tagged one is under it, so equal
        # values could never land on opposite sides.
        outcome = grade_set("humaneval", "f", "T/0", [[1]], [self.digest_tag()], 0.0,
                            fake_sandbox_result(), {"stage": "done"},
                            [{"i": 0, "status": "ok", "value": tag([1, 2, 3])}])
        self.assertEqual(outcome.failure_class, "wrong-answer")
        outcome = grade_set("humaneval", "f", "T/0", [[1]], [tag([1, 2, 3])], 0.0,
                            fake_sandbox_result(), {"stage": "done"},
                            [{"i": 0, "status": "ok", "value": self.digest_tag()}])
        self.assertEqual(outcome.failure_class, "wrong-answer")

    def test_digest_path_bypasses_oracles_and_tolerance(self):
        # `are_equivalent` normally accepts anything; on the digest path it does not.
        outcome = grade_set("mbpp", "are_equivalent", "Mbpp/164", [[1]],
                            [self.digest_tag("a")], 1.0, fake_sandbox_result(),
                            {"stage": "done"},
                            [{"i": 0, "status": "ok", "value": self.digest_tag("b")}])
        self.assertFalse(outcome.passed)


def fake_sandbox_result(status="ok", signal=None):
    return SandboxResult(status=status, returncode=0 if status == "ok" else 1, signal=signal)


class GradeSetCase(unittest.TestCase):
    def rows(self, *statuses_and_values):
        rows = []
        for index, (status, value) in enumerate(statuses_and_values):
            row = {"i": index, "status": status}
            if status == "ok":
                row["value"] = tag(value)
            else:
                row["error"] = str(value)
            rows.append(row)
        return rows

    def test_all_pass(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1], [2]],
                            [tag(2), tag(4)], 0.0, fake_sandbox_result(),
                            {"stage": "done"}, self.rows(("ok", 2), ("ok", 4)))
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.failure_class, "none")
        self.assertEqual(outcome.statuses, "..")
        self.assertIsNone(outcome.first_failure)

    def test_wrong_answer_records_the_first_failing_input(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1], [2], [3]],
                            [tag(2), tag(4), tag(6)], 0.0, fake_sandbox_result(),
                            {"stage": "done"}, self.rows(("ok", 2), ("ok", 99), ("ok", 6)))
        self.assertFalse(outcome.passed)
        self.assertEqual(outcome.failure_class, "wrong-answer")
        self.assertEqual(outcome.first_failure["index"], 1)
        self.assertIn("99", outcome.failure_detail)
        self.assertEqual(outcome.statuses, ".x.")

    def test_exception_maps_to_runtime_error(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1], [2]], [tag(2), tag(4)], 0.0,
                            fake_sandbox_result(), {"stage": "done"},
                            self.rows(("exception", "ValueError: boom"), ("ok", 4)))
        self.assertEqual(outcome.failure_class, "runtime-error")
        self.assertIn("ValueError", outcome.failure_detail)
        self.assertEqual(outcome.statuses, "e.")

    def test_per_input_timeout_maps_to_timeout(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1]], [tag(2)], 0.0,
                            fake_sandbox_result(), {"stage": "done"},
                            self.rows(("timeout", "exceeded 1.000s")))
        self.assertEqual(outcome.failure_class, "timeout")
        self.assertEqual(outcome.statuses, "t")

    def test_syntax_error_stage(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1], [2]], [tag(2), tag(4)], 0.0,
                            fake_sandbox_result(), {"stage": "syntax-error",
                                                    "error": "SyntaxError: bad"}, [])
        self.assertEqual(outcome.failure_class, "syntax-error")
        self.assertEqual(outcome.statuses, "--")
        self.assertEqual(outcome.counts, {"not-run": 2})

    def test_missing_entry_point_stage(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1]], [tag(2)], 0.0,
                            fake_sandbox_result(), {"stage": "missing-entry-point",
                                                    "error": "f not defined after exec"}, [])
        self.assertEqual(outcome.failure_class, "runtime-error")

    def test_hard_kill_with_partial_rows_is_a_timeout(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1], [2], [3]],
                            [tag(2), tag(4), tag(6)], 0.0,
                            fake_sandbox_result("cpu-timeout", signal=24), {"stage": "started"},
                            self.rows(("ok", 2)))
        self.assertFalse(outcome.passed)
        self.assertEqual(outcome.failure_class, "timeout")
        self.assertEqual(outcome.statuses, ".--")
        self.assertIn("1/3 inputs completed", outcome.failure_detail)

    def test_no_meta_is_a_sandbox_error(self):
        outcome = grade_set("humaneval", "f", "HumanEval/0", [[1]], [tag(2)], 0.0,
                            fake_sandbox_result("crashed"), {}, [])
        self.assertEqual(outcome.failure_class, "sandbox-error")

    def test_combine_failure_class_prefers_base(self):
        base = SetResult(failure_class="syntax-error", failure_detail="b")
        plus = SetResult(failure_class="wrong-answer", failure_detail="p")
        self.assertEqual(grader.combine_failure_class(base, plus), ("syntax-error", "b"))
        clean = SetResult(failure_class="none")
        self.assertEqual(grader.combine_failure_class(clean, plus), ("wrong-answer", "p"))
        self.assertEqual(grader.combine_failure_class(clean, None), ("none", None))

    def test_set_result_serialises(self):
        payload = SetResult(passed=True, inputs=1, statuses=".").as_dict()
        self.assertEqual(payload["passed"], True)
        self.assertEqual(payload["failureClass"], "none")


@unittest.skipUnless(MAC, f"requires macOS with {SANDBOX_EXEC}")
class SandboxGradingCase(unittest.TestCase):
    """End-to-end grading through the real sandbox, per DESIGN.md's test requirements."""

    @classmethod
    def setUpClass(cls):
        cls.sandbox = SandboxExec()

    def grade(self, code, entry_point, inputs, expected, dataset="humaneval", atol=0.0,
              limits=None, **kwargs):
        job = grader.build_job(code, entry_point, "HumanEval/0", dataset, inputs,
                              limits or grader.per_input_limits(None, len(inputs)), **kwargs)
        result, meta, rows = grader.run_in_sandbox(self.sandbox, job, wall_seconds=30,
                                                   cpu_seconds=20)
        return grade_set(dataset, entry_point, "HumanEval/0", inputs, expected, atol,
                         result, meta, rows)

    def test_correct_solution_passes(self):
        outcome = self.grade("def add(a, b):\n    return a + b\n", "add",
                             [[1, 2], [3, 4]], [tag(3), tag(7)])
        self.assertTrue(outcome.passed, outcome.as_dict())

    def test_wrong_solution_is_wrong_answer(self):
        outcome = self.grade("def add(a, b):\n    return a - b\n", "add",
                             [[1, 2]], [tag(3)])
        self.assertEqual(outcome.failure_class, "wrong-answer")

    def test_syntax_error_sample(self):
        outcome = self.grade("def add(a, b)\n    return a + b\n", "add", [[1, 2]], [tag(3)])
        self.assertEqual(outcome.failure_class, "syntax-error")
        self.assertIn("SyntaxError", outcome.failure_detail)

    def test_runtime_error_sample(self):
        outcome = self.grade("def add(a, b):\n    return a + undefined_name\n", "add",
                             [[1, 2]], [tag(3)])
        self.assertEqual(outcome.failure_class, "runtime-error")
        self.assertIn("NameError", outcome.failure_detail)

    def test_per_input_timeout_sample(self):
        code = "def add(a, b):\n    while True:\n        pass\n"
        outcome = self.grade(code, "add", [[1, 2]], [tag(3)], limits=[0.4])
        self.assertEqual(outcome.failure_class, "timeout")

    def test_tuple_returning_solution_is_not_confused_with_a_list(self):
        outcome = self.grade("def pair(a):\n    return [a, a]\n", "pair", [[1]], [tag((1, 1))])
        self.assertEqual(outcome.failure_class, "wrong-answer")
        outcome = self.grade("def pair(a):\n    return (a, a)\n", "pair", [[1]], [tag((1, 1))])
        self.assertTrue(outcome.passed)

    def test_mbpp_set_eq_task_through_the_sandbox(self):
        code = ("def similar_elements(a, b):\n"
                "    return tuple(sorted(set(a) & set(b), reverse=True))\n")
        outcome = self.grade(code, "similar_elements", [[[3, 4, 5, 6], [5, 7, 4, 10]]],
                             [tag((4, 5))], dataset="mbpp")
        self.assertTrue(outcome.passed, outcome.as_dict())

    def test_mbpp_not_none_task_through_the_sandbox(self):
        code = "import re\ndef check_str(s):\n    return re.match(r'^[aeiouAEIOU]', s)\n"
        outcome = self.grade(code, "check_str", [["annie"], ["dawood"]],
                             [tag(True), tag(False)], dataset="mbpp",
                             not_none_mode="candidate")
        self.assertTrue(outcome.passed, outcome.as_dict())


if __name__ == "__main__":
    unittest.main()
