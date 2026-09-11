"""Download one authorized, pinned artifact while installed-model inference runs."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

from campaign import CampaignHarness, validate_authorization
from nightly import atomic_json, now, read_json, state_lock
from owned_runtime import process_identity

ROOT=Path(__file__).resolve().parent

def worker(auth,selection,run_id):
    h=CampaignHarness(ROOT,auth);h.run_id=run_id;h.report['runId']=run_id
    h.report.update(mode='campaign-prefetch',selection=read_json(selection))
    try:
        # Only installed-model GPU jobs can coexist with this read/download operation.
        # No import, runtime startup, inference or model deletion occurs here.
        with state_lock(h.state/'prefetch.lock'):
            if not h.window_open():raise ValueError('Campaign inactive')
            plan=h.validate_candidate(read_json(selection))
            if plan['kind']!='huggingface':raise ValueError('Prefetch only supports pinned Hugging Face GGUF artifacts')
            h.report['admission']=plan;h.save_report()
            path=h.download(plan)
            h.report.update(status='completed',verifiedFile=str(path))
    except Exception as exc:h.report.update(status='error',error=str(exc))
    finally:h.save_report()
    return 0 if h.report['status']=='completed' else 1

def supervise(auth,selection,run_id):
    policy=read_json(ROOT/'policy.json')
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',run_id,'--authorization',str(auth),'--selection',str(selection)]
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
        creationflags=subprocess.CREATE_NO_WINDOW,env=dict(os.environ,PYTHONUTF8='1'))
    try:
        out,err=p.communicate(timeout=policy['maxRuntimeSeconds']);print(out);print(err,file=sys.stderr);return p.returncode
    except subprocess.TimeoutExpired:
        subprocess.run(['taskkill.exe','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        p.wait(timeout=15)
        path=ROOT/'runs'/(run_id+'.json');report=read_json(path,{})
        report.update(status='error',error='Prefetch hard deadline reached; partial retained',finishedAt=now());atomic_json(path,report)
        return 124

def launch(auth,selection):
    auth=Path(auth).resolve(strict=True);selection=Path(selection).resolve(strict=True)
    h=CampaignHarness(ROOT,auth)
    with state_lock(h.state/'prefetch-launch.lock'):
        for path in h.state.glob('prefetch-*.job.json'):
            job=read_json(path,{})
            if job.get('processIdentity') and process_identity(job['pid'])==job['processIdentity']:
                raise RuntimeError('Another prefetch is active')
        # No active Hugging Face worker may race with prefetch storage/import admission.
        for path in (h.state/'jobs').glob('*.json'):
            if path.name.endswith('.stdout.json'):continue
            job=read_json(path,{})
            if job.get('processIdentity') and process_identity(job['pid'])==job['processIdentity']:
                report=read_json(ROOT/'runs'/(job['runId']+'.json'),{})
                if report.get('selection',{}).get('kind')!='installed':raise RuntimeError('Active job is not an installed-model benchmark')
        h.report.update(mode='campaign-prefetch',status='queued',selection=read_json(selection));h.save_report()
        log=h.state/('prefetch-'+h.run_id+'.log')
        with log.open('wb') as output:
            p=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--supervisor',h.run_id,'--authorization',str(auth),'--selection',str(selection)],
                stdin=subprocess.DEVNULL,stdout=output,stderr=output,close_fds=True,
                creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP,env=dict(os.environ,PYTHONUTF8='1'))
        job={'runId':h.run_id,'pid':p.pid,'processIdentity':process_identity(p.pid),'campaignId':h.authorization['campaignId'],'log':str(log),'selectionFile':str(selection)}
        atomic_json(h.state/('prefetch-'+h.run_id+'.job.json'),job)
        print(json.dumps({'status':'started',**job}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--authorization',required=True,type=Path);parser.add_argument('--selection',required=True,type=Path)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--launch',action='store_true');mode.add_argument('--worker');mode.add_argument('--supervisor')
    args=parser.parse_args()
    if args.launch:launch(args.authorization,args.selection)
    elif args.worker:sys.exit(worker(args.authorization,args.selection,args.worker))
    else:sys.exit(supervise(args.authorization,args.selection,args.supervisor))
