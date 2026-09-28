"""Regrade saved results, summarize telemetry, and draw the thermal time series."""
import datetime as dt
import argparse
import gzip
import json
from pathlib import Path
import statistics
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input-dir',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--output-dir',type=Path)
parser.add_argument('--repo',type=Path,default=Path.home()/'repos/research')
args=parser.parse_args()
root=args.input_dir
out=args.output_dir or root
out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(args.repo/'local-model-benchmarks'))
from quality_screen import grade

def load(name):return json.loads((root/name).read_text())
def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
def stamp(s):return dt.datetime.fromisoformat(s).timestamp()
def describe(values):
    values=[v for v in values if v is not None]
    return dict(min=min(values),median=statistics.median(values),max=max(values)) if values else None

def summarize_cases(rows):
    for row in rows:
        r=row['response']
        assert row['passed']==(not r['truncated'] and not r['message']['parseError'] and grade(r['message']['content'],row['expected']))
    categories={}
    for row in rows:
        d=categories.setdefault(row['category'],dict(passed=0,total=0))
        d['passed']+=int(row['passed']);d['total']+=1
    return dict(passed=sum(r['passed'] for r in rows),attempted=len(rows),
        generationTokPerSec=describe([r['response']['genTokPerSec'] for r in rows]),
        wallSeconds=describe([r['response']['wallMs']/1000 for r in rows]),
        outputTokens=describe([r['response']['generatedTokens'] for r in rows]),
        truncated=sum(r['response']['truncated'] for r in rows),
        parseErrors=sum(bool(r['response']['message']['parseError']) for r in rows),categories=categories)

old=load('chat-and-speed-run.json' if (root/'chat-and-speed-run.json').exists() else 'run.json')
new=load('thinking-run.json')
thermal_text=(root/'thermal.jsonl').read_text() if (root/'thermal.jsonl').exists() else gzip.decompress((root/'thermal.jsonl.gz').read_bytes()).decode()
thermal=[json.loads(line) for line in thermal_text.splitlines() if line.strip()]
summary=dict(chat=summarize_cases(old['modes']['chat']['cases']),
    thinking=summarize_cases(new['modes'].get('thinking',{}).get('cases',[])),
    thinkingStatus=new['status'],throughput=old['throughput']['summary'])
summary['protocols']=dict(chat=old['protocol'],thinking=new['protocol'])
summary['thermal']=dict(samples=len(thermal),firstTimestamp=thermal[0]['timestamp'],lastTimestamp=thermal[-1]['timestamp'],
    cpuAverageC=describe([r['temp']['cpu_temp_avg'] for r in thermal]),
    gpuAverageC=describe([r['temp']['gpu_temp_avg'] for r in thermal]),
    gpuClockMHz=describe([r['gpu_freq_mhz'] for r in thermal]),
    gpuPowerWatts=describe([r['gpu_power'] for r in thermal]),
    systemRamGiB=describe([r['memory']['ram_usage']/2**30 for r in thermal]),
    swapBytes=describe([r['memory']['swap_usage'] for r in thermal]),
    fans={name:describe([f['rpm'] for r in thermal for f in r['fans'] if f['name']==name]) for name in ('fan0','fan1')},
    limits='macmon average sensor estimates, not hottest die or calibrated external measurements. Whole-monitor window includes baseline, model loading, warmup and cleanup. One-second sampling; response timestamps rounded to seconds.')
summary['perCaseThermal']=[]
for case in new['modes'].get('thinking',{}).get('cases',[]):
    r=case['response'];start=stamp(r['startedAt']);end=stamp(r['finishedAt'])
    subset=[t for t in thermal if start<=stamp(t['timestamp'])<=end]
    summary['perCaseThermal'].append(dict(id=case['id'],startedAt=r['startedAt'],finishedAt=r['finishedAt'],
        samples=len(subset),generationTokPerSec=r['genTokPerSec'],
        gpuAverageC=describe([t['temp']['gpu_temp_avg'] for t in subset]),
        gpuClockMHz=describe([t['gpu_freq_mhz'] for t in subset]),
        fanRPM={name:describe([f['rpm'] for t in subset for f in t['fans'] if f['name']==name]) for name in ('fan0','fan1')}))
save('summary.json',summary)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
first=stamp(thermal[0]['timestamp'])
x=[(stamp(t['timestamp'])-first)/60 for t in thermal]
fig,axes=plt.subplots(4,1,figsize=(11,10),sharex=True,layout='constrained')
for key,label,color in [('cpu_temp_avg','CPU average','#2563eb'),('gpu_temp_avg','GPU average','#dc2626')]:
    axes[0].plot(x,[r['temp'][key] for r in thermal],label=label,color=color,linewidth=1.3)
axes[0].set_ylabel('Temperature (°C)');axes[0].legend(loc='upper right',ncol=2)
for name,color in [('fan0','#059669'),('fan1','#7c3aed')]:
    axes[1].plot(x,[next((f['rpm'] for f in r['fans'] if f['name']==name),float('nan')) for r in thermal],label=name,color=color,linewidth=1.3)
axes[1].set_ylabel('Fan speed (RPM)');axes[1].set_ylim(bottom=0);axes[1].legend(loc='upper right',ncol=2)
axes[2].plot(x,[r['gpu_freq_mhz'] for r in thermal],color='#475569',linewidth=1.1)
axes[2].set_ylabel('GPU clock (MHz)');axes[2].set_ylim(bottom=0)
for case in new['modes'].get('thinking',{}).get('cases',[]):
    r=case['response'];pos=(stamp(r['finishedAt'])-first)/60
    axes[3].scatter([pos],[r['genTokPerSec']],color='#ea580c' if r['truncated'] else '#2563eb',marker='x' if r['truncated'] else 'o',s=28)
axes[3].set_ylabel('Generation (tok/s)')
rates=[c['response']['genTokPerSec'] for c in new['modes'].get('thinking',{}).get('cases',[])]
axes[3].set_ylim(0,max(45,max(rates,default=0)*1.15))
axes[3].set_xlabel('Minutes since telemetry began (includes loading and warmup)')
for ax in axes:ax.grid(alpha=.18)
fig.suptitle('DeepSeek V4 Flash on M5 Max — thinking mode, temperature 1.0\nTemperature and fan telemetry, sampled every second',fontsize=14,fontweight='bold')
fig.text(.5,-.017,'Temperature = macmon CPU/GPU sensor averages. Decode points = completed cases; orange × = output cap reached.',ha='center',fontsize=9)
fig.savefig(out/'thermal-chart.png',dpi=155,bbox_inches='tight')
plt.close(fig)
print(json.dumps(summary,indent=2))
