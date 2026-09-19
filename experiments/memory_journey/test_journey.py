"""Actual temporary file stores with injected responses; no native calls."""
from copy import deepcopy
import json
import multiprocessing
from pathlib import Path
import pytest
from managed_stash import ManagedStash, Conflict, PendingWrite, worker
from journey import prepare, execute, apply_job
from fixtures import packet, participant, answer

P = packet()


def setup(tmp_path):
    return ManagedStash.create(tmp_path/'cedar','cedar')


def prepared(adapter,tmp_path,stage, suffix=''):
    item=next(s for s in P['stages'] if s['id']==stage)
    return prepare(adapter,tmp_path/(stage+suffix),target=P['target'],operation=item['operation'],
                   task=item['task'],sources=item['sources'],policy=P['policy'])


def step(adapter,tmp_path,stage,suffix=''):
    store=prepared(adapter,tmp_path,stage,suffix)
    result=execute(adapter,store,stage,participant(stage))
    assert result['application']['disposition']=='applied'
    return store,result


def proposal(adapter,tmp_path,stage,suffix=''):
    store=prepared(adapter,tmp_path,stage,suffix)
    worker.run(store,stage,participant(stage))
    return store


def test_complete_real_lifecycle_retries_refresh_and_other_project(tmp_path):
    adapter=setup(tmp_path)
    foreign=ManagedStash.create(tmp_path/'elm','elm')
    foreign.backend.remember('FOREIGN_CANARY',memory_id='elm-note',topics=['type:note','cwd:elm','source:E1'])
    foreign_bytes=foreign.path.read_bytes()
    capture,_=step(adapter,tmp_path,'capture')
    old=adapter.recall('rehearsal');assert old['version']==1 and len(old['facts'])==1
    before=adapter.path.read_bytes()
    assert apply_job(adapter,capture,'capture')['replay']
    assert adapter.path.read_bytes()==before and len(adapter.backend.recent())==1
    correction,_=step(adapter,tmp_path,'correction')
    with pytest.raises(Conflict):adapter.assert_context(old)
    fresh=ManagedStash(tmp_path/'cedar','cedar').recall('rehearsal')
    assert fresh['version']==2 and '10:45' in fresh['facts'][0]['text']
    assert '09:15' not in fresh['facts'][0]['text']
    forgetting,_=step(adapter,tmp_path,'forget')
    with pytest.raises(Conflict):adapter.assert_context(fresh)
    assert adapter.recall('rehearsal')['facts']==[] and adapter.path.read_bytes()==b''
    assert adapter.snapshot()['version']==3 and adapter.snapshot()['sources']==[]
    for store,id in ((capture,'capture'),(correction,'correction'),(forgetting,'forget')):
        assert apply_job(adapter,store,id)['replay']
    assert adapter.path.read_bytes()==b'' and foreign.path.read_bytes()==foreign_bytes


@pytest.mark.parametrize('kind',['preference','lesson','decision','SENSITIVE'])
def test_unmapped_kind_rejected_before_worker(tmp_path,kind):
    adapter=setup(tmp_path);item=P['stages'][0]
    with pytest.raises(ValueError,match='mapped'):
        prepare(adapter,tmp_path/'job',target=P['target'],operation='capture',task=item['task'],
                sources=item['sources'],policy=P['policy'],kind=kind)
    assert not (tmp_path/'job').exists() and adapter.snapshot()['version']==0


def test_foreign_source_and_wrong_project_directory_rejected(tmp_path):
    adapter=setup(tmp_path);sources=deepcopy(P['stages'][0]['sources']);sources[0]['scope']='elm'
    with pytest.raises(ValueError,match='Foreign evidence'):
        prepare(adapter,tmp_path/'job',target=P['target'],operation='capture',task='Capture',sources=sources,policy=P['policy'])
    with pytest.raises(ValueError,match='does not own'):ManagedStash(tmp_path/'cedar','elm')
    assert not (tmp_path/'job').exists()


@pytest.mark.parametrize('change',['foreign_source','kind','task'])
def test_host_change_between_preflight_and_claim_cannot_reach_participant(tmp_path,monkeypatch,change):
    adapter=setup(tmp_path);store=prepared(adapter,tmp_path,'capture');original=store.claim
    def claim(id):
        envelope=deepcopy(store.read()['envelope'])
        if change=='foreign_source': envelope['input']['sources'].append(dict(id='E',text='FOREIGN_CANARY',scope='elm',context='Foreign'))
        elif change=='kind':envelope['input']['grants']['kinds']=['preference']
        else:envelope['input']['task']='Changed accepted request'
        store.replace_host_state(envelope=envelope)
        return original(id)
    monkeypatch.setattr(store,'claim',claim)
    result=execute(adapter,store,'capture',lambda *a:pytest.fail('Must not reach participant'))
    assert result['worker']['status']=='stale_stop' and result['application'] is None
    assert adapter.snapshot()['facts']==[]


@pytest.mark.parametrize('damage',['malformed','expired','duplicate','foreign','unknown_field'])
def test_complete_physical_validation_before_dispatch(tmp_path,damage):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture')
    store=prepared(adapter,tmp_path,'correction')
    row=json.loads(adapter.path.read_text().strip())
    if damage=='malformed':extra='broken-json\n'
    else:
        if damage=='expired':row['id']='old-note';row['ts']=1
        elif damage=='foreign':row['id']='elm-note';row['cwd']='elm';row['topics']=['type:note','cwd:elm','source:E1']
        elif damage=='unknown_field':row['id']='extra-note';row['unmodeled']='foreign payload'
        extra=json.dumps(row)+'\n'
    with adapter.path.open('a') as f:f.write(extra)
    corrupted=adapter.path.read_bytes()
    with pytest.raises(ValueError):execute(adapter,store,'correction',lambda *a:pytest.fail('No participant'))
    assert adapter.path.read_bytes()==corrupted and store.read()['jobs']=={}


def test_recall_foreign_result_cannot_become_context(tmp_path,monkeypatch):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture')
    monkeypatch.setattr(adapter.backend,'search',lambda *a,**k:[dict(id='elm',text='Foreign',cwd='elm',topics=['type:note','cwd:elm','source:E1'])])
    with pytest.raises(ValueError):adapter.recall('anything')


def test_live_change_during_participant_is_not_overwritten(tmp_path):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture')
    current=prepared(adapter,tmp_path,'correction')
    rival=proposal(adapter,tmp_path,'correction','-rival')
    def call(*args):
        apply_job(adapter,rival,'correction')
        return participant('correction')(*args)
    result=execute(adapter,current,'correction',call)
    assert result['worker']['status']=='stale_stop' and result['application'] is None
    assert adapter.snapshot()['version']==2 and len(adapter.backend.recent())==1


@pytest.mark.parametrize('field',['policy','grants'])
def test_current_worker_policy_checked_at_apply(tmp_path,field):
    adapter=setup(tmp_path);store=proposal(adapter,tmp_path,'capture')
    if field=='policy':
        policy=dict(store.read()['policy'],sample_salt='changed');store.replace_host_state(policy=policy)
    else:
        envelope=deepcopy(store.read()['envelope']);envelope['input']['grants']['create_ids']=[]
        store.replace_host_state(envelope=envelope)
    with pytest.raises(worker.old.StaleInput):apply_job(adapter,store,'capture')
    assert adapter.snapshot()['facts']==[]


@pytest.mark.parametrize('tamper',['candidate','sample','audit','verdict','kind','too_long'])
def test_ineligible_proposal_does_not_write(tmp_path,tamper):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture')
    store=proposal(adapter,tmp_path,'correction');state=store.read();job=state['jobs']['correction']
    if tamper=='candidate':job['result']['final']['candidate']['facts'][0]['text']='Forged'
    elif tamper=='sample':job['sampled']=False
    elif tamper=='audit':job['result']['audit']=None
    elif tamper=='verdict':job['result']['audit']['response']['verdict']='unsupported'
    else:
        key,new=('kind','lesson') if tamper=='kind' else ('text','x'*501)
        job['result']['final']['response']['facts'][0][key]=new
        job['result']['final']['candidate']['facts'][0][key]=new
    with store.records.lease():store.records.save(state)
    before=adapter.path.read_bytes()
    with pytest.raises(ValueError):apply_job(adapter,store,'correction')
    assert adapter.path.read_bytes()==before and adapter.snapshot()['version']==1


def test_conflicting_completed_operation_reuse_rejected(tmp_path):
    adapter=setup(tmp_path);store,_=step(adapter,tmp_path,'capture')
    state=store.read();state['jobs']['capture']['reason']='Altered host receipt'
    with store.records.lease():store.records.save(state)
    with pytest.raises(ValueError,match='Conflicting reuse'):apply_job(adapter,store,'capture')
    assert adapter.snapshot()['version']==1 and len(adapter.backend.recent())==1


@pytest.mark.parametrize('failure',['before','after','partial'])
def test_explicit_reconcile_never_repeats_uncertain_effect(tmp_path,monkeypatch,failure):
    adapter=setup(tmp_path)
    stage='correction' if failure=='partial' else 'capture'
    if stage=='correction':step(adapter,tmp_path,'capture')
    store=proposal(adapter,tmp_path,stage);original=adapter.backend.remember;calls=[]
    def remember(*args,**kwargs):
        calls.append('remember')
        if failure=='after':assert original(*args,**kwargs)
        return False
    monkeypatch.setattr(adapter.backend,'remember',remember)
    with pytest.raises(PendingWrite):apply_job(adapter,store,stage)
    with pytest.raises(PendingWrite):adapter.recall('rehearsal')
    with pytest.raises(PendingWrite):apply_job(adapter,store,stage)
    assert calls==['remember']
    if failure=='partial':
        with pytest.raises(PendingWrite):adapter.reconcile()
        assert adapter.path.read_bytes()==b'' and adapter._state()['pending'] is not None
    else:
        result=adapter.reconcile()
        assert result['disposition']==('applied' if failure=='after' else 'not_applied')
        assert apply_job(adapter,store,stage)['replay']
        assert len(adapter.backend.recent())==int(failure=='after')
    assert calls==['remember']


def test_failed_commit_persistence_reconciles_observed_effect(tmp_path,monkeypatch):
    adapter=setup(tmp_path);store=proposal(adapter,tmp_path,'capture');original=adapter.control.save
    def save(state):
        if state['operations']:raise OSError('Injected commit receipt failure')
        original(state)
    monkeypatch.setattr(adapter.control,'save',save)
    with pytest.raises(OSError):apply_job(adapter,store,'capture')
    assert len(adapter.backend.recent())==1 and adapter._state()['pending'] is not None
    monkeypatch.setattr(adapter.control,'save',original)
    assert adapter.reconcile()['disposition']=='applied'
    assert apply_job(adapter,store,'capture')['replay'] and len(adapter.backend.recent())==1


def test_failed_intent_persistence_has_no_backend_effect(tmp_path,monkeypatch):
    adapter=setup(tmp_path);store=proposal(adapter,tmp_path,'capture')
    def save(state):raise OSError('Injected intent persistence failure')
    monkeypatch.setattr(adapter.control,'save',save)
    monkeypatch.setattr(adapter.backend,'remember',lambda *a,**k:pytest.fail('No backend effect'))
    with pytest.raises(OSError):apply_job(adapter,store,'capture')
    assert not adapter.path.exists() and adapter._state()['pending'] is None


@pytest.mark.parametrize('damage',['foreign','malformed'])
def test_pending_contamination_cannot_be_reconciled(tmp_path,monkeypatch,damage):
    adapter=setup(tmp_path);store=proposal(adapter,tmp_path,'capture')
    monkeypatch.setattr(adapter.backend,'remember',lambda *a,**k:False)
    with pytest.raises(PendingWrite):apply_job(adapter,store,'capture')
    if damage=='foreign':
        adapter.path.write_text(json.dumps(dict(id='elm-note',text='Foreign',session_id=None,
            topics=['type:note','cwd:elm','source:E1'],cwd='elm',ts=1))+'\n')
    else:adapter.path.write_text('broken-json\n')
    before=adapter.path.read_bytes()
    with pytest.raises(ValueError):adapter.reconcile()
    assert adapter._state()['pending'] is not None and adapter.path.read_bytes()==before


def test_source_identifier_bounds_before_worker(tmp_path):
    adapter=setup(tmp_path);sources=deepcopy(P['stages'][0]['sources']);sources[0]['id']='S'*65000
    with pytest.raises(ValueError,match='bounded identifier'):
        prepare(adapter,tmp_path/'job',target=P['target'],operation='capture',task='Capture',sources=sources,policy=P['policy'])
    assert not (tmp_path/'job').exists() and not adapter.path.exists()


def test_ninth_note_refused_before_worker_and_effects(tmp_path,monkeypatch):
    adapter=setup(tmp_path)
    for index in range(8):
        id=f'note-{index}';source=dict(id=f'S{index}',text='A synthetic note.',scope='cedar',context='Accepted')
        store=prepare(adapter,tmp_path/id,target=id,operation='capture',task='Capture note',sources=[source],policy=P['policy'])
        def call(role,*args):
            if role=='audit':return dict(value=dict(verdict='supported',reason='Fixture',evidence_ids=[source['id']]))
            return dict(value=dict(operation='capture',outcome='update',facts=[dict(id=id,text=source['text'],scope='cedar',kind='note',source_ids=[source['id']])],reason='Fixture',evidence_ids=[source['id']],request=''))
        execute(adapter,store,id,call)
    before=adapter.path.read_bytes()
    monkeypatch.setattr(adapter.backend,'remember',lambda *a,**k:pytest.fail('No backend effect'))
    with pytest.raises(ValueError,match='eight notes'):prepared(adapter,tmp_path,'capture')
    assert adapter.path.read_bytes()==before and adapter.snapshot()['version']==8
    assert not (tmp_path/'capture').exists()


def test_raw_append_size_rejected_before_intent(tmp_path):
    adapter=setup(tmp_path)
    # A trusted imported file may have harmless blank space. It still consumes bytes.
    adapter.path.write_bytes(b'\n'*65400)
    from managed_stash import hashlib
    with adapter.control.lease():
        state=adapter._state();state['backend_sha']=hashlib.sha256(adapter.path.read_bytes()).hexdigest()
        adapter.control.save(state)
    store=proposal(adapter,tmp_path,'capture');before=adapter.path.read_bytes()
    with pytest.raises(ValueError,match='64 KiB'):apply_job(adapter,store,'capture')
    assert adapter.path.read_bytes()==before and adapter._state()['pending'] is None


def test_context_aba_remains_stale_when_content_returns(tmp_path):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture');old=adapter.recall('rehearsal')
    step(adapter,tmp_path,'correction')
    source=dict(id='N4',text='Restore the rehearsal to 09:15 on weekdays.',scope='cedar',context='Accepted restoration')
    store=prepare(adapter,tmp_path/'restore',target=P['target'],operation='amend',task=source['text'],sources=[source],policy=P['policy'])
    def call(role,*args):
        if role=='audit':return dict(value=dict(verdict='supported',reason='Fixture',evidence_ids=['N4']))
        value=answer('capture',None);value.update(operation='amend',evidence_ids=['N4'])
        value['facts'][0]['source_ids']=['N4']
        return dict(value=value)
    execute(adapter,store,'restore',call)
    assert adapter.recall('rehearsal')['facts'][0]['text']==old['facts'][0]['text']
    assert adapter.snapshot()['version']==3
    with pytest.raises(Conflict):adapter.assert_context(old)


def test_other_note_same_project_preserved(tmp_path):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture')
    source=dict(id='O1',text='Keep the spare cable in drawer 2.',scope='cedar',context='Accepted unrelated note')
    store=prepare(adapter,tmp_path/'other',target='other-note',operation='capture',task='Capture other note',sources=[source],policy=dict(P['policy'],sample_modulus=1))
    def call(role,*args):
        if role=='audit':return dict(value=dict(verdict='supported',reason='Fixture',evidence_ids=['O1']))
        return dict(value=dict(operation='capture',outcome='update',facts=[dict(id='other-note',text=source['text'],scope='cedar',kind='note',source_ids=['O1'])],reason='Fixture',evidence_ids=['O1'],request=''))
    execute(adapter,store,'other',call)
    other=deepcopy(adapter.recall('spare'))
    step(adapter,tmp_path,'correction');step(adapter,tmp_path,'forget')
    assert adapter.recall('spare')['facts']==other['facts'] and len(adapter.backend.recent())==1


def _apply_process(directory,store_dir,start,queue):
    adapter=ManagedStash(directory,'cedar');store=worker.WorkerStore(store_dir)
    if not start.wait(10):raise RuntimeError('No start signal')
    try:apply_job(adapter,store,'correction');queue.put('applied')
    except (ValueError,OSError):queue.put('refused')


def test_two_processes_same_version_only_one_applies(tmp_path):
    adapter=setup(tmp_path);step(adapter,tmp_path,'capture')
    one=proposal(adapter,tmp_path,'correction','-one');two=proposal(adapter,tmp_path,'correction','-two')
    context=multiprocessing.get_context('spawn');start=context.Event();queue=context.Queue()
    children=[context.Process(target=_apply_process,args=(str(tmp_path/'cedar'),str(s.records.directory),start,queue)) for s in (one,two)]
    try:
        for child in children:child.start()
        start.set()
        for child in children:child.join(15);assert child.exitcode==0
        assert sorted(queue.get(timeout=5) for _ in children)==['applied','refused']
        assert adapter.snapshot()['version']==2 and len(adapter.backend.recent())==1
    finally:
        for child in children:
            if child.is_alive():child.terminate();child.join(5)
        queue.close()


def test_runner_uses_current_context_and_only_scheduled_audit():
    from run_journey import lifecycle
    calls=[];saved=[]
    def call(stage,role,model,prompt,schema):
        calls.append((stage,role,model,deepcopy(prompt)))
        return participant(stage)(role,model,prompt,schema)
    result=lifecycle(call,saved.append)
    assert [(s,r,m) for s,r,m,_ in calls]==[
        ('capture','worker','luna'),('correction','worker','luna'),
        ('correction','audit','astra'),('forget','worker','luna')]
    assert calls[-1][3]['record']['facts'][0]['source_ids']==['N2']
    assert [s['id'] for s in calls[-1][3]['sources']]==['N2','N3']
    assert result['status']=='completed' and result['final_version']==3
    assert saved[-1]['artifacts']['cedar/backend/findings.jsonl']==''
    assert '09:15' in saved[-1]['artifacts']['capture/record.json']  # History is intentionally retained.


def test_runner_preserves_uncertain_attempt_and_stops():
    from run_journey import lifecycle
    saved=[];calls=[]
    def call(*args):
        calls.append(args);raise RuntimeError('Injected unknown participant outcome')
    with pytest.raises(RuntimeError):lifecycle(call,saved.append)
    assert len(calls)==1 and saved[-1]['status']=='stopped'
    artifacts=saved[-1]['artifacts']
    assert 'cedar/backend/findings.jsonl' not in artifacts
    state=json.loads(artifacts['capture/record.json'])
    assert state['jobs']['capture']['status']=='unresolved'
    assert state['jobs']['capture']['attempts'][0]['state']=='unresolved'


def test_runner_rejected_audit_preserves_prior_store_and_stops():
    from run_journey import lifecycle
    saved=[];calls=[]
    def call(stage,role,*args):
        calls.append((stage,role))
        if role=='audit':return dict(value=dict(verdict='unsupported',reason='Injected rejection',evidence_ids=['N2']))
        return participant(stage)(role,*args)
    with pytest.raises(ValueError,match='applied operation'):lifecycle(call,saved.append)
    assert calls==[('capture','worker'),('correction','worker'),('correction','audit')]
    state=json.loads(saved[-1]['artifacts']['cedar/record.json'])
    assert state['version']==1 and '09:15' in state['facts'][0]['text']
    assert state['pending'] is None and saved[-1]['status']=='stopped'


def test_persistent_receipt_failure_retains_actual_scratch_files():
    from run_journey import lifecycle, ArtifactPreservationError
    import shutil
    def preserve(value):
        if value['stages'][0].get('state')=='completed':
            raise OSError('Injected persistent receipt failure after capture effect')
    with pytest.raises(ArtifactPreservationError) as error:
        lifecycle(lambda stage,*rest:participant(stage)(*rest),preserve)
    root=error.value.directory
    try:
        assert root.is_dir() and str(root) in str(error.value)
        assert ManagedStash(root/'cedar','cedar').snapshot()['version']==1
        assert '09:15' in (root/'cedar/backend/findings.jsonl').read_text()
        assert (root/'capture/record.json').exists()
    finally:
        shutil.rmtree(root)
