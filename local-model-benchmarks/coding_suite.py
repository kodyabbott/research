"""Eight authored JavaScript tasks with deterministic held-out functional tests."""
import csv
import hashlib
import io
import json
import random

VERSION='javascript-functions-v1'

def tasks():
    result=[]
    def add(name,spec,tests,reference):
        prompt='Write a synchronous JavaScript ES2020 function solve(input). Do not mutate input. Use no external libraries or host APIs. Return JavaScript code only; no explanation.\n'+spec
        result.append({'id':name,'prompt':prompt,'tests':[{'id':str(i),'input':x,'expected':y} for i,(x,y) in enumerate(tests)],'reference':reference})
    rng=random.Random(55113)
    tests=[]
    for n in [0,1,2,4,8,16,32,48,64,96,128,160]:
        events=[{'eventId':str(i),'account':rng.choice(['a','b','c','__proto__','constructor']),'delta':rng.randrange(-50,51)} for i in range(n)]
        events += [x.copy() for x in events[:n//3]];rng.shuffle(events);seen=set();totals={}
        for e in events:
            if e['eventId'] not in seen:seen.add(e['eventId']);totals[e['account']]=totals.get(e['account'],0)+e['delta']
        tests.append((events,[[k,v] for k,v in sorted(totals.items())]))
    add('deduplicated-ledger','Input is an array of {eventId, account, delta}. Duplicate eventId records are identical duplicate deliveries; count each eventId once. Sum integer delta per account. Return [[account,balance],...] sorted by account using ordinary lexicographic string order. Accounts can be any strings, including object prototype names.',tests,
        'function solve(input){const seen=new Set(),totals=new Map();for(const e of input){if(seen.has(e.eventId))continue;seen.add(e.eventId);totals.set(e.account,(totals.get(e.account)||0)+e.delta)}return [...totals].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0)}')
    tests=[]
    for n in [0,1,2,4,8,16,24,32,48,64,96,128]:
        events=[];state={}
        for i in range(n):
            k=rng.choice(['a','b','c','__proto__','constructor']);e={'key':k,'version':i,'op':rng.choice(['set','set','delete']),'value':rng.choice([None,False,0,'x',17])};events.append(e);state[k]=e
        rng.shuffle(events);expected={k:e['value'] for k,e in state.items() if e['op']=='set'};tests.append((events,expected))
    add('versioned-state','Input is an array of {key,version,op,value}, arriving out of order. Versions are unique nonnegative integers. For each key choose the greatest version. op="delete" removes that key; op="set" sets its value, including null/false/0. Return a JSON-compatible object of final keys to values. Keys may include __proto__ or constructor.',tests,
        'function solve(input){const m=new Map();for(const e of input)if(!m.has(e.key)||m.get(e.key).version<e.version)m.set(e.key,e);return Object.fromEntries([...m].filter(([k,e])=>e.op==="set").map(([k,e])=>[k,e.value]))}')
    tests=[([],[]),([[1,1]],[[1,1]]),([[2,4],[1,2]],[[1,4]])]
    for n in [2,3,5,8,12,20,32,50,100]:
        intervals=[]
        for _ in range(n):a=rng.randrange(-100,101);intervals.append([a,a+rng.randrange(20)])
        merged=[]
        for a,b in sorted(intervals):
            if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
            else:merged.append([a,b])
        tests.append((intervals,merged))
    add('merge-intervals','Input is an array of closed integer intervals [start,end], with start<=end. Merge intervals that overlap or touch, and return intervals sorted by start then end. Preserve the original input and its inner arrays. Example [[7,9],[1,4],[4,6]] -> [[1,6],[7,9]].',tests,
        'function solve(input){const out=[];for(const [a,b] of input.map(x=>x.slice()).sort((a,b)=>a[0]-b[0]||a[1]-b[1])){const p=out[out.length-1];if(p&&a<=p[1])p[1]=Math.max(p[1],b);else out.push([a,b])}return out}')
    tests=[]
    for n in range(12):
        nodes=[chr(97+i) for i in range(n)];edges=[]
        for a in nodes:
            for b in nodes:
                if a!=b and rng.random()<0.1:edges.append([a,b])
        if edges:edges.append(edges[0][:])
        pending=set(nodes);order=[];unique={tuple(e) for e in edges}
        while pending:
            ready=sorted(x for x in pending if not any(v==x and u in pending for u,v in unique))
            if not ready:break
            order.append(ready[0]);pending.remove(ready[0])
        tests.append(({'nodes':nodes,'edges':edges},None if pending else order))
    tests.append(({'nodes':['a'],'edges':[['a','a']]},None))
    add('topological-order','Input is {nodes,edges}. nodes is an array of unique strings; every edge [u,v] means u must precede v, and both nodes exist. Ignore duplicate edges. Return a topological order, always choosing the lexicographically smallest currently available node. Return null if any cycle exists, including a self-loop.',tests,
        'function solve(input){const pending=new Set(input.nodes),out=[];while(pending.size){const ready=[...pending].filter(x=>!input.edges.some(([u,v])=>v===x&&pending.has(u))).sort();if(!ready.length)return null;out.push(ready[0]);pending.delete(ready[0])}return out}')
    tests=[]
    for n in [0,1,2,4,8,16,24,32,48,64,96,128]:
        events=[];clock=0;cache={};answers=[]
        for i in range(n):
            clock+=rng.randrange(3);key=rng.choice(['a','b','__proto__']);op=rng.choice(['put','get','get','delete'])
            e={'t':clock,'op':op,'key':key}
            if op=='put':e.update(value=rng.choice([None,False,0,'v',17]),ttl=rng.randrange(6));cache[key]=(e['value'],clock+e['ttl'])
            elif op=='delete':cache.pop(key,None)
            else:answers.append(cache[key][0] if key in cache and clock<cache[key][1] else None)
            events.append(e)
        tests.append((events,answers))
    add('ttl-cache','Simulate a cache from operations in input order. Timestamps t are nondecreasing integers. put has {t,op:"put",key,value,ttl}; it replaces a key and expires exactly at t+ttl, so ttl=0 expires immediately. get has {t,op:"get",key} and returns the current value or null if absent/expired. delete removes a key. Return an array of get results only. Same-timestamp operations obey input order.',tests,
        'function solve(input){const cache=new Map(),out=[];for(const e of input){if(e.op==="put")cache.set(e.key,[e.value,e.t+e.ttl]);else if(e.op==="delete")cache.delete(e.key);else {const x=cache.get(e.key);out.push(x&&e.t<x[1]?x[0]:null)}}return out}')
    obj={'a':[0,None,{'x/y':False,'m~n':'ok'}],'':{'__proto__':7},'constructor':'data','01':'object key'}
    tests=[]
    for pointer in ['', '/a','/a/0','/a/1','/a/2/x~1y','/a/2/m~0n','//__proto__','/constructor','/01','/a/01','/a/-','/missing','/a/5','/a/1/x']:
        cur=obj;found=True
        for part in ([] if pointer=='' else pointer[1:].split('/')):
            part=part.replace('~1','/').replace('~0','~')
            if isinstance(cur,dict) and part in cur:cur=cur[part]
            elif isinstance(cur,list) and part.isdigit() and str(int(part))==part and int(part)<len(cur):cur=cur[int(part)]
            else:found=False;break
        tests.append(({'document':obj,'pointer':pointer},{'found':True,'value':cur} if found else {'found':False}))
    add('json-pointer','Input is {document,pointer}. Resolve a JSON Pointer: empty pointer selects the whole document; otherwise split after the leading slash, decode ~1 to / then ~0 to ~. Use only own object properties. Array indexes must be canonical nonnegative decimal integers (0 valid; 01 and - invalid). Return {found:true,value:...} if found, otherwise {found:false}. Null is a real found value.',tests,
        'function solve(input){let x=input.document;for(const raw of input.pointer===""?[]:input.pointer.slice(1).split("/")){const k=raw.replace(/~1/g,"/").replace(/~0/g,"~");if(Array.isArray(x)){if(!/^(0|[1-9][0-9]*)$/.test(k)||Number(k)>=x.length)return {found:false};x=x[Number(k)]}else if(x!==null&&typeof x==="object"&&Object.prototype.hasOwnProperty.call(x,k))x=x[k];else return {found:false}}return {found:true,value:x}}')
    tests=[('',[]),('\n',[['']]),('a,b',[['a','b']]),('""',[['']])]
    for n in [1,2,3,4,5,8,12,16]:
        rows=[[rng.choice(['a','b,c','"quoted"','line\nbreak','','x\r\ny','0']) for _ in range(rng.randrange(1,5))] for _ in range(n)]
        stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\r\n').writerows(rows);text=stream.getvalue()
        tests.append((text,rows))
    add('csv-parser','Input is a valid CSV string. Return an array of rows (arrays of strings). Handle commas, quoted fields, doubled quote escapes, newlines inside quoted fields, and LF or CRLF row endings. Preserve embedded newlines inside quotes. Empty input returns []; a final row terminator must not create an extra row. An empty line is one empty field.',tests,
        'function solve(input){if(input==="")return [];const rows=[];let row=[],field="",quoted=false;for(let i=0;i<input.length;i++){let c=input[i];if(quoted){if(c===\'"\'){if(input[i+1]===\'"\'){field+=\'"\';i++}else quoted=false}else field+=c}else if(c===\'"\')quoted=true;else if(c===","){row.push(field);field=""}else if(c==="\\n"||c==="\\r"){if(c==="\\r"&&input[i+1]==="\\n")i++;row.push(field);rows.push(row);row=[];field=""}else field+=c}if(field!==""||row.length||!/[\\r\\n]$/.test(input)){row.push(field);rows.push(row)}return rows}')
    tests=[]
    def redact(x):
        if isinstance(x,list):return [redact(v) for v in x]
        if isinstance(x,dict):return {k:'[REDACTED]' if k.lower() in ('password','token','secret') else redact(v) for k,v in x.items()}
        return x
    for value in [None,0,False,'text',[],{}, {'password':0,'safe':False}, {'Token':None,'SECRET':{'a':1}}, {'nested':[{'password':'x'},{'ok':['secret',None]}]}, {'__proto__':{'token':'x'},'constructor':7}, [{'safe':1},{'token':False}], {'passwordHint':'keep','secrets':'keep','secret':'hide'}]:tests.append((value,redact(value)))
    add('recursive-redaction','Return a deep copy of a JSON-compatible input value. In every object, replace values of keys equal to password, token, or secret (case-insensitive) with "[REDACTED]". Recursively process all other values, including objects inside arrays. Preserve every key (including __proto__), array order, null, and primitive values. Do not mutate input.',tests,
        'function solve(input){if(Array.isArray(input))return input.map(solve);if(input!==null&&typeof input==="object")return Object.fromEntries(Object.entries(input).map(([k,v])=>[k,["password","token","secret"].includes(k.toLowerCase())?"[REDACTED]":solve(v)]));return input}')
    return result

def digest(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
