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

    def validate_action(self, action):
        if action['kind'] != 'final':
            raise ValueError('Assessment assignment requires a final response, not another tool call')
        if len(action['text'].encode('utf-8')) > self.task['request']['budgets']['max_output_bytes']:
            raise ValueError('Assignment exceeded accepted output budget')

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


def execute_task(directory, *, checkpoint=None, max_operations=None, exchange_factory=ReviewExchange):
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
        execute_assessment(task['execution'], TaskExecutionStore(store, task), prepared,
            allow_external=grants['external'], allow_provider=grants['provider'],
            max_operations=max_operations, exchange_factory=exchange_factory,
            services=(retrieve_sources, verify_document, authorize_external), policy=AssessmentPolicy(task))
        return task


def validate_execution(task):
    from .recovery import validate_events
    execution = task['execution']
    request = task['request']
    if (execution['operation'] != 'review' or execution['schema_version'] != 1 or
            execution['status'] != task['status'] or execution['run_id'] != request['task_id'] or
            execution['requirement_revision'] != digest(request) or
            execution['record_path'] != task['record_path'] or execution['registry'] != request['registry'] or
            execution['recovery']['profile'] != engine_profile(request['registry'])):
        raise ValueError('Execution differs from accepted task identity/profile')
    expected = {role: {'participant_id': a['participant_id'], 'attempt_id': a['assignment_id']}
                for role, a in task['bindings']['assessment']['assignments'].items()}
    if execution['recovery']['assignments'] != expected:
        raise ValueError('Execution assignments differ from accepted task bindings')
    validate_events(execution)
    if len(execution['events']) > request['budgets']['max_operations']:
        raise ValueError('Execution exceeds accepted operation budget')
