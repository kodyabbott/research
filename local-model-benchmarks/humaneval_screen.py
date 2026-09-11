"""Pinned HumanEval-X JavaScript continuation tasks in an isolated WASM guest."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import coding_screen

ROOT=Path(__file__).resolve().parent
DATA_SHA='1ffbb18b60d36c50c8a7d1230b7fbb82e5dd838d341242aab1caa2f8d7b598eb'
REVISION='62c78627f3072a1454fa0cb0184737cafe5e4198'
VERSION='humaneval-x-js-wasm-v1'
CHAT_VERSION='humaneval-x-js-wasm-chat-v2'
MISSING_CALLS={'JavaScript/32','JavaScript/119','JavaScript/151'}

def tasks(prompt_style="continuation"):
    raw=(ROOT/'fixtures/humaneval-x/javascript.jsonl').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DATA_SHA:raise ValueError('HumanEval-X dataset digest changed')
    result=[]
    for item in map(json.loads,raw.decode().splitlines()):
        if item['task_id']=='JavaScript/162':continue
        test=item['test']
        if item['task_id'] in MISSING_CALLS:test+='\n'+re.match(r'const (\w+) =',test).group(1)+'();\n'
        prompt=('Complete the following JavaScript code. Return ONLY the missing continuation, including the closing brace. '
            'Do not repeat the supplied code. Do not include Markdown, explanations, tests, or host APIs.\n\n'+item['prompt'])
        if prompt_style=='full-program':
            prompt=('Implement the unfinished JavaScript program below. Return the COMPLETE JavaScript program, including the function declaration and any helper functions shown. '
                'Fill in the unfinished body and close all braces. Return code only, without Markdown, explanations, tests, or host APIs.\n\n'+item['prompt'])
        elif prompt_style!='continuation':raise ValueError('Invalid prompt style')
        result.append({'id':item['task_id'],'prompt':prompt,'tests':[{'id':item['task_id'],'sourcePrompt':item['prompt'],'test':test,'assembly':prompt_style}]})
    return result

def evaluate(code,tests,timeout=30):
    if len(tests)!=1:raise ValueError('Expected one complete upstream test program')
    task=tests[0]
    payload={'tasks':[{'id':task['id'],'code':code if task.get('assembly')=='full-program' else task['sourcePrompt']+code,'test':task['test']}],'timeoutMs':2000}
    result=subprocess.run([shutil.which('node'),'--max-old-space-size=256',str(ROOT/'humaneval_sandbox_runner.cjs')],
        input=json.dumps(payload),capture_output=True,text=True,encoding='utf-8',timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('HumanEval-X sandbox failed: '+result.stderr[-1500:])
    rows=json.loads(result.stdout)['rows']
    if len(rows)!=1 or rows[0]['id']!=task['id']:raise RuntimeError('HumanEval-X result identity mismatch')
    return {'passed':int(rows[0]['passed']),'total':1,'rows':rows,'meaning':'Each check here is one whole upstream test program, not one console assertion.'}

def run(h,selection,**kwargs):
    style='full-program' if 'chat-v2' in selection.get('campaignProtocol','') else 'continuation'
    all_tasks=tasks(style);offset=selection.get('caseOffset',0);count=selection.get('caseCount',20)
    if type(offset)!=int or type(count)!=int or offset<0 or not 1<=count<=24 or offset+count>len(all_tasks):raise ValueError('Invalid HumanEval-X block')
    selected=all_tasks[offset:offset+count]
    suite_sha=hashlib.sha256(json.dumps(all_tasks,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return coding_screen.run(h,selection,benchmark={'tasks':selected,'evaluate':evaluate,'name':CHAT_VERSION if style=='full-program' else VERSION,'suiteSha256':suite_sha,
        'mode':'campaign-humanevalx-screen','scope':'Adapted HumanEval-X JavaScript screen; one greedy sample per task, not the original 200-sample leaderboard protocol.',
        'extraProtocol':{'promptStyle':style,'upstream':'https://huggingface.co/datasets/zai-org/humaneval-x','datasetRevision':REVISION,'datasetSha256':DATA_SHA,
            'supportedTasks':163,'upstreamTasks':164,'caseOffset':offset,'caseCount':count,
            'excludedTasks':{'JavaScript/162':'Reference requires the Node crypto module, unavailable in this WASM guest.'},
            'testInvocationRepairs':sorted(MISSING_CALLS),'randomSeed':42,'randomAlgorithm':'xorshift32','guestDeadlineMs':2000,
            'contaminationCaveat':'This longstanding public benchmark may be represented in model training data; scores do not establish unseen-task or repository-agent performance.'}},**kwargs)
