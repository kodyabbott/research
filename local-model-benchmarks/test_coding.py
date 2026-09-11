import unittest
from unittest.mock import patch
from test_workloads import WorkloadTests
import coding_screen as c
import coding_suite

class CodingTests(unittest.TestCase):
    def test_undefined_does_not_pass_a_null_expected_value(self):
        tests=[{'id':'0','input':{},'expected':None}]
        self.assertEqual(c.evaluate('function solve(){}',tests)['passed'],0)
        self.assertEqual(c.evaluate('function solve(){return null}',tests)['passed'],1)

    def test_mutation_is_rejected_even_with_correct_return_value(self):
        tests=[{'id':'0','input':{'x':1},'expected':{'x':2}}]
        self.assertEqual(c.evaluate('function solve(input){input.x=2;return input}',tests)['passed'],0)

    def test_model_lifecycle_restores_context_and_unloads(self):
        h=WorkloadTests().harness();h.chat.return_value={'done':True,'done_reason':'stop','message':{'content':'function solve(input){return input}'},'supervisedWallMs':10}
        with patch.object(c,'evaluate',side_effect=lambda code,tests,*a:{'passed':len(tests),'total':len(tests)}):
            report=c.run(h,{'kind':'installed'})
        self.assertEqual(report['status'],'completed');self.assertEqual(report['benchmarks'][0]['summary']['tasksPassed'],8)
        self.assertEqual(h.policy['numCtx'],8192);h.reserve.assert_called_once();h.finish_reservation.assert_called_once();h.confirm_unloaded.assert_called_once()

    def test_oversized_budget_refused_before_inference(self):
        h=WorkloadTests().harness();report=c.run(h,{'kind':'installed','codingContext':1000000})
        self.assertEqual(report['status'],'error');h.chat.assert_not_called();h.reserve.assert_not_called()

    def test_larger_budget_is_bounded_restored_and_reported(self):
        h=WorkloadTests().harness();h.api.side_effect=lambda method,*a,**kw:({'capabilities':['thinking']} if method=='show' else {'models':[{'name':'model','digest':'digest','context_length':32768}]} if method=='ps' else {})
        seen=[]
        def chat(*a,**kw):
            seen.append((h.policy['numCtx'],kw['num_predict']))
            return {'done':True,'done_reason':'stop','message':{'content':'function solve(input){return input}'},'supervisedWallMs':10}
        h.chat.side_effect=chat
        with patch.object(c,'evaluate',side_effect=lambda code,tests,*a:{'passed':len(tests),'total':len(tests)}):
            report=c.run(h,{'kind':'installed','thinking':True,'codingContext':32768,'codingOutputCap':16384})
        self.assertEqual(report['status'],'completed');self.assertEqual(report['protocol']['outputCap'],16384)
        self.assertEqual(seen[1:],[(32768,16384)]*8);self.assertEqual(h.policy['numCtx'],8192);h.confirm_unloaded.assert_called_once()

    def test_sampling_profile_reaches_every_request_and_is_reported(self):
        h=WorkloadTests().harness();h.chat.return_value={'done':True,'done_reason':'stop','message':{'content':'function solve(input){return input}'},'supervisedWallMs':10}
        with patch.object(c,'evaluate',side_effect=lambda code,tests,*a:{'passed':len(tests),'total':len(tests)}):
            report=c.run(h,{'kind':'installed','samplingProfile':'nex-recommended-v1'})
        self.assertEqual(report['status'],'completed')
        self.assertEqual(report['protocol']['temperature'],0.7)
        self.assertEqual(report['protocol']['topP'],0.95)
        self.assertEqual(len(h.chat.call_args_list),9)
        self.assertTrue(all(call.kwargs['sampling_profile']=='nex-recommended-v1' for call in h.chat.call_args_list))

    def test_unsupported_sampling_profile_refused_before_inference(self):
        h=WorkloadTests().harness();report=c.run(h,{'kind':'installed','samplingProfile':'unbounded'})
        self.assertEqual(report['status'],'error');h.chat.assert_not_called();h.reserve.assert_not_called()

    def test_fence_removal_is_narrow(self):
        self.assertEqual(c.extract_code('```javascript\nfunction solve(){}\n```'),('function solve(){}',True))
        self.assertFalse(c.extract_code('Explanation\n```js\nfunction solve(){}\n```')[1])

if __name__=='__main__':unittest.main()
