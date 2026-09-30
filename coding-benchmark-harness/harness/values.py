"""Decoding of the type-tagged values produced by `sandbox_runner.encode`.

Pure data construction: lists, tuples, sets, dicts, numbers, strings. Nothing here executes or
evaluates model output, so decoded values are safe to compare with real Python `==`, which is what
keeps grading faithful to EvalPlus (tuple != list, `1 == 1.0`, set membership, NaN handling).
"""

from __future__ import annotations

import hashlib
import json

DIGEST_TAG = "digest"


def _dumps(payload) -> str:
    """Canonical serialization for digests. Must match sandbox_runner._dumps byte for byte."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def digest_of(tagged) -> str:
    """SHA-256 identifying a tagged value, whether it arrived whole or already digested."""
    if isinstance(tagged, dict) and tagged.get("t") == DIGEST_TAG:
        return tagged.get("v") or ""
    return hashlib.sha256(_dumps(tagged).encode("utf-8")).hexdigest()


def is_digest(tagged) -> bool:
    return isinstance(tagged, dict) and tagged.get("t") == DIGEST_TAG


class Digest:
    """An oversized value represented only by the hash of its canonical form."""

    __slots__ = ("hex", "bytes")

    def __init__(self, hex_digest: str, size: int | None = None):
        self.hex = hex_digest
        self.bytes = size

    def __eq__(self, other):
        return isinstance(other, Digest) and self.hex == other.hex

    def __hash__(self):
        return hash(self.hex)

    def __repr__(self):
        return f"Digest({self.hex[:16]}..., bytes={self.bytes})"


class Opaque:
    """Stand-in for an object EvalPlus would have compared by identity/equality in-process.

    Only equal to another Opaque with the same repr. Used for objects whose type cannot cross the
    sandbox boundary (re.Match, custom classes, generators, ...).
    """

    __slots__ = ("cls", "text")

    def __init__(self, cls: str, text: str):
        self.cls = cls
        self.text = text

    def __eq__(self, other):
        return isinstance(other, Opaque) and (self.cls, self.text) == (other.cls, other.text)

    def __hash__(self):
        return hash((self.cls, self.text))

    def __repr__(self):
        return f"Opaque({self.cls}, {self.text!r})"


class Overflow:
    """A value that exceeded the encoder's depth/node budget. Never equal to anything."""

    __slots__ = ()

    def __eq__(self, other):
        return False

    def __hash__(self):
        return hash("<overflow>")

    def __repr__(self):
        return "Overflow()"


class DecodeError(ValueError):
    pass


def decode(tagged):
    """Rebuild a native Python value from the tagged encoding."""
    if not isinstance(tagged, dict) or "t" not in tagged:
        raise DecodeError(f"not a tagged value: {tagged!r}")
    kind = tagged["t"]
    if kind == "none":
        return None
    if kind == "bool":
        return bool(tagged["v"])
    if kind == "int":
        return int(tagged["v"])
    if kind == "float":
        return float(tagged["v"])
    if kind == "str":
        return tagged["v"]
    if kind == "complex":
        return complex(float(tagged["v"][0]), float(tagged["v"][1]))
    if kind == "bytes":
        return bytes.fromhex(tagged["v"])
    if kind == "bytearray":
        return bytearray(bytes.fromhex(tagged["v"]))
    if kind == "list":
        return [decode(item) for item in tagged["v"]]
    if kind == "tuple":
        return tuple(decode(item) for item in tagged["v"])
    if kind in ("set", "frozenset"):
        items = [decode(item) for item in tagged["v"]]
        try:
            return set(items) if kind == "set" else frozenset(items)
        except TypeError:  # unhashable member; keep something comparable instead of crashing
            return Opaque(kind, repr(items))
    if kind == "dict":
        result = {}
        for pair in tagged["v"]:
            key, value = decode(pair[0]), decode(pair[1])
            try:
                result[key] = value
            except TypeError:
                return Opaque("dict", repr(tagged["v"]))
        return result
    if kind == "repr":
        return Opaque(tagged.get("cls", "object"), tagged.get("v", ""))
    if kind == DIGEST_TAG:
        return Digest(tagged.get("v") or "", tagged.get("bytes"))
    if kind == "overflow":
        return Overflow()
    raise DecodeError(f"unknown tag {kind!r}")


def brief(tagged, limit: int = 240) -> str:
    """Short human-readable rendering of a tagged value, for failure details in run records."""
    try:
        text = repr(decode(tagged))
    except Exception:
        text = repr(tagged)
    return text if len(text) <= limit else text[:limit] + "..."
