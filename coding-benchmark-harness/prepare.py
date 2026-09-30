#!/usr/bin/env python3
"""Download and verify a pinned EvalPlus dataset, then compute its expected outputs in the sandbox.

Expected outputs come from running the canonical solution (`prompt + canonical_solution`, exactly
as `evalplus.evaluate.get_groundtruth` does) over the base and plus inputs **inside the sandbox**,
once. The per-input wall time is recorded at the same time; candidate code later gets
`max(1.0 s, 4 x canonical per-input time)` per input, which is EvalPlus's
`DEFAULT_MIN_TIME_LIMIT` / `DEFAULT_GT_TIME_LIMIT_FACTOR`.

    python3 coding-benchmark-harness/prepare.py --suite humaneval-plus
    python3 coding-benchmark-harness/prepare.py --suite humaneval-plus --suite mbpp-plus
    python3 coding-benchmark-harness/prepare.py --suite fixture

A task whose canonical solution fails or times out is written to `expected/<suite>/_skipped.json`
with the reason and is excluded from scoring.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import grader, java_grader, java_sandbox, java_toolchain, suites  # noqa: E402
from harness.sandbox import SandboxExec, SandboxUnavailable, runner_sha256  # noqa: E402

DOWNLOAD_TIMEOUT = 300
PREPARE_WALL_SECONDS = 600.0
PREPARE_CPU_SECONDS = 300


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def download(url: str, target: Path, expected_sha256: str | None, expected_bytes: int | None,
             force: bool = False) -> dict:
    """Fetch `url` to `target` and verify its SHA-256. Refuses to keep a mismatching file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        digest = suites.sha256_file(target)
        if expected_sha256 and digest != expected_sha256:
            raise SystemExit(
                f"{target} is already present but its SHA-256 is {digest}, not {expected_sha256}. "
                f"Delete it and re-run, or fix datasets.json.")
        return {"downloaded": False, "path": str(target), "sha256": digest,
                "bytes": target.stat().st_size}
    print(f"  downloading {url}")
    with tempfile.NamedTemporaryFile(delete=False, dir=target.parent, suffix=".part") as handle:
        temporary = Path(handle.name)
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
            shutil.copyfileobj(response, handle)
    digest = suites.sha256_file(temporary)
    size = temporary.stat().st_size
    if expected_sha256 and digest != expected_sha256:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"SHA-256 mismatch for {url}: expected {expected_sha256}, got {digest}. "
                         f"Refusing to use the download.")
    if expected_bytes and size != expected_bytes:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"size mismatch for {url}: expected {expected_bytes} bytes, got {size}")
    os.replace(temporary, target)
    return {"downloaded": True, "path": str(target), "sha256": digest, "bytes": size}


def compute_expected(sandbox: SandboxExec, task: suites.Task, which: str,
                     wall_seconds: float, cpu_seconds: int) -> tuple[dict | None, str | None]:
    """Run the canonical solution over one input set. Returns (payload, skip reason)."""
    inputs = task.base_input if which == "base" else task.plus_input
    job = grader.build_job(
        code=task.canonical_program,
        entry_point=task.entry_point,
        task_id=task.task_id,
        dataset=task.dataset,
        inputs=inputs,
        # The canonical solution is trusted; give it a generous ceiling rather than the
        # candidate limits, which are derived from its own timings.
        per_input_seconds=[wall_seconds] * len(inputs),
        not_none_mode=grader.not_none_mode_for(task.dataset, task.entry_point, trusted=True),
        record_time=True,
        exec_seconds=min(60.0, wall_seconds),
    )
    result, meta, rows = grader.run_in_sandbox(sandbox, job, wall_seconds=wall_seconds,
                                               cpu_seconds=cpu_seconds)
    stage = meta.get("stage")
    if stage != "done":
        detail = meta.get("error") or f"sandbox status {result.status}"
        return None, f"{which}: canonical solution {stage or 'produced no result'} ({detail})"
    if len(rows) != len(inputs):
        return None, (f"{which}: canonical solution completed {len(rows)}/{len(inputs)} inputs "
                      f"(sandbox status {result.status})")
    bad = [row for row in rows if row.get("status") != "ok"]
    if bad:
        first = bad[0]
        return None, (f"{which}: canonical solution failed on input {first.get('i')}: "
                      f"{first.get('status')} {first.get('error')}")
    payload = {
        "expected": [row["value"] for row in rows],
        "times": [row.get("seconds", 0.0) for row in rows],
        "inputs": len(inputs),
        "sandboxWallMs": result.wall_ms,
    }
    return payload, None


def prepare_java_suite(suite_name: str, force: bool = False, recompute: bool = False,
                       limit: int | None = None) -> dict:
    """Compile and run every canonical Java solution on the pinned JDK 8.

    For `humaneval-x-java` a task whose canonical fails is recorded in `_skipped.json` with the
    compiler diagnostic and excluded from scoring -- which also measures how Java-8-clean the
    dataset is. For the authored suite a failing canonical is a bug in the suite, so preparation
    refuses to ship (DESIGN-JAVA.md: "refuses to ship a suite with a failing canonical").
    """
    entry = suites.entry_for(suite_name)
    authored = bool(entry.get("authored"))
    print(f"suite {suite_name} (java, {'authored' if authored else entry.get('version')})")
    if entry.get("url"):
        info = download(entry["url"], suites.DATASET_DIR / entry["localName"],
                        entry.get("sha256"), entry.get("bytes"), force=force)
        print(f"  dataset {'downloaded' if info['downloaded'] else 'already cached'}: "
              f"{info['path']} (sha256 {info['sha256'][:16]}...)")
        dataset_sha = info["sha256"]
    else:
        dataset_sha = suites.authored_digest(suite_name)
        print(f"  authored suite digest {dataset_sha[:16]}...")

    box = java_sandbox.load()
    self_test = box.self_test()
    if not self_test["passed"]:
        raise SystemExit("java sandbox self-test failed:\n"
                         + json.dumps(self_test, indent=1))
    print(f"  java sandbox ok: {box.toolchain.record['javaVersion']} "
          f"profile {box.profile_sha256[:16]}...")

    tasks = suites.build_tasks(suite_name)
    if entry.get("tasks") and len(tasks) != entry["tasks"]:
        raise SystemExit(f"{suite_name} has {len(tasks)} tasks, datasets.json says "
                         f"{entry['tasks']}")
    if limit is not None:
        tasks = tasks[:limit]
    directory = suites.expected_dir(suite_name)
    directory.mkdir(parents=True, exist_ok=True)

    skipped: dict[str, str] = {}
    computed = reused = 0
    started = time.monotonic()
    check_counts: dict[str, int] = {}
    for index, task in enumerate(tasks, start=1):
        path = directory / f"{suites.safe_id(task.task_id)}.json"
        if path.exists() and not recompute:
            try:
                with path.open(encoding="utf-8") as handle:
                    cached = json.load(handle)
            except json.JSONDecodeError:
                cached = {}
            if cached.get("datasetSha256") == dataset_sha:
                reused += 1
                if cached.get("checks"):
                    check_counts[task.task_id] = cached["checks"].get("total", 0)
                continue
        sources = task.java_sources(task.canonical_java)
        compiled, ran = box.compile_and_run(sources)
        outcome = (java_grader.grade_checked(compiled, ran) if authored
                   else java_grader.grade_humaneval_x(compiled, ran))
        if not outcome.passed:
            reason = f"{outcome.failure_class}: {outcome.failure_detail}"
            if authored:
                raise SystemExit(
                    f"canonical solution for {task.task_id} does not pass its own tests on "
                    f"JDK 8 -- refusing to ship the suite.\n  {reason}\n"
                    f"  diagnostics: {compiled.diagnostics[:1500]}")
            skipped[task.task_id] = reason
            print(f"  [{index}/{len(tasks)}] {task.task_id} SKIPPED -- {reason[:220]}")
            path.unlink(missing_ok=True)
            continue
        if outcome.checks:
            check_counts[task.task_id] = outcome.checks.get("total", 0)
        record_payload = {
            "taskId": task.task_id,
            "suite": suite_name,
            "language": "java",
            "entryPoint": task.entry_point,
            "datasetSha256": dataset_sha,
            "canonicalPassesOnJdk8": True,
            "compileSeconds": compiled.seconds,
            "runSeconds": ran.seconds if ran else None,
            "checks": outcome.checks,
            "computedAt": now(),
            "toolchain": box.toolchain.describe(),
            "javaProfileSha256": box.profile_sha256,
        }
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(record_payload, handle)
        temporary.replace(path)
        computed += 1
        if computed % 20 == 0 or index == len(tasks):
            print(f"  [{index}/{len(tasks)}] verified={computed} reused={reused} "
                  f"skipped={len(skipped)} ({time.monotonic() - started:.0f}s)")

    skip_path = directory / "_skipped.json"
    existing = {} if recompute else suites.load_skipped(suite_name)
    merged = {**existing, **skipped}
    with skip_path.open("w", encoding="utf-8") as handle:
        json.dump({"suite": suite_name, "datasetSha256": dataset_sha, "updatedAt": now(),
                   "tasks": merged}, handle, indent=1)

    suite = suites.load(suite_name, require_expected=False)
    summary = {
        "suite": suite_name,
        "language": "java",
        "version": entry.get("version"),
        "datasetSha256": dataset_sha,
        "tasksInDataset": len(suites.build_tasks(suite_name)),
        "tasksPrepared": len(suite.tasks),
        "tasksVerifiedNow": computed,
        "tasksReusedFromCache": reused,
        "tasksSkipped": len(merged),
        "skipped": merged,
        "suiteDigest": suite.digest,
        "elapsedSeconds": round(time.monotonic() - started, 1),
        "javaToolchain": box.toolchain.describe(),
        "javaProfileSha256": box.profile_sha256,
    }
    if check_counts:
        summary["checksPerTask"] = check_counts
        summary["minChecksPerTask"] = min(check_counts.values())
        summary["totalChecks"] = sum(check_counts.values())
    print(f"  tasks in dataset : {summary['tasksInDataset']}")
    print(f"  canonical passes : {summary['tasksPrepared']} "
          f"(verified {computed}, reused {reused})")
    print(f"  skipped          : {summary['tasksSkipped']}")
    if check_counts:
        print(f"  hidden checks    : {summary['totalChecks']} total, "
              f"min {summary['minChecksPerTask']} per task")
    print(f"  suite digest     : {summary['suiteDigest']}")
    print(f"  elapsed          : {summary['elapsedSeconds']}s")
    return summary


def prepare_suite(suite_name: str, sandbox: SandboxExec, force: bool = False,
                  recompute: bool = False, wall_seconds: float = PREPARE_WALL_SECONDS,
                  cpu_seconds: int = PREPARE_CPU_SECONDS, limit: int | None = None) -> dict:
    entry = suites.entry_for(suite_name)
    print(f"suite {suite_name} (EvalPlus {entry.get('version')}, dataset {entry['dataset']})")

    if entry.get("url"):
        info = download(entry["url"], suites.DATASET_DIR / entry["localName"],
                        entry.get("sha256"), entry.get("bytes"), force=force)
        print(f"  dataset {'downloaded' if info['downloaded'] else 'already cached'}: "
              f"{info['path']} ({info['bytes']} bytes, sha256 {info['sha256'][:16]}...)")
    else:
        path = suites.dataset_path(suite_name)
        if not path.exists():
            raise SystemExit(f"local dataset missing: {path}")
        digest = suites.sha256_file(path)
        if entry.get("sha256") and digest != entry["sha256"]:
            raise SystemExit(f"{path} SHA-256 is {digest}, not {entry['sha256']}")
        info = {"downloaded": False, "path": str(path), "sha256": digest,
                "bytes": path.stat().st_size}
        print(f"  local dataset: {path} (sha256 {digest[:16]}...)")

    dataset_sha = info["sha256"]
    tasks = suites.build_tasks(suite_name)
    if entry.get("tasks") and len(tasks) != entry["tasks"]:
        raise SystemExit(f"{suite_name} has {len(tasks)} tasks, datasets.json says "
                         f"{entry['tasks']}")
    if limit is not None:
        tasks = tasks[:limit]
    directory = suites.expected_dir(suite_name)
    directory.mkdir(parents=True, exist_ok=True)

    skipped: dict[str, str] = {}
    existing = suites.load_skipped(suite_name) if not recompute else {}
    computed = reused = 0
    started = time.monotonic()
    base_inputs = plus_inputs = 0
    slowest: list[tuple[float, str]] = []

    for index, task in enumerate(tasks, start=1):
        path = directory / f"{suites.safe_id(task.task_id)}.json"
        if path.exists() and not recompute:
            try:
                with path.open(encoding="utf-8") as handle:
                    cached = json.load(handle)
            except json.JSONDecodeError:
                cached = {}
            if cached.get("datasetSha256") == dataset_sha:
                reused += 1
                base_inputs += (cached.get("base") or {}).get("inputs", 0)
                plus_inputs += (cached.get("plus") or {}).get("inputs", 0)
                continue
        if task.task_id in existing and not recompute:
            skipped[task.task_id] = existing[task.task_id]
            continue

        payloads: dict[str, dict] = {}
        reason = None
        for which in ("base", "plus"):
            payload, reason = compute_expected(sandbox, task, which, wall_seconds, cpu_seconds)
            if reason is not None:
                break
            payloads[which] = payload
        if reason is not None:
            skipped[task.task_id] = reason
            print(f"  [{index}/{len(tasks)}] {task.task_id} SKIPPED -- {reason}")
            path.unlink(missing_ok=True)
            continue

        record = {
            "taskId": task.task_id,
            "suite": suite_name,
            "dataset": task.dataset,
            "entryPoint": task.entry_point,
            "atol": task.atol,
            "datasetSha256": dataset_sha,
            "evalplusVersion": entry.get("version"),
            "notNoneMode": grader.not_none_mode_for(task.dataset, task.entry_point, trusted=True),
            "computedAt": now(),
            "sandbox": {"profileSha256": sandbox.profile_sha256,
                        "runnerSha256": runner_sha256(),
                        "python": sandbox.python,
                        "pythonVersion": sandbox.python_version()},
            "base": payloads["base"],
            "plus": payloads["plus"],
        }
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(record, handle)
        temporary.replace(path)
        computed += 1
        base_inputs += payloads["base"]["inputs"]
        plus_inputs += payloads["plus"]["inputs"]
        total_seconds = sum(payloads["plus"]["times"]) + sum(payloads["base"]["times"])
        slowest.append((total_seconds, task.task_id))
        if computed % 20 == 0 or index == len(tasks):
            print(f"  [{index}/{len(tasks)}] computed={computed} reused={reused} "
                  f"skipped={len(skipped)} ({time.monotonic() - started:.0f}s)")

    skip_path = directory / "_skipped.json"
    merged = dict(existing)
    merged.update(skipped)
    with skip_path.open("w", encoding="utf-8") as handle:
        json.dump({"suite": suite_name, "datasetSha256": dataset_sha, "updatedAt": now(),
                   "tasks": merged}, handle, indent=1)

    suite = suites.load(suite_name, require_expected=False)
    summary = {
        "suite": suite_name,
        "evalplusVersion": entry.get("version"),
        "datasetSha256": dataset_sha,
        "tasksInDataset": len(suites.build_tasks(suite_name)),
        "tasksPrepared": len(suite.tasks),
        "tasksComputedNow": computed,
        "tasksReusedFromCache": reused,
        "tasksSkipped": len(merged),
        "skipped": merged,
        "baseInputs": base_inputs,
        "plusInputs": plus_inputs,
        "suiteDigest": suite.digest,
        "elapsedSeconds": round(time.monotonic() - started, 1),
        "slowestCanonicalTasks": [
            {"taskId": task_id, "canonicalSeconds": round(seconds, 3)}
            for seconds, task_id in sorted(slowest, reverse=True)[:10]],
    }
    print(f"  tasks in dataset : {summary['tasksInDataset']}")
    print(f"  expected cached  : {summary['tasksPrepared']} "
          f"(computed {computed}, reused {reused})")
    print(f"  skipped          : {summary['tasksSkipped']}")
    print(f"  inputs per suite : base {base_inputs}, plus {plus_inputs}")
    print(f"  inputs per task  : base {base_inputs / max(1, summary['tasksPrepared']):.1f}, "
          f"plus {plus_inputs / max(1, summary['tasksPrepared']):.1f} (mean)")
    print(f"  suite digest     : {summary['suiteDigest']}")
    print(f"  elapsed          : {summary['elapsedSeconds']}s")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", action="append", default=[],
                        choices=suites.suite_names(),
                        help="repeatable; e.g. --suite humaneval-plus --suite mbpp-plus")
    parser.add_argument("--jdk", action="store_true",
                        help="download, verify and pin the Azul Zulu 8 JDK (Java suites need it)")
    parser.add_argument("--allow-unpinned-jdk", action="store_true",
                        help="fall back to trust-on-first-download if Azul's hash endpoint is "
                             "unreachable (documented fallback only)")
    parser.add_argument("--force-download", action="store_true",
                        help="re-download even if the cached file verifies")
    parser.add_argument("--recompute", action="store_true",
                        help="recompute expected outputs even when cached")
    parser.add_argument("--sandbox-python", help="interpreter to run inside the sandbox")
    parser.add_argument("--wall-seconds", type=float, default=PREPARE_WALL_SECONDS)
    parser.add_argument("--cpu-seconds", type=int, default=PREPARE_CPU_SECONDS)
    parser.add_argument("--limit", type=int, help="only prepare the first N tasks (smoke path)")
    parser.add_argument("--summary-json", type=Path, help="write the summary as JSON")
    args = parser.parse_args(argv)
    if not args.suite and not args.jdk:
        parser.error("nothing to do: pass --jdk and/or --suite")

    jdk_record = None
    if args.jdk:
        print("toolchain: Azul Zulu JDK 8 (macOS aarch64)")
        try:
            jdk_record = java_toolchain.prepare(
                allow_trust_on_first_download=args.allow_unpinned_jdk)
        except java_toolchain.ToolchainError as exc:
            print(f"jdk preparation failed: {exc}", file=sys.stderr)
            return 2
        parsed = jdk_record["parsedVersion"]
        print(f"  java -version : {jdk_record['javaVersionOutput'].splitlines()[0]}")
        print(f"  parsed        : {parsed['version']} (major {parsed['major']}, "
              f"isJava8={parsed['isJava8']})")
        print(f"  sha256        : {jdk_record['sha256']}")
        print(f"  hash source   : {jdk_record['hashSource']} "
              f"(verified={jdk_record['hashVerifiedAgainstPublishedValue']})")
        if not args.suite:
            return 0

    python_suites = [name for name in args.suite
                     if suites.entry_for(name).get("language", "python") == "python"]
    try:
        sandbox = SandboxExec(python=args.sandbox_python)
    except SandboxUnavailable as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2
    report = sandbox.self_test() if python_suites else {"skipped": "no python suites requested",
                                                        "passed": True}
    if not report["passed"]:
        print("sandbox self-test failed; refusing to execute any code:", file=sys.stderr)
        print(json.dumps(report, indent=1), file=sys.stderr)
        return 2
    if python_suites:
        print(f"sandbox self-test passed ({sandbox.python}, profile "
              f"{sandbox.profile_sha256[:16]}...)")

    summaries = []
    for suite_name in args.suite:
        if suites.entry_for(suite_name).get("language") == "java":
            try:
                summaries.append(prepare_java_suite(
                    suite_name, force=args.force_download, recompute=args.recompute,
                    limit=args.limit))
            except java_toolchain.ToolchainError as exc:
                print(f"java suite {suite_name} needs a prepared JDK: {exc}", file=sys.stderr)
                return 2
            continue
        summaries.append(prepare_suite(
            suite_name, sandbox, force=args.force_download, recompute=args.recompute,
            wall_seconds=args.wall_seconds, cpu_seconds=args.cpu_seconds, limit=args.limit))
    payload = {"preparedAt": now(), "sandboxSelfTest": report, "suites": summaries}
    if jdk_record:
        payload["javaToolchain"] = jdk_record
    if args.summary_json:
        args.summary_json.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        print(f"summary written to {args.summary_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
