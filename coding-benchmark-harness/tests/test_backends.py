"""Backend tests. No network: `harness.backends._urlopen` is replaced by a fake for every call.

The live backends are fully implemented but were never pointed at a real server during
implementation (DESIGN.md revisions item 1: ports 11434 and 11436 were off limits). These tests are
what stands in for that, so they assert on the exact request bodies that would go over the wire.
"""

import json
import unittest
from unittest import mock

import context  # noqa: F401

from harness import backends
from harness.backends import BackendError, ChatResult, EndpointRefused, OllamaBackend, \
    OpenAIBackend, ReplayBackend, check_endpoint, think_field

ENDPOINT = "http://127.0.0.1:11436"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class FakeServer:
    """Records every request and answers from a per-path queue or callable."""

    def __init__(self, routes):
        self.routes = routes
        self.requests = []

    def __call__(self, request, timeout):
        path = request.full_url.split("127.0.0.1:11436", 1)[-1]
        body = json.loads(request.data) if request.data else None
        self.requests.append({"path": path, "body": body, "method": request.get_method(),
                              "timeout": timeout, "headers": dict(request.headers)})
        handler = self.routes.get(path)
        if handler is None:
            raise AssertionError(f"unexpected request to {path}")
        if callable(handler):
            return FakeResponse(handler(body))
        if isinstance(handler, list):
            return FakeResponse(handler.pop(0) if len(handler) > 1 else handler[0])
        return FakeResponse(handler)

    def bodies(self, path):
        return [item["body"] for item in self.requests if item["path"] == path]


def ollama_chat_response(content="```python\ndef f():\n    return 1\n```", **extra):
    payload = {
        "model": "test-model", "done": True, "done_reason": "stop",
        "message": {"role": "assistant", "content": content},
        "eval_count": 100, "eval_duration": 5_000_000_000,
        "prompt_eval_count": 40, "prompt_eval_duration": 200_000_000,
        "total_duration": 5_300_000_000, "load_duration": 1_000_000,
    }
    payload.update(extra)
    return payload


class EndpointCase(unittest.TestCase):
    def test_primary_port_is_refused(self):
        for endpoint in ("http://127.0.0.1:11434", "http://127.0.0.1:11434/",
                         "http://localhost:11434"):
            with self.subTest(endpoint=endpoint), self.assertRaises(EndpointRefused):
                check_endpoint(endpoint)

    def test_empty_endpoint_is_refused(self):
        with self.assertRaises(EndpointRefused):
            check_endpoint("")

    def test_dedicated_port_is_accepted_and_normalised(self):
        self.assertEqual(check_endpoint(ENDPOINT + "/"), ENDPOINT)
        self.assertEqual(backends.DEFAULT_ENDPOINT, ENDPOINT)

    def test_constructing_a_backend_on_the_primary_port_raises(self):
        with self.assertRaises(EndpointRefused):
            OllamaBackend("http://127.0.0.1:11434", "m")


class ThinkMappingCase(unittest.TestCase):
    """Mirrors bench.py: {'false': False, 'true': True}.get(mode, mode), omitted for 'default'."""

    def test_mapping(self):
        self.assertIs(think_field("false"), False)
        self.assertIs(think_field("true"), True)
        self.assertEqual(think_field("low"), "low")
        self.assertEqual(think_field("medium"), "medium")
        self.assertEqual(think_field("high"), "high")
        self.assertIsNone(think_field("default"))

    def test_unknown_mode_is_rejected_at_construction(self):
        with self.assertRaises(BackendError):
            OllamaBackend(ENDPOINT, "m", think="maybe")

    def test_default_omits_the_field_entirely(self):
        body = OllamaBackend(ENDPOINT, "m", think="default").build_body("hi")
        self.assertNotIn("think", body)

    def test_each_mode_appears_in_the_request_body(self):
        for mode, expected in (("false", False), ("true", True), ("low", "low"),
                               ("medium", "medium"), ("high", "high")):
            with self.subTest(mode=mode):
                body = OllamaBackend(ENDPOINT, "m", think=mode).build_body("hi")
                self.assertEqual(body["think"], expected)


class OllamaRequestCase(unittest.TestCase):
    def test_request_body_matches_the_protocol(self):
        backend = OllamaBackend(ENDPOINT, "qwen3.8:27b-q8_0", think="false",
                                output_cap=4096, context=16384)
        body = backend.build_body("Complete the function")
        self.assertEqual(body["model"], "qwen3.8:27b-q8_0")
        self.assertEqual(body["messages"],
                         [{"role": "user", "content": "Complete the function"}])
        self.assertIs(body["stream"], False)
        self.assertEqual(body["keep_alive"], "10m")
        self.assertIs(body["think"], False)
        self.assertEqual(body["options"], {
            "temperature": 0, "seed": 42, "top_p": 1, "top_k": 40, "repeat_penalty": 1.0,
            "num_ctx": 16384, "num_predict": 4096})

    def test_num_ctx_is_always_sent_explicitly(self):
        # The dedicated server runs with OLLAMA_CONTEXT_LENGTH=8192, so this cannot be implicit.
        for context in (8192, 16384, 32768):
            with self.subTest(context=context):
                body = OllamaBackend(ENDPOINT, "m", context=context).build_body("x")
                self.assertEqual(body["options"]["num_ctx"], context)

    def test_no_system_prompt_is_sent(self):
        body = OllamaBackend(ENDPOINT, "m").build_body("x")
        self.assertEqual([message["role"] for message in body["messages"]], ["user"])

    def test_chat_parses_timings_and_content(self):
        server = FakeServer({"/api/chat": ollama_chat_response()})
        with mock.patch.object(backends, "_urlopen", server):
            result = OllamaBackend(ENDPOINT, "m").chat("prompt", task_id="HumanEval/0")
        self.assertIn("def f()", result.content)
        self.assertEqual(result.done_reason, "stop")
        self.assertEqual(result.eval_count, 100)
        self.assertAlmostEqual(result.gen_tok_per_sec, 20.0)
        self.assertFalse(result.truncated)
        self.assertEqual(server.requests[0]["path"], "/api/chat")
        self.assertEqual(server.requests[0]["method"], "POST")

    def test_truncation_is_detected(self):
        server = FakeServer({"/api/chat": ollama_chat_response(done_reason="length")})
        with mock.patch.object(backends, "_urlopen", server):
            result = OllamaBackend(ENDPOINT, "m").chat("prompt")
        self.assertTrue(result.truncated)

    def test_thinking_text_is_captured_separately_from_content(self):
        payload = ollama_chat_response()
        payload["message"]["thinking"] = "let me think"
        server = FakeServer({"/api/chat": payload})
        with mock.patch.object(backends, "_urlopen", server):
            result = OllamaBackend(ENDPOINT, "m").chat("prompt")
        self.assertEqual(result.thinking, "let me think")
        self.assertNotIn("let me think", result.content)

    def test_incomplete_response_raises(self):
        server = FakeServer({"/api/chat": {"done": False, "message": {"content": ""}}})
        with mock.patch.object(backends, "_urlopen", server):
            with self.assertRaises(BackendError):
                OllamaBackend(ENDPOINT, "m").chat("prompt")

    def test_preflight_refuses_when_another_model_is_loaded(self):
        server = FakeServer({"/api/ps": {"models": [{"name": "other:70b"}]}})
        with mock.patch.object(backends, "_urlopen", server):
            with self.assertRaises(BackendError) as caught:
                OllamaBackend(ENDPOINT, "m").preflight()
        self.assertIn("already has", str(caught.exception))

    def test_preflight_collects_model_identity(self):
        server = FakeServer({
            "/api/ps": {"models": []},
            "/api/show": {"details": {"family": "qwen3"}, "capabilities": ["thinking"],
                          "parameters": "stop ...", "template": "{{ .Prompt }}",
                          "model_info": {"general.parameter_count": 27_000_000_000,
                                         "tokenizer.ggml.tokens": ["a", "b"]}},
            "/api/tags": {"models": [{"name": "m", "digest": "sha256:abc", "size": 123}]},
            "/api/version": {"version": "0.15.0"},
        })
        with mock.patch.object(backends, "_urlopen", server):
            info = OllamaBackend(ENDPOINT, "m").preflight()
        self.assertEqual(info["digest"], "sha256:abc")
        self.assertEqual(info["capabilities"], ["thinking"])
        self.assertEqual(len(info["templateSha256"]), 64)
        # Long list-valued model_info entries (the whole vocabulary) are dropped.
        self.assertNotIn("tokenizer.ggml.tokens", info["modelInfo"])
        self.assertIn("general.parameter_count", info["modelInfo"])

    def test_preflight_refuses_a_model_that_is_not_installed(self):
        server = FakeServer({"/api/ps": {"models": []}, "/api/show": {},
                             "/api/tags": {"models": [{"name": "other"}]}})
        with mock.patch.object(backends, "_urlopen", server):
            with self.assertRaises(BackendError):
                OllamaBackend(ENDPOINT, "m").preflight()

    def test_verify_context_accepts_a_match(self):
        server = FakeServer({"/api/ps": {"models": [
            {"name": "m", "context_length": 16384, "size_vram": 1, "digest": "sha256:abc"}]}})
        with mock.patch.object(backends, "_urlopen", server):
            report = OllamaBackend(ENDPOINT, "m", context=16384).verify_context()
        self.assertTrue(report["verified"])
        self.assertEqual(report["loadedContext"], 16384)

    def test_verify_context_aborts_on_mismatch(self):
        server = FakeServer({"/api/ps": {"models": [{"name": "m", "context_length": 8192}]}})
        with mock.patch.object(backends, "_urlopen", server):
            with self.assertRaises(BackendError) as caught:
                OllamaBackend(ENDPOINT, "m", context=16384).verify_context()
        self.assertIn("8192", str(caught.exception))
        self.assertIn("16384", str(caught.exception))

    def test_verify_context_aborts_when_nothing_is_loaded(self):
        server = FakeServer({"/api/ps": {"models": []}})
        with mock.patch.object(backends, "_urlopen", server):
            with self.assertRaises(BackendError):
                OllamaBackend(ENDPOINT, "m").verify_context()

    def test_unload_sends_keep_alive_zero_and_confirms_via_ps(self):
        server = FakeServer({"/api/generate": {"done": True},
                             "/api/ps": {"models": []}})
        with mock.patch.object(backends, "_urlopen", server):
            report = OllamaBackend(ENDPOINT, "m").unload()
        self.assertTrue(report["confirmed"])
        self.assertEqual(server.bodies("/api/generate"), [{"model": "m", "keep_alive": 0}])

    def test_unload_reports_failure_when_the_model_stays_loaded(self):
        server = FakeServer({"/api/generate": {"done": True},
                             "/api/ps": {"models": [{"name": "m"}]}})
        with mock.patch.object(backends, "_urlopen", server), \
                mock.patch("harness.backends.time.sleep", lambda _s: None):
            report = OllamaBackend(ENDPOINT, "m").unload()
        self.assertFalse(report["confirmed"])


class OpenAIRequestCase(unittest.TestCase):
    def test_request_body_matches_the_protocol(self):
        body = OpenAIBackend(ENDPOINT, "local-model", think="false",
                             output_cap=4096).build_body("prompt")
        self.assertEqual(body["model"], "local-model")
        self.assertEqual(body["max_tokens"], 4096)
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["seed"], 42)
        self.assertEqual(body["top_p"], 1)
        self.assertNotIn("top_k", body)
        self.assertNotIn("num_ctx", body)

    def test_reasoning_level_is_sent_as_reasoning_effort(self):
        self.assertEqual(
            OpenAIBackend(ENDPOINT, "m", think="high").build_body("p")["reasoning_effort"], "high")
        self.assertIs(OpenAIBackend(ENDPOINT, "m", think="true").build_body("p")["reasoning"], True)
        self.assertNotIn("reasoning_effort",
                         OpenAIBackend(ENDPOINT, "m", think="default").build_body("p"))

    def test_chat_records_usage_and_leaves_server_timings_null(self):
        payload = {"choices": [{"finish_reason": "stop",
                                "message": {"content": "```python\nx = 1\n```"}}],
                   "usage": {"completion_tokens": 50, "prompt_tokens": 20, "total_tokens": 70}}
        server = FakeServer({"/v1/chat/completions": payload})
        with mock.patch.object(backends, "_urlopen", server):
            result = OpenAIBackend(ENDPOINT, "m").chat("prompt")
        self.assertEqual(result.eval_count, 50)
        self.assertIsNone(result.eval_duration)
        self.assertIsNone(result.gen_tok_per_sec)
        self.assertEqual(result.usage["total_tokens"], 70)
        self.assertEqual(server.requests[0]["path"], "/v1/chat/completions")

    def test_max_tokens_finish_reason_counts_as_truncated(self):
        payload = {"choices": [{"finish_reason": "max_tokens", "message": {"content": "x"}}]}
        server = FakeServer({"/v1/chat/completions": payload})
        with mock.patch.object(backends, "_urlopen", server):
            self.assertTrue(OpenAIBackend(ENDPOINT, "m").chat("p").truncated)

    def test_empty_choices_raises(self):
        server = FakeServer({"/v1/chat/completions": {"choices": []}})
        with mock.patch.object(backends, "_urlopen", server):
            with self.assertRaises(BackendError):
                OpenAIBackend(ENDPOINT, "m").chat("p")

    def test_api_key_is_sent_as_a_bearer_header(self):
        server = FakeServer({"/v1/chat/completions": {
            "choices": [{"finish_reason": "stop", "message": {"content": "x"}}]}})
        with mock.patch.object(backends, "_urlopen", server):
            OpenAIBackend(ENDPOINT, "m", api_key="secret").chat("p")
        headers = {key.lower(): value for key, value in server.requests[0]["headers"].items()}
        self.assertEqual(headers["authorization"], "Bearer secret")

    def test_context_cannot_be_verified_over_this_api(self):
        report = OpenAIBackend(ENDPOINT, "m").verify_context()
        self.assertFalse(report["verified"])
        self.assertIsNone(report["loadedContext"])
        self.assertIn("caveat", report)
        self.assertIn("contextCaveat", OpenAIBackend(ENDPOINT, "m").describe())


class ReplayCase(unittest.TestCase):
    def test_returns_canned_content(self):
        backend = ReplayBackend({"A/0": "```python\ndef f():\n    return 1\n```"})
        result = backend.chat("prompt", task_id="A/0")
        self.assertIn("def f()", result.content)
        self.assertEqual(result.done_reason, "stop")
        self.assertEqual(backend.calls, ["A/0"])

    def test_dict_form_carries_timings_and_thinking(self):
        backend = ReplayBackend({"A/0": {"content": "x", "thinking": "hmm", "eval_count": 7,
                                         "eval_duration": 1_000_000_000, "wallMs": 12.5}})
        result = backend.chat("prompt", task_id="A/0")
        self.assertEqual(result.thinking, "hmm")
        self.assertEqual(result.eval_count, 7)
        self.assertAlmostEqual(result.gen_tok_per_sec, 7.0)
        self.assertEqual(result.wall_ms, 12.5)

    def test_missing_task_raises(self):
        with self.assertRaises(BackendError):
            ReplayBackend({}).chat("prompt", task_id="A/0")

    def test_from_file_loads_the_fixture(self):
        path = context.FIXTURES + "/replay-responses.json"
        backend = ReplayBackend.from_file(path)
        self.assertEqual(sorted(backend.responses), ["Fixture/0", "Fixture/1", "Fixture/2"])
        self.assertEqual(backend.model, "replay-fixture-v1")

    def test_replay_never_touches_urlopen(self):
        def explode(*_args, **_kwargs):
            raise AssertionError("the replay backend must not make HTTP requests")
        with mock.patch.object(backends, "_urlopen", explode):
            backend = ReplayBackend.from_file(context.FIXTURES + "/replay-responses.json")
            backend.chat("prompt", task_id="Fixture/0")
            backend.preflight()
            backend.verify_context()
            self.assertTrue(backend.unload()["confirmed"])


class ChatResultCase(unittest.TestCase):
    def test_gen_tok_per_sec_needs_both_fields(self):
        self.assertIsNone(ChatResult(eval_count=10).gen_tok_per_sec)
        self.assertIsNone(ChatResult(eval_duration=1_000_000_000).gen_tok_per_sec)
        self.assertAlmostEqual(
            ChatResult(eval_count=10, eval_duration=1_000_000_000).gen_tok_per_sec, 10.0)

    def test_as_record_keeps_thinking_out_of_content(self):
        payload = ChatResult(content="code", thinking="scratch").as_record()
        self.assertEqual(payload["content"], "code")
        self.assertEqual(payload["thinking"], "scratch")

    def test_build_rejects_unknown_backends(self):
        with self.assertRaises(BackendError):
            backends.build("nope", endpoint=ENDPOINT, model="m")


if __name__ == "__main__":
    unittest.main()
