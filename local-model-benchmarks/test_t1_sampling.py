import unittest
from unittest.mock import patch
import coding_screen as coding
import test_workloads as workload_tests
import test_nightly as nightly_tests

class TemperatureOneTests(unittest.TestCase):
    def test_all_coding_requests_and_metadata_use_selected_profile(self):
        h=workload_tests.WorkloadTests().harness()
        h.chat.return_value={'done':True,'done_reason':'stop','message':{'content':'function solve(input){return input}'},'supervisedWallMs':10}
        with patch.object(coding,'evaluate',side_effect=lambda code,tests,*a:{'passed':len(tests),'total':len(tests)}):
            report=coding.run(h,{'kind':'installed','samplingProfile':'t1-p95-k40-v1'})
        self.assertEqual(report['status'],'completed')
        self.assertEqual(report['protocol']['temperature'],1.0)
        self.assertEqual(report['protocol']['topP'],0.95)
        self.assertEqual(report['protocol']['topK'],40)
        self.assertEqual(len(h.chat.call_args_list),9)
        self.assertTrue(all(c.kwargs['sampling_profile']=='t1-p95-k40-v1' for c in h.chat.call_args_list))

    def test_request_options_and_default_are_separate(self):
        fixture=nightly_tests.HarnessTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        h=fixture.h
        calls=[]
        h.api=lambda path,body,**kwargs:(calls.append(body) or {'done':True})
        h.chat('example:latest','hello',True,sampling_profile='t1-p95-k40-v1')
        h.chat('example:latest','hello',True)
        self.assertEqual(calls[0]['options']['temperature'],1.0)
        self.assertEqual(calls[0]['options']['top_p'],0.95)
        self.assertEqual(calls[0]['options']['top_k'],40)
        self.assertEqual(calls[0]['options']['seed'],42)
        self.assertEqual(calls[1]['options']['temperature'],0)
        self.assertEqual(calls[1]['options']['top_p'],1)

if __name__=='__main__':unittest.main()
