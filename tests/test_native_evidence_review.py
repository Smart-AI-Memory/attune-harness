"""Native evidence policy uses real host tools and a deterministic native peer."""
import copy
import json

import pytest

from test_review import case, change, change_config
from test_astra_review import as_astra
from attune_harness import review_participants
from attune_harness.native import NativeExchange
from attune_harness.process import ProcessResult
from attune_harness.review import review
from attune_harness.recovery import resume_review
from attune_harness.review_contract import accept_request, canonical, digest, load_registry
from attune_harness.review_participants import ReviewExchange, evidence_step


def configure(data):
    as_astra(data)
    for item in data['participants'].values(): item['review_mode'] = 'evidence'


def install_peer(monkeypatch, calls, text='The reference link exists; policy judgments remain unverified.'):
    def runner(argv, prompt, **kwargs):
        calls.append((argv, prompt))
        assert argv[argv.index('--model')+1] == 'gpt-6-astra'
        assert 'model_reasoning_effort="xhigh"' in argv
        task = json.loads(prompt.split('\n', 1)[1])['attempt']['task']
        evidence = json.loads(task['objective'])
        assert set(evidence) == {'objective', 'document', 'references', 'limited_tool_checks', 'judgment_scope'}
        assert [r['path'] for r in evidence['references']] == ['reference.md']
        assert evidence['references'][0]['text'] == 'Quartz retention policy is a test fixture.'
        assert 'request_digest' not in evidence and 'protocol' not in evidence
        assert evidence['limited_tool_checks'][0]['semantic_ran'] is False
        assert 'Do not return an action' in task['requirements'][0]
        output = text if isinstance(text, str) else text[len(calls)-1]
        raw = '\n'.join(json.dumps(e) for e in [
            {'type':'thread.started','thread_id':'native-evidence-fixture'}, {'type':'turn.started'},
            {'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'text':output})}},
            {'type':'turn.completed','usage':{}},
        ])
        return ProcessResult(argv,0,raw,'')
    monkeypatch.setattr(review_participants,'NativeExchange',lambda name,**kwargs:NativeExchange(name,**kwargs,runner=runner))


def test_real_tools_then_one_native_call_per_role_with_host_correlation(case, monkeypatch):
    change_config(case, configure)
    calls=[];install_peer(monkeypatch,calls)
    result=review(*case,allow_external=True)
    assert result['status']=='completed',result.get('error')
    assert len(calls)==2
    for role,item in result['participants'].items():
        assert item['tool_calls']==2 and item['status']=='completed'
        assert item['text'].startswith('Native model review (unverified proposal):')
        assert item['last_identity']['review_mode']=='evidence'
        assert item['last_identity']['requested_reasoning_effort']=='xhigh'
    host_steps=[e for e in result['events'] if e.get('result',{}).get('identity',{}).get('adapter')=='host-evidence']
    assert len(host_steps)==4
    assert [e['result']['action']['name'] for e in host_steps]==['retrieve','verify','retrieve','verify']
    replay=resume_review(case[2],case[0],case[1],result['checkpoint_digest'],allow_external=True)
    assert canonical(replay)==canonical(result) and len(calls)==2


@pytest.mark.parametrize('text',['', 'Findings:', 'x'*32750])
def test_empty_unfinished_or_oversized_review_fails_without_retry(case,monkeypatch,text):
    change_config(case,configure)
    calls=[];install_peer(monkeypatch,calls,text)
    result=review(*case,allow_external=True)
    assert result['status']=='failed'
    assert len(calls)==1
    expected = 'output text' if text == '' else 'substantive account' if text == 'Findings:' else 'final text'
    assert expected in result['error']['detail']
    assert result['participants']['lead']['tool_calls']==2
    assert 'reviewer' not in result['participants']


@pytest.mark.parametrize('field,value',[('review_mode','bad'),('review_mode',None),('tools',['verify','retrieve']),('tools',['retrieve']),('max_turns',2),('max_tool_calls',1)])
def test_invalid_evidence_configuration_fails_before_dispatch(case,field,value):
    change_config(case,configure)
    change(case[1],lambda d:d['participants']['alpha'].update({field:value}))
    with pytest.raises(ValueError):load_registry(case[1])


def request():
    turn={'tools':['retrieve','verify'],'history':[],'query':'quartz','remaining_tool_calls':2,'remaining_turns':3}
    return {'schema_version':1,'request_digest':digest(turn),'turn':turn}


@pytest.mark.parametrize('kind',['digest','history_order','history_operation','tool_budget','turn_budget','version'])
def test_tampered_turn_or_inadequate_budget_cannot_dispatch(kind):
    wire=request()
    if kind=='digest':wire['request_digest']='shortened...'
    elif kind=='version':wire['schema_version']=True
    else:
        turn=wire['turn']
        if kind=='history_order':turn['history']=[{'action':{'name':'verify'},'result':{'operation':'verify'}}]
        if kind=='history_operation':turn['history']=[{'action':{'name':'retrieve'},'result':{'operation':'verify'}}]
        if kind=='tool_budget':turn['remaining_tool_calls']=1
        if kind=='turn_budget':turn['remaining_turns']=2
        wire['request_digest']=digest(turn)
    with pytest.raises(ValueError):evidence_step(wire)


def test_mode_change_invalidates_acceptance_and_paused_continuation(case):
    change_config(case,as_astra)
    change(case[1],lambda d:d['participants']['alpha'].update(review_mode='evidence'))
    with pytest.raises(ValueError,match='Stale form revision'):accept_request(case[0],load_registry(case[1]))
    change_config(case,configure)
    paused=review(*case,allow_external=True,max_operations=3)
    assert paused['status']=='paused'
    before=(case[2]/'record.json').read_bytes()
    change_config(case,lambda d:d['participants']['alpha'].pop('review_mode'))
    with pytest.raises(ValueError):
        resume_review(case[2],case[0],case[1],paused['checkpoint_digest'],allow_external=True,
                      exchange_factory=lambda *_:pytest.fail('changed mode dispatched'))
    assert (case[2]/'record.json').read_bytes()==before


def test_self_reference_only_is_rejected_before_model(case,monkeypatch):
    change_config(case,configure)
    (case[0].parent/'project/reference.md').unlink()
    monkeypatch.setattr(review_participants,'NativeExchange',lambda *_a,**_k:pytest.fail('self-corroboration dispatched'))
    result=review(*case,allow_external=True)
    assert result['status']=='failed'
    assert 'distinct retrieved reference' in result['error']['detail']
