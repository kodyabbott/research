"""The program that runs INSIDE the sandbox. Standalone: imports nothing from `harness`.

Reads a job as JSON on stdin, execs the supplied code in a fresh namespace, calls the entry point
once per input under a per-input SIGALRM timeout, and appends one JSON object per input to
`$WORKDIR/results.jsonl` (flushed each time, so a SIGXCPU/SIGKILL still shows how far it got).
A summary lands in `$WORKDIR/meta.json`.

Results are written to files rather than stdout because a candidate's stray `print()` would
otherwise corrupt the payload (EvalPlus wraps execution in `swallow_io` for the same reason).

Job schema (all keys optional unless noted):
  code              str   -- required; the candidate or canonical program
  entry_point       str   -- required; function name to resolve after exec
  task_id           str   -- e.g. "Mbpp/2"; used by the MBPP input deserializer
  inputs            list  -- required; raw JSON argument lists, one per call
  deserialize       str   -- "mbpp" to apply mbpp_deserialize_inputs, else null
  not_none_mode     str   -- "trusted" | "candidate" | null (see MBPP not-None oracle)
  per_input_seconds float | list[float] -- wall timeout per call
  record_time       bool  -- include per-call seconds in the output

Value encoding: every returned object is serialized with a type-tagged encoding so the harness can
rebuild native Python values and compare them with real `==` semantics (tuple != list, sets by
membership, NaN, arbitrary nesting) without ever executing anything.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import signal
import sys
import time
import traceback

MAX_DEPTH = 100
# Above this many nodes a value is hashed by streaming rather than materialized as tagged JSON,
# so HumanEval+'s extreme inputs (make_a_pile(1000000) and friends) cannot exhaust memory.
MAX_NODES = 2_000_000
# Values whose canonical JSON exceeds this are reported as a digest instead of a value.
MAX_VALUE_BYTES = 64 * 1024
MAX_REPR = 4096
MAX_ERROR = 600


def _dumps(payload) -> str:
    """The canonical serialization a digest is taken over. Must match harness.values._dumps."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------------------------
# Type-tagged value encoding
# ---------------------------------------------------------------------------------------------


class _Budget:
    __slots__ = ("nodes",)

    def __init__(self):
        self.nodes = 0


def encode(obj, budget: _Budget | None = None, depth: int = 0):
    """Serialize `obj` into JSON-safe tagged form. Unknown objects degrade to their repr."""
    budget = budget if budget is not None else _Budget()
    budget.nodes += 1
    if budget.nodes > MAX_NODES or depth > MAX_DEPTH:
        return {"t": "overflow"}
    if obj is None:
        return {"t": "none"}
    cls = type(obj)
    if cls is bool:
        return {"t": "bool", "v": obj}
    if cls is int:
        return {"t": "int", "v": str(obj)}
    if cls is float:
        return {"t": "float", "v": repr(obj)}
    if cls is str:
        return {"t": "str", "v": obj}
    if cls is complex:
        return {"t": "complex", "v": [repr(obj.real), repr(obj.imag)]}
    if cls in (bytes, bytearray):
        return {"t": "bytes" if cls is bytes else "bytearray", "v": bytes(obj).hex()}
    if cls in (list, tuple):
        return {"t": "list" if cls is list else "tuple",
                "v": [encode(item, budget, depth + 1) for item in obj]}
    if cls in (set, frozenset):
        return {"t": "set" if cls is set else "frozenset",
                "v": [encode(item, budget, depth + 1) for item in obj]}
    if cls is dict:
        return {"t": "dict",
                "v": [[encode(key, budget, depth + 1), encode(value, budget, depth + 1)]
                      for key, value in obj.items()]}
    if isinstance(obj, bool):
        return {"t": "bool", "v": bool(obj), "cls": cls.__name__}
    if isinstance(obj, int):
        return {"t": "int", "v": str(int(obj)), "cls": cls.__name__}
    if isinstance(obj, float):
        return {"t": "float", "v": repr(float(obj)), "cls": cls.__name__}
    if isinstance(obj, str):
        return {"t": "str", "v": str(obj), "cls": cls.__name__}
    if isinstance(obj, (list, tuple)):
        return {"t": "tuple" if isinstance(obj, tuple) else "list", "cls": cls.__name__,
                "v": [encode(item, budget, depth + 1) for item in obj]}
    try:
        text = repr(obj)
    except BaseException:  # pragma: no cover - pathological __repr__
        text = "<unreprable>"
    return {"t": "repr", "cls": cls.__name__, "v": text[:MAX_REPR]}


_CONTAINER_TAGS = {list: "list", tuple: "tuple", set: "set", frozenset: "frozenset"}


def count_nodes(obj, limit: int = MAX_NODES, depth: int = 0) -> int:
    """Cheap node count with early exit. Never allocates a copy of the value."""
    if depth > MAX_DEPTH:
        return limit + 1
    cls = type(obj)
    if cls in _CONTAINER_TAGS:
        total = 1
        for item in obj:
            total += count_nodes(item, limit, depth + 1)
            if total > limit:
                return total
        return total
    if cls is dict:
        total = 1
        for key, value in obj.items():
            total += count_nodes(key, limit, depth + 1) + count_nodes(value, limit, depth + 1)
            if total > limit:
                return total
        return total
    return 1


def canonical_chunks(obj, depth: int = 0):
    """Yield exactly the bytes `_dumps(encode(obj))` would produce, without building it.

    json.dumps with fixed separators is compositional over nested structures, and every tagged
    object uses the same literal keys in the same order, so a streamed digest over these chunks is
    byte-identical to hashing the materialized form.
    """
    if depth > MAX_DEPTH:
        raise ValueError("value nests deeper than the encoder supports")
    cls = type(obj)
    tag = _CONTAINER_TAGS.get(cls)
    if tag is not None:
        yield '{"t":"' + tag + '","v":['
        first = True
        for item in obj:
            if not first:
                yield ","
            first = False
            yield from canonical_chunks(item, depth + 1)
        yield "]}"
        return
    if cls is dict:
        yield '{"t":"dict","v":['
        first = True
        for key, value in obj.items():
            if not first:
                yield ","
            first = False
            yield "["
            yield from canonical_chunks(key, depth + 1)
            yield ","
            yield from canonical_chunks(value, depth + 1)
            yield "]"
        yield "]}"
        return
    yield _dumps(encode(obj, _Budget(), depth))


def encode_or_digest(obj):
    """Tagged value when it is small enough, otherwise a digest of its canonical form.

    HumanEval+'s plus inputs include cases such as `string_sequence(1000011)` (a ~7 MB string) and
    `make_a_pile(1000000)` (a million integers). Shipping those out of the sandbox for every input
    would produce multi-hundred-megabyte payloads, so oversized values are compared by digest.
    """
    if count_nodes(obj) > MAX_NODES:
        digest = hashlib.sha256()
        total = 0
        for chunk in canonical_chunks(obj):
            encoded = chunk.encode("utf-8")
            digest.update(encoded)
            total += len(encoded)
        return {"t": "digest", "v": digest.hexdigest(), "bytes": total}
    tagged = encode(obj)
    blob = _dumps(tagged).encode("utf-8")
    if len(blob) > MAX_VALUE_BYTES:
        return {"t": "digest", "v": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
    return tagged


# ---------------------------------------------------------------------------------------------
# MBPP+ input reconstruction
# ---------------------------------------------------------------------------------------------
# Verbatim port of `mbpp_deserialize_inputs` from evalplus/data/mbpp.py at evalplus v0.3.1
# (commit e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2). MBPP+ stores tuples/sets/complex numbers as
# JSON lists and strings; without this the canonical solutions receive the wrong argument types.

_MBPP_TUPLE_LISTS = [2, 116, 132, 143, 222, 261, 273, 394, 399, 421, 424, 429, 470, 560, 579, 596,
                     616, 630, 726, 740, 744, 809]
_MBPP_NESTED_TUPLE_LISTS = [63, 64, 70, 94, 120, 237, 272, 299, 400, 409, 417, 438, 473, 614, 780]
_MBPP_FIRST_ARG_TUPLE_LIST = [75, 413, 444, 753]
_MBPP_FIRST_ARG_TUPLE = [250, 405, 446, 617, 720, 763, 808]
_MBPP_NESTED_THEN_TUPLE = [259, 401, 445]
_MBPP_ALL_TUPLES = [580, 615, 791]


def mbpp_deserialize_inputs(task_id: str, inputs: list) -> list:
    numeric = int(str(task_id).split("/")[-1])
    if numeric in _MBPP_TUPLE_LISTS:
        return [[tuple(lst) for lst in inp] for inp in inputs]
    if numeric in _MBPP_NESTED_TUPLE_LISTS:
        return [[[tuple(lst) for lst in lst_lst] for lst_lst in inp] for inp in inputs]
    if numeric in _MBPP_FIRST_ARG_TUPLE_LIST:
        return [[[tuple(lst) for lst in inp[0]]] + [inp[1]] for inp in inputs]
    if numeric in (106, 750):
        return [[inp[0]] + [tuple(inp[1])] for inp in inputs]
    if numeric == 115:
        # EvalPlus uses `{}` (an empty dict) for empty members; ported verbatim, quirk included.
        return [[[set(item) if isinstance(item, list) and len(item) else {}
                  for item in inp[0]]] for inp in inputs]
    if numeric == 124:
        return [(float(inp[0]), complex(inp[1])) for inp in inputs]
    if numeric in _MBPP_FIRST_ARG_TUPLE:
        return [[tuple(inp[0])] + [inp[1]] for inp in inputs]
    if numeric in _MBPP_NESTED_THEN_TUPLE:
        modified = [[[tuple(lst) for lst in lst_lst] for lst_lst in inp] for inp in inputs]
        return [[tuple(lst) for lst in inp] for inp in modified]
    if numeric == 278:
        modified = [[[tuple(item) if isinstance(item, list) else item for item in inp[0]]]
                    for inp in inputs]
        return [[tuple(lst) for lst in inp] for inp in modified]
    if numeric == 307:
        return [[tuple(inp[0])] + [inp[1], inp[2]] for inp in inputs]
    if numeric == 722:
        return [[{key: tuple(value) for key, value in inp[0].items()}] + inp[1:] for inp in inputs]
    if numeric == 252:
        return [[complex(inp[0])] for inp in inputs]
    if numeric in _MBPP_ALL_TUPLES:
        def to_tuple(value):
            if isinstance(value, list):
                return tuple(to_tuple(item) for item in value)
            return value
        return [to_tuple(inp) for inp in inputs]
    return inputs


# ---------------------------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------------------------


class _Discard:
    """Swallows candidate output. Avoids needing a /dev/null allow rule in the sandbox profile."""

    def write(self, _data):
        return len(_data) if isinstance(_data, (str, bytes)) else 0

    def writelines(self, _lines):
        return None

    def flush(self):
        return None

    def isatty(self):
        return False

    def fileno(self):
        raise OSError("no file descriptor")

    def read(self, *_args):
        return ""

    def readline(self, *_args):
        return ""


class _PerInputTimeout(BaseException):
    """Raised from the SIGALRM handler. BaseException so `except Exception` cannot swallow it."""


def _alarm(_signum, _frame):
    raise _PerInputTimeout()


def _short(exc: BaseException) -> str:
    try:
        message = str(exc)
    except BaseException:  # pragma: no cover
        message = "<unprintable>"
    return f"{type(exc).__name__}: {message}"[:MAX_ERROR]


def main() -> int:
    if hasattr(sys, "set_int_max_str_digits"):
        # Python 3.11+ caps int->str at 4300 digits; EvalPlus's reference environment predates
        # that cap, and HumanEval/83 and /139 legitimately build much larger integers.
        sys.set_int_max_str_digits(0)
    workdir = os.environ.get("WORKDIR") or os.getcwd()
    meta_path = os.path.join(workdir, "meta.json")
    results_path = os.path.join(workdir, "results.jsonl")

    def write_meta(**fields):
        with open(meta_path, "w", encoding="utf-8") as handle:
            json.dump(fields, handle)
            handle.flush()
            os.fsync(handle.fileno())

    try:
        job = json.loads(sys.stdin.read())
    except Exception as exc:
        write_meta(stage="bad-job", error=_short(exc))
        return 2

    code = job["code"]
    entry_point = job["entry_point"]
    inputs = job.get("inputs") or []
    record_time = bool(job.get("record_time"))
    not_none_mode = job.get("not_none_mode")
    per_input = job.get("per_input_seconds", 1.0)
    if not isinstance(per_input, list):
        per_input = [float(per_input)] * len(inputs)
    per_input = [max(0.01, float(value)) for value in per_input]

    if job.get("deserialize") == "mbpp":
        try:
            inputs = mbpp_deserialize_inputs(job.get("task_id", "Mbpp/0"), inputs)
        except Exception as exc:
            write_meta(stage="deserialize-error", error=_short(exc))
            return 3

    write_meta(stage="started", count=len(inputs))
    real_stdout, real_stderr = sys.stdout, sys.stderr
    sink = _Discard()
    namespace = {"__name__": "__candidate__", "__builtins__": __builtins__}

    sys.stdout, sys.stderr = sink, sink
    try:
        compiled = compile(code, "<candidate>", "exec")
    except BaseException as exc:
        sys.stdout, sys.stderr = real_stdout, real_stderr
        write_meta(stage="syntax-error", error=_short(exc),
                   traceback=traceback.format_exc()[-2000:])
        return 0
    try:
        signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, float(job.get("exec_seconds", 10.0)))
        try:
            exec(compiled, namespace)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    except _PerInputTimeout:
        sys.stdout, sys.stderr = real_stdout, real_stderr
        write_meta(stage="exec-timeout", error="module-level code exceeded its time limit")
        return 0
    except BaseException as exc:
        sys.stdout, sys.stderr = real_stdout, real_stderr
        write_meta(stage="exec-error", error=_short(exc), traceback=traceback.format_exc()[-2000:])
        return 0

    function = namespace.get(entry_point)
    if function is None or not callable(function):
        sys.stdout, sys.stderr = real_stdout, real_stderr
        write_meta(stage="missing-entry-point", error=f"{entry_point} not defined after exec",
                   defined=sorted(k for k in namespace if not k.startswith("__"))[:50])
        return 0

    handle = open(results_path, "w", encoding="utf-8")
    completed = 0
    try:
        for index, raw in enumerate(inputs):
            row = {"i": index}
            try:
                args = copy.deepcopy(raw)
            except BaseException as exc:  # pragma: no cover - dataset inputs are JSON-derived
                row.update(status="harness-error", error=_short(exc))
                _emit(handle, row)
                completed += 1
                continue
            if not isinstance(args, (list, tuple)):
                args = [args]
            started = time.perf_counter()
            try:
                signal.setitimer(signal.ITIMER_REAL, per_input[index])
                value = function(*args)
                signal.setitimer(signal.ITIMER_REAL, 0)
                if not_none_mode == "trusted":
                    value = value is not None
                elif not_none_mode == "candidate" and not isinstance(value, bool):
                    value = value is not None
                row.update(status="ok", value=encode_or_digest(value))
            except _PerInputTimeout:
                signal.setitimer(signal.ITIMER_REAL, 0)
                row.update(status="timeout", error=f"exceeded {per_input[index]:.3f}s")
            except BaseException as exc:
                signal.setitimer(signal.ITIMER_REAL, 0)
                row.update(status="exception", error=_short(exc))
            if record_time:
                row["seconds"] = round(time.perf_counter() - started, 6)
            _emit(handle, row)
            completed += 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            handle.close()
        except BaseException:
            pass
        sys.stdout, sys.stderr = real_stdout, real_stderr
    write_meta(stage="done", count=len(inputs), completed=completed)
    return 0


def _emit(handle, row) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    handle.flush()


if __name__ == "__main__":
    sys.exit(main())
