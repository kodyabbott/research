"""Build a dated progress report from saved campaign records; never launches inference."""
import json
from pathlib import Path
from nightly import atomic_json, now, read_json

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'campaigns/20260910-overnight'


def screen_text(screen):
    if not screen:
        return 'not run'
    if screen.get('status') != 'completed':
        return screen.get('status', 'unknown')
    score = f"{screen['passed']}/{screen['total']}"
    if not screen.get('validThinkingOffScreen') and not screen.get('validReasoningScreen'):
        score += ' (thinking mismatch)'
    return score


def build(campaign_id=None):
    global FOLDER
    queue_path = ROOT/'state/campaign-20260910-queue.json'
    if campaign_id:
        import re
        if not re.fullmatch(r'[a-z0-9-]+',campaign_id):
            raise ValueError('Invalid campaign ID')
        FOLDER = ROOT/'campaigns'/campaign_id
        queue_path = ROOT/'state'/('campaign-'+campaign_id+'-queue.json')
    queue = read_json(queue_path)
    rows = []
    for item in queue['items']:
        selection = read_json(ROOT/item['selectionFile'])
        path = ROOT/'runs'/(item.get('runId', 'not-started')+'.json')
        report = read_json(path, {})
        benches = report.get('benchmarks', [])
        candidate = benches[0] if benches else {}
        baseline = benches[1] if len(benches)>1 else {}
        rows.append({'id':item['id'], 'model':selection.get('model') or selection.get('repoId'),
            'mode':report.get('mode'), 'protocol':report.get('protocol'),
            'artifact':selection.get('filename'), 'status':report.get('status',item['status']),
            'runId':item.get('runId'), 'resultFile':report.get('resultFile'),
            'startedAt':report.get('startedAt'), 'finishedAt':report.get('finishedAt'),
            'comparison':report.get('comparison'),
            'candidate':{k:candidate.get(k) for k in ('model','digest','details','summary','qualityScreen','thinkingProbe','unloadConfirmed')},
            'baseline':{k:baseline.get(k) for k in ('model','digest','summary','qualityScreen','thinkingProbe','unloadConfirmed')},
            'primaryDigestsUnchanged':report.get('primaryIntegrity',{}).get('modelDigestsUnchanged'),
            'error':report.get('error') or report.get('reason'),
            'cleanupErrors':{k:report[k] for k in ('cleanupError','preflightCleanupError','uploadedBlobCleanupErrors','importBookkeepingError','postProcessingError') if k in report}})
    data={'campaignId':queue['campaignId'],'campaignStatus':queue.get('status','running'),'cancelledAt':queue.get('cancelledAt'),'generatedAt':now(),'rows':rows,
          'scope':'Separate text throughput, authored exact-answer workloads, and isolated JavaScript function-writing screens; protocol and reasoning budgets are recorded per run.'}
    atomic_json(FOLDER/'results.json',data)
    lines=['# Model benchmark campaign results', '', 'Updated: '+data['generatedAt'], '',
           ('The user canceled the campaign at '+queue['cancelledAt']+'. All campaign processes are stopped and overnight follow-ups are paused.' if queue.get('status')=='cancelled' else 'This is a progress report until every worthwhile queued test is complete or its authorization ends.'),
           'Rows remain in queue order, not quality rank. Only terminal records are scored. Raw throughput from invalid comparisons is omitted here and retained in the linked JSON.', '',
           '| Model / artifact | Run status | Valid throughput, candidate / coder (tok/s) | Quality screen (protocol shown) | Exact checks, candidate / coder |',
           '|---|---|---:|---|---|']
    for row in rows:
        report_status=row['status']; comparison=row.get('comparison') or {}
        c,b=row['candidate'],row['baseline']; cs,bs=c.get('summary') or {},b.get('summary') or {}
        cq,bq=c.get('qualityScreen') or {},b.get('qualityScreen') or {}
        label=row['model'] + (('<br>'+row['artifact']) if row.get('artifact') else '')
        if row.get('resultFile') and report_status not in ('queued','running'):
            label='['+label+'](../../'+row['resultFile']+')'
        terminal=report_status=='completed'
        status=report_status
        speed=quality=checks='—'
        if terminal and row.get('mode')=='campaign-humanevalx-screen':
            status='HumanEval-X adapted screen'
            quality=f"{cs.get('tasksPassed')}/{cs.get('tasksTotal')} tasks (separate)"
        elif terminal and row.get('mode')=='campaign-coding-screen':
            status='code-writing screen'
            quality=f"{cs.get('tasksPassed')}/{cs.get('tasksTotal')} tasks; {cs.get('testsPassed')}/{cs.get('testsTotal')} tests (separate)"
        elif terminal and row.get('mode')=='campaign-workload-screen':
            status='workload screen'
            quality=f"{cs.get('passed')}/{cs.get('total')} (practical-json-v1, separate)"
        elif terminal and row.get('mode')=='campaign-reasoning-screen':
            status='reasoning-only screen'
            quality=screen_text(cq)+' (low reasoning; unpaired)'
        elif terminal:
            status='valid comparison' if comparison.get('valid') else 'invalid comparison'
            if comparison.get('valid'):
                speed=f"{cs.get('medianGenTokPerSec')} / {bs.get('medianGenTokPerSec')}"
            if cq.get('version')=='overnight-screen-v2' and bq.get('version')=='overnight-screen-v2':
                quality=screen_text(cq)+' / '+screen_text(bq)
            elif cq.get('version')=='overnight-screen-v1':
                quality='v1 pilot; kept separate'
            checks=f"{cs.get('checksPassed','?')}/{cs.get('checksTotal','?')} / {bs.get('checksPassed','?')}/{bs.get('checksTotal','?')}"
        lines.append(f'| {label} | {status} | {speed} | {quality} | {checks} |')
    lines += ['', '## Limits and failed cases', '',
              'The separate function-writing screen executes eight generated functions against 99 hidden checks in QuickJS WASM; it uses 16384 context and is not pooled with the answer-only screens. The practical JSON suite uses 96 authored checks in 24-case blocks. The 16-item v2 screen measures exact structured answers, code comprehension, small reasoning problems and evidence handling. It does not execute generated code or test a production coding agent. One item changes the score by 6.25 percentage points; differences are descriptive and have no statistical significance claim. V1 pilot and V2 main-sweep scores are not pooled.', '',
              'A valid throughput comparison does not certify model quality. A completed quality screen is reported separately when throughput is invalid; truncation counts as a failed screen case, and unexpected returned thinking is explicitly marked. Stored BF16/MTP/DFlash configurations include custom settings and cannot isolate quantization effects.', '',
              'The separate GPT-OSS low-reasoning screen allows 8192 generated tokens per case versus 512 in the main sweep. It is unpaired and is not an equal-budget quality ranking. Thinking probes below are single exploratory trials excluded from throughput medians; ratios against an invalid ordinary comparison are diagnostic only.', '']
    for row in rows:
        if row['status'] not in ('completed','error','deferred','cancelled') or not row.get('runId'):
            continue
        lines.append('### '+row['id'])
        lines.append('')
        if row.get('error'):
            lines.append('Run issue: '+row['error'])
        comp=row.get('comparison') or {}
        if comp.get('invalidReason'):
            lines.append('Comparison issue: '+comp['invalidReason'])
        for side in ('candidate','baseline'):
            q=row[side].get('qualityScreen') or {}
            failed=[x['name'] for x in q.get('cases',[]) if not x['passed']]
            if q:
                lines.append(side.capitalize()+': '+q.get('version','unknown')+', '+screen_text(q)+'. Failed cases: '+(', '.join(failed) if failed else 'none recorded')+'.')
                if q.get('error') or q.get('reason'):
                    lines.append(side.capitalize()+' quality screen issue: '+str(q.get('error') or q.get('reason')))
            probe=row[side].get('thinkingProbe') or {}
            if probe:
                line=side.capitalize()+' thinking probe: '+probe.get('status','unknown')+'.'
                if probe.get('error') or probe.get('reason'):
                    line+=' '+str(probe.get('error') or probe.get('reason'))
                if probe.get('status')=='completed':
                    ratio=probe.get('wallTimeRatioToThinkingOffMedian')
                    line+=' Wall-time ratio to ordinary median: '+(f'{ratio:.2f}x' if isinstance(ratio,(int,float)) else 'unavailable')+'.'
                    line+=' Thinking characters: '+str(probe.get('thinkingCharacters'))+'; answer characters: '+str(probe.get('answerCharacters'))+'.'
                    if probe.get('response',{}).get('done_reason')=='length':
                        line+=' Output reached the token cap.'
                lines.append(line)
        lines.append('Personal model digests unchanged: '+str(row.get('primaryDigestsUnchanged'))+'.')
        if row.get('cleanupErrors'):
            lines.append('Cleanup/postprocessing issue: '+json.dumps(row['cleanupErrors']))
        lines.append('')
    lines += ['Public publishing remains pending the specific approval requested in this thread. Local reports and commits continue independently.', '']
    (FOLDER/'results.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'generatedAt':data['generatedAt'],'completed':sum(r['status']=='completed' for r in rows),
        'running':sum(r['status'] in ('queued','running') for r in rows),'pending':sum(r['status']=='pending' for r in rows),
        'report':str(FOLDER/'results.md')}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--campaign')
    args=parser.parse_args()
    build(args.campaign)
