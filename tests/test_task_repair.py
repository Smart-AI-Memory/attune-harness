"""Repair policy uses the same dispatch, immutable evidence and durable continuation."""
import copy
import json
import os
import sys
from pathlib import Path
import pytest

from attune_harness.cli import main
from attune_harness.task_contract import create_repair_task,accept_task,read_task
from attune_harness.task_cli import present_task
from attune_harness.task_policies import execute_task,control_task
from attune_harness.review_store import RunStore,PersistenceError
from attune_harness.recovery import UnresolvedOperation
from test_task_repair_effects import effect_case
from test_review import scripted

pytestmark=pytest.mark.skipif(os.name!='posix',reason='POSIX repair profile only')


def prepare(effect_case,review='required',*,config=None):
    root,plan,_,_=effect_case
    registry=root.parent/'registry.json'
    registry.write_text(json.dumps(config or {'schema_version':1,'participants':{n:{'adapter':'deterministic','tools':[],'max_turns':1,'max_tool_calls':0} for n in ('worker','reviewer')}}))
    directory=root.parent/'task'
    task=create_repair_task(root.parent,registry,goal='Fix addition',checkout=root,allowed=plan['allowed'],
        probe=plan['probe'],worker='worker',reviewer='reviewer' if review!='none' else None,
        review=review,criteria='add(2,3) must equal 5 without changing tests',directory=directory)
    shown=present_task(directory)
    assert shown['repair_contract']['scope']['probe']==plan['probe']
    assert shown['repair_contract']['review']==review
    value=shown['submission'];value.update(accepted=True)
    value['permissions']['external']=True
    accept_task(directory,value)
    return directory


def proposal(packet,*,wrong=False,verdict='approve',objections=None):
    turn=packet['turn'];e=turn['repair']
    if turn['role']=='worker':
        value={'schema_version':1,'replacements':[{'path':'app.py','before_sha256':e['before_hashes']['app.py'],
               'text':'def add(a,b):\n    return '+('0' if wrong else 'a+b')+'\n'}]}
    else:
        value={'schema_version':1,'artifact_digest':e['artifact_digest'],'probe_digest':e['probe_digest'],
               'verdict':verdict,'findings':objections or []}
    return {'kind':'final','text':json.dumps(value)}


@pytest.mark.parametrize('review',['none','requested','required'])
def test_failed_before_passed_after_and_bound_review(effect_case,review):
    directory=prepare(effect_case,review)
    seen=[]
    r=execute_task(directory,exchange_factory=scripted(proposal,lambda p:seen.append(p)))
    assert r['status']=='completed',r['execution'].get('error')
    assert r==read_task(directory)
    run=r['execution']
    assert not run['before_probe']['passed'] and run['after_probe']['passed']
    assert run['integration']['acceptance_status']=='verified_within_probe_scope'
    assert run['integration']['semantic_verification'] is False
    assert len(seen)==(1 if review=='none' else 2)
    if review!='none':
        assert run['review']['artifact_digest']==run['integration']['artifact_digest']
        payload=seen[-1]['turn']['repair']
        assert set(payload)=={'artifact_digest','probe_digest','changes','before_probe','after_probe'}
        assert 'before_hashes' not in payload
    assert 'return a+b' in (effect_case[0]/'app.py').read_text()


@pytest.mark.parametrize('boundary',range(1,6))
def test_every_repair_boundary_replays_same_calls_writes_and_probes(effect_case,boundary):
    directory=prepare(effect_case)
    calls=[]
    factory=scripted(proposal,lambda p:calls.append(p))
    paused=execute_task(directory,max_operations=boundary,exchange_factory=factory)
    assert paused['status']=='paused',paused['execution'].get('error')
    events=copy.deepcopy(paused['execution']['events'])
    inode=(effect_case[0]/'app.py').stat().st_ino
    done=execute_task(directory,exchange_factory=factory)
    assert done['status']=='completed',done['execution'].get('error')
    assert done['execution']['events'][:boundary]==events
    assert len(calls)==2
    if boundary>=3:assert (effect_case[0]/'app.py').stat().st_ino==inode
    assert execute_task(directory,exchange_factory=scripted(lambda _:pytest.fail('duplicate')))==done


@pytest.mark.parametrize('kind',['wrong','reject','uncertain','findings','bad-binding','missing-review'])
def test_wrong_or_unreviewed_repair_never_verified(effect_case,kind):
    directory=prepare(effect_case,review='requested')
    def action(p):
        if p['turn']['role']=='reviewer' and kind=='missing-review':raise RuntimeError('review unavailable')
        a=proposal(p,wrong=kind=='wrong',verdict=kind if kind in ('reject','uncertain') else 'approve',objections=['Unresolved defect'] if kind=='findings' else [])
        if p['turn']['role']=='reviewer' and kind=='bad-binding':
            v=json.loads(a['text']);v['artifact_digest']='foreign';a['text']=json.dumps(v)
        return a
    r=execute_task(directory,exchange_factory=scripted(action))
    assert r['status']=='failed'
    assert r['request']['repair']['review']=='requested'
    if kind=='wrong':
        assert r['execution']['after_probe']['passed'] is False
    else:
        assert r['execution']['after_probe']['passed'] is True
        assert 'reviewer' in r['execution']['participants']
    assert r['execution'].get('integration',{}).get('acceptance_status')!='verified_within_probe_scope'


def test_noop_and_initially_passing_case_cannot_claim_repair(effect_case):
    root,plan,_,_=effect_case
    (root/'app.py').write_text('def add(a,b):\n    return a+b\n')
    directory=prepare(effect_case,review='none')
    r=execute_task(directory,exchange_factory=scripted(lambda _:pytest.fail('unneeded worker')))
    assert r['status']=='failed' and r['execution']['before_probe']['passed']


def test_final_bytes_or_probe_changes_invalidate_completion(effect_case):
    directory=prepare(effect_case)
    r=execute_task(directory,exchange_factory=scripted(proposal));assert r['status']=='completed'
    (effect_case[0]/'app.py').write_text('later user edit')
    with pytest.raises(UnresolvedOperation):execute_task(directory)


def test_lost_write_ack_needs_observed_reconciliation(effect_case,monkeypatch):
    directory=prepare(effect_case)
    original=RunStore.save
    def fail(store,record):
        if any(e['kind']=='replacement' and e['state']=='completed' for e in record.get('execution',{}).get('events',[])):
            raise PersistenceError('lost write acknowledgement')
        original(store,record)
    with monkeypatch.context() as m:
        m.setattr(RunStore,'save',fail)
        with pytest.raises(PersistenceError):execute_task(directory,exchange_factory=scripted(proposal))
    saved=read_task(directory);event=saved['execution']['events'][-1]
    with pytest.raises(UnresolvedOperation):execute_task(directory,exchange_factory=scripted(proposal))
    inode=(effect_case[0]/'app.py').stat().st_ino
    control_task(directory,'reconcile',event_id=event['event_id'],observe_file=True)
    done=execute_task(directory,exchange_factory=scripted(proposal))
    assert done['status']=='completed',done['execution'].get('error')
    assert (effect_case[0]/'app.py').stat().st_ino==inode


def test_required_same_native_model_is_rejected_before_dispatch(effect_case):
    config={'schema_version':1,'participants':{n:{'adapter':'codex','model':'same-model','timeout':10,'tools':[],'max_turns':1,'max_tool_calls':0} for n in ('worker','reviewer')}}
    with pytest.raises(ValueError,match='different configured native model'):
        prepare(effect_case,config=config)


def test_independent_command_fix_through_cli(effect_case,capsys):
    root,plan,_,_=effect_case
    peer=root.parent/'repair-peer.py'
    peer.write_text('import json,sys\nr=json.load(sys.stdin);t=r["turn"];e=t["repair"]\n'
      'if t["role"]=="worker":v={"schema_version":1,"replacements":[{"path":"app.py","before_sha256":e["before_hashes"]["app.py"],"text":"def add(a,b):\\n    return a+b\\n"}]}\n'
      'else:v={"schema_version":1,"artifact_digest":e["artifact_digest"],"probe_digest":e["probe_digest"],"verdict":"approve","findings":[]}\n'
      'print(json.dumps({"schema_version":1,"request_digest":r["request_digest"],"action":{"kind":"final","text":json.dumps(v)}}))\n')
    registry=root.parent/'registry.json';registry.write_text(json.dumps({'schema_version':1,'participants':{n:{'adapter':'command','command':[sys.executable,'-I',str(peer)],'timeout':10,'tools':[],'max_turns':1,'max_tool_calls':0} for n in ('worker','reviewer')}}))
    probe=root.parent/'probe.json';probe.write_text(json.dumps(plan['probe']))
    task=root.parent/'cli-task'
    assert main(['fix','--goal','Repair addition','--project',str(root.parent),'--config',str(registry),
        '--checkout',str(root),'--scope','app.py','--probe',str(probe),'--criteria','2+3=5',
        '--worker','worker','--reviewer','reviewer','--task-dir',str(task),'--accept','--allow-external','--pause-after','3'])==1
    paused=json.loads(capsys.readouterr().out);assert paused['status']=='paused',paused
    assert main(['resume',str(task)])==0
    done=json.loads(capsys.readouterr().out);assert done['execution']['integration']['acceptance_status']=='verified_within_probe_scope'


def test_native_repair_transport_stays_read_only(effect_case,monkeypatch):
    from attune_harness import review_participants
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    config={'schema_version':1,'participants':{'worker':{'adapter':'codex','model':'fixture-model','timeout':10,'tools':[],'max_turns':1,'max_tool_calls':0}}}
    directory=prepare(effect_case,review='none',config=config)
    calls=[]
    def runner(argv,prompt,**kwargs):
        assert argv[argv.index('--sandbox')+1]=='read-only'
        task=json.loads(prompt.split('\n',1)[1])['attempt']['task']
        packet=json.loads(task['objective']);calls.append(packet)
        action=proposal(packet)
        action_reply=json.dumps({'schema_version':1,'request_digest':packet['request_digest'],'action':action})
        output='\n'.join(json.dumps(e) for e in [
            {'type':'thread.started','thread_id':'fixture'}, {'type':'turn.started'},
            {'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'text':action_reply})}},
            {'type':'turn.completed','usage':{}}])
        return ProcessResult(argv,0,output,'')
    monkeypatch.setattr(review_participants,'NativeExchange',lambda name,**kw:NativeExchange(name,runner=runner,**kw))
    r=execute_task(directory)
    assert r['status']=='completed',r['execution'].get('error')
    assert len(calls)==1


def test_reviewer_side_effect_invalidates_acceptance(effect_case):
    directory=prepare(effect_case)
    def malicious(packet):
        if packet['turn']['role']=='reviewer':(effect_case[0]/'probe.py').write_text('print("cheat")')
        return proposal(packet)
    result=execute_task(directory,exchange_factory=scripted(malicious))
    assert result['status']=='unresolved'
    assert 'integration' not in result['execution']


def test_lost_probe_ack_blocks_automatic_retry(effect_case,monkeypatch):
    directory=prepare(effect_case,review='none')
    original=RunStore.save
    def fail(store,record):
        if any(e['kind']=='acceptance_probe' and e['state']=='completed' for e in record.get('execution',{}).get('events',[])):
            raise PersistenceError('probe acknowledgement lost')
        original(store,record)
    with monkeypatch.context() as m:
        m.setattr(RunStore,'save',fail)
        with pytest.raises(PersistenceError):execute_task(directory,exchange_factory=scripted(lambda _:pytest.fail('worker after lost probe')))
    event=read_task(directory)['execution']['events'][0]
    with pytest.raises(UnresolvedOperation):execute_task(directory)
    with pytest.raises(UnresolvedOperation):control_task(directory,'reconcile',event_id=event['event_id'],retry_read_only=True)
    with pytest.raises(ValueError):control_task(directory,'reconcile',event_id=event['event_id'],observe_file=True)


def test_noop_worker_result_never_writes(effect_case):
    directory=prepare(effect_case,review='none')
    def no_change(packet):
        a=proposal(packet);v=json.loads(a['text']);v['replacements'][0]['text']=packet['turn']['repair']['before_files']['app.py']
        a['text']=json.dumps(v);return a
    result=execute_task(directory,exchange_factory=scripted(no_change))
    assert result['status']=='failed'
    assert 'No-op' in result['execution']['error']['detail']
    assert not any(e['kind']=='replacement' for e in result['execution']['events'])
