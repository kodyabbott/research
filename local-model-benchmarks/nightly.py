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

GIB = 1024 ** 3
OLLAMA = 'http://127.0.0.1:11434'
HF = 'https://huggingface.co'
TAGS = ('text-generation', 'image-text-to-text', 'text-to-image',
        'image-to-video', 'text-to-speech', 'text-to-audio')
TEXT_TAGS = TAGS[:2]
OWNED_PREFIX = 'nightly-bench-'


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(temporary, path)
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
        self.deadline = time.monotonic() + self.policy['maxRuntimeSeconds']
        self.run_id = dt.datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8]
        self.report = {'schemaVersion': 2, 'runId': self.run_id, 'startedAt': now(), 'status': 'running'}

    def remaining(self, maximum=None):
        seconds = self.deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError('Run exceeded its policy runtime limit')
        return min(seconds, maximum) if maximum else seconds

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
        return self.request(OLLAMA + '/api/' + path, data, timeout)

    def save_report(self):
        self.report['finishedAt'] = now()
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

    def discover(self, top_n=25, detail_cap=40):
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
            old_revision = row.get('revision')
            if item.get('sha') and old_revision and old_revision != item['sha']:
                row.update(detailStatus='pending', detailAttempts=0, benchmarkStatus='not-run')
            row.update(lastSeen=now(), pipeline=item.get('pipeline_tag'),
                       trendingScore=item.get('trendingScore', 0), downloads=item.get('downloads'),
                       likes=item.get('likes'), gated=bool(item.get('gated')))

        # Retry failures and deferred metadata even after a model leaves the trending window.
        pending = [row for row in registry['models'].values() if row.get('detailStatus') != 'ready']
        pending.sort(key=lambda row: (row.get('detailAttempts', 0), -(row.get('trendingScore') or 0)))
        detail_failures = []
        for row in pending[:detail_cap]:
            row['detailAttempts'] = row.get('detailAttempts', 0) + 1
            try:
                detail = self.request(HF + '/api/models/' + urllib.parse.quote(row['modelId'], safe='/') + '?blobs=true')
                if not detail.get('sha'):
                    raise ValueError('Model detail response omitted revision')
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
            trendingSeen=len(models), newCount=len(new_ids), new=[registry['models'][key] for key in new_ids],
            detailLookups=min(detail_cap, len(pending)), detailFailures=detail_failures,
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
            raise RuntimeError('Ollama is already serving a loaded model; skip rather than unload another workload')
        gpu = self.gpu()
        if gpu['utilizationPercent'] > self.policy['maxGpuUtilizationPercent']:
            raise RuntimeError('GPU is busy; leave candidate queued')
        if gpu['freeGiB'] < bytes_required / GIB + self.policy['minGpuHeadroomGiB']:
            raise RuntimeError('Insufficient live GPU headroom; leave candidate queued')
        return gpu

    def storage_check(self, new_bytes, installed):
        download_dir = self.state / 'downloads'
        existing_downloads = sum(file.stat().st_size for file in download_dir.rglob('*') if file.is_file()) if download_dir.exists() else 0
        owned = sum(row.get('size', 0) for name, row in installed.items() if name.startswith(OWNED_PREFIX))
        # Failed imports can leave unreferenced Ollama blobs. Conservatively keep their
        # reservations charged until a human reconciles storage; never silently erase them.
        ledger = read_json(self.state / 'nightly-ledger.json', {'days': {}})
        reservations = {}
        for runs in ledger['days'].values():
            for run in runs:
                reservations[run['model']] = max(reservations.get(run['model'], 0), run.get('reservedBytes', 0))
        owned = max(owned, sum(reservations.values()))
        if owned + existing_downloads + 2 * new_bytes > self.policy['maxOwnedStorageGiB'] * GIB:
            raise RuntimeError('Task storage budget full (including transient import copy); no models are deleted automatically')
        stores = [download_dir, Path(self.policy['ollamaModelsDir'])]
        by_device = {}
        for path in stores:
            parent = path
            while not parent.exists():
                parent = parent.parent
            device = os.stat(parent).st_dev
            amount, previous_parent = by_device.get(device, (0, parent))
            by_device[device] = (amount + new_bytes, previous_parent)
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
            self.storage_check(size, installed)
        return {'kind': 'huggingface', 'model': name, 'bytes': size, 'sha256': sha,
                'repoId': repo, 'revision': revision, 'filename': filename,
                'alreadyImported': name in installed, 'selection': selection}

    def download(self, plan):
        target = self.state / 'downloads' / (plan['sha256'] + '.gguf')
        target.parent.mkdir(parents=True, exist_ok=True)
        # Only this exact content-addressed temporary file is ever removed.
        temporary = target.with_suffix('.part')
        url = HF + '/' + plan['repoId'] + '/resolve/' + plan['revision'] + '/' + urllib.parse.quote(plan['filename'])
        sha, count = hashlib.sha256(), 0
        try:
            with urllib.request.urlopen(url, timeout=self.remaining(30)) as source, temporary.open('wb') as output:
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
            if count != plan['bytes'] or sha.hexdigest() != plan['sha256']:
                raise ValueError('Downloaded GGUF size or SHA-256 does not match the pinned repository')
            with temporary.open('rb') as handle:
                if handle.read(4) != b'GGUF':
                    raise ValueError('Downloaded file does not have a GGUF header')
            os.replace(temporary, target)
            return target
        finally:
            temporary.unlink(missing_ok=True)

    def import_model(self, plan, path):
        executable = shutil.which('ollama')
        if not executable:
            raise RuntimeError('Installed Ollama CLI is unavailable')
        modelfile = path.with_suffix('.Modelfile')
        modelfile.write_text('FROM "' + str(path.resolve()).replace('\\', '/') + '"\n', encoding='utf-8')
        try:
            result = subprocess.run([executable, 'create', plan['model'], '-f', str(modelfile)],
                capture_output=True, text=True, timeout=self.remaining(),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode:
                raise RuntimeError('Ollama import failed: ' + result.stderr[-1500:])
            installed = self.installed()
            if plan['model'] not in installed:
                raise RuntimeError('Imported model did not appear in Ollama')
            digest = installed[plan['model']]['digest']
            imports = read_json(self.state / 'imports.json', {})
            imports[plan['model']] = {'sha256': plan['sha256'], 'digest': digest,
                'repoId': plan['repoId'], 'revision': plan['revision'], 'filename': plan['filename']}
            atomic_json(self.state / 'imports.json', imports)
            return digest
        finally:
            modelfile.unlink(missing_ok=True)
            path.unlink(missing_ok=True)

    def chat(self, model, prompt, thinking_capable):
        options = {key: self.policy[value] for key, value in (
            ('num_ctx', 'numCtx'), ('num_predict', 'numPredict'), ('temperature', 'temperature'), ('seed', 'seed'))}
        options.update(top_p=1, top_k=40, repeat_penalty=1.0)
        body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                'stream': False, 'keep_alive': '5m', 'options': options}
        if thinking_capable:
            body['think'] = False
        started = time.monotonic()
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

    def benchmark(self, model):
        installed = self.installed()
        if model not in installed:
            raise ValueError('Benchmark target must already be installed locally')
        gpu = self.check_idle(installed[model].get('size', 0))
        info = self.api('show', {'model': model})
        thinking = 'thinking' in info.get('capabilities', [])
        measurement = {'model': model, 'digest': installed[model]['digest'],
            'runtime': self.api('version'), 'details': info.get('details'),
            'modelParameters': info.get('parameters'), 'capabilities': info.get('capabilities'),
            'templateSha256': hashlib.sha256(info.get('template', '').encode()).hexdigest(),
            'policy': self.policy.copy(), 'gpuBefore': gpu, 'thinking': 'disabled' if thinking else 'not-supported',
            'loadTiming': 'Ollama model-load duration; not time to first token; warmup excluded from medians',
            'qualityScope': 'Small instruction-following checks; no coding-quality claim',
            'trials': [], 'checks': [], 'generatedCodeExecution': 'disabled'}
        self.report.setdefault('benchmarks', []).append(measurement)
        started_model = False
        try:
            started_model = True
            warmup = self.chat(model, 'Reply with exactly: ready', thinking)
            measurement['warmup'] = warmup
            measurement['loadedModel'] = self.api('ps').get('models', [])
            for trial in range(self.policy['repetitions']):
                short = self.chat(model, 'Write a 100 word description of the Rocky Mountains.', thinking)
                # Distinct first tokens prevent cross-trial prefix cache hits in the ingest measurement.
                filler = ('The quick brown fox jumps over the lazy dog. ' * 700)
                ingest = self.chat(model, f'Trial {trial + 1}.\n{filler}\nReply with the single word: acknowledged.', thinking)
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
            values = [row['short']['genTokPerSec'] for row in measurement['trials'] if row['short']['genTokPerSec'] is not None]
            wall = [row['short']['clientWallMs'] for row in measurement['trials']]
            measurement['summary'] = {'medianGenTokPerSec': statistics.median(values) if values else None,
                'minGenTokPerSec': min(values) if values else None, 'maxGenTokPerSec': max(values) if values else None,
                'medianClientWallMs': statistics.median(wall),
                'checksPassed': sum(row['passed'] for row in measurement['checks']), 'checksTotal': len(cases),
                'anyTruncated': any(row[kind]['truncated'] for row in measurement['trials'] for kind in ('short', 'ingest'))}
            measurement['status'] = 'completed'
            return measurement
        finally:
            if started_model:
                try:
                    # Only unload the target this run loaded; never stop another installed model.
                    self.api('generate', {'model': model, 'keep_alive': 0}, timeout=10)
                except Exception as exc:
                    measurement['unloadWarning'] = str(exc)

    def reserve(self, plan):
        ledger_path = self.state / 'nightly-ledger.json'
        ledger = read_json(ledger_path, {'days': {}})
        today = dt.date.today().isoformat()
        runs = ledger['days'].setdefault(today, [])
        if len(runs) >= self.policy['maxCandidatesPerDay']:
            raise RuntimeError('Daily candidate limit already used; failed attempts also consume the slot')
        runs.append({'runId': self.run_id, 'model': plan['model'], 'selection': plan['selection'],
                     'reservedBytes': plan['bytes'] if plan['kind'] == 'huggingface' and not plan['alreadyImported'] else 0,
                     'status': 'reserved', 'reservedAt': now()})
        atomic_json(ledger_path, ledger)

    def finish_reservation(self):
        path = self.state / 'nightly-ledger.json'
        ledger = read_json(path, {'days': {}})
        for runs in ledger['days'].values():
            for entry in runs:
                if entry['runId'] == self.run_id:
                    entry.update(status=self.report['status'], resultFile=self.report.get('resultFile'), finishedAt=now())
        atomic_json(path, ledger)

    def run_candidate(self, selection):
        self.report.update(mode='nightly', selection=selection)
        hour = dt.datetime.now().hour
        start, end = self.policy['benchmarkWindowStartHour'], self.policy['benchmarkWindowEndHour']
        in_window = (hour >= start or hour < end) if start > end else start <= hour < end
        if not in_window:
            self.report.update(status='deferred', reason='Daytime catch-up: benchmarks start only in the configured overnight window')
            return self.report
        plan = self.validate_candidate(selection)
        self.report['admission'] = plan
        installed = self.installed()
        baseline = self.policy['baselineModel']
        if baseline not in installed:
            raise ValueError('Configured baseline is not installed; report rather than download a second model')
        self.check_idle(max(plan['bytes'], installed[baseline].get('size', 0)))
        self.reserve(plan)  # Durable admission precedes every download, import, and inference side effect.
        try:
            if plan['kind'] == 'huggingface' and not plan['alreadyImported']:
                path = self.download(plan)
                plan['digest'] = self.import_model(plan, path)
            candidate = self.benchmark(plan['model'])
            baseline_name = self.policy['baselineModel']
            if baseline_name != plan['model']:
                baseline = self.benchmark(baseline_name)
                self.report['comparison'] = {'candidate': candidate['summary'], 'baseline': baseline['summary'],
                    'baselineModel': baseline_name, 'caveat': 'Same settings and machine; model templates and tokenizers differ.'}
            registry = self.registry()
            model_id = plan.get('repoId')
            if model_id in registry['models']:
                registry['models'][model_id].update(benchmarkStatus='completed', benchmarkRun=self.run_id,
                    benchmarkRevision=plan.get('revision'), benchmarkFile=plan.get('filename'))
                atomic_json(self.state / 'candidates.json', registry)
            self.report['status'] = 'completed'
        except Exception as exc:
            self.report.update(status='error', error=str(exc))
        finally:
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
    modes.add_argument('--benchmark')
    parser.add_argument('--top-n', type=int, default=25)
    parser.add_argument('--detail-cap', type=int, default=40)
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
                result = {'status': 'ok', 'plan': harness.validate_candidate(read_json(args.validate_candidate))}
            elif args.run_candidate:
                result = harness.run_candidate(read_json(args.run_candidate))
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


def supervised(argv):
    """A parent deadline also bounds stalled sockets and native imports."""
    root = Path(__file__).resolve().parent
    harness = Harness(root)
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', harness.run_id, *argv],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
        env=dict(os.environ, PYTHONUTF8='1'),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        output, errors = process.communicate(timeout=harness.policy['maxRuntimeSeconds'])
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
            harness.report.update(status='error', error='Hard runtime limit reached; worker stopped')
            harness.save_report()
            harness.finish_reservation()
        print(json.dumps(harness.report, indent=2))
        return 124


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--worker':
        sys.exit(main(sys.argv[3:], run_id=sys.argv[2]))
    sys.exit(supervised(sys.argv[1:]))
