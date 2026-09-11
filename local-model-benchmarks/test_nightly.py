"""Offline regression and admission tests. No model downloads or inference."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import socket
import http.server
import threading
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

import nightly
import owned_runtime
import background
from contextlib import contextmanager


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.policy = json.loads(Path(__file__).with_name('policy.json').read_text())
        self.policy['benchmarkWindowStartMinute'] = 0
        self.policy['benchmarkWindowEndMinute'] = 0
        self.policy['ollamaModelsDir'] = str(self.root / 'ollama')
        self.policy['taskStorageRoot'] = str(self.root / 'cache')
        self.policy['ollamaModelsDir'] = str(self.root / 'cache' / 'ollama')
        self.policy['downloadDir'] = str(self.root / 'cache' / 'downloads')
        self.policy['idleWaitSeconds'] = 0
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
        self.h.storage_check = lambda *args: None
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
        self.detail['siblings'][0]['size'] = (self.policy['maxDownloadGiB'] + 1) * nightly.GIB
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
        with patch('nightly.tree_bytes', side_effect=[0, 239 * nightly.GIB]):
            with self.assertRaisesRegex(RuntimeError, 'storage budget'):
                self.h.storage_check(nightly.GIB, {})

    def test_old_reservations_do_not_charge_deleted_bytes(self):
        self.h.storage_check = nightly.Harness.storage_check.__get__(self.h)
        nightly.atomic_json(self.h.ledger_path, {'days': {'2026-09-01': [
            {'model': 'nightly-bench-old', 'reservedBytes': 1000 * nightly.GIB}]}})
        with patch('nightly.shutil.disk_usage', return_value=type('Disk', (), {'free': 100 * nightly.GIB})()):
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
        with patch('nightly.urllib.request.urlopen', return_value=io.BytesIO(b'GGUF' + b'x' * (len(self.contents) - 4))), \
             patch('nightly.shutil.disk_usage', return_value=type('Disk', (), {'free': 100 * nightly.GIB})()):
            with self.assertRaisesRegex(ValueError, 'size or SHA-256'):
                self.h.download(plan)
        self.assertEqual(list(self.h.download_dir.iterdir()), [])

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

    def test_minute_precision_overnight_window_boundaries(self):
        policy = {'benchmarkWindowStartHour': 20, 'benchmarkWindowStartMinute': 15,
                  'benchmarkWindowEndHour': 6}
        for clock, expected in [('20:00:00', False), ('20:14:59', False), ('20:15:00', True),
                                ('23:59:59', True), ('00:00:00', True), ('05:59:59', True),
                                ('06:00:00', False), ('12:00:00', False)]:
            with self.subTest(clock=clock):
                instant = nightly.dt.datetime.fromisoformat('2026-09-10T' + clock)
                self.assertEqual(nightly.benchmark_window_open(policy, instant), expected)

    def test_window_defaults_and_non_overnight_windows(self):
        legacy = {'benchmarkWindowStartHour': 21, 'benchmarkWindowEndHour': 6}
        self.assertFalse(nightly.benchmark_window_open(legacy, nightly.dt.datetime(2026, 9, 10, 20, 59)))
        self.assertTrue(nightly.benchmark_window_open(legacy, nightly.dt.datetime(2026, 9, 10, 21)))
        daytime = {'benchmarkWindowStartHour': 8, 'benchmarkWindowStartMinute': 15,
                   'benchmarkWindowEndHour': 8, 'benchmarkWindowEndMinute': 45}
        for minute, expected in [(14, False), (15, True), (44, True), (45, False)]:
            self.assertEqual(nightly.benchmark_window_open(daytime, nightly.dt.datetime(2026, 9, 10, 8, minute)), expected)
        self.assertFalse(nightly.benchmark_window_open({'benchmarkWindowStartHour': 8,
            'benchmarkWindowEndHour': 8}, nightly.dt.datetime(2026, 9, 10, 8)))

    def test_invalid_window_values_are_rejected(self):
        policy = {'benchmarkWindowStartHour': 20, 'benchmarkWindowStartMinute': 15,
                  'benchmarkWindowEndHour': 6}
        for key, value in [('benchmarkWindowStartHour', 24), ('benchmarkWindowEndHour', -1),
                           ('benchmarkWindowStartMinute', 60), ('benchmarkWindowEndMinute', -1),
                           ('benchmarkWindowStartMinute', '15'), ('benchmarkWindowStartMinute', True)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                nightly.benchmark_window_open(policy | {key: value})

    def test_before_start_minute_does_not_touch_runtime_or_quota(self):
        self.h.policy.update(benchmarkWindowStartHour=20, benchmarkWindowStartMinute=15,
                             benchmarkWindowEndHour=6, benchmarkWindowEndMinute=0)
        instant = nightly.dt.datetime(2026, 9, 10, 20, 14, 59)
        with patch.object(nightly.dt, 'datetime', wraps=nightly.dt.datetime) as clock, \
             patch.object(self.h, 'installed', side_effect=AssertionError('must not contact runtime')), \
             patch.object(self.h, 'reserve', side_effect=AssertionError('must not reserve quota')), \
             patch.object(self.h, 'download', side_effect=AssertionError('must not download')):
            clock.now.return_value = instant
            self.assertEqual(self.h.run_candidate(self.selection)['status'], 'deferred')
        self.assertFalse((self.h.state / 'nightly-ledger.json').exists())

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

    def test_duplicate_before_reservation_is_admission_failure(self):
        model = 'candidate:latest'
        self.h.installed = lambda: {model: {'digest': 'b' * 64, 'size': 100},
            self.policy['baselineModel']: {'digest': 'c' * 64, 'size': 100}}
        self.h.wait_idle = lambda *args: {}
        nightly.atomic_json(self.h.state / 'acceptance-ledger.json', {'days': {
            nightly.dt.date.today().isoformat(): [{'model': model, 'status': 'completed'}]}})
        selection = {'kind': 'installed', 'model': model, 'expectedDigest': 'b' * 64,
                     'rationale': self.selection['rationale']}
        with patch.object(self.h, 'benchmark', side_effect=AssertionError('must not benchmark')):
            result = self.h.run_candidate(selection, acceptance_validation=True)
        self.assertEqual(result['failureKind'], 'admission')
        self.assertIn('already used its daily slot', result['error'])

    def test_invalid_comparison_records_the_truncation_reason(self):
        model = 'candidate:latest'
        self.h.installed = lambda: {model: {'digest': 'b' * 64, 'size': 100},
            self.policy['baselineModel']: {'digest': 'c' * 64, 'size': 100}}
        self.h.wait_idle = lambda *args: {}
        self.h.benchmark = lambda name: {'status': 'completed', 'summary': {
            'anyTruncated': name == model, 'promptNearContextLimit': False}}
        selection = {'kind': 'installed', 'model': model, 'expectedDigest': 'b' * 64,
                     'rationale': self.selection['rationale']}
        result = self.h.run_candidate(selection, acceptance_validation=True)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['comparison']['valid'])
        self.assertEqual(result['comparison']['invalidReason'], 'candidate: output truncated')

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
        (self.root / 'owned_runtime.py').write_bytes(source.with_name('owned_runtime.py').read_bytes())
        policy = self.policy | {'maxRuntimeSeconds': 0.001}
        (self.root / 'policy.json').write_text(json.dumps(policy))
        result = subprocess.run([nightly.sys.executable, str(self.root / 'nightly.py'), '--pending'],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertIn('Hard runtime limit', result.stdout)

    def test_deadline_recovery_waits_for_port_even_when_vram_is_already_free(self):
        record = {'host': 'fixture', 'pid': 123, 'processIdentity': {'imagePath': 'fixture', 'creationFileTime': '1'}}
        self.h.report.update(secondaryRuntime=record, gpuBefore={'freeGiB': 90})
        nightly.atomic_json(self.h.state / 'secondary-process.json', record)
        self.h.gpu = lambda: {'freeGiB': 90}
        worker = Mock()
        worker.communicate.side_effect = subprocess.TimeoutExpired('fixture', 1)
        output = io.StringIO()
        with patch('nightly.Harness', return_value=self.h), \
             patch('nightly.subprocess.Popen', return_value=worker), \
             patch('nightly.subprocess.run'), \
             patch('nightly.process_identity', return_value=None), \
             patch('nightly.port_open', side_effect=[True, True, False]) as port, \
             patch('nightly.time.sleep') as sleep, nightly.contextlib.redirect_stdout(output):
            code = nightly.supervised([], worker_command=lambda run_id: ['fixture'], timeout=1)
        self.assertEqual(code, 124)
        recovery = json.loads(output.getvalue())['deadlineRecovery']
        self.assertTrue(recovery['portFree'])
        self.assertTrue(recovery['vramRecovered'])
        self.assertEqual(port.call_count, 3)
        sleep.assert_called_once()
        self.assertTrue(recovery['ownedProcessExited'])
        self.assertEqual(nightly.read_json(self.h.state / 'secondary-process.json')['stopReason'], 'hard-runtime-limit')

    def test_supervisor_forwards_json_to_calling_shell(self):
        source = Path(__file__).with_name('nightly.py')
        (self.root / 'nightly.py').write_bytes(source.read_bytes())
        (self.root / 'owned_runtime.py').write_bytes(source.with_name('owned_runtime.py').read_bytes())
        result = subprocess.run([nightly.sys.executable, str(self.root / 'nightly.py'), '--pending'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'ok')

    def test_revision_refresh_works_without_sha_in_trending(self):
        nightly.atomic_json(self.h.state / 'candidates.json', {'schemaVersion': 2, 'models': {
            'test/model': {'modelId': 'test/model', 'pipeline': 'text-generation',
                'detailStatus': 'ready', 'detailCheckedAt': '2026-01-01T00:00:00+00:00',
                'revision': 'a' * 40, 'benchmarkStatus': 'completed'}}})
        self.h.request = lambda url: ([{'id': 'test/model', 'pipeline_tag': 'text-generation'}]
            if '/api/models?' in url else {'sha': 'b' * 40, 'pipeline_tag': 'text-generation'})
        self.h.discover()
        row = self.h.registry()['models']['test/model']
        self.assertEqual(row['revision'], 'b' * 40)
        self.assertEqual(row['benchmarkStatus'], 'not-run')

    def test_stale_port_defers_without_spawning_or_killing(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            self.h.policy['secondaryPort'] = listener.getsockname()[1]
            with patch('owned_runtime.subprocess.Popen', side_effect=AssertionError('must not start')), \
                 patch('owned_runtime.stop_tree', side_effect=AssertionError('must not stop')):
                with self.assertRaisesRegex(owned_runtime.RuntimeBusy, 'occupied'):
                    with owned_runtime.secondary(self.h):
                        self.fail('must refuse an occupied port')
            self.assertTrue(owned_runtime.port_open(self.h.policy['secondaryPort']))

    def test_cleanup_cannot_target_primary(self):
        with self.assertRaisesRegex(RuntimeError, 'secondary'):
            self.h.cleanup()

    def test_resume_rehashes_partial_and_requests_exact_range(self):
        plan = self.h.validate_candidate(self.selection)
        self.h.download_dir.mkdir(parents=True)
        partial = self.h.download_dir / (plan['sha256'] + '.part')
        partial.write_bytes(self.contents[:10])
        response = io.BytesIO(self.contents[10:])
        response.status = 206
        response.headers = {'Content-Range': f'bytes 10-{len(self.contents)-1}/{len(self.contents)}'}
        with patch('nightly.urllib.request.urlopen', return_value=response) as request:
            path = self.h.download(plan)
        self.assertEqual(request.call_args.args[0].get_header('Range'), 'bytes=10-')
        self.assertEqual(path.read_bytes(), self.contents)
        self.assertEqual(self.h.report['download']['resumedFromBytes'], 10)

    def test_short_network_response_keeps_partial_for_next_night(self):
        plan = self.h.validate_candidate(self.selection)
        with patch('nightly.urllib.request.urlopen', return_value=io.BytesIO(self.contents[:10])):
            with self.assertRaisesRegex(OSError, 'retained'):
                self.h.download(plan)
        self.assertEqual((self.h.download_dir / (plan['sha256'] + '.part')).read_bytes(), self.contents[:10])

    def test_ignored_range_restarts_instead_of_appending(self):
        plan = self.h.validate_candidate(self.selection)
        self.h.download_dir.mkdir(parents=True)
        (self.h.download_dir / (plan['sha256'] + '.part')).write_bytes(self.contents[:10])
        with patch('nightly.urllib.request.urlopen', return_value=io.BytesIO(self.contents)):
            path = self.h.download(plan)
        self.assertEqual(path.read_bytes(), self.contents)
        self.assertTrue(self.h.report['download']['rangeIgnoredRestarted'])

    def test_unload_waits_for_empty_server_and_vram_recovery(self):
        self.h.api = lambda *args, **kwargs: {'models': []}
        snapshots = iter([{'freeGiB': 50}, {'freeGiB': 90}])
        self.h.gpu = lambda: next(snapshots)
        with patch('nightly.time.sleep'):
            self.h.confirm_unloaded('example:latest', 90)
        self.assertEqual(self.h.report['unloads'][0]['gpuAfter']['freeGiB'], 90)

    def test_thinking_probe_is_separate_and_preserves_answer_lengths(self):
        self.h.chat = lambda *args, **kwargs: {'done': True, 'message': {'thinking': 'abc', 'content': 'defg'},
            'clientWallMs': 200, 'eval_count': 10, 'eval_duration': 100000000, 'done_reason': 'stop'}
        probe = self.h.thinking_probe('example:latest', True, {'medianClientWallMs': 100})
        self.assertFalse(probe['includedInThroughputMedians'])
        self.assertEqual((probe['thinkingCharacters'], probe['answerCharacters']), (3, 4))
        self.assertEqual(probe['wallTimeRatioToThinkingOffMedian'], 2)

    def uploaded_blob_fixture(self):
        self.h.endpoint = 'http://127.0.0.1:11435'
        self.h.secondary_process = object()
        self.h.api = lambda *args: {'models': []}
        name = nightly.OWNED_PREFIX + self.sha[:16] + ':latest'
        blob = self.h.models_dir / 'blobs' / ('sha256-' + self.sha)
        blob.parent.mkdir(parents=True)
        blob.write_bytes(self.contents)
        marker = Path(self.h.policy['taskStorageRoot']) / '.nightly-benchmark.json'
        nightly.atomic_json(marker, {'schemaVersion': 1, 'project': str(self.root.resolve())})
        manifest = self.h.models_dir / 'manifests' / 'registry.ollama.ai' / 'library' / name.split(':')[0] / 'latest'
        data = {'schemaVersion': 2, 'config': {'digest': 'sha256:' + 'c' * 64},
                'layers': [{'digest': 'sha256:' + 'd' * 64}]}
        nightly.atomic_json(manifest, data)
        digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
        provenance = {'sha256': self.sha, 'bytes': len(self.contents), 'digest': digest}
        self.h.installed = lambda: {name: {'digest': digest}}
        return name, provenance, blob, manifest

    def test_prune_only_verified_unreferenced_upload_and_journal_before_deletion(self):
        name, provenance, blob, manifest = self.uploaded_blob_fixture()
        unrelated = blob.with_name('sha256-' + 'e' * 64)
        unrelated.write_bytes(b'unknown orphan')
        original_unlink = Path.unlink
        def unlink(path, *args, **kwargs):
            if path == blob:
                journal = nightly.read_json(self.h.state / 'blob-deletions.json')
                self.assertEqual(journal['deletions'][-1]['status'], 'requested')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', unlink):
            result = owned_runtime.prune_uploaded_blob(self.h, name, provenance)
        self.assertEqual(result['status'], 'deleted')
        self.assertFalse(blob.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(manifest.exists())

    def test_prune_preserves_upload_referenced_by_any_private_manifest(self):
        name, provenance, blob, manifest = self.uploaded_blob_fixture()
        other = manifest.parent.parent / 'another-model' / 'latest'
        nightly.atomic_json(other, {'schemaVersion': 2, 'config': {'digest': 'sha256:' + 'c' * 64},
            'layers': [{'digest': 'sha256:' + self.sha}]})
        self.assertIsNone(owned_runtime.prune_uploaded_blob(self.h, name, provenance))
        self.assertTrue(blob.exists())

    def test_prune_refuses_changed_upload_and_changed_manifest(self):
        name, provenance, blob, manifest = self.uploaded_blob_fixture()
        blob.write_bytes(b'x' * len(self.contents))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            owned_runtime.prune_uploaded_blob(self.h, name, provenance)
        self.assertTrue(blob.exists())
        blob.write_bytes(self.contents)
        manifest.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'manifest no longer matches'):
            owned_runtime.prune_uploaded_blob(self.h, name, provenance)
        self.assertTrue(blob.exists())

    def test_storage_reserves_upload_and_rewritten_copy(self):
        self.h.storage_check = nightly.Harness.storage_check.__get__(self.h)
        with patch('nightly.shutil.disk_usage', return_value=type('Disk', (), {'free': 27 * nightly.GIB})()):
            with self.assertRaisesRegex(RuntimeError, 'free-disk reserve'):
                self.h.storage_check(nightly.GIB, {})
        self.assertEqual(self.h.report['storageAccounting']['newCopyAllowanceBytes'], 3 * nightly.GIB)

    def test_cleanup_three_completed_imports_deletes_only_oldest_and_releases_reservation(self):
        self.h.endpoint = 'http://127.0.0.1:11435'
        self.h.secondary_process = object()
        imports, installed, entries = {}, {}, []
        for i in range(3):
            name = f'nightly-bench-{i}:latest'
            digest = str(i) * 64
            run_id = f'20260910-12000{i}-abcdef01'
            imports[name] = {'digest': digest, 'completedRun': run_id, 'completedAt': str(i)}
            installed[name] = {'digest': digest, 'size': 100}
            entries.append({'model': name, 'reservedBytes': 100})
            nightly.atomic_json(self.root / 'runs' / (run_id + '.json'), {'status': 'completed',
                'benchmarks': [{'model': name, 'digest': digest, 'status': 'completed'}]})
        installed['personal:latest'] = {'digest': 'x' * 64, 'size': 999}
        nightly.atomic_json(self.h.state / 'imports.json', imports)
        nightly.atomic_json(self.h.ledger_path, {'days': {'2026-09-10': entries}})
        self.h.installed = lambda: copy.deepcopy(installed)
        self.h.api = lambda *args: {'models': []}
        def delete(request, **kwargs):
            self.assertEqual(request.full_url, self.h.endpoint + '/api/delete')
            self.assertEqual(request.method, 'DELETE')
            self.assertEqual(nightly.read_json(self.h.ledger_path)['deletions'][-1]['status'], 'requested')
            installed.pop(json.loads(request.data)['model'])
            return io.BytesIO(b'')
        with patch('nightly.urllib.request.urlopen', side_effect=delete):
            self.h.cleanup()
        self.assertEqual(set(installed), {'nightly-bench-1:latest', 'nightly-bench-2:latest', 'personal:latest'})
        ledger = nightly.read_json(self.h.ledger_path)
        self.assertEqual(ledger['days']['2026-09-10'][0]['reservedBytes'], 0)
        self.assertEqual(len(ledger['deletions']), 1)

    def test_mismatched_versions_refused_before_reservation(self):
        self.h.installed = lambda: {'candidate:latest': {'digest': 'b' * 64, 'size': 100},
            self.policy['baselineModel']: {'digest': 'c' * 64, 'size': 100}}
        self.h.wait_idle = lambda *args: {}
        versions = iter([{'version': '1'}, {'version': '2'}])
        self.h.api = lambda *args: next(versions)
        result = self.h.run_candidate({'kind': 'installed', 'model': 'candidate:latest',
            'expectedDigest': 'b' * 64, 'rationale': self.selection['rationale']}, acceptance_validation=True)
        self.assertEqual(result['status'], 'deferred')
        self.assertFalse(result['runtimeVersions']['match'])
        self.assertFalse(self.h.ledger_path.exists())

    def test_refresh_budget_leaves_room_for_new_text_candidates(self):
        models = {f'test/old{i}': {'modelId': f'test/old{i}', 'pipeline': 'text-generation',
            'revision': 'a' * 40, 'detailStatus': 'ready', 'detailCheckedAt': '2026-01-01T00:00:00+00:00'} for i in range(30)}
        nightly.atomic_json(self.h.state / 'candidates.json', {'schemaVersion': 2, 'models': models})
        calls = []
        def request(url):
            if '/api/models?' in url:
                return [{'id': f'test/new{i}', 'pipeline_tag': 'text-generation'} for i in range(20)]
            calls.append(url)
            return {'sha': 'b' * 40, 'pipeline_tag': 'text-generation'}
        self.h.request = request
        self.h.discover(detail_cap=10)
        self.assertEqual(sum('/test/old' in url for url in calls), 2)
        self.assertEqual(sum('/test/new' in url for url in calls), 8)

    def test_known_text_retry_is_not_starved_by_untyped_legacy_entries(self):
        models = {f'test/legacy{i}': {'modelId': f'test/legacy{i}', 'detailStatus': 'pending',
            'detailAttempts': 0} for i in range(238)}
        models['test/retry'] = {'modelId': 'test/retry', 'pipeline': 'text-generation',
            'detailStatus': 'failed', 'detailAttempts': 1, 'trendingScore': 100}
        nightly.atomic_json(self.h.state / 'candidates.json', {'schemaVersion': 2, 'models': models})
        calls = []
        def request(url):
            if '/api/models?' in url:
                return [{'id': f'test/new{i}', 'pipeline_tag': 'text-generation'} for i in range(20)]
            calls.append(url)
            return {'sha': 'b' * 40, 'pipeline_tag': 'text-generation'}
        self.h.request = request
        self.h.discover()
        self.assertTrue(any('/test/retry?' in url for url in calls))

    def test_thinking_probe_kills_stalled_http_child_at_its_own_deadline(self):
        requested = threading.Event()
        class Stalled(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                requested.set()
                time.sleep(2)
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Stalled)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.h.endpoint = f'http://127.0.0.1:{server.server_port}'
            self.h.policy['thinkingProbeSeconds'] = 0.6
            started = time.monotonic()
            result = self.h.thinking_probe('example:latest', True, {'medianClientWallMs': 100})
            self.assertTrue(requested.is_set())
            self.assertEqual(result['status'], 'error')
            self.assertLess(time.monotonic() - started, 1.5)
            self.assertGreater(self.h.remaining(), 100)
        finally:
            server.shutdown()
            server.server_close()

    def test_cleanup_failure_preserves_completed_benchmark(self):
        model = nightly.OWNED_PREFIX + self.sha[:16] + ':latest'
        digest = 'b' * 64
        nightly.atomic_json(self.h.state / 'imports.json', {model: {'sha256': self.sha, 'digest': digest}})
        self.h.installed = lambda: ({self.policy['baselineModel']: {'digest': 'c' * 64, 'size': 100}}
            if self.h.endpoint == nightly.OLLAMA else {model: {'digest': digest, 'size': 100}})
        @contextmanager
        def runtime(selection):
            self.h.endpoint = 'http://127.0.0.1:11435'
            self.h.secondary_process = object()
            try:
                yield
            finally:
                self.h.endpoint = nightly.OLLAMA
                self.h.secondary_process = None
        self.h.candidate_runtime = runtime
        self.h.wait_idle = lambda *args: {}
        self.h.api = lambda *args: {'version': 'test'}
        self.h.benchmark = lambda name: {'model': name, 'status': 'completed', 'summary': {'anyTruncated': False}}
        self.h.cleanup = lambda: (_ for _ in ()).throw(RuntimeError('cleanup failure fixture'))
        result = self.h.run_candidate(self.selection, acceptance_validation=True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['cleanupError'], 'cleanup failure fixture')
        entry = next(iter(nightly.read_json(self.h.ledger_path)['days'].values()))[0]
        self.assertEqual(entry['status'], 'completed')

    def test_failed_verified_import_is_evicted(self):
        name, digest = 'nightly-bench-failed:latest', 'a' * 64
        run_id = '20260910-120000-abcdef01'
        self.h.endpoint, self.h.secondary_process = 'http://127.0.0.1:11435', object()
        installed = {name: {'digest': digest}}
        self.h.installed = lambda: dict(installed)
        self.h.api = lambda *args: {'models': []}
        nightly.atomic_json(self.h.state / 'imports.json', {name: {'digest': digest, 'runId': run_id}})
        nightly.atomic_json(self.root / 'runs' / (run_id + '.json'), {'status': 'error',
            'admission': {'model': name, 'digest': digest}, 'error': 'unsupported architecture'})
        def delete(*args, **kwargs):
            installed.pop(name)
            return io.BytesIO(b'')
        with patch('nightly.urllib.request.urlopen', side_effect=delete):
            self.h.cleanup()
        self.assertFalse(installed)

    def test_environment_and_timeout_aborts_do_not_evict_models(self):
        name, digest = 'nightly-bench-interrupted:latest', 'a' * 64
        run_id = '20260910-120000-abcdef01'
        self.h.endpoint, self.h.secondary_process = 'http://127.0.0.1:11435', object()
        self.h.installed = lambda: {name: {'digest': digest}}
        self.h.api = lambda *args: {'models': []}
        nightly.atomic_json(self.h.state / 'imports.json', {name: {'digest': digest, 'runId': run_id}})
        for kind in ('environment', 'timeout', 'baseline', 'admission'):
            nightly.atomic_json(self.root / 'runs' / (run_id + '.json'), {'status': 'error',
                'admission': {'model': name, 'digest': digest}, 'failureKind': kind, 'error': 'interrupted fixture'})
            with patch('nightly.urllib.request.urlopen', side_effect=AssertionError('must not delete')):
                self.h.cleanup()
        self.assertIn(name, nightly.read_json(self.h.state / 'imports.json'))

    def test_expired_work_budget_still_allows_bounded_unload(self):
        self.h.deadline = time.monotonic() - 1
        self.h.hard_deadline = time.monotonic() + 5
        with self.h.cleanup_window():
            self.assertGreater(self.h.remaining(), 0)
            self.assertLessEqual(self.h.remaining(), 5)
        with self.assertRaises(TimeoutError):
            self.h.remaining()

    def test_launch_reports_active_operation_without_spawning(self):
        output = io.StringIO()
        with nightly.state_lock(self.h.state / 'operation.lock'), patch('nightly.Harness', return_value=self.h), \
             patch('background.subprocess.Popen', side_effect=AssertionError('must not launch')), \
             nightly.contextlib.redirect_stdout(output):
            background.launch(self.root / 'not-needed.json')
        self.assertEqual(json.loads(output.getvalue())['status'], 'deferred')

    def test_missing_drive_refuses_instead_of_looping_at_root(self):
        self.h.storage_check = nightly.Harness.storage_check.__get__(self.h)
        with patch('nightly.tree_bytes', return_value=0), patch.object(Path, 'exists', return_value=False):
            with self.assertRaisesRegex(owned_runtime.RuntimeBusy, 'drive is unavailable'):
                self.h.storage_check(100, {})

    def test_original_load_error_survives_unload_failure(self):
        self.h.installed = lambda: {'fixture:latest': {'digest': 'a' * 64, 'size': 100}}
        self.h.wait_idle = lambda *args: {'freeGiB': 90}
        def api(path, *args, **kwargs):
            if path == 'generate':
                raise RuntimeError('unload failure fixture')
            return {}
        self.h.api = api
        self.h.chat = lambda *args: (_ for _ in ()).throw(RuntimeError('original load failure'))
        with self.assertRaisesRegex(RuntimeError, 'original load failure'):
            self.h.benchmark('fixture:latest')
        self.assertIn('unload failure', self.h.report['benchmarks'][0]['unloadWarning'])

    def test_unload_does_not_wait_for_another_primary_model(self):
        self.h.api = lambda *args: {'models': [{'name': 'someone-elses-model'}]}
        self.h.gpu = lambda: {'freeGiB': 10}
        self.h.confirm_unloaded('our-model', 90)
        self.assertEqual(self.h.report['unloads'][0]['otherWorkloadLoaded'], ['someone-elses-model'])
        self.assertIsNone(self.h.report['unloads'][0]['vramRecovered'])

    @unittest.skipUnless(nightly.os.name == 'nt', 'Windows ownership APIs')
    def test_orphan_reclaim_requires_exact_process_birth_identity(self):
        process = subprocess.Popen([nightly.sys.executable, '-c',
            'import socket,time; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); print(s.getsockname()[1],flush=True); time.sleep(30)'],
            stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            port = int(process.stdout.readline())
            identity = owned_runtime.process_identity(process.pid)
            self.assertIsNotNone(identity)
            record = {'pid': process.pid, 'host': f'127.0.0.1:{port}', 'processIdentity':
                identity | {'creationFileTime': str(int(identity['creationFileTime']) + 1)}}
            nightly.atomic_json(self.h.state / 'secondary-process.json', record)
            self.assertFalse(owned_runtime.reclaim_orphan(self.h, port, nightly.sys.executable))
            self.assertIsNone(process.poll())
            record['processIdentity'] = identity
            nightly.atomic_json(self.h.state / 'secondary-process.json', record)
            self.assertTrue(owned_runtime.reclaim_orphan(self.h, port, nightly.sys.executable))
            process.wait(timeout=5)
        finally:
            owned_runtime.stop_tree(process)
            process.stdout.close()

    def test_detached_run_survives_launcher_exit_and_can_be_polled(self):
        source = Path(__file__).parent
        for filename in ('nightly.py', 'owned_runtime.py', 'background.py'):
            data = (source / filename).read_text()
            if filename == 'nightly.py':
                data = data.replace('        self.report.update(mode=\'nightly\', selection=selection)',
                                    '        time.sleep(1)\n        self.report.update(mode=\'nightly\', selection=selection)')
            (self.root / filename).write_text(data)
        hour = nightly.dt.datetime.now().hour
        self.policy.update(benchmarkWindowStartHour=(hour + 1) % 24, benchmarkWindowEndHour=(hour + 2) % 24)
        (self.root / 'policy.json').write_text(json.dumps(self.policy))
        selection = self.root / 'selection.json'
        selection.write_text(json.dumps(self.selection))
        started = time.monotonic()
        launch = subprocess.run([nightly.sys.executable, str(self.root / 'nightly.py'), '--launch-candidate', str(selection)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(launch.returncode, 0, launch.stderr)
        self.assertLess(time.monotonic() - started, 1)
        job = json.loads(launch.stdout)
        result = subprocess.run([nightly.sys.executable, str(self.root / 'nightly.py'), '--wait-run', job['runId']],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(json.loads(result.stdout)['status'], 'deferred', result.stderr)
        until = time.monotonic() + 5
        while owned_runtime.process_identity(job['pid']) == job['processIdentity'] and time.monotonic() < until:
            time.sleep(0.05)


if __name__ == '__main__':
    unittest.main(verbosity=2)
