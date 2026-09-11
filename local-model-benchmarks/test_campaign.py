"""Offline tests for expiring count exemption and the independently scored screen."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import time
import unittest
from unittest.mock import Mock, patch

import campaign
import nightly
import quality_screen as qs


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'policy.json').write_bytes(Path(__file__).with_name('policy.json').read_bytes())
        (self.root / 'state').mkdir()
        self.original = (self.root / 'policy.json').read_bytes()
        self.auth_path = self.root / 'state/auth.json'
        self.current = dt.datetime.now(dt.timezone.utc)
        self.auth = {'schemaVersion': 1, 'scope': 'overnight-candidate-count-exemption',
            'campaignId': 'test-campaign', 'userRequest': 'Test worthwhile models overnight, no count limit.',
            'notBefore': (self.current-dt.timedelta(minutes=5)).isoformat(),
            'latestStartAt': (self.current+dt.timedelta(hours=1)).isoformat(),
            'expiresAt': (self.current+dt.timedelta(hours=3)).isoformat(),
            'policySha256': hashlib.sha256(self.original).hexdigest()}
        self.write_auth()

    def write_auth(self):
        self.auth_path.write_text(json.dumps(self.auth))

    def test_expiry_future_naive_and_policy_changes_refused(self):
        for current in (self.current-dt.timedelta(hours=1), self.current+dt.timedelta(hours=2)):
            with self.assertRaises(ValueError):
                campaign.validate_authorization(self.root, self.auth_path, current)
        self.auth['notBefore'] = '2026-09-10T20:00:00'
        self.write_auth()
        with self.assertRaises(ValueError):
            campaign.validate_authorization(self.root, self.auth_path)
        self.auth['notBefore'] = (self.current-dt.timedelta(minutes=5)).isoformat()
        self.write_auth()
        (self.root/'policy.json').write_bytes(self.original+b'\n')
        with self.assertRaisesRegex(ValueError, 'Policy changed'):
            campaign.validate_authorization(self.root, self.auth_path)

    def test_full_deadline_margin_and_single_night_required(self):
        self.auth['expiresAt'] = (self.current+dt.timedelta(hours=1, minutes=30)).isoformat()
        self.write_auth()
        with self.assertRaisesRegex(ValueError, 'deadline'):
            campaign.validate_authorization(self.root, self.auth_path)
        self.auth['expiresAt'] = (self.current+dt.timedelta(days=2)).isoformat()
        self.write_auth()
        with self.assertRaisesRegex(ValueError, 'single overnight'):
            campaign.validate_authorization(self.root, self.auth_path)

    def test_only_campaign_reservation_bypasses_exhausted_count(self):
        h = campaign.CampaignHarness(self.root, self.auth_path)
        plan = {'kind': 'installed', 'model': 'example:latest', 'bytes': 1, 'selection': {'kind': 'installed'}}
        day = dt.date.today().isoformat()
        normal = nightly.Harness(self.root)
        nightly.atomic_json(normal.ledger_path, {'days': {day: [{'runId': 'prior', 'status': 'completed'}]}})
        normal_before = normal.ledger_path.read_bytes()
        nightly.atomic_json(h.ledger_path, {'days': {day: [{'runId': 'campaign-prior', 'status': 'completed'}]}})
        with nightly.state_lock(h.state / 'operation.lock'):
            h.reserve(plan)
        self.assertEqual(len(nightly.read_json(h.ledger_path)['days'][day]), 2)
        self.assertEqual(h.policy['maxCandidatesPerDay'], 1)
        self.assertEqual((self.root / 'policy.json').read_bytes(), self.original)
        self.assertEqual(normal.ledger_path.read_bytes(), normal_before)
        self.assertTrue(h.report['campaign']['reservation']['countExemptionUsed'])
        with self.assertRaisesRegex(RuntimeError, 'Daily candidate limit'):
            nightly.Harness(self.root).reserve(plan)

    def test_campaign_leaves_unused_regular_quota_available(self):
        h = campaign.CampaignHarness(self.root, self.auth_path)
        plan = {'kind': 'installed', 'model': 'example:latest', 'bytes': 1, 'selection': {'kind': 'installed'}}
        with nightly.state_lock(h.state / 'operation.lock'):
            h.reserve(plan)
            normal = nightly.Harness(self.root)
            self.assertFalse(normal.ledger_path.exists())
            normal.reserve(plan)
        day = dt.date.today().isoformat()
        self.assertEqual(len(nightly.read_json(normal.ledger_path)['days'][day]), 1)
        self.assertEqual(len(nightly.read_json(h.ledger_path)['days'][day]), 1)

    def test_hard_deadline_finishes_campaign_ledger_only(self):
        h = campaign.CampaignHarness(self.root, self.auth_path)
        run_id = h.run_id
        day = dt.date.today().isoformat()
        nightly.atomic_json(h.ledger_path, {'days': {day: [{'runId': run_id, 'status': 'reserved'}]}})
        normal = nightly.Harness(self.root)
        nightly.atomic_json(normal.ledger_path, {'days': {day: [{'runId': 'normal', 'status': 'completed'}]}})
        normal_before = normal.ledger_path.read_bytes()
        h.save_report()
        process = Mock(pid=123)
        process.communicate.side_effect = subprocess.TimeoutExpired('mock', 1)
        process.wait.return_value = 0
        with patch.object(nightly, '__file__', str(self.root/'nightly.py')), \
             patch.object(nightly.subprocess, 'Popen', return_value=process), \
             patch.object(nightly.subprocess, 'run', return_value=Mock(returncode=0)), \
             patch('builtins.print'):
            code = nightly.supervised([], timeout=1, run_id=run_id)
        self.assertEqual(code, 124)
        self.assertEqual(nightly.read_json(h.ledger_path)['days'][day][0]['status'], 'error')
        self.assertEqual(normal.ledger_path.read_bytes(), normal_before)

    def test_reservation_failure_restores_in_memory_limit(self):
        h = campaign.CampaignHarness(self.root, self.auth_path)
        with patch.object(nightly.Harness, 'reserve', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                h.reserve({})
        self.assertEqual(h.policy['maxCandidatesPerDay'], 1)
        self.assertEqual((self.root/'policy.json').read_bytes(), self.original)

    def test_authorization_rechecked_at_reservation(self):
        h = campaign.CampaignHarness(self.root, self.auth_path)
        self.auth['userRequest'] += ' changed'
        self.write_auth()
        with self.assertRaisesRegex(ValueError, 'changed during preflight'):
            h.reserve({})
        self.assertFalse(h.ledger_path.exists())

    def test_quality_grader_requires_exact_json_value_and_type(self):
        self.assertTrue(qs.grade('{ "answer": [1,2] }', [1, 2]))
        self.assertTrue(qs.grade('{"answer":null}', None))
        for content in ('{"answer":true}', '{"answer":1.0}', '{"answer":1,"extra":2}',
                        '{"answer":0,"answer":1}', '{"answer":NaN}', '```json\n{"answer":1}\n```',
                        'Explanation {"answer":1}', '{"answer":1} trailing'):
            self.assertFalse(qs.grade(content, 1), content)

    def test_quality_screen_scores_and_persists_without_changing_deadline(self):
        h = nightly.Harness(self.root)
        h.report['benchmarks'] = [{}]
        original_deadline = h.deadline
        answers = iter([expected for _, _, _, expected in qs.CASES])
        def chat(*args, **kwargs):
            return {'message': {'content': json.dumps({'answer': next(answers)})}, 'done_reason': 'stop'}
        h.chat = chat
        result = qs.run(h, 'mock', False, {})
        self.assertEqual((result['status'], result['passed'], result['attempted']), ('completed', 16, 16))
        self.assertTrue(result['validThinkingOffScreen'])
        self.assertEqual(h.deadline, original_deadline)
        self.assertEqual(len(nightly.read_json(h.root / h.report['resultFile'])['benchmarks'][0]['qualityScreen']['cases']), 16)

    def test_contaminated_screen_skips_and_interrupted_screen_is_incomplete(self):
        h = nightly.Harness(self.root)
        h.report['benchmarks'] = [{}]
        h.chat = lambda *a, **k: self.fail('Must not call contaminated model')
        self.assertEqual(qs.run(h, 'mock', True, {'unexpectedThinking': True})['status'], 'skipped')
        original_deadline = h.deadline
        with patch.object(h, 'chat', side_effect=TimeoutError('case deadline')):
            result = qs.run(h, 'mock', True, {})
        self.assertEqual(result['status'], 'incomplete')
        self.assertFalse(result['validThinkingOffScreen'])
        self.assertEqual(h.deadline, original_deadline)

    def test_truncation_and_unexpected_thinking_are_retained(self):
        h = nightly.Harness(self.root)
        h.report['benchmarks'] = [{}]
        responses = iter([{'message': {'content': json.dumps({'answer': e}), 'thinking': 'unexpected'},
                           'done_reason': 'length'} for _, _, _, e in qs.CASES])
        h.chat = lambda *a, **k: next(responses)
        result = qs.run(h, 'mock', False, {})
        self.assertEqual(result['passed'], 0)
        self.assertTrue(result['unexpectedThinking'])
        self.assertFalse(result['validThinkingOffScreen'])


if __name__ == '__main__':
    unittest.main()
