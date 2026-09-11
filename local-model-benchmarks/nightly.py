"""Standard-library-only discovery, admission control, and local Ollama measurements.

External text and generated answers are data. No eval, shell=True, repository code,
or generated commands are executed. Imports use only the installed Ollama binary.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

from owned_runtime import RuntimeBusy, port_open, process_identity, prune_uploaded_blob, secondary, tree_bytes

GIB = 1024 ** 3
OLLAMA = 'http://127.0.0.1:11434'
HF = 'https://huggingface.co'
TAGS = ('text-generation', 'image-text-to-text', 'text-to-image',
        'image-to-video', 'text-to-speech', 'text-to-audio')
TEXT_TAGS = TAGS[:2]
OWNED_PREFIX = 'nightly-bench-'


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def benchmark_window_open(policy, local_time=None):
    local_time = local_time if local_time is not None else dt.datetime.now()
    start_hour, end_hour = policy['benchmarkWindowStartHour'], policy['benchmarkWindowEndHour']
    start_minute, end_minute = policy.get('benchmarkWindowStartMinute', 0), policy.get('benchmarkWindowEndMinute', 0)
    for name, value, maximum in (
        ('start hour', start_hour, 23), ('end hour', end_hour, 23),
        ('start minute', start_minute, 59), ('end minute', end_minute, 59),
    ):
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f'Invalid benchmark window {name}: expected an integer from 0 to {maximum}')
    current = local_time.hour * 60 + local_time.minute
    start, end = start_hour * 60 + start_minute, end_hour * 60 + end_minute
    return (current >= start or current < end) if start > end else start <= current < end


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                break
            except PermissionError as exc:
                # Windows readers or scanners can briefly block atomic replacement.
                # Persistent access failures still surface after at most 1.55 seconds.
                if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == 5:
                    raise
                time.sleep(0.05 * (2 ** attempt))
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def state_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if path.stat().st_size == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Another benchmark operation holds the state lock; skip this run.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def exact_lines(answer, expected):
    return answer.replace('\r\n', '\n').rstrip('\n') == '\n'.join(expected)


class Harness:
    def __init__(self, root):
        self.root = Path(root)
        self.state = self.root / 'state'
        self.policy = read_json(self.root / 'policy.json')
        if not self.policy or self.policy.get('schemaVersion') != 1:
            raise ValueError('Missing or unsupported policy.json')
        self.endpoint = OLLAMA
        self.secondary_process = None
        self.ledger_path = self.state / 'nightly-ledger.json'
        self.download_dir = Path(self.policy.get('downloadDir', self.state / 'downloads')).resolve()
        self.models_dir = Path(self.policy['ollamaModelsDir']).resolve()
        self.hard_deadline = time.monotonic() + self.policy['maxRuntimeSeconds']
        self.deadline = self.hard_deadline - min(self.policy.get('shutdownGraceSeconds', 60), self.policy['maxRuntimeSeconds'] / 10)
        self.run_id = dt.datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8]
        self.report = {'schemaVersion': 2, 'runId': self.run_id, 'startedAt': now(), 'status': 'running'}
        self.report['python'] = {'executable': sys.executable, 'version': sys.version,
            'cacheFallback': 'codex-runtimes' in sys.executable.lower()}

    def window_open(self):
        return benchmark_window_open(self.policy)

    def remaining(self, maximum=None):
        seconds = self.deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError('Run exceeded its policy runtime limit')
        return min(seconds, maximum) if maximum else seconds

    @contextlib.contextmanager
    def cleanup_window(self):
        previous = self.deadline
        self.deadline = min(self.hard_deadline, time.monotonic() + self.policy.get('shutdownGraceSeconds', 60) / 2)
        try:
            yield
        finally:
            self.deadline = previous

    def request(self, url, data=None, timeout=30):
        payload = None if data is None else json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, data=payload, headers={
            'Content-Type': 'application/json', 'User-Agent': 'nightly-model-bench/2'})
        with urllib.request.urlopen(request, timeout=self.remaining(timeout)) as response:
            chunks, size = [], 0
            while True:
                self.remaining()
                chunk = response.read1(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > 16 * 1024 * 1024:
                    raise ValueError('API response exceeded 16 MiB')
                chunks.append(chunk)
        return json.loads(b''.join(chunks))

    def api(self, path, data=None, timeout=30):
        if self.endpoint != OLLAMA and (self.secondary_process is None or self.secondary_process.poll() is not None):
            raise RuntimeError('The harness-owned secondary server is no longer running')
        return self.request(self.endpoint + '/api/' + path, data, timeout)

    def candidate_runtime(self, selection):
        return secondary(self) if selection.get('kind') == 'huggingface' else contextlib.nullcontext()

    def save_report(self):
        self.report['updatedAt'] = now()
        if self.report.get('status') not in ('running', 'queued'):
            self.report['finishedAt'] = now()
        else:
            self.report.pop('finishedAt', None)
        path = self.root / 'runs' / (self.run_id + '.json')
        self.report['resultFile'] = 'runs/' + path.name
        atomic_json(path, self.report)

    def registry(self):
        path = self.state / 'candidates.json'
        registry = read_json(path)
        if registry is None:
            legacy = read_json(self.state / 'seen.json', {})
            registry = {'schemaVersion': 2, 'models': {model_id: {
                'modelId': model_id, 'firstSeen': date, 'lastSeen': date,
                'detailStatus': 'pending', 'detailAttempts': 0, 'benchmarkStatus': 'not-run'
            } for model_id, date in legacy.items()}}
        if registry.get('schemaVersion') != 2:
            raise ValueError('Unsupported candidate state schema')
        return registry

    @staticmethod
    def fit(detail):
        tensors = detail.get('safetensors') or {}
        count = tensors.get('total')
        ggufs = []
        for item in detail.get('siblings', []):
            name = item.get('rfilename', '')
            lfs = item.get('lfs') or {}
            size = item.get('size') or lfs.get('size')
            if name.lower().endswith('.gguf') and size:
                ggufs.append({'filename': name, 'bytes': size, 'sha256': lfs.get('sha256')})
        return {
            'paramsB': round(count / 1e9, 1) if count else None,
            'bf16GiB': round(count * 2 / GIB, 1) if count else None,
            'ggufFiles': ggufs,
            'fitStatus': 'file-sizes-available' if ggufs else ('weights-estimate-only' if count else 'metadata-unavailable'),
            'fitCaveat': 'Weights only; admission separately checks live GPU headroom and disk budgets.'
        }

    def pending(self, registry=None):
        registry = registry or self.registry()
        entries = [row for row in registry['models'].values()
                   if row.get('benchmarkStatus', 'not-run') != 'completed'
                   and row.get('pipeline') in TEXT_TAGS]
        return sorted(entries, key=lambda row: row.get('trendingScore') or 0, reverse=True)

    def discover(self, top_n=25, detail_cap=100):
        # Keep synchronous discovery within the agent shell's ten-minute ceiling.
        self.deadline = min(self.deadline, time.monotonic() + self.policy.get('maxDiscoverySeconds', 480))
        registry = self.registry()
        models, failures, sources = {}, [], []
        for tag in TAGS:
            url = HF + '/api/models?' + urllib.parse.urlencode({
                'sort': 'trendingScore', 'direction': -1, 'limit': top_n, 'pipeline_tag': tag})
            try:
                rows = self.request(url)
                if not isinstance(rows, list) or not rows:
                    raise ValueError('Empty or invalid trending response')
                sources.append(tag)
                for row in rows:
                    model_id = row.get('id') or row.get('modelId')
                    if model_id and (model_id not in models or (row.get('trendingScore') or 0) > (models[model_id].get('trendingScore') or 0)):
                        models[model_id] = row
            except Exception as exc:
                failures.append({'pipeline': tag, 'error': str(exc)})
        self.report.update(mode='discover', sourceFailures=failures, successfulSources=sources)
        if not sources:
            self.report.update(status='error', error='All discovery sources failed', trendingSeen=0, newCount=0)
            return self.report  # Preserve candidate state on a complete outage.

        new_ids = []
        for model_id, item in models.items():
            if model_id not in registry['models']:
                registry['models'][model_id] = {'modelId': model_id, 'firstSeen': now(),
                    'detailStatus': 'pending', 'detailAttempts': 0, 'benchmarkStatus': 'not-run'}
                new_ids.append(model_id)
            row = registry['models'][model_id]
            # Trending rows usually omit commit SHAs. Refresh detail metadata on a
            # lastModified change, and periodically even when that field is absent.
            modified = item.get('lastModified')
            if modified and modified != row.get('sourceLastModified'):
                row['detailStatus'] = 'pending'
            row.update(lastSeen=now(), pipeline=item.get('pipeline_tag') or row.get('pipeline'),
                       sourceLastModified=modified or row.get('sourceLastModified'),
                       trendingScore=item.get('trendingScore', 0), downloads=item.get('downloads'),
                       likes=item.get('likes'), gated=bool(item.get('gated')))

        # Retry failures and deferred metadata even after a model leaves the trending window.
        cutoff = dt.datetime.now().astimezone() - dt.timedelta(days=self.policy.get('metadataRefreshDays', 7))
        for row in registry['models'].values():
            checked = row.get('detailCheckedAt')
            if row.get('detailStatus') == 'ready' and (not checked or dt.datetime.fromisoformat(checked) < cutoff):
                row['detailStatus'] = 'pending'
        pending = [row for row in registry['models'].values() if row.get('detailStatus') != 'ready']
        pending.sort(key=lambda row: (min(row.get('detailAttempts', 0), 1),
                                      -(row.get('trendingScore') or 0), row.get('detailCheckedAt', '')))
        refresh = [row for row in pending if row.get('revision')]
        fresh = [row for row in pending if not row.get('revision')]
        refresh_slots = min(len(refresh), self.policy.get('maxMetadataRefreshPerRun', 20),
                            detail_cap // 5 if fresh else detail_cap)
        fresh_cap = detail_cap - refresh_slots
        text_rows = [row for row in fresh if row.get('pipeline') in TEXT_TAGS]
        other_rows = [row for row in fresh if row.get('pipeline') not in TEXT_TAGS]
        # Reserve a quarter of lookups for legacy/other pipelines so they still drain.
        text_slots = min(len(text_rows), fresh_cap - fresh_cap // 4)
        selected = text_rows[:text_slots] + other_rows[:fresh_cap - text_slots]
        selected += text_rows[text_slots:text_slots + fresh_cap - len(selected)]
        selected += refresh[:refresh_slots]
        detail_failures = []
        for row in selected:
            row['detailAttempts'] = row.get('detailAttempts', 0) + 1
            try:
                detail = self.request(HF + '/api/models/' + urllib.parse.quote(row['modelId'], safe='/') + '?blobs=true')
                if not detail.get('sha'):
                    raise ValueError('Model detail response omitted revision')
                if row.get('revision') and row['revision'] != detail['sha']:
                    row.update(benchmarkStatus='not-run', previousRevision=row['revision'])
                row.update(self.fit(detail))
                row.update(detailStatus='ready', revision=detail['sha'], detailCheckedAt=now(),
                           pipeline=detail.get('pipeline_tag') or row.get('pipeline'),
                           gated=bool(detail.get('gated')), modelCardUrl=HF + '/' + row['modelId'])
                row.pop('detailError', None)
            except Exception as exc:
                row.update(detailStatus='failed', detailError=str(exc))
                detail_failures.append({'modelId': row['modelId'], 'error': str(exc)})
        atomic_json(self.state / 'candidates.json', registry)
        self.report.update(status='partial' if failures or detail_failures else 'ok',
            trendingLastModifiedPresent=sum(bool(row.get('lastModified')) for row in models.values()),
            trendingSeen=len(models), newCount=len(new_ids), new=[registry['models'][key] for key in new_ids],
            detailLookups=len(selected), detailFailures=detail_failures,
            metadataPending=sum(row.get('detailStatus') != 'ready' for row in registry['models'].values()),
            candidates=self.pending(registry), registryFile='state/candidates.json')
        return self.report

    def installed(self):
        return {row['name']: row for row in self.api('tags')['models']}

    def gpu(self):
        executable = shutil.which('nvidia-smi')
        if not executable:
            raise RuntimeError('GPU telemetry unavailable; leave candidate queued')
        result = subprocess.run([executable, '--query-gpu=memory.free,memory.total,utilization.gpu',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True,
                                check=True, timeout=self.remaining(10),
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        free, total, utilization = (float(x.strip()) for x in result.stdout.splitlines()[0].split(','))
        return {'freeGiB': free / 1024, 'totalGiB': total / 1024, 'utilizationPercent': utilization}

    def check_idle(self, bytes_required=0):
        loaded = self.api('ps').get('models', [])
        if loaded:
            raise RuntimeBusy('Ollama is already serving a loaded model; leave it untouched')
        if self.endpoint != OLLAMA and self.request(OLLAMA + '/api/ps').get('models'):
            raise RuntimeBusy('Primary Ollama is serving another workload; leave it untouched')
        gpu = self.gpu()
        if gpu['utilizationPercent'] > self.policy['maxGpuUtilizationPercent']:
            raise RuntimeBusy('GPU is busy; leave candidate queued')
        if gpu['freeGiB'] < bytes_required / GIB + self.policy['minGpuHeadroomGiB']:
            raise RuntimeBusy('Insufficient live GPU headroom; leave candidate queued')
        return gpu

    def wait_idle(self, bytes_required=0):
        until = time.monotonic() + min(self.policy.get('idleWaitSeconds', 300), self.remaining())
        while True:
            try:
                return self.check_idle(bytes_required)
            except RuntimeBusy:
                if time.monotonic() >= until:
                    raise
                time.sleep(min(5, until - time.monotonic(), self.remaining()))

    def storage_check(self, new_bytes, installed, resume_bytes=0):
        download_dir = self.download_dir
        existing_downloads = tree_bytes(download_dir)
        # The entire private store is charged, including failed-import orphan blobs.
        # Historic reservations are an audit trail, not an ever-growing storage bill.
        owned = tree_bytes(self.models_dir)
        allowance = 3 * new_bytes - min(new_bytes, resume_bytes)
        self.report['storageAccounting'] = {'basis': 'actual private store and download bytes',
            'storeBytes': owned, 'downloadBytes': existing_downloads, 'newCopyAllowanceBytes': allowance,
            'importCaveat': 'Reserve download plus upload blob plus a possible Ollama-rewritten model layer'}
        if owned + existing_downloads + allowance > self.policy['maxOwnedStorageGiB'] * GIB:
            raise RuntimeError('Task storage budget full including orphan blobs and transient import copies; reconcile private storage')
        stores = [download_dir, self.models_dir]
        by_device = {}
        for path in stores:
            parent = path
            while not parent.exists():
                if parent.parent == parent:
                    raise RuntimeBusy('Storage drive is unavailable: ' + str(path))
                parent = parent.parent
            device = os.stat(parent).st_dev
            amount, previous_parent = by_device.get(device, (0, parent))
            needed = new_bytes - min(new_bytes, resume_bytes) if path == download_dir else 2 * new_bytes
            by_device[device] = (amount + needed, previous_parent)
        for required, parent in by_device.values():
            if shutil.disk_usage(parent).free < required + self.policy['minFreeDiskGiB'] * GIB:
                raise RuntimeError('Download/import would cross the free-disk reserve')

    def validate_candidate(self, selection):
        if not isinstance(selection.get('rationale'), str) or len(selection['rationale'].strip()) < 20:
            raise ValueError('Selection needs a concrete rationale')
        installed = self.installed()
        if selection.get('kind') == 'installed':
            name = selection.get('model')
            if name not in installed or selection.get('expectedDigest') != installed[name].get('digest'):
                raise ValueError('Installed selection must pin the currently installed model digest')
            if installed[name].get('remote_host') or installed[name].get('remote_model') or not installed[name].get('size') or 'cloud' in name.lower():
                raise ValueError('Only local weight-backed models are eligible')
            return {'kind': 'installed', 'model': name, 'digest': installed[name]['digest'],
                    'bytes': installed[name]['size'], 'selection': selection}
        if selection.get('kind') != 'huggingface':
            raise ValueError('Only installed models or a pinned Hugging Face GGUF are supported')
        repo = selection.get('repoId', '')
        revision = selection.get('revision', '')
        filename = selection.get('filename', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Invalid repository ID')
        if repo.split('/')[0].lower() not in {name.lower() for name in self.policy['approvedPublishers']}:
            raise ValueError('Publisher is outside the approved list; report for user review')
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError('Pin a full 40-character commit SHA, not main or a moving tag')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.gguf', filename, re.IGNORECASE) or re.search(r'-\d+-of-\d+', filename):
            raise ValueError('Only a single root-level GGUF is supported; split models require review')
        if selection.get('modelCardUrl') != HF + '/' + repo:
            raise ValueError('Selection must identify the source model card')
        detail = self.request(HF + '/api/models/' + repo + '/revision/' + revision + '?blobs=true')
        if detail.get('sha') != revision or detail.get('gated'):
            raise ValueError('Revision mismatch or gated model')
        matching = [item for item in detail.get('siblings', []) if item.get('rfilename') == filename]
        if len(matching) != 1:
            raise ValueError('GGUF not found at the pinned revision')
        item = matching[0]
        lfs = item.get('lfs') or {}
        size, sha = item.get('size') or lfs.get('size'), lfs.get('sha256', '')
        if not isinstance(size, int) or size <= 0 or not re.fullmatch(r'[0-9a-f]{64}', sha):
            raise ValueError('Exact GGUF size and SHA-256 are required')
        if size > self.policy['maxDownloadGiB'] * GIB:
            raise ValueError('GGUF exceeds the per-night download budget')
        name = OWNED_PREFIX + sha[:16] + ':latest'
        if name in installed:
            provenance = read_json(self.state / 'imports.json', {}).get(name, {})
            if provenance.get('sha256') != sha or provenance.get('digest') != installed[name]['digest']:
                raise ValueError('Task model name exists without matching recorded weights and digest')
        else:
            partial = self.download_dir / (sha + '.part')
            if not partial.exists():
                partial = self.download_dir / (sha + '.gguf')
            resume_bytes = partial.stat().st_size if partial.exists() else 0
            self.storage_check(size, installed, resume_bytes)
        return {'kind': 'huggingface', 'model': name, 'bytes': size, 'sha256': sha,
                'repoId': repo, 'revision': revision, 'filename': filename,
                'alreadyImported': name in installed, 'digest': installed.get(name, {}).get('digest'), 'selection': selection}

    def download(self, plan):
        target = self.download_dir / (plan['sha256'] + '.gguf')
        target.parent.mkdir(parents=True, exist_ok=True)
        # The content address and pinned source make a retained partial safe to resume.
        temporary = target.with_suffix('.part')
        url = HF + '/' + plan['repoId'] + '/resolve/' + plan['revision'] + '/' + urllib.parse.quote(plan['filename'])
        if target.exists() and not temporary.exists():
            os.replace(target, temporary)
        sha, count = hashlib.sha256(), 0
        try:
            if temporary.exists():
                if temporary.stat().st_size > plan['bytes']:
                    raise ValueError('Partial exceeds the declared size')
                with temporary.open('rb') as previous:
                    while chunk := previous.read(1024 * 1024):
                        self.remaining()
                        sha.update(chunk)
                        count += len(chunk)
            resumed = count
            self.report['download'] = {'path': str(target), 'partialPath': str(temporary),
                'resumedFromBytes': resumed, 'source': url, 'verified': False}
            self.save_report()
            if count < plan['bytes']:
                request = urllib.request.Request(url, headers={'Range': f'bytes={count}-'} if count else {})
                with urllib.request.urlopen(request, timeout=self.remaining(30)) as source:
                    status = getattr(source, 'status', 200)
                    if count and status == 200:  # Origin ignored Range: restart; never append a full response.
                        count, sha = 0, hashlib.sha256()
                        self.report['download']['rangeIgnoredRestarted'] = True
                    elif count:
                        expected_range = f'bytes {count}-{plan["bytes"] - 1}/{plan["bytes"]}'
                        if status != 206 or source.headers.get('Content-Range') != expected_range:
                            raise ValueError('Resume response has an invalid Content-Range')
                    with temporary.open('ab' if count else 'wb') as output:
                        while True:
                            self.remaining()
                            chunk = source.read1(1024 * 1024)
                            if not chunk:
                                break
                            count += len(chunk)
                            if count > plan['bytes'] or count > self.policy['maxDownloadGiB'] * GIB:
                                raise ValueError('Download exceeded its declared size or budget')
                            if shutil.disk_usage(target.parent).free < len(chunk) + self.policy['minFreeDiskGiB'] * GIB:
                                raise RuntimeError('Free disk reserve reached during download')
                            sha.update(chunk)
                            output.write(chunk)
            if count < plan['bytes']:
                raise OSError('Download ended early; verified-length partial retained for the next attempt')
            if count != plan['bytes'] or sha.hexdigest() != plan['sha256']:
                raise ValueError('Downloaded GGUF size or SHA-256 does not match the pinned repository')
            with temporary.open('rb') as handle:
                if handle.read(4) != b'GGUF':
                    raise ValueError('Downloaded file does not have a GGUF header')
            os.replace(temporary, target)
            self.report['download'].update(bytes=count, sha256=sha.hexdigest(), verified=True)
            self.save_report()
            return target
        except ValueError:
            temporary.unlink(missing_ok=True)
            raise

    def import_model(self, plan, path):
        if self.endpoint == OLLAMA or self.secondary_process is None:
            raise RuntimeError('GGUF imports require the harness-owned secondary server')
        # Other processes may consume disk while the download is in progress.
        self.storage_check(plan['bytes'], self.installed(), resume_bytes=plan['bytes'])
        executable = shutil.which('ollama')
        if not executable:
            raise RuntimeError('Installed Ollama CLI is unavailable')
        modelfile = path.with_suffix('.Modelfile')
        modelfile.write_text('FROM "' + str(path.resolve()).replace('\\', '/') + '"\n', encoding='utf-8')
        imported = False
        try:
            result = subprocess.run([executable, 'create', plan['model'], '-f', str(modelfile)],
                capture_output=True, text=True, timeout=self.remaining(),
                env=dict(os.environ, OLLAMA_HOST=self.endpoint, OLLAMA_MODELS=str(self.models_dir)),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode:
                raise RuntimeError('Ollama import failed: ' + result.stderr[-1500:])
            installed = self.installed()
            if plan['model'] not in installed:
                raise RuntimeError('Imported model did not appear in Ollama')
            digest = installed[plan['model']]['digest']
            imports = read_json(self.state / 'imports.json', {})
            imports[plan['model']] = {'sha256': plan['sha256'], 'digest': digest,
                'repoId': plan['repoId'], 'revision': plan['revision'], 'filename': plan['filename'],
                'bytes': plan['bytes'], 'importedAt': now(), 'runId': self.run_id}
            atomic_json(self.state / 'imports.json', imports)
            try:
                prune_uploaded_blob(self, plan['model'], imports[plan['model']])
            except Exception as exc:
                self.report.setdefault('uploadedBlobCleanupErrors', []).append(str(exc))
            imported = True
            return digest
        finally:
            modelfile.unlink(missing_ok=True)
            if imported:
                path.unlink(missing_ok=True)

    def chat(self, model, prompt, thinking_capable, think=False, num_predict=None, supervise=False, sampling_profile=None):
        if self.endpoint != OLLAMA and self.request(OLLAMA + '/api/ps').get('models'):
            raise RuntimeBusy('Primary Ollama became busy during candidate battery')
        options = {key: self.policy[value] for key, value in (
            ('num_ctx', 'numCtx'), ('num_predict', 'numPredict'), ('temperature', 'temperature'), ('seed', 'seed'))}
        options.update(top_p=1, top_k=40, repeat_penalty=1.0)
        if sampling_profile is not None:
            if sampling_profile != 'nex-recommended-v1':
                raise ValueError('Unsupported sampling profile')
            options.update(temperature=0.7, top_p=0.95, top_k=40)
        if num_predict is not None:
            options['num_predict'] = num_predict
        body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                'stream': False, 'keep_alive': '5m', 'options': options}
        if thinking_capable:
            body['think'] = think
        started = time.monotonic()
        if supervise:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('api_probe.py'))],
                input=json.dumps({'url': self.endpoint + '/api/chat', 'body': body, 'seconds': self.remaining()}),
                capture_output=True, text=True, encoding='utf-8', timeout=self.remaining(),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode:
                raise RuntimeError('Thinking probe failed: ' + result.stderr[-1500:])
            response = json.loads(result.stdout)
            response['supervisedWallMs'] = round((time.monotonic() - started) * 1000, 1)
        else:
            response = self.api('chat', body, timeout=self.remaining())
            response['clientWallMs'] = round((time.monotonic() - started) * 1000, 1)
        if not response.get('done'):
            raise RuntimeError('Incomplete Ollama response')
        return response

    @staticmethod
    def measurement(response):
        generated = response.get('eval_count', 0)
        duration = response.get('eval_duration', 0)
        prompt_count = response.get('prompt_eval_count', 0)
        cached = response.get('prompt_eval_cached_count')
        prompt_duration = response.get('prompt_eval_duration', 0)
        return {'genTokPerSec': round(generated * 1e9 / duration, 2) if duration else None,
                'outputTokens': generated, 'promptTokens': prompt_count, 'cachedPromptTokens': cached,
                'promptTokPerSec': round((prompt_count - (cached or 0)) * 1e9 / prompt_duration, 2) if prompt_duration else None,
                'promptRateBasis': 'uncached tokens' if cached is not None else 'reported tokens; cache split unavailable',
                'loadMs': response.get('load_duration', 0) / 1e6,
                'serverTotalMs': response.get('total_duration', 0) / 1e6,
                'clientWallMs': response['clientWallMs'], 'doneReason': response.get('done_reason'),
                'truncated': response.get('done_reason') == 'length'}

    @staticmethod
    def observe_thinking(measurement, response, phase):
        message = response.get('message', {})
        thinking = message.get('thinking', '')
        if not isinstance(thinking, str) or not thinking.strip():
            return
        answer = message.get('content', '')
        measurement['thinking'] = 'unexpected-output'
        measurement['thinkingControl']['unexpectedResponses'].append({
            'phase': phase, 'thinkingCharacters': len(thinking),
            'answerCharacters': len(answer) if isinstance(answer, str) else None})

    def benchmark(self, model):
        installed = self.installed()
        if model not in installed:
            raise ValueError('Benchmark target must already be installed locally')
        gpu = self.wait_idle(installed[model].get('size', 0))
        self.report.setdefault('gpuBefore', gpu)
        info = self.api('show', {'model': model})
        thinking = 'thinking' in info.get('capabilities', [])
        measurement = {'model': model, 'digest': installed[model]['digest'], 'endpoint': self.endpoint,
            'runtime': self.api('version'), 'details': info.get('details'),
            'modelParameters': info.get('parameters'), 'capabilities': info.get('capabilities'),
            'templateSha256': hashlib.sha256(info.get('template', '').encode()).hexdigest(),
            'policy': self.policy.copy(), 'gpuBefore': gpu, 'thinking': 'requested-off' if thinking else 'not-advertised',
            'thinkingControl': {'advertised': thinking, 'requested': 'off' if thinking else 'not-sent',
                'unexpectedResponses': [],
                'caveat': 'Checks returned thinking text only, not unexposed internal reasoning; character counts are not tokens.'},
            'loadTiming': 'Ollama model-load duration; not time to first token; warmup excluded from medians',
            'qualityScope': 'Small instruction-following checks; no coding-quality claim',
            'trials': [], 'checks': [], 'generatedCodeExecution': 'disabled'}
        self.report.setdefault('benchmarks', []).append(measurement)
        started_model = False
        try:
            started_model = True
            warmup = self.chat(model, 'Reply with exactly: ready', thinking)
            measurement['warmup'] = warmup
            self.observe_thinking(measurement, warmup, 'warmup')
            measurement['loadedModel'] = self.api('ps').get('models', [])
            if any(row.get('digest') and row['digest'] != installed[model]['digest']
                   for row in measurement['loadedModel'] if row.get('name') == model):
                raise RuntimeError('Loaded model digest changed during benchmark startup')
            for trial in range(self.policy['repetitions']):
                short = self.chat(model, 'Write a 100 word description of the Rocky Mountains.', thinking)
                self.observe_thinking(measurement, short, f'short-{trial + 1}')
                # Distinct first tokens prevent cross-trial prefix cache hits in the ingest measurement.
                filler = ('The quick brown fox jumps over the lazy dog. ' * 700)
                ingest = self.chat(model, f'Trial {trial + 1}.\n{filler}\nReply with the single word: acknowledged.', thinking)
                self.observe_thinking(measurement, ingest, f'ingest-{trial + 1}')
                measurement['trials'].append({'trial': trial + 1,
                    'short': self.measurement(short), 'ingest': self.measurement(ingest),
                    'shortResponse': short, 'ingestResponse': ingest})
                self.save_report()
            cases = [
                ('sequence', 'Print the numbers 1 through 5, one per line. Output nothing else.', ['1', '2', '3', '4', '5']),
                ('arithmetic', 'What is 17 * 23? Output only the integer.', ['391']),
                ('extraction', 'Extract only the order ID from: Customer Mira, order AB-204, total $17. Output only the ID.', ['AB-204'])]
            for name, prompt, expected in cases:
                response = self.chat(model, prompt, thinking)
                content = response.get('message', {}).get('content', '')
                measurement['checks'].append({'name': name, 'passed': exact_lines(content, expected), 'response': response})
                self.observe_thinking(measurement, response, 'check-' + name)
            values = [row['short']['genTokPerSec'] for row in measurement['trials'] if row['short']['genTokPerSec'] is not None]
            wall = [row['short']['clientWallMs'] for row in measurement['trials']]
            measurement['summary'] = {'medianGenTokPerSec': statistics.median(values) if values else None,
                'minGenTokPerSec': min(values) if values else None, 'maxGenTokPerSec': max(values) if values else None,
                'medianClientWallMs': statistics.median(wall),
                'checksPassed': sum(row['passed'] for row in measurement['checks']), 'checksTotal': len(cases),
                'unexpectedThinking': bool(measurement['thinkingControl']['unexpectedResponses']),
                'anyTruncated': any(row[kind]['truncated'] for row in measurement['trials'] for kind in ('short', 'ingest')),
                'promptNearContextLimit': any(row['ingest']['promptTokens'] >= 0.9 * self.policy['numCtx'] for row in measurement['trials']),
                'contextCaveat': 'Prompt counts near 90% of context may reflect silent input truncation; not a proof of truncation.'}
            measurement['thinkingProbe'] = self.thinking_probe(model, thinking, measurement['summary'])
            measurement['visionProbe'] = {'status': 'not-run', 'reason':
                'Optional vision fixture is not configured; this battery measures text only.'}
            measurement['status'] = 'completed'
            return measurement
        finally:
            original_error = sys.exc_info()[1]
            if started_model:
                try:
                    # Only unload the target this run loaded; never stop another installed model.
                    with self.cleanup_window():
                        self.api('generate', {'model': model, 'keep_alive': 0}, timeout=10)
                        self.confirm_unloaded(model, gpu['freeGiB'])
                    measurement['unloadConfirmed'] = True
                except Exception as exc:
                    measurement['unloadWarning'] = str(exc)
                    if original_error is None:
                        raise RuntimeError('Own model unload could not be confirmed: ' + str(exc)) from exc

    def confirm_unloaded(self, model, free_before):
        until = time.monotonic() + min(self.policy.get('unloadWaitSeconds', 60), self.remaining())
        while True:
            loaded = self.api('ps').get('models', [])
            gpu = self.gpu()
            own_loaded = any(row.get('name') == model or row.get('model') == model for row in loaded)
            if not own_loaded and loaded and self.endpoint == OLLAMA:
                self.report.setdefault('unloads', []).append({'model': model, 'endpoint': self.endpoint,
                    'confirmedAt': now(), 'gpuAfter': gpu, 'freeBeforeGiB': free_before,
                    'vramRecovered': None, 'otherWorkloadLoaded': [row.get('name') for row in loaded]})
                return
            if not loaded and gpu['freeGiB'] >= free_before - self.policy.get('vramRecoveryToleranceGiB', 2):
                self.report.setdefault('unloads', []).append({'model': model, 'endpoint': self.endpoint,
                    'confirmedAt': now(), 'gpuAfter': gpu, 'freeBeforeGiB': free_before})
                return
            if time.monotonic() >= until:
                raise RuntimeError('Model unload or VRAM recovery timed out')
            time.sleep(min(1, self.remaining()))

    def thinking_probe(self, model, capable, summary):
        if summary.get('unexpectedThinking'):
            return {'status': 'skipped', 'includedInThroughputMedians': False,
                    'reason': 'Ordinary responses returned thinking; a thinking-off reference was not established.'}
        if not capable:
            return {'status': 'unsupported', 'includedInThroughputMedians': False}
        deadline = self.deadline
        self.deadline = min(deadline, time.monotonic() + self.policy.get('thinkingProbeSeconds', 180))
        result = {'includedInThroughputMedians': False,
            'maxTokens': self.policy.get('thinkingProbeTokens', 8192),
            'maxSeconds': self.policy.get('thinkingProbeSeconds', 180),
            'caveat': 'One thinking-enabled trial; generated tokens include thinking and answer. Character counts are not tokens.'}
        try:
            response = self.chat(model, 'Write a 100 word description of the Rocky Mountains.', True,
                                 think=True, num_predict=result['maxTokens'], supervise=True)
            message = response.get('message', {})
            result.update(status='completed', measurement=self.measurement(response), response=response,
                thinkingCharacters=len(message.get('thinking', '')), answerCharacters=len(message.get('content', '')),
                wallTimeRatioToThinkingOffMedian=response['clientWallMs'] / summary['medianClientWallMs']
                    if summary['medianClientWallMs'] else None)
        except Exception as exc:
            result.update(status='error', error=str(exc))
        finally:
            self.deadline = deadline
        return result

    def complete_import(self, plan):
        if plan['kind'] != 'huggingface':
            return
        imports = read_json(self.state / 'imports.json', {})
        imports[plan['model']].update(completedAt=now(), completedRun=self.run_id)
        atomic_json(self.state / 'imports.json', imports)

    def cleanup(self):
        if self.endpoint == OLLAMA or self.secondary_process is None:
            raise RuntimeError('Cleanup requires the harness-owned secondary server')
        imports = read_json(self.state / 'imports.json', {})
        installed = self.installed()
        loaded = {row['name'] for row in self.api('ps').get('models', [])}
        eligible, failed = [], []
        for name, item in imports.items():
            if not (name.startswith(OWNED_PREFIX) and name in installed and name not in loaded
                    and item.get('digest') == installed[name].get('digest')):
                continue
            try:
                prune_uploaded_blob(self, name, item)
            except Exception as exc:
                self.report.setdefault('uploadedBlobCleanupErrors', []).append(str(exc))
            terminal_failure = False
            for run_id in dict.fromkeys(item.get(key, '') for key in ('completedRun', 'lastRun', 'runId')):
                if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}', run_id):
                    continue
                result = read_json(self.root / 'runs' / (run_id + '.json'), {})
                complete = result.get('status') == 'completed' or (run_id == self.run_id and result.get('benchmarkStatus') == 'completed')
                if complete and any(row.get('model') == name and row.get('digest') == item['digest']
                                    and row.get('status') == 'completed' for row in result.get('benchmarks', [])):
                    eligible.append((item.get('completedAt') or result.get('finishedAt', ''), name))
                    break
                admission = result.get('admission', {})
                if (result.get('status') == 'error' and result.get('error')
                        and result.get('failureKind') not in ('environment', 'timeout', 'baseline', 'admission')
                        and admission.get('model') == name and admission.get('digest') == item['digest']):
                    terminal_failure = True
            else:
                if terminal_failure:
                    failed.append(('', name))
        eligible.sort(reverse=True)
        for _, name in failed + eligible[self.policy.get('keepCompletedModels', 2):]:
            # Recheck immediately before deletion. Prefix alone never establishes ownership.
            if self.installed().get(name, {}).get('digest') != imports[name]['digest'] or self.api('ps').get('models'):
                raise RuntimeBusy('Cleanup state changed; nothing further deleted')
            self.report.setdefault('cleanup', []).append({'model': name, 'digest': imports[name]['digest'], 'status': 'requested'})
            self.save_report()
            ledger_path = self.ledger_path
            ledger = read_json(ledger_path, {'days': {}})
            deletion = {'model': name, 'digest': imports[name]['digest'], 'runId': self.run_id,
                        'requestedAt': now(), 'endpoint': self.endpoint, 'status': 'requested'}
            ledger.setdefault('deletions', []).append(deletion)
            atomic_json(ledger_path, ledger)
            payload = json.dumps({'model': name}).encode()
            request = urllib.request.Request(self.endpoint + '/api/delete', data=payload, method='DELETE',
                                             headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=self.remaining(30)) as response:
                response.read(1024)
            if name in self.installed():
                raise RuntimeError('Deleted model still appears in the secondary store')
            deletion.update(status='deleted', deletedAt=now())
            atomic_json(ledger_path, ledger)
            for path in (self.state / 'nightly-ledger.json', self.state / 'acceptance-ledger.json'):
                if path.exists():
                    reservations = read_json(path)
                    for runs in reservations['days'].values():
                        for entry in runs:
                            if entry['model'] == name:
                                entry.update(reservationReleasedAt=now(), reservedBytes=0)
                    atomic_json(path, reservations)
            imports.pop(name)
            atomic_json(self.state / 'imports.json', imports)
            self.report['cleanup'][-1]['status'] = 'deleted'

    def reserve(self, plan):
        ledger_path = self.ledger_path
        ledger = read_json(ledger_path, {'days': {}})
        today = dt.date.today().isoformat()
        runs = ledger['days'].setdefault(today, [])
        acceptance = self.ledger_path.name == 'acceptance-ledger.json'
        limit = self.policy.get('maxAcceptanceAttemptsPerDay', 3) if acceptance else self.policy['maxCandidatesPerDay']
        if acceptance and any(entry['model'] == plan['model'] for entry in runs):
            raise RuntimeError('This acceptance fixture already used its daily slot; no repeat download')
        if len(runs) >= limit:
            raise RuntimeError('Daily candidate limit already used; failed attempts also consume the slot')
        runs.append({'runId': self.run_id, 'model': plan['model'], 'selection': plan['selection'],
                     'reservedBytes': plan['bytes'] if plan['kind'] == 'huggingface' and not plan['alreadyImported'] else 0,
                     'status': 'reserved', 'reservedAt': now()})
        atomic_json(ledger_path, ledger)

    def finish_reservation(self):
        path = self.ledger_path
        ledger = read_json(path, {'days': {}})
        for runs in ledger['days'].values():
            for entry in runs:
                if entry['runId'] == self.run_id:
                    entry.update(status=self.report['status'], resultFile=self.report.get('resultFile'), finishedAt=now())
        atomic_json(path, ledger)

    def run_candidate(self, selection, *, acceptance_validation=False):
        self.report.update(mode='nightly', selection=selection)
        if acceptance_validation:
            # Only the explicit human acceptance script calls this, never the nightly CLI.
            self.ledger_path = self.state / 'acceptance-ledger.json'
            self.report.update(mode='acceptance-validation', ledgerFile='state/acceptance-ledger.json')
        if not self.window_open() and not acceptance_validation:
            self.report.update(status='deferred', reason='Daytime catch-up: benchmarks start only in the configured overnight window')
            return self.report
        reserved, measurements_done, plan = False, False, None
        try:
            installed = self.installed()
            primary_before = {name: row['digest'] for name, row in installed.items()}
            primary_version = self.api('version')
            primary_free_before = shutil.disk_usage(self.root).free
            baseline_name = self.policy['baselineModel']
            if baseline_name not in installed:
                raise ValueError('Configured baseline is not installed; report rather than download a second model')
            self.wait_idle()
            with self.candidate_runtime(selection):
                if selection.get('kind') == 'huggingface':
                    try:
                        self.cleanup()  # Reclaim verified terminal failures before admitting more bytes.
                    except Exception as exc:
                        self.report['preflightCleanupError'] = str(exc)
                # Starting an empty owned server is preflight, not a candidate attempt.
                plan = self.validate_candidate(selection)
                self.report.update(admission=plan, acceptanceValidation=acceptance_validation)
                if acceptance_validation and plan['bytes'] > 2 * GIB:
                    raise ValueError('Manual acceptance fixture must be at most 2 GiB')
                version = self.api('version')
                self.report['runtimeVersions'] = {'primary': primary_version, 'candidate': version,
                                                  'match': primary_version == version}
                if primary_version != version:
                    raise RuntimeBusy('Ollama versions differ; comparison refused')
                self.wait_idle(max(plan['bytes'], installed[baseline_name].get('size', 0)))
                self.reserve(plan)  # Durable reservation before weights, import, and inference.
                reserved = True
                if plan['kind'] == 'huggingface' and not plan['alreadyImported']:
                    path = self.download(plan)
                    plan['digest'] = self.import_model(plan, path)
                candidate = self.benchmark(plan['model'])
                self.report['phase'] = 'baseline'
                if baseline_name != plan['model'] or self.endpoint != OLLAMA:
                    candidate_endpoint = self.endpoint
                    self.endpoint = OLLAMA
                    try:
                        baseline = self.benchmark(baseline_name)
                    finally:
                        self.endpoint = candidate_endpoint
                    invalid_reasons = []
                    for label, result in (('candidate', candidate), ('baseline', baseline)):
                        if result.get('status') != 'completed':
                            invalid_reasons.append(label + ': battery incomplete')
                        if result['summary'].get('anyTruncated'):
                            invalid_reasons.append(label + ': output truncated')
                        if result['summary'].get('promptNearContextLimit'):
                            invalid_reasons.append(label + ': prompt near context limit')
                        if result['summary'].get('unexpectedThinking'):
                            invalid_reasons.append(label + ': unexpected thinking in ordinary responses')
                    self.report['comparison'] = {'candidate': candidate['summary'], 'baseline': baseline['summary'],
                        'baselineModel': baseline_name, 'valid': not invalid_reasons,
                        'caveat': 'Same versions, request settings, and machine; templates/tokenizers differ. Primary server environment is not verified identical.'}
                    if invalid_reasons:
                        self.report['comparison']['invalidReason'] = '; '.join(invalid_reasons)
                measurements_done = True
                self.report['phase'] = 'postprocessing'
                self.report['benchmarkStatus'] = 'completed'
                self.save_report()
                try:
                    self.complete_import(plan)
                except Exception as exc:
                    self.report['importBookkeepingError'] = str(exc)
                registry = self.registry()
                model_id = plan.get('repoId')
                if model_id in registry['models']:
                    registry['models'][model_id].update(benchmarkStatus='completed', benchmarkRun=self.run_id,
                        benchmarkRevision=plan.get('revision'), benchmarkFile=plan.get('filename'))
                    atomic_json(self.state / 'candidates.json', registry)
                if plan['kind'] == 'huggingface':
                    try:
                        self.cleanup()
                    except Exception as exc:
                        self.report['cleanupError'] = str(exc)
            self.report['status'] = 'completed'
            after = {name: row['digest'] for name, row in self.installed().items()}
            self.report['primaryIntegrity'] = {'before': primary_before, 'after': after,
                'modelDigestsUnchanged': primary_before == after,
                'systemDriveFreeBytesBefore': primary_free_before,
                'systemDriveFreeBytesAfter': shutil.disk_usage(self.root).free,
                'caveat': 'Other Windows processes may change system-drive free space during a run.'}
            if primary_before != after and 'comparison' in self.report:
                self.report['comparison'].update(valid=False, invalidReason='Primary model inventory changed during the run')
            if any(row.get('otherWorkloadLoaded') for row in self.report.get('unloads', [])) and 'comparison' in self.report:
                self.report['comparison'].update(valid=False, invalidReason='Another workload appeared during baseline unload')
        except RuntimeBusy as exc:
            self.report.update(status='completed' if measurements_done else ('error' if reserved else 'deferred'),
                               reason=str(exc), failureKind='environment')
            if measurements_done:
                self.report['postProcessingError'] = str(exc)
        except Exception as exc:
            if measurements_done:
                self.report.update(status='completed', postProcessingError=str(exc))
            else:
                kind = ('admission' if not reserved else 'timeout' if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else
                        ('baseline' if self.report.get('phase') == 'baseline' else 'execution'))
                self.report.update(status='error', error=str(exc), failureKind=kind)
        finally:
            self.save_report()
            if reserved:
                if plan and plan['kind'] == 'huggingface':
                    try:
                        imports = read_json(self.state / 'imports.json', {})
                        if imports.get(plan['model'], {}).get('digest') == plan.get('digest'):
                            imports[plan['model']]['lastRun'] = self.run_id
                            atomic_json(self.state / 'imports.json', imports)
                    except Exception as exc:
                        self.report['importBookkeepingError'] = str(exc)
                        self.save_report()
                self.finish_reservation()
        return self.report


def main(argv=None, run_id=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--discover', action='store_true')
    modes.add_argument('--pending', action='store_true')
    modes.add_argument('--validate-candidate', type=Path)
    modes.add_argument('--run-candidate', type=Path)
    modes.add_argument('--acceptance-fixture', type=Path,
        help='Human-requested plumbing validation only; <=2 GiB and separate daily ledger')
    modes.add_argument('--benchmark')
    parser.add_argument('--top-n', type=int, default=25)
    parser.add_argument('--detail-cap', type=int, default=100)
    args = parser.parse_args(argv)
    harness = Harness(Path(__file__).resolve().parent)
    if run_id:
        harness.run_id = run_id
        harness.report['runId'] = run_id
    with state_lock(harness.state / 'operation.lock'):
        try:
            if args.discover:
                if not 1 <= args.top_n <= 100 or not 1 <= args.detail_cap <= 100:
                    raise ValueError('Discovery limits must be between 1 and 100')
                result = harness.discover(args.top_n, args.detail_cap)
            elif args.pending:
                result = {'status': 'ok', 'candidates': harness.pending()}
            elif args.validate_candidate:
                selection = read_json(args.validate_candidate)
                with harness.candidate_runtime(selection):
                    result = {'status': 'ok', 'plan': harness.validate_candidate(selection)}
                    harness.report.update(mode='validate', status='validated', admission=result['plan'])
            elif args.run_candidate:
                result = harness.run_candidate(read_json(args.run_candidate))
            elif args.acceptance_fixture:
                result = harness.run_candidate(read_json(args.acceptance_fixture), acceptance_validation=True)
            else:
                harness.report.update(mode='manual-benchmark')
                harness.benchmark(args.benchmark)
                harness.report['status'] = 'completed'
                result = harness.report
        except Exception as exc:
            harness.report.update(status='error', error=str(exc))
            result = harness.report
        if not args.pending and not args.validate_candidate:
            harness.save_report()
        print(json.dumps(result, indent=2))
        return 1 if result.get('status') == 'error' else 0


def supervised(argv, worker_command=None, timeout=None, run_id=None):
    """A parent deadline also bounds stalled sockets and native imports."""
    root = Path(__file__).resolve().parent
    harness = Harness(root)
    if run_id:
        harness.run_id = run_id
        harness.report['runId'] = run_id
    command = worker_command(harness.run_id) if worker_command else [sys.executable, str(Path(__file__).resolve()), '--worker', harness.run_id, *argv]
    process = subprocess.Popen(command,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
        env=dict(os.environ, PYTHONUTF8='1'),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        output, errors = process.communicate(timeout=min(timeout or harness.policy['maxRuntimeSeconds'], harness.policy['maxRuntimeSeconds']))
        sys.stdout.write(output)
        sys.stderr.write(errors)
        return process.returncode
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            process.kill()
        process.wait(timeout=10)
        with state_lock(harness.state / 'operation.lock'):
            partial = read_json(root / 'runs' / (harness.run_id + '.json'))
            if partial:
                harness.report = partial
                if partial.get('mode') == 'acceptance-validation':
                    harness.ledger_path = harness.state / 'acceptance-ledger.json'
                elif partial.get('campaign'):
                    campaign_id = partial['campaign'].get('campaignId', '')
                    if re.fullmatch(r'[a-z0-9-]{1,80}', campaign_id):
                        ledger_name = 'campaign-' + campaign_id + '-ledger.json'
                        if partial.get('ledgerFile') == 'state/' + ledger_name:
                            harness.ledger_path = harness.state / ledger_name
            if harness.report.get('secondaryRuntime'):
                record = harness.report['secondaryRuntime']
                expected = record.get('processIdentity')
                recovery = {'portFree': not port_open(harness.policy['secondaryPort'])}
                try:
                    harness.deadline = time.monotonic() + 35  # bounded shutdown verification, no inference
                    before = harness.report.get('gpuBefore', {}).get('freeGiB')
                    until = time.monotonic() + 30
                    while True:
                        gpu = harness.gpu()
                        # taskkill can return before a descendant releases its listening socket.
                        # Poll both resources within the same bounded recovery window.
                        recovery.update(portFree=not port_open(harness.policy['secondaryPort']),
                            gpuAfter=gpu, vramRecovered=(gpu['freeGiB'] >= before - harness.policy.get('vramRecoveryToleranceGiB', 2)) if before is not None else None)
                        recovery['ownedProcessExited'] = (process_identity(record['pid']) != expected) if expected and record.get('pid') else None
                        if (recovery['portFree'] and recovery['ownedProcessExited'] is not False and (before is None or recovery['vramRecovered'])) or time.monotonic() >= until:
                            break
                        time.sleep(0.25)
                except Exception as exc:
                    recovery['verificationError'] = str(exc)
                harness.report['deadlineRecovery'] = recovery
                record['deadlineRecovery'] = recovery
                if recovery.get('portFree') and recovery.get('ownedProcessExited') is True:
                    record.update(stoppedAt=now(), stopReason='hard-runtime-limit')
                previous = read_json(harness.state / 'secondary-process.json', {})
                if expected and previous.get('pid') == record.get('pid') and previous.get('processIdentity') == expected:
                    atomic_json(harness.state / 'secondary-process.json', record)
            harness.report.update(status='error', error='Hard runtime limit reached; worker stopped', failureKind='timeout')
            harness.save_report()
            harness.finish_reservation()
        print(json.dumps(harness.report, indent=2))
        return 124


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--launch-candidate':
        from background import launch
        launch(sys.argv[2])
        sys.exit(0)
    if len(sys.argv) == 3 and sys.argv[1] in ('--status-run', '--wait-run'):
        from background import status
        status(sys.argv[2], 55 if sys.argv[1] == '--wait-run' else 0)
        sys.exit(0)
    if len(sys.argv) > 3 and sys.argv[1] == '--supervisor':
        sys.exit(supervised(sys.argv[3:], run_id=sys.argv[2]))
    if len(sys.argv) > 2 and sys.argv[1] == '--worker':
        sys.exit(main(sys.argv[3:], run_id=sys.argv[2]))
    sys.exit(supervised(sys.argv[1:]))
