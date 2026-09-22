import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics

root=Path(__file__).resolve().parent
out=Path('/Users/kody/Documents/Codex/2026-09-22/le/outputs/deepseek-v4-report')
def load(p):return json.loads(p.read_text())
old=load(root/'run.json');new=load(root/'thinking-run.json');s=load(out/'summary.json')
assert new['status']=='completed' and len(new['modes']['thinking']['cases'])==24
assert load(root/'monitor-metadata.json')['processesExited']
for name in ('thinking-run.json','thinking-benchmark.log','monitor-metadata.json','deepseek_replay.py','run_monitored.py','analyze.py','build_report.py','test_replay.py'):
    shutil.copy2(root/name,out/name)
with (root/'thermal.jsonl').open('rb') as inp,gzip.open(out/'thermal.jsonl.gz','wb') as dst:shutil.copyfileobj(inp,dst)
chat=s['chat'];think=s['thinking'];thermal=s['thermal'];trials=old['throughput']['trials']
peak=max(r['response']['peakMemoryGB'] for r in new['modes']['thinking']['cases'])
oldpeak=max(t[k]['peakMemoryGB'] for t in trials for k in ('short','ingest'))
throughput=s['throughput'];ttfy=statistics.median(t['ingest']['timeToFirstYieldMs']/1000 for t in trials)
previous=load(Path('/Users/kody/repos/research/mac-model-benchmarks/native-runs/20260922-mlx-gpt-oss-v2.json'))
gpt=previous['summary']
category_rows='\n'.join(f"| {category} | {chat['categories'][category]['passed']}/{chat['categories'][category]['total']} | {result['passed']}/{result['total']} |" for category,result in think['categories'].items())
comparisons=[dict(model='DeepSeek V4 Flash 0731 2.4-bit mixed',mode='chat, temperature 0',source='chat-and-speed-run.json',**chat),
             dict(model='DeepSeek V4 Flash 0731 2.4-bit mixed',mode='thinking low, temperature 1',source='thinking-run.json',**think),
             dict(model='GPT-OSS 20B MXFP4-Q8',mode='low reasoning, temperature 0',source='../mac-model-benchmarks/native-runs/20260922-mlx-gpt-oss-v2.json',summary=gpt)]
(out/'comparison.json').write_text(json.dumps(comparisons,indent=2)+'\n')
text=f'''# DeepSeek V4 Flash on the M5 Max: speed, quality, temperature and fans

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Kody directed the work; Codex (OpenAI) prepared the runner, conducted the local measurements, and checked the sources.
<!-- /AI-ASSISTED-NOTE -->

Measured September 22, 2026, on an M5 Max MacBook Pro with 40 GPU cores, 18 CPU cores, 128 GiB unified memory, macOS 26.5, and AC power. This is an interactive desktop host.

**DeepSeek ran locally at {throughput['medianGenTokPerSec']:.1f} generation tokens/sec in the three short speed trials.** The thinking-mode pass, using DeepSeek's recommended local sampling temperature, answered **{think['passed']}/24** saved practical cases correctly. It generated at a median **{think['generationTokPerSec']['median']:.1f} tok/s**, with a median response time of **{think['wallSeconds']['median']:.1f} seconds**. The tests and their temperature/fan logger have completed and exited.

## Quality and response speed

| Configuration | Correct | Median generation tok/s | Median response seconds | Incomplete outputs |
|---|---:|---:|---:|---:|
| DeepSeek, thinking off, temperature 0 | {chat['passed']}/24 | {chat['generationTokPerSec']['median']:.2f} | {chat['wallSeconds']['median']:.3f} | {chat['truncated']} |
| DeepSeek, low thinking, temperature 1 | {think['passed']}/24 | {think['generationTokPerSec']['median']:.2f} | {think['wallSeconds']['median']:.3f} | {think['truncated']} |
| Earlier GPT-OSS 20B MLX, low reasoning, temperature 0 | {gpt['passed']}/24 | {gpt['medianGenTokPerSec']:.2f} | {gpt['medianWallMs']/1000:.3f} | {gpt['truncated']} |

All use the same 24 saved prompts and strict JSON grader. These are three cases each of ledger calculations, event state, dependency scheduling, SQL, shortest paths, extraction, Python tracing, and retrieval. They are **not a general intelligence or software-engineering benchmark**. Temperature, model, tokenizer, conversion, runtime, and cache architecture differ; the table compares observed configurations, not isolated hardware or runtime effects. Generation rates include reasoning and stop tokens reported by the runtime. Smaller models can finish these tasks faster even when decode tok/s alone is similar.

The thinking pass had {think['parseErrors']} channel-parsing failure{'s' if think['parseErrors']!=1 else ''}. One SQL response eventually included the correct values, but also emitted an earlier contradictory answer and two closing thinking delimiters. A second SQL response contained the correct values but an extra closing bracket, making its JSON invalid. Both fail the strict screen; manually repaired answers are not counted as passes. See the raw record and [notes](notes.md) for this distinction.

| Saved case category | Chat, temperature 0 | Thinking, temperature 1 |
|---|---:|---:|
{category_rows}

The initial greedy thinking diagnostic repeated fragments on its first case, hit the 8192-token cap, and produced no final answer. That diagnostic is retained separately. DeepSeek's official local guidance recommends temperature 1.0, top_p 1.0 for non-agentic scenarios. The completed thinking pass uses that sampling policy, unrestricted top_k, low effort, seed 42, an 8192-token cap, and a 300-second request limit. This is one sample per case, not an estimate of average accuracy over many seeds. No capped or timed-out output is counted as correct. [Official sampling guidance](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731#how-to-run-locally), [diagnostic](greedy-thinking-diagnostic/thinking-run.json).

## Short generation and prompt processing

| Measurement | Result |
|---|---:|
| Short generation, median of three trials | {throughput['medianGenTokPerSec']:.2f} tok/s |
| Ingest of 7,018-token prompt, median of three trials | {throughput['medianPromptTokPerSec']:.2f} tok/s |
| Time to first streamed yield for that long prompt, median | {ttfy:.2f} seconds |
| Peak MLX allocation across speed trials | {oldpeak:.2f} GB |
| Peak MLX allocation across thinking cases | {peak:.2f} GB |

These trials reuse the prior 100-word Rocky Mountains request and repeated-text ingest prompt. The earlier Qwen3-Coder 30B native MLX baseline was 139.68 generation tok/s and 4780.08 ingest tok/s at the same 2048-token prefill step. This is a different model with different quality and memory needs. See the [earlier benchmark](../mac-benchmark-report/README.md). Prompt timing includes the runtime's initial decode boundary; first-yield latency is a separate wall-clock measurement. Short warmup output is excluded.

## Temperature and fans

Installed **macmon 0.8.2** and verified CPU/GPU temperatures and both fan RPM sensors on this host. The thinking pass has **{thermal['samples']} one-second samples**, including loading, warmup, inference, and cleanup. The original speed/chat run happened before sensor logging and has no temperature trace.

| Sensor | Maximum observed during this monitored window |
|---|---:|
| CPU average temperature | {thermal['cpuAverageC']['max']:.1f}°C |
| GPU average temperature | {thermal['gpuAverageC']['max']:.1f}°C |
| Fan 0 | {thermal['fans']['fan0']['max']:.0f} RPM |
| Fan 1 | {thermal['fans']['fan1']['max']:.0f} RPM |
| Whole-system memory use | {thermal['systemRamGiB']['max']:.1f} GiB |
| Swap used | {thermal['swapBytes']['max']/2**20:.1f} MiB |

![Temperature, fan speeds, GPU clock, and per-case generation rates](thermal-chart.png)

Temperatures are macmon's sensor averages, not hottest-die or external calibrated measurements. GPU clocks and power are software-reported estimates. The chart shows the fan response and observed performance together; temperature alone cannot establish thermal throttling, and task length also affects speed. The pass started after an earlier diagnostic, not from a controlled cold state. Monitor overhead was not measured separately. [macmon documentation](https://github.com/vladkens/macmon).

For a live view, run `macmon`. For a ten-minute recording:

```sh
macmon pipe -i 1000 -s 600 > thermal.jsonl
```

The monitoring setup reads sensors. It does not change fan curves or install a startup service. macmon remains installed for future use; the benchmark logger exits with the run.

## Model and runtime

The [mixed 2.4-bit MLX artifact](https://huggingface.co/mlx-community/DeepSeek-V4-Flash-0731-2.4bit-mixed) is pinned to revision `10001e0065f8394e03e968e652cbbe7cd2ca122c`. Its tensors occupy 92.832 decimal GB on disk; all 24 downloaded files were hash-verified. This is aggressive quantization, and the results should not be generalized to DeepSeek's full-precision model.

Inference uses the official oMLX 0.6.4 wheel's model loader and direct MLX-LM generation, MLX 0.32.0, and MLX-LM 0.31.3 at the exact Git revision in [requirements](requirements.txt). Both native indexer kernels were available. Prefill step 2048; fresh architecture-native rotating/compressed caches; no KV quantization, cross-request prompt reuse, or speculative decoding. MTP/DSpark acceleration was not evaluated, so these measurements do not establish the maximum attainable speed. No generated code was executed.

The model remains cached for reuse. The earlier run was stopped at the user's request and resumed with a separate record; historical artifacts were not overwritten. See [notes](notes.md) for the full sequence, exact release checksum, and limitations.

## More models to consider

The earlier shortlist was not exhaustive. **Muse Glimmer 30B, Nemotron 3 Super, Qwen3.5-122B, Devstral Small 2, GLM-4.7-Flash, LFM2-24B, MiniMax M2.7 3-bit, and Granite 4.2 3B** all have relevant roles to evaluate. [The expanded comparison](OTHER-MODELS.md) provides verified weight sizes, primary sources, runtime caveats, and reasons to test each. None of those additional model weights was downloaded for this experiment.

## Saved evidence

- [Chat and speed raw record](chat-and-speed-run.json)
- [Completed thinking raw record](thinking-run.json)
- [Regraded summary and per-case thermal statistics](summary.json)
- [Raw one-second sensor log, gzip](thermal.jsonl.gz)
- [Monitor lifecycle and command](monitor-metadata.json)
- [Hash-verified model manifest](verified.json)
- [Runner](deepseek_replay.py), [monitor wrapper](run_monitored.py), [analysis and chart script](analyze.py)
- [Original chat/speed runner](original_replay.py), [observed-output regression checks](test_replay.py)
- [Candidate revisions and sizes](candidate-metadata.json), [source link checks](source-checks.json)

The scripts use local paths recorded in the notes; pass the research repository and artifact manifest explicitly when replaying. `requirements.txt` is the captured environment, including the local release-wheel path. Reinstall that checksum-verified official wheel to reproduce its environment. To regenerate the summary/plot from this directory, use a Python environment with Matplotlib and run `python analyze.py --repo /path/to/research`.
'''
(out/'README.md').write_text(text)
files=[]
for p in sorted(out.rglob('*')):
    if p.is_file() and p.name!='manifest.json':files.append(dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(out/'manifest.json').write_text(json.dumps(dict(createdAt=dt.datetime.now().astimezone().isoformat(),files=files),indent=2)+'\n')
print('Report assembled with',len(files),'files')
