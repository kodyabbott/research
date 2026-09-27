"""Summarize completed runs into comparison.json and a Markdown table (ranked by workload score)."""
import json
from pathlib import Path

HERE = Path(__file__).parent


def row(path):
    d = json.loads(path.read_text())
    w, t, r = d.get('workloadSummary', {}), d.get('throughput', {}).get('summary', {}), d.get('refusal', {}).get('sets', {})
    return {'label': d['label'], 'file': path.name, 'status': d['status'], 'model': d['model'],
            'quant': (d.get('details') or {}).get('quantization_level'), 'think': d['think'],
            'blobBytes': d.get('artifact', {}).get('size'), 'runtime': d.get('runtime', {}).get('version'),
            'workloadPassed': w.get('passed'), 'workloadAttempted': w.get('attempted'), 'first24Passed': w.get('first24Passed'),
            'byCategory': w.get('byCategory'), 'truncated': w.get('truncated'), 'errors': w.get('errors'),
            'unexpectedThinking': w.get('unexpectedThinking'), 'workloadMedianGenTokPerSec': w.get('medianGenTokPerSec'),
            'workloadWallMin': round(w['totalWallMs'] / 60000, 1) if w.get('totalWallMs') else None,
            'genTokPerSec': t.get('medianGenTokPerSec'), 'promptTokPerSec': t.get('medianPromptTokPerSec'),
            'checks': f"{t.get('checksPassed')}/{t.get('checksTotal')}" if t else None,
            'refusalCap': d.get('refusal', {}).get('cap'),
            'harmfulFlagged': r.get('harmful', {}).get('flagged'), 'harmfulEmpty': r.get('harmful', {}).get('empty'),
            'harmlessFlagged': r.get('harmless', {}).get('flagged'), 'harmlessEmpty': r.get('harmless', {}).get('empty')}


rows = sorted((row(p) for p in sorted((HERE / 'runs').glob('*.json'))),
              key=lambda x: (-(x['workloadPassed'] or 0), -(x['genTokPerSec'] or 0)))
(HERE / 'comparison.json').write_text(json.dumps(rows, indent=1) + '\n')
print('| Rank | Model | Quant | Workload /96 | First 24 | Gen tok/s | Prompt tok/s | Checks | Harmful flagged /100 | Harmless flagged /100 |')
print('|---:|---|---|---:|---:|---:|---:|---:|---:|---:|')
for i, x in enumerate(rows, 1):
    print(f"| {i} | {x['label']} | {x['quant']} | {x['workloadPassed']} | {x['first24Passed']} | {x['genTokPerSec']} | "
          f"{x['promptTokPerSec']} | {x['checks']} | {x['harmfulFlagged']} | {x['harmlessFlagged']} |")
