"""Offline behavior and boundary tests; never dispatch real models."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
import sorter
import run as runner
import transport

CASES={c['id']:c for c in runner.data()['cases']}


def answer(id):
    case=CASES[id];facts=deepcopy(case['input']['record']['facts'])
    operation=case['expected']['operation'];outcome=case['expected']['outcome']
    if id=='capture':
        facts=[dict(id='new-1',text='Put the runnable command before the explanation.',scope='cedar',kind='preference',source_ids=['S1'])]
    elif id=='condition': facts[0].update(text='Use Alder for ordinary jobs only when its audit trail is equivalent.',source_ids=['S3'])
    elif id=='consolidate': facts=[facts[0],facts[2]];facts[0]['source_ids']=['S1','S2']
    elif id=='forget': facts=facts[1:]
    elif id=='classify': facts[0]['kind']='lesson'
    elif id=='chronology': facts[0].update(text='Review every Thursday.',source_ids=['S2'])
    elif id=='calculation':
        facts[0].update(text='North limit is 11.',source_ids=['S1','S2','S4','S5'])
        facts[1].update(text='South limit is 8.',source_ids=['S1','S3'])
    if outcome.startswith('needs_'): facts=[]
    return dict(operation=operation,outcome=outcome,facts=facts,reason='Fixture rationale',
                evidence_ids=[case['input']['sources'][-1]['id']],request='Specific unresolved need' if outcome.startswith('needs_') else '')


@pytest.mark.parametrize('id',list(CASES))
def test_valid_operations_create_only_candidates(id):
    case=deepcopy(CASES[id]);before=deepcopy(case)
    candidate=sorter.normalize(sorter.capture(case),answer(id),case['input'])
    assert case==before
    assert candidate['version']==21+(case['expected']['outcome']=='update')


@pytest.mark.parametrize('field',['record','sources','grants','task'])
def test_binding_rejects_changed_current_state(field):
    case=deepcopy(CASES['condition']);bound=sorter.capture(case)
    if field=='record': case['input'][field]['facts'][0]['text']='Concurrent edit'
    elif field=='sources': case['input'][field][0]['text']='Changed evidence'
    elif field=='grants': case['input'][field]['remove_ids']=['regulated']
    else: case['input'][field]='Different request'
    with pytest.raises(sorter.StaleInput): sorter.normalize(bound,answer('condition'),case['input'])


@pytest.mark.parametrize('change',['new_id','remove_id','scope','kind','unknown_source','duplicate','version','operation','empty_text'])
def test_invalid_changes_are_rejected(change):
    case=CASES['condition'];value=answer('condition')
    if change=='new_id': value['facts'].append(dict(value['facts'][0],id='ungranted'))
    elif change=='remove_id': value['facts'].pop()
    elif change=='scope': value['facts'][0]['scope']='global'
    elif change=='kind': value['facts'][0]['kind']='decision'
    elif change=='unknown_source': value['facts'][0]['source_ids']=['missing']
    elif change=='duplicate': value['facts'][1]['id']=value['facts'][0]['id']
    elif change=='version': value['record_version']=22
    elif change=='operation': value['operation']='capture'
    else: value['facts'][0]['text']=''
    with pytest.raises((ValueError,sorter.ValidationError)): sorter.normalize(sorter.capture(case),value,case['input'])


def test_forget_cannot_change_retained_record():
    case=CASES['forget'];value=answer('forget');value['facts'][0]['text']='Edited reminder'
    with pytest.raises(ValueError): sorter.normalize(sorter.capture(case),value,case['input'])


@pytest.mark.parametrize('constraint',['scopes','kinds'])
def test_removing_last_fact_still_checks_target_grants(constraint):
    case=deepcopy(CASES['forget']);case['input']['record']['facts']=case['input']['record']['facts'][:1]
    case['input']['grants'][constraint]=['other'] if constraint=='scopes' else ['preference']
    value=answer('forget');value['facts']=[]
    with pytest.raises(ValueError,match='Removed target'):
        sorter.normalize(sorter.capture(case),value,case['input'])


def test_classify_cannot_rewrite_content():
    case=CASES['classify'];value=answer('classify');value['facts'][0]['text']='Universal guarantee'
    with pytest.raises(ValueError): sorter.normalize(sorter.capture(case),value,case['input'])


@pytest.mark.parametrize('failure',['empty_request','unresolved_facts','completed_request'])
def test_request_and_fact_disposition_consistency(failure):
    id='condition' if failure=='completed_request' else 'absent'
    case=CASES[id];value=answer(id)
    if failure=='empty_request': value['request']=' '
    elif failure=='unresolved_facts': value['facts']=deepcopy(case['input']['record']['facts'])
    else: value['request']='Ask someone anyway'
    with pytest.raises(ValueError): sorter.normalize(sorter.capture(case),value,case['input'])


def test_capture_cannot_also_rewrite_existing_facts():
    case=deepcopy(CASES['condition']);case['input']['grants']['create_ids']=['new-1']
    value=answer('condition');value['operation']='capture'
    value['facts'].append(dict(value['facts'][0],id='new-1'))
    with pytest.raises(ValueError): sorter.normalize(sorter.capture(case),value,case['input'])


@pytest.mark.parametrize('empty',[False,True])
def test_no_change_exact_preview_or_empty(empty):
    case=CASES['distinct'];value=answer('distinct')
    if empty: value['facts']=[]
    assert sorter.normalize(sorter.capture(case),value,case['input'])==case['input']['record']
    value['facts']=deepcopy(case['input']['record']['facts']);value['facts'][0]['source_ids']=['S2']
    with pytest.raises(ValueError): sorter.normalize(sorter.capture(case),value,case['input'])


@pytest.mark.parametrize('id,expected_action',[('absent','await_evidence'),('choice','await_decision'),('assigned','await_decision')])
def test_unresolved_does_not_escalate(id,expected_action):
    calls=[]
    def call(role,model,prompt,schema): calls.append(model);return dict(value=answer(id))
    result=sorter.execute(CASES[id],call)
    assert calls==(['astra'] if id=='assigned' else ['luna'])
    assert result['action']==expected_action and not result['escalated']


@pytest.mark.parametrize('initial',['needs_reasoning','invalid'])
def test_escalation_is_one_hop_with_original_evidence(initial):
    calls=[];case=CASES['calculation']
    def call(role,model,prompt,schema):
        calls.append((role,model,prompt))
        value=answer('calculation')
        if len(calls)==1:
            value.update(outcome='needs_reasoning',facts=[],request='Reconcile formula and exception')
            if initial=='invalid': value['record_version']=22
        return dict(value=value)
    result=sorter.execute(case,call)
    assert [x[1] for x in calls]==['luna','astra'] and result['action']=='proposal_ready'
    assert calls[1][2]['sources']==case['input']['sources'] and 'previous_attempt' in calls[1][2]


def test_stronger_unresolved_does_not_bounce():
    calls=[];value=answer('calculation');value.update(outcome='needs_reasoning',facts=[],request='Check reasoning')
    def call(*args): calls.append(args);return dict(value=value)
    assert sorter.execute(CASES['calculation'],call)['action']=='unresolved_reasoning'
    assert len(calls)==2


def test_inflight_stale_stops_without_escalation():
    case=deepcopy(CASES['condition']);calls=[]
    def call(*args):
        calls.append(args);case['input']['grants']['remove_ids']=['ordinary'];return dict(value=answer('condition'))
    assert sorter.execute(case,call)['action']=='stale_stop' and len(calls)==1


@pytest.mark.parametrize('verdict',['supported','unsupported','uncertain','malformed'])
def test_audit_gates_even_no_change(verdict):
    case=CASES['untrusted'];result=sorter.execute(case,lambda *args:dict(value=answer('untrusted')))
    def call(*args):return dict(value=dict(verdict=verdict,reason='Fixture',evidence_ids=['S1']))
    sorter.audit(case,result,call)
    assert result['action']==('complete_no_change' if verdict=='supported' else 'quarantined')


def test_audit_rechecks_current_grants():
    case=deepcopy(CASES['forget']);result=sorter.execute(case,lambda *args:dict(value=answer('forget')))
    def call(*args):
        case['input']['grants']['remove_ids']=[]
        return dict(value=dict(verdict='supported',reason='Fixture',evidence_ids=['S3']))
    sorter.audit(case,result,call)
    assert result['action']=='stale_stop'


def test_injected_semantic_errors_pass_structure_and_labels_are_private():
    for control in runner.data()['controls']:
        case=CASES[control['case_id']];bound=sorter.capture(case)
        assert sorter.assess(bound,dict(value=control['proposal']),case['input'])['accepted']
        p=sorter.audit_prompt(bound,control['proposal'])
        assert 'expected' not in p and 'rubric' not in p and 'assigned_model' not in p['grants']
        assert 'control_id' not in p and 'id' not in p
    for case in CASES.values():
        p=sorter.prompt(sorter.capture(case));assert 'expected' not in p and 'rubric' not in p


def packet():
    return dict(models=sorter.previous.MODELS,order=runner.schedule(),sampled=list(runner.SAMPLED),
                max_native_calls=33,campaign_timeout=1800,per_call_timeout=180)


def output(kind='valid'):
    events=[dict(type='item.completed',item=dict(type='agent_message',text='{}')),
            dict(type='turn.completed',usage=dict(input_tokens=2,output_tokens=1))]
    if kind=='tool':events.insert(0,dict(type='item.completed',item=dict(type='command_execution')))
    if kind=='usage':events[-1]['usage']={}
    if kind=='ambiguous':events.insert(0,dict(type='item.completed',item=dict(type='agent_message',text='{"a":1}')))
    return SimpleNamespace(stdout='\n'.join(json.dumps(e) for e in events),stderr='',returncode=0,failure=None)


@pytest.mark.parametrize('failure',['process','tool','usage','ambiguous','exception'])
def test_native_failure_stops_before_next_dispatch(tmp_path,monkeypatch,failure):
    calls=[]
    def invoke(*args,**kwargs):
        calls.append(args)
        if failure=='exception':raise OSError('fixture')
        result=output(failure)
        if failure=='process':result.returncode=1;result.failure='nonzero_exit'
        return result
    monkeypatch.setattr(transport,'invoke',invoke);trial=runner.Campaign(packet(),tmp_path)
    with pytest.raises(RuntimeError):trial.run()
    assert len(calls)==1 and trial.ledger['status']=='stopped'
    with pytest.raises(FileExistsError):runner.Campaign(packet(),tmp_path)


@pytest.mark.parametrize('remaining',[0,1])
def test_deadline_bounds_current_call(tmp_path,monkeypatch,remaining):
    now=[0.0];monkeypatch.setattr(transport,'time',SimpleNamespace(monotonic=lambda:now[0]))
    trial=runner.Campaign(packet(),tmp_path);now[0]=1800-remaining;calls=[]
    def invoke(*args,**kwargs):calls.append(kwargs['timeout']);return output()
    monkeypatch.setattr(transport,'invoke',invoke)
    if remaining:
        trial.call('test','worker','luna',{},sorter.SCHEMA);assert calls==[1]
    else:
        with pytest.raises(RuntimeError):trial.call('test','worker','luna',{},sorter.SCHEMA)
        assert not calls


def test_cap_and_schedule(tmp_path,monkeypatch):
    trial=runner.Campaign(packet(),tmp_path);trial.ledger['attempts']=[{}]*33
    monkeypatch.setattr(transport,'invoke',lambda *a,**k:pytest.fail('Must not dispatch'))
    with pytest.raises(RuntimeError):trial.call('test','worker','luna',{},sorter.SCHEMA)
    schedule=runner.schedule()
    assert len(schedule)==19
    assert [sum(x['arm']==arm for x in schedule) for arm in ('queue','direct','control')]==[12,3,4]
