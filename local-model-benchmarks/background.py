"""Short shell calls launch and inspect a supervised nightly job on Windows."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from owned_runtime import process_identity


def launch(selection):
    from nightly import Harness, atomic_json, state_lock
    h = Harness(Path(__file__).parent)
    try:
        with state_lock(h.state / 'operation.lock'):
            pass
    except RuntimeError:
        print(json.dumps({'status': 'deferred', 'reason': 'Another benchmark operation is already active; no job launched'}))
        return
    selection = Path(selection).resolve(strict=True)
    jobs = h.state / 'jobs'
    jobs.mkdir(parents=True, exist_ok=True)
    h.report.update(mode='nightly', status='queued')
    h.save_report()
    output, errors = jobs / (h.run_id + '.stdout.json'), jobs / (h.run_id + '.stderr.log')
    with output.open('wb') as stdout, errors.open('wb') as stderr:
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('nightly.py')),
            '--supervisor', h.run_id, '--run-candidate', str(selection)], stdout=stdout, stderr=stderr,
            stdin=subprocess.DEVNULL, close_fds=True, creationflags=flags,
            start_new_session=os.name != 'nt', env=dict(os.environ, PYTHONUTF8='1'))
    job = {'runId': h.run_id, 'pid': process.pid, 'processIdentity': process_identity(process.pid),
           'resultFile': h.report['resultFile'], 'stdoutFile': str(output), 'stderrFile': str(errors)}
    atomic_json(jobs / (h.run_id + '.json'), job)
    print(json.dumps({'status': 'started', **job}))


def status(run_id, wait_seconds=0):
    from nightly import Harness, read_json, state_lock
    if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}', run_id):
        raise ValueError('Invalid run ID')
    h = Harness(Path(__file__).parent)
    path = h.root / 'runs' / (run_id + '.json')
    job = read_json(h.state / 'jobs' / (run_id + '.json'), {})
    until = time.monotonic() + min(55, wait_seconds)
    while True:
        report = read_json(path)
        if not report:
            raise ValueError('No saved result for this run')
        if report.get('status') not in ('queued', 'running'):
            break
        if job.get('processIdentity') and process_identity(job['pid']) != job['processIdentity']:
            try:
                with state_lock(h.state / 'operation.lock'):
                    report = read_json(path)
                    if report.get('status') in ('queued', 'running'):
                        h.run_id, h.report = run_id, report
                        h.report.update(status='error', error='Supervisor exited before a terminal result; next run checks for an owned orphan')
                        h.save_report()
                        h.finish_reservation()
            except RuntimeError:
                report['monitorWarning'] = 'Supervisor is absent; an operation still holds the lock'
            if report.get('status') == 'error':
                break
        if time.monotonic() >= until:
            break
        time.sleep(min(5, max(0, until - time.monotonic())))
    print(json.dumps({'runId': run_id, 'status': report['status'], 'resultFile': 'runs/' + path.name,
                      'error': report.get('error'), 'reason': report.get('reason'),
                      'monitorWarning': report.get('monitorWarning')}))
