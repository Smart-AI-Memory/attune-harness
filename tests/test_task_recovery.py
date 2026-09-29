"""Task continuation through real effects, shared controls, and injected storage faults."""
import copy
import json
import shutil

import pytest

from attune_harness.cli import main
from attune_harness.recovery import UnresolvedOperation
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import RunStore, PersistenceError
from attune_harness.task_contract import accept_task, read_task, revise_task
from attune_harness.task_policies import execute_task, inspect_task, control_task
from test_review import case, change, scripted
from test_task_contract import draft, response


@pytest.mark.parametrize('plan,boundary', [('solo',i) for i in range(1,5)]+[('independent-review',i) for i in range(1,6)])
def test_each_boundary_replays_without_repeating_operations(case,plan,boundary):
    draft(case,plan=plan);accept_task(case[2],response(case[2]))
    calls=[]
    def factory(config,cwd):
        real=ReviewExchange(config,cwd)
        def call(raw):
            calls.append(json.loads(raw)['request_digest']);return real(raw)
        return call
    paused=execute_task(case[2],max_operations=boundary,exchange_factory=factory)
    assert paused['status']=='paused'
    prior=copy.deepcopy(paused['execution']['events'])
    done=execute_task(case[2],checkpoint=paused['checkpoint_digest'],exchange_factory=factory)
    assert done['status']=='completed'
    assert done['execution']['events'][:boundary]==prior
    assert len(calls)==(1 if plan=='solo' else 2)
    raw=(case[2]/'record.json').read_bytes()
    assert execute_task(case[2],exchange_factory=lambda *_:pytest.fail('replayed completion'))==done
    assert (case[2]/'record.json').read_bytes()==raw


def lost_ack(case,monkeypatch):
    draft(case);accept_task(case[2],response(case[2]))
    original=RunStore.save
    def save(store,record):
        if any(e['kind']=='participant_turn' and e['state']=='completed' for e in record.get('execution',{}).get('events',[])):
            raise PersistenceError('lost acknowledgement')
        return original(store,record)
    with monkeypatch.context() as m:
        m.setattr(RunStore,'save',save)
        with pytest.raises(PersistenceError):
            execute_task(case[2],exchange_factory=scripted({'kind':'final','text':'Recovered assessment'}))
    persisted=read_task(case[2]);event=persisted['execution']['events'][-1]
    assert event['phase']=='dispatching' and event['state']=='pending'
    return persisted,event


def test_lost_ack_blocks_retry_and_matching_recovered_reply_resumes(case,monkeypatch):
    persisted,event=lost_ack(case,monkeypatch)
    raw=(case[2]/'record.json').read_bytes()
    assert inspect_task(case[2])['status']=='unresolved'
    with pytest.raises(UnresolvedOperation):execute_task(case[2])
    with pytest.raises(UnresolvedOperation):
        control_task(case[2],'reconcile',event_id=event['event_id'],retry_read_only=True)
    assert (case[2]/'record.json').read_bytes()==raw
    reply=case[0].parent/'reply.json'
    reply.write_text(json.dumps({'schema_version':1,'request_digest':event['request_digest'],'action':{'kind':'final','text':'Recovered assessment'}}))
    r=control_task(case[2],'reconcile',checkpoint=persisted['checkpoint_digest'],event_id=event['event_id'],reply_file=reply)
    done=execute_task(case[2],exchange_factory=scripted(lambda _:pytest.fail('duplicate dispatch')))
    assert done['status']=='completed'
    assert done['execution']['participants']['assessor']['text']=='Recovered assessment'
    assert 'not authenticated' in r['execution']['recovery']['reconciliations'][0]['evidence']['identity']


def test_cancellation_preserves_uncertain_effects_and_terminal_precedence(case,monkeypatch):
    _,event=lost_ack(case,monkeypatch)
    r=control_task(case[2],'cancel',reason='Stop this run')
    assert r['status']=='cancelled'
    assert r['execution']['events'][-1]==event
    raw=(case[2]/'record.json').read_bytes()
    assert control_task(case[2],'cancel',reason='Again')==r
    assert (case[2]/'record.json').read_bytes()==raw
    with pytest.raises(ValueError):execute_task(case[2])


def test_completed_cancel_does_not_mutate(case):
    draft(case);accept_task(case[2],response(case[2]));done=execute_task(case[2])
    assert control_task(case[2],'cancel',reason='Too late')==done


def test_transfer_retains_old_attempt_and_isolates_reviewer(case):
    change(case[1],lambda d:d['participants'].update(gamma=copy.deepcopy(d['participants']['alpha'])))
    draft(case,plan='independent-review');accept_task(case[2],response(case[2]))
    r=execute_task(case[2],max_operations=3)
    original=copy.deepcopy(r['execution']['events'])
    moved=control_task(case[2],'transfer',participant_id='gamma',reason='Fresh assessment')
    assert moved==read_task(case[2])
    seen=[]
    result=execute_task(case[2],exchange_factory=scripted({'kind':'final','text':'New assessment'},lambda p:seen.append(p)))
    assert result['status']=='completed',result
    assert result['execution']['events'][:3]==original
    assert result['execution']['participants']['assessor']['participant_id']=='gamma'
    assert len(seen)==2
    assert all('Deterministic demonstration' not in json.dumps(p) for p in seen)


@pytest.mark.parametrize('boundary,identity',[(2,'beta'),(4,'gamma')])
def test_invalid_transfer_refused(case,boundary,identity):
    change(case[1],lambda d:d['participants'].update(gamma=copy.deepcopy(d['participants']['alpha'])))
    draft(case,plan='independent-review');accept_task(case[2],response(case[2]))
    execute_task(case[2],max_operations=boundary)
    with pytest.raises(ValueError):control_task(case[2],'transfer',participant_id=identity,reason='Invalid')


def test_stale_copied_busy_or_changed_inputs_cannot_resume(case):
    draft(case);accept_task(case[2],response(case[2]));p=execute_task(case[2],max_operations=2)
    with pytest.raises(ValueError,match='checkpoint'):execute_task(case[2],checkpoint='stale')
    copied=case[2].with_name('copy');shutil.copytree(case[2],copied)
    with pytest.raises(ValueError,match='Copied'):execute_task(copied)
    with RunStore(case[2],existing=True).lease():
        with pytest.raises(PersistenceError,match='busy'):execute_task(case[2])
    with pytest.raises(ValueError,match='Executed'):revise_task(case[2],checkpoint=p['checkpoint_digest'])
    (case[0].parent/'project/reference.md').write_text('changed')
    with pytest.raises(ValueError,match='Stale'):execute_task(case[2])


def test_primary_status_resume_and_legacy_status(case,capsys):
    draft(case);accept_task(case[2],response(case[2]));execute_task(case[2],max_operations=2)
    assert main(['status',str(case[2])])==0
    assert json.loads(capsys.readouterr().out)['status']=='paused'
    assert main(['resume',str(case[2])])==0
    assert json.loads(capsys.readouterr().out)['status']=='completed'
    from attune_harness.review import review
    legacy=case[2].with_name('legacy');review(case[0],case[1],legacy)
    assert main(['status',str(legacy)])==0
    assert json.loads(capsys.readouterr().out)['operation']=='review'


def test_read_only_retry_is_explicit_and_bounded(case,monkeypatch):
    from attune_harness import retrieval
    draft(case);accept_task(case[2],response(case[2]))
    with monkeypatch.context() as m:
        m.setattr(retrieval,'retrieve_sources',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('read failed')))
        failed=execute_task(case[2])
    event=failed['execution']['events'][-1]
    assert event['effect_class']=='read_only'
    with pytest.raises(UnresolvedOperation):execute_task(case[2])
    control_task(case[2],'reconcile',event_id=event['event_id'],retry_read_only=True)
    done=execute_task(case[2]);assert done['status']=='completed'
    assert done['execution']['events'][1]['attempts']==2


def test_foreign_recovered_reply_does_not_mutate(case,monkeypatch):
    before,event=lost_ack(case,monkeypatch)
    reply=case[0].parent/'foreign.json'
    reply.write_text(json.dumps({'schema_version':1,'request_digest':'different assignment','action':{'kind':'final','text':'OK'}}))
    with pytest.raises(ValueError,match='current turn'):
        control_task(case[2],'reconcile',event_id=event['event_id'],reply_file=reply)
    assert read_task(case[2])==before


def refusing(envelope, calls):
    """Refuse the reviewer turn the way the Claude CLI does, through the real translator."""
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    def factory(config, cwd):
        real = ReviewExchange(config, cwd)
        def call(raw):
            calls.append(json.loads(raw)['turn']['role'])
            if json.loads(raw)['turn']['role'] == 'reviewer' and envelope is not None:
                runner = lambda argv, prompt, **_: ProcessResult(argv, 1, json.dumps(envelope), '', None)
                NativeExchange('claude', cwd=cwd, runner=runner)(json.dumps({'version': 1}))
            return real(raw)
        return call
    return factory


REFUSAL = {'type': 'result', 'subtype': 'success', 'is_error': True, 'num_turns': 1,
           'result': "You're out of usage credits.", 'total_cost_usd': 0, 'modelUsage': {}}


def test_structured_cli_refusal_authorizes_one_retry_that_keeps_completed_turns(case):
    draft(case, plan='independent-review'); accept_task(case[2], response(case[2]))
    calls = []
    failed = execute_task(case[2], exchange_factory=refusing(REFUSAL, calls))
    assert failed['status'] == 'failed' and calls == ['assessor', 'reviewer']
    event = failed['execution']['events'][-1]
    assert event['state'] == 'failed' and event['effects'] == 'unknown'
    assert event['native_refusal'] == {'kind': 'claude_structured_error', 'returncode': 1,
                                       'result': "You're out of usage credits.", 'model_usage': {}}
    with pytest.raises(UnresolvedOperation):
        control_task(case[2], 'reconcile', event_id=event['event_id'], retry_read_only=True)
    paused = control_task(case[2], 'reconcile', event_id=event['event_id'], retry_refused=True)
    assert paused['execution']['status'] == 'paused'
    evidence = paused['execution']['recovery']['reconciliations'][-1]['evidence']
    assert evidence['kind'] == 'native_refusal_retry' and evidence['refusal'] == event['native_refusal']
    calls.clear()
    done = execute_task(case[2], exchange_factory=refusing(None, calls))
    assert done['status'] == 'completed', done
    assert calls == ['reviewer']  # The completed assessor turn is replayed, not paid for again.
    retried = next(e for e in done['execution']['events'] if e['event_id'] == event['event_id'])
    assert retried['state'] == 'completed' and retried['attempts'] == 2


@pytest.mark.parametrize('envelope', [
    {k: v for k, v in REFUSAL.items() if k != 'modelUsage'},
    {**REFUSAL, 'modelUsage': {'claude-sonnet-5': {}}},
    {**REFUSAL, 'is_error': False},
])
def test_refusal_without_structured_no_usage_evidence_stays_unresolved(case, envelope):
    draft(case, plan='independent-review'); accept_task(case[2], response(case[2]))
    assert execute_task(case[2], exchange_factory=refusing(envelope, []))['status'] == 'failed'
    event = read_task(case[2])['execution']['events'][-1]
    assert 'native_refusal' not in event
    raw = (case[2] / 'record.json').read_bytes()
    with pytest.raises(UnresolvedOperation, match='structured CLI refusal'):
        control_task(case[2], 'reconcile', event_id=event['event_id'], retry_refused=True)
    assert (case[2] / 'record.json').read_bytes() == raw
    assert control_task(case[2], 'cancel', reason='Close the record honestly')['status'] == 'cancelled'


def test_refused_turn_retry_is_limited_to_one(case):
    draft(case, plan='independent-review'); accept_task(case[2], response(case[2]))
    for _ in range(2):
        assert execute_task(case[2], exchange_factory=refusing(REFUSAL, []))['status'] == 'failed'
        event = read_task(case[2])['execution']['events'][-1]
        if event['attempts'] == 1:
            control_task(case[2], 'reconcile', event_id=event['event_id'], retry_refused=True)
    with pytest.raises(ValueError, match='limit exhausted'):
        control_task(case[2], 'reconcile', event_id=event['event_id'], retry_refused=True)
