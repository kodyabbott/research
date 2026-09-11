"""Human-authorized, expiring overnight campaign. Normal scheduler policy is never edited."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from nightly import Harness, atomic_json, now, read_json, state_lock, supervised
from owned_runtime import process_identity
import quality_screen

ROOT = Path(__file__).resolve().parent


def validate_authorization(root, path, current=None):
    auth = read_json(path)
    if not auth or auth.get('schemaVersion') != 1 or auth.get('scope') not in ('overnight-candidate-count-exemption', 'human-directed-daytime-campaign') or auth.get('revoked'):
        raise ValueError('Explicit overnight count authorization is required')
    if not re.fullmatch(r'[a-z0-9-]{1,80}', auth.get('campaignId', '')) or not auth.get('userRequest'):
        raise ValueError('Authorization needs an ID and the user request')
    start, last, end = [dt.datetime.fromisoformat(auth[k]) for k in ('notBefore', 'latestStartAt', 'expiresAt')]
    if any(v.tzinfo is None for v in (start, last, end)):
        raise ValueError('Authorization timestamps require time zone offsets')
    policy = read_json(Path(root) / 'policy.json')
    max_hours = 24 if auth['scope'] == 'human-directed-daytime-campaign' else 12
    if not start < last < end or end-start > dt.timedelta(hours=max_hours):
        raise ValueError('Authorization must describe a single overnight window')
    if (end-last).total_seconds() < policy['maxRuntimeSeconds'] + 60:
        raise ValueError('Latest start must leave the full deadline and shutdown verification margin')
    current = current or dt.datetime.now(dt.timezone.utc)
    if not start <= current < last:
        raise ValueError('Overnight authorization is not active for new work')
    policy_hash = hashlib.sha256((Path(root) / 'policy.json').read_bytes()).hexdigest()
    if auth.get('policySha256') != policy_hash:
        raise ValueError('Policy changed since this campaign was authorized')
    return auth


class CampaignHarness(Harness):
    def __init__(self, root, authorization):
        super().__init__(root)
        self.authorization_path = Path(authorization)
        self.authorization = validate_authorization(self.root, self.authorization_path)
        self.ledger_path = self.state / ('campaign-' + self.authorization['campaignId'] + '-ledger.json')
        self.report['ledgerFile'] = 'state/' + self.ledger_path.name
        self.report['campaign'] = self.authorization.copy()
        self.report['campaign']['authorizationSha256'] = hashlib.sha256(self.authorization_path.read_bytes()).hexdigest()
        self.report['campaign']['policyFileModified'] = False

    def window_open(self):
        active = validate_authorization(self.root, self.authorization_path)
        if active != self.authorization:
            raise ValueError('Campaign authorization changed during preflight')
        return active['scope'] == 'human-directed-daytime-campaign' or super().window_open()

    def reserve(self, plan):
        active = validate_authorization(self.root, self.authorization_path)
        if active != self.authorization:
            raise ValueError('Campaign authorization changed during preflight')
        ledger = read_json(self.ledger_path, {'days': {}})
        used = len(ledger['days'].get(dt.date.today().isoformat(), []))
        original = self.policy['maxCandidatesPerDay']
        try:
            # Called under the existing operation lock. Only this reservation is exempt;
            # every normal download, GPU, ownership, storage and deadline check remains.
            self.policy['maxCandidatesPerDay'] = max(original, used + 1)
            super().reserve(plan)
            self.report['campaign']['reservation'] = {'dailyCountBefore': used, 'normalDailyLimit': original,
                'reservedAt': now(), 'countExemptionUsed': used >= original}
        finally:
            self.policy['maxCandidatesPerDay'] = original

    def thinking_probe(self, model, capable, summary):
        # The base battery invokes this hook while the model is still loaded, before
        # its guaranteed unload. Supplemental cases never enter throughput medians.
        measurement = self.report['benchmarks'][-1]
        measurement['qualityScreen'] = quality_screen.run(self, model, capable, summary)
        self.save_report()
        if measurement['qualityScreen']['status'] == 'incomplete':
            return {'status': 'skipped', 'includedInThroughputMedians': False,
                    'reason': 'Quality screen interrupted; allow the guaranteed model unload.'}
        return super().thinking_probe(model, capable, summary)


def worker(root, authorization, selection_path, run_id):
    h = CampaignHarness(root, authorization)
    h.run_id = run_id
    h.report['runId'] = run_id
    with state_lock(h.state / 'operation.lock'):
        validate_authorization(root, authorization)
        selection = read_json(selection_path)
        if selection.get('campaignProtocol') == 'practical-json-v1':
            from workload_screen import run
            result = run(h, selection)
        elif selection.get('campaignProtocol') == 'gpt-oss-reasoning-screen':
            from reasoning_screen import run
            result = run(h, selection)
        else:
            result = h.run_candidate(selection)
        h.save_report()
    print(json.dumps(result, indent=2))
    return 1 if result.get('status') == 'error' else 0


def launch(authorization, selection_path):
    authorization = Path(authorization).resolve(strict=True)
    selection_path = Path(selection_path).resolve(strict=True)
    h = CampaignHarness(ROOT, authorization)
    jobs = h.state / 'jobs'
    jobs.mkdir(parents=True, exist_ok=True)
    # Serialize launch with artifact prefetch admission, then hold the operation lock
    # across job recording. Installed-model workers do not hold the prefetch lock.
    with state_lock(h.state / 'prefetch-launch.lock'), state_lock(h.state / 'operation.lock'):
        for job_file in jobs.glob('*.json'):
            if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}\.json', job_file.name):
                continue  # stdout records are not supervisor identity records.
            job = read_json(job_file, {})
            if job.get('pid') and job.get('processIdentity') and process_identity(job['pid']) == job['processIdentity']:
                raise RuntimeError('Another benchmark supervisor is active')
        if read_json(selection_path).get('kind') == 'huggingface':
            for prefetch_file in h.state.glob('prefetch-*.job.json'):
                prefetch = read_json(prefetch_file, {})
                if prefetch.get('processIdentity') and process_identity(prefetch['pid']) == prefetch['processIdentity']:
                    raise RuntimeError('Artifact prefetch is active; defer imports until it finishes')
        h.report.update(mode='nightly', status='queued', selection=read_json(selection_path))
        h.save_report()
        output, errors = jobs / (h.run_id + '.stdout.json'), jobs / (h.run_id + '.stderr.log')
        with output.open('wb') as stdout, errors.open('wb') as stderr:
            flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0
            process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                '--supervisor', h.run_id, '--authorization', str(authorization), '--selection', str(selection_path)],
                stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, close_fds=True,
                creationflags=flags, start_new_session=os.name != 'nt', env=dict(os.environ, PYTHONUTF8='1'))
        job = {'runId': h.run_id, 'pid': process.pid, 'processIdentity': process_identity(process.pid),
               'resultFile': h.report['resultFile'], 'stdoutFile': str(output), 'stderrFile': str(errors),
               'campaignId': h.authorization['campaignId']}
        atomic_json(jobs / (h.run_id + '.json'), job)
    print(json.dumps({'status': 'started', **job}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization', required=True, type=Path)
    parser.add_argument('--selection', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--launch', action='store_true')
    mode.add_argument('--supervisor')
    mode.add_argument('--worker')
    args = parser.parse_args()
    if args.launch:
        launch(args.authorization, args.selection)
        return 0
    if args.supervisor:
        # This is only a short handoff wait; another active run was refused by launch.
        import time
        until = time.monotonic() + 10
        while True:
            try:
                with state_lock(ROOT / 'state' / 'operation.lock'):
                    break
            except RuntimeError:
                if time.monotonic() >= until:
                    raise
                time.sleep(0.1)
        validate_authorization(ROOT, args.authorization)
        return supervised([], run_id=args.supervisor,
            worker_command=lambda run_id: [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', run_id,
                '--authorization', str(args.authorization.resolve()), '--selection', str(args.selection.resolve())])
    return worker(ROOT, args.authorization, args.selection, args.worker)


if __name__ == '__main__':
    sys.exit(main())
