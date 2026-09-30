"""Sandbox tests: the five required self-tests plus runner behaviour and encoding round trips.

Skipped with a clear message when not on macOS or when sandbox-exec is missing.
"""

import json
import os
import sys
import unittest

import context  # noqa: F401  (sys.path setup)

from harness import values
from harness.sandbox import SANDBOX_EXEC, SandboxExec, SandboxUnavailable, runner_source

MAC = sys.platform == "darwin" and os.path.exists(SANDBOX_EXEC)
REASON = f"requires macOS with {SANDBOX_EXEC}; this harness has no unsandboxed fallback"


@unittest.skipUnless(MAC, REASON)
class SelfTestCase(unittest.TestCase):
    """DESIGN.md's five required sandbox self-tests, run against the real profile."""

    @classmethod
    def setUpClass(cls):
        cls.sandbox = SandboxExec()
        cls.report = cls.sandbox.self_test()
        cls.by_name = {check["name"]: check for check in cls.report["checks"]}

    def test_all_self_tests_pass(self):
        self.assertTrue(self.report["passed"], json.dumps(self.report, indent=1)[:4000])
        self.assertEqual(len(self.report["checks"]), 5)

    def test_normal_program_returns_json(self):
        self.assertTrue(self.by_name["normal-program-returns-json"]["passed"])

    def test_network_denied(self):
        check = self.by_name["network-denied"]
        self.assertTrue(check["passed"])
        # Not vacuous: a real listener was running and refused nothing; the connect got EPERM.
        self.assertEqual(check["probe"]["result"], "EPERM")
        self.assertEqual(check["probe"]["type"], "PermissionError")
        self.assertFalse(check["listenerAccepted"])

    def test_write_outside_workdir_denied(self):
        check = self.by_name["write-outside-workdir-denied"]
        self.assertTrue(check["passed"])
        self.assertEqual(check["probe"]["tmp"], "PermissionError:EPERM")
        self.assertEqual(check["probe"]["home"], "PermissionError:EPERM")
        self.assertFalse(check["filesCreated"])

    def test_read_home_and_repo_denied(self):
        check = self.by_name["read-home-and-repo-denied"]
        self.assertTrue(check["passed"])
        # Both probe targets exist, so EPERM cannot be confused with ENOENT.
        self.assertTrue(os.path.exists(check["repoProbePath"]))
        self.assertEqual(check["probe"]["repo"], "PermissionError:EPERM")
        self.assertEqual(check["probe"]["home"], "PermissionError:EPERM")

    def test_infinite_loop_killed(self):
        check = self.by_name["infinite-loop-killed"]
        self.assertTrue(check["passed"])
        self.assertIn(check["status"], ("timeout", "cpu-timeout"))


@unittest.skipUnless(MAC, REASON)
class RunnerCase(unittest.TestCase):
    """sandbox_runner.py behaviour, exercised through the real sandbox."""

    @classmethod
    def setUpClass(cls):
        cls.sandbox = SandboxExec()

    def run_job(self, job, **kwargs):
        result = self.sandbox.run_python(
            {"sandbox_runner.py": runner_source()}, argv=["sandbox_runner.py"],
            stdin_text=json.dumps(job), want=("meta.json", "results.jsonl"), **kwargs)
        meta = json.loads(result.files.get("meta.json") or "null")
        rows = [json.loads(line) for line in (result.files.get("results.jsonl") or "").splitlines()
                if line.strip()]
        return result, meta, rows

    def test_round_trip_of_every_encoded_type(self):
        code = (
            "def f(_):\n"
            "    return [1, 1.5, float('nan'), float('inf'), -0.0, True, False, None,\n"
            "            'text', b'\\x00\\xff', bytearray(b'ab'), 2 ** 80, 1 + 2j,\n"
            "            (1, (2, 3)), {1, 2}, frozenset({3}), {'k': [1, 2], 7: (8,)}]\n"
        )
        _result, meta, rows = self.run_job({"code": code, "entry_point": "f", "inputs": [[0]]})
        self.assertEqual(meta["stage"], "done")
        decoded = values.decode(rows[0]["value"])
        self.assertEqual(decoded[0], 1)
        self.assertEqual(decoded[1], 1.5)
        self.assertNotEqual(decoded[2], decoded[2])  # NaN
        self.assertEqual(decoded[3], float("inf"))
        self.assertIs(type(decoded[5]), bool)
        self.assertIsNone(decoded[7])
        self.assertEqual(decoded[9], b"\x00\xff")
        self.assertEqual(decoded[11], 2 ** 80)
        self.assertEqual(decoded[12], 1 + 2j)
        self.assertEqual(decoded[13], (1, (2, 3)))
        self.assertIs(type(decoded[13]), tuple)
        self.assertEqual(decoded[14], {1, 2})
        self.assertEqual(decoded[16], {"k": [1, 2], 7: (8,)})

    def test_tuple_and_list_stay_distinct(self):
        code = "def f(n):\n    return (1, 2) if n else [1, 2]\n"
        _result, _meta, rows = self.run_job(
            {"code": code, "entry_point": "f", "inputs": [[1], [0]]})
        first, second = values.decode(rows[0]["value"]), values.decode(rows[1]["value"])
        self.assertIs(type(first), tuple)
        self.assertIs(type(second), list)
        self.assertNotEqual(first, second)

    def test_syntax_error_is_reported_without_running(self):
        _result, meta, rows = self.run_job(
            {"code": "def f(:\n    pass", "entry_point": "f", "inputs": [[1]]})
        self.assertEqual(meta["stage"], "syntax-error")
        self.assertIn("SyntaxError", meta["error"])
        self.assertEqual(rows, [])

    def test_missing_entry_point(self):
        _result, meta, _rows = self.run_job(
            {"code": "def other():\n    return 1\n", "entry_point": "f", "inputs": [[1]]})
        self.assertEqual(meta["stage"], "missing-entry-point")
        self.assertIn("other", meta["defined"])

    def test_module_level_exception(self):
        _result, meta, _rows = self.run_job(
            {"code": "raise RuntimeError('at import')\n", "entry_point": "f", "inputs": [[1]]})
        self.assertEqual(meta["stage"], "exec-error")
        self.assertIn("RuntimeError", meta["error"])

    def test_per_input_timeout_and_exception_and_stray_print(self):
        code = (
            "def f(n):\n"
            "    print('stray output that would corrupt stdout', n)\n"
            "    if n == 0:\n"
            "        while True:\n"
            "            pass\n"
            "    if n == 1:\n"
            "        raise ValueError('boom')\n"
            "    return n * 2\n"
        )
        _result, meta, rows = self.run_job(
            {"code": code, "entry_point": "f", "inputs": [[0], [1], [2]],
             "per_input_seconds": [0.3, 1.0, 1.0]})
        self.assertEqual(meta["stage"], "done")
        self.assertEqual([row["status"] for row in rows], ["timeout", "exception", "ok"])
        self.assertIn("ValueError", rows[1]["error"])
        self.assertEqual(values.decode(rows[2]["value"]), 4)

    def test_inputs_are_deep_copied_between_calls(self):
        code = "def f(xs):\n    xs.append(99)\n    return sum(xs)\n"
        _result, _meta, rows = self.run_job(
            {"code": code, "entry_point": "f", "inputs": [[[1, 2]], [[1, 2]]]})
        self.assertEqual([values.decode(row["value"]) for row in rows], [102, 102])

    def test_mbpp_inputs_are_deserialized_to_tuples(self):
        code = ("def similar_elements(a, b):\n"
                "    return (type(a).__name__, type(b).__name__)\n")
        _result, _meta, rows = self.run_job(
            {"code": code, "entry_point": "similar_elements", "task_id": "Mbpp/2",
             "deserialize": "mbpp", "inputs": [[[3, 4], [5, 4]]]})
        self.assertEqual(values.decode(rows[0]["value"]), ("tuple", "tuple"))

    def test_not_none_modes(self):
        code = "import re\ndef check_str(s):\n    return re.match(r'[aeiou]', s)\n"
        for mode in ("trusted", "candidate"):
            _result, _meta, rows = self.run_job(
                {"code": code, "entry_point": "check_str", "inputs": [["apple"], ["zebra"]],
                 "not_none_mode": mode})
            self.assertEqual([values.decode(row["value"]) for row in rows], [True, False], mode)

    def test_candidate_not_none_mode_keeps_real_booleans(self):
        code = "def check_str(s):\n    return s.startswith('a')\n"
        _result, _meta, rows = self.run_job(
            {"code": code, "entry_point": "check_str", "inputs": [["apple"], ["zebra"]],
             "not_none_mode": "candidate"})
        self.assertEqual([values.decode(row["value"]) for row in rows], [True, False])

    def test_cpu_limit_kills_and_leaves_partial_results(self):
        code = ("def f(n):\n"
                "    import time\n"
                "    start = time.perf_counter()\n"
                "    while time.perf_counter() - start < 0.4:\n"
                "        pass\n"
                "    return n\n")
        result, meta, rows = self.run_job(
            {"code": code, "entry_point": "f", "inputs": [[i] for i in range(40)],
             "per_input_seconds": 10.0}, cpu_seconds=2, timeout=25)
        self.assertTrue(result.timed_out, result.status)
        self.assertEqual(meta["stage"], "started")
        self.assertGreater(len(rows), 0)
        self.assertLess(len(rows), 40)

    def test_subprocess_spawning_is_denied(self):
        code = ("def f(_):\n"
                "    import subprocess\n"
                "    try:\n"
                "        subprocess.run(['/bin/echo', 'hi'], capture_output=True)\n"
                "        return 'SPAWNED'\n"
                "    except OSError as exc:\n"
                "        return type(exc).__name__\n")
        _result, _meta, rows = self.run_job({"code": code, "entry_point": "f", "inputs": [[0]]})
        self.assertEqual(values.decode(rows[0]["value"]), "PermissionError")

    def test_profile_records_home_deny_before_workdir_allow(self):
        text = self.sandbox.profile_text("/tmp/example-workdir")
        self.assertIn("(deny default)", text)
        self.assertIn("(deny network*)", text)
        deny_home = text.index(f'(deny file-read* (subpath "{self.sandbox.home}"')
        allow_work = text.index('(allow file-read* (subpath "/private/tmp/example-workdir"')
        self.assertLess(deny_home, allow_work, "later rules win; WORKDIR allow must come last")


class EncodingCase(unittest.TestCase):
    """Encoder properties that do not need the sandbox: digest identity and order insensitivity."""

    def digests(self, obj):
        import hashlib
        from harness import sandbox_runner
        materialized = hashlib.sha256(
            sandbox_runner._dumps(sandbox_runner.encode(obj)).encode()).hexdigest()
        streamed = hashlib.sha256(
            "".join(sandbox_runner.canonical_chunks(obj)).encode()).hexdigest()
        return materialized, streamed

    def test_streaming_and_materialized_digests_are_byte_identical(self):
        for obj in (list(range(20000)),
                    [[index, float(index), str(index)] for index in range(4000)],
                    [(index, {"k": [index]}) for index in range(3000)],
                    [{1, 2, 3}] * 3000,
                    [{"a": 1, "b": 2}] * 3000,
                    ["x" * 100] * 2000):
            with self.subTest(kind=type(obj[0]).__name__):
                materialized, streamed = self.digests(obj)
                self.assertEqual(materialized, streamed)

    def test_oversized_values_report_a_matching_digest(self):
        from harness import sandbox_runner
        obj = list(range(20000))
        tagged = sandbox_runner.encode_or_digest(obj)
        self.assertEqual(tagged["t"], "digest")
        self.assertEqual(tagged["v"], self.digests(obj)[0])
        self.assertGreater(tagged["bytes"], sandbox_runner.MAX_VALUE_BYTES)

    def test_small_values_are_not_digested(self):
        from harness import sandbox_runner
        self.assertEqual(sandbox_runner.encode_or_digest([1, 2, 3])["t"], "list")
        self.assertEqual(sandbox_runner.encode_or_digest("x")["t"], "str")

    def test_set_and_dict_encodings_ignore_insertion_order(self):
        from harness import sandbox_runner
        left, right = set(), set()
        for value in (5, 1, 9, 3, 7):
            left.add(value)
        for value in (9, 7, 3, 5, 1):
            right.add(value)
        self.assertEqual(sandbox_runner._dumps(sandbox_runner.encode(left)),
                         sandbox_runner._dumps(sandbox_runner.encode(right)))
        self.assertEqual(sandbox_runner._dumps(sandbox_runner.encode({"z": 1, "a": 2})),
                         sandbox_runner._dumps(sandbox_runner.encode({"a": 2, "z": 1})))

    def test_large_equal_sets_digest_identically(self):
        from harness import sandbox_runner
        left = sandbox_runner.encode_or_digest(set(range(3000)))
        right = sandbox_runner.encode_or_digest(set(range(2999, -1, -1)))
        self.assertEqual(left["t"], "digest")
        self.assertEqual(left, right)

    def test_digest_comparison_is_available_to_the_grader(self):
        from harness import sandbox_runner
        tagged = sandbox_runner.encode_or_digest(list(range(20000)))
        self.assertTrue(values.is_digest(tagged))
        self.assertEqual(values.digest_of(tagged), tagged["v"])
        # digest_of over a whole tagged value reproduces the same hash
        small = sandbox_runner.encode([1, 2, 3])
        self.assertEqual(len(values.digest_of(small)), 64)
        self.assertIsInstance(values.decode(tagged), values.Digest)

    def test_decoded_digests_compare_only_to_the_same_hash(self):
        left = values.decode({"t": "digest", "v": "a" * 64, "bytes": 10})
        same = values.decode({"t": "digest", "v": "a" * 64, "bytes": 99})
        other = values.decode({"t": "digest", "v": "b" * 64})
        self.assertEqual(left, same)
        self.assertNotEqual(left, other)
        self.assertNotEqual(left, [1, 2, 3])


class NonMacCase(unittest.TestCase):
    def test_refuses_without_sandbox_exec(self):
        if MAC:
            self.skipTest("sandbox-exec is present; the refusal path cannot be exercised here")
        with self.assertRaises(SandboxUnavailable):
            SandboxExec()


if __name__ == "__main__":
    unittest.main()
