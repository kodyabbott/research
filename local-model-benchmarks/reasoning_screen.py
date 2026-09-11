"""Separate installed GPT-OSS screen; no throughput comparison or model downloads."""
import hashlib

from nightly import benchmark_window_open
import quality_screen


def run(h, selection):
    h.report.update(mode='campaign-reasoning-screen', selection=selection,
        protocol={'name':'gpt-oss-low-v2','thinking':'low','outputCap':h.policy['thinkingProbeTokens'],
            'context':h.policy['numCtx'],'maxCaseSeconds':45,
            'caveat':'Exploratory reasoning-enabled quality screen. Different token/reasoning budget from thinking-off v2; no throughput or equal-budget quality ranking.'})
    reserved, loaded, measurement, before = False, False, None, None
    try:
        if not benchmark_window_open(h.policy):
            h.report.update(status='deferred', reason='Outside the overnight benchmark window')
            return h.report
        if selection.get('kind') != 'installed':
            raise ValueError('Reasoning screen only accepts an existing digest-pinned local GPT-OSS model')
        plan = h.validate_candidate(selection)
        info = h.api('show', {'model':plan['model']})
        if info.get('details',{}).get('family') != 'gptoss' or 'thinking' not in info.get('capabilities',[]):
            raise ValueError('The low-reasoning protocol is restricted to verified GPT-OSS capabilities')
        before = {name:row['digest'] for name,row in h.installed().items()}
        gpu = h.wait_idle(plan['bytes'])
        h.report.update(admission=plan, gpuBefore=gpu)
        h.reserve(plan)
        reserved = True
        measurement = {'model':plan['model'],'digest':plan['digest'],'endpoint':h.endpoint,
            'runtime':h.api('version'),'details':info.get('details'),'modelParameters':info.get('parameters'),
            'capabilities':info.get('capabilities'),'templateSha256':hashlib.sha256(info.get('template','').encode()).hexdigest(),
            'policy':h.policy.copy(),'thinking':'requested-low','generatedCodeExecution':'disabled'}
        h.report['benchmarks']=[measurement]
        h.save_report()
        loaded = True
        measurement['warmup'] = h.chat(plan['model'],'Reply with exactly: ready',True,think='low',num_predict=512,supervise=True)
        measurement['loadedModel']=h.api('ps').get('models',[])
        if any(row.get('digest') and row['digest'] != plan['digest'] for row in measurement['loadedModel'] if row.get('name') == plan['model']):
            raise RuntimeError('Loaded GPT-OSS digest changed')
        screen = quality_screen.run(h,plan['model'],True,{},think='low',output_cap=h.policy['thinkingProbeTokens'],allow_thinking=True)
        measurement['qualityScreen']=screen
        measurement['status']=screen['status']
        h.report['status']='completed' if screen['status']=='completed' else 'error'
        if screen['status']!='completed':
            h.report['error']='Reasoning screen incomplete: '+screen.get('reason','unknown')
    except Exception as exc:
        h.report.update(status='error',error=str(exc))
    finally:
        if loaded:
            try:
                with h.cleanup_window():
                    h.api('generate',{'model':plan['model'],'keep_alive':0},timeout=10)
                    h.confirm_unloaded(plan['model'],gpu['freeGiB'])
                measurement['unloadConfirmed']=True
            except Exception as exc:
                measurement['unloadWarning']=str(exc)
                h.report.update(status='error',cleanupError=str(exc))
        if before is not None:
            try:
                after={name:row['digest'] for name,row in h.installed().items()}
                h.report['primaryIntegrity']={'before':before,'after':after,'modelDigestsUnchanged':before==after}
                if before!=after:
                    h.report.update(status='error',error='Primary model digests changed during reasoning screen')
            except Exception as exc:
                h.report.update(status='error',error='Primary integrity could not be verified: '+str(exc))
        h.save_report()
        if reserved:
            h.finish_reservation()
    return h.report
