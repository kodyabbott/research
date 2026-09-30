#!/usr/bin/env python3
"""Generate code from one model on one suite and grade it by executing hidden tests in a sandbox.

    python3 coding-benchmark-harness/run.py --backend ollama \\
        --endpoint http://127.0.0.1:11436 --model qwen3.8:27b-q8_0 \\
        --suite humaneval-plus --think false --label qwen3.8-27b-q8_0-off

    python3 coding-benchmark-harness/run.py --backend replay --suite fixture \\
        --replay-file coding-benchmark-harness/tests/fixtures/replay-responses.json \\
        --label fixture-replay

The sandbox self-test runs before any model code is executed and is stored in the record; the run
aborts if any check fails. There is no unsandboxed mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import HARNESS_VERSION, backends, extract, grader, record, suites  # noqa: E402
from harness.sandbox import SandboxExec, SandboxUnavailable, runner_sha256  # noqa: E402

RUNS_DIR = Path(__file__).resolve().parent / "runs"
DEFAULT_TASK_SECONDS = 300.0
DEFAULT_CPU_SECONDS = 60
DEFAULT_GRADE_WALL_SECONDS = 300.0


def output_cap_for(think: str, explicit: int | None) -> int:
    if explicit:
        return explicit
    # Reasoning tokens count against num_predict, so thinking-on needs far more room.
    return 4096 if think == "false" else 16384


def make_backend(args) -> backends.Backend:
    if args.backend == "replay":
        path = args.replay_file or (Path(__file__).resolve().parent
                                   / "tests/fixtures/replay-responses.json")
        return backends.ReplayBackend.from_file(
            path, think=args.think, output_cap=output_cap_for(args.think, args.output_cap),
            context=args.context, label=args.suite)
    if not args.endpoint:
        raise SystemExit("--endpoint is required for the ollama and openai backends")
    if not args.model:
        raise SystemExit("--model is required for the ollama and openai backends")
    return backends.build(
        args.backend, endpoint=args.endpoint, model=args.model, think=args.think,
        output_cap=output_cap_for(args.think, args.output_cap), context=args.context,
        request_timeout=args.task_seconds)


def grade_task(sandbox: SandboxExec, task: suites.Task, code: str, args) -> tuple[dict, dict]:
    """Run the candidate over the base inputs, then the plus inputs. Two sandbox invocations."""
    outcomes = {}
    for which in ("base", "plus"):
        raw_inputs = task.base_input if which == "base" else task.plus_input
        expected = task.expected_for(which)
        limits = grader.per_input_limits(task.times_for(which), len(raw_inputs))
        job = grader.build_job(
            code=code, entry_point=task.entry_point, task_id=task.task_id,
            dataset=task.dataset, inputs=raw_inputs, per_input_seconds=limits,
            not_none_mode=grader.not_none_mode_for(task.dataset, task.entry_point, trusted=False),
            record_time=False, exec_seconds=min(30.0, args.grade_wall_seconds))
        cpu_seconds, wall_seconds = grader.task_budget(
            task.reference_wall_seconds(which), args.cpu_seconds, args.grade_wall_seconds)
        result, meta, rows = grader.run_in_sandbox(
            sandbox, job, wall_seconds=wall_seconds, cpu_seconds=cpu_seconds)
        outcomes[which] = grader.grade_set(task.dataset, task.entry_point, task.task_id,
                                          raw_inputs, expected, task.atol, result, meta, rows)
        outcomes[which].sandbox["cpuSecondsAllowed"] = cpu_seconds
        outcomes[which].sandbox["wallSecondsAllowed"] = round(wall_seconds, 1)
        outcomes[which].sandbox["canonicalWallSeconds"] = round(
            task.reference_wall_seconds(which), 3)
        if which == "base" and not outcomes["base"].passed and args.stop_on_base_failure:
            outcomes["plus"] = grader.SetResult(
                inputs=len(task.plus_input), statuses="-" * len(task.plus_input),
                failure_class=outcomes["base"].failure_class,
                failure_detail="not run: base inputs already failed")
            break
    return outcomes["base"], outcomes["plus"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", required=True, choices=("ollama", "openai", "replay"))
    parser.add_argument("--endpoint", default=None,
                        help=f"required for live backends; port {backends.PRIMARY_PORT} is refused")
    parser.add_argument("--model")
    parser.add_argument("--suite", required=True, choices=suites.suite_names())
    parser.add_argument("--label", required=True)
    parser.add_argument("--think", default="false", choices=backends.THINK_MODES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", help="comma-separated task ids")
    parser.add_argument("--context", type=int, default=backends.DEFAULT_CONTEXT)
    parser.add_argument("--output-cap", type=int,
                        help="num_predict / max_tokens (default 4096 off, 16384 on)")
    parser.add_argument("--task-seconds", type=float, default=DEFAULT_TASK_SECONDS,
                        help="per-task generation timeout")
    parser.add_argument("--grade-wall-seconds", type=float, default=DEFAULT_GRADE_WALL_SECONDS,
                        help="wall timeout for one sandboxed grading invocation")
    parser.add_argument("--cpu-seconds", type=int, default=DEFAULT_CPU_SECONDS,
                        help="RLIMIT_CPU per sandboxed grading invocation")
    parser.add_argument("--sandbox-python")
    parser.add_argument("--replay-file", type=Path)
    parser.add_argument("--output", type=Path, help="override runs/<date>-<label>.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-on-base-failure", action="store_true",
                        help="skip the plus inputs when the base inputs already failed")
    parser.add_argument("--keep-loaded", action="store_true",
                        help="do not unload the model at the end")
    args = parser.parse_args(argv)

    # 1. Sandbox first: no model code runs, and no request is made, until this passes.
    try:
        sandbox = SandboxExec(python=args.sandbox_python)
    except SandboxUnavailable as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2
    self_test = sandbox.self_test()
    if not self_test["passed"]:
        print("sandbox self-test failed; refusing to execute model code:", file=sys.stderr)
        print(json.dumps(self_test, indent=1), file=sys.stderr)
        return 2
    print(f"sandbox ok: {sandbox.python} profile {sandbox.profile_sha256[:16]}...")

    # 2. Suite and expected outputs.
    try:
        suite = suites.load(args.suite, limit=args.limit,
                            ids=args.ids.split(",") if args.ids else None)
    except suites.SuiteError as exc:
        print(f"suite error: {exc}", file=sys.stderr)
        return 2
    print(f"suite {suite.name}: running {len(suite.tasks)} task(s); "
          f"{suite.total_tasks} in dataset, {len(suite.skipped)} skipped at prepare; "
          f"digest {suite.digest[:16]}...")

    # 3. Backend.
    try:
        backend = make_backend(args)
    except (backends.BackendError, SystemExit) as exc:
        print(f"backend error: {exc}", file=sys.stderr)
        return 2
    output_cap = output_cap_for(args.think, args.output_cap)

    try:
        model_info = backend.preflight()
    except backends.BackendError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2

    protocol = {
        **suite.protocol(),
        "think": args.think,
        "options": backend.describe().get("options"),
        "outputCap": output_cap,
        "context": args.context,
        "taskSeconds": args.task_seconds,
        "gradeWallSeconds": args.grade_wall_seconds,
        "cpuSeconds": args.cpu_seconds,
        "perTaskBudget": "max(--cpu-seconds, 4 x the canonical solution's measured sandbox wall "
                         "time for that input set); recorded per task under base/plus.sandbox",
        "samplingProfile": "greedy-v1",
        "samplesPerTask": 1,
        "perInputTimeout": "max(1.0s, 4 x canonical per-input time) -- EvalPlus "
                           "DEFAULT_MIN_TIME_LIMIT / DEFAULT_GT_TIME_LIMIT_FACTOR",
        "codeExecution": "sandbox-exec deny-default, see runtime.sandboxProfileSha256",
        "scope": f"{suite.name} pass@1 with one greedy sample per task; a task passes only when "
                 f"both the base and the plus inputs pass. Not a repository-editing agent eval.",
    }
    runtime = {
        "harness": HARNESS_VERSION,
        "backend": backend.name,
        "endpoint": getattr(backend, "endpoint", None),
        "sandboxPython": sandbox.python,
        "sandboxPythonVersion": sandbox.python_version(),
        "sandboxProfileSha256": sandbox.profile_sha256,
        "sandboxRunnerSha256": runner_sha256(),
        "sandboxSelfTest": self_test,
        "harnessPython": sys.version.split()[0],
    }

    path = args.output or (RUNS_DIR / f"{record.now()[:10].replace('-', '')}-{args.label}.json")
    try:
        run = record.RunRecord(path, args.label, protocol, runtime, model_info,
                               resume=args.resume)
    except record.RecordError as exc:
        print(f"record error: {exc}", file=sys.stderr)
        return 2
    done = run.completed_ids
    if done:
        print(f"resuming {path}: {len(done)} task(s) already recorded")
    print(f"writing {path}")

    status = "completed"
    error = None
    context_verified = None
    try:
        for index, task in enumerate(suite.tasks, start=1):
            if task.task_id in done:
                continue
            try:
                chat = backend.chat(task.prompt, task_id=task.task_id,
                                    seconds=args.task_seconds)
            except backends.BackendError as exc:
                status, error = "incomplete", str(exc)
                print(f"  {task.task_id}: generation failed -- {exc}", file=sys.stderr)
                break
            if context_verified is None:
                try:
                    context_verified = backend.verify_context()
                    run.data["model"]["contextCheck"] = context_verified
                except backends.BackendError as exc:
                    status, error = "error", str(exc)
                    print(f"  aborting: {exc}", file=sys.stderr)
                    break

            unexpected_thinking = args.think == "false" and bool(chat.thinking.strip())
            picked = extract.extract(chat.content, task.entry_point, task.source_prompt,
                                     allow_body_completion=task.allow_body_completion)
            entry = {
                "id": task.task_id,
                "prompt": task.prompt,
                "response": chat.as_record(),
                "wallMs": chat.wall_ms,
                "code": picked.code,
                "extractionRule": picked.rule,
                "completionPrefixed": picked.completion_prefixed,
                "truncated": chat.truncated,
                "unexpectedThinking": unexpected_thinking,
            }
            if chat.truncated:
                base = grader.SetResult(inputs=len(task.base_input),
                                        statuses="-" * len(task.base_input),
                                        failure_class="truncated",
                                        failure_detail=f"done_reason={chat.done_reason} at "
                                                       f"{output_cap} tokens")
                plus = grader.SetResult(inputs=len(task.plus_input),
                                        statuses="-" * len(task.plus_input),
                                        failure_class="truncated",
                                        failure_detail="not run: response was truncated")
            elif not picked.usable:
                base = grader.SetResult(inputs=len(task.base_input),
                                        statuses="-" * len(task.base_input),
                                        failure_class="no-code",
                                        failure_detail=picked.detail or picked.rule)
                plus = grader.SetResult(inputs=len(task.plus_input),
                                        statuses="-" * len(task.plus_input),
                                        failure_class="no-code",
                                        failure_detail="not run: no code extracted")
            else:
                base, plus = grade_task(sandbox, task, picked.code, args)

            failure_class, failure_detail = grader.combine_failure_class(base, plus)
            entry.update(base=base.as_dict(), plus=plus.as_dict(),
                         failureClass=failure_class, failureDetail=failure_detail)
            run.add_task(entry)
            rate = chat.gen_tok_per_sec
            rate_text = f"{rate:8.1f} tok/s" if rate else "     n/a tok/s"
            print(f"  [{index}/{len(suite.tasks)}] {task.task_id:<16} "
                  f"base={'ok  ' if base.passed else 'fail'} "
                  f"plus={'ok  ' if plus.passed else 'fail'} {failure_class:<13} "
                  f"{rate_text} {chat.wall_ms / 1000:6.1f}s", flush=True)
        if status == "completed" and len(run.data["tasks"]) < len(suite.tasks):
            status = "incomplete"
    except KeyboardInterrupt:
        status, error = "incomplete", "interrupted by the operator"
    except Exception as exc:  # noqa: BLE001 - recorded, then re-raised context is printed
        status, error = "error", repr(exc)
        print(f"run failed: {exc!r}", file=sys.stderr)
    finally:
        run.set_status(status, error)
        if not args.keep_loaded:
            try:
                run.data["unload"] = backend.unload()
            except backends.BackendError as exc:
                run.data["unload"] = {"confirmed": False, "error": str(exc)}
                if status == "completed":
                    run.set_status("error", f"unload failed: {exc}")
                    status = "error"
        summary = run.summarize(len(suite.tasks))
        run.finish(status)

    print(f"{args.label}: {summary['plusPass']}/{summary['tasksTotal']} pass@1 "
          f"(base {summary['basePass']}), classes {summary['failureClasses']}, "
          f"median {summary['medianGenTokPerSec']} tok/s, status {status}, "
          f"protocolValid={summary['protocolValid']}")
    print(f"record: {path}")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
