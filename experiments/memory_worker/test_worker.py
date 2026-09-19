"""Controller fault fixtures and saved-response replay; no provider calls."""
from copy import deepcopy
import hashlib
import multiprocessing
import pytest
from attune_harness.review_store import PersistenceError
import worker
from worker import WorkerStore, run
from replay_worker import fixtures, demonstrate

PACKET = fixtures()
CASES = {c['id']: c for c in PACKET['cases']}


def policy(audit=False):
    # Explicit test policy: modulus 1 audits all; modulus 2 bucket excludes test ID.
    value = dict(sample_modulus=1 if audit else 2, sample_bucket=0, sample_salt='test')
    if not audit:
        value['sample_bucket'] = 1 - int.from_bytes(hashlib.sha256(b'test:job').digest(),'big') % 2
    return value


def make_store(tmp_path, id='condition', audit=False, **host):
    envelope=deepcopy(CASES[id]['envelope']);envelope.update(host)
    return WorkerStore.create(tmp_path/'worker',envelope,policy(audit))


def value(id='condition'):
    return deepcopy(CASES[id]['calls'][0]['reply']['value'])


def reviewer(verdict='supported', ids=None):
    return dict(value=dict(verdict=verdict,reason='Injected controller fixture; not a model quality observation.',
                           evidence_ids=['P21','P22'] if ids is None else ids))


def injected(values, calls):
    def call(role,model,prompt,schema):
        calls.append(dict(role=role,model=model,prompt=deepcopy(prompt),schema=deepcopy(schema)))
        result=values[len(calls)-1]
        if isinstance(result,BaseException): raise result
        return deepcopy(result)
    return call


def test_exact_saved_native_replay_and_reopen():
    observed=demonstrate()
    assert observed['native_calls']==0 and observed['replayed_calls']==9
    assert len(observed['rows'])==8
    assert [r['case_id'] for r in observed['rows'] if r['sampled']]==['condition']
    assert all(r['memory_record_unchanged'] for r in observed['rows'])


@pytest.mark.parametrize('task_class,models',[('routine',['luna']),('known_difficult',['astra'])])
def test_host_route_without_router_call(tmp_path,task_class,models):
    store=make_store(tmp_path,task_class=task_class);calls=[]
    result=run(store,'job',injected([dict(value=value())],calls))
    assert [c['model'] for c in calls]==models
    assert result['status']=='proposal_ready' and not result['sampled']
    assert store.read()['envelope']==CASES['condition']['envelope'] | {'task_class':task_class}
    assert all(k not in calls[0]['prompt'] for k in ('expected','policy','task_class','sampled'))


@pytest.mark.parametrize('host',[{'task_class':'unknown'},{'capability':'live_memory'},
                               {'capability':'security_classification'},{'capability':'retrieval_refresh'}])
def test_unsupported_work_never_dispatches(tmp_path,host):
    store=make_store(tmp_path,**host)
    result=run(store,'job',lambda *a:pytest.fail('No dispatch'))
    assert result['status']=='blocked' and result['attempts']==[]


@pytest.mark.parametrize('invalid',['empty_sources','duplicate_sources','duplicate_facts','assigned_model','kind','policy','version'])
def test_invalid_host_input_rejected_before_artifact(tmp_path,invalid):
    envelope=deepcopy(CASES['condition']['envelope']);p=policy()
    bound=envelope['input']
    if invalid=='empty_sources': bound['sources']=[]
    elif invalid=='duplicate_sources': bound['sources'][1]['id']=bound['sources'][0]['id']
    elif invalid=='duplicate_facts': bound['record']['facts'].append(deepcopy(bound['record']['facts'][0]))
    elif invalid=='assigned_model': bound['grants']['assigned_model']='astra'
    elif invalid=='kind': bound['grants']['kinds']=['SENSITIVE']
    elif invalid=='version': bound['record']['version']=True
    else: p['sample_modulus']=0
    with pytest.raises((ValueError,worker.contract.ValidationError)):
        WorkerStore.create(tmp_path/'worker',envelope,p)
    assert not (tmp_path/'worker').exists()


@pytest.mark.parametrize('initial',['contract','reasoning'])
def test_one_hop_escalation_preserves_evidence_and_call_limit(tmp_path,initial):
    store=make_store(tmp_path,audit=True);first=value();calls=[]
    if initial=='contract':first['evidence_ids']=[]
    else:first.update(outcome='needs_reasoning',facts=[],request='Resolve the supplied rules.')
    result=run(store,'job',injected([dict(value=first),dict(value=value()),reviewer()],calls))
    assert result['status']=='proposal_ready' and result['result']['escalated']
    assert [(c['role'],c['model']) for c in calls]==[('worker','luna'),('escalation','astra'),('audit','astra')]
    assert all(c['prompt']['sources']==CASES['condition']['envelope']['input']['sources'] for c in calls)
    assert calls[1]['prompt']['previous_attempt']['response']==first


@pytest.mark.parametrize('task_class,expected_calls',[('routine',2),('known_difficult',1)])
@pytest.mark.parametrize('audit',[False,True])
def test_stronger_unresolved_stops_without_bounce(tmp_path,task_class,expected_calls,audit):
    store=make_store(tmp_path,task_class=task_class,audit=audit);v=value();calls=[]
    v.update(outcome='needs_reasoning',facts=[],request='Cannot reconcile supplied rules.')
    result=run(store,'job',injected([dict(value=v)]*expected_calls,calls))
    assert result['status']=='unresolved_reasoning' and len(calls)==expected_calls
    assert result['result']['audit'] is None


@pytest.mark.parametrize('id,status',[('absent','await_evidence'),('choice','await_decision')])
def test_missing_evidence_and_choice_are_not_reasoning_escalations(tmp_path,id,status):
    store=make_store(tmp_path,id);calls=[]
    result=run(store,'job',injected([dict(value=value(id))],calls))
    assert result['status']==status and len(calls)==1
    assert store.read()['envelope']==CASES[id]['envelope']


@pytest.mark.parametrize('id',['condition','distinct','absent','choice'])
def test_sampled_dispositions_audited_before_publication(tmp_path,id):
    store=make_store(tmp_path,id,audit=True);calls=[]
    def call(role,model,prompt,schema):
        saved=store.inspect('job')
        assert saved['status']=='running' and saved['result'] is None
        assert saved['attempts'][-1]['state']=='dispatched'
        calls.append(role)
        return dict(value=value(id)) if role=='worker' else reviewer(ids=value(id)['evidence_ids'])
    result=run(store,'job',call)
    assert result['status']==CASES[id]['expected_action'] and calls==['worker','audit']


@pytest.mark.parametrize('fault',['confident_error','false_no_change','uncertain','empty_citations','unknown_citation'])
def test_audit_failure_quarantines_without_memory_effect(tmp_path,fault):
    store=make_store(tmp_path,audit=True);v=value();audit=reviewer();calls=[]
    if fault=='confident_error':
        v['facts'][0]['text']='Always use Willow for ordinary runs.'
        audit=reviewer('unsupported')
    elif fault=='false_no_change':
        v.update(operation='retain',outcome='no_change',facts=[])
        audit=reviewer('unsupported')
    elif fault=='uncertain': audit=reviewer('uncertain')
    elif fault=='empty_citations':audit=reviewer(ids=[])
    else:audit=reviewer(ids=['absent'])
    result=run(store,'job',injected([dict(value=v),audit],calls))
    assert result['status']=='quarantined' and len(calls)==2
    assert store.read()['envelope']==CASES['condition']['envelope']


def test_unsampled_semantic_error_is_not_claimed_detected(tmp_path):
    store=make_store(tmp_path);v=value()
    v['facts'][0]['text']='Always use Willow for ordinary runs.'
    result=run(store,'job',injected([dict(value=v)],[]))
    assert result['status']=='proposal_ready' and result['result']['audit'] is None
    assert store.read()['envelope']['input']['record']==CASES['condition']['envelope']['input']['record']


@pytest.mark.parametrize('at_audit',[False,True])
@pytest.mark.parametrize('field',['task','sources','record','grants','policy','task_class','aba'])
def test_inflight_host_change_stops_publication(tmp_path,at_audit,field):
    store=make_store(tmp_path,audit=at_audit);calls=[]
    def call(role,model,prompt,schema):
        calls.append(role)
        if (role=='audit')==at_audit:
            state=store.read();envelope=deepcopy(state['envelope'])
            if field=='policy':
                p=deepcopy(state['policy']);p['sample_salt']='new';store.replace_host_state(policy=p)
            else:
                if field=='task_class':envelope['task_class']='known_difficult'
                elif field=='task':envelope['input']['task']='Changed task'
                elif field=='sources':envelope['input']['sources'][0]['context']='Changed evidence'
                elif field=='record':envelope['input']['record']['version']+=1
                elif field=='grants':envelope['input']['grants']['create_ids']=['new-target']
                else:envelope['input']['task']='Transient change'
                store.replace_host_state(envelope=envelope)
                if field=='aba':store.replace_host_state(envelope=state['envelope'])
        return reviewer() if role=='audit' else dict(value=value())
    result=run(store,'job',call)
    assert result['status']=='stale_stop' and len(calls)==(2 if at_audit else 1)
    assert result['result'] is None


def test_final_publication_rechecks_after_controller_returns(tmp_path,monkeypatch):
    store=make_store(tmp_path);original=worker.contract.execute
    def change_after(*args,**kwargs):
        result=original(*args,**kwargs)
        store.replace_host_state()
        return result
    monkeypatch.setattr(worker.contract,'execute',change_after)
    result=run(store,'job',injected([dict(value=value())],[]))
    assert result['status']=='stale_stop'


def test_change_before_dispatch_has_zero_calls(tmp_path,monkeypatch):
    store=make_store(tmp_path);original=store.claim
    def claim(id):
        result=original(id);store.replace_host_state();return result
    monkeypatch.setattr(store,'claim',claim)
    result=run(store,'job',lambda *a:pytest.fail('No dispatch'))
    assert result['status']=='stale_stop' and not result['attempts']


@pytest.mark.parametrize('where',['worker','audit'])
def test_provider_failure_no_retry_or_publication(tmp_path,where):
    store=make_store(tmp_path,audit=where=='audit');calls=[]
    responses=([dict(value=value())] if where=='audit' else [])+[RuntimeError('injected unavailable')]
    with pytest.raises(RuntimeError,match='unavailable'):run(store,'job',injected(responses,calls))
    result=store.inspect('job')
    assert result['status']=='unresolved' and result['result'] is None
    assert result['attempts'][-1]['state']=='unresolved'
    with pytest.raises(ValueError,match='already claimed'):run(store,'job',lambda *a:pytest.fail('No retry'))


@pytest.mark.parametrize('state',['dispatched','completed'])
def test_persistence_failure_keeps_uncertain_intent_and_no_retry(tmp_path,monkeypatch,state):
    store=make_store(tmp_path);original=store.records.save;calls=[]
    def fail(record):
        attempts=record['jobs'].get('job',{}).get('attempts',[])
        if attempts and attempts[-1]['state']==state: raise PersistenceError('Injected save failure')
        return original(record)
    monkeypatch.setattr(store.records,'save',fail)
    with pytest.raises(PersistenceError):run(store,'job',injected([dict(value=value())],calls))
    assert len(calls)==int(state=='completed')
    assert store.inspect('job')['status']=='running'
    with pytest.raises(ValueError,match='already claimed'):run(store,'job',lambda *a:pytest.fail('No retry'))


def test_interruption_inspection_and_repeat_do_not_dispatch(tmp_path):
    store=make_store(tmp_path)
    with pytest.raises(SystemExit):run(store,'job',injected([SystemExit('interrupt')],[]))
    raw=store.records.path.read_bytes()
    result=WorkerStore(tmp_path/'worker').inspect('job')
    assert result['status']=='running' and result['attempts'][0]['state']=='dispatched'
    assert 'inspection_note' in result and store.records.path.read_bytes()==raw
    with pytest.raises(ValueError,match='already claimed'):run(store,'job',lambda *a:pytest.fail('No retry'))


def _competing_process(directory, start, queue):
    store=WorkerStore(directory)
    if not start.wait(10): raise RuntimeError('No start signal')
    def call(*args):
        queue.put('participant')
        return dict(value=value())
    try:
        run(store,'job',call)
        queue.put('completed')
    except (ValueError,PersistenceError):queue.put('refused')


def test_two_real_processes_cannot_dispatch_one_job_twice(tmp_path):
    store=make_store(tmp_path)
    context=multiprocessing.get_context('spawn');start=context.Event();queue=context.Queue()
    children=[context.Process(target=_competing_process,args=(str(tmp_path/'worker'),start,queue)) for _ in range(2)]
    try:
        for child in children:child.start()
        start.set()
        for child in children:
            child.join(15)
            assert child.exitcode==0
        messages=[queue.get(timeout=5) for _ in range(3)]
        assert sorted(messages)==['completed','participant','refused']
        assert len(store.inspect('job')['attempts'])==1
    finally:
        for child in children:
            if child.is_alive():child.terminate();child.join(5)
        queue.close()
