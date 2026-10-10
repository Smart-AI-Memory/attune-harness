"""One tutorial pilot, extending #250's cold-start fixtures; POSIX execution only."""
# qualify: platform
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


ACCEPTANCE = module('tutorial_acceptance', ROOT / 'scripts/tutorial_acceptance.py')
COLD = module('cold_start_reference', ROOT / 'tests/test_cold_start_journey.py')
home = COLD.home
CONTRACT = ROOT / 'docs/journeys/first-repair-acceptance.json'
DOCUMENT_ROOT = Path(os.environ.get('HARNESS_FIRST_REPAIR_DOCUMENT_ROOT', ROOT))
EXAMPLE_ROOT = Path(os.environ.get('HARNESS_FIRST_REPAIR_EXAMPLE_ROOT', ROOT))


def load():
    return ACCEPTANCE.load(CONTRACT, document_root=DOCUMENT_ROOT, example_root=EXAMPLE_ROOT)


@pytest.mark.parametrize('drift', ['document','block','release','example','result_inventory',
                                 'acceptance_reference','acceptance_criteria'])
def test_contract_refuses_input_drift_before_execution(tmp_path, drift):
    contract, _ = load()
    altered = copy.deepcopy(contract)
    if drift == 'document':
        altered['document_sha256'] = '0'*64
    elif drift == 'block':
        altered['journeys']['first-repair-result']['body_sha256'] = '0'*64
    elif drift == 'release':
        altered['release']['source_commit'] = '0'*40
    elif drift == 'example':
        altered['examples']['examples/starter/worker.py'] = '0'*64
    elif drift == 'acceptance_reference':
        altered['acceptance_reference']['document'] = 'unreviewed-reference'
    elif drift == 'acceptance_criteria':
        altered['acceptance_reference']['criteria'] = ['J1','J3']
    else:
        altered['journeys']['first-repair-result']['expected'].pop()
    path = tmp_path / 'mutated-contract.json'
    path.write_text(json.dumps(altered))
    with pytest.raises(ValueError):
        ACCEPTANCE.load(path, document_root=DOCUMENT_ROOT, example_root=EXAMPLE_ROOT)
    assert list(tmp_path.iterdir()) == [path]


def test_expected_outcome_drift_is_detected():
    contract, _ = load()
    expected = contract['journeys']['first-repair-continue']['expected'][0]
    assert expected == {'exit':1,'status':'paused'}
    with pytest.raises(AssertionError):
        ACCEPTANCE.check_result(0, {'status':'completed'}, expected)


def test_protected_oracle_drift_is_detected(tmp_path):
    contract, _ = load()
    oracle = tmp_path / 'test_calc.py'
    oracle.write_text('def test_add():\n    assert True\n')
    with pytest.raises(AssertionError, match='oracle drifted'):
        ACCEPTANCE.check_oracle(oracle, contract)


@COLD.POSIX_ONLY
def test_documented_repair_refuses_stale_approval_then_recovers(home, record_property, monkeypatch):
    contract, blocks = load()
    startup_names = ['PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONUSERBASE',
                     'PYTHONOPTIMIZE','PYTHONWARNINGS','PYTEST_ADDOPTS','PYTEST_PLUGINS']
    for name in startup_names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('PYTHONNOUSERSITE', '1')
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
    record_property('scrubbed_startup_variable_names', json.dumps(startup_names))
    # Check the same nonisolated interpreter/environment used by the CLI helper.
    identity_code = ('import hashlib,json,pathlib,sys,attune_harness; '
                     'p=pathlib.Path(attune_harness.__file__).parent; '
                     'print(json.dumps({"prefix":sys.prefix,"source":str(p),'
                     '"hashes":{str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() '
                     'for f in p.rglob("*.py")}}))')
    identity = subprocess.run([sys.executable,'-B','-c',identity_code], cwd=home,
        env=COLD.environment(),capture_output=True,text=True,timeout=15,check=True)
    identity = json.loads(identity.stdout)
    expected_source = EXAMPLE_ROOT / 'src/attune_harness'
    expected_hashes = {str(p.relative_to(expected_source)):ACCEPTANCE.digest(p)
                       for p in expected_source.rglob('*.py')}
    assert expected_hashes and identity['hashes'] == expected_hashes
    assert identity['prefix'] == sys.prefix
    record_property('child_import_source', identity['source'])
    record_property('child_source_module_count', len(expected_hashes))
    record_property('child_source_inventory_sha256', hashlib.sha256(
        json.dumps(expected_hashes,sort_keys=True).encode()).hexdigest())
    record_property('tutorial_id', contract['tutorial_id'])
    record_property('tutorial_document_sha256', contract['document_sha256'])
    record_property('expected_release_source', contract['release']['source_commit'])
    record_property('runtime_interpreter', sys.executable)
    record_property('human_approval_comprehension', 'not measured by automated submission')
    project, task = home / 'project-δ', home / 'repair-task'
    variables = {'FIRST_REPAIR_ROOT':str(home),'FIRST_REPAIR_PROJECT':str(project),
                 'FIRST_REPAIR_TASK':str(task),'FIRST_REPAIR_RELEASE':str(EXAMPLE_ROOT),
                 'FIRST_REPAIR_PYTHON':sys.executable}
    table = {'$'+name:value for name,value in variables.items()}

    def python_block(name, filename):
        (code,) = ACCEPTANCE.READER.commands(blocks[name])
        path = home / filename
        path.write_text(code)
        result = subprocess.run([sys.executable,'-B',str(path)],cwd=home,
            env=dict(COLD.environment(),**variables),capture_output=True,text=True,timeout=60)
        ACCEPTANCE.check_result(result.returncode, None, contract['journeys'][name]['expected'][0])
        assert not result.stderr, result.stderr

    def command(name, index, *, response=None, check=True):
        text = ACCEPTANCE.READER.commands(blocks[name])[index]
        argv = COLD.split(ACCEPTANCE.READER.substitute(text, table))
        redirected = name == 'first-repair-preview' and index == 1
        if redirected:
            assert argv[-4:] == ['<','/dev/null','>',str(home / 'preview.json')]
            argv = argv[:-4]
        if response:
            argv[argv.index('--task-response') + 1] = str(response)
        assert argv[0] == 'attune-harness'
        code, envelope, output = COLD.harness(argv[1:],home,
            stdout_file=home / 'preview.json' if redirected else None)
        if redirected:
            assert envelope is not None, output
        if check:
            ACCEPTANCE.check_result(code,envelope,contract['journeys'][name]['expected'][index])
        return code,envelope,output

    python_block('first-repair-prepare','prepare.py')
    source = (project / 'calc.py').read_bytes()
    oracle = project / 'tests/test_calc.py'
    ACCEPTANCE.check_oracle(oracle, contract)
    command('first-repair-preview',0)
    _, draft, _ = command('first-repair-preview',1)
    assert draft['submission']['accepted'] is False
    before_accept_record = (task / 'record.json').read_bytes()
    before_accept_files = {str(p.relative_to(task)):p.read_bytes()
                           for p in task.rglob('*') if p.is_file()}
    approved_scope = json.loads(before_accept_record)['request']['repair']['scope']
    python_block('first-repair-response','accept-response.py')
    response = json.loads((home / 'accepted-response.json').read_text())
    assert response['permissions'] == {'external':True,'provider':False}
    stale = copy.deepcopy(response)
    stale['checkpoint_digest'] = '0'*64
    stale_path = home / 'stale-response.json'
    stale_path.write_text(json.dumps(stale))
    code, rejected, output = command('first-repair-continue',0,response=stale_path,check=False)
    assert code != 0 and rejected and rejected['status'] == 'failed', output
    assert 'stale' in output.lower() and 'response' in output.lower(), output
    assert (task / 'record.json').read_bytes() == before_accept_record
    assert {str(p.relative_to(task)):p.read_bytes() for p in task.rglob('*')
            if p.is_file()} == before_accept_files
    assert (project / 'calc.py').read_bytes() == source
    ACCEPTANCE.check_oracle(oracle,contract)

    # Recover using the original current response, never by editing the saved record.
    _,paused,_ = command('first-repair-continue',0)
    command('first-repair-continue',1)
    (before_event,) = paused['execution']['events']
    assert before_event['operation_key'] == 'probe:before' and before_event['result']['passed'] is False
    assert (project / 'calc.py').read_bytes() == source
    ACCEPTANCE.check_oracle(oracle,contract)
    _, completed, _ = command('first-repair-result',0)
    _, inspected, _ = command('first-repair-result',1)
    _, replayed, _ = command('first-repair-result',2)
    execution = completed['execution']
    assert execution['before_probe']['passed'] is False and execution['after_probe']['passed'] is True
    assert execution['before_probe']['plan_digest'] == execution['after_probe']['plan_digest'] == before_event['result']['plan_digest']
    approved_plan = hashlib.sha256(json.dumps(approved_scope, sort_keys=True,
        separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert execution['before_probe']['plan_digest'] == approved_plan
    assert ACCEPTANCE.digest(project / 'calc.py') == contract['repaired_source_sha256']
    ACCEPTANCE.check_oracle(oracle,contract)
    assert execution['integration']['acceptance_status'] == 'verified_within_probe_scope'
    assert execution['integration']['semantic_verification'] is False
    assert len(execution['events']) == 5 and all(e['attempts'] == 1 for e in execution['events'])
    assert execution['events'] == inspected['execution']['events'] == replayed['execution']['events']
