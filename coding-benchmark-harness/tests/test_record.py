"""Run record: atomic save, overwrite refusal, resume with matching and mismatching digests,
host snapshot hygiene, and summary arithmetic."""

import json
import tempfile
import unittest
from pathlib import Path

import context  # noqa: F401

from harness import record
from harness.record import RecordError, RunRecord, host_snapshot, median_or_none

PROTOCOL = {
    "suite": "fixture", "suiteDigest": "a" * 64, "datasetSha256": "b" * 64,
    "promptTemplateSha256": "c" * 64, "think": "false",
    "options": {"temperature": 0, "num_ctx": 16384}, "outputCap": 4096, "context": 16384,
    "samplingProfile": "greedy-v1",
}
RUNTIME = {"backend": "replay", "sandboxProfileSha256": "d" * 64, "sandboxSelfTest":
           {"passed": True}}
MODEL = {"name": "replay", "digest": "sha256:e"}


def task(task_id, base=True, plus=True, failure="none", tok=10.0, wall=100.0, tokens=50,
         thinking="", truncated=False, unexpected=False):
    return {
        "id": task_id,
        "response": {"genTokPerSec": tok, "eval_count": tokens, "thinking": thinking},
        "wallMs": wall,
        "base": {"passed": base},
        "plus": {"passed": plus},
        "failureClass": failure,
        "truncated": truncated,
        "unexpectedThinking": unexpected,
    }


class RecordCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "20260930-test.json"

    def tearDown(self):
        self.temporary.cleanup()

    def new(self, **kwargs):
        return RunRecord(self.path, "test", dict(PROTOCOL), dict(RUNTIME), dict(MODEL), **kwargs)

    def test_save_is_atomic_and_leaves_no_temp_file(self):
        run = self.new()
        run.add_task(task("A/0"))
        self.assertTrue(self.path.exists())
        self.assertFalse(self.path.with_suffix(".tmp").exists())
        payload = json.loads(self.path.read_text())
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(len(payload["tasks"]), 1)
        self.assertEqual(payload["status"], "running")

    def test_save_after_every_task(self):
        run = self.new()
        for index in range(3):
            run.add_task(task(f"A/{index}"))
            self.assertEqual(len(json.loads(self.path.read_text())["tasks"]), index + 1)

    def test_refuses_to_overwrite_an_existing_run(self):
        self.new().save()
        with self.assertRaises(RecordError) as caught:
            self.new()
        self.assertIn("refusing to overwrite", str(caught.exception))

    def test_resume_keeps_completed_tasks(self):
        first = self.new()
        first.add_task(task("A/0"))
        first.add_task(task("A/1"))
        resumed = self.new(resume=True)
        self.assertEqual(resumed.completed_ids, {"A/0", "A/1"})
        self.assertEqual(resumed.data["status"], "running")
        self.assertEqual(len(resumed.data["resumedAt"]), 1)
        resumed.add_task(task("A/2"))
        self.assertEqual(len(json.loads(self.path.read_text())["tasks"]), 3)

    def test_resume_on_a_missing_file_starts_fresh(self):
        resumed = self.new(resume=True)
        self.assertEqual(resumed.completed_ids, set())

    def test_resume_refuses_a_different_suite_digest(self):
        self.new().add_task(task("A/0"))
        changed = dict(PROTOCOL, suiteDigest="f" * 64)
        with self.assertRaises(RecordError) as caught:
            RunRecord(self.path, "test", changed, dict(RUNTIME), dict(MODEL), resume=True)
        self.assertIn("suiteDigest", str(caught.exception))

    def test_resume_refuses_every_protocol_field_it_pins(self):
        self.new().add_task(task("A/0"))
        for key, value in (("suite", "mbpp-plus"), ("datasetSha256", "0" * 64),
                           ("promptTemplateSha256", "0" * 64), ("think", "high"),
                           ("options", {"temperature": 1}), ("outputCap", 8192),
                           ("context", 32768), ("samplingProfile", "other")):
            with self.subTest(key=key), self.assertRaises(RecordError) as caught:
                RunRecord(self.path, "test", dict(PROTOCOL, **{key: value}), dict(RUNTIME),
                          dict(MODEL), resume=True)
            self.assertIn(key, str(caught.exception))

    def test_resume_refuses_a_different_model_digest_or_name(self):
        self.new().add_task(task("A/0"))
        for field, value in (("digest", "sha256:other"), ("name", "another-model")):
            with self.subTest(field=field), self.assertRaises(RecordError) as caught:
                RunRecord(self.path, "test", dict(PROTOCOL), dict(RUNTIME),
                          dict(MODEL, **{field: value}), resume=True)
            self.assertIn(f"model.{field}", str(caught.exception))

    def test_resume_refuses_a_different_sandbox_profile(self):
        self.new().add_task(task("A/0"))
        with self.assertRaises(RecordError) as caught:
            RunRecord(self.path, "test", dict(PROTOCOL),
                      dict(RUNTIME, sandboxProfileSha256="0" * 64), dict(MODEL), resume=True)
        self.assertIn("sandboxProfileSha256", str(caught.exception))

    def test_resume_refuses_a_different_schema_version(self):
        run = self.new()
        run.data["schemaVersion"] = 99
        run.save()
        with self.assertRaises(RecordError):
            self.new(resume=True)

    def test_finish_records_the_end_state(self):
        run = self.new()
        run.add_task(task("A/0"))
        run.finish("completed")
        payload = json.loads(self.path.read_text())
        self.assertEqual(payload["status"], "completed")
        self.assertIsNotNone(payload["finishedAt"])
        self.assertIn("hostAfter", payload)

    def test_error_is_truncated_and_stored(self):
        run = self.new()
        run.set_status("error", "x" * 5000)
        self.assertEqual(len(run.data["error"]), 2000)


class SummaryCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "run.json"

    def tearDown(self):
        self.temporary.cleanup()

    def run_with(self, tasks, status="completed"):
        run = RunRecord(self.path, "test", dict(PROTOCOL), dict(RUNTIME), dict(MODEL))
        for entry in tasks:
            run.data["tasks"].append(entry)
        run.data["status"] = status
        return run

    def test_pass_at_1_requires_both_base_and_plus(self):
        run = self.run_with([
            task("A/0", base=True, plus=True),
            task("A/1", base=True, plus=False, failure="wrong-answer"),
            task("A/2", base=False, plus=False, failure="syntax-error"),
            # plus passing while base fails must not count as a pass.
            task("A/3", base=False, plus=True, failure="wrong-answer"),
        ])
        summary = run.summarize(4)
        self.assertEqual(summary["basePass"], 2)
        self.assertEqual(summary["plusPass"], 1)
        self.assertEqual(summary["passAt1"], 0.25)
        self.assertEqual(summary["basePassAt1"], 0.5)

    def test_pass_at_1_denominator_is_the_whole_task_list(self):
        run = self.run_with([task("A/0")], status="incomplete")
        summary = run.summarize(10)
        self.assertEqual(summary["tasksAttempted"], 1)
        self.assertEqual(summary["tasksTotal"], 10)
        self.assertEqual(summary["passAt1"], 0.1)

    def test_failure_class_counts(self):
        run = self.run_with([task("A/0"), task("A/1", failure="timeout"),
                             task("A/2", failure="timeout")])
        self.assertEqual(run.summarize(3)["failureClasses"], {"none": 1, "timeout": 2})

    def test_medians(self):
        run = self.run_with([task("A/0", tok=10, wall=100, tokens=10, thinking="ab"),
                             task("A/1", tok=20, wall=200, tokens=20, thinking="abcd"),
                             task("A/2", tok=30, wall=300, tokens=30, thinking="abcdef")])
        summary = run.summarize(3)
        self.assertEqual(summary["medianGenTokPerSec"], 20)
        self.assertEqual(summary["medianWallMs"], 200)
        self.assertEqual(summary["medianGeneratedTokens"], 20)
        self.assertEqual(summary["medianThinkingChars"], 4)

    def test_medians_tolerate_missing_server_timings(self):
        run = self.run_with([task("A/0", tok=None), task("A/1", tok=None)])
        self.assertIsNone(run.summarize(2)["medianGenTokPerSec"])
        self.assertIsNone(median_or_none([None, "x"]))

    def test_protocol_valid_requires_completion_full_coverage_and_no_thinking_leak(self):
        good = self.run_with([task("A/0")])
        self.assertTrue(good.summarize(1)["protocolValid"])
        partial = self.run_with([task("A/0")])
        self.assertFalse(partial.summarize(2)["protocolValid"])
        leaked = self.run_with([task("A/0", unexpected=True)])
        self.assertFalse(leaked.summarize(1)["protocolValid"])
        failed_run = self.run_with([task("A/0")], status="error")
        self.assertFalse(failed_run.summarize(1)["protocolValid"])

    def test_protocol_valid_requires_a_passing_sandbox_self_test(self):
        run = RunRecord(self.path, "test", dict(PROTOCOL),
                        dict(RUNTIME, sandboxSelfTest={"passed": False}), dict(MODEL))
        run.data["tasks"].append(task("A/0"))
        run.data["status"] = "completed"
        self.assertFalse(run.summarize(1)["protocolValid"])

    def test_truncated_and_thinking_counts(self):
        run = self.run_with([task("A/0", truncated=True, failure="truncated"),
                             task("A/1", unexpected=True)])
        summary = run.summarize(2)
        self.assertEqual(summary["truncated"], 1)
        self.assertEqual(summary["unexpectedThinking"], 1)


class HostSnapshotCase(unittest.TestCase):
    def test_no_identifiers_are_recorded(self):
        snapshot = host_snapshot()
        blob = json.dumps(snapshot).lower()
        for banned in ("serial_number", "hardware_uuid", "provisioning", "udid"):
            self.assertNotIn(banned, blob)
        for key in snapshot:
            for banned in record.FORBIDDEN_KEYS:
                self.assertNotIn(banned, key.lower())
        self.assertIn("identifiersOmitted", snapshot)

    def test_expected_fields_are_present(self):
        snapshot = host_snapshot()
        for key in ("capturedAt", "chip", "cpu_cores", "memory_gb", "os_version",
                    "power_source", "caveat"):
            self.assertIn(key, snapshot)


if __name__ == "__main__":
    unittest.main()
