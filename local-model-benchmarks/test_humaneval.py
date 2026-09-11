import json
import subprocess
import shutil
import unittest
import humaneval_screen as hx

class HumanEvalTests(unittest.TestCase):
    def sandbox(self,code,test):
        r=subprocess.run([shutil.which('node'),str(hx.ROOT/'humaneval_sandbox_runner.cjs')],input=json.dumps({'tasks':[{'id':'probe','code':code,'test':test}]}),capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout)['rows'][0]
    def test_dataset_and_repairs(self):
        ts=hx.tasks();self.assertEqual(len(ts),163)
        self.assertNotIn('JavaScript/162',[t['id'] for t in ts])
        self.assertTrue(all('canonical_solution' not in t for t in ts))
        for t in ts:
            if t['id'] in hx.MISSING_CALLS:self.assertTrue(t['tests'][0]['test'].rstrip().endswith('();'))
    def test_all_references(self):
        rows={r['task_id']:r for r in map(json.loads,(hx.ROOT/'fixtures/humaneval-x/javascript.jsonl').read_text().splitlines())}
        for t in hx.tasks():
            with self.subTest(t=t['id']):self.assertEqual(hx.evaluate(rows[t['id']]['canonical_solution'],t['tests'])['passed'],1)
    def test_false_assertion_fails(self):
        self.assertFalse(self.sandbox('','console.assert(false);')['passed'])
    def test_assertion_cannot_be_replaced(self):
        self.assertFalse(self.sandbox('console.assert=()=>{};','console.assert(false);')['passed'])
    def test_host_apis_absent(self):
        self.assertTrue(self.sandbox('','console.assert(typeof process === "undefined" && typeof require === "undefined" && typeof fetch === "undefined");')['passed'])
    def test_infinite_loop_interrupts(self):
        self.assertIn('error',self.sandbox('while(true){}','console.assert(true);'))
    def test_zero_assertions_not_success(self):
        self.assertFalse(self.sandbox('','')['passed'])

if __name__=='__main__':unittest.main()
