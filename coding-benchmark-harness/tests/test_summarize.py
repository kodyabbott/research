"""Summarizer tests over synthetic and real fixture run records, plus run.py's CLI guards."""

import json
import tempfile
import unittest
from pathlib import Path

import context  # noqa: F401

import run as runner
import summarize
from harness import backends

FIXTURE_RUN = Path(context.ROOT) / "runs/20260929-replay-fixture.json"


def make_record(label, suite="fixture", digest="a" * 64, plus=2, base=2, total=3,
                status="completed", think="false", classes=None, valid=True):
    return {
        "schemaVersion": 1, "label": label, "status": status,
        "host": {"chip": "Apple"},
        "runtime": {"backend": "replay", "sandboxProfileSha256": "d" * 64,
                    "sandboxSelfTest": {"passed": True}},
        "model": {"name": label, "digest": "sha256:" + label},
        "protocol": {"suite": suite, "suiteDigest": digest, "datasetSha256": "b" * 64,
                     "promptTemplateSha256": "c" * 64, "think": think, "context": 16384,
                     "outputCap": 4096, "evalplusVersion": "v0.1.10"},
        "tasks": [],
        "summary": {"tasksTotal": total, "tasksAttempted": total, "basePass": base,
                    "plusPass": plus, "passAt1": round(plus / total, 4),
                    "basePassAt1": round(base / total, 4),
                    "failureClasses": classes or {"none": plus, "wrong-answer": total - plus},
                    "medianWallMs": 2000.0, "medianGenTokPerSec": 20.0,
                    "medianGeneratedTokens": 42, "medianThinkingChars": 0,
                    "truncated": 0, "unexpectedThinking": 0, "protocolValid": valid},
        "unload": {"confirmed": True},
    }


class SummarizeCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.dir = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, name, payload):
        path = self.dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_single_row(self):
        path = self.write("a.json", make_record("model-a"))
        payload, warnings = summarize.build([path])
        self.assertEqual(payload["runs"], 1)
        self.assertEqual(warnings, [])
        self.assertFalse(payload["mixedSuites"])
        row = payload["rows"][0]
        self.assertEqual(row["model"], "model-a")
        self.assertEqual(row["passAt1"], 0.6667)
        self.assertEqual(row["wrongAnswer"], 1)
        self.assertEqual(row["medianWallSeconds"], 2.0)

    def test_rows_sorted_by_suite_then_pass_at_1_descending(self):
        paths = [
            self.write("low.json", make_record("low", plus=1)),
            self.write("high.json", make_record("high", plus=3, base=3)),
            self.write("mbpp.json", make_record("mbpp-model", suite="mbpp-plus", plus=2)),
        ]
        payload, _warnings = summarize.build(paths)
        self.assertEqual([row["model"] for row in payload["rows"]],
                         ["high", "low", "mbpp-model"])

    def test_mixed_suite_digests_are_flagged_and_warned(self):
        paths = [self.write("a.json", make_record("a", digest="a" * 64)),
                 self.write("b.json", make_record("b", digest="f" * 64))]
        payload, warnings = summarize.build(paths)
        self.assertTrue(payload["mixedSuites"])
        self.assertTrue(any("NOT directly comparable" in warning for warning in warnings))
        self.assertEqual(len(payload["suiteDigests"]["fixture"]), 2)

    def test_matching_digests_are_not_flagged(self):
        paths = [self.write("a.json", make_record("a")), self.write("b.json", make_record("b"))]
        payload, _warnings = summarize.build(paths)
        self.assertFalse(payload["mixedSuites"])

    def test_incomplete_and_invalid_runs_are_warned_about(self):
        paths = [self.write("a.json", make_record("a", status="incomplete")),
                 self.write("b.json", make_record("b", valid=False))]
        _payload, warnings = summarize.build(paths)
        self.assertTrue(any("status is 'incomplete'" in warning for warning in warnings))
        self.assertTrue(any("protocolValid is false" in warning for warning in warnings))

    def test_failed_sandbox_self_test_is_warned_about(self):
        payload = make_record("a")
        payload["runtime"]["sandboxSelfTest"] = {"passed": False}
        _summary, warnings = summarize.build([self.write("a.json", payload)])
        self.assertTrue(any("sandbox self-test did not pass" in warning for warning in warnings))

    def test_unreadable_file_is_skipped_with_a_warning(self):
        bad = self.dir / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        payload, warnings = summarize.build([bad, self.write("a.json", make_record("a"))])
        self.assertEqual(payload["runs"], 1)
        self.assertTrue(any("skipping" in warning for warning in warnings))

    def test_markdown_table_shape(self):
        payload, _warnings = summarize.build([self.write("a.json", make_record("a"))])
        table = summarize.markdown_table(payload["rows"])
        lines = table.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].count("|"), len(summarize.COLUMNS) + 1)
        self.assertIn("2/3 (66.7%)", lines[2])

    def test_cli_writes_both_outputs(self):
        self.write("a.json", make_record("a"))
        markdown, comparison = self.dir / "R.md", self.dir / "c.json"
        code = summarize.main([str(self.dir / "a.json"), "--markdown", str(markdown),
                               "--json", str(comparison)])
        self.assertEqual(code, 0)
        self.assertIn("| model |", markdown.read_text())
        self.assertEqual(json.loads(comparison.read_text())["runs"], 1)

    def test_cli_with_no_readable_runs_fails(self):
        self.assertEqual(summarize.main([str(self.dir / "missing.json")]), 2)

    def test_mixed_suites_adds_a_warning_block_to_the_markdown(self):
        self.write("a.json", make_record("a", digest="a" * 64))
        self.write("b.json", make_record("b", digest="f" * 64))
        markdown = self.dir / "R.md"
        summarize.main([str(self.dir / "a.json"), str(self.dir / "b.json"),
                        "--markdown", str(markdown)])
        self.assertIn("[!WARNING]", markdown.read_text())


@unittest.skipUnless(FIXTURE_RUN.exists(), f"{FIXTURE_RUN.name} not present; run run.py --backend "
                                           f"replay --suite fixture first")
class FixtureRunCase(unittest.TestCase):
    """Summarizes the committed replay run, which is a real end-to-end record."""

    @classmethod
    def setUpClass(cls):
        cls.payload, cls.warnings = summarize.build([FIXTURE_RUN])
        cls.row = cls.payload["rows"][0]

    def test_no_warnings(self):
        self.assertEqual(self.warnings, [])
        self.assertFalse(self.payload["mixedSuites"])

    def test_row_reflects_the_recorded_outcome(self):
        self.assertEqual(self.row["suite"], "fixture")
        self.assertEqual(self.row["backend"], "replay")
        self.assertEqual(self.row["tasks"], 3)
        self.assertEqual(self.row["plusPass"], 2)
        self.assertEqual(self.row["wrongAnswer"], 1)
        self.assertTrue(self.row["protocolValid"])
        self.assertTrue(self.row["sandboxSelfTestPassed"])

    def test_record_carries_the_digests_needed_to_compare_runs(self):
        for key in ("suiteDigest", "datasetSha256", "promptTemplateSha256",
                    "sandboxProfileSha256", "modelDigest"):
            with self.subTest(key=key):
                self.assertIn(key, self.row)
        self.assertEqual(len(self.row["suiteDigest"]), 64)

    def test_markdown_renders(self):
        self.assertIn("2/3 (66.7%)", summarize.markdown_table(self.payload["rows"]))


class RunCliCase(unittest.TestCase):
    def test_output_cap_defaults_depend_on_thinking(self):
        self.assertEqual(runner.output_cap_for("false", None), 4096)
        self.assertEqual(runner.output_cap_for("true", None), 16384)
        self.assertEqual(runner.output_cap_for("high", None), 16384)
        self.assertEqual(runner.output_cap_for("false", 2048), 2048)

    def test_live_backends_require_an_endpoint_and_a_model(self):
        args = runner.argparse.Namespace(
            backend="ollama", endpoint=None, model=None, think="false", output_cap=None,
            context=16384, task_seconds=300.0, suite="fixture", replay_file=None)
        with self.assertRaises(SystemExit):
            runner.make_backend(args)
        args.endpoint = "http://127.0.0.1:11436"
        with self.assertRaises(SystemExit):
            runner.make_backend(args)

    def test_primary_ollama_port_is_refused_by_the_cli_path(self):
        args = runner.argparse.Namespace(
            backend="ollama", endpoint="http://127.0.0.1:11434", model="m", think="false",
            output_cap=None, context=16384, task_seconds=300.0, suite="fixture",
            replay_file=None)
        with self.assertRaises(backends.EndpointRefused):
            runner.make_backend(args)

    def test_replay_backend_needs_no_endpoint(self):
        args = runner.argparse.Namespace(
            backend="replay", endpoint=None, model=None, think="false", output_cap=None,
            context=16384, task_seconds=300.0, suite="fixture", replay_file=None)
        backend = runner.make_backend(args)
        self.assertEqual(backend.name, "replay")
        self.assertEqual(sorted(backend.responses), ["Fixture/0", "Fixture/1", "Fixture/2"])


if __name__ == "__main__":
    unittest.main()
