"""Stop only a selected campaign's identity-verified processes; retain all evidence."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from nightly import read_json,atomic_json,state_lock,now
from owned_runtime import process_identity,port_open

ROOT=Path(__file__).resolve().parent

def api(method,body=None):
    data=None if body is None else json.dumps(body).encode()
    request=urllib.request.Request('http://127.0.0.1:11434/api/'+method,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)

def stop(cid,reason,dry_run=False):
    if not re.fullmatch(r'[a-z0-9-]{1,80}',cid):raise ValueError('Invalid campaign ID')
    folder=ROOT/'campaigns'/cid;auth_path=folder/'authorization.json';auth=read_json(auth_path)
    if auth.get('campaignId')!=cid:raise ValueError('Campaign identity mismatch')
    queue_path=ROOT/'state'/('campaign-'+cid+'-queue.json')
    queue=read_json(queue_path)
    controller_path=queue_path.with_name(queue_path.name+'.controller.json')
    controller=read_json(controller_path,{})
    records=[]
    if controller.get('pid'):records.append(('controller',controller,False))
    for path in (ROOT/'state/jobs').glob('*.json'):
        if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}\.json',path.name):continue
        job=read_json(path,{})
        if job.get('campaignId')==cid:records.append(('supervisor',job,True))
    for path in (ROOT/'state').glob('prefetch-*.job.json'):
        job=read_json(path,{})
        if job.get('campaignId')==cid:records.append(('prefetch',job,True))
    live=[(kind,r,tree) for kind,r,tree in records if r.get('processIdentity') and process_identity(r['pid'])==r['processIdentity']]
    if dry_run:
        print(json.dumps({'dryRun':True,'campaignId':cid,'liveProcesses':[{'kind':k,'pid':r['pid'],'runId':r.get('runId')} for k,r,t in live]}));return
    stopped=[];owned_primary={};run_ids=[]
    # Holding the queue lock makes any in-flight launch finish recording its PID
    # before controller termination. Rescan jobs afterwards to catch that last launch.
    with state_lock(queue_path.with_name(queue_path.name+'.lock')):
        auth.update(revoked=True,revokedAt=now(),revocationReason=reason);atomic_json(auth_path,auth)
        control_path=ROOT/'state'/('campaign-'+cid+'-control.json');control=read_json(control_path,{})
        control.update(status='stopped',stoppedAt=now(),reason=reason);atomic_json(control_path,control)
        if controller.get('processIdentity') and process_identity(controller['pid'])==controller['processIdentity']:
            result=subprocess.run(['taskkill.exe','/PID',str(controller['pid']),'/F'],capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            stopped.append({'kind':'controller','pid':controller['pid'],'exitCode':result.returncode})
    records=[]
    for path in (ROOT/'state/jobs').glob('*.json'):
        if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}\.json',path.name):continue
        job=read_json(path,{})
        if job.get('campaignId')==cid:records.append(('supervisor',job,True))
    for path in (ROOT/'state').glob('prefetch-*.job.json'):
        job=read_json(path,{})
        if job.get('campaignId')==cid:records.append(('prefetch',job,True))
    live=[(kind,r,tree) for kind,r,tree in records if r.get('processIdentity') and process_identity(r['pid'])==r['processIdentity']]
    for kind,record,tree in live:
        run_id=record.get('runId')
        if run_id:
            run_ids.append(run_id);report=read_json(ROOT/'runs'/(run_id+'.json'),{})
            for bench in report.get('benchmarks',[]):
                if bench.get('endpoint')=='http://127.0.0.1:11434' or (not bench.get('endpoint') and report.get('selection',{}).get('kind')=='installed'):
                    if bench.get('model') and bench.get('digest'):owned_primary[bench['model']]=bench['digest']
        if process_identity(record['pid'])!=record['processIdentity']:continue
        command=['taskkill.exe','/PID',str(record['pid']),'/F']+(['/T'] if tree else [])
        result=subprocess.run(command,capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        stopped.append({'kind':kind,'pid':record['pid'],'runId':run_id,'exitCode':result.returncode})
    with state_lock(queue_path.with_name(queue_path.name+'.lock')):
        queue=read_json(queue_path);queue.update(status='cancelled',cancelledAt=now(),cancelReason=reason)
        for item in queue['items']:
            if item['status']=='running' and item.get('runId'):
                completed=read_json(ROOT/'runs'/(item['runId']+'.json'),{})
                if completed.get('status') not in (None,'queued','running'):
                    item.update(status=completed['status'],finishedAt=completed.get('finishedAt'));continue
            if item['status'] in ('pending','running'):item.update(status='cancelled',cancelledAt=now(),reason=reason)
        atomic_json(queue_path,queue)
    for run_id in run_ids:
        path=ROOT/'runs'/(run_id+'.json');report=read_json(path,{})
        if report.get('status') in ('queued','running'):
            report.update(status='cancelled',finishedAt=now(),reason=reason);atomic_json(path,report)
    ledger_path=ROOT/'state'/('campaign-'+cid+'-ledger.json');ledger=read_json(ledger_path,{'days':{}})
    for rows in ledger['days'].values():
        for row in rows:
            if row.get('runId') in run_ids and row.get('status')=='reserved':row.update(status='cancelled',finishedAt=now(),reason=reason)
    atomic_json(ledger_path,ledger)
    unloaded=[]
    for loaded in api('ps').get('models',[]):
        name=loaded.get('name') or loaded.get('model')
        if name in owned_primary and loaded.get('digest')==owned_primary[name]:
            api('generate',{'model':name,'keep_alive':0});unloaded.append(name)
    until=time.monotonic()+15
    while time.monotonic()<until and (port_open(11435) or any((m.get('name') or m.get('model')) in owned_primary for m in api('ps').get('models',[]))):time.sleep(0.5)
    result={'campaignId':cid,'stoppedAt':now(),'reason':reason,'processes':stopped,'primaryModelsUnloaded':unloaded,
        'remainingOwnedProcesses':[{'kind':k,'pid':r['pid']} for k,r,t in live if process_identity(r['pid'])==r['processIdentity']],
        'privatePortFree':not port_open(11435),'primaryLoadedAfter':api('ps').get('models',[])}
    atomic_json(folder/'cancellation.json',result);print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--campaign',required=True);p.add_argument('--reason',required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    stop(a.campaign,a.reason,a.dry_run)
