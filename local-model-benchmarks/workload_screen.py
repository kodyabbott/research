"""Digest-pinned installed-model workload protocol, separately scored from v2."""
import hashlib
import statistics
import time
import quality_screen
import workload_suite

def run(h,selection):
    reserved=loaded=False; measurement=None; before=None
    try:
        if not h.window_open(): raise ValueError('Outside authorized campaign window')
        if selection.get('kind')!='installed': raise ValueError('Workload screen requires a digest-pinned installed model')
        offset=selection.get('caseOffset',0); count=selection.get('caseCount',24)
        if type(offset) is not int or type(count) is not int or offset<0 or count<1 or count>24 or offset+count>96:
            raise ValueError('Invalid workload case slice')
        all_cases=workload_suite.cases(); cases=all_cases[offset:offset+count]
        plan=h.validate_candidate(selection);info=h.api('show',{'model':plan['model']})
        capable='thinking' in info.get('capabilities',[])
        think=selection.get('thinking',False)
        if think not in (False,True,'low','medium','high'): raise ValueError('Unsupported thinking control')
        if info.get('details',{}).get('family')=='gptoss' and think not in ('low','medium','high'):
            raise ValueError('GPT-OSS requires explicit reasoning level')
        before={name:row['digest'] for name,row in h.installed().items()}
        gpu=h.wait_idle(plan['bytes']); h.reserve(plan); reserved=True
        h.report.update(mode='campaign-workload-screen',selection=selection,admission=plan,gpuBefore=gpu,
            protocol={'name':workload_suite.VERSION,'suiteSha256':workload_suite.digest(all_cases),'caseOffset':offset,'caseCount':count,
            'thinking':think,'outputCap':8192 if think else 2048,'context':h.policy['numCtx'],'caseDeadlineSeconds':120,
            'scope':'96 authored algorithm, Python trace, SQL, ledger, record extraction and retrieval cases. JSON output only; generated code is never executed. No claim of a standardized coding benchmark.'})
        measurement={'model':plan['model'],'digest':plan['digest'],'runtime':h.api('version'),'details':info.get('details'),
            'modelParameters':info.get('parameters'),'templateSha256':hashlib.sha256(info.get('template','').encode()).hexdigest(),
            'cases':[],'status':'running'}
        h.report['benchmarks']=[measurement];h.save_report();loaded=True
        measurement['warmup']=h.chat(plan['model'],'Reply with exactly: ready',capable,think=think,num_predict=512,supervise=True)
        measurement['loadedModel']=h.api('ps').get('models',[])
        for row in cases:
            if h.remaining()<150:
                measurement.update(status='incomplete',reason='Shared deadline leaves insufficient case and cleanup time');break
            deadline=h.deadline;h.deadline=min(deadline,time.monotonic()+120)
            try:
                response=h.chat(plan['model'],row['prompt'],capable,think=think,num_predict=h.report['protocol']['outputCap'],supervise=True)
                msg=response.get('message',{});unexpected=not think and bool(msg.get('thinking','').strip())
                measurement['cases'].append({**row,'response':response,
                    'passed':response.get('done_reason')!='length' and quality_screen.grade(msg.get('content'),row['expected']),
                    'unexpectedThinking':unexpected,'wallMs':response.get('supervisedWallMs'),
                    'truncated':response.get('done_reason')=='length'})
                h.save_report()
            finally: h.deadline=deadline
        else:measurement['status']='completed'
        measured=measurement['cases'];walls=[r['wallMs'] for r in measured if r.get('wallMs') is not None]
        measurement['summary']={'passed':sum(r['passed'] for r in measured),'attempted':len(measured),'total':len(cases),
            'medianWallMs':statistics.median(walls) if walls else None,'totalWallMs':sum(walls),
            'totalGeneratedTokens':sum(r['response'].get('eval_count',0) for r in measured),
            'truncated':sum(r['truncated'] for r in measured),'unexpectedThinking':any(r['unexpectedThinking'] for r in measured),
            'protocolValid':measurement['status']=='completed' and not any(r['unexpectedThinking'] for r in measured)}
        h.report['status']='completed' if measurement['status']=='completed' else 'error'
    except Exception as exc:
        h.report.update(status='error',error=str(exc))
        if measurement is not None: measurement['status']='incomplete'
    finally:
        if loaded:
            try:
                with h.cleanup_window():
                    h.api('generate',{'model':plan['model'],'keep_alive':0},timeout=10)
                    h.confirm_unloaded(plan['model'],gpu['freeGiB'])
                measurement['unloadConfirmed']=True
            except Exception as exc:h.report.update(status='error',cleanupError=str(exc))
        if before is not None:
            try:
                after={name:row['digest'] for name,row in h.installed().items()}
                h.report['primaryIntegrity']={'before':before,'after':after,'modelDigestsUnchanged':before==after}
                if before!=after:h.report.update(status='error',error='Personal model inventory changed')
            except Exception as exc:h.report.update(status='error',error=str(exc))
        h.save_report()
        if reserved:h.finish_reservation()
    return h.report
