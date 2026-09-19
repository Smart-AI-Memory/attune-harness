"""Offline controls and replay of preserved failures; no model dispatch."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator
from baseline import old
import citation_contract as contract
import run_citations as runner

CASES = {c['id']: c for c in runner.data()}


def answer(id):
    case = CASES[id]
    facts = deepcopy(case['input']['record']['facts'])
    refs = [s['id'] for s in case['input']['sources']]
    request = ''
    if id == 'capture':
        facts = [dict(id='new-7', text='State the outcome first.', scope='cedar', kind='preference', source_ids=['P10'])]
    elif id == 'condition':
        facts[0].update(text='Prefer Willow for ordinary runs only if execution logs are retained.', source_ids=['P22'])
    elif id == 'consolidate':
        facts.pop(1)
        facts[0]['source_ids'] = ['P40', 'P41']
    elif id == 'forget_all':
        facts = []
        refs = ['P52']
    elif id == 'kind':
        facts[0]['kind'] = 'lesson'
        refs = ['P61']
    elif id in ('absent', 'choice'):
        facts = []
        refs = ['P71' if id == 'absent' else 'P81']
        request = 'Supply decision-bundle-m2.' if id == 'absent' else 'Choose Ash or Fir.'
    return dict(operation=case['expected']['operation'], outcome=case['expected']['outcome'],
                facts=facts, reason='Synthetic offline fixture.', evidence_ids=refs, request=request)


def mock_call(values, calls):
    def call(role, model, prompt, schema):
        calls.append(dict(role=role, model=model, prompt=prompt, schema=schema))
        return dict(value=deepcopy(values[len(calls)-1]))
    return call


@pytest.mark.parametrize('id', CASES)
def test_valid_outputs_and_prompt_schema_identity(id):
    case = CASES[id]
    calls = []
    original = deepcopy(old.SCHEMA)
    result = contract.execute(case, 'repaired', mock_call([answer(id)], calls))
    assert result['first']['accepted'] and not result['escalated']
    assert calls[0]['schema'] == calls[0]['prompt']['schema']
    assert 'expected' not in calls[0]['prompt'] and 'rubric' not in calls[0]['prompt']
    assert 'assigned_model' not in calls[0]['prompt']['grants']
    assert old.SCHEMA == original
    assert result['final']['candidate']['version'] == (32 if case['expected']['outcome']=='update' else 31)


def test_original_failures_rejected_without_rewriting():
    rows = json.loads((runner.HERE / 'regressions.json').read_text())
    assert len(rows) == 11 and sum(r['was_accepted'] for r in rows) == 1
    for row in rows:
        value = deepcopy(row['response'])
        assert Draft202012Validator(old.SCHEMA).is_valid(value)
        assert Draft202012Validator(contract.schema_for(row['binding'])).is_valid(value) == row['was_accepted']
        assert value == row['response']


@pytest.mark.parametrize('field', ['evidence_ids', 'source_ids'])
@pytest.mark.parametrize('refs', [[], ['unknown'], ['P10', 'P10']])
def test_bad_references_rejected(field, refs):
    value = answer('capture')
    target = value if field == 'evidence_ids' else value['facts'][0]
    target[field] = refs
    bound = old.capture(CASES['capture'])
    assessment = contract.assess(bound, dict(value=value), bound, 'repaired')
    assert not assessment['accepted']
    if len(refs) == 2:
        assert Draft202012Validator(contract.schema_for(bound)).is_valid(value)  # Host owns uniqueness.
    else:
        assert not Draft202012Validator(contract.schema_for(bound)).is_valid(value)


def test_valid_but_irrelevant_reference_needs_semantic_grading():
    bound = old.capture(CASES['forget_all'])
    value = answer('forget_all')
    value['evidence_ids'] = ['P50']  # Content provenance does not support requested forgetting.
    assert contract.assess(bound, dict(value=value), bound, 'repaired')['accepted']
    assert 'P52' not in value['evidence_ids']


@pytest.mark.parametrize('change', ['scope', 'kind', 'remove', 'classify', 'source_scope'])
def test_old_authority_controls_still_enforced(change):
    id = 'kind' if change == 'classify' else 'forget_all' if change in ('scope','kind','remove') else 'capture'
    case = deepcopy(CASES[id])
    bound = case['input']
    value = answer(id)
    if change == 'scope': bound['grants']['scopes'] = ['elsewhere']
    elif change == 'kind': bound['grants']['kinds'] = ['decision']
    elif change == 'remove': bound['grants']['remove_ids'] = []
    elif change == 'classify': bound['grants']['classify_ids'] = []
    else: bound['sources'][0]['scope'] = 'elsewhere'
    assert not contract.assess(bound, dict(value=value), bound, 'repaired')['accepted']


@pytest.mark.parametrize('sources', [[], [{'id':'a'}]*2, [{'id':[]}], [{'id':' '}], [{'id':str(i)} for i in range(9)]])
@pytest.mark.parametrize('arm', ['legacy','repaired'])
def test_invalid_source_packet_stops_before_any_call(sources, arm):
    cases = runner.data()
    cases[-1]['input']['sources'] = sources
    def forbidden(*args): pytest.fail('Must not dispatch')
    with pytest.raises(ValueError): contract.execute(cases[-1], arm, forbidden)
    with pytest.raises(ValueError): runner.Campaign(packet(), '/nonexistent', cases)


@pytest.mark.parametrize('field', ['record','sources','grants','task'])
def test_stale_state_stops_without_escalation(field):
    case = deepcopy(CASES['capture'])
    current = deepcopy(case['input'])
    current[field] = {} if field != 'task' else 'new task'
    calls = []
    result = contract.execute(case, 'repaired', mock_call([answer('capture')], calls), lambda:current)
    assert result['action']=='stale_stop' and len(calls)==1


@pytest.mark.parametrize('failure', ['contract','reasoning'])
def test_one_hop_escalation_keeps_original_evidence(failure):
    value = answer('capture')
    if failure == 'contract': value['evidence_ids']=[]
    else: value.update(outcome='needs_reasoning',facts=[],request='Reason about the evidence.')
    calls=[]
    result=contract.execute(CASES['capture'],'repaired',mock_call([value,value],calls))
    assert result['escalated'] and len(calls)==2
    assert [c['model'] for c in calls]==['luna','astra']
    assert calls[1]['prompt']['sources']==CASES['capture']['input']['sources']
    assert calls[1]['schema']==calls[0]['schema']==calls[1]['prompt']['schema']
    assert result['action']==('rejected' if failure=='contract' else 'unresolved_reasoning')


@pytest.mark.parametrize('verdict', ['supported','unsupported','uncertain','malformed','stale'])
def test_audit_schema_and_fail_closed(verdict):
    case=CASES['condition'];calls=[]
    result=contract.execute(case,'repaired',mock_call([answer('condition')],[]))
    value=dict(verdict=verdict if verdict in ('supported','unsupported','uncertain') else 'supported',
               reason='Fixture',evidence_ids=[] if verdict=='malformed' else ['P21','P22'])
    currents=iter([case['input'],{} if verdict=='stale' else case['input']])
    audit=contract.audit(case,result,mock_call([value],calls),lambda:next(currents))
    assert calls[0]['schema']==calls[0]['prompt']['schema']
    assert 'verdict' in calls[0]['prompt']['citation_contract']
    assert all(word not in calls[0]['prompt']['citation_contract'] for word in ('outcome','request','source_ids'))
    assert result['action']==('stale_stop' if verdict=='stale' else 'proposal_ready' if verdict=='supported' else 'quarantined')
    assert audit['response']==value


def packet():
    return dict(models=old.previous.MODELS, order=runner.schedule(runner.data()),sampled=['condition-repaired'],
                max_native_calls=33,campaign_timeout=1800,per_call_timeout=180)


def test_whole_campaign_schedule_and_rerun_guard(tmp_path):
    trial=runner.Campaign(packet(),tmp_path)
    calls=[]
    def call(id,role,model,prompt,schema):
        calls.append((id,role,model))
        if role=='audit': return dict(value=dict(verdict='supported',reason='Fixture',evidence_ids=['P21','P22']))
        return dict(value=answer(id.rsplit('-',1)[0]))
    trial.call=call
    trial.run()
    assert trial.ledger['status']=='completed' and len(calls)==17
    assert len(trial.ledger['jobs'])==16
    assert [c for c in calls if c[1]=='audit']==[('condition-repaired','audit','astra')]
    with pytest.raises(FileExistsError): runner.Campaign(packet(),tmp_path)
    path=tmp_path/'packet.json';path.write_text(json.dumps(packet()))
    runner.verify_frozen(packet(),path)
    changed=packet();changed['max_native_calls']=34
    with pytest.raises(ValueError):runner.verify_frozen(changed,path)
