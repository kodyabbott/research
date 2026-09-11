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

    def test_fence_removal_is_narrow(self):
        self.assertEqual(c.extract_code('```javascript\nfunction solve(){}\n```'),('function solve(){}',True))
        self.assertFalse(c.extract_code('Explanation\n```js\nfunction solve(){}\n```')[1])

if __name__=='__main__':unittest.main()
