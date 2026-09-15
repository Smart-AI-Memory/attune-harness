"""Targeted guard-removal checks on disposable source copies; no models."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
MUTANTS={
 'omit-catalog-budget':('native.py',"argv += ['-c', 'skills.max_context_tokens=' + str(self.skills_context_tokens)]",'pass'),
 'skip-registry-budget-validation':('review_contract.py',"validate_skills_context_tokens(item['skills_context_tokens'])",'pass'),
 'omit-registry-acceptance-binding':('review_contract.py',"{'form': definition, 'registry': registry}","{'form': definition}"),
 'skip-duplicate-triage':('operations.py',"elif key in handled_keys:","elif False:"),
 'ignore-quality-floor':('operations.py',"eligible = [r for r in summary if r['quality_passed'] and r['cost_complete']]", "eligible = [r for r in summary if r['cost_complete']]"),
 'drop-failed-costs':('operations.py',"total = None if missing else sum(r['model_cost_usd'] + r['verification_cost_usd'] +", "rows = [r for r in rows if r['outcome'] == 'verified']\n        total = None if missing else sum(r['model_cost_usd'] + r['verification_cost_usd'] +"),
 'ignore-github-revision':('github_checks.py',"if not isinstance(run,dict) or run.get('head_sha')!=revision:","if not isinstance(run,dict):"),
}


def main(python,out):
    out.mkdir(parents=True,exist_ok=False)
    def run(label,source):
        path=out/(label+'.xml')
        r=subprocess.run([str(python),'-m','pytest','-q','-o','pythonpath='+str(source),
            '--junitxml='+str(path),*[str(ROOT/'tests'/t) for t in
            ['test_focused_native.py','test_operations.py','test_github_checks.py']]],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',timeout=60)
        (out/(label+'.txt')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        cases=ET.parse(path).getroot().findall('.//testcase')
        assert cases and not any(c.find('error') is not None for c in cases)
        return {'name':label,'exit':r.returncode,'cases':len(cases),
                'failed':[c.attrib['name'] for c in cases if c.find('failure') is not None]}
    baseline=run('baseline',ROOT/'src');assert baseline['exit']==0
    results=[]
    for name,(filename,before,after) in MUTANTS.items():
        with tempfile.TemporaryDirectory(prefix='harness-opportunity-mutation-') as tmp:
            source=Path(tmp)/'src'
            shutil.copytree(ROOT/'src/attune_harness',source/'attune_harness',ignore=shutil.ignore_patterns('__pycache__'))
            path=source/'attune_harness'/filename;text=path.read_text(encoding='utf-8')
            assert before in text
            path.write_text(text.replace(before,after),encoding='utf-8')
            r=run(name,source);assert r['exit']==1 and r['failed'],r;results.append(r)
    summary={'mutants_detected':len(results),'mutants_tried':len(MUTANTS),'tests':baseline['cases'],
             'tests_detecting_mutations':len({t for r in results for t in r['failed']}),'results':results}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--python',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.python.absolute(),a.output.absolute())
