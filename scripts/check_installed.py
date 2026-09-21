"""Exercise real CLI journeys against an installed wheel outside its source tree."""

import argparse
import importlib.metadata
import json
import subprocess
import tempfile
from pathlib import Path


def check(python: Path, mode: str) -> dict:
    cases = []
    with tempfile.TemporaryDirectory(prefix='harness-installed-') as tmp:
        root = Path(tmp)
        project = root/'project'
        project.mkdir()
        document = project/'guide.md'
        reference = project/'reference.md'
        reference.write_text('# Quartz retention policy\nA local source for audit retention.\n',encoding='utf-8')
        context = root/'context.json'
        context.write_text(json.dumps({'schema_version':1,'project_root':'project'}),encoding='utf-8')

        def run(arguments, expected, status):
            invocation = [str(python),'-I','-m','attune_harness',*arguments]
            result = subprocess.run(invocation,cwd=root,text=True,capture_output=True)
            assert result.returncode == expected, (result.stdout,result.stderr)
            payload = json.loads(result.stdout)
            assert payload['status'] == status,payload
            cases.append({'arguments':arguments,'exit':result.returncode,'status':status})
            return payload

        assert run([],0,'verified')['output']['text']=='4'
        absent = ['attune','anthropic','claude_agent_sdk','openai','model2vec','sentence_transformers']
        if mode=='core':
            absent += ['attune_verify','attune_rag']
        elif mode=='verify':
            absent += ['attune_rag']
        elif mode=='rag':
            absent += ['attune_verify']
        code = 'import importlib.util; assert all(importlib.util.find_spec(n) is None for n in '+repr(absent)+')'
        subprocess.run([str(python),'-I','-c',code],cwd=root,check=True)
        document.write_text('[reference](reference.md)',encoding='utf-8')
        args=['verify',str(document),'--context',str(context)]
        if mode in ('core','rag'):
            run(args,2,'unavailable')
        else:
            output=root/'report.json'
            valid=run(args+['--output',str(output)],0,'verified')
            assert valid==json.loads(output.read_text())
            assert valid['result']['claims'][0]['evidence']
            reference.unlink()
            run(args,1,'refuted')
            document.write_text('[remote](https://example.com)',encoding='utf-8')
            run(args,1,'unknown')
            document.write_text('Ordinary prose.',encoding='utf-8')
            assert run(args,1,'unknown')['result']['coverage']['total']==0
            original=context.read_bytes()
            run(args+['--output',str(context)],2,'failed')
            assert context.read_bytes()==original
            document.unlink()
            run(args,2,'failed')
        # Retrieval is independent of the verification extra.
        reference.write_text('# Quartz retention policy\nA local source for audit retention.\n',encoding='utf-8')
        retrieval=['retrieve','quartz retention policy','--corpus',str(project),'--k','1']
        if mode in ('core','verify'):
            run(retrieval,2,'unavailable')
        else:
            output=root/'retrieval.json'
            found=run(retrieval+['--output',str(output)],0,'retrieved')
            assert found==json.loads(output.read_text())
            assert found['sources'][0]['path']=='reference.md'
            assert found['sources'][0]['sha256']
            run(['retrieve','zyxw9876','--corpus',str(project)],1,'no_results')
            before=found['corpus']['version']
            reference.write_text('# Quartz retention policy\nChanged source.\n',encoding='utf-8')
            assert run(retrieval,0,'retrieved')['corpus']['version']!=before
        console=subprocess.run([str(python.parent/'attune-harness'),'--help'],cwd=root,text=True,capture_output=True)
        assert console.returncode==0 and all(
            command in console.stdout for command in ('plan', 'review', 'fix', '--help-all'))
        catalog=subprocess.run([str(python.parent/'attune-harness'),'--help-all'],cwd=root,text=True,capture_output=True)
        assert catalog.returncode==0 and all(
            command in catalog.stdout for command in ('verify', 'retrieve', 'memory'))
    return {'mode':mode,'cases':cases,'provider_dependencies_absent':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--mode',choices=['core','verify','rag','all'],required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    # Resolving the venv's Python symlink selects the base interpreter instead.
    result=check(args.python.absolute(),args.mode)
    payload=json.dumps(result,indent=2)+'\n'
    if args.report:
        args.report.write_text(payload,encoding='utf-8')
    print(payload)


if __name__=='__main__':
    main()
