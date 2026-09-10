"""Offline regression and admission tests. No model downloads or inference."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import nightly


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.policy = json.loads(Path(__file__).with_name('policy.json').read_text())
        self.policy['ollamaModelsDir'] = str(self.root / 'ollama')
        (self.root / 'policy.json').write_text(json.dumps(self.policy))
        self.h = nightly.Harness(self.root)
        self.h.state.mkdir()
        self.selection = {'kind': 'huggingface', 'repoId': 'ggml-org/example', 'revision': 'a' * 40,
            'filename': 'example-Q4_K_M.gguf', 'rationale': 'Compare a different architecture on the fixed local battery.',
            'modelCardUrl': nightly.HF + '/ggml-org/example'}
        self.contents = b'GGUFunit-test-only-not-a-real-model'
        self.sha = hashlib.sha256(self.contents).hexdigest()
        self.detail = {'sha': 'a' * 40, 'gated': False, 'pipeline_tag': 'text-generation',
            'siblings': [{'rfilename': self.selection['filename'], 'size': len(self.contents),
                          'lfs': {'sha256': self.sha, 'size': len(self.contents)}}]}
        self.h.installed = lambda: {}
        self.h.storage_check = lambda size, models: None
        self.h.request = lambda *args, **kwargs: copy.deepcopy(self.detail)

    def test_deferred_details_survive_and_retry_after_leaving_trending(self):
        trending = [{'id': 'test/model' + str(i), 'pipeline_tag': 'text-generation', 'trendingScore': 10-i} for i in range(4)]
        calls = []
        def request(url, *args, **kwargs):
            if '/api/models?' in url:
                return trending
            calls.append(url)
            return {'sha': 'b' * 40, 'pipeline_tag': 'text-generation', 'safetensors': {'total': 1000000000}}
        self.h.request = request
        first = copy.deepcopy(self.h.discover(detail_cap=2))
        self.assertEqual(first['newCount'], 4)
        self.assertEqual(first['metadataPending'], 2)
        trending[:] = trending[:1]
        second = self.h.discover(detail_cap=2)
        self.assertEqual(second['newCount'], 0)
        self.assertEqual(second['metadataPending'], 0)
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(self.h.pending()), 4)

    def test_legacy_seen_entries_become_pending_without_erasing_original(self):
        legacy = {'test/old-model': '2026-08-15'}
        nightly.atomic_json(self.h.state / 'seen.json', legacy)
        registry = self.h.registry()
        self.assertEqual(registry['models']['test/old-model']['detailStatus'], 'pending')
        self.assertEqual(nightly.read_json(self.h.state / 'seen.json'), legacy)

    def test_all_sources_failing_is_error_and_preserves_state(self):
        original = {'schemaVersion': 2, 'models': {}}
        nightly.atomic_json(self.h.state / 'candidates.json', original)
        self.h.request = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('offline'))
        result = self.h.discover()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(len(result['sourceFailures']), 6)
        self.assertEqual(nightly.read_json(self.h.state / 'candidates.json'), original)

    def test_partial_source_failure_is_explicit(self):
        def request(url, *args, **kwargs):
            if 'pipeline_tag=text-to-image' in url:
                raise OSError('offline')
            if '/api/models?' in url:
                return [{'id': 'test/model', 'pipeline_tag': 'text-generation'}]
            return {'sha': 'b' * 40}
        self.h.request = request
        result = self.h.discover()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(result['sourceFailures']), 1)

    def test_failed_detail_is_retried(self):
        fail = [True]
        def request(url, *args, **kwargs):
            if '/api/models?' in url:
                return [{'id': 'test/model', 'pipeline_tag': 'text-generation'}]
            if fail[0]:
                raise OSError('transient failure')
            return {'sha': 'b' * 40}
        self.h.request = request
        self.assertEqual(self.h.discover()['metadataPending'], 1)
        fail[0] = False
        self.assertEqual(self.h.discover()['metadataPending'], 0)

    def test_gguf_sizes_do_not_require_safetensors(self):
        fit = self.h.fit(self.detail)
        self.assertEqual(fit['fitStatus'], 'file-sizes-available')
        self.assertEqual(fit['ggufFiles'][0]['bytes'], len(self.contents))
        self.assertIsNone(fit['paramsB'])

    def test_exact_output_rejects_false_positives(self):
        expected = ['1', '2', '3', '4', '5']
        self.assertTrue(nightly.exact_lines('1\r\n2\r\n3\r\n4\r\n5\r\n', expected))
        for bad in ('1\n1\n1\n1\n1', '5\n4\n3\n2\n1', 'extra\n1\n2\n3\n4\n5', '1 2 3 4 5'):
            self.assertFalse(nightly.exact_lines(bad, expected))

    def test_selection_pins_file_size_hash_and_revision(self):
        plan = self.h.validate_candidate(self.selection)
        self.assertEqual(plan['sha256'], self.sha)
        self.assertEqual(plan['bytes'], len(self.contents))
        self.assertTrue(plan['model'].startswith(nightly.OWNED_PREFIX))

    def test_unapproved_or_moving_or_split_sources_rejected(self):
        changes = [{'repoId': 'unknown/example'}, {'revision': 'main'},
            {'filename': '../escape.gguf'}, {'filename': 'model-00001-of-00002.gguf'},
            {'filename': 'installer.py'}, {'modelCardUrl': 'https://example.com'}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.h.validate_candidate(self.selection | change)

    def test_oversize_download_rejected(self):
        self.detail['siblings'][0]['size'] = 21 * nightly.GIB
        with self.assertRaisesRegex(ValueError, 'download budget'):
            self.h.validate_candidate(self.selection)

    def test_gated_or_missing_checksum_rejected(self):
        self.detail['gated'] = 'auto'
        with self.assertRaises(ValueError):
            self.h.validate_candidate(self.selection)
        self.detail['gated'] = False
        self.detail['siblings'][0]['lfs'] = {}
        with self.assertRaises(ValueError):
            self.h.validate_candidate(self.selection)

    def test_installed_model_digest_must_match(self):
        self.h.installed = lambda: {'example:latest': {'digest': 'b' * 64, 'size': 100}}
        selection = {'kind': 'installed', 'model': 'example:latest', 'expectedDigest': 'c' * 64,
            'rationale': self.selection['rationale']}
        with self.assertRaises(ValueError):
            self.h.validate_candidate(selection)
        self.assertEqual(self.h.validate_candidate(selection | {'expectedDigest': 'b' * 64})['kind'], 'installed')

    def test_task_name_without_matching_provenance_rejected(self):
        name = nightly.OWNED_PREFIX + self.sha[:16] + ':latest'
        self.h.installed = lambda: {name: {'digest': 'b' * 64, 'size': 100}}
        with self.assertRaisesRegex(ValueError, 'matching recorded'):
            self.h.validate_candidate(self.selection)

    def test_daily_limit_persists_across_processes_even_on_failed_run(self):
        plan = self.h.validate_candidate(self.selection)
        self.h.reserve(plan)
        self.h.report['status'] = 'error'
        self.h.finish_reservation()
        other = nightly.Harness(self.root)
        with self.assertRaisesRegex(RuntimeError, 'Daily candidate limit'):
            other.reserve(plan)

    def test_disk_reserve_includes_download_and_import_copy(self):
        self.h.storage_check = nightly.Harness.storage_check.__get__(self.h)
        with patch('nightly.shutil.disk_usage', return_value=type('Disk', (), {'free': 26 * nightly.GIB})()):
            with self.assertRaisesRegex(RuntimeError, 'free-disk reserve'):
                self.h.storage_check(1 * nightly.GIB, {})

    def test_owned_budget_accounts_for_failed_imports(self):
        self.h.storage_check = nightly.Harness.storage_check.__get__(self.h)
        nightly.atomic_json(self.h.state / 'nightly-ledger.json', {'days': {'2026-09-01': [
            {'model': 'nightly-bench-old', 'reservedBytes': 59 * nightly.GIB}]}})
        with self.assertRaisesRegex(RuntimeError, 'storage budget'):
            self.h.storage_check(nightly.GIB, {})

    def test_busy_gpu_or_ollama_skips_without_unloading(self):
        self.h.api = lambda *args, **kwargs: {'models': [{'name': 'user-work'}]}
        with self.assertRaisesRegex(RuntimeError, 'already serving'):
            self.h.check_idle()
        self.h.api = lambda *args, **kwargs: {'models': []}
        self.h.gpu = lambda: {'freeGiB': 90, 'utilizationPercent': 90}
        with self.assertRaisesRegex(RuntimeError, 'GPU is busy'):
            self.h.check_idle()

    def test_download_verifies_hash_and_does_not_leave_bad_file(self):
        plan = self.h.validate_candidate(self.selection)
        with patch('nightly.urllib.request.urlopen', return_value=io.BytesIO(self.contents)), \
             patch('nightly.shutil.disk_usage', return_value=type('Disk', (), {'free': 100 * nightly.GIB})()):
            path = self.h.download(plan)
        self.assertEqual(path.read_bytes(), self.contents)
        path.unlink()
        with patch('nightly.urllib.request.urlopen', return_value=io.BytesIO(b'GGUFwrong')), \
             patch('nightly.shutil.disk_usage', return_value=type('Disk', (), {'free': 100 * nightly.GIB})()):
            with self.assertRaisesRegex(ValueError, 'size or SHA-256'):
                self.h.download(plan)
        self.assertEqual(list((self.h.state / 'downloads').iterdir()), [])

    def test_download_rejects_bytes_beyond_declared_size(self):
        plan = self.h.validate_candidate(self.selection)
        with patch('nightly.urllib.request.urlopen', return_value=io.BytesIO(self.contents + b'extra')):
            with self.assertRaisesRegex(ValueError, 'declared size'):
                self.h.download(plan)

    def test_chat_pins_context_sampling_and_output_cap(self):
        calls = []
        self.h.api = lambda path, body, **kwargs: (calls.append(body) or {'done': True})
        self.h.chat('example:latest', 'hello', True)
        self.assertEqual(calls[0]['options']['num_ctx'], 8192)
        self.assertEqual(calls[0]['options']['num_predict'], 512)
        self.assertEqual(calls[0]['options']['temperature'], 0)
        self.assertEqual(calls[0]['options']['seed'], 42)
        self.assertFalse(calls[0]['think'])

    def test_metrics_exclude_cached_prompt_tokens_and_flag_truncation(self):
        result = self.h.measurement({'prompt_eval_count': 7000, 'prompt_eval_cached_count': 2000,
            'prompt_eval_duration': 1000000000, 'eval_count': 10, 'eval_duration': 1000000000,
            'clientWallMs': 2000, 'done_reason': 'length'})
        self.assertEqual(result['promptTokPerSec'], 5000)
        self.assertTrue(result['truncated'])

    def test_expired_runtime_blocks_requests(self):
        self.h.deadline = time.monotonic() - 1
        with self.assertRaises(TimeoutError):
            self.h.remaining()

    def test_daytime_catchup_does_not_download_or_reserve(self):
        self.h.policy['benchmarkWindowStartHour'] = (nightly.dt.datetime.now().hour + 1) % 24
        self.h.policy['benchmarkWindowEndHour'] = (nightly.dt.datetime.now().hour + 2) % 24
        with patch.object(self.h, 'download', side_effect=AssertionError('must not download')):
            self.assertEqual(self.h.run_candidate(self.selection)['status'], 'deferred')
        self.assertFalse((self.h.state / 'nightly-ledger.json').exists())

    def test_lock_prevents_a_second_process(self):
        # A real second process verifies Windows file-lock semantics rather than mocking them.
        lock = self.h.state / 'lock'
        command = 'from pathlib import Path; import nightly;\nwith nightly.state_lock(Path(' + repr(str(lock)) + ')):\n print("unexpected")'
        with nightly.state_lock(lock):
            result = subprocess.run([nightly.sys.executable, '-c', command], capture_output=True, text=True,
                                    cwd=Path(__file__).parent, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('holds the state lock', result.stderr)

    def test_candidate_and_baseline_complete_with_persisted_ledger(self):
        hour = nightly.dt.datetime.now().hour
        self.h.policy.update(benchmarkWindowStartHour=hour, benchmarkWindowEndHour=(hour + 1) % 24)
        model = 'candidate:latest'
        self.h.installed = lambda: {model: {'digest': 'b' * 64, 'size': 100},
            self.policy['baselineModel']: {'digest': 'c' * 64, 'size': 100}}
        self.h.check_idle = lambda *args: {}
        calls = []
        self.h.benchmark = lambda name: (calls.append(name) or {'summary': {'medianGenTokPerSec': 1}})
        selection = {'kind': 'installed', 'model': model, 'expectedDigest': 'b' * 64,
            'rationale': self.selection['rationale']}
        result = self.h.run_candidate(selection)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(calls, [model, self.policy['baselineModel']])
        ledger = nightly.read_json(self.h.state / 'nightly-ledger.json')
        entry = next(iter(ledger['days'].values()))[0]
        self.assertEqual(entry['status'], 'completed')
        self.assertTrue((self.root / entry['resultFile']).exists())

    def test_supervisor_stops_worker_at_hard_deadline(self):
        source = Path(__file__).with_name('nightly.py')
        (self.root / 'nightly.py').write_bytes(source.read_bytes())
        policy = self.policy | {'maxRuntimeSeconds': 0.001}
        (self.root / 'policy.json').write_text(json.dumps(policy))
        result = subprocess.run([nightly.sys.executable, str(self.root / 'nightly.py'), '--pending'],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertIn('Hard runtime limit', result.stdout)

    def test_supervisor_forwards_json_to_calling_shell(self):
        source = Path(__file__).with_name('nightly.py')
        (self.root / 'nightly.py').write_bytes(source.read_bytes())
        result = subprocess.run([nightly.sys.executable, str(self.root / 'nightly.py'), '--pending'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'ok')


if __name__ == '__main__':
    unittest.main(verbosity=2)
