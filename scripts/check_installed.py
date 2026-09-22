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
        memory = memory_checks(run, python, root, mode)
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
        console=subprocess.run([str(console_script(python)),'--help'],cwd=root,text=True,capture_output=True)
        assert console.returncode==0 and all(
            command in console.stdout for command in ('plan', 'review', 'fix', '--help-all'))
        catalog=subprocess.run([str(console_script(python)),'--help-all'],cwd=root,text=True,capture_output=True)
        assert catalog.returncode==0 and all(
            command in catalog.stdout for command in ('verify', 'retrieve', 'memory'))
    return {'mode':mode,'cases':cases,'provider_dependencies_absent':True,'memory':memory}


def console_script(python):
    """The installed ``attune-harness`` entry point beside this interpreter, on any platform.

    POSIX puts it next to ``python`` in ``bin/``. Windows puts ``attune-harness.exe``
    in ``Scripts\\``, which is beside a venv's ``python.exe`` or, for an
    interpreter installed at a root such as the hosted tool cache, one level down.
    """
    parent = python.parent
    for candidate in (parent/'attune-harness', parent/'attune-harness.exe',
                      parent/'Scripts'/'attune-harness.exe', parent/'Scripts'/'attune-harness'):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f'No attune-harness console script beside {python}')


def memory_checks(run, python, root, mode):
    """The memory verbs from an installed wheel: the extra absent, or present with no server.

    With the ``redis`` package absent, ``memory redis`` names the extra; with it
    present and no server (a closed local port), it reports unreachable. Either
    way the file scratch store round-trips, a Redis scratch is refused without
    a file being written, and a config with no sections is disabled.
    """
    probe = subprocess.run([str(python),'-I','-c','import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("redis") else 1)'])
    redis_installed = probe.returncode == 0
    if mode == 'redis':
        assert redis_installed, 'the redis mode checks a wheel installed with the redis extra'
    if mode == 'core':
        assert not redis_installed, 'the core mode checks the package alone'
    expected = 'unreachable' if redis_installed else 'attune-harness[redis]'
    scratch_root = root/'scratch-root'
    scratch_root.mkdir()
    unreachable = {'url': 'redis://127.0.0.1:1/0'}
    configs = {
        'file': {'scratch': {'backend': 'file', 'root': str(scratch_root.resolve())}, 'redis': unreachable},
        'none': {'roots': []},
        'redis-scratch': {'scratch': {'backend': 'redis'}, 'redis': unreachable},
    }
    paths = {}
    for name, value in configs.items():
        paths[name] = root/f'memory-{name}.json'
        paths[name].write_text(json.dumps(value), encoding='utf-8')
    cfg = ['memory','--config',str(paths['file'])]
    detail = run([*cfg,'redis','status'],2,'unavailable')['detail']
    assert expected in detail, detail
    run(['memory','--config',str(paths['none']),'redis','status'],2,'disabled')
    assert run([*cfg,'scratch','capabilities'],0,'ok')['backend'] == 'file'
    run([*cfg,'scratch','stash','check:key','--value','{"n": 1}','--ttl','60'],0,'ok')
    assert run([*cfg,'scratch','retrieve','check:key'],0,'ok')['value'] == {'n': 1}
    assert run([*cfg,'scratch','keys','check:*'],0,'ok')['keys'] == ['check:key']
    assert run([*cfg,'scratch','forget','check:key'],0,'ok')['forgotten'] is True
    run([*cfg,'scratch','retrieve','check:key'],0,'no_results')
    before = sorted(str(p) for p in scratch_root.rglob('*'))
    detail = run(['memory','--config',str(paths['redis-scratch']),'scratch','stash','k','--value','1'],2,'unavailable')['detail']
    assert expected in detail, detail
    assert sorted(str(p) for p in scratch_root.rglob('*')) == before, 'a Redis scratch must never write to the file store'
    # serve fails open: exit 0, nothing on stdout, one stderr line naming the reason.
    for name, reason in (('file', expected), ('none', "no 'redis' section")):
        served = subprocess.run([str(python),'-I','-m','attune_harness','memory','--config',str(paths[name]),'serve'],
                                cwd=root,text=True,capture_output=True)
        assert served.returncode == 0 and served.stdout == '', (served.stdout, served.stderr)
        assert served.stderr.startswith('[attune-harness memory] skipped: ') and reason in served.stderr, served.stderr
        assert served.stderr.count('\n') == 1, served.stderr
    return {'redis_installed': redis_installed, 'refusal': expected, 'serve': 'skipped'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--mode',choices=['core','verify','rag','all','redis'],required=True)
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
