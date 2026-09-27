"""Summarize runs into comparison.json and Markdown tables.

Ranking rule: workload pass rate in each model's best supported mode (thinking on where the model has a
toggle, low reasoning for GPT-OSS, thinking off for Qwen3-Coder-Next), compared on the first 24 cases,
generation speed as tiebreak. Refusal flags are reported beside the ranking, never folded into it.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / 'local-model-benchmarks'))
import quality_screen  # noqa: E402

# Diagnostic only: the prompts say "No markdown", so the strict score is the protocol result.
FENCE = re.compile(r'^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$', re.S | re.I)


def fences_stripped(cases):
    total = 0
    for x in cases:
        m = FENCE.match(x.get('response', {}).get('message', {}).get('content') or '')
        total += bool(x['passed'] or (not x['truncated'] and m and quality_screen.grade(m.group(1), x['expected'])))
    return total


def row(path):
    d = json.loads(path.read_text())
    w, t, r = d.get('workloadSummary', {}), d.get('throughput', {}).get('summary', {}), d.get('refusal', {}).get('sets', {})
    return {'label': d['label'].removesuffix('-think'), 'file': path.name, 'status': d['status'], 'model': d['model'],
            'quant': (d.get('details') or {}).get('quantization_level'), 'think': d['think'],
            'caseCount': d['workloadProtocol']['caseCount'], 'outputCap': d['workloadProtocol']['outputCap'],
            'runtime': d.get('runtime', {}).get('version'), 'optionOverrides': d.get('optionOverrides'),
            'workloadPassed': w.get('passed'), 'workloadAttempted': w.get('attempted'), 'first24Passed': w.get('first24Passed'),
            'fencesStripped': fences_stripped(d.get('cases', [])), 'fencesStripped24': fences_stripped(d.get('cases', [])[:24]),
            'secPerCase24': round(sum(c['response']['supervisedWallMs'] for c in d.get('cases', [])[:24] if 'response' in c) / 24000, 1) if d.get('cases') else None,
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
primary = {x['label']: x for x in rows if x['caseCount'] == 96 and x['workloadPassed'] is not None and not x['label'].endswith('-think96')}
thinking = {x['label']: x for x in rows if x['caseCount'] == 24 and x['think'] != 'false'}
full_reasoning = [x for x in rows if x['label'].endswith('-think96')]
prefill = {x['label'].removesuffix('-refusal-prefill'): x for x in rows if x['label'].endswith('-refusal-prefill')}

print('## Primary protocol: 96 cases, each model as configured in run_all.sh\n')
print('| Model | Quant | Mode | Workload /96 | Fences stripped /96 | First 24 | Gen tok/s | Prompt tok/s | Checks | Harmful flagged /100 | Harmless flagged /100 |')
print('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|')
for x in sorted(primary.values(), key=lambda x: -(x['workloadPassed'] or 0)):
    print(f"| {x['label']} | {x['quant']} | think={x['think']} | {x['workloadPassed']} | {x['fencesStripped']} | {x['first24Passed']} | {x['genTokPerSec']} | "
          f"{x['promptTokPerSec']} | {x['checks']} | {x['harmfulFlagged']} | {x['harmlessFlagged']} |")

print('\n## Ranking: best supported mode, first 24 cases\n')
print('Tiebreak speed is the thinking-off throughput-trial generation rate; s/case is wall time per case in the ranked mode.\n')
best = []
for label, x in primary.items():
    alt = thinking.get(label)
    use = alt if alt and (alt['first24Passed'] or 0) >= (x['first24Passed'] or 0) else x
    best.append((use['first24Passed'] or 0, x['genTokPerSec'] or 0, label, use, x))
print('| Rank | Model | Best mode | First 24 | Fences stripped | s/case (ranked mode) | Gen tok/s (throughput trial) | Harmful flagged /100 |')
print('|---:|---|---|---:|---:|---:|---:|---:|')
for i, (score, speed, label, use, x) in enumerate(sorted(best, key=lambda b: (-b[0], -b[1])), 1):
    harmful = prefill[label]['harmfulFlagged'] if label in prefill else x['harmfulFlagged']
    print(f"| {i} | {label} | think={use['think']} | {score}/24 | {use['fencesStripped24']}/24 | {use['secPerCase24']} | {speed} | {harmful} |")

if full_reasoning:
    print('\n## Full 96 cases with reasoning on\n')
    print('| Model | Mode | Strict /96 | Fences stripped | Truncated | Median generated tokens | Wall min |')
    print('|---|---|---:|---:|---:|---:|---:|')
    for x in full_reasoning + [p for p in primary.values() if p['think'] not in ('false',)]:
        print(f"| {x['label']} | think={x['think']} | {x['workloadPassed']} | {x['fencesStripped']} | {x['truncated']} | {x['medianOutputTokens']} | {x['workloadWallMin']} |")

if prefill:
    print('\n## Refusal with Heretic-style GPT-OSS prefill (100 tokens, final channel)\n')
    print('| Model | Harmful flagged /100 | Harmful empty | Harmless flagged /100 | Harmless empty |')
    print('|---|---:|---:|---:|---:|')
    for label, x in prefill.items():
        print(f"| {label} | {x['harmfulFlagged']} | {x['harmfulEmpty']} | {x['harmlessFlagged']} | {x['harmlessEmpty']} |")
