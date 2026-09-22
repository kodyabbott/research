"""Replay pinned Windows benchmark cases on a local Ollama server.

No scheduler, downloads, model imports, or generated-code execution. Start a
dedicated server first. Results refuse changed artifacts or runtime versions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import urllib.request

REFERENCES = {
    'qwen3-coder:30b': '20260911-102013-bde53f62.json',
    'gpt-oss:20b': '20260911-102255-5507f7e0.json',
    'nightly-bench-d5808e5874e660a8:latest': '20260911-130939-8525ec43.json',
}
THROUGHPUT_REFERENCE = '20260911-130439-1c5fbf86.json'
OPTIONS = dict(num_ctx=8192, temperature=0, seed=42, top_p=1, top_k=40, repeat_penalty=1.0)


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def parameters(text):
    """Ollama prints parameter groups in nondeterministic map order."""
    groups = {}
    for line in (text or '').splitlines():
        if line.strip():
            key, value = line.split(None, 1)
            groups.setdefault(key, []).append(value.strip())
    return groups


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return {'exitCode': result.returncode, 'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()}


def host_snapshot():
    return {
        'capturedAt': now(),
        'chip': command(['sysctl', '-n', 'machdep.cpu.brand_string']),
        'memoryBytes': command(['sysctl', '-n', 'hw.memsize']),
        'cpuCores': command(['sysctl', '-n', 'hw.ncpu']),
        'os': command(['sw_vers']),
        'power': command(['pmset', '-g', 'batt']),
        'thermal': command(['pmset', '-g', 'therm']),
        'vm': command(['vm_stat']),
        'swap': command(['sysctl', '-n', 'vm.swapusage']),
        'caveat': 'Interactive desktop host; dedicated-host isolation and GPU utilization are not established. Unified memory is not discrete VRAM.',
    }


class Replay:
    def __init__(self, args):
        self.args = args
        self.root = args.repo / 'local-model-benchmarks'
        sys.path.insert(0, str(self.root))
        import quality_screen
        import workload_suite
        from nightly import Harness, exact_lines
        self.grade, self.exact_lines = quality_screen.grade, exact_lines
        self.measurement = Harness.measurement
        self.path = args.output
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise ValueError('Refusing to overwrite an existing raw run')
        self.deadline = time.monotonic() + 1800
        ref_path = self.root / 'runs' / REFERENCES[args.model]
        self.reference = json.loads(ref_path.read_text(encoding='utf-8-sig'))
        self.old = next(b for b in self.reference['benchmarks'] if b['model'] == args.model)
        self.protocol = self.reference['protocol']
        all_cases = workload_suite.cases()
        assert workload_suite.digest(all_cases) == self.protocol['suiteSha256']
        self.cases = [{k: row[k] for k in ('id', 'category', 'prompt', 'expected')} for row in self.old['cases']]
        assert self.cases == all_cases[:24], 'Saved cases differ from the checked-in suite'
        assert self.protocol['caseCount'] == 24 and self.protocol['caseOffset'] == 0
        self.report = {
            'schemaVersion': 1, 'startedAt': now(), 'status': 'running',
            'model': args.model, 'endpoint': args.endpoint, 'protocol': self.protocol,
            'reference': {'file': str(ref_path.relative_to(args.repo)), 'sha256': sha(ref_path),
                          'summary': self.old['summary']},
            'sourceCommit': command(['git', '-C', str(args.repo), 'rev-parse', 'HEAD'])['stdout'],
            'sourceHashes': {name: sha(self.root / name) for name in ('nightly.py', 'quality_screen.py', 'workload_suite.py', 'workload_screen.py', 'api_probe.py')},
            'runnerSha256': sha(__file__), 'hostBefore': host_snapshot(),
            'cases': [], 'options': OPTIONS, 'generatedCodeExecution': 'disabled',
            'timing': 'Client HTTP round trip and subprocess-supervised wall time recorded separately. Warmup excluded. Historical wall summaries include Python subprocess startup.',
        }

    def api(self, path, data=None, timeout=30):
        req = urllib.request.Request(self.args.endpoint + '/api/' + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)

    def chat(self, prompt, cap, thinking, supervised=True):
        seconds = min(120, self.deadline - time.monotonic())
        if seconds < 1:
            raise TimeoutError('Thirty-minute replay deadline reached')
        body = {'model': self.args.model, 'messages': [{'role': 'user', 'content': prompt}],
                'stream': False, 'keep_alive': '5m', 'options': {**OPTIONS, 'num_predict': cap}}
        if 'thinking' in self.info.get('capabilities', []):
            body['think'] = thinking
        start = time.monotonic()
        if supervised:
            result = subprocess.run([sys.executable, str(self.root / 'api_probe.py')],
                input=json.dumps({'url': self.args.endpoint + '/api/chat', 'body': body, 'seconds': seconds}),
                capture_output=True, text=True, timeout=seconds)
            if result.returncode:
                raise RuntimeError(result.stderr[-2000:])
            response = json.loads(result.stdout)
            response['supervisedWallMs'] = round((time.monotonic() - start) * 1000, 1)
        else:
            response = self.api('chat', body, seconds)
            response['clientWallMs'] = round((time.monotonic() - start) * 1000, 1)
        if not response.get('done'):
            raise RuntimeError('Incomplete response')
        return {'request': body, 'response': response}

    def unload(self):
        self.api('generate', {'model': self.args.model, 'keep_alive': 0}, timeout=30)
        for _ in range(30):
            rows = self.api('ps')['models']
            if not rows:
                return {'confirmed': True, 'confirmedAt': now(), 'loadedModels': rows}
            time.sleep(1)
        raise RuntimeError('Model unload not confirmed')

    def record(self):
        self.report['updatedAt'] = now()
        save(self.path, self.report)

    def throughput(self):
        ref_path = self.root / 'runs' / THROUGHPUT_REFERENCE
        previous = json.loads(ref_path.read_text())
        old = next(b for b in previous['benchmarks'] if b['model'] == self.args.model)
        result = {'referenceFile': str(ref_path.relative_to(self.args.repo)),
                  'referenceSha256': sha(ref_path), 'referenceSummary': old['summary'], 'trials': [], 'checks': []}
        self.report['throughput'] = result
        result['warmup'] = self.chat('Reply with exactly: ready', 512, False, supervised=False)
        result['loadedModel'] = self.api('ps')['models']
        for trial in range(3):
            short = self.chat('Write a 100 word description of the Rocky Mountains.', 512, False, supervised=False)
            filler = 'The quick brown fox jumps over the lazy dog. ' * 700
            ingest = self.chat(f'Trial {trial + 1}.\n{filler}\nReply with the single word: acknowledged.', 512, False, supervised=False)
            result['trials'].append({'trial': trial + 1, 'short': self.measurement(short['response']),
                'ingest': self.measurement(ingest['response']), 'shortExchange': short, 'ingestExchange': ingest})
            self.record()
        for name, prompt, expected in (
            ('sequence', 'Print the numbers 1 through 5, one per line. Output nothing else.', ['1','2','3','4','5']),
            ('arithmetic', 'What is 17 * 23? Output only the integer.', ['391']),
            ('extraction', 'Extract only the order ID from: Customer Mira, order AB-204, total $17. Output only the ID.', ['AB-204'])):
            exchange = self.chat(prompt, 512, False, supervised=False)
            result['checks'].append({'name': name, **exchange,
                'passed': self.exact_lines(exchange['response']['message']['content'], expected)})
        responses = [result['warmup']['response']] + [t[k]['response'] for t in result['trials'] for k in ('shortExchange','ingestExchange')] + [r['response'] for r in result['checks']]
        rates = [t['short']['genTokPerSec'] for t in result['trials']]
        result['summary'] = {'medianGenTokPerSec': statistics.median(rates), 'minGenTokPerSec': min(rates), 'maxGenTokPerSec': max(rates),
            'medianClientWallMs': statistics.median(t['short']['clientWallMs'] for t in result['trials']),
            'medianPromptTokPerSec': statistics.median(t['ingest']['promptTokPerSec'] for t in result['trials']),
            'checksPassed': sum(t['passed'] for t in result['checks']), 'checksTotal': 3,
            'unexpectedThinking': any(bool(r.get('message',{}).get('thinking','').strip()) for r in responses),
            'anyTruncated': any(r.get('done_reason') == 'length' for r in responses),
            'promptNearContextLimit': any(t['ingest']['promptTokens'] >= 8192 * .9 for t in result['trials'])}
        result['unload'] = self.unload()
        self.record()

    def run(self):
        loaded = False
        try:
            assert not self.api('ps')['models'], 'Dedicated server already has a loaded model'
            installed = {r['name']: r for r in self.api('tags')['models']}
            model = installed[self.args.model]
            runtime = self.api('version')
            self.info = self.api('show', {'model': self.args.model})
            template = hashlib.sha256(self.info.get('template', '').encode()).hexdigest()
            checks = {'modelDigest': model['digest'] == self.old['digest'],
                      'runtimeVersion': runtime == self.old['runtime'],
                      'templateHash': template == self.old['templateSha256'],
                      'parameters': parameters(self.info.get('parameters')) == parameters(self.old['modelParameters']),
                      'quantization': self.info.get('details') == self.old['details']}
            self.report.update(artifact=model, runtime=runtime, modelInfo=self.info, templateSha256=template, identityChecks=checks)
            if not all(checks.values()):
                raise ValueError('Historical identity mismatch: ' + str(checks))
            self.record()
            loaded = True
            if self.args.model != 'gpt-oss:20b':
                self.throughput()
            think = self.protocol['thinking']
            self.report['warmup'] = self.chat('Reply with exactly: ready', 512, think)
            self.report['loadedModel'] = self.api('ps')['models']
            for row in self.cases:
                exchange = self.chat(row['prompt'], self.protocol['outputCap'], think)
                response = exchange['response']
                msg = response.get('message', {})
                truncated = response.get('done_reason') == 'length'
                self.report['cases'].append({**row, **exchange,
                    'passed': not truncated and self.grade(msg.get('content'), row['expected']),
                    'truncated': truncated, 'unexpectedThinking': not think and bool(msg.get('thinking', '').strip())})
                self.record()
                print(f"{self.args.model}: {len(self.report['cases'])}/24", flush=True)
            rows = self.report['cases']
            self.report['summary'] = {'passed': sum(r['passed'] for r in rows), 'attempted': len(rows),
                'medianWallMs': statistics.median(r['response']['supervisedWallMs'] for r in rows),
                'medianClientWallMs': statistics.median(r['response']['clientWallMs'] for r in rows),
                'totalWallMs': sum(r['response']['supervisedWallMs'] for r in rows),
                'medianGenTokPerSec': statistics.median(r['response']['eval_count'] * 1e9 / r['response']['eval_duration'] for r in rows),
                'truncated': sum(r['truncated'] for r in rows),
                'unexpectedThinking': any(r['unexpectedThinking'] for r in rows),
                'protocolValid': len(rows) == 24 and not any(r['unexpectedThinking'] for r in rows)}
            self.report['status'] = 'completed'
        except Exception as exc:
            self.report.update(status='error', error=str(exc))
            raise
        finally:
            if loaded:
                try:
                    self.report['unload'] = self.unload()
                except Exception as exc:
                    self.report.update(status='error', cleanupError=str(exc))
            self.report.update(hostAfter=host_snapshot(), finishedAt=now())
            self.record()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--model', choices=REFERENCES, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:11436')
    args = parser.parse_args()
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]+', args.endpoint) or args.endpoint.endswith(':11434'):
        parser.error('Use a dedicated loopback Ollama port, not the personal default server')
    Replay(args).run()


if __name__ == '__main__':
    main()
