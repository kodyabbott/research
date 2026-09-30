"""Suite loader tests, driven by the 3-task synthetic fixture rather than the real datasets.

`prepare.py --suite fixture` must have been run once (the end-to-end step does this); the tests
that need expected outputs skip with a clear message when the cache is absent.
"""

import gzip
import json
import unittest
from pathlib import Path

import context  # noqa: F401

from harness import suites
from harness.suites import Suite, SuiteError, Task, compute_digest, split_mbpp_prompt

FIXTURE_PREPARED = (suites.expected_dir("fixture") / "Fixture_0.json").exists()
PREPARE_HINT = "run: python3 coding-benchmark-harness/prepare.py --suite fixture"


class RegistryCase(unittest.TestCase):
    def test_registry_lists_the_three_suites(self):
        self.assertEqual(suites.suite_names(), ["fixture", "humaneval-plus", "mbpp-plus"])

    def test_pinned_versions_match_the_evalplus_source(self):
        registry = suites.registry()
        self.assertEqual(registry["suites"]["humaneval-plus"]["version"], "v0.1.10")
        self.assertEqual(registry["suites"]["mbpp-plus"]["version"], "v0.2.0")
        self.assertEqual(registry["evalplus"]["tag"], "v0.3.1")
        self.assertEqual(registry["suites"]["humaneval-plus"]["tasks"], 164)
        self.assertEqual(registry["suites"]["mbpp-plus"]["tasks"], 378)

    def test_release_urls_have_the_shape_evalplus_builds(self):
        for name, repo in (("humaneval-plus", "humanevalplus_release"),
                           ("mbpp-plus", "mbppplus_release")):
            entry = suites.entry_for(name)
            self.assertEqual(
                entry["url"],
                f"https://github.com/evalplus/{repo}/releases/download/"
                f"{entry['version']}/{entry['asset']}")

    def test_unknown_suite_raises(self):
        with self.assertRaises(SuiteError):
            suites.entry_for("no-such-suite")


class FixtureLoaderCase(unittest.TestCase):
    def test_fixture_file_matches_its_recorded_sha256(self):
        entry = suites.entry_for("fixture")
        path = suites.dataset_path("fixture")
        self.assertTrue(path.exists(), path)
        self.assertEqual(suites.sha256_file(path), entry["sha256"])

    def test_build_tasks_parses_three_tasks(self):
        tasks = suites.build_tasks("fixture")
        self.assertEqual([task.task_id for task in tasks],
                         ["Fixture/0", "Fixture/1", "Fixture/2"])
        self.assertEqual([task.entry_point for task in tasks],
                         ["add_two", "min_max", "mean_of"])
        self.assertTrue(all(task.dataset == "humaneval" for task in tasks))

    def test_humaneval_prompt_template_is_applied(self):
        task = suites.build_tasks("fixture")[0]
        self.assertTrue(task.prompt.startswith("Complete the following Python function."))
        self.assertIn("```python", task.prompt)
        self.assertTrue(task.prompt.endswith(task.source_prompt))

    def test_canonical_program_is_prompt_plus_solution(self):
        task = suites.build_tasks("fixture")[0]
        self.assertEqual(task.canonical_program, task.source_prompt + task.canonical_solution)
        compile(task.canonical_program, "<test>", "exec")

    def test_missing_required_field_is_rejected(self):
        broken = Path(context.FIXTURES) / "_broken.jsonl.gz"
        with gzip.open(broken, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps({"task_id": "X/0", "entry_point": "f", "prompt": "p"}) + "\n")
        try:
            registry = suites.registry()
            registry["suites"]["_broken"] = {
                "dataset": "humaneval", "localPath": "tests/fixtures/_broken.jsonl.gz"}
            original = suites.registry
            suites.registry = lambda: registry
            try:
                with self.assertRaises(SuiteError) as caught:
                    suites.build_tasks("_broken")
                self.assertIn("lacks", str(caught.exception))
            finally:
                suites.registry = original
        finally:
            broken.unlink(missing_ok=True)


@unittest.skipUnless(FIXTURE_PREPARED, PREPARE_HINT)
class FixtureExpectedCase(unittest.TestCase):
    def test_load_attaches_expected_outputs(self):
        suite = suites.load("fixture")
        self.assertEqual(len(suite.tasks), 3)
        self.assertEqual(suite.total_tasks, 3)
        self.assertEqual(suite.skipped, {})
        for task in suite.tasks:
            self.assertEqual(len(task.expected_for("base")), len(task.base_input))
            self.assertEqual(len(task.expected_for("plus")), len(task.plus_input))
            self.assertEqual(len(task.times_for("plus")), len(task.plus_input))

    def test_expected_values_are_correct_for_the_fixture(self):
        from harness import values
        suite = suites.load("fixture")
        by_id = {task.task_id: task for task in suite.tasks}
        add_two = by_id["Fixture/0"]
        self.assertEqual([values.decode(item) for item in add_two.expected_for("base")], [3, 7])
        min_max = by_id["Fixture/1"]
        first = values.decode(min_max.expected_for("base")[0])
        self.assertEqual(first, (1, 3))
        self.assertIs(type(first), tuple)  # a list would be a different answer

    def test_digest_is_stable_across_loads(self):
        self.assertEqual(suites.load("fixture").digest, suites.load("fixture").digest)

    def test_limit_and_ids_narrow_the_tasks_but_keep_the_suite_digest(self):
        full = suites.load("fixture")
        limited = suites.load("fixture", limit=1)
        chosen = suites.load("fixture", ids=["Fixture/2"])
        self.assertEqual(len(limited.tasks), 1)
        self.assertEqual([task.task_id for task in chosen.tasks], ["Fixture/2"])
        self.assertEqual(limited.digest, full.digest)
        self.assertEqual(chosen.digest, full.digest)

    def test_unknown_id_raises(self):
        with self.assertRaises(SuiteError):
            suites.load("fixture", ids=["Fixture/99"])

    def test_protocol_block_is_recorded(self):
        protocol = suites.load("fixture").protocol()
        self.assertEqual(protocol["suite"], "fixture")
        self.assertEqual(protocol["tasks"], 3)
        self.assertEqual(protocol["skippedAtPrepare"], 0)
        self.assertEqual(len(protocol["suiteDigest"]), 64)
        self.assertEqual(len(protocol["promptTemplateSha256"]), 64)


class DigestCase(unittest.TestCase):
    def make(self, task_id="A/0", prompt="p", entry_point="f"):
        return Task(task_id=task_id, dataset="humaneval", entry_point=entry_point, prompt=prompt,
                    source_prompt=prompt, canonical_solution="", base_input=[], plus_input=[],
                    atol=0.0)

    def test_digest_changes_with_every_covered_field(self):
        base = [self.make()]
        original = compute_digest(base, {"A/0": "h"})
        self.assertNotEqual(original, compute_digest([self.make(task_id="A/1")], {"A/1": "h"}))
        self.assertNotEqual(original, compute_digest([self.make(prompt="other")], {"A/0": "h"}))
        self.assertNotEqual(original, compute_digest([self.make(entry_point="g")], {"A/0": "h"}))
        self.assertNotEqual(original, compute_digest(base, {"A/0": "different"}))

    def test_digest_is_order_sensitive(self):
        one, two = self.make("A/0"), self.make("A/1")
        hashes = {"A/0": "x", "A/1": "y"}
        self.assertNotEqual(compute_digest([one, two], hashes),
                            compute_digest([two, one], hashes))

    def test_digest_is_not_confusable_by_field_concatenation(self):
        # Separators must prevent ("ab", "c") from hashing the same as ("a", "bc").
        left = compute_digest([self.make(task_id="ab", entry_point="c")], {})
        right = compute_digest([self.make(task_id="a", entry_point="bc")], {})
        self.assertNotEqual(left, right)


class MbppPromptCase(unittest.TestCase):
    """MBPP+ has no `text` field; the statement and its curated assertion come from `prompt`."""

    REAL = ('"""\nWrite a function to find the shared elements from the given two lists.\n'
            'assert set(similar_elements((3, 4, 5, 6),(5, 7, 4, 10))) == set((4, 5))\n"""\n')

    def test_split_extracts_statement_and_assertion(self):
        text, assertion = split_mbpp_prompt(self.REAL)
        self.assertEqual(text, "Write a function to find the shared elements from the given "
                               "two lists.")
        self.assertEqual(assertion,
                         "assert set(similar_elements((3, 4, 5, 6),(5, 7, 4, 10))) == set((4, 5))")

    def test_multi_line_statements_are_preserved(self):
        prompt = '"""\nLine one.\nLine two.\nassert f(1) == 2\n"""\n'
        text, assertion = split_mbpp_prompt(prompt)
        self.assertEqual(text, "Line one.\nLine two.")
        self.assertEqual(assertion, "assert f(1) == 2")

    def test_prompt_without_an_assertion_returns_an_empty_assertion(self):
        text, assertion = split_mbpp_prompt('"""\nJust a statement.\n"""\n')
        self.assertEqual(text, "Just a statement.")
        self.assertEqual(assertion, "")

    def test_rendered_mbpp_prompt_uses_the_docstring_assertion(self):
        record = {"prompt": self.REAL, "entry_point": "similar_elements"}
        rendered, text, assertion = suites.render_prompt("mbpp", record)
        self.assertIn("Write a Python function named `similar_elements`", rendered)
        self.assertIn("Example test: assert set(similar_elements", rendered)
        self.assertTrue(rendered.startswith(text))
        self.assertTrue(rendered.endswith(assertion))
        self.assertNotIn('"""', rendered)


class RealDatasetCase(unittest.TestCase):
    """Only runs when the pinned datasets are already in the out-of-repo cache."""

    def setUp(self):
        for name in ("humaneval-plus", "mbpp-plus"):
            if not suites.dataset_path(name).exists():
                self.skipTest("pinned datasets not downloaded; run prepare.py")

    def test_pinned_checksums_and_counts_hold(self):
        for name, tasks in (("humaneval-plus", 164), ("mbpp-plus", 378)):
            entry = suites.entry_for(name)
            with self.subTest(suite=name):
                self.assertEqual(suites.sha256_file(suites.dataset_path(name)), entry["sha256"])
                parsed = suites.build_tasks(name)
                self.assertEqual(len(parsed), tasks)
                self.assertEqual(sum(len(task.base_input) for task in parsed),
                                 entry["baseInputs"])
                self.assertEqual(sum(len(task.plus_input) for task in parsed),
                                 entry["plusInputs"])

    def test_every_mbpp_prompt_yields_exactly_one_assertion(self):
        for task in suites.build_tasks("mbpp-plus"):
            with self.subTest(task=task.task_id):
                self.assertTrue(task.assertion.startswith("assert"), task.assertion)
                self.assertNotIn("assert", task.text)


if __name__ == "__main__":
    unittest.main()
