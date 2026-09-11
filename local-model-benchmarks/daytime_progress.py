from pathlib import Path
import collections
import datetime as dt
import json
import statistics
import subprocess
import sys
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from nightly import atomic_json,read_json
folder=root/'campaigns/20260911-daytime'
import argparse
parser=argparse.ArgumentParser(description='Build September 11 campaign progress from saved records.')
parser.add_argument('--output-dir',type=Path,default=folder)
args=parser.parse_args()
out=args.output_dir
out.mkdir(parents=True,exist_ok=True)
queue=read_json(root/'state/campaign-20260911-daytime-queue.json')
groups={};terminal=[];active=[];coding=[];human_groups={};standard=[]
for item in queue['items']:
    if not item.get('runId'):continue
    report=read_json(root/'runs'/(item['runId']+'.json'),{})
    if report.get('status') in ('queued','running'):active.append({'id':item['id'],'runId':item['runId']});continue
    terminal.append({'id':item['id'],'runId':item['runId'],'status':report.get('status'),'error':report.get('error') or report.get('reason')})
    if report.get('status')=='completed' and report.get('comparison'):
        benches=report.get('benchmarks',[]);b=benches[0];base=benches[1] if len(benches)>1 else {};sel=report.get('selection',{});comparison=report['comparison']
        standard.append({'model':sel.get('repoId',b['model']),'artifact':sel.get('filename'),'runId':item['runId'],'valid':comparison.get('valid',False),
            'reason':comparison.get('invalidReason'),'candidateTokensPerSecond':b.get('summary',{}).get('medianGenTokPerSec') if comparison.get('valid') else None,
            'baselineTokensPerSecond':base.get('summary',{}).get('medianGenTokPerSec') if comparison.get('valid') else None,
            'quality':{k:b.get('qualityScreen',{}).get(k) for k in ['version','status','passed','total']},
            'baselineQuality':{k:base.get('qualityScreen',{}).get(k) for k in ['version','status','passed','total']}})
    if report.get('mode')=='campaign-humanevalx-screen' and report.get('status')=='completed':
        b=report['benchmarks'][0];sel=report['selection'];pr=report['protocol'];label=sel.get('repoId',b['model'])
        key=(label,b['digest'],str(pr['thinking']),pr['context'],pr['outputCap'],pr['suiteSha256'])
        g=human_groups.setdefault(key,{'model':label,'digest':b['digest'],'thinking':pr['thinking'],'context':pr['context'],'outputCap':pr['outputCap'],'suiteSha256':pr['suiteSha256'],'protocol':pr['name'],'promptStyle':pr.get('promptStyle','continuation'),'runs':[],'tasks':[]})
        g['runs'].append(item['runId']);g['tasks'].extend(b['tasks'])
    if report.get('mode')=='campaign-coding-screen' and report.get('status')=='completed':
        b=report['benchmarks'][0];sel=report['selection'];pr=report['protocol']
        coding.append({'model':sel.get('repoId',b['model']),'artifact':sel.get('filename'),'digest':b['digest'],'runId':item['runId'],
            'protocol':pr,**b['summary'],'tasks':[{'id':x['id'],'passed':x['taskPassed'],'testsPassed':x['evaluation']['passed'],'testsTotal':x['evaluation']['total']} for x in b['tasks']]})
    if report.get('mode')!='campaign-workload-screen' or report.get('status')!='completed':continue
    bench=report['benchmarks'][0];protocol=report['protocol'];selection=report.get('selection',{})
    label=(selection['repoId']+' / '+selection.get('filename','')) if selection.get('repoId') else bench['model']
    key=(label,bench['digest'],str(protocol['thinking']),protocol['context'],protocol['name'],protocol['suiteSha256'])
    group=groups.setdefault(key,{'model':label,'digest':bench['digest'],'thinking':protocol['thinking'],'context':protocol['context'],'protocol':protocol['name'],'suiteSha256':protocol['suiteSha256'],'runs':[],'cases':[]})
    group['runs'].append(item['runId']);group['cases'].extend(bench['cases'])
import workload_suite
common_ids={r['id'] for r in workload_suite.cases()[:24]}
common_results=[]
results=[]
for g in groups.values():
    recorded=g.pop('cases');cases=list({c['id']:c for c in recorded}.values());times=[r['wallMs'] for r in cases if r.get('wallMs') is not None]
    matched=[r for r in cases if r['id'] in common_ids]
    if {r['id'] for r in matched}==common_ids:
        common_results.append({'model':g['model'],'digest':g['digest'],'thinking':g['thinking'],'context':g['context'],'suiteSha256':g['suiteSha256'],
            'passed':sum(r['passed'] for r in matched),'total':24,'medianWallMs':statistics.median(r['wallMs'] for r in matched),
            'truncated':sum(r['truncated'] for r in matched),'unexpectedThinking':any(r['unexpectedThinking'] for r in matched)})
    categories={}
    for c in cases:
        row=categories.setdefault(c['category'],{'passed':0,'total':0});row['passed']+=int(c['passed']);row['total']+=1
    results.append({**g,'repeatedCases':len(recorded)-len(cases),'passed':sum(c['passed'] for c in cases),'total':len(cases),'medianWallMs':statistics.median(times) if times else None,
        'totalWallMs':sum(times),'truncated':sum(c['truncated'] for c in cases),'unexpectedThinking':any(c['unexpectedThinking'] for c in cases),'categories':categories})
human_results=[]
for g in human_groups.values():
    recorded=g.pop('tasks');tasks=list({t['id']:t for t in recorded}.values());walls=[t['wallMs'] for t in tasks if t.get('wallMs') is not None]
    human_results.append({**g,'passed':sum(t['taskPassed'] for t in tasks),'total':len(tasks),'supportedTasks':163,'repeatedTasks':len(recorded)-len(tasks),
        'medianWallMs':statistics.median(walls) if walls else None,'truncated':sum(t['truncated'] for t in tasks),
        'unexpectedThinking':any(t['unexpectedThinking'] for t in tasks),'failedTasks':[t['id'] for t in tasks if not t['taskPassed']]})
artifacts=[]
for job_path in (root/'state').glob('prefetch-*.job.json'):
    job=read_json(job_path,{})
    if job.get('campaignId')!=queue['campaignId']:continue
    report=read_json(root/'runs'/(job['runId']+'.json'),{});download=report.get('download',{});size=download.get('bytes',0)
    if not download.get('verified') and download.get('partialPath'):
        p=Path(download['partialPath'])
        if p.exists():
            with p.open('rb') as stream:size=stream.seek(0,2)
    artifacts.append({'model':report.get('selection',{}).get('repoId'),'status':report.get('status'),'verified':download.get('verified',False),
        'bytesDownloaded':size,'expectedBytes':report.get('admission',{}).get('bytes'),'runId':job['runId']})
data={'updatedAt':dt.datetime.now().astimezone().isoformat(),'campaignId':queue['campaignId'],'active':active,'terminal':terminal,
 'pending':sum(r['status']=='pending' for r in queue['items']),'standardResults':standard,'workloadResults':results,'common24Results':common_results,'codingResults':coding,'humanEvalResults':human_results,'artifactPrefetches':artifacts,
 'supervision':read_json(root/'state'/('campaign-'+queue['campaignId']+'-control.json'),{})}
try:
    sample=subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw,clocks_event_reasons.active','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip().splitlines()[0]
    data['gpuSample']=dict(zip(('utilizationPercent','memoryUsedMiB','temperatureC','powerWatts','clockEventReasons'),[x.strip() for x in sample.split(',')]))
    import csv
    telemetry=out/'gpu-telemetry.csv';empty=not telemetry.exists()
    with telemetry.open('a',encoding='utf-8',newline='') as f:
        writer=csv.writer(f)
        if empty:writer.writerow(['sampledAt','activeRun','utilizationPercent','memoryUsedMiB','temperatureC','powerWatts','clockEventReasons'])
        writer.writerow([data['updatedAt'],','.join(x['runId'] for x in active),*data['gpuSample'].values()])
except Exception as exc:data['gpuSampleError']=str(exc)
atomic_json(folder/'workload-results.json',data);atomic_json(out/'benchmark-progress.json',data)
lines=['# RTX PRO 6000 benchmark progress','', 'Updated: '+data['updatedAt'], '',
 'September 11 campaign status: '+queue.get('status','unknown')+'. Results below are measured locally; scores from different reasoning budgets are separate.', '',
 'Running: '+(', '.join(x['id'] for x in active) or 'between jobs')+'. Pending queue entries: '+str(data['pending'])+'.', '',
 '## Broader workload results','',
 'The deterministic 96-case suite covers ledger replay, event-state reconstruction, dependency scheduling, SQL, shortest paths, record extraction, Python tracing, and retrieval. Completed blocks are accumulated below. In this JSON-answer suite, model-generated code is never executed. These are authored workload checks, not a standardized coding benchmark.', '',
 '| Model | Thinking | Context | Correct / attempted | Median response seconds | Truncated | Protocol note |', '|---|---|---:|---:|---:|---:|---|']
for r in results:
    lines.append(f"| {r['model']} | {r['thinking']} | {r['context']} | {r['passed']}/{r['total']} | {(r['medianWallMs'] or 0)/1000:.2f} | {r['truncated']} | {'unexpected thinking' if r['unexpectedThinking'] else 'none'} |")
lines+=['','Thinking-off jobs allow 2,048 output tokens; reasoning jobs allow 8,192. All use an 8,192-token context. Raw answers, runtime versions, model digests, and exact prompts are preserved in the research repository. Partial totals should not be read as a final ranking. Rows marked unexpected thinking violate their requested mode and must not be used as valid thinking-off comparisons.','','## Initial candidate screens','',
 '- GPT-OSS 20B: 15/16 on the separate low-reasoning v2 screen. It followed an instruction embedded inside a data field on the failed extraction case.',
 '- LFM2.5 2.6B BF16: downloaded and hash-verified, imported, and tested. Its ordinary responses returned unexpected thinking and hit the token cap, so the ordinary throughput comparison is invalid. This is a protocol compatibility finding, not an overall model-quality verdict.',
 '- Nex-N2.5-mini Q6: a newly found Bartowski mirror was verified and added to the queue. Text-only evaluation will not test its advertised computer-use or vision capabilities.', '',
 '## Background model downloads','']
lines[-2:]=[]
lines+=['## Function-writing results','','Eight authored JavaScript tasks, 99 hidden checks, and input immutability. Generated functions execute only inside an isolated QuickJS WebAssembly guest, with no host functions or module loader. This is a small function-writing screen, not a standardized coding leaderboard or repository agent evaluation.','',
 '| Model | Thinking | Context / output cap | Functions fully correct | Hidden checks passed | Median generation seconds | Issues |','|---|---|---:|---:|---:|---:|---|']
for c in coding:
    issues=([str(c['truncated'])+' truncated'] if c['truncated'] else [])+(['unexpected thinking'] if c['unexpectedThinking'] else [])
    lines.append(f"| {c['model']} | {c['protocol']['thinking']} | {c['protocol']['context']} / {c['protocol']['outputCap']} | {c['tasksPassed']}/{c['tasksTotal']} | {c['testsPassed']}/{c['testsTotal']} | {(c['medianWallMs'] or 0)/1000:.2f} | {'; '.join(issues) or 'none'} |")
lines+=['','Initial runs use 16,384 context and 4,096 output tokens with thinking off or 8,192 with reasoning. Larger-budget rows use 32,768 context and 16,384 output tokens; they are separate configurations, not equal-budget comparisons. Hidden-test counts are correlated within each function; passing a function requires all its checks. Prompts, generated code, sandbox dependency lock, and every observed result are saved.','','## Background model downloads','']
lines[-2:]=[]
lines+=['## HumanEval-X JavaScript, adapted WASM evaluation','','One greedy sample per task from the [published dataset](https://huggingface.co/datasets/zai-org/humaneval-x). The supported set is 163 of 164 tasks: Node crypto task 162 is excluded. Missing test invocations in tasks 32, 119, and 151 are explicitly added, and test randomness uses seed 42. All 163 reference solutions passed this runner. This is an adapted evaluation, not the original 200-sample leaderboard protocol; this longstanding public dataset may appear in model training data.','',
 '| Model | Prompt style | Thinking | Correct / attempted | Median generation seconds | Truncated | Protocol note |','|---|---|---|---:|---:|---:|---|']
for r in human_results:
    lines.append(f"| {r['model']} | {r['promptStyle']} | {r['thinking']} | {r['passed']}/{r['total']} | {(r['medianWallMs'] or 0)/1000:.2f} | {r['truncated']} | {'unexpected thinking' if r['unexpectedThinking'] else 'none'} |")
lines+=['','These HumanEval-X runs use 16384 context and 4096 output tokens with thinking off or 8192 with reasoning. Partial totals cover completed blocks only. Source data, transformations, reference validation, prompts, raw continuations, and test outcomes are saved.','','## Background model downloads','']
for a in artifacts:
    lines.append(f"- {a['model']}: {a['status']}; {a['bytesDownloaded']/1e9:.2f} / {(a['expectedBytes'] or 0)/1e9:.2f} GB; complete-file hash verified: {a['verified']}.")
lines += ['',
 '## Resource and stop behavior','',
 'One GPU inference job runs at a time. Model downloads use the existing F: benchmark store. Each worker has a one-hour hard deadline. The original nightly policy and canceled September 10 campaign remain preserved. New launches require a current agent-supervision lease and remaining usage; already authorized workers retain their deadline and cleanup. A user stop request revokes the campaign and terminates its identity-verified processes.', '',
 'The workstation thermal state is not held constant. Downloads, report generation, reference-fixture tests, and brief browser QA with GPU rendering disabled overlapped some runs. Latency is descriptive for this machine and run; different model configurations and reasoning budgets are recorded separately. If a case was repeated under the same configuration, the latest completed result is counted once.','']
standard_lines=['## Standard candidate comparisons','','The short throughput battery uses 8192 context and a 512-token output cap. Valid rows show candidate / Qwen3-Coder median generation tokens per second. The separate v2 answer screen has 16 authored cases; it does not execute code.','',
 '| Candidate | Throughput status | Tokens/second, candidate / coder | v2 answers, candidate / coder | Issue |','|---|---|---:|---|---|']
def short_quality(q):
    return str(q['passed'])+'/'+str(q['total']) if q.get('status')=='completed' and q.get('version')=='overnight-screen-v2' else 'not scored'
for r in standard:
    speed=str(r['candidateTokensPerSecond'])+' / '+str(r['baselineTokensPerSecond']) if r['valid'] else 'not comparable'
    standard_lines.append(f"| {r['model']} | {'valid' if r['valid'] else 'invalid'} | {speed} | {short_quality(r['quality'])} / {short_quality(r['baselineQuality'])} | {r['reason'] or 'none'} |")
standard_lines+=[''];position=lines.index('## Initial candidate screens');lines[position:position]=standard_lines
common_lines=['## Matched 24-case workload comparison','','Every row below covers exactly the same first 24 authored cases. Thinking-off output caps are 2048 tokens; reasoning caps are 8192. The 8-case LFM diagnostic is excluded from this matched table. These are workload answers, not generated-code execution scores.','',
 '| Model | Thinking | Correct / 24 | Median response seconds | Truncated | Protocol note |','|---|---|---:|---:|---:|---|']
for r in common_results:
    common_lines.append(f"| {r['model']} | {r['thinking']} | {r['passed']}/24 | {r['medianWallMs']/1000:.2f} | {r['truncated']} | {'unexpected thinking' if r['unexpectedThinking'] else 'none'} |")
common_lines+=['']
position=lines.index('## Broader workload results');lines[position:position]=common_lines
text='\n'.join(lines)
(out/'benchmark-progress.md').write_text(text,encoding='utf-8');(folder/'progress.md').write_text(text,encoding='utf-8')
print(json.dumps({'active':active,'terminalCount':len(terminal),'pending':data['pending'],'workloadResults':[{k:r[k] for k in ('model','thinking','passed','total','medianWallMs')} for r in results]}))
