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
    def test_registry_lists_the_python_and_java_suites(self):
        names = suites.suite_names()
        for expected in ("fixture", "humaneval-plus", "mbpp-plus"):
            self.assertIn(expected, names)
        registry = suites.registry()["suites"]
        python = sorted(name for name, entry in registry.items()
                        if entry.get("language", "python") == "python")
        java = sorted(name for name, entry in registry.items()
                      if entry.get("language") == "java")
        self.assertEqual(python, ["fixture", "humaneval-plus", "mbpp-plus"])
        self.assertTrue(java, "expected at least one Java suite")
        for name in java:
            self.assertIn(name, names)

    def test_every_registry_entry_declares_a_language_or_defaults_to_python(self):
        for name, entry in suites.registry()["suites"].items():
            with self.subTest(suite=name):
                self.assertIn(entry.get("language", "python"), ("python", "java"))

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


class JavaSuiteCase(unittest.TestCase):
    """HumanEval-X Java loader. Skips when the dataset has not been downloaded."""

    def setUp(self):
        if not suites.dataset_path("humaneval-x-java").exists():
            self.skipTest("run: python3 coding-benchmark-harness/prepare.py "
                          "--suite humaneval-x-java")

    def test_registry_pins_the_revision_and_checksum(self):
        entry = suites.entry_for("humaneval-x-java")
        self.assertEqual(entry["revision"], "62c78627f3072a1454fa0cb0184737cafe5e4198")
        self.assertEqual(entry["language"], "java")
        self.assertEqual(entry["asset"], "data/java/data/humaneval.jsonl")
        self.assertEqual(entry["tasks"], 164)
        self.assertIn("zai-org/humaneval-x", entry["url"])
        self.assertIn(entry["revision"], entry["url"])

    def test_dataset_matches_its_pinned_sha256(self):
        entry = suites.entry_for("humaneval-x-java")
        self.assertEqual(suites.sha256_file(suites.dataset_path("humaneval-x-java")),
                         entry["sha256"])

    def test_all_164_tasks_parse(self):
        tasks = suites.build_tasks("humaneval-x-java")
        self.assertEqual(len(tasks), 164)
        self.assertTrue(all(task.language == "java" for task in tasks))
        self.assertTrue(all(task.is_java for task in tasks))
        self.assertEqual(tasks[0].task_id, "Java/0")

    def test_dataset_fields_are_the_ones_the_design_expected(self):
        for record in suites.read_jsonl(suites.dataset_path("humaneval-x-java"))[:5]:
            for field_name in suites.JAVA_REQUIRED_FIELDS:
                self.assertIn(field_name, record)

    def test_prompt_states_the_java8_constraint_by_default(self):
        task = suites.build_tasks("humaneval-x-java")[0]
        self.assertIn("Target Java 8", task.prompt)
        self.assertIn("```java", task.prompt)
        self.assertIn("List.of/Map.of/Set.of", task.prompt)
        self.assertTrue(task.prompt.endswith(task.source_prompt))

    def test_no_java8_hint_variant_omits_the_constraint(self):
        task = suites.build_tasks("humaneval-x-java", java8_hint=False)[0]
        self.assertNotIn("Target Java 8", task.prompt)
        self.assertIn("```java", task.prompt)

    def test_canonical_is_prompt_plus_solution_with_no_extra_brace(self):
        # DESIGN-JAVA.md says `prompt + canonical_solution + "}"`, but canonical_solution already
        # closes the method and the class in every record; an extra brace would not parse.
        for task in suites.build_tasks("humaneval-x-java"):
            with self.subTest(task=task.task_id):
                program = task.canonical_java
                self.assertEqual(program.count("{"), program.count("}"))
                self.assertEqual(program, task.source_prompt + task.canonical_solution)

    def test_entry_points_are_parsed_for_every_task(self):
        tasks = suites.build_tasks("humaneval-x-java")
        by_id = {task.task_id: task.entry_point for task in tasks}
        self.assertEqual(by_id["Java/0"], "hasCloseElements")
        # Java/162 declares `throws NoSuchAlgorithmException`, which broke the first regex.
        self.assertEqual(by_id["Java/162"], "stringToMd5")
        # Java/84 and Java/161 genuinely have a method called `solve`.
        self.assertEqual(by_id["Java/84"], "solve")
        self.assertEqual(len(by_id), 164)
        self.assertTrue(all(name.isidentifier() for name in by_id.values()))
        # Java/153's method really is `StrongestExtension` in the dataset -- a capitalised method
        # name is unusual Java, but it is what the prompt declares, so the parser is right.
        self.assertEqual(by_id["Java/153"], "StrongestExtension")
        odd = sorted(task for task, name in by_id.items() if not name[0].islower())
        self.assertEqual(odd, ["Java/153"])

    def test_hidden_tests_get_the_scaffold_imports(self):
        """None of the 164 dataset `test` values carry imports, so Main cannot compile alone."""
        for record in suites.read_jsonl(suites.dataset_path("humaneval-x-java")):
            self.assertNotIn("\nimport ", "\n" + record["test"])
        task = suites.build_tasks("humaneval-x-java")[0]
        sources = task.java_sources("class Solution {}\n")
        self.assertEqual(sorted(sources), ["Main.java", "Solution.java"])
        self.assertTrue(sources["Main.java"].startswith("import java.util.*;"))
        self.assertIn("public class Main", sources["Main.java"])

    def test_import_block_is_taken_from_each_task(self):
        # 4 tasks add java.util.stream.Collectors and 1 adds BigInteger/security.
        blocks = {task.task_id: task.import_block
                  for task in suites.build_tasks("humaneval-x-java")}
        self.assertIn("import java.util.stream.Collectors;", "".join(blocks.values()))
        self.assertIn("import java.math.BigInteger;", blocks["Java/162"])

    def test_solution_and_tests_are_separate_files(self):
        task = suites.build_tasks("humaneval-x-java")[0]
        sources = task.java_sources("class Solution { }\n")
        self.assertEqual(sources["Solution.java"], "class Solution { }\n")
        self.assertNotIn("class Solution", sources["Main.java"])


class JavaPreparedSuiteCase(unittest.TestCase):
    def setUp(self):
        if not (suites.expected_dir("humaneval-x-java") / "_skipped.json").exists():
            self.skipTest("run: python3 coding-benchmark-harness/prepare.py "
                          "--suite humaneval-x-java")

    def test_loaded_suite_excludes_the_skipped_tasks(self):
        suite = suites.load("humaneval-x-java")
        self.assertEqual(suite.language, "java")
        self.assertEqual(suite.total_tasks, 164)
        self.assertEqual(len(suite.tasks) + len(suite.skipped), 164)
        self.assertGreater(len(suite.tasks), 0)
        for task in suite.tasks:
            self.assertNotIn(task.task_id, suite.skipped)

    def test_every_skip_has_a_diagnostic_reason(self):
        for task_id, reason in suites.load("humaneval-x-java").skipped.items():
            with self.subTest(task=task_id):
                self.assertTrue(reason.strip())
                self.assertIn(":", reason)

    def test_protocol_records_the_language_and_digest(self):
        protocol = suites.load("humaneval-x-java").protocol()
        self.assertEqual(protocol["language"], "java")
        self.assertEqual(protocol["tasksInSuite"], 164)
        self.assertEqual(len(protocol["suiteDigest"]), 64)

    def test_digest_is_stable(self):
        self.assertEqual(suites.load("humaneval-x-java").digest,
                         suites.load("humaneval-x-java").digest)


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
