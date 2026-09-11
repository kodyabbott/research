from contextlib import nullcontext
import collections
import io
import json
import unittest
from unittest.mock import Mock,patch
import workload_suite as suite
import workload_screen as screen

class WorkloadTests(unittest.TestCase):
    def test_deterministic_balanced_suite(self):
        a=suite.cases();b=suite.cases()
        self.assertEqual(suite.digest(a),suite.digest(b));self.assertEqual(len(a),96)
        self.assertEqual(len({x['id'] for x in a}),96)
        self.assertEqual(set(collections.Counter(x['category'] for x in a).values()),{12})
        self.assertLess(max(len(x['prompt']) for x in a),20000)

    def test_authored_python_trace_oracle(self):
        from contextlib import redirect_stdout
        import ast
        for row in suite.cases():
            if row['category']!='python-trace': continue
            code=row['prompt'].split('\n',1)[1].split('\nReturn exactly')[0]
            with redirect_stdout(io.StringIO()) as out:
                # Only the trusted fixture text authored in workload_suite is executed.
                exec(compile(code,'authored-fixture','exec'),{})
            self.assertEqual(ast.literal_eval(out.getvalue()),row['expected'])

    def harness(self):
        h=Mock();h.report={};h.policy={'numCtx':8192};h.endpoint='http://127.0.0.1:11434';h.deadline=10**20
        h.window_open.return_value=True;h.remaining.return_value=1000
        h.validate_candidate.return_value={'model':'model','digest':'digest','bytes':10}
        h.installed.return_value={'model':{'digest':'digest'}};h.wait_idle.return_value={'freeGiB':90}
        h.api.return_value={};h.cleanup_window.side_effect=nullcontext
        return h

    def test_success_scoring_and_cleanup(self):
        h=self.harness();expected=suite.cases()[0]['expected']
        h.chat.return_value={'done':True,'done_reason':'stop','message':{'content':json.dumps({'answer':expected})},'supervisedWallMs':12,'eval_count':4}
        report=screen.run(h,{'kind':'installed','caseCount':1})
        self.assertEqual(report['status'],'completed');self.assertEqual(report['benchmarks'][0]['summary']['passed'],1)
        h.reserve.assert_called_once();h.finish_reservation.assert_called_once();h.confirm_unloaded.assert_called_once()

    def test_error_unloads_model(self):
        h=self.harness();h.chat.side_effect=TimeoutError('case deadline')
        report=screen.run(h,{'kind':'installed','caseCount':1})
        self.assertEqual(report['status'],'error');h.confirm_unloaded.assert_called_once();h.finish_reservation.assert_called_once()

    def test_wrong_slice_refused_before_model_admission(self):
        h=self.harness();screen.run(h,{'kind':'installed','caseOffset':90,'caseCount':24})
        h.reserve.assert_not_called();h.chat.assert_not_called()

    def test_thinking_mismatch_is_not_valid_protocol(self):
        h=self.harness();h.chat.return_value={'done':True,'done_reason':'length','message':{'content':'{}','thinking':'unexpected'}}
        report=screen.run(h,{'kind':'installed','caseCount':1})
        result=report['benchmarks'][0]['summary'];self.assertFalse(result['protocolValid']);self.assertEqual(result['passed'],0)

    def test_implicit_thinking_omits_control_field(self):
        h=self.harness();h.chat.return_value={'done':True,'done_reason':'stop','message':{'content':'{}','thinking':'natural'}}
        report=screen.run(h,{'kind':'installed','caseCount':1,'thinking':'implicit'})
        self.assertFalse(h.chat.call_args.args[2]);self.assertFalse(h.chat.call_args.kwargs['think'])
        self.assertFalse(report['benchmarks'][0]['summary']['unexpectedThinking'])

    def test_cached_owned_workload_reserves_once_and_verifies_primary(self):
        h=self.harness();h.validate_candidate.return_value.update(kind='huggingface',alreadyImported=True)
        h.candidate_runtime.side_effect=lambda _:nullcontext()
        h.request.return_value={'models':[{'name':'model','digest':'digest'}]}
        h.chat.return_value={'done':True,'done_reason':'stop','message':{'content':json.dumps({'answer':suite.cases()[0]['expected']})},'supervisedWallMs':12}
        report=screen.run_downloaded(h,{'kind':'huggingface','caseCount':1})
        self.assertEqual(report['status'],'completed');self.assertTrue(report['primaryIntegrity']['modelDigestsUnchanged'])
        h.reserve.assert_called_once();h.finish_reservation.assert_called_once();h.download.assert_not_called();h.complete_import.assert_called_once()

    def test_explicit_thinking_requires_advertised_capability(self):
        h=self.harness();report=screen.run(h,{'kind':'installed','caseCount':1,'thinking':True})
        self.assertEqual(report['status'],'error');h.chat.assert_not_called();h.reserve.assert_not_called()

if __name__=='__main__':unittest.main()
