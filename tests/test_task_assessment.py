"""Actual forms/tools and independently correlated command peers; no paid calls."""
import json
import sys
import pytest

from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import execute_task
from attune_harness.review_participants import ReviewExchange
from test_review import case, change, scripted
from test_task_contract import draft, response


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
