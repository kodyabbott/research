"""The five Java sandbox self-tests, plus the java9plus fixture capture and its patterns."""

import json
import os
import sys
import unittest
from pathlib import Path

import context  # noqa: F401

from harness import java_grader, java_sandbox
from harness.sandbox import JAVA_PROFILE_TEMPLATE, PROFILE_TEMPLATE_SHA256, SANDBOX_EXEC

MAC = sys.platform == "darwin" and os.path.exists(SANDBOX_EXEC)
JAVA_READY = MAC and java_sandbox.available()
HINT = "no prepared JDK; run: python3 coding-benchmark-harness/prepare.py --jdk"
FIXTURES = Path(context.FIXTURES) / "java9plus"


class ProfileCase(unittest.TestCase):
    def test_java_profile_is_deny_default_with_network_denied(self):
        self.assertTrue(JAVA_PROFILE_TEMPLATE.startswith("(version 1)\n(deny default)"))
        self.assertIn("(deny network*)", JAVA_PROFILE_TEMPLATE)

    def test_java_profile_writes_only_to_the_work_directory(self):
        writes = [line for line in JAVA_PROFILE_TEMPLATE.splitlines()
                  if "file-write" in line]
        self.assertEqual(len(writes), 2)
        self.assertIn('(allow file-write* (subpath "@WORKDIR@")', JAVA_PROFILE_TEMPLATE)
        # /dev/null is the only write target outside WORKDIR, and data only.
        self.assertIn('(allow file-write-data (literal "/dev/null"))', JAVA_PROFILE_TEMPLATE)

    def test_home_deny_precedes_the_jdk_and_workdir_allows(self):
        # Later rules win, so the JDK (which lives under $HOME) must be re-allowed after the deny.
        deny = JAVA_PROFILE_TEMPLATE.index('(deny file-read* (subpath "@HOME@")')
        java_home = JAVA_PROFILE_TEMPLATE.index('(allow file-read* (subpath "@JAVA_HOME@")')
        workdir = JAVA_PROFILE_TEMPLATE.index('(allow file-read* (subpath "@WORKDIR@")')
        self.assertLess(deny, java_home)
        self.assertLess(deny, workdir)

    def test_ancestor_rule_is_metadata_only(self):
        # Ancestors of JAVA_HOME/WORKDIR are stat-able, never readable: no directory listings and
        # no file contents anywhere else under $HOME.
        self.assertIn("(allow file-read-metadata @ANCESTORS@)", JAVA_PROFILE_TEMPLATE)
        self.assertNotIn("file-read* @ANCESTORS@", JAVA_PROFILE_TEMPLATE)

    def test_adding_java_did_not_move_the_python_profile_hash(self):
        # The Python suites' expected-output files embed this hash; it must stay put.
        self.assertEqual(
            PROFILE_TEMPLATE_SHA256,
            "130725dd62edac6f75294223a380fc8eb63c43c4611968bffa85b43135a3bdcc")


@unittest.skipUnless(JAVA_READY, HINT)
class JavaSelfTestCase(unittest.TestCase):
    """DESIGN-JAVA.md's five required Java self-tests, run against the real profile and JDK."""

    @classmethod
    def setUpClass(cls):
        cls.box = java_sandbox.load()
        cls.report = cls.box.self_test()
        cls.by_name = {check["name"]: check for check in cls.report["checks"]}

    def test_all_five_pass(self):
        self.assertTrue(self.report["passed"], json.dumps(self.report, indent=1)[:4000])
        self.assertEqual(len(self.report["checks"]), 5)

    def test_hello_world_compiles_and_runs(self):
        self.assertTrue(self.by_name["java-hello-world-compiles-and-runs"]["passed"])

    def test_network_denied(self):
        check = self.by_name["java-network-denied"]
        self.assertTrue(check["passed"])
        # Non-vacuous: a real listener was up and accepted nothing.
        self.assertFalse(check["listenerAccepted"])
        self.assertIn("BLOCKED", check["output"])
        self.assertNotIn("CONNECTED", check["output"])

    def test_write_to_home_denied(self):
        check = self.by_name["java-write-outside-workdir-denied"]
        self.assertTrue(check["passed"])
        self.assertFalse(check["fileCreated"])
        self.assertIn("BLOCKED", check["output"])

    def test_infinite_loop_killed(self):
        check = self.by_name["java-infinite-loop-killed"]
        self.assertTrue(check["passed"])
        self.assertIn(check["runStatus"], ("timeout", "cpu-timeout"))

    def test_list_of_rejected_on_jdk8(self):
        check = self.by_name["java9plus-rejected-on-jdk8"]
        self.assertTrue(check["passed"])
        self.assertFalse(check["compileOk"])
        self.assertIn("cannot find symbol", check["diagnostics"])


@unittest.skipUnless(JAVA_READY, HINT)
class JavaExecutionCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.box = java_sandbox.load()

    def test_compile_errors_carry_the_file_they_are_in(self):
        sources = {
            "Solution.java": "class Solution { static int f() { return 1 } }\n",
            "Main.java": "public class Main { public static void main(String[] a) {} }\n",
        }
        compiled, ran = self.box.compile_and_run(sources)
        self.assertFalse(compiled.ok)
        self.assertIsNone(ran)
        self.assertEqual(compiled.files_with_errors, ["Solution.java"])
        self.assertGreaterEqual(compiled.error_count, 1)

    def test_errors_only_in_main_are_signature_mismatch(self):
        sources = {
            "Solution.java": "class Solution { static int f() { return 1; } }\n",
            "Main.java": ("public class Main { public static void main(String[] a) {"
                          " Solution.wrongName(); } }\n"),
        }
        compiled, _ran = self.box.compile_and_run(sources)
        self.assertFalse(compiled.ok)
        self.assertEqual(compiled.files_with_errors, ["Main.java"])
        outcome = java_grader.classify_compile_failure(compiled)
        self.assertEqual(outcome.failure_class, "signature-mismatch")

    def test_assertions_are_enabled(self):
        sources = {"Main.java": ("public class Main { public static void main(String[] a) {"
                                 " assert false : \"boom\"; } }\n")}
        compiled, ran = self.box.compile_and_run(sources)
        self.assertTrue(compiled.ok)
        self.assertNotEqual(ran.exit_code, 0)
        self.assertIn("AssertionError", ran.stderr_tail)

    def test_workdir_is_writable_and_tmpdir_points_at_it(self):
        sources = {"Main.java": (
            "import java.io.*;\n"
            "public class Main { public static void main(String[] a) throws Exception {\n"
            "  File f = new File(System.getProperty(\"java.io.tmpdir\"), \"probe.txt\");\n"
            "  FileWriter w = new FileWriter(f); w.write(\"ok\"); w.close();\n"
            "  System.out.println(\"WROTE \" + f.exists());\n"
            "} }\n")}
        compiled, ran = self.box.compile_and_run(sources)
        self.assertTrue(compiled.ok)
        self.assertEqual(ran.exit_code, 0)
        self.assertIn("WROTE true", ran.stdout_tail)

    def test_subprocess_spawning_is_denied(self):
        sources = {"Main.java": (
            "public class Main { public static void main(String[] a) {\n"
            "  try { Runtime.getRuntime().exec(\"/bin/echo hi\");"
            " System.out.println(\"SPAWNED\"); }\n"
            "  catch (Throwable t) { System.out.println(\"BLOCKED \""
            " + t.getClass().getName()); }\n"
            "} }\n")}
        compiled, ran = self.box.compile_and_run(sources)
        self.assertTrue(compiled.ok)
        self.assertNotIn("SPAWNED", ran.stdout_tail)
        self.assertIn("BLOCKED", ran.stdout_tail)


class Java9PlusPatternCase(unittest.TestCase):
    """The pattern list is derived from the checked-in JDK 8 diagnostics, not guessed."""

    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((FIXTURES / "index.json").read_text(encoding="utf-8"))

    def test_fixtures_were_captured_on_a_java_8_toolchain(self):
        self.assertEqual(self.index["toolchain"]["mode"], "jdk8")
        self.assertTrue(self.index["toolchain"]["version"].startswith("8."))

    def test_every_java9plus_fixture_failed_to_compile_on_jdk8(self):
        for name, info in self.index["cases"].items():
            if info["isJava9Plus"]:
                with self.subTest(case=name):
                    self.assertFalse(info["compiled"],
                                     f"{name} compiled on JDK 8; it is not a Java 9+ marker")

    def test_each_fixture_is_detected_exactly_when_it_should_be(self):
        for name, info in sorted(self.index["cases"].items()):
            diagnostics = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
            hits = java_grader.detect_java9plus(diagnostics)
            with self.subTest(case=name):
                self.assertEqual(bool(hits), info["isJava9Plus"],
                                 f"{name}: detected {[h['name'] for h in hits]}")

    def test_controls_are_plain_compile_errors_not_java9plus(self):
        # An ordinary typo, a missing import and a type error must not be misread as a Java 9+
        # leak: the first diagnostic line of a typo is also `cannot find symbol`.
        for name in ("control-typo", "control-missing-import", "control-type-mismatch"):
            diagnostics = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
            with self.subTest(case=name):
                self.assertEqual(java_grader.detect_java9plus(diagnostics), [])

    def test_every_pattern_is_backed_by_a_fixture_that_triggers_it(self):
        triggered = set()
        for name in self.index["cases"]:
            diagnostics = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
            for hit in java_grader.detect_java9plus(diagnostics):
                triggered.add(hit["name"])
        for pattern in java_grader.JAVA9PLUS_PATTERNS:
            with self.subTest(pattern=pattern.name):
                self.assertIn(pattern.name, triggered)
                self.assertTrue((FIXTURES / pattern.fixture).exists(), pattern.fixture)

    def test_pattern_coverage_includes_every_feature_the_design_names(self):
        names = {pattern.name for pattern in java_grader.JAVA9PLUS_PATTERNS}
        for required in ("var", "record", "text-block", "switch-expression", "list-of", "map-of",
                         "set-of", "string-isblank", "stream-tolist", "optional-isempty",
                         "string-strip", "string-repeat"):
            self.assertIn(required, names)


if __name__ == "__main__":
    unittest.main()
