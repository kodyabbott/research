"""Run record: schema, host snapshot, atomic save, overwrite refusal, resume.

Follows `uncensored-models-m5-benchmark/bench.py`: write after every task (temp file + rename),
refuse to overwrite an existing raw run, and keep no hardware serials in the host snapshot.
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
import subprocess
from pathlib import Path

from . import SCHEMA_VERSION

# Only these keys are read out of `system_profiler`. Serial numbers, hardware UUID, provisioning
# UDID and the Bluetooth/Wi-Fi addresses are deliberately not among them.
HARDWARE_KEYS = {
    "machine_model": "model_identifier",
    "chip_type": "chip",
    "number_processors": "cpu_cores",
    "physical_memory": "memory_gb",
}
FORBIDDEN_KEYS = ("serial", "uuid", "udid", "address", "provisioning")


class RecordError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _command(args: list[str], timeout: int = 30) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def host_snapshot() -> dict:
    """Host identity and state, with no serials or other hardware identifiers."""
    snapshot = {
        "capturedAt": now(),
        "model_identifier": None,
        "chip": _command(["sysctl", "-n", "machdep.cpu.brand_string"]) or None,
        "cpu_cores": _command(["sysctl", "-n", "hw.ncpu"]) or None,
        "gpu_cores": None,
        "memory_gb": None,
        "os_version": _command(["sw_vers", "-productVersion"]) or None,
        "os_build": _command(["sw_vers", "-buildVersion"]) or None,
        "kernel": _command(["uname", "-r"]) or None,
        "power_source": None,
        "thermal": _command(["pmset", "-g", "therm"]) or None,
        "swap": _command(["sysctl", "-n", "vm.swapusage"]) or None,
        "identifiersOmitted": "hardware identifiers are never collected; see record.HARDWARE_KEYS and record.FORBIDDEN_KEYS",
        "caveat": "Interactive desktop host; dedicated-host isolation is not established.",
    }
    memory = _command(["sysctl", "-n", "hw.memsize"])
    if memory.isdigit():
        snapshot["memory_gb"] = round(int(memory) / (1024 ** 3))
    battery = _command(["pmset", "-g", "batt"])
    if battery:
        first = battery.splitlines()[0]
        snapshot["power_source"] = first.replace("Now drawing from ", "").strip("'")
    raw = _command(["system_profiler", "-json", "SPHardwareDataType"], timeout=60)
    if raw:
        try:
            items = (json.loads(raw).get("SPHardwareDataType") or [{}])[0]
        except (json.JSONDecodeError, IndexError):
            items = {}
        for source, target in HARDWARE_KEYS.items():
            value = items.get(source)
            if value is not None and target in ("model_identifier", "chip"):
                snapshot[target] = value
    display = _command(["system_profiler", "-json", "SPDisplaysDataType"], timeout=60)
    if display:
        try:
            cores = (json.loads(display).get("SPDisplaysDataType") or [{}])[0]
            snapshot["gpu_cores"] = cores.get("sppci_cores")
        except (json.JSONDecodeError, IndexError):
            pass
    # Defence in depth: drop anything that looks like an identifier even if a key is added later.
    return {key: value for key, value in snapshot.items()
            if not any(bad in key.lower() for bad in FORBIDDEN_KEYS)}


def median_or_none(values: list) -> float | None:
    numbers = [value for value in values if isinstance(value, (int, float))]
    return round(statistics.median(numbers), 3) if numbers else None


class RunRecord:
    """The JSON document written to runs/<name>.json, saved atomically after every task."""

    def __init__(self, path: Path, label: str, protocol: dict, runtime: dict, model: dict,
                 resume: bool = False):
        self.path = Path(path)
        self.resume = resume
        if self.path.exists() and not resume:
            raise RecordError(
                f"refusing to overwrite an existing raw run: {self.path}. "
                f"Choose another --label or pass --resume.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.data = self._load_for_resume(protocol, runtime, model)
        else:
            self.data = {
                "schemaVersion": SCHEMA_VERSION,
                "label": label,
                "startedAt": now(),
                "finishedAt": None,
                "status": "running",
                "error": None,
                "host": host_snapshot(),
                "runtime": runtime,
                "model": model,
                "protocol": protocol,
                "tasks": [],
                "summary": {},
                "unload": None,
            }

    # -- resume ------------------------------------------------------------------------------

    RESUME_PROTOCOL_KEYS = ("suite", "suiteDigest", "datasetSha256", "promptTemplateSha256",
                            "think", "options", "outputCap", "context", "samplingProfile")

    def _load_for_resume(self, protocol: dict, runtime: dict, model: dict) -> dict:
        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("schemaVersion") != SCHEMA_VERSION:
            raise RecordError(f"cannot resume schemaVersion {data.get('schemaVersion')!r}; "
                              f"this harness writes {SCHEMA_VERSION}")
        mismatches = [key for key in self.RESUME_PROTOCOL_KEYS
                      if (data.get("protocol") or {}).get(key) != protocol.get(key)]
        if (data.get("model") or {}).get("digest") != model.get("digest"):
            mismatches.append("model.digest")
        if (data.get("model") or {}).get("name") != model.get("name"):
            mismatches.append("model.name")
        if (data.get("runtime") or {}).get("sandboxProfileSha256") != \
                runtime.get("sandboxProfileSha256"):
            mismatches.append("runtime.sandboxProfileSha256")
        if mismatches:
            raise RecordError(
                f"refusing to resume {self.path}: {', '.join(mismatches)} do not match the "
                f"existing record. A resumed run must use an identical protocol.")
        data["status"] = "running"
        data["error"] = None
        data["resumedAt"] = (data.get("resumedAt") or []) + [now()]
        data["runtime"] = runtime
        return data

    @property
    def completed_ids(self) -> set:
        return {task.get("id") for task in self.data.get("tasks") or []}

    # -- mutation ----------------------------------------------------------------------------

    def add_task(self, task: dict) -> None:
        self.data.setdefault("tasks", []).append(task)
        self.save()

    def set_status(self, status: str, error: str | None = None) -> None:
        self.data["status"] = status
        if error is not None:
            self.data["error"] = error[-2000:]

    def finish(self, status: str | None = None) -> None:
        if status:
            self.data["status"] = status
        self.data["finishedAt"] = now()
        self.data["hostAfter"] = host_snapshot()
        self.save()

    def save(self) -> None:
        self.data["updatedAt"] = now()
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=1, ensure_ascii=False)
            handle.write("\n")
        temporary.replace(self.path)

    # -- summary -----------------------------------------------------------------------------

    def summarize(self, tasks_total: int) -> dict:
        tasks = self.data.get("tasks") or []
        classes: dict[str, int] = {}
        for task in tasks:
            key = task.get("failureClass") or "none"
            classes[key] = classes.get(key, 0) + 1
        base_pass = sum(1 for task in tasks if (task.get("base") or {}).get("passed"))
        plus_pass = sum(1 for task in tasks
                        if (task.get("base") or {}).get("passed")
                        and (task.get("plus") or {}).get("passed"))
        unexpected = sum(1 for task in tasks if task.get("unexpectedThinking"))
        summary = {
            "tasksTotal": tasks_total,
            "tasksAttempted": len(tasks),
            "basePass": base_pass,
            "plusPass": plus_pass,
            "passAt1": round(plus_pass / tasks_total, 4) if tasks_total else None,
            "basePassAt1": round(base_pass / tasks_total, 4) if tasks_total else None,
            "failureClasses": classes,
            "medianWallMs": median_or_none([task.get("wallMs") for task in tasks]),
            "medianGenTokPerSec": median_or_none(
                [(task.get("response") or {}).get("genTokPerSec") for task in tasks]),
            "medianGeneratedTokens": median_or_none(
                [(task.get("response") or {}).get("eval_count") for task in tasks]),
            "medianThinkingChars": median_or_none(
                [len((task.get("response") or {}).get("thinking") or "") for task in tasks]),
            "truncated": sum(1 for task in tasks if task.get("truncated")),
            "unexpectedThinking": unexpected,
        }
        summary["protocolValid"] = bool(
            self.data.get("status") == "completed"
            and len(tasks) == tasks_total
            and unexpected == 0
            and (self.data.get("runtime") or {}).get("sandboxSelfTest", {}).get("passed"))
        self.data["summary"] = summary
        return summary


def load_record(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)
