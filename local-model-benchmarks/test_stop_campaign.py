import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
import stop_campaign as s
from nightly import atomic_json,read_json

class StopTests(unittest.TestCase):
    def test_stop_rescans_last_controller_launch_and_keeps_other_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'state/jobs').mkdir(parents=True);(root/'runs').mkdir()
            cid='test';run='20260911-100000-abcdef01';identity={'creationFileTime':'1','imagePath':'python'}
            atomic_json(root/'campaigns/test/authorization.json',{'campaignId':cid})
            atomic_json(root/'state/campaign-test-queue.json',{'items':[{'id':'a','status':'running','runId':run}]})
            atomic_json(root/'state/campaign-test-queue.json.controller.json',{'pid':1,'processIdentity':identity})
            atomic_json(root/'state/jobs/20260911-100000-abcdef02.json',{'pid':3,'processIdentity':identity,'campaignId':'other'})
            atomic_json(root/'runs'/(run+'.json'),{'status':'running'})
            alive={1:identity,3:identity};killed=[]
            def kill(cmd,**kwargs):
                pid=int(cmd[cmd.index('/PID')+1]);killed.append(pid)
                if pid==1:
                    alive[2]=identity
                    atomic_json(root/'state/jobs'/(run+'.json'),{'pid':2,'processIdentity':identity,'campaignId':cid,'runId':run})
                alive.pop(pid,None);return Mock(returncode=0)
            with patch.object(s,'ROOT',root),patch.object(s,'process_identity',side_effect=lambda pid:alive.get(pid)),patch.object(s.subprocess,'run',side_effect=kill),patch.object(s,'api',return_value={'models':[]}),patch.object(s,'port_open',return_value=False),patch('builtins.print'):
                s.stop(cid,'test shutdown')
            self.assertEqual(killed,[1,2]);self.assertIn(3,alive)
            self.assertTrue(read_json(root/'campaigns/test/authorization.json')['revoked'])
            self.assertEqual(read_json(root/'runs'/(run+'.json'))['status'],'cancelled')

if __name__=='__main__':unittest.main()
