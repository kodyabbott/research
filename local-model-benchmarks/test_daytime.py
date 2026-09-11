import datetime as dt
import unittest
from unittest.mock import patch
from test_campaign import CampaignTests
import campaign
import nightly
import reasoning_screen


class DaytimeTests(CampaignTests):
    def daytime(self):
        self.auth['scope']='human-directed-daytime-campaign'
        self.write_auth()
        return campaign.CampaignHarness(self.root,self.auth_path)

    def test_daytime_only_with_new_scope(self):
        old=campaign.CampaignHarness(self.root,self.auth_path)
        with patch.object(nightly,'benchmark_window_open',return_value=False):
            self.assertFalse(old.window_open())
            new=self.daytime()
            self.assertTrue(new.window_open())
            self.assertFalse(nightly.Harness(self.root).window_open())
        self.assertEqual((self.root/'policy.json').read_bytes(),self.original)

    def test_revocation_and_modified_authority_refuse_new_work(self):
        h=self.daytime()
        self.auth['revoked']=True; self.write_auth()
        with self.assertRaises(ValueError): h.window_open()
        with self.assertRaises(ValueError): h.reserve({})
        self.auth['revoked']=False;self.auth['userRequest']='Changed authority';self.write_auth()
        with self.assertRaises(ValueError): h.window_open()

    def test_launcher_ignores_empty_stdout_records(self):
        import json
        from unittest.mock import Mock
        self.daytime()
        jobs=self.root/'state/jobs';jobs.mkdir()
        (jobs/'20260910-231202-3881969d.stdout.json').write_text('')
        selection=self.root/'selection.json';selection.write_text(json.dumps({'kind':'installed','model':'test'}))
        with patch.object(campaign,'ROOT',self.root), patch.object(campaign.subprocess,'Popen',return_value=Mock(pid=123)), patch.object(campaign,'process_identity',return_value={'imagePath':'mock','creationFileTime':'1'}), patch('builtins.print'):
            campaign.launch(self.auth_path,selection)
        self.assertEqual(len([p for p in jobs.glob('*.json') if not p.name.endswith('.stdout.json')]),1)

    def test_expired_supervision_and_exhausted_usage_block_launch(self):
        self.auth['scope']='human-directed-daytime-campaign'
        self.auth['supervisionFile']='state/campaign-test-campaign-control.json'
        self.write_auth()
        control={'status':'active','leaseExpiresAt':(self.current+dt.timedelta(minutes=30)).isoformat(),'usageRemainingPercent':25}
        nightly.atomic_json(self.root/self.auth['supervisionFile'],control)
        campaign.validate_authorization(self.root,self.auth_path)
        control['usageRemainingPercent']=0
        nightly.atomic_json(self.root/self.auth['supervisionFile'],control)
        with self.assertRaisesRegex(ValueError,'usage exhausted'):campaign.validate_authorization(self.root,self.auth_path)
        control['usageRemainingPercent']=25;control['leaseExpiresAt']=(self.current-dt.timedelta(seconds=1)).isoformat()
        nightly.atomic_json(self.root/self.auth['supervisionFile'],control)
        with self.assertRaisesRegex(ValueError,'supervision lease'):campaign.validate_authorization(self.root,self.auth_path)

    def test_bounded_daytime_duration(self):
        self.auth['scope']='human-directed-daytime-campaign'
        self.auth['latestStartAt']=(self.current+dt.timedelta(hours=13)).isoformat()
        self.auth['expiresAt']=(self.current+dt.timedelta(hours=15)).isoformat()
        self.write_auth()
        campaign.validate_authorization(self.root,self.auth_path)
        self.auth['expiresAt']=(self.current+dt.timedelta(hours=25)).isoformat();self.write_auth()
        with self.assertRaises(ValueError): campaign.validate_authorization(self.root,self.auth_path)


if __name__=='__main__': unittest.main()
