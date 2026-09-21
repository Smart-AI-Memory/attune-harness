"""Explicit assessment policy; model narratives are never tool-certified judgments."""

import copy
from pathlib import Path

from .features import read_text
from .review_contract import digest
from .review_participants import ReviewExchange
from .review_store import RunStore
from .recovery import engine_profile
from .task_contract import check_fresh, read_task, safe_storage

RUNTIME_PROFILE = {'kind': 'assessment', 'version': 1}


class AssessmentPolicy:
    def __init__(self, task):
        self.task = task

    def check_fresh(self):
        check_fresh(self.task)

    def prepare_turn(self, turn):
        turn.update(tools=['retrieve', 'verify'], remaining_tool_calls=0, remaining_turns=1,
                    criteria=self.task['request']['answers']['criteria'])
        turn['objective'] += '\nAcceptance criteria: ' + turn['criteria']
        turn['protocol'] += ' Host evidence is complete. Return only a final action; additional tools are unavailable.'
        if self.task['request'].get('result_profile') == 'assessment-findings-v1':
            turn['result_profile'] = 'assessment-findings-v1'
            turn['protocol'] += (
                ' Return final action text as JSON with schema_version 1, kind '
                '"assessment-findings-v1", findings (each with unique id, low/medium/high '
                'severity, text, and nonempty evidence strings), and notes. '
                'Findings identify repair candidates but grant no file or execution authority.'
            )

    def validate_action(self, action):
        if action['kind'] != 'final':
            raise ValueError('Assessment assignment requires a final response, not another tool call')
        if len(action['text'].encode('utf-8')) > self.task['request']['budgets']['max_output_bytes']:
            raise ValueError('Assignment exceeded accepted output budget')
        if self.task['request'].get('result_profile') == 'assessment-findings-v1':
            from .review_contract import parse_json
            from .task_handoff import validate_assessment_payload
            validate_assessment_payload(parse_json(action['text']))

    def integrate(self, record):
        return {'execution_status': 'completed', 'acceptance_status': 'unverified',
                'document_outcome': record['document_outcome'],
                'retrieval_outcome': record['retrieval_outcome'],
                'narratives': copy.deepcopy(record['participants']),
                'semantic_verification': False,
                'disagreement': 'Not automatically adjudicated; inspect the attributed narratives',
                'scope': 'Tools check supported document claims only. Narratives and agreement remain unverified.'}


class TaskExecutionStore:
    """One authoritative checkpoint, even while the shared engine saves its projection."""
    def __init__(self, store, task):
        self.store, self.task = store, task
        self.directory, self.path = store.directory, store.path

    def save(self, execution):
        if len(execution['events']) > self.task['request']['budgets']['max_operations']:
            from .review_store import PersistenceError
            raise PersistenceError('Accepted operation budget exhausted')
        self.task['execution'] = execution
        self.task['status'] = execution['status']
        self.store.save(self.task)


def prepare_task(task):
    request = task['request']
    answers = request['answers']
    paths = {name: (Path(request['project_root']) / answers[name]).resolve()
             for name in ('document', 'context', 'corpus')}
    source = request['evidence']['retrieval']
    snapshot = (source['sources'] if source['mode'] == 'keyword' else
                {'generation': request['registry']['retrieval']['generation'], 'manifest': source['manifest_digest']})
    return {'answers': {**answers, 'objective': answers['goal']}, 'paths': paths,
            'originals': {paths[n]: read_text(paths[n], 65536) for n in ('document', 'context')},
            'source_snapshot': snapshot}


def execute_task(directory, *, checkpoint=None, max_operations=None, exchange_factory=ReviewExchange,
                 allow_external=False, allow_native=False):
    if read_task(directory).get('task_profile') == 'feature-work-v1':
        from .work_runtime import plan_work, build_work
        work = read_task(directory)
        execute = build_work if work['status'] == 'accepted' and work['request'].get('effects') else plan_work
        return execute(directory, checkpoint=checkpoint, max_operations=max_operations, exchange_factory=exchange_factory,
                       allow_external=allow_external, allow_native=allow_native)
    if read_task(directory).get('task_profile') == 'pytest-change-v1':
        from .test_change import execute_test_task
        return execute_test_task(directory, checkpoint=checkpoint, max_operations=max_operations)
    """Start or continue accepted work; completed operations belong to their assignment."""
    from .review import authorize_external
    from .retrieval import retrieve_sources
    from .verification import verify_document
    from .task_runtime import execute_assessment
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        task = read_task(store.directory)
        if checkpoint is not None and checkpoint != task['checkpoint_digest']:
            raise ValueError('Stale task checkpoint')
        if task['status'] in ('draft', 'cancelled'):
            raise ValueError('Task must be accepted and active')
        check_fresh(task)
        if task['status'] == 'completed':
            return task
        request = task['request']
        bound = task['bindings']['assessment']['assignments']
        selected = {role: assignment['configuration'] for role, assignment in bound.items()}
        grants = task['acceptance']['permissions']
        authorize_external(selected, grants['external'])
        if 'repair' in request:
            return execute_repair(task, store, max_operations=max_operations, exchange_factory=exchange_factory)
        # One preflight, retrieval, final verification, and one call per assignment.
        if request['budgets']['max_operations'] < 3 + len(bound):
            raise ValueError('Accepted operation budget cannot complete the assessment plan')
        prepared = prepare_task(task)
        if 'execution' not in task:
            task['execution'] = {
                'schema_version': 1, 'operation': 'review', 'status': 'running',
                'run_id': request['task_id'], 'requirement_revision': digest(request),
                'registry': request['registry'], 'events': [], 'participants': {},
                'record_path': str(store.path),
                'recovery': {'profile': engine_profile(request['registry']),
                             'source_snapshot': prepared['source_snapshot'],
                             'assignments': {role: {'participant_id': a['participant_id'],
                                                   'attempt_id': a['assignment_id']} for role, a in bound.items()},
                             'transfers': [], 'reconciliations': []}}
            task['recovery']['runtime'] = RUNTIME_PROFILE
        from .recovery import prepare_continuation
        prepare_continuation(task['execution'], store)
        execute_assessment(task['execution'], TaskExecutionStore(store, task), prepared,
            allow_external=grants['external'], allow_provider=grants['provider'],
            max_operations=max_operations, exchange_factory=exchange_factory,
            services=(retrieve_sources, verify_document, authorize_external), policy=AssessmentPolicy(task))
        return task


def validate_execution(task):
    from .recovery import validate_events
    execution = task['execution']
    request = task['request']
    if (execution['operation'] != ('fix' if 'repair' in request else 'review') or execution['schema_version'] != 1 or
            execution['status'] != task['status'] or execution['run_id'] != request['task_id'] or
            execution['requirement_revision'] != digest(request) or
            execution['record_path'] != task['record_path'] or execution['registry'] != request['registry'] or
            execution['recovery']['profile'] != engine_profile(request['registry'])):
        raise ValueError('Execution differs from accepted task identity/profile')
    expected = {role: {'participant_id': a['participant_id'], 'attempt_id': a['assignment_id']}
                for role, a in task['bindings']['assessment']['assignments'].items()}
    transfers = execution['recovery']['transfers']
    if not isinstance(transfers, list) or len(transfers) > 2:
        raise ValueError('Invalid task transfer history')
    for transfer in transfers:
        current = expected['assessor']
        if (transfer['from'] != current['participant_id'] or
                transfer['prior_attempt_id'] != current['attempt_id'] or
                transfer['to'] not in request['registry']['participants'] or
                transfer['to'] in (current['participant_id'], expected.get('reviewer', {}).get('participant_id'))):
            raise ValueError('Invalid transferred assignment')
        expected['assessor'] = {'participant_id': transfer['to'], 'attempt_id': transfer['attempt_id']}
    if execution['recovery']['assignments'] != expected:
        raise ValueError('Execution assignments differ from accepted task bindings')
    if 'repair' in request:
        validate_events(execution, kinds=('acceptance_probe', 'participant_turn', 'replacement'))
    else:
        validate_events(execution)
    if len(execution['events']) > request['budgets']['max_operations']:
        raise ValueError('Execution exceeds accepted operation budget')


def inspect_task(directory):
    task = read_task(directory)
    if task.get('task_profile') == 'pytest-change-v1':
        from .test_change import present_test_task
        return present_test_task(task)
    if task['status'] == 'running':
        task['persisted_status'] = 'running'
        task['status'] = 'unresolved'
        task['inspection_note'] = 'Owner may still be running; no dispatch or retry was performed.'
    return task


def control_task(directory, action, *, checkpoint=None, **kwargs):
    if read_task(directory).get('task_profile') == 'pytest-change-v1':
        from .test_change import control_test_task
        return control_test_task(directory, action, checkpoint=checkpoint, **kwargs)
    from .recovery import reconcile_record, transfer_record, cancel_record
    from .review_contract import bounded_text
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        task = read_task(store.directory)
        current = task['checkpoint_digest']
        if checkpoint is not None and checkpoint != current:
            raise ValueError('Stale task checkpoint')
        if 'execution' not in task:
            raise ValueError('Task has no execution to control')
        run, adapter = task['execution'], TaskExecutionStore(store, task)
        if action == 'reconcile':
            reply = kwargs.get('reply_file')
            retry = kwargs.get('retry_read_only', False)
            file_resolution = kwargs.get('observe_file', False) or kwargs.get('retry_before', False)
            if sum((reply is not None, bool(retry), bool(kwargs.get('observe_file')), bool(kwargs.get('retry_before')))) != 1:
                raise ValueError('Choose one recovered reply or read-only retry')
            if 'repair' in task['request']:
                event = next((e for e in run['events'] if e['event_id'] == kwargs['event_id']), None)
                if event and event['kind'] == 'replacement':
                    if task['status'] in ('completed','cancelled'):
                        raise ValueError('Task is terminal')
                    from .repair import reconcile_replacement
                    before = copy.deepcopy(event)
                    evidence = reconcile_replacement(task['request']['repair']['scope'], event,
                        retry_before=kwargs.get('retry_before',False), events=run['events'])
                    check_fresh(task)
                    run['recovery']['reconciliations'].append({'event_id':event['event_id'],'checkpoint':current,'previous':before,'evidence':evidence})
                    run['status']='paused';run.pop('error',None);adapter.save(run)
                    return task
            if file_resolution:
                raise ValueError('File observation/retry applies only to a replacement effect')
            check_fresh(task)
            reconcile_record(run, adapter, current, kwargs['event_id'], reply_file=reply, retry_read_only=retry)
        elif action == 'transfer':
            bounded_text(kwargs['reason'], 'transfer reason')
            check_fresh(task)
            if 'repair' in task['request'] and any(e['kind']=='replacement' for e in run['events']):
                raise ValueError('Repair transfer is unavailable after replacement effects begin')
            if 'repair' in task['request']:
                from .task_contract import validate_repair_request
                candidate = copy.deepcopy(task['request'])
                candidate['answers']['assessor'] = kwargs['participant_id']
                validate_repair_request(candidate)
            transfer_record(run, adapter, current, kwargs['participant_id'], kwargs['reason'], role='assessor')
        elif action == 'cancel':
            bounded_text(kwargs['reason'], 'cancellation reason')
            cancel_record(run, adapter, current, kwargs['reason'])
        else:
            raise ValueError('Unknown task control')
        return task


def execute_repair(task, store, *, max_operations=None, exchange_factory=ReviewExchange):
    from .repair import apply_patch, decode_patch, expected_snapshot, assert_snapshot
    from .recovery import RecoveryCursor, prepare_continuation, stable_id
    from .task_runtime import guarded_execution, perform_probe, dispatch_assignment
    from .review_participants import PROTOCOL
    from .review_contract import canonical, fields, parse_json, versioned
    from .review import authorize_external
    request = task['request']
    repair = request['repair']
    scope = repair['scope']
    bound = task['bindings']['assessment']['assignments']
    # Reserve the worst-case accepted file count before the first operation.
    if request['budgets']['max_operations'] < 2 + len(bound) + len(scope['allowed']):
        raise ValueError('Accepted operation budget cannot cover the repair plan')
    if 'execution' not in task:
        task['execution'] = {'schema_version':1,'operation':'fix','status':'running',
            'run_id':request['task_id'],'requirement_revision':digest(request),'registry':request['registry'],
            'events':[],'participants':{},'record_path':str(store.path),
            'recovery':{'profile':engine_profile(request['registry']),
                        'assignments':{role:{'participant_id':a['participant_id'],'attempt_id':a['assignment_id']} for role,a in bound.items()},
                        'transfers':[],'reconciliations':[]}}
        task['recovery']['runtime'] = {'kind':'repair','version':1}
    run = task['execution']
    assignments = run['recovery']['assignments']
    selected = {role:request['registry']['participants'][a['participant_id']] for role,a in assignments.items()}
    authorize_external(selected,task['acceptance']['permissions']['external'])
    prepare_continuation(run,store)
    adapter = TaskExecutionStore(store,task)
    cursor = RecoveryCursor(run,adapter,max_operations)
    run['status']='running';run.pop('error',None)
    adapter.save(run)
    def assignment(role, payload, protocol):
        check_fresh(task)
        a=assignments[role];config=selected[role]
        outcome={'participant_id':a['participant_id'],'attempt_id':a['attempt_id'],'adapter':config['adapter'],'status':'running','tool_calls':0}
        run['participants'][role]=outcome
        turn={'task_id':request['task_id'],'attempt_id':a['attempt_id'],'turn_id':stable_id(a['attempt_id'],'0'),
              'requirement_revision':digest(request),'participant_id':a['participant_id'],
              'role':'worker' if role=='assessor' else 'reviewer',
              'objective':request['answers']['goal']+'\nAcceptance criteria: '+request['answers']['criteria'],
              'query':'','document':{'path':scope['root'],'text':canonical(payload)},
              'initial_retrieval':None,'history':[],'tools':[],'remaining_tool_calls':0,'remaining_turns':1,
              'protocol':PROTOCOL+' '+protocol,'repair':payload}
        response=dispatch_assignment(cursor,a['attempt_id']+':turn:0',turn,config,
                                     exchange_factory(config,Path(scope['root'])),outcome)
        AssessmentPolicy(task).validate_action(response['action'])
        check_fresh(task)
        outcome.update(status='completed',text=response['action']['text'])
        adapter.save(run)
        return response['action']['text']
    def steps():
        before=perform_probe(cursor,scope,'probe:before',expected=scope['before'])
        run['before_probe']=before
        if before['passed'] or before['failure'] != 'nonzero_exit' or not isinstance(before['returncode'], int) or before['returncode'] <= 0:
            raise ValueError('Repair requires an observed failing baseline probe, not an already passing or unresolved probe')
        raw=assignment('assessor',{'before_files':scope['inputs'],'before_hashes':{n:scope['before'][n]['sha256'] for n in scope['allowed']},
            'probe':scope['probe'],'baseline_result':before},
            'Return a final action whose text is JSON {"schema_version":1,"replacements":[{"path":"accepted relative path","before_sha256":"accepted hash","text":"complete replacement"}]}. Do not change the probe or claim acceptance.')
        proposal=decode_patch(raw,scope)
        run['patch']=proposal
        run['replacements']=apply_patch(scope,proposal,cursor)
        after=perform_probe(cursor,scope,'probe:after')
        run['after_probe']=after
        if not after['passed']:
            raise ValueError('Final immutable acceptance probe did not pass')
        expected=expected_snapshot(scope,run['events'])
        artifact=digest(expected)
        review_result=None
        if repair['review']!='none':
            text=assignment('reviewer',{'artifact_digest':artifact,'probe_digest':digest(after),
                'changes':[{'path':i['path'],'before':scope['inputs'][i['path']],'after':i['text']} for i in proposal['replacements']],
                'before_probe':before,'after_probe':after},
                'Review the final diff and probe independently. Return a final action whose text is JSON with schema_version 1, artifact_digest, probe_digest copied from evidence, verdict (approve/reject/uncertain), and findings (list of strings). '
                'Findings are blocking defects or material uncertainty only: any finding blocks acceptance. '
                'If you approve with no blocking issue, return verdict "approve" and findings []. '
                'Do not put positive summaries or nonblocking scope disclosures in findings. '
                'Evaluate the supplied host probe receipts within their stated scope; independent review does not require rerunning the probe. '
                'Use reject or uncertain when the evidence does not support acceptance, and explain the blocking issue in findings. Do not copy another participant verdict.')
            review_result=parse_json(text)
            fields(review_result,('schema_version','artifact_digest','probe_digest','verdict','findings'));versioned(review_result)
            if (review_result['artifact_digest']!=artifact or review_result['probe_digest']!=digest(after) or
                    review_result['verdict'] not in ('approve','reject','uncertain') or
                    not isinstance(review_result['findings'],list) or any(not isinstance(v,str) for v in review_result['findings'])):
                raise ValueError('Review does not bind the final artifact/probe or has invalid fields')
            run['review']=review_result
            if review_result['verdict']!='approve' or review_result['findings']:
                raise ValueError('Requested review has unresolved objections or uncertainty')
        assert_snapshot(scope,expected)
        check_fresh(task)
        run['integration']={'execution_status':'completed','acceptance_status':'verified_within_probe_scope',
            'artifact_digest':artifact,'probe_digest':digest(after),'review_policy':repair['review'],
            'review':review_result,'semantic_verification':False,
            'scope':'Failed-before/passed-after immutable probe and the accepted review obligation; not general correctness'}
        run['status']='completed'
    guarded_execution(run,adapter,steps)
    return task
