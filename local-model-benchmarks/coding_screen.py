"""Generate functions locally and evaluate only inside an isolated QuickJS WASM guest."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time
import coding_suite
from quality_screen import _same

ROOT=Path(__file__).resolve().parent

def extract_code(content):
    text=content.strip()
    fence=re.fullmatch(r'```(?:javascript|js)?\s*\n([\s\S]*?)\n```',text,re.I)
    return (fence.group(1),True) if fence else (text,False)

def evaluate(code,tests,timeout=30):
    if not code or len(code)>131072:raise ValueError('Empty or oversized code response')
    result=subprocess.run([shutil.which('node'),'--max-old-space-size=256',str(ROOT/'coding_sandbox_runner.cjs')],
        input=json.dumps({'code':code,'tests':[{'id':t['id'],'input':t['input']} for t in tests]}),
        capture_output=True,text=True,encoding='utf-8',timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('Sandbox runner failed: '+result.stderr[-1500:])
    data=json.loads(result.stdout)
    if len(data['rows'])!=len(tests):raise RuntimeError('Sandbox returned an incomplete test record')
    for row,test in zip(data['rows'],tests):
        if row.get('id')!=test['id']:raise RuntimeError('Sandbox test identity mismatch')
        expected_kind={type(None):'null',bool:'boolean',int:'number',float:'number',str:'string',list:'object',dict:'object'}[type(test['expected'])]
        row['passed']=not row.get('error') and not row.get('mutated') and row.get('outputKind')==expected_kind and _same(row.get('actual'),test['expected'])
        row['expected']=test['expected']
    data['passed']=sum(bool(x['passed']) for x in data['rows']);data['total']=len(tests)
    return data

def request_budget(selection,thinking):
    context=selection.get('codingContext',16384)
    cap=selection.get('codingOutputCap',8192 if thinking else 4096)
    if type(context) is not int or context not in (16384,32768):raise ValueError('Unsupported coding context')
    allowed=(8192,16384) if thinking else (4096,)
    if type(cap) is not int or cap not in allowed or cap>context-1024:raise ValueError('Unsupported coding output budget')
    return context,cap


def run(h,selection,*,prepared_plan=None,reserved_elsewhere=False,personal_before=None,benchmark=None):
    loaded=reserved=False;before=None;measurement=None;old_ctx=h.policy['numCtx']
    try:
        if not h.window_open():raise ValueError('Outside authorized campaign window')
        if selection.get('kind')!='installed' and prepared_plan is None:raise ValueError('Coding screen requires pinned local weights')
        plan=prepared_plan or h.validate_candidate(selection);info=h.api('show',{'model':plan['model']})
        capable='thinking' in info.get('capabilities',[]);think=selection.get('thinking',False)
        if think not in (False,True,'low','medium','high','implicit'):raise ValueError('Invalid thinking mode')
        if info.get('details',{}).get('family')=='gptoss' and think not in ('low','medium','high'):raise ValueError('GPT-OSS requires explicit reasoning level')
        if think and think!='implicit' and not capable:raise ValueError('Explicit thinking is not advertised by this model')
        request_capable=capable and think!='implicit';request_think=think if think!='implicit' else False
        profile=selection.get('samplingProfile')
        if profile not in (None,'nex-recommended-v1','t1-p95-k40-v1'):raise ValueError('Unsupported coding sampling profile')
        sampling_args={'sampling_profile':profile} if profile else {}
        context,cap=request_budget(selection,think)
        h.policy['numCtx']=context
        before=personal_before if personal_before is not None else {name:row['digest'] for name,row in h.installed().items()}
        gpu=h.wait_idle(plan['bytes'])
        if not reserved_elsewhere:h.reserve(plan);reserved=True
        config=benchmark or {};tasks=config.get('tasks') or coding_suite.tasks()
        evaluator=config.get('evaluate',evaluate)
        h.report.update(mode=config.get('mode','campaign-coding-screen'),selection=selection,admission=plan,gpuBefore=gpu,
            protocol={'name':config.get('name',coding_suite.VERSION),'suiteSha256':config.get('suiteSha256') or coding_suite.digest(tasks),'thinking':think,'context':context,'outputCap':cap,
            'maxGenerationSeconds':240,'tasks':len(tasks),'hiddenTests':sum(len(t['tests']) for t in tasks),'temperature':(0.7 if profile=='nex-recommended-v1' else 1.0) if profile else 0,'topP':0.95 if profile else 1,'topK':40,'repeatPenalty':1.0,'samplingProfile':profile or 'greedy-v1','seed':42,
            'codeExecution':'QuickJS WebAssembly only, no exposed host functions or module loader',
            'sandboxPackageLockSha256':hashlib.sha256((ROOT/'state/coding-sandbox/package-lock.json').read_bytes()).hexdigest(),
            'scope':config.get('scope','Eight authored JavaScript function-writing tasks and 99 deterministic hidden functional checks; not a standardized coding benchmark or a repository-editing agent eval.'),**config.get('extraProtocol',{})})
        measurement={'model':plan['model'],'digest':plan['digest'],'endpoint':h.endpoint,'runtime':h.api('version'),'details':info.get('details'),
            'capabilities':info.get('capabilities',[]),'modelParameters':info.get('parameters'),
            'templateSha256':hashlib.sha256(info.get('template','').encode()).hexdigest(),'tasks':[],'status':'running'}
        h.report['benchmarks']=[measurement];h.save_report();loaded=True
        measurement['warmup']=h.chat(plan['model'],'Reply with exactly: ready',request_capable,think=request_think,num_predict=512,supervise=True,**sampling_args)
        measurement['loadedModel']=h.api('ps').get('models',[])
        for live in measurement['loadedModel']:
            if (live.get('name') or live.get('model'))==plan['model']:
                if live.get('digest') and live['digest']!=plan['digest']:raise RuntimeError('Loaded model digest changed')
                if live.get('context_length') and live['context_length']!=context:raise RuntimeError('Runtime did not honor the requested coding context')
        for task in tasks:
            if h.remaining()<275:measurement.update(status='incomplete',reason='Insufficient shared deadline for another task');break
            previous=h.deadline;h.deadline=min(previous,time.monotonic()+240)
            try:response=h.chat(plan['model'],task['prompt'],request_capable,think=request_think,num_predict=cap,supervise=True,**sampling_args)
            finally:h.deadline=previous
            message=response.get('message',{});code,fence=extract_code(message.get('content',''))
            record={'id':task['id'],'prompt':task['prompt'],'response':response,'code':code,'markdownFenceRemoved':fence,
                'truncated':response.get('done_reason')=='length','unexpectedThinking':not think and bool(message.get('thinking','').strip()),
                'wallMs':response.get('supervisedWallMs'),'taskPassed':False}
            if not code or record['truncated']:
                record['evaluation']={'passed':0,'total':len(task['tests']),'reason':'Empty or truncated code response'}
            else:
                record['evaluation']=evaluator(code,task['tests'],min(30,h.remaining()))
                record['taskPassed']=record['evaluation']['passed']==record['evaluation']['total']
            measurement['tasks'].append(record);h.save_report()
        else:measurement['status']='completed'
        rows=measurement['tasks'];walls=[x['wallMs'] for x in rows if x.get('wallMs') is not None]
        measurement['summary']={'tasksPassed':sum(x['taskPassed'] for x in rows),'tasksAttempted':len(rows),'tasksTotal':len(tasks),
            'testsPassed':sum(x['evaluation']['passed'] for x in rows),'testsTotal':sum(x['evaluation']['total'] for x in rows),
            'medianWallMs':statistics.median(walls) if walls else None,'totalWallMs':sum(walls),
            'truncated':sum(x['truncated'] for x in rows),'unexpectedThinking':any(x['unexpectedThinking'] for x in rows),
            'protocolValid':measurement['status']=='completed' and not any(x['unexpectedThinking'] for x in rows)}
        h.report['status']='completed' if measurement['status']=='completed' else 'error'
    except Exception as exc:
        h.report.update(status='error',error=str(exc))
        if measurement is not None:measurement['status']='incomplete'
    finally:
        if loaded:
            try:
                with h.cleanup_window():
                    h.api('generate',{'model':plan['model'],'keep_alive':0},timeout=10);h.confirm_unloaded(plan['model'],gpu['freeGiB'])
                measurement['unloadConfirmed']=True
            except Exception as exc:h.report.update(status='error',cleanupError=str(exc))
        if before is not None:
            try:
                after=({r['name']:r['digest'] for r in h.request('http://127.0.0.1:11434/api/tags')['models']} if personal_before is not None else {name:row['digest'] for name,row in h.installed().items()})
                h.report['primaryIntegrity']={'before':before,'after':after,'modelDigestsUnchanged':before==after}
                if before!=after:h.report.update(status='error',error='Personal model inventory changed')
            except Exception as exc:h.report.update(status='error',error=str(exc))
        h.policy['numCtx']=old_ctx;h.save_report()
        if reserved:h.finish_reservation()
    return h.report
