"""Rebuild pinned dependency wheels from local Git objects, without checkout edits."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repos-root',type=Path,default=root.parent)
    parser.add_argument('--output',type=Path,default=root/'dist/dependencies')
    args=parser.parse_args()
    target=args.output.absolute()
    target.mkdir(parents=True,exist_ok=True)
    lock=json.loads((root/'dependency-lock.json').read_text(encoding='utf-8'))
    for dependency in lock['dependencies']:
        repo=args.repos_root/dependency['name']
        commit=dependency['commit']
        resolved=subprocess.check_output(['git','-C',str(repo),'rev-parse',commit+'^{commit}'],text=True).strip()
        if resolved!=commit:
            raise RuntimeError('Dependency lock must name a full commit')
        with tempfile.TemporaryDirectory(prefix='harness-dependency-build-') as temp:
            work=Path(temp)
            archive=work/'source.tar'
            with archive.open('wb') as stream:
                subprocess.run(['git','-C',str(repo),'archive',commit],stdout=stream,check=True)
            source=work/'source'
            source.mkdir()
            subprocess.run(['tar','-xf',str(archive),'-C',str(source)],check=True)
            env=dict(os.environ)
            env['SOURCE_DATE_EPOCH']=subprocess.check_output(['git','-C',str(repo),'show','-s','--format=%ct',commit],text=True).strip()
            built=work/'wheels'
            subprocess.run([sys.executable,'-m','build','--wheel','--no-isolation','--outdir',str(built)],cwd=source,env=env,check=True)
            wheel=built/dependency['wheel']
            content=wheel.read_bytes()
            if hashlib.sha256(content).hexdigest()!=dependency['sha256']:
                raise RuntimeError(f"{dependency['name']} wheel differs from lock; compare the recorded build tool versions before installing")
            (target/wheel.name).write_bytes(content)
            print(f"Verified {dependency['name']} {dependency['version']} from {commit}")


if __name__=='__main__':
    main()
