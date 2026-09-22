import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mac_replay

REPO = Path(os.environ.get('RESEARCH_REPO', Path(__file__).resolve().parents[1]))


class ReplayTests(unittest.TestCase):
    def test_parameter_group_order_is_not_a_configuration_change(self):
        one = 'temperature 0.7\nstop "first"\nstop "second"'
        two = 'stop    "first"\nstop "second"\ntemperature    0.7'
        self.assertEqual(mac_replay.parameters(one), mac_replay.parameters(two))
        self.assertNotEqual(mac_replay.parameters(one), mac_replay.parameters(two.replace('0.7', '0.8')))
        self.assertNotEqual(mac_replay.parameters(one), mac_replay.parameters(two.replace('second', 'third')))

    def make(self, folder):
        args = argparse.Namespace(repo=REPO, model='gpt-oss:20b', endpoint='http://127.0.0.1:11436', output=Path(folder) / 'run.json')
        with patch.object(mac_replay, 'host_snapshot', return_value={}):
            return mac_replay.Replay(args)

    def test_saved_cases_and_scores_are_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            replay = self.make(folder)
            for model, name in mac_replay.REFERENCES.items():
                report = json.loads((REPO / 'local-model-benchmarks/runs' / name).read_text())
                old = next(b for b in report['benchmarks'] if b['model'] == model)
                score = sum(replay.grade(r['response']['message']['content'], r['expected']) and not r['truncated'] for r in old['cases'])
                self.assertEqual(score, old['summary']['passed'])

    def test_digest_mismatch_refuses_before_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            replay = self.make(folder)
            seen = []
            def api(path, data=None, timeout=30):
                seen.append(path)
                return {'ps': {'models': []}, 'tags': {'models': [{'name': replay.args.model, 'digest': 'changed'}]},
                        'version': replay.old['runtime'], 'show': {'template': '', 'parameters': replay.old['modelParameters'], 'details': replay.old['details']}}[path]
            replay.api = api
            with patch.object(mac_replay, 'host_snapshot', return_value={}):
                with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                    replay.run()
            self.assertNotIn('chat', seen)
            self.assertFalse(json.loads(replay.path.read_text())['identityChecks']['modelDigest'])

    def test_inference_failure_still_unloads_and_saves_error(self):
        with tempfile.TemporaryDirectory() as folder:
            replay = self.make(folder)
            replay.old['templateSha256'] = hashlib.sha256(b'').hexdigest()
            seen = []
            def api(path, data=None, timeout=30):
                seen.append(path)
                return {'ps': {'models': []}, 'tags': {'models': [{'name': replay.args.model, 'digest': replay.old['digest']}]},
                        'version': replay.old['runtime'], 'show': {'template': '', 'parameters': replay.old['modelParameters'], 'details': replay.old['details']}, 'generate': {}}[path]
            replay.api = api
            with patch.object(replay, 'chat', side_effect=TimeoutError('case timeout')), patch.object(mac_replay, 'host_snapshot', return_value={}):
                with self.assertRaisesRegex(TimeoutError, 'case timeout'):
                    replay.run()
            report = json.loads(replay.path.read_text())
            self.assertEqual(report['status'], 'error')
            self.assertTrue(report['unload']['confirmed'])
            self.assertIn('generate', seen)


if __name__ == '__main__':
    unittest.main()
