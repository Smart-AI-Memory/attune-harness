"""Bridge the unchanged worker contract to isolated, explicitly mapped notes."""
from copy import deepcopy
from pathlib import Path
from managed_stash import ManagedStash, identifier, worker, digest


def prepare(adapter, directory, *, target, operation, task, sources, policy,
            kind='note', task_class='routine'):
    identifier(target)
    if kind != 'note' or operation not in ('capture', 'amend', 'forget'):
        raise ValueError('Only note capture/amend/forget is mapped')
    if any(s['scope'] != adapter.scope for s in sources):
        raise ValueError('Foreign evidence refused before participant dispatch')
    snapshot = adapter.snapshot()
    facts = [f for f in snapshot['facts'] if f['id'] == target]
    if (operation == 'capture') == bool(facts):
        raise ValueError('Capture requires absence; correction/forgetting requires the exact note')
    refs = {id for fact in facts for id in fact['source_ids']}
    known = {s['id']: s for s in snapshot['sources'] if s['id'] in refs}
    for source in sources:
        if source['id'] in known and known[source['id']] != source:
            raise ValueError('Conflicting source ID')
        known[source['id']] = deepcopy(source)
    bound = dict(task=task, record=dict(version=snapshot['version'], facts=facts),
        sources=list(known.values()), grants=dict(scopes=[adapter.scope], kinds=['note'],
        create_ids=[target] if operation == 'capture' else [],
        remove_ids=[target] if operation == 'forget' else [], classify_ids=[]))
    adapter.assert_binding(bound)
    return worker.WorkerStore.create(directory, dict(input=bound,task_class=task_class,
                                     capability=worker.CAPABILITY), policy)


def apply_job(adapter, store, job_id):
    with store.records.lease():
        state = store.read()
        job = state['jobs'][job_id]
        worker.check_current(state, job)
        if job['status'] != 'proposal_ready' or job['result'] is None:
            raise ValueError('Only a completed ready proposal can be applied')
        bound = deepcopy(job['envelope']['input'])
        bound['grants']['assigned_model'] = worker.ROUTES[job['envelope']['task_class']]
        result = job['result']
        assessment = worker.contract.assess(bound, dict(value=result['final']['response']), bound, 'repaired')
        if not assessment['accepted'] or assessment != result['final'] or result['binding'] != bound:
            raise ValueError('Stored proposal does not match revalidated worker input')
        selected = worker.sampled(job_id, job['policy'])
        if selected != job['sampled']:
            raise ValueError('Stored sample selection disagrees with host policy')
        if selected:
            audit = result['audit']
            if not isinstance(audit, dict) or audit.get('state') != 'completed':
                raise ValueError('Required semantic audit is missing')
            answer = audit['response']
            worker.Draft202012Validator(worker.contract.schema_for(bound, audit=True)).validate(answer)
            worker.old.refs(bound, answer['evidence_ids'])
            if answer['verdict'] != 'supported':
                raise ValueError('Required semantic review did not support the proposal')
        operation_id = digest(dict(store=str(store.records.directory.resolve()), job_id=job_id))
        return adapter.apply(operation_id, digest(job), bound, assessment['candidate'],
                             assessment['response']['operation'])


def execute(adapter, store, job_id, participant):
    bound = deepcopy(store.read()['envelope']['input'])
    adapter.assert_binding(bound)
    def guarded(role, model, prompt, schema):
        if {key: prompt[key] for key in bound} != bound:
            raise worker.old.StaleInput('Claimed participant input differs from preflighted adapter input')
        adapter.assert_binding(bound)
        reply = participant(role, model, prompt, schema)
        adapter.assert_binding(bound)
        return reply
    result = worker.run(store, job_id, guarded)
    receipt = apply_job(adapter, store, job_id) if result['status'] == 'proposal_ready' else None
    return dict(worker=result, application=receipt)
