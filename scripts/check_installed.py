"""Exercise real CLI journeys against an installed wheel outside its source tree."""

import argparse
import importlib.metadata
import json
import os
import subprocess
import tempfile
import time
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
            """Run one verb and record it.

            ``expected`` is one exit code or a tuple of the codes allowed;
            ``status=None`` for an envelope that carries no status key.
            """
            invocation = [str(python),'-I','-m','attune_harness',*arguments]
            result = subprocess.run(invocation,cwd=root,text=True,capture_output=True)
            allowed = expected if isinstance(expected, tuple) else (expected,)
            assert result.returncode in allowed, (result.stdout,result.stderr)
            payload = json.loads(result.stdout)
            if status is not None:
                assert payload['status'] == status,payload
            cases.append({'arguments':arguments,'exit':result.returncode,'status':payload.get('status')})
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
        journey = journey_checks(run, python, root, mode)
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
    return {'mode':mode,'cases':cases,'provider_dependencies_absent':True,'memory':memory,'journey':journey}


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
    # The native reader (Phase 2, D19) reads a raw root with nothing installed: the core
    # gate's --no-deps wheel included; and the document tiers wherever attune-rag is present,
    # which every mode but core has. The sections coexist in one file. On Windows the reader
    # refuses in its own words; the receipt records which it was.
    rag = subprocess.run([str(python),'-I','-c','import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("attune_rag") else 1)']).returncode == 0
    raw_root = root/'raw-root'
    raw_root.mkdir()
    stamp = time.time()  # one stamp, so the two rows tie and keep file order
    rows = [dict(id='a', text='Aurora check row one', topics=['type:note'], cwd='check', ts=stamp),
            dict(id='b', text='Aurora check row two', topics=['type:note'], cwd='check', ts=stamp)]
    (raw_root/'findings.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
    personal_root, curated_root = root/'personal-root', root/'curated-root'
    (personal_root/'aurora').mkdir(parents=True)
    (personal_root/'aurora'/'decision.md').write_text('# Aurora\n\nAurora check reminder is 09:15.\n', encoding='utf-8')
    curated_root.mkdir()
    (curated_root/'aurora_policy.md').write_text('---\nname: aurora_policy\ndescription: Aurora check policy\nmetadata:\n  type: reference\n---\n\nAurora check policy body.\n', encoding='utf-8')
    def roots_config(*roots):
        return {'schema_version': 1, 'actor': 'check', 'owners': ['check'], 'scopes': ['check'],
                'classifications': ['internal'], 'profiles': ['claude'],
                'roots': [dict(id=rid, path=str(path.resolve()), tier=tier, scope='check', owner='check',
                               classification='internal') for rid, path, tier in roots],
                'redis': unreachable}
    paths['roots'] = root/'memory-roots.json'
    paths['roots'].write_text(json.dumps(roots_config(('r', raw_root, 'raw'))), encoding='utf-8')
    reads = ['memory','--config',str(paths['roots'])]
    capabilities = run([*reads,'capabilities'],0,None)
    assert capabilities['read'] == ['raw','personal','curated'] and capabilities['reader'] == 'native', capabilities
    tiers = []
    if os.name == 'posix':
        packet = run([*reads,'recall','Aurora','--k','2'],0,'available')
        assert [i['handle']['id'] for i in packet['items']] == ['r:a','r:b'], packet['items']
        handle = root/'memory-handle.json'
        handle.write_text(json.dumps(packet['items'][0]['handle']), encoding='utf-8')
        assert run([*reads,'resolve',str(handle)],0,None)['text'] == 'Aurora check row one'
        refresh = root/'memory-context.json'  # not context.json, which the verify journey reads
        refresh.write_text(json.dumps(packet), encoding='utf-8')
        assert run([*reads,'refresh',str(refresh)],0,'available')['invalidated_ids'] == []
        tiers = ['raw']
        if rag:
            paths['tiers'] = root/'memory-tiers.json'
            paths['tiers'].write_text(json.dumps(roots_config(('r', raw_root, 'raw'), ('p', personal_root, 'personal'),
                                                              ('c', curated_root, 'curated'))), encoding='utf-8')
            packet = run(['memory','--config',str(paths['tiers']),'recall','Aurora','--k','10'],0,'available')
            ids = {i['handle']['id'] for i in packet['items']}
            assert {'r:a','r:b','p:aurora/decision.md','c:aurora_policy.md'} <= ids, sorted(ids)
            assert packet['problems'] == [], packet['problems']
            tiers = ['raw','personal','curated']
        native = 'available'
    else:
        packet = run([*reads,'recall','Aurora','--k','2'],2,'unavailable')
        assert 'qualified only on POSIX' in packet['problems'][0]['detail'], packet['problems']
        native = 'posix-only refusal'
    return {'redis_installed': redis_installed, 'refusal': expected, 'serve': 'skipped',
            'native_reader': native, 'tiers_read': tiers, 'reader_named': capabilities['reader']}


INSTALL_HINT = 'is missing; reinstall with: pip install --force-reinstall attune-harness'

# The build's worker and reviewer: one local script run as two command
# participants. The worker proposes the files each step names; the reviewer
# returns an empty critique. One JSON request on stdin, one JSON reply on stdout.
PEER = (
    "import json,sys,hashlib\n"
    "w=json.load(sys.stdin);t=w['turn']\n"
    "if t['role']=='reviewer':p={'kind':'critique','findings':[],'notes':['Synthetic command fixture']}\n"
    "else:\n"
    " texts={'pkg/export.py':'def answer():\\n    return 42\\n','tests/generated/test_app.py':'def test_generated():\\n    assert True\\n','source.py':'from pkg.export import answer\\ndef value():\\n    return answer()\\n'}\n"
    " p={'schema_version':1,'task_id':t['step']['id'],'dependencies':t['step']['dependencies'],'files':[{'path':n,'before_sha256':hashlib.sha256(t['source_evidence'][n].encode()).hexdigest() if n in t['source_evidence'] else None,'text':texts[n]} for n in t['step']['outputs']]}\n"
    "print(json.dumps({'schema_version':1,'request_digest':w['request_digest'],'action':{'kind':'final','text':json.dumps(p)}}))\n"
)

# Freezes the effects manifest and writes the work request. No command line
# verb freezes a manifest, so this runs inside the checked interpreter, with
# the installed package; argv: project root, task directory, request path.
FREEZE = r"""
import json, os, sys
from pathlib import Path
from attune_harness import work_effects
root, directory, request_path = (Path(a) for a in sys.argv[1:4])
EXPORT, GENERATED = "pkg/export.py", "tests/generated/test_app.py"
BUDGET = {"max_operations": 30, "max_attempts": 1, "max_output_bytes": 32768}


def probe(argv, oracle):
    environment = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    if os.name == "nt":  # the Windows probe contract wants one frozen SystemRoot
        environment["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
    return {"argv": [sys.executable, "-B", *argv], "cwd": ".", "timeout": 10,
            "max_output_bytes": 2048, "environment": environment, "oracle_paths": [oracle]}


def assignment(role, participant, contract):
    return {"role": role, "participant": participant, "output_contract": contract, "budgets": BUDGET}


control = {"id": "baseline", "kind": "check", "owner": "host", "version": 1, "required": True, "phases": ["build"]}
scope = [EXPORT, GENERATED, "source.py"]
effects = work_effects.freeze(
    root, scope, ["pkg", "tests", "tests/generated"], ["baseline.py", "oracle.py", "plan.md", "pytest.ini"],
    [{"control": work_effects.identity(control), "probe": probe(["baseline.py"], "baseline.py")}], directory,
    verification=[{"task_id": "export", "probe": probe(["-c", "from pkg.export import answer;assert answer()==42"], "oracle.py")},
                  *[{"task_id": n, "probe": probe(["oracle.py"], "oracle.py")} for n in ("wire", "final")]])
acceptance = ["value returns 42 without changing protected checks"]
request = {
    "intent": {"goal": "Export every finding", "context": ["Default JSON must survive"], "scope": scope,
               "constraints": ["Preserve unknown claims"], "acceptance": acceptance, "questions": []},
    "assignments": [assignment("planner", "local", "Ordered task plan"), assignment("worker", "local", "Scoped file proposal"),
                    assignment("reviewer", "critic", "Evidence-backed critique")],
    "controls": [control],
    "tasks": [{"id": "export", "objective": "Create exporter and supplemental test", "dependencies": [],
               "outputs": [EXPORT, GENERATED], "checks": ["answer returns 42"]},
              {"id": "wire", "objective": "Use exporter in the existing function", "dependencies": ["export"],
               "outputs": ["source.py"], "checks": acceptance}],
    "inputs": ["source.py"], "artifact": "plan.md", "budget": BUDGET, "effects": effects}
request_path.write_text(json.dumps(request), encoding="utf-8")
"""


def journey_checks(run, python, root, mode):
    """R2 from the installed wheel: plan, accept, build, review and status with ``attune`` absent.

    Where attune-forms is installed, which the base install carries, the whole
    journey runs, with two command participants (one local script) as the
    build's worker and reviewer and a deterministic assessor for the review, so
    no model is called (spec authority Task 4, D23.1 and D23.4). From the
    ``--no-deps`` wheel, ``plan --request`` still drafts and ``status`` still
    reads the draft; ``plan --accept`` and ``review`` refuse with the install
    hint; ``build`` refuses for want of accepted authority, since nothing could
    accept it. On Windows the build may refuse in the platform's own words; the
    receipt records which of the two outcomes it saw rather than skipping. The
    ``attune`` package is asserted absent by the caller, in every mode.
    """
    forms = subprocess.run([str(python),'-I','-c','import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("attune_forms") else 1)']).returncode == 0
    # The core mode checks the --no-deps wheel; every other mode is an install with the
    # base dependencies, attune-forms among them (D15), so its absence is a finding there.
    assert forms == (mode != 'core'), f"attune-forms {'present' if forms else 'absent'} in the {mode} mode"
    root = root.resolve()  # the task store refuses to traverse a symlink, and macOS's temporary root is one
    project = root/'journey'
    project.mkdir()
    (project/'source.py').write_text('def value():\n    return 1\n', encoding='utf-8')
    (project/'plan.md').write_text('Preserve all findings and default JSON.\n', encoding='utf-8')
    (project/'baseline.py').write_text('from source import value\nassert value()==1\n', encoding='utf-8')
    (project/'oracle.py').write_text('from source import value\nassert value()==42\n', encoding='utf-8')
    (project/'pytest.ini').write_text('[pytest]\n', encoding='utf-8')
    (project/'docs').mkdir()
    (project/'docs'/'guide.md').write_text('The exporter answers 42. See [reference](reference.md).\n', encoding='utf-8')
    (project/'docs'/'reference.md').write_text('# Reference\nThe exporter returns 42.\n', encoding='utf-8')
    hooks = root/'no-hooks'  # an empty hooks directory, which Git reads the same on every platform
    hooks.mkdir()
    git = ['git','-C',str(project),'-c','commit.gpgsign=false','-c',f'core.hooksPath={hooks}',
           '-c','user.name=Check','-c','user.email=check@example.invalid']
    subprocess.run(['git','init','-q',str(project)], check=True, capture_output=True)
    subprocess.run([*git,'add','source.py','plan.md','baseline.py','oracle.py','pytest.ini','docs'], check=True, capture_output=True)
    subprocess.run([*git,'commit','-qm','Journey baseline'], check=True, capture_output=True)
    # The review's verification context lives inside the project, as its intake requires.
    context = project/'context.json'
    context.write_text(json.dumps({'schema_version': 1, 'project_root': '.'}), encoding='utf-8')
    peer = root/'journey-peer.py'
    peer.write_text(PEER, encoding='utf-8')
    command = {'adapter': 'command', 'command': [str(python), '-B', str(peer)], 'timeout': 30,
               'tools': [], 'max_turns': 1, 'max_tool_calls': 0}
    deterministic = {'adapter': 'deterministic', 'tools': [], 'max_turns': 1, 'max_tool_calls': 0}
    participants = root/'journey-participants.json'
    participants.write_text(json.dumps({'schema_version': 1, 'participants': {
        'local': command, 'critic': command, 'assessor': deterministic}}), encoding='utf-8')
    directory, request = root/'journey-work', root/'journey-request.json'
    frozen = subprocess.run([str(python),'-I','-c',FREEZE,str(project),str(directory),str(request)], text=True, capture_output=True)
    assert frozen.returncode == 0, frozen.stderr

    plan = run(['plan','--task-dir',str(directory),'--project',str(project),'--config',str(participants),'--request',str(request)],0,'draft')
    assert not plan['questions']['missing'], plan
    accept = ['plan','--task-dir',str(directory),'--accept','--checkpoint',plan['checkpoint_digest']]
    build = ['build',str(directory),'--allow-external']
    review = ['review','--goal',"Check the guide against the exporter's evidence",'--project',str(project),
              '--config',str(participants),'--document','docs/guide.md','--context',str(context),'--corpus','docs',
              '--query','exporter','--criteria','Identify unsupported claims and preserve uncertainty',
              '--assessor','assessor','--accept','--task-dir',str(root/'journey-review')]
    receipt = {'forms_installed': forms, 'plan': plan['status']}
    if not forms:
        detail = run(accept,2,'failed')['error']['detail']
        assert detail == f'attune-forms {INSTALL_HINT}', detail
        receipt['accept'] = f'refused: {detail}'
        detail = run(build,2,'failed')['error']['detail']
        assert detail == 'Effects require current accepted work authority', detail
        receipt['build'] = f'refused: {detail}'
        detail = run(review,2,'failed')['error']['detail']
        assert detail.endswith(INSTALL_HINT), detail
        receipt['review'] = f'refused: {detail}'
        receipt['status'] = run(['status',str(directory)],0,'draft')['status']
        return receipt
    accepted = run(accept,0,'accepted')
    assert accepted['receipt']['disposition'] == 'approve_task', accepted
    receipt['accept'] = 'accepted'
    built = run(build,(0,2),None)
    turns = []
    if built['status'] == 'completed':
        assert built['blocking'] is False and built['execution_evidence']['runs'], built
        assert (project/'pkg'/'export.py').read_text(encoding='utf-8').startswith('def answer():')
        # What ran, from the evidence: the host control, and each participant turn with the adapter it reported.
        operations = built['execution_evidence']['runs'][0]['operations']
        receipt['controls_run'] = [op['operation'] for op in operations if op.get('kind') == 'build_control']
        assert receipt['controls_run'] == ['control:baseline'], receipt['controls_run']
        turns = [((op.get('participant_reported_adapter_identity') or {}).get('value') or {}).get('adapter')
                 for op in operations if op.get('kind') == 'participant_turn']
        assert len(turns) == 3 and set(turns) == {'command'}, turns
        receipt['build'] = 'completed'
    else:
        # Recorded, not skipped: the Windows effects profile refused, in its own words and no other's.
        error = built.get('error') or {}
        assert os.name == 'nt' and error.get('type') == 'FeatureUnavailable', built
        assert error.get('detail','').startswith(('Windows effects require','Windows WCHAR layout')), built
        receipt['build'] = f"refused: {error['detail']}"
    reviewed = run(review,0,'completed')
    assert reviewed['operation'] == 'task', reviewed
    assessors = [p.get('adapter') for p in reviewed['execution']['participants'].values()]
    assert assessors == ['deterministic'], assessors
    receipt['review'] = 'completed'
    # Measured, not declared: every participant turn's adapter, and how many were a model.
    receipt['participant_turns'] = len(turns) + len(assessors)
    receipt['adapters'] = sorted(set(turns + assessors))
    receipt['model_calls'] = sum(1 for a in turns + assessors if a not in ('command', 'deterministic'))
    receipt['status'] = run(['status',str(directory)],0,'completed' if receipt['build'] == 'completed' else 'accepted')['status']
    return receipt


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
