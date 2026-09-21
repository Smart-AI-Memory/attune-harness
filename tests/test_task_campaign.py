"""Campaign integrity and offline rehearsals never launch a native provider process."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('task_campaign',ROOT/'experiments/task_execution/campaign.py')
campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)


@pytest.fixture
def frozen(tmp_path,monkeypatch):
    from attune_harness import review_participants,voyage_provider
    def poison(*a,**k):pytest.fail('Offline campaign attempted provider construction')
    monkeypatch.setattr(review_participants,'NativeExchange',poison)
    monkeypatch.setattr(voyage_provider,'VoyageProvider',poison)
    wheel=tmp_path/'candidate.whl';wheel.write_bytes(b'fixture artifact; identity check is separately installed-qualified')
    output=tmp_path/'packet';campaign.prepare(output,wheel)
    return output


def test_prepare_is_frozen_complete_and_non_dispatching(frozen):
    protocol=campaign.verify(frozen)
    assert len(protocol['trials'])==60
    assert protocol['max_participant_calls']==92
    assert protocol['estimated_billed_usd'] is None
    assert not (frozen/'runs').exists()
    with pytest.raises(FileExistsError):campaign.prepare(frozen,Path(protocol['candidate_wheel']))


@pytest.mark.parametrize('change',['case','key','settings','wheel'])
def test_modified_packet_or_artifact_is_rejected(frozen,change):
    p=campaign.read(frozen/'protocol.json')
    if change=='wheel':Path(p['candidate_wheel']).write_bytes(b'changed')
    else:
        if change=='case':p['cases'][0]['document']='changed'
        if change=='key':p['cases'][0]['expected']='critical_defect'
        if change=='settings':p['profiles']['codex-lead']['lead']['model']='different'
        campaign.write(frozen/'protocol.json',p)
    with pytest.raises(ValueError):campaign.verify(frozen)


def test_no_spend_without_exact_estimated_admission(frozen):
    p=campaign.verify(frozen);grant=frozen/'grant.json'
    campaign.write(grant,{'protocol_sha256':campaign.digest(p),'approved':False,'max_calls':92,
        'estimated_usd':None,'budget_reviewed':False,'native_profiles_confirmed':False})
    with pytest.raises(ValueError,match='admission'):campaign.execute(frozen,grant)
    assert not (frozen/'runs').exists()


@pytest.mark.parametrize('slice_name,arm',[('assessment','legacy'),('assessment','solo'),('assessment','independent-review'),('repair','direct'),('repair','solo'),('repair','required-review')])
@pytest.mark.parametrize('interrupted',[False,True])
def test_each_arm_uses_real_tools_and_effects_without_native_calls(frozen,slice_name,arm,interrupted):
    p=campaign.verify(frozen)
    case='clean' if slice_name=='assessment' else 'arithmetic'
    next(c for c in p['cases'] if c['id']==case)['interrupt']=interrupted
    trial=next(t for t in p['trials'] if t['case']==case and t['arm']==arm and t['profile']=='codex-lead')
    seen=[]
    def factory(config,cwd):
        def exchange(raw):
            request=json.loads(raw);turn=request['turn'];seen.append(turn)
            if 'repair' not in turn:text='Maple reference supports the supplied statement; interpretation unverified.'
            elif turn['role']=='worker':
                e=turn['repair'];text=json.dumps({'schema_version':1,'replacements':[{'path':'module.py','before_sha256':e['before_hashes']['module.py'],'text':'def compute(a,b):\n    return a+b\n'}]})
            else:
                e=turn['repair'];text=json.dumps({'schema_version':1,'artifact_digest':e['artifact_digest'],'probe_digest':e['probe_digest'],'verdict':'approve','findings':[]})
            return json.dumps({'schema_version':1,'request_digest':request['request_digest'],'action':{'kind':'final','text':text}})
        return exchange
    result=campaign.trial_execution(p,trial,frozen/'offline-arm',factory)
    assert result['status']=='completed',result.get('execution',result).get('error')
    assert len(seen)==trial['max_calls']
    if slice_name=='repair':
        run=result.get('execution',result)
        assert not run['before_probe']['passed'] and run['after_probe']['passed']


def retained(frozen):
    p=campaign.verify(frozen);rows=[];grades=[]
    for trial in p['trials']:
        folder=frozen/'runs'/trial['id'];folder.mkdir(parents=True)
        result={'status':'completed','participants':{'role':{'text':'Fixture narrative'}}}
        campaign.write(folder/'result.json',result)
        rows.append({'trial_id':trial['id'],'state':'completed','result_sha256':campaign.digest(result),'billed_usd':None})
        grades.append({'trial_id':trial['id'],'completed_correct':True,'critical_miss':False,'unsupported_findings':0,'human_correction_seconds':None})
    campaign.write(frozen/'ledger.json',{'protocol_sha256':campaign.digest(p),'trials':rows})
    campaign.write(frozen/'grades.json',grades)
    return grades


def test_unknown_cost_and_human_time_never_become_zero(frozen):
    retained(frozen);result=campaign.audit(frozen,frozen/'grades.json')
    assert result['billed_usd'] is None and result['human_seconds'] is None
    assert result['cost_ranking'].startswith('unqualified')


@pytest.mark.parametrize('fault',['missing-grade','extra-grade','missing-trial','changed-result','critical-miss','lost-correct'])
def test_failure_retention_and_quality_floor(frozen,fault):
    grades=retained(frozen)
    if fault=='missing-grade':grades.pop()
    if fault=='extra-grade':grades.append(copy.deepcopy(grades[0]))
    if fault=='missing-trial':
        ledger=campaign.read(frozen/'ledger.json');ledger['trials'].pop();campaign.write(frozen/'ledger.json',ledger)
    if fault=='changed-result':campaign.write(frozen/'runs'/grades[0]['trial_id']/'result.json',{'status':'changed'})
    if fault in ('critical-miss','lost-correct'):
        row=next(g for g in grades if g['trial_id'].endswith('-solo'))
        row['critical_miss']=fault=='critical-miss';row['completed_correct']=fault!='lost-correct'
    campaign.write(frozen/'grades.json',grades)
    if fault in ('critical-miss','lost-correct'):assert campaign.audit(frozen,frozen/'grades.json')['status']=='revise'
    else:
        with pytest.raises(ValueError):campaign.audit(frozen,frozen/'grades.json')


def test_blind_packet_omits_role_mapping_and_checks_its_integrity(frozen):
    grades=retained(frozen);campaign.blind(frozen)
    packet=campaign.read(frozen/'blind-packet.json');key=campaign.read(frozen/'blind-key.json')
    assert all('trial_id' not in r and 'profile' not in r for r in packet)
    by_id={g['trial_id']:g for g in grades}
    anonymous=[{'blind_id':b,**{k:v for k,v in by_id[t].items() if k!='trial_id'}} for b,t in key['mapping'].items()]
    campaign.write(frozen/'anonymous.json',anonymous)
    assert campaign.audit(frozen,frozen/'anonymous.json')['quality_floor'] is True
    packet[0]['narratives']=['altered'];campaign.write(frozen/'blind-packet.json',packet)
    with pytest.raises(ValueError):campaign.audit(frozen,frozen/'anonymous.json')


def test_failed_initial_campaign_journal_never_dispatches(frozen,monkeypatch):
    p=campaign.verify(frozen);grant=frozen/'test-grant.json'
    campaign.write(grant,{'protocol_sha256':campaign.digest(p),'approved':True,'max_calls':92,
        'estimated_usd':0,'budget_reviewed':True,'native_profiles_confirmed':True})
    def fail(*a,**k):raise OSError('journal write failed')
    monkeypatch.setattr(campaign,'write',fail)
    monkeypatch.setattr(campaign,'trial_execution',lambda *a,**k:pytest.fail('dispatch after failed journal'))
    with pytest.raises(OSError,match='journal write'):campaign.execute(frozen,grant)


@pytest.mark.parametrize('adapter,raw,expected',[
 ('codex','{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":8,"reasoning_output_tokens":6}}',(10,8,6)),
 ('claude','{"usage":{"input_tokens":12,"output_tokens":4},"total_cost_usd":0.02}',(12,4,None)),
 ('codex','not json',(None,None,None)),
 ('claude','{"usage":{"input_tokens":true,"output_tokens":-1}}',(None,None,None))])
def test_observed_tokens_preserve_unknown_and_reasoning_subset(adapter,raw,expected):
    result=campaign.native_usage(adapter,raw)
    assert tuple(result[k] for k in ('input_tokens','output_tokens','reasoning_output_tokens'))==expected


@pytest.mark.parametrize('case',['clean','critical-retention','unknown-region','unsupported-guarantee','qualified-exception','interrupted'])
@pytest.mark.parametrize('arm',['legacy','solo','independent-review'])
def test_measurement_keeps_native_raw_receipt_and_observed_usage(frozen,monkeypatch,case,arm):
    from attune_harness import review_participants
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    p=campaign.verify(frozen)
    trial=next(t for t in p['trials'] if t['case']==case and t['arm']==arm and t['profile']=='codex-lead')
    def runner(argv,prompt,**kwargs):
        raw='\n'.join(json.dumps(e) for e in [
            {'type':'thread.started','thread_id':'fixture'}, {'type':'turn.started'},
            {'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'text':'Maple reference agrees; this interpretation is unverified.'})}},
            {'type':'turn.completed','usage':{'input_tokens':42,'output_tokens':12,'reasoning_output_tokens':7}}])
        return ProcessResult(argv,0,raw,'')
    monkeypatch.setattr(review_participants,'NativeExchange',lambda name,**kwargs:NativeExchange(name,runner=runner,**kwargs))
    row={'trial_id':trial['id']};ledger={'trials':[row]};campaign.write(frozen/'ledger.json',ledger)
    factory=campaign.measured_factory(frozen,trial,row,ledger)
    result=campaign.trial_execution(p,trial,frozen/'runs'/trial['id'],factory)
    assert result['status']=='completed', result.get('execution',result).get('error')
    calls=trial['max_calls']
    assert row['input_tokens']==42*calls and row['output_tokens']==12*calls and row['reasoning_output_tokens']==7*calls
    assert len(row['native_calls'])==calls
    raw=campaign.read(frozen/'runs'/trial['id']/'native-0.json')
    assert row['native_calls'][0]['raw_sha256']==campaign.digest(raw)
