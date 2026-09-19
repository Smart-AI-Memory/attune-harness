"""Actual forms/tools and independently correlated command peers; no paid calls."""
import json
import subprocess
import sys
import pytest

from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import execute_task
from attune_harness.review_participants import ReviewExchange
from test_review import case, change, scripted
from test_task_contract import draft, response


def test_goal_accept_pause_status_resume_as_one_cli_journey(case):
    """The advertised primary command keeps one identity without repeated calls."""
    root, registry, task = case[0].parent, case[1], case[2]
    calls = root / 'peer-calls.jsonl'
    peer = root / 'journey-peer.py'
    peer.write_text(
        'import json,sys\n'
        'packet=json.load(sys.stdin)\n'
        'with open(sys.argv[1], "a", encoding="utf-8") as log:\n'
        '    log.write(json.dumps(packet)+"\\n")\n'
        'print(json.dumps({"schema_version":1,"request_digest":packet["request_digest"],'
        '"action":{"kind":"final","text":"Observed role " + packet["turn"]["role"]}}))\n',
        encoding='utf-8',
    )
    configuration = {'adapter': 'command', 'command': [sys.executable, '-I', str(peer), str(calls)],
                     'timeout': 10, 'tools': [], 'max_turns': 1, 'max_tool_calls': 0}
    change(registry, lambda data: data.update(participants={
        name: configuration for name in ('alpha', 'beta')}))

    def invoke(arguments, expected):
        result = subprocess.run([sys.executable, '-B', '-m', 'attune_harness', *arguments],
                                cwd=root, capture_output=True, text=True, timeout=30)
        assert result.returncode == expected, result.stdout + result.stderr
        return json.loads(result.stdout)

    paused = invoke([
        'review', '--goal', 'Check guide evidence', '--project', str(root),
        '--config', str(registry), '--task-dir', str(task),
        '--criteria', 'Preserve uncertainty', '--query', 'quartz',
        '--document', 'project/guide.md', '--context', 'context.json', '--corpus', 'project',
        '--plan', 'independent-review', '--assessor', 'alpha', '--reviewer', 'beta',
        '--allow-external', '--accept', '--pause-after', '3',
    ], 1)
    assert paused['status'] == 'paused'
    first_calls = calls.read_bytes()
    packets = [json.loads(line) for line in first_calls.splitlines()]
    assert [packet['turn']['role'] for packet in packets] == ['assessor']
    before_status = read_task(task)
    inspected = invoke(['status', str(task)], 0)
    assert inspected['status'] == 'paused'
    assert read_task(task) == before_status and calls.read_bytes() == first_calls

    completed = invoke(['resume', str(task)], 0)
    assert completed['status'] == 'completed'
    assert completed['request']['task_id'] == inspected['request']['task_id'] == paused['request']['task_id']
    final_calls = calls.read_bytes()
    packets = [json.loads(line) for line in final_calls.splitlines()]
    assert [packet['turn']['role'] for packet in packets] == ['assessor', 'reviewer']
    assert len({packet['request_digest'] for packet in packets}) == 2
    assert all(packet['turn']['task_id'] == completed['request']['task_id'] for packet in packets)
    integration = completed['execution']['integration']
    assert integration['acceptance_status'] == 'unverified'
    assert integration['semantic_verification'] is False
    assert invoke(['resume', str(task)], 0) == completed
    assert calls.read_bytes() == final_calls


@pytest.mark.parametrize('plan,count', [('solo', 1), ('independent-review', 2)])
def test_one_dispatch_per_isolated_assignment(case, plan, count):
    draft(case, plan=plan)
    accepted = accept_task(case[2], response(case[2]))
    packets = []
    def factory(config, cwd):
        real = ReviewExchange(config, cwd)
        def exchange(raw):
            packets.append(json.loads(raw))
            return real(raw)
        return exchange
    result = execute_task(case[2], exchange_factory=factory)
    assert result == read_task(case[2])
    assert result['status'] == 'completed'
    run = result['execution']
    assert len(packets) == count
    assert len(run['events']) == count + 3
    assert run['preflight_verification']['result']['claims']
    assert run['initial_retrieval']['sources']
    assert run['integration']['semantic_verification'] is False
    assert run['integration']['acceptance_status'] == 'unverified'
    for packet in packets:
        assert packet['turn']['task_id'] == accepted['request']['task_id']
        assert 'Deterministic demonstration' not in json.dumps(packet)
        assert len(packet['turn']['history']) == 2
    assert len({p['request_digest'] for p in packets}) == count
    assert len({p['turn']['attempt_id'] for p in packets}) == count


@pytest.mark.parametrize('content,status', [('[bad](missing.md)', 'refuted'), ('No supported claims', 'unknown')])
def test_document_failure_does_not_become_execution_failure(case, content, status):
    (case[0].parent / 'project/guide.md').write_text(content)
    draft(case)
    accept_task(case[2], response(case[2]))
    r = execute_task(case[2])
    assert r['status'] == 'completed'
    assert r['execution']['document_outcome'] == status
    assert r['execution']['integration']['acceptance_status'] == 'unverified'


def test_disagreement_preserves_both_unverified_narratives(case):
    draft(case, plan='independent-review'); accept_task(case[2], response(case[2]))
    def action(packet):
        role = packet['turn']['role']
        return {'kind': 'final', 'text': 'Everything is definitely verified' if role == 'assessor' else 'This is contradicted by reference.md'}
    r = execute_task(case[2], exchange_factory=scripted(action))
    assert r['status'] == 'completed'
    i = r['execution']['integration']
    assert i['semantic_verification'] is False
    assert 'definitely' in i['narratives']['assessor']['text']
    assert 'contradicted' in i['narratives']['reviewer']['text']


@pytest.mark.parametrize('action', [{'kind':'tool','name':'verify','arguments':{}}, {'kind':'final','text':''}])
def test_invalid_or_extra_tool_request_fails(case, action):
    draft(case); accept_task(case[2], response(case[2]))
    r = execute_task(case[2], exchange_factory=scripted(action))
    assert r['status'] == 'failed'
    assert 'integration' not in r['execution']


def test_sources_changed_by_peer_cannot_complete(case):
    draft(case); accept_task(case[2], response(case[2]))
    def mutate(packet):
        (case[0].parent / 'project/reference.md').write_text('changed')
    r = execute_task(case[2], exchange_factory=scripted({'kind':'final','text':'OK'}, mutate))
    assert r['status'] == 'failed'
    assert 'Stale source' in r['execution']['error']['detail']


def test_independent_command_peer(case):
    peer = case[0].parent / 'peer.py'
    peer.write_text('import json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"schema_version":1,"request_digest":r["request_digest"],"action":{"kind":"final","text":"Independent command sees " + r["turn"]["role"]}}))\n')
    change(case[1], lambda d: d['participants'].update(alpha={'adapter':'command','command':[sys.executable,str(peer)],'timeout':10,'tools':[],'max_turns':1,'max_tool_calls':0}))
    draft(case)
    s = response(case[2]);s['permissions']['external']=True
    accept_task(case[2],s)
    r=execute_task(case[2])
    assert r['status']=='completed'
    assert r['execution']['participants']['assessor']['text']=='Independent command sees assessor'


def test_operation_budget_denies_before_tools(case):
    draft(case, budget={'max_operations':3,'max_attempts':1,'max_output_bytes':32768})
    accept_task(case[2],response(case[2]))
    with pytest.raises(ValueError,match='budget'):
        execute_task(case[2])
    assert 'execution' not in read_task(case[2])


def test_primary_cli_executes_accepted_task(case, capsys, monkeypatch):
    from attune_harness.cli import main
    draft(case)
    p=case[0].parent/'response.json';p.write_text(json.dumps(response(case[2])))
    assert main(['review','--task-response',str(p),'--task-dir',str(case[2])])==0
    assert json.loads(capsys.readouterr().out)['execution']['status']=='completed'


def test_output_budget_and_external_permission(case):
    draft(case, budget={'max_operations':100,'max_attempts':1,'max_output_bytes':4})
    accept_task(case[2],response(case[2]))
    r=execute_task(case[2],exchange_factory=scripted({'kind':'final','text':'too large'}))
    assert r['status']=='failed'
    assert 'output budget' in r['execution']['error']['detail']


def test_native_evidence_has_one_invocation(case, monkeypatch):
    from test_native_evidence_review import configure, install_peer
    change(case[1], configure)
    draft(case, plan='independent-review')
    value=response(case[2]);value['permissions']['external']=True
    accept_task(case[2],value)
    calls=[];install_peer(monkeypatch,calls)
    r=execute_task(case[2])
    assert r['status']=='completed',r['execution'].get('error')
    assert len(calls)==2
