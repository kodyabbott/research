"""Summarize the recorded native MLX and matched Ollama experiments."""
import argparse
import json
from pathlib import Path


def build(root):
    ollama={r['model']:r for p in (root/'runs').glob('20260922-*.json') if (r:=json.loads(p.read_text())).get('status')=='completed'}
    native=[(p,json.loads(p.read_text())) for p in (root/'native-runs').glob('20260922-*.json')]
    complete=[(p,r) for p,r in native if r.get('status')=='completed' and r.get('summary')]
    complete.sort(key=lambda item:(item[1]['modelKey'],item[1]['protocol']['prefillStepSize']))
    names={'qwen3-coder:30b':'Qwen3-Coder 30B','gpt-oss:20b':'GPT-OSS 20B','nightly-bench-d5808e5874e660a8:latest':'Gemma 4 31B'}
    lines=['# Local models on the M5 Max: MLX and Ollama', '',
        '<!-- AI-ASSISTED-NOTE -->','> [!NOTE]',
        '> This is an AI-assisted research report. Kody directed the work; Codex (OpenAI) prepared and ran the measurements.',
        '<!-- /AI-ASSISTED-NOTE -->','',
        'Measured September 22, 2026, on this MacBook Pro: M5 Max, 18 CPU cores, 40 GPU cores, 128 GB unified memory, macOS 26.5, AC power. The user selected a Mac-focused comparison with runtime differences labeled. Three exact-artifact Ollama runs provide a reference, followed by two native MLX model conversions and a Qwen prefill-size diagnostic.', '',
        '**Observed result:** Qwen MLX with an 8192-token prefill batch processed the long prompt at 5802 tokens/sec versus 2033 for Ollama (2.85 times the rate); generation remained about 136 tokens/sec. GPT-OSS MLX had a 3.00-second median workload response versus 3.70 seconds over Ollama HTTP. Both MLX conversions scored one fewer case correct in this 24-case screen. The speed gains and that small accuracy tradeoff should be considered together.', '',
        '## Native MLX versus Ollama on this Mac', '',
        'All rows use the same 24 saved workload prompts and strict JSON grader. Each covers three cases from each of eight categories: ledger replay, event reconstruction, scheduling, SQL, shortest paths, extraction, Python tracing, and retrieval. These are small authored answer-quality checks, not a coding benchmark or general model ranking.', '',
        '| Model / MLX prefill batch | MLX correct | Ollama correct | MLX median s | Ollama HTTP median s | Ollama / MLX latency |',
        '|---|---:|---:|---:|---:|---:|']
    data=[]
    for p,r in complete:
        o=ollama[r['modelKey']];s=r['summary'];old=o['summary'];a=s['medianWallMs']/1000;b=old['medianClientWallMs']/1000
        lines.append(f"| {names[r['modelKey']]} / {r['protocol']['prefillStepSize']} | {s['passed']}/24 | {old['passed']}/24 | {a:.3f} | {b:.3f} | {b/a:.2f}× |")
        data.append({'modelKey':r['modelKey'],'mlxModel':r['model'],'prefillStepSize':r['protocol']['prefillStepSize'],
            'mlx':s,'ollama':old,'ollamaHttpToMlxLatencyRatio':b/a,'rawFile':'native-runs/'+p.name,
            'quantization':r['modelConfig'].get('quantization'),'runtime':r['runtime']})
    lines += ['',
        'A ratio above 1 means the observed MLX median was faster. MLX latency includes template rendering and generation in one Python process; Ollama latency is the local HTTP round trip, excluding the separate Python supervisor startup. This is an application-path comparison, not a pure kernel benchmark.', '',
        'Qwen uses thinking off and a 2048-token output cap; GPT-OSS uses low reasoning and an 8192-token cap. Both use temperature 0, seed 42, top_p 1, top_k 40, and no repetition penalty. The 8192-token MLX KV-cache limit has rotating-cache semantics; raw records flag any sequence that exceeded that budget.', '',
        '## Qwen short generation and long-prompt ingest', '',
        '| Configuration | Median generation tok/s | Median ingest tok/s | Median short-response s |',
        '|---|---:|---:|---:|']
    q=ollama['qwen3-coder:30b']['throughput']['summary']
    lines.append(f"| Ollama 0.32.13, Q4_K_M | {q['medianGenTokPerSec']:.2f} | {q['medianPromptTokPerSec']:.2f} | {q['medianClientWallMs']/1000:.3f} |")
    for p,r in complete:
        if not r.get('throughput'):continue
        s=r['throughput']['summary']
        lines.append(f"| MLX 4-bit, prefill {r['protocol']['prefillStepSize']} | {s['medianGenTokPerSec']:.2f} | {s['medianPromptTokPerSec']:.2f} | {s['medianWallMs']/1000:.3f} |")
    lines += ['',
        'Three repetitions after warmup reuse the same 100-word Rocky Mountains request and roughly 7000-token ingest prompt. Generation rates are runtime-reported and their timing boundaries differ. A few-percent generation difference is not established as significant by three trials. Larger prefill batches are an explicitly separate configuration, with workload scoring retained.', '',
        '## Runtime and artifact differences', '',
        '- MLX 0.32.2, MLX-LM 0.31.3, Python 3.12.14. Both conversions are pinned to full Hugging Face revisions and every downloaded file was hash-verified. [Environment versions](requirements-mlx.txt).',
        '- Qwen MLX uses affine 4-bit weights with 64-element groups and selected 8-bit gates; Ollama uses Q4_K_M GGUF. GPT-OSS MLX uses the MXFP4-Q8 conversion; Ollama uses its MXFP4 GGUF. These are different artifacts. Score or speed differences cannot be attributed solely to MLX.',
        '- MLX uses its native chat templates, fresh KV caches, no KV quantization, and no speculative decoding. The rendered prompt and raw reasoning/final channel text are saved. Template and token-count differences remain visible.',
        '- The activation-quantization option in the installed MLX-LM source accepts nvfp4/mxfp8 layers; these selected affine/mxfp4 artifacts are ineligible. It was inspected, not forced on or benchmarked.',
        '- The first GPT-OSS native warmup exposed a parser mismatch with the artifact’s channel-token spellings. It produced zero scored cases, is preserved as a diagnostic, and is excluded here. A regression test covers the observed spelling; the corrected run retains the model’s final channel verbatim for grading.',
        '- This is an interactive desktop session, not an isolated laboratory host. No sustained-load, energy, battery, full coding-suite, LM Studio, or newest-Ollama comparison was run. These results identify observed tradeoffs among the tested configurations, not a global optimum.', '',
        '## Matched Windows reference', '',
        'The Windows records below are from September 11, the latest committed campaign in the cloned repository. Matching Ollama 0.32.13, exact model digests, template hashes, parameter values, request settings, and prompts were verified before the Mac reference runs. Windows used an RTX PRO 6000 Blackwell Max-Q with 96 GB VRAM; Mac used Metal.', '',
        '| Model | Mac Ollama correct | RTX correct | Mac supervised median s | RTX supervised median s |',
        '|---|---:|---:|---:|---:|']
    for key in names:
        r=ollama[key];s=r['summary'];old=r['reference']['summary']
        lines.append(f"| {names[key]} | {s['passed']}/24 | {old['passed']}/24 | {s['medianWallMs']/1000:.3f} | {old['medianWallMs']/1000:.3f} |")
    lines += ['',
        'These historical medians include the Python supervisor startup, unlike the HTTP-only column above. See [the full matched comparison](OLLAMA-COMPARISON.md) for the Gemma/Qwen throughput and source-run links. All three matched Mac reference runs completed without truncation or unexpected thinking, and unloaded successfully.', '',
        '## Evidence and reuse', '',
        'The repository is `~/repos/research`, local branch `codex/m5-max-benchmark-comparison`. The original nightly policy and all historical records are unchanged. Models remain in `/Users/<user>/Documents/Codex/model-cache/mac-benchmarks` for reuse; weights are not committed.', '',
        '- [Research notes and commands](notes.md)',
        '- [Native replay runner](mlx_replay.py), [Ollama replay runner](mac_replay.py)',
        '- [Native comparison data](native-comparison.json), [matched comparison data](comparison.json)',
    ]
    for p,r in complete:lines.append(f"- [{names[r['modelKey']]} MLX, prefill {r['protocol']['prefillStepSize']} raw run](native-runs/{p.name}).")
    lines += ['',
        'Primary runtime/model references: [MLX-LM](https://github.com/ml-explore/mlx-lm), [Qwen MLX artifact](https://huggingface.co/mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit/tree/6e302ea604ad9ab206367e2c501d1571023e7b6d), [GPT-OSS MLX artifact](https://huggingface.co/mlx-community/gpt-oss-20b-MXFP4-Q8/tree/773a7da77e569019bb0fd17a554b263738d669a3).', '']
    return '\n'.join(lines),data


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    report,data=build(a.root)
    (a.root/'README.md').write_text(report)
    (a.root/'native-comparison.json').write_text(json.dumps(data,indent=2)+'\n')
