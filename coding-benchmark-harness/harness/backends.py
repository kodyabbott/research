"""Model backends: Ollama native `/api/chat`, OpenAI-compatible `/v1/chat/completions`, and Replay.

Request handling follows `uncensored-models-m5-benchmark/bench.py`: one non-streaming POST per task,
`think` sent unless the mode is `default`, and the full server response stored verbatim in the run
record.

Every HTTP call goes through the module-level `_urlopen`, which the tests replace with a fake. No
network call is made anywhere else in this package.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

PRIMARY_PORT = "11434"
DEFAULT_ENDPOINT = "http://127.0.0.1:11436"
DEFAULT_CONTEXT = 16384
KEEP_ALIVE = "10m"
THINK_MODES = ("false", "true", "default", "low", "medium", "high")

# DESIGN.md sampling profile "greedy-v1".
OLLAMA_OPTIONS = {"temperature": 0, "seed": 42, "top_p": 1, "top_k": 40, "repeat_penalty": 1.0}
OPENAI_OPTIONS = {"temperature": 0, "seed": 42, "top_p": 1}


class BackendError(RuntimeError):
    pass


class EndpointRefused(BackendError):
    """Raised for the personal Ollama server on port 11434."""


def _urlopen(request, timeout):  # pragma: no cover - replaced by a fake in tests
    return urllib.request.urlopen(request, timeout=timeout)


def check_endpoint(endpoint: str) -> str:
    """Refuse the personal Ollama server outright, as bench.py does."""
    cleaned = (endpoint or "").rstrip("/")
    if not cleaned:
        raise EndpointRefused("an explicit --endpoint is required")
    if cleaned.endswith(":" + PRIMARY_PORT):
        raise EndpointRefused(
            f"refusing endpoint {cleaned}: port {PRIMARY_PORT} is the personal Ollama server; "
            f"use the dedicated benchmark server (default {DEFAULT_ENDPOINT})")
    return cleaned


def think_field(mode: str):
    """bench.py's mapping: false/true become booleans, levels pass through, default is omitted."""
    if mode == "default":
        return None
    return {"false": False, "true": True}.get(mode, mode)


@dataclass
class ChatResult:
    content: str = ""
    thinking: str = ""
    request: dict = field(default_factory=dict)
    response: dict = field(default_factory=dict)
    wall_ms: float = 0.0
    done_reason: str | None = None
    eval_count: int | None = None
    eval_duration: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration: int | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    usage: dict | None = None

    @property
    def truncated(self) -> bool:
        return self.done_reason in ("length", "max_tokens")

    @property
    def gen_tok_per_sec(self) -> float | None:
        if self.eval_count and self.eval_duration:
            return self.eval_count * 1e9 / self.eval_duration
        return None

    def as_record(self) -> dict:
        return {
            "content": self.content,
            "thinking": self.thinking,
            "done_reason": self.done_reason,
            "eval_count": self.eval_count,
            "eval_duration": self.eval_duration,
            "prompt_eval_count": self.prompt_eval_count,
            "prompt_eval_duration": self.prompt_eval_duration,
            "total_duration": self.total_duration,
            "load_duration": self.load_duration,
            "usage": self.usage,
            "genTokPerSec": self.gen_tok_per_sec,
        }


class Backend:
    name = "base"

    def describe(self) -> dict:
        raise NotImplementedError

    def chat(self, prompt: str, task_id: str | None = None,
             seconds: float = 300.0) -> ChatResult:
        raise NotImplementedError

    def preflight(self) -> dict:
        """Model identity and server state captured before the first task."""
        return {}

    def unload(self) -> dict:
        return {"confirmed": None, "reason": "backend does not support unloading"}


class HttpBackend(Backend):
    def __init__(self, endpoint: str, model: str, think: str = "false",
                 output_cap: int = 4096, context: int = DEFAULT_CONTEXT,
                 request_timeout: float = 300.0):
        if think not in THINK_MODES:
            raise BackendError(f"unknown think mode {think!r}; choose from {THINK_MODES}")
        self.endpoint = check_endpoint(endpoint)
        self.model = model
        self.think = think
        self.output_cap = output_cap
        self.context = context
        self.request_timeout = request_timeout

    def post(self, path: str, body: dict | None = None, timeout: float | None = None,
             method: str | None = None) -> dict:
        url = self.endpoint + path
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"},
            method=method or ("POST" if data is not None else "GET"))
        try:
            with _urlopen(request, timeout or self.request_timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:2000].decode("utf-8", "replace") if exc.fp else ""
            raise BackendError(f"{url} returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise BackendError(f"{url} unreachable: {exc.reason}") from exc
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise BackendError(f"{url} returned non-JSON: {payload[:200]!r}") from exc


class OllamaBackend(HttpBackend):
    """Ollama native API. Sends `options.num_ctx` explicitly and verifies it via /api/ps."""

    name = "ollama"

    def build_body(self, prompt: str) -> dict:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {**OLLAMA_OPTIONS, "num_ctx": self.context,
                        "num_predict": self.output_cap},
        }
        # Sent unless 'default': some imports reject the field entirely (bench.py, Gemma).
        value = think_field(self.think)
        if value is not None:
            body["think"] = value
        return body

    def chat(self, prompt: str, task_id: str | None = None,
             seconds: float = 300.0) -> ChatResult:
        body = self.build_body(prompt)
        started = time.monotonic()
        response = self.post("/api/chat", body, timeout=seconds)
        wall_ms = round((time.monotonic() - started) * 1000, 2)
        if not response.get("done"):
            raise BackendError(f"incomplete response for {task_id}: {str(response)[:400]}")
        message = response.get("message") or {}
        return ChatResult(
            content=message.get("content") or "",
            thinking=message.get("thinking") or "",
            request=body, response=response, wall_ms=wall_ms,
            done_reason=response.get("done_reason"),
            eval_count=response.get("eval_count"),
            eval_duration=response.get("eval_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            prompt_eval_duration=response.get("prompt_eval_duration"),
            total_duration=response.get("total_duration"),
            load_duration=response.get("load_duration"),
        )

    def describe(self) -> dict:
        return {"backend": self.name, "endpoint": self.endpoint, "think": self.think,
                "options": {**OLLAMA_OPTIONS, "num_ctx": self.context,
                            "num_predict": self.output_cap}}

    def ps(self) -> dict:
        return self.post("/api/ps", timeout=60)

    def show(self) -> dict:
        return self.post("/api/show", {"model": self.model}, timeout=120)

    def tags(self) -> dict:
        return self.post("/api/tags", timeout=60)

    def version(self) -> dict:
        return self.post("/api/version", timeout=60)

    def preflight(self) -> dict:
        """Record model identity. Raises when another model already occupies the server."""
        loaded = (self.ps().get("models") or [])
        if loaded:
            names = [row.get("name") or row.get("model") for row in loaded]
            raise BackendError(
                f"the server at {self.endpoint} already has {names} loaded; "
                f"another benchmark may be using the GPU. Refusing to start.")
        info = self.show()
        installed = {row.get("name"): row for row in (self.tags().get("models") or [])}
        artifact = installed.get(self.model)
        if artifact is None:
            raise BackendError(f"model {self.model!r} is not installed on {self.endpoint}")
        return {
            "name": self.model,
            "digest": artifact.get("digest"),
            "sizeBytes": artifact.get("size"),
            "details": info.get("details"),
            "capabilities": info.get("capabilities"),
            "parameters": info.get("parameters"),
            "templateSha256": hashlib.sha256((info.get("template") or "").encode()).hexdigest(),
            "modelInfo": {key: value for key, value in (info.get("model_info") or {}).items()
                          if not isinstance(value, list)},
            "serverVersion": self.version(),
        }

    def verify_context(self) -> dict:
        """Confirm the loaded context equals what was requested; abort on mismatch.

        The dedicated server runs with OLLAMA_CONTEXT_LENGTH=8192, so `options.num_ctx` has to be
        honoured for the protocol to hold (DESIGN.md revisions item 4).
        """
        loaded = self.ps().get("models") or []
        report = {"requestedContext": self.context, "loaded": loaded, "verified": False}
        for row in loaded:
            if (row.get("name") or row.get("model")) != self.model:
                continue
            report["loadedContext"] = row.get("context_length")
            report["sizeVram"] = row.get("size_vram")
            report["digest"] = row.get("digest")
            if row.get("context_length") and row["context_length"] != self.context:
                raise BackendError(
                    f"server loaded context {row['context_length']} but the protocol requested "
                    f"{self.context}; refusing to continue")
            report["verified"] = True
            return report
        raise BackendError(f"model {self.model!r} is not loaded after the first request")

    def unload(self) -> dict:
        self.post("/api/generate", {"model": self.model, "keep_alive": 0}, timeout=120)
        for _attempt in range(60):
            if not (self.ps().get("models") or []):
                return {"confirmed": True,
                        "confirmedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            time.sleep(1)
        return {"confirmed": False, "reason": "model still loaded after 60s"}


class OpenAIBackend(HttpBackend):
    """OpenAI-compatible `/v1/chat/completions` (LM Studio, llama-server, mlx_lm.server)."""

    name = "openai"

    def __init__(self, *args, api_key: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = api_key

    def build_body(self, prompt: str) -> dict:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": self.output_cap,
            **OPENAI_OPTIONS,
        }
        # No portable way to request a context size over this API; recorded as a caveat instead.
        value = think_field(self.think)
        if value is not None:
            body["reasoning_effort" if isinstance(value, str) else "reasoning"] = value
        return body

    def post(self, path: str, body: dict | None = None, timeout: float | None = None,
             method: str | None = None) -> dict:
        if not self.api_key:
            return super().post(path, body, timeout, method)
        url = self.endpoint + path
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            url, data=data, method=method or ("POST" if data is not None else "GET"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        with _urlopen(request, timeout or self.request_timeout) as response:
            return json.loads(response.read() or b"{}")

    def chat(self, prompt: str, task_id: str | None = None,
             seconds: float = 300.0) -> ChatResult:
        body = self.build_body(prompt)
        started = time.monotonic()
        response = self.post("/v1/chat/completions", body, timeout=seconds)
        wall_ms = round((time.monotonic() - started) * 1000, 2)
        choices = response.get("choices") or []
        if not choices:
            raise BackendError(f"no choices returned for {task_id}: {str(response)[:400]}")
        message = choices[0].get("message") or {}
        usage = response.get("usage") or {}
        return ChatResult(
            content=message.get("content") or "",
            thinking=message.get("reasoning_content") or message.get("reasoning") or "",
            request=body, response=response, wall_ms=wall_ms,
            done_reason=choices[0].get("finish_reason"),
            # Server-side timings are not part of this API; only token counts are available.
            eval_count=usage.get("completion_tokens"),
            prompt_eval_count=usage.get("prompt_tokens"),
            usage=usage,
        )

    def describe(self) -> dict:
        return {"backend": self.name, "endpoint": self.endpoint, "think": self.think,
                "options": {**OPENAI_OPTIONS, "max_tokens": self.output_cap},
                "contextCaveat": "this API cannot request a context size; "
                                 "loadedContext is recorded as null"}

    def preflight(self) -> dict:
        try:
            models = self.post("/v1/models", timeout=60)
        except BackendError:
            models = {}
        return {"name": self.model, "digest": None, "serverModels": models,
                "contextUnverified": True}

    def verify_context(self) -> dict:
        return {"requestedContext": None, "loadedContext": None, "verified": False,
                "caveat": "the OpenAI-compatible API exposes no context length"}


class ReplayBackend(Backend):
    """Returns canned responses. Used by the tests and by `run.py --backend replay`."""

    name = "replay"

    def __init__(self, responses: dict, model: str = "replay",
                 think: str = "false", output_cap: int = 4096,
                 context: int = DEFAULT_CONTEXT, label: str | None = None):
        self.responses = responses
        self.model = model
        self.think = think
        self.output_cap = output_cap
        self.context = context
        self.endpoint = "replay://" + (label or "fixture")
        self.calls: list[str] = []

    @classmethod
    def from_file(cls, path, **kwargs) -> "ReplayBackend":
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls(payload.get("responses") or payload,
                   model=payload.get("model", "replay"), **kwargs)

    def describe(self) -> dict:
        return {"backend": self.name, "endpoint": self.endpoint, "think": self.think,
                "options": {"replay": True, "num_predict": self.output_cap},
                "responses": len(self.responses)}

    def chat(self, prompt: str, task_id: str | None = None,
             seconds: float = 300.0) -> ChatResult:
        self.calls.append(task_id or prompt[:40])
        canned = self.responses.get(task_id)
        if canned is None:
            raise BackendError(f"replay backend has no response for {task_id!r}")
        if isinstance(canned, str):
            canned = {"content": canned}
        content = canned.get("content", "")
        return ChatResult(
            content=content,
            thinking=canned.get("thinking", ""),
            request={"model": self.model, "messages": [{"role": "user", "content": prompt}],
                     "replay": True},
            response={"done": True, "replay": True, **canned},
            wall_ms=float(canned.get("wallMs", 1.0)),
            done_reason=canned.get("done_reason", "stop"),
            eval_count=canned.get("eval_count", max(1, len(content) // 4)),
            eval_duration=canned.get("eval_duration", 1_000_000_00),
            prompt_eval_count=canned.get("prompt_eval_count", max(1, len(prompt) // 4)),
            prompt_eval_duration=canned.get("prompt_eval_duration", 1_000_000_0),
            total_duration=canned.get("total_duration", 1_100_000_00),
            load_duration=canned.get("load_duration", 0),
        )

    def preflight(self) -> dict:
        return {"name": self.model, "digest": None, "replay": True,
                "responses": sorted(self.responses)}

    def verify_context(self) -> dict:
        return {"requestedContext": self.context, "loadedContext": self.context,
                "verified": True, "replay": True}

    def unload(self) -> dict:
        return {"confirmed": True, "replay": True}


def build(backend: str, **kwargs) -> Backend:
    if backend == "ollama":
        return OllamaBackend(**kwargs)
    if backend == "openai":
        return OpenAIBackend(**kwargs)
    raise BackendError(f"unknown backend {backend!r}")
