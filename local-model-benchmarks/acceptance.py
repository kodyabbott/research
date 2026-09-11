"""Human-invoked live acceptance checks. Never called by the nightly task.

The fixture uses the real admission path and a separate bounded validation ledger (three distinct fixtures per day).
The deadline smoke reuses that imported fixture; it performs no download or import.
"""
import argparse
from pathlib import Path
import sys
import time

import nightly
from owned_runtime import secondary


def timeout_worker(run_id):
    h = nightly.Harness(Path(__file__).parent)
    h.run_id = run_id
    h.report.update(runId=run_id, mode='acceptance-deadline-smoke')
    with nightly.state_lock(h.state / 'operation.lock'):
        h.wait_idle()
        h.report['gpuBefore'] = h.gpu()
        imports = nightly.read_json(h.state / 'imports.json', {})
        eligible = [name for name, item in imports.items() if item.get('completedRun') and item.get('bytes', 3 * nightly.GIB) <= 2 * nightly.GIB]
        if not eligible:
            raise RuntimeError('Run the small acceptance fixture successfully first')
        model = eligible[-1]
        with secondary(h):
            if h.installed().get(model, {}).get('digest') != imports[model]['digest']:
                raise RuntimeError('Acceptance fixture digest changed')
            h.api('chat', {'model': model, 'messages': [{'role': 'user', 'content': 'Reply ready.'}],
                          'stream': False, 'think': False, 'keep_alive': '5m',
                          'options': {'num_ctx': 8192, 'num_predict': 32}}, timeout=60)
            h.report['loadedForDeadlineTest'] = h.api('ps').get('models')
            h.save_report()
            while True:
                time.sleep(1)  # deliberately stalled worker; parent must kill its whole tree


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--fixture', type=Path)
    group.add_argument('--deadline-smoke', action='store_true')
    group.add_argument('--timeout-worker')
    args = parser.parse_args()
    if args.timeout_worker:
        timeout_worker(args.timeout_worker)
    elif args.fixture:
        sys.exit(nightly.supervised(['--acceptance-fixture', str(args.fixture)]))
    else:
        sys.exit(nightly.supervised([], worker_command=lambda run_id:
            [sys.executable, str(Path(__file__).resolve()), '--timeout-worker', run_id], timeout=30))
