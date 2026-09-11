"""Run the reviewed overnight queue sequentially; heartbeats inspect and adapt it."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import campaign
import background
from nightly import atomic_json, now, read_json, state_lock
from owned_runtime import process_identity

ROOT = Path(__file__).resolve().parent
QUEUE = 'campaign-20260910-queue.json'


def advance(root=ROOT, launch=None, inspect=None, queue_name=QUEUE):
    root = Path(root)
    launch = launch or campaign.launch
    inspect = inspect or background.status
    with contextlib.ExitStack() as locks:
        try:
            locks.enter_context(state_lock(root / 'state' / (queue_name + '.lock')))
        except RuntimeError as exc:
            return {'status': 'busy', 'reason': 'Queue update in progress: ' + str(exc)}
        path = root / 'state' / queue_name
        queue = read_json(path)
        if queue.get('status') in ('cancelled', 'stopped', 'paused'):
            return {'status': 'stopped', 'reason': 'Queue is ' + queue['status']}
        active = [x for x in queue['items'] if x['status'] == 'running']
        if len(active) > 1:
            raise RuntimeError('Multiple active queue entries; inspect before proceeding')
        if active:
            row = active[0]
            with contextlib.redirect_stdout(io.StringIO()) as output:
                inspect(row['runId'])
            status = json.loads(output.getvalue())
            if status['status'] in ('queued', 'running'):
                return {'status': 'waiting', 'runId': row['runId']}
            report = read_json(root / 'runs' / (row['runId'] + '.json'))
            row.update(status=status['status'], finishedAt=report.get('finishedAt'),
                comparisonValid=report.get('comparison', {}).get('valid'),
                reason=report.get('error') or report.get('reason') or report.get('comparison', {}).get('invalidReason'))
            atomic_json(path, queue)
        pending = [x for x in queue['items'] if x['status'] == 'pending']
        if not pending:
            return {'status': 'queue-complete'}
        try:
            campaign.validate_authorization(root, root / queue['authorizationFile'])
        except ValueError as exc:
            return {'status': 'stopped', 'reason': str(exc)}
        row = pending[0]
        prefetch_active = False
        for prefetch_file in (root/'state').glob('prefetch-*.job.json'):
            job = read_json(prefetch_file, {})
            if job.get('processIdentity') and process_identity(job['pid']) == job['processIdentity']:
                prefetch_active = True
                break
        if prefetch_active:
            runnable = [item for item in pending if read_json(root/item['selectionFile'], {}).get('kind') == 'installed']
            if not runnable:
                return {'status': 'waiting-prefetch', 'reason': 'Imports wait for artifact prefetch to finish'}
            row = runnable[0]
        try:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                launch(root / queue['authorizationFile'], root / row['selectionFile'])
            job = json.loads(output.getvalue())
            if job.get('status') != 'started' or not job.get('runId'):
                raise RuntimeError('Launcher did not confirm a job')
        except RuntimeError as exc:
            # A final supervisor may take a moment to exit after writing its result.
            # The launcher remains authoritative about active jobs and operation locks.
            return {'status': 'busy', 'reason': str(exc)}
        row.update(status='running', runId=job['runId'], launchedAt=now())
        atomic_json(path, queue)
        return {'status': 'started', 'id': row['id'], 'runId': row['runId']}


def worker(queue_name=QUEUE):
    record_path = ROOT / 'state' / (queue_name + '.controller.json')
    with state_lock(ROOT / 'state' / (queue_name + '.controller.lock')):
        record = {'pid': os.getpid(), 'processIdentity': process_identity(os.getpid()),
                  'startedAt': now(), 'status': 'running'}
        atomic_json(record_path, record)
        try:
            while True:
                result = advance(queue_name=queue_name)
                record.update(lastStep=result, updatedAt=now())
                atomic_json(record_path, record)
                print(json.dumps(result), flush=True)
                if result['status'] in ('queue-complete', 'stopped'):
                    record.update(status=result['status'], finishedAt=now())
                    atomic_json(record_path, record)
                    return
                time.sleep(10)
        except Exception as exc:
            record.update(status='error', error=str(exc), finishedAt=now())
            atomic_json(record_path, record)
            raise


def launch_controller(queue_name=QUEUE):
    path = ROOT / 'state' / (queue_name + '.controller.json')
    record = read_json(path, {})
    if record.get('pid') and record.get('processIdentity') == process_identity(record['pid']):
        raise RuntimeError('Campaign controller is already active')
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0
    with (ROOT/'state'/(queue_name + '.controller.log')).open('ab') as output:
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', '--queue', queue_name],
            stdin=subprocess.DEVNULL, stdout=output, stderr=output, close_fds=True,
            creationflags=flags, start_new_session=os.name != 'nt', env=dict(os.environ, PYTHONUTF8='1'))
    print(json.dumps({'status': 'started', 'pid': process.pid, 'processIdentity': process_identity(process.pid)}))


if __name__ == '__main__':
    import argparse
    import re
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue',default=QUEUE)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--launch',action='store_true')
    group.add_argument('--worker',action='store_true')
    group.add_argument('--advance',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'campaign-[a-z0-9-]+-queue\.json',args.queue):
        parser.error('Queue must be a campaign JSON basename')
    if args.launch: launch_controller(args.queue)
    elif args.worker: worker(args.queue)
    else: print(json.dumps(advance(queue_name=args.queue)))
