import copy
from contextlib import nullcontext
import unittest
from unittest.mock import Mock,patch
import reasoning_screen as r
import quality_screen as qs


class ReasoningTests(unittest.TestCase):
    def make_harness(self):
        h=Mock()
        h.window_open.side_effect=lambda: r.benchmark_window_open(h.policy)
        h.report={};h.policy={'thinkingProbeTokens':8192,'numCtx':8192};h.endpoint='http://127.0.0.1:11434'
        h.validate_candidate.return_value={'model':'gpt-oss:20b','digest':'digest','bytes':1}
        h.installed.return_value={'gpt-oss:20b':{'digest':'digest'}}
        h.wait_idle.return_value={'freeGiB':90}
        h.api.side_effect=lambda method,*a,**k: {'details':{'family':'gptoss'},'capabilities':['thinking','completion']} if method=='show' else ({'models':[{'name':'gpt-oss:20b','digest':'digest'}]} if method=='ps' else {})
        h.cleanup_window.side_effect=nullcontext
        h.chat.return_value={'done':True,'message':{'content':'ready'}}
        return h

    def test_reasoning_mode_preserves_admission_and_cleanup(self):
        h=self.make_harness()
        with patch.object(r,'benchmark_window_open',return_value=True), patch.object(r.quality_screen,'run',return_value={'status':'completed','passed':16,'total':16}) as screen:
            report=r.run(h,{'kind':'installed'})
        self.assertEqual(report['status'],'completed')
        self.assertNotIn('comparison',report)
        h.validate_candidate.assert_called_once();h.reserve.assert_called_once();h.finish_reservation.assert_called_once()
        self.assertTrue(report['benchmarks'][0]['unloadConfirmed'])
        self.assertTrue(report['primaryIntegrity']['modelDigestsUnchanged'])
        self.assertEqual(screen.call_args.kwargs,{'think':'low','output_cap':8192,'allow_thinking':True})

    def test_remote_and_wrong_family_refused_before_reservation(self):
        h=self.make_harness()
        with patch.object(r,'benchmark_window_open',return_value=True):
            self.assertEqual(r.run(h,{'kind':'huggingface'})['status'],'error')
        h.reserve.assert_not_called();h.chat.assert_not_called()
        h=self.make_harness();h.api.side_effect=lambda *a,**k:{'details':{'family':'wrong'},'capabilities':['thinking']}
        with patch.object(r,'benchmark_window_open',return_value=True):
            self.assertEqual(r.run(h,{'kind':'installed'})['status'],'error')
        h.reserve.assert_not_called()

    def test_inference_failure_still_unloads_and_finishes_ledger(self):
        h=self.make_harness();h.chat.side_effect=TimeoutError('warmup stalled')
        with patch.object(r,'benchmark_window_open',return_value=True):
            result=r.run(h,{'kind':'installed'})
        self.assertEqual(result['status'],'error');h.confirm_unloaded.assert_called_once();h.finish_reservation.assert_called_once()

    def test_off_hours_never_load_or_reserve(self):
        h=self.make_harness()
        with patch.object(r,'benchmark_window_open',return_value=False):
            self.assertEqual(r.run(h,{'kind':'installed'})['status'],'deferred')
        h.validate_candidate.assert_not_called();h.reserve.assert_not_called();h.chat.assert_not_called()

    def test_expected_thinking_is_not_reported_as_thinking_off(self):
        h=Mock();h.report={'benchmarks':[{}]};h.deadline=10**20;h.remaining.return_value=1000
        answers=iter(qs.CASES)
        h.chat.side_effect=lambda *a,**k:{'done_reason':'stop','message':{'content':__import__('json').dumps({'answer':next(answers)[3]}),'thinking':'deliberate reasoning'}}
        result=qs.run(h,'mock',True,{},think='low',output_cap=8192,allow_thinking=True)
        self.assertIsNone(result['validThinkingOffScreen']);self.assertTrue(result['validReasoningScreen'])
        self.assertFalse(result['unexpectedThinking']);self.assertEqual(result['passed'],16)


if __name__=='__main__':
    unittest.main()
