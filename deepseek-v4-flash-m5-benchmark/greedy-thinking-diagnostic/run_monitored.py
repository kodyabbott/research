"""Run the remaining benchmark with a bounded, read-only macmon logger."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root=Path(__file__).resolve().parent
metrics=root/'thermal.jsonl'
output=root/'thinking-run.json'
if metrics.exists() or output.exists():
    raise SystemExit('Refusing to overwrite prior telemetry or benchmark results')
metadata=dict(startedAt=datetime.datetime.now().astimezone().isoformat(),
    intervalMs=1000, monitor=subprocess.check_output(['/opt/homebrew/bin/macmon','--version'],text=True).strip(),
    command=['macmon','pipe','-i','1000'],
    note='Read-only sensors. No fan control, stress mode, background service, or HTTP listener enabled.',
    scope='Resume: thinking mode only; previous chat and speed trials preserved separately.')
monitor=None; bench=None
def stop(sig,frame):
    raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
try:
    with metrics.open('x') as sensor_log, (root/'thermal-stderr.log').open('w') as err:
        monitor=subprocess.Popen(['/opt/homebrew/bin/macmon','pipe','-i','1000'],stdout=sensor_log,stderr=err)
        # Obtain a short baseline before loading the model.
        time.sleep(5)
        if monitor.poll() is not None:raise RuntimeError('Telemetry process exited before benchmark')
        env=dict(os.environ,HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')
        cmd=[str(root/'release-venv/bin/python'),str(root/'deepseek_replay.py'),
            '--repo','/Users/kody/repos/research','--selection',str(root/'verified.json'),
            '--output',str(output),'--modes','thinking','--skip-throughput','--worker']
        with (root/'thinking-benchmark.log').open('x') as log:
            bench=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
            metadata['benchmarkPid']=bench.pid
            metadata['benchmarkCommand']=cmd
            (root/'monitor-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
            code=bench.wait(timeout=3600)
            metadata['benchmarkExitCode']=code
            if code:raise RuntimeError(f'Benchmark exited {code}')
        time.sleep(5)
except BaseException as exc:
    metadata['error']=str(exc) or type(exc).__name__
    raise
finally:
    for proc in (bench,monitor):
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    metadata['finishedAt']=datetime.datetime.now().astimezone().isoformat()
    metadata['processesExited']=all(p is None or p.poll() is not None for p in (bench,monitor))
    (root/'monitor-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
