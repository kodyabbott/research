"""Digest-pinned installed-model workload protocol, separately scored from v2."""
import hashlib
import statistics
import time
import quality_screen
import workload_suite

def run(h,selection,*,prepared_plan=None,reserved_elsewhere=False,personal_before=None):
    reserved=loaded=False; measurement=None; before=None
    try:
        if not h.window_open(): raise ValueError('Outside authorized campaign window')
        if selection.get('kind')!='installed' and prepared_plan is None: raise ValueError('Workload screen requires a digest-pinned model or a prepared owned import')
        offset=selection.get('caseOffset',0); count=selection.get('caseCount',24)
        if type(offset) is not int or type(count) is not int or offset<0 or count<1 or count>24 or offset+count>96:
            raise ValueError('Invalid workload case slice')
        all_cases=workload_suite.cases(); cases=all_cases[offset:offset+count]
        plan=prepared_plan or h.validate_candidate(selection);info=h.api('show',{'model':plan['model']})
        capable='thinking' in info.get('capabilities',[])
        think=selection.get('thinking',False)
        if think not in (False,True,'low','medium','high','implicit'): raise ValueError('Unsupported thinking control')
        if info.get('details',{}).get('family')=='gptoss' and think not in ('low','medium','high'):
            raise ValueError('GPT-OSS requires explicit reasoning level')
        if think and think!='implicit' and not capable: raise ValueError('Model does not advertise explicit thinking; use the separately labeled implicit protocol if observed')
        request_capable=capable and think!='implicit'
        request_think=think if think!='implicit' else False
        before=personal_before if personal_before is not None else {name:row['digest'] for name,row in h.installed().items()}
        gpu=h.wait_idle(plan['bytes'])
        if not reserved_elsewhere: h.reserve(plan); reserved=True
        h.report.update(mode='campaign-workload-screen',selection=selection,admission=plan,gpuBefore=gpu,
            protocol={'name':workload_suite.VERSION,'suiteSha256':workload_suite.digest(all_cases),'caseOffset':offset,'caseCount':count,
            'thinking':think,'outputCap':8192 if think else 2048,'context':h.policy['numCtx'],'caseDeadlineSeconds':120,
            'scope':'96 authored algorithm, Python trace, SQL, ledger, record extraction and retrieval cases. JSON output only; generated code is never executed. No claim of a standardized coding benchmark.'})
        measurement={'model':plan['model'],'digest':plan['digest'],'endpoint':h.endpoint,'runtime':h.api('version'),'details':info.get('details'),
            'capabilities':info.get('capabilities',[]),'thinkingRequestSent':request_capable,
            'modelParameters':info.get('parameters'),'templateSha256':hashlib.sha256(info.get('template','').encode()).hexdigest(),
            'cases':[],'status':'running'}
        h.report['benchmarks']=[measurement];h.save_report();loaded=True
        measurement['warmup']=h.chat(plan['model'],'Reply with exactly: ready',request_capable,think=request_think,num_predict=512,supervise=True)
        measurement['loadedModel']=h.api('ps').get('models',[])
        for row in cases:
            if h.remaining()<150:
                measurement.update(status='incomplete',reason='Shared deadline leaves insufficient case and cleanup time');break
            deadline=h.deadline;h.deadline=min(deadline,time.monotonic()+120)
            try:
                response=h.chat(plan['model'],row['prompt'],request_capable,think=request_think,num_predict=h.report['protocol']['outputCap'],supervise=True)
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
                after=({row['name']:row['digest'] for row in h.request('http://127.0.0.1:11434/api/tags')['models']} if personal_before is not None else {name:row['digest'] for name,row in h.installed().items()})
                h.report['primaryIntegrity']={'before':before,'after':after,'modelDigestsUnchanged':before==after}
                if before!=after:h.report.update(status='error',error='Personal model inventory changed')
            except Exception as exc:h.report.update(status='error',error=str(exc))
        h.save_report()
        if reserved:h.finish_reservation()
    return h.report


def run_downloaded(h,selection):
    """Use the same private runtime/import transaction for a broader candidate screen."""
    reserved=False;plan=None
    h.report.update(mode='campaign-workload-screen',selection=selection)
    try:
        if selection.get('kind')!='huggingface':raise ValueError('Downloaded workload requires pinned Hugging Face selection')
        if not h.window_open():raise ValueError('Outside authorized campaign window')
        before={name:row['digest'] for name,row in h.installed().items()}
        h.wait_idle()
        with h.candidate_runtime(selection):
            h.cleanup()
            plan=h.validate_candidate(selection);h.report['admission']=plan
            h.wait_idle(plan['bytes']);h.reserve(plan);reserved=True
            if not plan['alreadyImported']:
                path=h.download(plan);plan['digest']=h.import_model(plan,path)
            run(h,selection,prepared_plan=plan,reserved_elsewhere=True,personal_before=before)
            if h.report.get('status')=='completed':
                h.complete_import(plan);h.cleanup()
    except Exception as exc:h.report.update(status='error',error=str(exc))
    finally:
        h.save_report()
        if reserved:h.finish_reservation()
    return h.report
