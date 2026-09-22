"""Native MLX comparison using the saved practical-json-v1 cases.

This is a separately labeled runtime/quantization experiment, not an exact GGUF
reproduction. Run with the pinned MLX environment documented in notes.md.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import signal
import statistics
import subprocess
import sys
import time


def extract_answer(raw, is_gpt_oss):
    if not is_gpt_oss:
        return {'content': raw, 'thinking': '', 'parseError': None,
                'unexpectedThinking': '<think>' in raw or '</think>' in raw}
    marker = re.compile(r'(?:<\|start\|>assistant)?<\|channel\|>final<\|message\|>|(?:<\|im_start\|>assistant)?<\|meta_sep\|>final<\|im_sep\|>')
    matches = list(marker.finditer(raw))
    if len(matches) != 1:
        return {'content': '', 'thinking': raw, 'parseError': 'Expected exactly one Harmony final channel', 'unexpectedThinking': False}
    match = matches[0]
    final = raw[match.end():]
    # EOS is normally excluded by stream_generate; remove only protocol trailers.
    final = re.sub(r'(?:<\|fim_suffix\|>|<\|im_end\|>|<\|return\|>|<\|end\|>)$', '', final)
    return {'content': final, 'thinking': raw[:match.start()], 'parseError': None, 'unexpectedThinking': False}


class NativeReplay:
    def __init__(self, args):
        self.args = args
        sys.path.insert(0, str(args.repo / 'mac-model-benchmarks'))
        import mac_replay
        self.common = mac_replay
        sys.path.insert(0, str(args.repo / 'local-model-benchmarks'))
        import quality_screen, workload_suite
        self.grade = quality_screen.grade
        self.cases = workload_suite.cases()[:24]
        self.spec = json.loads(args.selection.read_text())
        assert self.spec['verified']
        self.is_gpt = 'gpt-oss' in self.spec['repoId']
        self.key = 'gpt-oss:20b' if self.is_gpt else 'qwen3-coder:30b'
        self.cap = 8192 if self.is_gpt else 2048
        reference = args.repo/'local-model-benchmarks/runs'/mac_replay.REFERENCES[self.key]
        self.previous = json.loads(reference.read_text())
        old = next(b for b in self.previous['benchmarks'] if b['model'] == self.key)
        assert self.cases == [{k:r[k] for k in ('id','category','prompt','expected')} for r in old['cases']]
        self.path = args.output
        if self.path.exists(): raise ValueError('Refusing to overwrite raw results')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.report = {'schemaVersion':1,'runtimeKind':'mlx-lm','model':self.spec['repoId'], 'modelKey':self.key,
            'startedAt':mac_replay.now(),'status':'running','artifact':self.spec,
            'runtime':{name:importlib.metadata.version(name) for name in ('mlx','mlx-lm','transformers','tokenizers')},
            'python':sys.version,'runnerSha256':mac_replay.sha(__file__),
            'hostBefore':mac_replay.host_snapshot(),'cases':[],
            'protocol':{**self.previous['protocol'],'variant':'native-mlx-direct-v1',
                'prefillStepSize':args.prefill_step_size,'maxKvSize':8192,'kvCacheQuantization':None,'crossRequestPromptCache':False,
                'temperature':0,'seed':42,'top_p':1,'top_k':40,'repeatPenalty':1.0},
            'reference':{'file':str(reference.relative_to(args.repo)),'sha256':mac_replay.sha(reference),'summary':old['summary']},
            'comparisonLimits':['Different weight conversion and quantization from GGUF; do not attribute differences solely to the runtime.',
                'Native model chat template, direct in-process latency, fresh KV cache per request; Ollama includes HTTP/client overhead and may reuse prefixes.',
                'KV cache limited to 8192 with MLX rotating-cache semantics; not a guarantee of identical Ollama context-management behavior.'],
            'generatedCodeExecution':'disabled'}

    def save(self):
        self.report['updatedAt']=self.common.now()
        self.common.save(self.path,self.report)

    def generate(self, prompt, cap):
        mx=self.mx
        start=time.perf_counter()
        kwargs={'reasoning_effort':'low'} if self.is_gpt else {'enable_thinking':False}
        rendered=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True,**kwargs)
        tokens=self.tokenizer.encode(rendered,add_special_tokens=False)
        if len(tokens)>=8192:raise ValueError('Prompt exceeds the declared cache capacity')
        mx.random.seed(42)
        chunks=[];ids=[];first=None;last=None
        def timed_out(signum,frame):raise TimeoutError('Native request exceeded 120 seconds')
        previous_handler=signal.signal(signal.SIGALRM,timed_out)
        signal.setitimer(signal.ITIMER_REAL,120)
        try:
            for response in self.stream_generate(self.model,self.tokenizer,tokens,max_tokens=cap,
                sampler=self.sampler,max_kv_size=8192,prefill_step_size=self.args.prefill_step_size,kv_bits=None):
                if first is None:first=(time.perf_counter()-start)*1000
                chunks.append(response.text);ids.append(response.token);last=response
            mx.synchronize()
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,previous_handler)
        wall=(time.perf_counter()-start)*1000
        raw=''.join(chunks)
        answer=extract_answer(raw,self.is_gpt)
        return {'prompt':prompt,'renderedPrompt':rendered,'templateOptions':kwargs,'outputCap':cap,
            'rawText':raw,'generatedTokenIds':ids,'message':answer,
            'wallMs':wall,'timeToFirstYieldMs':first,'promptTokens':last.prompt_tokens,
            'promptTokPerSec':last.prompt_tps,'generatedTokens':last.generation_tokens,
            'genTokPerSec':last.generation_tps,'peakMemoryGB':last.peak_memory,
            'finishReason':last.finish_reason,'truncated':last.finish_reason=='length',
            'contextBudgetExceeded':last.prompt_tokens+last.generation_tokens>8192}

    def run(self):
        import mlx.core as mx
        from mlx_lm import load,stream_generate
        from mlx_lm.sample_utils import make_sampler
        self.mx=mx;self.stream_generate=stream_generate
        self.sampler=make_sampler(temp=0,top_p=1,top_k=40)
        self.report['metalDevice']=mx.device_info()
        self.save()
        try:
            start=time.perf_counter()
            self.model,self.tokenizer,config=load(self.spec['localPath'],return_config=True,
                tokenizer_config={'trust_remote_code':False,'local_files_only':True})
            self.report['modelLoadMs']=(time.perf_counter()-start)*1000
            self.report['modelConfig']=config
            self.report['chatTemplate']=self.tokenizer.chat_template
            self.report['chatTemplateSha256']=hashlib.sha256(str(self.tokenizer.chat_template).encode()).hexdigest()
            self.report['eosTokenIds']=sorted(self.tokenizer.eos_token_ids)
            self.report['warmup']=self.generate('Reply with exactly: ready',512)
            if self.report['warmup']['message']['parseError']:
                raise ValueError('Warmup channel parsing failed: '+self.report['warmup']['message']['parseError'])
            if not self.is_gpt:
                self.report['throughput']={'trials':[]}
                for i in range(3):
                    short=self.generate('Write a 100 word description of the Rocky Mountains.',512)
                    filler='The quick brown fox jumps over the lazy dog. '*700
                    ingest=self.generate(f'Trial {i+1}.\n{filler}\nReply with the single word: acknowledged.',512)
                    self.report['throughput']['trials'].append({'trial':i+1,'short':short,'ingest':ingest})
                    self.save()
                t=self.report['throughput']['trials']
                self.report['throughput']['summary']={'medianGenTokPerSec':statistics.median(x['short']['genTokPerSec'] for x in t),
                    'medianPromptTokPerSec':statistics.median(x['ingest']['promptTokPerSec'] for x in t),
                    'medianWallMs':statistics.median(x['short']['wallMs'] for x in t),
                    'anyTruncated':any(x[k]['truncated'] for x in t for k in ('short','ingest'))}
            for row in self.cases:
                response=self.generate(row['prompt'],self.cap)
                passed=not response['truncated'] and not response['message']['parseError'] and self.grade(response['message']['content'],row['expected'])
                self.report['cases'].append({**row,'response':response,'passed':passed})
                self.save()
                print(self.key,len(self.report['cases']),'/24',flush=True)
            rows=self.report['cases']
            self.report['summary']={'passed':sum(x['passed'] for x in rows),'attempted':len(rows),
                'medianWallMs':statistics.median(x['response']['wallMs'] for x in rows),
                'medianGenTokPerSec':statistics.median(x['response']['genTokPerSec'] for x in rows),
                'truncated':sum(x['response']['truncated'] for x in rows),
                'channelParseErrors':sum(bool(x['response']['message']['parseError']) for x in rows),
                'unexpectedThinking':any(x['response']['message']['unexpectedThinking'] for x in rows),
                'contextBudgetExceeded':sum(x['response']['contextBudgetExceeded'] for x in rows),
                'maxPeakMemoryGB':max(x['response']['peakMemoryGB'] for x in rows)}
            self.report['status']='completed'
        except Exception as exc:
            self.report.update(status='error',error=str(exc))
            raise
        finally:
            if hasattr(self,'model'):del self.model
            gc.collect();mx.clear_cache();mx.synchronize()
            self.report['cleanup']={'activeMemoryBytesAfterModelRelease':mx.get_active_memory(),
                'processExitRequired':True}
            self.report.update(hostAfter=self.common.host_snapshot(),finishedAt=self.common.now())
            self.save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True);p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--worker',action='store_true')
    p.add_argument('--prefill-step-size',type=int,choices=(2048,4096,8192),default=2048)
    a=p.parse_args()
    if a.worker:NativeReplay(a).run()
    else:
        # Hard per-model process deadline, independent of native-call signal handling.
        subprocess.run([sys.executable,__file__,*sys.argv[1:],'--worker'],check=True,timeout=1800)


if __name__=='__main__':main()
