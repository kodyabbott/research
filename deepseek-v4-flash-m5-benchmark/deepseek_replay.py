"""Pinned DeepSeek V4 Flash MLX replay of the saved 24 practical JSON cases."""
from __future__ import annotations
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time


def extract_answer(raw, mode):
    if mode == 'chat':
        unexpected = '<think>' in raw or '</think>' in raw
        return dict(content=raw, thinking='', parseError='Unexpected thinking delimiter' if unexpected else None)
    # The prompt already ends in <think>; the generated stream must close it.
    if raw.count('</think>') != 1:
        return dict(content='', thinking=raw, parseError='Expected exactly one closing thinking delimiter')
    thinking, final = raw.split('</think>')
    if '<think>' in final:
        return dict(content='', thinking=raw, parseError='Unexpected second thinking block')
    return dict(content=final.strip(), thinking=thinking, parseError=None)


class Replay:
    def __init__(self, args):
        self.args = args
        sys.path.insert(0, str(args.repo / 'mac-model-benchmarks'))
        import mac_replay
        self.common = mac_replay
        sys.path.insert(0, str(args.repo / 'local-model-benchmarks'))
        import quality_screen, workload_suite
        self.grade = quality_screen.grade
        self.cases = workload_suite.cases()[:24]
        spec = json.loads(args.selection.read_text())
        assert spec['verified'] and 'DeepSeek-V4-Flash-0731' in spec['repoId']
        self.spec = spec
        reference = args.repo / 'local-model-benchmarks/runs' / mac_replay.REFERENCES['gpt-oss:20b']
        historical = json.loads(reference.read_text())
        benchmark = next(b for b in historical['benchmarks'] if b['model'] == 'gpt-oss:20b')
        assert self.cases == [{k:r[k] for k in ('id','category','prompt','expected')} for r in benchmark['cases']]
        if args.output.exists():
            raise ValueError('Refusing to overwrite raw results')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        self.report = dict(
            schemaVersion=1, runtimeKind='oMLX loader plus mlx-lm direct generation',
            startedAt=mac_replay.now(), status='running', model=spec['repoId'], artifact=spec,
            runnerSha256=mac_replay.sha(__file__), python=sys.version,
            runtime={name:importlib.metadata.version(name) for name in ('omlx','mlx','mlx-lm','transformers','tokenizers')},
            dependencyPins={d.metadata['Name']:d.read_text('direct_url.json') for d in importlib.metadata.distributions() if d.read_text('direct_url.json')},
            hostBefore=mac_replay.host_snapshot(), generatedCodeExecution='disabled',
            reference=dict(file=str(reference.relative_to(args.repo)),sha256=mac_replay.sha(reference)),
            sourceHashes={n:mac_replay.sha(args.repo/'local-model-benchmarks'/n) for n in ('workload_suite.py','quality_screen.py')},
            protocol=dict(suiteSha256=historical['protocol']['suiteSha256'],caseCount=24,temperature=args.temperature,seed=42,
                topP=1,topK=40 if args.temperature==0 else 0,repeatPenalty=1,requestTimeoutSeconds=300,
                prefillStepSize=2048,kvCacheQuantization=None,crossRequestPromptCache=False,
                cache='DeepSeek architecture-native rotating and compressed pooling caches; no global 8192 cap',
                speculativeDecoding=False,reasoningEffort='low',outputCaps=dict(chat=2048,thinking=8192),
                requestedModes=args.modes,skipThroughput=args.skip_throughput),
            comparisonLimits=[
                'Different model, quantization, tokenizer and runtime from prior runs; not a runtime-only experiment.',
                'Generation throughput counts reasoning tokens as well as final-answer tokens.',
                'A 24-case authored screen is not a general intelligence or software engineering benchmark.',
                'Direct in-process latency excludes HTTP and server overhead; fresh cache per request.',
                'Model-native compressed caches differ from the previous 8192-token cache configuration.',
                'Reasoning effort names do not imply equal compute budgets across models.'],
            throughput=dict(trials=[]), modes={})

    def save(self):
        self.report['updatedAt'] = self.common.now()
        self.common.save(self.args.output, self.report)

    def generate(self, prompt, mode, cap):
        from omlx.patches.deepseek_v4.chat_template_v4 import apply_chat_template
        start = time.perf_counter()
        started_at = self.common.now()
        rendered = apply_chat_template([dict(role='user',content=prompt)],add_generation_prompt=True,
                                       thinking_mode=mode,reasoning_effort='low')
        expected_suffix = '<think>' if mode == 'thinking' else '</think>'
        assert rendered.endswith(expected_suffix)
        tokens = self.tokenizer.encode(rendered, add_special_tokens=False)
        self.mx.random.seed(42)
        self.mx.reset_peak_memory()
        chunks=[]; ids=[]; first=None; last=None; timed_out=False
        def timeout(signum, frame):
            raise TimeoutError('Request exceeded 300 seconds')
        old_handler = signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, 300)
        try:
            for response in self.stream_generate(self.model,self.tokenizer,tokens,max_tokens=cap,
                sampler=self.sampler,prefill_step_size=2048,kv_bits=None):
                if first is None: first=(time.perf_counter()-start)*1000
                chunks.append(response.text); ids.append(response.token); last=response
            self.mx.synchronize()
        except TimeoutError:
            timed_out=True
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,old_handler)
        if last is None: raise ValueError('No generated response')
        raw=''.join(chunks)
        return dict(startedAt=started_at,finishedAt=self.common.now(),prompt=prompt,renderedPrompt=rendered,templateOptions=dict(thinking_mode=mode,reasoning_effort='low'),
            outputCap=cap,rawText=raw,generatedTokenIds=ids,message=extract_answer(raw,mode),
            wallMs=(time.perf_counter()-start)*1000,timeToFirstYieldMs=first,promptTokens=last.prompt_tokens,
            promptTokPerSec=last.prompt_tps,generatedTokens=last.generation_tokens,genTokPerSec=last.generation_tps,
            peakMemoryGB=last.peak_memory,finishReason='timeout' if timed_out else last.finish_reason,
            truncated=timed_out or last.finish_reason=='length')

    def run(self):
        import mlx.core as mx
        from omlx.utils.model_loading import load_text_model
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler
        self.mx=mx; self.stream_generate=stream_generate
        self.sampler=make_sampler(temp=self.args.temperature,top_p=1,top_k=40 if self.args.temperature==0 else 0)
        self.report['metalDevice']=mx.device_info()
        self.save()
        try:
            start=time.perf_counter()
            self.model,self.tokenizer=load_text_model(self.spec['localPath'],tokenizer_config=dict(trust_remote_code=False,local_files_only=True))
            self.report['modelLoadMs']=(time.perf_counter()-start)*1000
            self.report['modelConfig']=json.loads((Path(self.spec['localPath'])/'config.json').read_text())
            import omlx.patches.deepseek_v4.chat_template_v4 as template
            self.report['templateSourceSha256']=self.common.sha(template.__file__)
            self.report['eosTokenIds']=sorted(self.tokenizer.eos_token_ids)
            from omlx.custom_kernels.glm_moe_dsa import fast
            self.report['nativeIndexerKernels']={name:fast.has_symbol(name) for name in ('dsa_indexer_scores','dsa_topk_indices')}
            print('LOADED',self.report['nativeIndexerKernels'],flush=True)
            self.report['warmup']=self.generate('Reply with exactly: ready','chat',128)
            self.save()
            if self.report['warmup']['message']['parseError']:raise ValueError('Warmup parsing failed')
            print('WARMUP',self.report['warmup']['genTokPerSec'],repr(self.report['warmup']['message']['content']),flush=True)
            for i in range(0 if self.args.skip_throughput else 3):
                short=self.generate('Write a 100 word description of the Rocky Mountains.','chat',512)
                filler='The quick brown fox jumps over the lazy dog. '*700
                ingest=self.generate(f'Trial {i+1}.\n{filler}\nReply with the single word: acknowledged.','chat',512)
                self.report['throughput']['trials'].append(dict(trial=i+1,short=short,ingest=ingest))
                self.save()
                print('THROUGHPUT',i+1,short['genTokPerSec'],ingest['promptTokPerSec'],flush=True)
            trials=self.report['throughput']['trials']
            self.report['throughput']['summary']=dict(
                medianGenTokPerSec=statistics.median(t['short']['genTokPerSec'] for t in trials),
                medianPromptTokPerSec=statistics.median(t['ingest']['promptTokPerSec'] for t in trials),
                anyTruncated=any(t[k]['truncated'] for t in trials for k in ('short','ingest'))) if trials else None
            for mode in self.args.modes:
                result=self.report['modes'][mode]=dict(cases=[],status='running')
                for row in self.cases:
                    response=self.generate(row['prompt'],mode,2048 if mode=='chat' else 8192)
                    passed=not response['truncated'] and not response['message']['parseError'] and self.grade(response['message']['content'],row['expected'])
                    result['cases'].append({**row,'response':response,'passed':passed})
                    self.save()
                    print('CASE',mode,len(result['cases']),'/24',row['id'],'PASS' if passed else 'FAIL',round(response['genTokPerSec'],2),flush=True)
                rows=result['cases']
                result['summary']=dict(passed=sum(r['passed'] for r in rows),attempted=len(rows),
                    medianGenTokPerSec=statistics.median(r['response']['genTokPerSec'] for r in rows),
                    medianWallMs=statistics.median(r['response']['wallMs'] for r in rows),
                    maxPeakMemoryGB=max(r['response']['peakMemoryGB'] for r in rows),
                    truncated=sum(r['response']['truncated'] for r in rows),
                    parseErrors=sum(bool(r['response']['message']['parseError']) for r in rows))
                result['status']='completed'; self.save()
            self.report['status']='completed'
        except Exception as exc:
            self.report.update(status='error',error=str(exc)); raise
        finally:
            if hasattr(self,'model'):del self.model
            gc.collect(); mx.clear_cache(); mx.synchronize()
            self.report['cleanup']=dict(activeMemoryBytesAfterModelRelease=mx.get_active_memory(),processExitRequired=True)
            self.report.update(hostAfter=self.common.host_snapshot(),finishedAt=self.common.now())
            self.save()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--modes',nargs='+',choices=('chat','thinking'),default=['chat','thinking'])
    parser.add_argument('--skip-throughput',action='store_true')
    parser.add_argument('--temperature',type=float,choices=(0,1),default=0)
    args=parser.parse_args()
    if args.worker: Replay(args).run()
    else: subprocess.run([sys.executable,__file__,*sys.argv[1:],'--worker'],check=True,timeout=3600)


if __name__=='__main__': main()
