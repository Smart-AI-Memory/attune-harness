"""Demonstrate isolated package rollback, old-path operation and restoration."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def snapshot(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def main(python,pilot,output):
    output.mkdir(parents=True,exist_ok=False)
    original=snapshot(pilot);calls=[]
    def invoke(args,label,code=0):
        result=subprocess.run(list(map(str,args)),cwd=output,capture_output=True,text=True,timeout=120)
        entry={'argv':list(map(str,args)),'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        (output/(label+'.json')).write_text(json.dumps(entry,indent=2)+'\n');calls.append(entry)
        assert result.returncode==code,(label,result.stdout[-2000:],result.stderr[-2000:])
        return result.stdout
    def install(version,label):
        return invoke([python,'-m','pip','--isolated','install','--no-index','--no-deps','--force-reinstall',
                       ROOT/f'dist/attune_harness-{version}-py3-none-any.whl'],label)
    def cli(args,label,code=0):
        return json.loads(invoke([python,'-I','-m','attune_harness',*args],label,code))
    install('0.1.0.dev0','rollback-install')
    try:
        invoke([python,'-m','pip','check'],'rollback-dependencies')
        version=invoke([python,'-I','-c','from importlib.metadata import version; print(version("attune-harness"))'],'rollback-version').strip()
        assert version=='0.1.0.dev0'
        historical=cli(['inspect-review',pilot/'review'],'old-inspects-new',1)
        assert historical==json.loads((pilot/'review/record.json').read_text())
        config,request=output/'participants.json',output/'request.json'
        registry={'schema_version':1,'participants':{n:{'adapter':'deterministic','tools':['retrieve','verify'],
            'max_turns':3,'max_tool_calls':2} for n in ('lead','reviewer')}}
        config.write_text(json.dumps(registry)+'\n')
        submission=cli(['review-form','--config',config],'old-form')['submission']
        answers=json.loads((pilot/'request.json').read_text())['answers']
        submission.update(accepted=True,answers={**answers,'lead':'lead','reviewer':'reviewer'})
        request.write_text(json.dumps(submission)+'\n')
        review=cli(['review',request,'--config',config,'--run-dir',output/'old-review'],'old-review',1)
        assert review['status']=='completed' and review['document_outcome']=='unknown'
        assert review['verification']['result']['coverage']==historical['verification']['result']['coverage']
    finally:
        install('0.1.0.dev3','restore-install')
    restored=cli(['inspect-review',pilot/'review'],'restored-inspects-original',1)
    assert restored==historical and snapshot(pilot)==original
    invoke([python,'-I','-m','attune_harness.ollama_review','--help'],'restored-peer-help')
    invoke([python,'-m','pip','check'],'restored-dependencies')
    result={'status':'passed','rollback_version':'0.1.0.dev0','restored_version':'0.1.0.dev3',
        'original_pilot_files_unchanged':len(original),'old_path_review_completed':True,
        'coverage_preserved':True,'model_calls':0,'paid_api_calls':0,'commands':len(calls)}
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--pilot-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();main(args.python.absolute(),args.pilot_dir.absolute(),args.output.absolute())
