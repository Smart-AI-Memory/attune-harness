"""Install the pinned pilot profiles and rerun the prior 110 installed cases."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main(wheel,output):
    output.mkdir(parents=True,exist_ok=False)
    calls=[]
    for item in json.loads((ROOT/'docs/receipts/phase6/compatible-dependencies.json').read_text()).values():
        assert hashlib.sha256((ROOT/item['wheel']).read_bytes()).hexdigest()==item['sha256'], 'Dependency archive changed'
    with zipfile.ZipFile(wheel) as archive:
        packaged={Path(name).name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith('attune_harness/') and name.endswith('.py')}
    assert packaged, 'Wheel contains no Harness modules'
    def invoke(args,label):
        result=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=180)
        (output/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr)
        calls.append({'argv':list(map(str,args)),'exit':result.returncode,'log':label+'.txt'})
        assert result.returncode==0,(label,result.stdout[-2000:],result.stderr[-2000:])
        return result.stdout
    interpreters={}
    for name,extra in [('core',''),('verify','[verify]'),('rag','[rag]'),('review','[review]'),('mcp','[mcp]')]:
        env=ROOT/('.venv-pilot-'+name);python=env/'bin/python';interpreters[name]=python
        if not python.exists():invoke([sys.executable,'-m','venv',env],'venv-'+name)
        invoke([python,'-m','pip','--isolated','install','--no-index','--find-links',ROOT/'dist/pilot-dependencies',
            '-c',ROOT/'requirements-workflow.lock','-c',ROOT/'requirements-mcp.lock',str(wheel)+extra],'install-'+name)
        invoke([python,'-m','pip','check'],'dependencies-'+name)
        identity=json.loads(invoke([python,'-I','-c','import json,hashlib,pathlib,attune_harness,importlib.metadata as m; print(json.dumps(dict(location=attune_harness.__file__,version=m.version("attune-harness"),sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(attune_harness.__file__).parent.glob("*.py")},packages={d.metadata["Name"]:d.version for d in m.distributions()})))'],'identity-'+name))
        assert identity['sources']==packaged and str(env) in identity['location'], 'Installed module bytes differ from the wheel'
    invoke([interpreters['review'],'-m','pip','--isolated','install','--no-index','--no-deps',
        ROOT/'dist/dependencies/attune_harness_evidence_example-0.1.0-py3-none-any.whl'],'install-extension')
    checks=[]
    for name,mode in [('core','core'),('verify','verify'),('rag','rag'),('review','all')]:
        checks.append(('check_installed.py',name,['--mode',mode],mode))
    checks += [('check_review_installed.py','core',['--core-only'],'review-core'),
        ('check_review_installed.py','review',[],'review'),('check_recovery_installed.py','review',[],'recovery'),
        ('check_extensions_installed.py','core',['--core'],'extensions-core'),
        ('check_extensions_installed.py','review',[],'extensions'),
        ('check_mcp_installed.py','mcp',['--legacy-python',ROOT/'.venv-mcp-check/bin/python'],'mcp'),
        ('check_a2a_installed.py','core',[],'a2a')]
    counts={}
    for script,profile,args,label in checks:
        report=output/(label+'.json')
        invoke([sys.executable,ROOT/'scripts'/script,'--python',interpreters[profile],*args,'--report',report],label)
        value=json.loads(report.read_text());counts[label]=len(value['cases'])
    assert sum(counts.values())==110,counts
    bridge=ROOT/'.venv-pilot-bridge';python=bridge/'bin/python'
    if not python.exists():invoke([sys.executable,'-m','venv','--system-site-packages',bridge],'venv-bridge')
    invoke([python,'-m','pip','--isolated','install','--no-index','--no-deps',wheel,ROOT/'dist/dependencies/attune_rag-1.2.0-py3-none-any.whl'],'install-bridge')
    invoke([python,'-I',ROOT/'scripts/check_attune_bridge.py','--report',output/'attune-bridge.json'],'attune-bridge')
    summary={'status':'passed','installed_cases':sum(counts.values()),'case_counts':counts,'wheel':str(wheel),
        'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'host':{'system':platform.system(),'release':platform.release(),
        'machine':platform.machine(),'macos':platform.mac_ver()[0],'python':platform.python_version()},'commands':calls,'paid_api_calls':0}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='commands'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();main(args.wheel.absolute(),args.output.absolute())
