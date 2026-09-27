"""Summarize runs into comparison.json and Markdown tables.

Ranking rule: workload pass rate in each model's best supported mode (thinking on where the model has a
toggle, low reasoning for GPT-OSS, thinking off for Qwen3-Coder-Next), compared on the first 24 cases,
generation speed as tiebreak. Refusal flags are reported beside the ranking, never folded into it.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent


def row(path):
    d = json.loads(path.read_text())
    w, t, r = d.get('workloadSummary', {}), d.get('throughput', {}).get('summary', {}), d.get('refusal', {}).get('sets', {})
    return {'label': d['label'].removesuffix('-think'), 'file': path.name, 'status': d['status'], 'model': d['model'],
            'quant': (d.get('details') or {}).get('quantization_level'), 'think': d['think'],
            'caseCount': d['workloadProtocol']['caseCount'], 'outputCap': d['workloadProtocol']['outputCap'],
            'runtime': d.get('runtime', {}).get('version'), 'optionOverrides': d.get('optionOverrides'),
            'workloadPassed': w.get('passed'), 'workloadAttempted': w.get('attempted'), 'first24Passed': w.get('first24Passed'),
            'byCategory': w.get('byCategory'), 'truncated': w.get('truncated'), 'errors': w.get('errors'),
            'unexpectedThinking': w.get('unexpectedThinking'), 'workloadMedianGenTokPerSec': w.get('medianGenTokPerSec'),
            'medianOutputTokens': w.get('medianOutputTokens'),
            'workloadWallMin': round(w['totalWallMs'] / 60000, 1) if w.get('totalWallMs') else None,
            'genTokPerSec': t.get('medianGenTokPerSec'), 'promptTokPerSec': t.get('medianPromptTokPerSec'),
            'checks': f"{t.get('checksPassed')}/{t.get('checksTotal')}" if t else None,
            'refusalCap': d.get('refusal', {}).get('cap'),
            'harmfulFlagged': r.get('harmful', {}).get('flagged'), 'harmfulEmpty': r.get('harmful', {}).get('empty'),
            'harmlessFlagged': r.get('harmless', {}).get('flagged'), 'harmlessEmpty': r.get('harmless', {}).get('empty')}


rows = [x for x in (row(p) for p in sorted((HERE / 'runs').glob('*.json'))) if x['status'] == 'completed']
(HERE / 'comparison.json').write_text(json.dumps(rows, indent=1) + '\n')
primary = {x['label']: x for x in rows if x['caseCount'] == 96}
thinking = {x['label']: x for x in rows if x['caseCount'] == 24 and x['think'] == 'true'}

print('## Primary protocol: 96 cases, each model as configured in run_all.sh\n')
print('| Model | Quant | Mode | Workload /96 | First 24 | Gen tok/s | Prompt tok/s | Checks | Harmful flagged /100 | Harmless flagged /100 |')
print('|---|---|---|---:|---:|---:|---:|---:|---:|---:|')
for x in sorted(primary.values(), key=lambda x: -(x['workloadPassed'] or 0)):
    print(f"| {x['label']} | {x['quant']} | think={x['think']} | {x['workloadPassed']} | {x['first24Passed']} | {x['genTokPerSec']} | "
          f"{x['promptTokPerSec']} | {x['checks']} | {x['harmfulFlagged']} | {x['harmlessFlagged']} |")

print('\n## Ranking: best supported mode, first 24 cases\n')
best = []
for label, x in primary.items():
    alt = thinking.get(label)
    use = alt if alt and (alt['first24Passed'] or 0) >= (x['first24Passed'] or 0) else x
    best.append((use['first24Passed'] or 0, x['genTokPerSec'] or 0, label, use['think'], x))
print('| Rank | Model | Best mode | First 24 | Gen tok/s (throughput trial) | Harmful flagged /100 |')
print('|---:|---|---|---:|---:|---:|')
for i, (score, speed, label, mode, x) in enumerate(sorted(best, key=lambda b: (-b[0], -b[1])), 1):
    print(f"| {i} | {label} | think={mode} | {score}/24 | {speed} | {x['harmfulFlagged']} |")
