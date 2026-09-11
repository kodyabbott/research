import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import campaign_queue as q
from nightly import atomic_json, read_json


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); (self.root/'state').mkdir(); (self.root/'runs').mkdir()
        self.path=self.root/'state'/q.QUEUE
        self.data={'authorizationFile':'auth.json','items':[{'id':'a','status':'running','runId':'run-a'},
                    {'id':'b','status':'pending','selectionFile':'b.json'}]}
        atomic_json(self.path,self.data)

    def test_running_job_prevents_next_launch(self):
        launch=Mock()
        out=q.advance(self.root,launch,lambda _: print(json.dumps({'status':'running'})))
        self.assertEqual(out['status'],'waiting'); launch.assert_not_called()

    def test_terminal_failure_is_recorded_and_next_is_launched(self):
        atomic_json(self.root/'runs/run-a.json',{'status':'error','error':'unsupported architecture'})
        with patch.object(q.campaign,'validate_authorization',return_value={}):
            result=q.advance(self.root,lambda *a: print(json.dumps({'status':'started','runId':'run-b'})),
                             lambda _: print(json.dumps({'status':'error'})))
        data=read_json(self.path)
        self.assertEqual(data['items'][0]['reason'],'unsupported architecture')
        self.assertEqual(data['items'][1]['runId'],'run-b')
        self.assertEqual(result['status'],'started')

    def test_expired_authorization_prevents_next_launch(self):
        self.data['items'][0]['status']='completed'; atomic_json(self.path,self.data)
        launch=Mock()
        with patch.object(q.campaign,'validate_authorization',side_effect=ValueError('expired')):
            result=q.advance(self.root,launch)
        self.assertEqual(result['status'],'stopped'); launch.assert_not_called()
        self.assertEqual(read_json(self.path)['items'][1]['status'],'pending')

    def test_busy_launcher_does_not_lose_pending_entry(self):
        self.data['items'][0]['status']='completed'; atomic_json(self.path,self.data)
        with patch.object(q.campaign,'validate_authorization',return_value={}):
            result=q.advance(self.root,Mock(side_effect=RuntimeError('another supervisor is active')))
        self.assertEqual(result['status'],'busy')
        self.assertEqual(read_json(self.path)['items'][1]['status'],'pending')


if __name__=='__main__':
    unittest.main()
