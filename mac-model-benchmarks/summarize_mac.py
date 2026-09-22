"""Build a comparison report from raw Mac runs and pinned Windows records."""
import argparse
import json
from pathlib import Path
import statistics


def build(repo, raw_dir):
    rows = [json.loads(p.read_text()) for p in sorted(raw_dir.glob('*.json')) if p.name.startswith('20260922-')]
    rows = [r for r in rows if r.get('status') == 'completed' and r.get('summary')]
    names = {'qwen3-coder:30b': 'Qwen3-Coder 30B Q4_K_M', 'gpt-oss:20b': 'GPT-OSS 20B MXFP4',
             'nightly-bench-d5808e5874e660a8:latest': 'Gemma 4 31B Q8_0'}
    rows.sort(key=lambda r: list(names).index(r['model']))
    lines = [
        '# M5 Max versus RTX PRO 6000: matched local-model comparison', '',
        '<!-- AI-ASSISTED-NOTE -->',
        '> [!NOTE]',
        '> This is an AI-assisted research report. Kody directed the work; Codex (OpenAI) prepared and ran the local measurements.',
        '<!-- /AI-ASSISTED-NOTE -->', '',
        'Measured on September 22, 2026, against saved September 11 Windows runs. This is a system-level comparison: Apple Metal on an M5 Max versus CUDA on an RTX PRO 6000 Blackwell Max-Q. Model digests, quantization, template hashes, model parameters, Ollama 0.32.13, prompts, and request settings match. Operating systems, GPU backends, and host conditions differ.', '',
        'The Mac is a MacBook Pro with an M5 Max, 18 CPU cores, 40 GPU cores, and 128 GB unified memory, running macOS 26.5 (25F71) on AC power. The historical workstation has an RTX PRO 6000 Blackwell Max-Q with 96 GB VRAM, Ryzen 9 9950X, and 128 GB RAM. See [the original report](../local-model-benchmarks/README.md) and the raw host snapshots in each run.', '',
        '## Matched 24-case workload', '',
        '| Model | Mode | Mac correct | RTX correct | Mac median s | RTX median s | Mac / RTX latency |',
        '|---|---|---:|---:|---:|---:|---:|',
    ]
    comparison = []
    for r in rows:
        s, old = r['summary'], r['reference']['summary']
        a,b = s['medianWallMs']/1000, old['medianWallMs']/1000
        mode = 'low reasoning' if r['protocol']['thinking'] == 'low' else 'thinking off'
        lines.append(f"| {names[r['model']]} | {mode} | {s['passed']}/24 | {old['passed']}/24 | {a:.3f} | {b:.3f} | {a/b:.2f}× |")
        ref = json.loads((repo/r['reference']['file']).read_text())
        previous = next(x for x in ref['benchmarks'] if x['model'] == r['model'])
        before = {x['id']:x for x in previous['cases']}
        changes = [{'id':x['id'], 'windowsPassed':before[x['id']]['passed'], 'macPassed':x['passed']} for x in r['cases'] if x['passed'] != before[x['id']]['passed']]
        comparison.append({'model':r['model'],'mac':s,'windows':old,'latencyRatio':a/b,'changedCaseOutcomes':changes,
                           'reference':r['reference'],'identityChecks':r['identityChecks']})
    lines += ['',
        'Each row replays the exact first 24 `practical-json-v1` cases: three each for ledger replay, event-state reconstruction, dependency scheduling, SQL analysis, shortest paths, record extraction, Python tracing, and retrieval. One deterministic sample is generated per case. Correctness uses the existing strict JSON grader; generated code is never executed.', '',
        'Settings: context 8192, temperature 0, seed 42, top_p 1, top_k 40, repeat penalty 1.0. Qwen and Gemma receive a 2048-token output cap; GPT-OSS retains its historical low-reasoning mode and 8192-token cap. These modes are not an equal-budget cross-model quality comparison.', '',
        'Latency is the median supervised response wall time, including Python subprocess startup; raw records also preserve HTTP round-trip and server timings. Model load and warmup are excluded. A ratio above 1 means the Mac took longer. Same-seed outputs can differ between Metal and CUDA, so score changes are observations from one pass, not evidence that hardware improves model capability.', '',
        '## Short generation and prompt ingest', '',
        '| Model | Mac generation tok/s | RTX generation tok/s | Mac / RTX throughput | Mac ingest tok/s | RTX ingest tok/s |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for r in rows:
        if not r.get('throughput'): continue
        t=r['throughput'];s=t['summary'];old=t['referenceSummary']
        ref=json.loads((repo/t['referenceFile']).read_text());b=next(x for x in ref['benchmarks'] if x['model']==r['model'])
        ingest=statistics.median(x['ingest']['promptTokPerSec'] for x in b['trials'])
        lines.append(f"| {names[r['model']]} | {s['medianGenTokPerSec']:.2f} | {old['medianGenTokPerSec']:.2f} | {s['medianGenTokPerSec']/old['medianGenTokPerSec']:.2f}× | {s['medianPromptTokPerSec']:.1f} | {ingest:.1f} |")
    lines += ['',
        'Three repetitions after warmup reuse the historical 100-word Rocky Mountains request and roughly 7000-token ingest prompt, with a 512-token output cap. Prompt rates use the runtime-reported token counts; cache-split telemetry is unavailable in these records. These API numbers are not time to first token. GPT-OSS has no thinking-off throughput row because its matched workload uses reasoning.', '',
        '## Integrity and limitations', '',
        '- The runner refuses model digest, template, parameter, quantization, or runtime-version mismatches. Parameter group ordering is normalized because Ollama prints map entries in varying order; values and repeated stop sequences must still match.',
        '- Historical Windows files and the nightly policy remain unchanged. This is a separately requested manual Mac run; the canceled Windows campaign is not resumed.',
        '- Each request has a 120-second deadline and each model replay a 30-minute deadline. Failure preserves partial records and attempts model unload.',
        '- One model is loaded at a time. The host is an interactive desktop, not an isolated laboratory machine. GPU utilization is not continuously sampled; operating-system work and thermal conditions are uncontrolled.',
        '- This appendix measures the pinned Ollama configuration. The separate MLX experiment is in README.md; LM Studio, current Ollama, long-context behavior, full coding suites, and energy consumption are not measured.', '',
        '## Evidence', '',
    ]
    for r in rows:
        file=next(p.name for p in raw_dir.glob('20260922-*.json') if json.loads(p.read_text()).get('startedAt')==r['startedAt'] and json.loads(p.read_text()).get('model')==r['model'])
        lines.append(f"- {names[r['model']]}: [Mac raw run](runs/{file}); [Windows workload source](../{r['reference']['file']}).")
    lines += ['', 'See [notes and reproduction steps](notes.md), [replay runner](mac_replay.py), and [comparison data](comparison.json).', '']
    return '\n'.join(lines), comparison


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    report,rows=build(a.repo,a.raw_dir);a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/'README.md').write_text(report)
    (a.output_dir/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
