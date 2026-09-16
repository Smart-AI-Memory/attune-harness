"""Disposable targeted task guards, retaining every test outcome and source hash."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
MUTANTS={
 'assignment-correlation':('review_participants.py',"if response['request_digest'] != request_digest:",'if False:', 'test_foreign_recovered_reply_does_not_mutate'),
 'completed-replay':('recovery.py',"if event['state'] == 'completed':",'if False:', 'test_each_boundary_replays_without_repeating_operations'),
 'source-freshness':('task_contract.py',"if actual != request['evidence']:",'if False:', 'test_sources_changed_by_peer_cannot_complete'),
 'output-budget':('task_policies.py',"if len(action['text'].encode('utf-8')) > self.task['request']['budgets']['max_output_bytes']:",'if False:', 'test_output_budget_and_external_permission'),
 'reviewer-isolation':('task_policies.py',"        turn['objective'] +=", "        turn['prior_narratives'] = self.task['execution']['participants']\n        turn['objective'] +=",'test_one_dispatch_per_isolated_assignment'),
}


def main(python,output):
 output.mkdir(parents=True,exist_ok=False)
 selection=' or '.join(v[3] for v in MUTANTS.values())
 tests=['tests/test_task_assessment.py','tests/test_task_recovery.py']
 def run(label,source):
  xml=output/(label+'.xml')
  cmd=[str(python),'-B','-m','pytest',*tests,'-k',selection,'-q','-p','no:cacheprovider','-o','pythonpath='+str(source),'--junitxml='+str(xml)]
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=60)
  (output/(label+'.txt')).write_text(p.stdout+'\n'+p.stderr)
  cases=ET.parse(xml).getroot().findall('.//testcase')
  errors=[c.attrib['name'] for c in cases if c.find('error') is not None]
  assert not errors,(label,errors)
  return {'label':label,'exit':p.returncode,'cases':len(cases),'failed':[c.attrib['name'] for c in cases if c.find('failure') is not None],'argv':cmd}
 baseline=run('control',ROOT/'src');assert baseline['exit']==0,baseline
 rows=[]
 for name,(filename,before,after,_) in MUTANTS.items():
  with tempfile.TemporaryDirectory(prefix='harness-task-mutation-') as t:
   src=Path(t)/'src';shutil.copytree(ROOT/'src/attune_harness',src/'attune_harness',ignore=shutil.ignore_patterns('__pycache__'))
   path=src/'attune_harness'/filename;original=path.read_text();assert before in original
   path.write_text(original.replace(before,after,1));row=run(name,src)
   assert row['exit']==1 and row['failed'],row
   rows.append(row)
 summary={'status':'passed','mutants_detected':len(rows),'mutants_tried':len(MUTANTS),'distinct_failing_cases':len(set(n for r in rows for n in r['failed'])),
          'control':baseline,'results':rows,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/attune_harness').glob('*.py')},'provider_calls':0}
 (output/'summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps({k:v for k,v in summary.items() if k not in ('control','results','source_hashes')}))


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--python',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();main(a.python.absolute(),a.output.absolute())
