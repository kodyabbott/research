"""Regression checks using the actual saved model responses."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from deepseek_replay import extract_answer

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--results',type=Path,required=True)
parser.add_argument('--repo',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.repo/'local-model-benchmarks'))
from quality_screen import grade
results=json.loads(args.results.read_text())
cases=results['modes']['thinking']['cases']
ledger=next(c for c in cases if c['id']=='ledger-0')
assert grade(extract_answer(ledger['response']['rawText'],'thinking')['content'],ledger['expected'])
sql=next(c for c in cases if c['id']=='sql-0')
assert sql['response']['rawText'].count('</think>')==2
assert extract_answer(sql['response']['rawText'],'thinking')['parseError']
# Last-answer salvage would silently accept this contradictory protocol output.
assert grade(sql['response']['rawText'].rsplit('</think>',1)[-1],sql['expected'])
sql2=next(c for c in cases if c['id']=='sql-2')
assert not extract_answer(sql2['response']['rawText'],'thinking')['parseError']
assert not grade(sql2['response']['message']['content'],sql2['expected'])
assert extract_answer('unfinished reasoning without a final channel','thinking')['parseError']
for case in cases:
    r=case['response'];answer=extract_answer(r['rawText'],'thinking')
    assert answer==r['message']
    passed=not r['truncated'] and not answer['parseError'] and grade(answer['content'],case['expected'])
    assert passed==case['passed'],case['id']
assert results['runnerSha256']==hashlib.sha256(Path(__file__).with_name('deepseek_replay.py').read_bytes()).hexdigest()
print(f'Observed-output regression checks and {len(cases)} case regrades passed')
