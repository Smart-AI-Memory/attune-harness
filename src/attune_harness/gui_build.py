"""Explicit command-build grants over registered, accepted work and owner journals."""

from concurrent.futures import ThreadPoolExecutor
import secrets

from . import task_view, work_build, work_effects
from .review_contract import digest
from .task_contract import load_task_registry
from .work_contract import PROFILE, check_work_fresh


class Builds:
    """Request-thread control; only build_work runs on the single worker thread."""

    def __init__(self, decisions):
        self.decisions = decisions
        self.previews = {}
        self.active = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='harness-build')

    def close(self):
        self.previews.clear()
        # Shutdown waits for an already-authorized owner operation. A killed
        # process leaves the owner's journal to explain any uncertain outcome.
        self.executor.shutdown(wait=True, cancel_futures=True)

    def _ready(self, task, checkpoint):
        record = self.decisions._record(task)
        if record['task_profile'] != PROFILE or record['status'] != 'accepted':
            raise ValueError('Build requires accepted feature-work intent')
        if record['checkpoint_digest'] != checkpoint:
            raise ValueError('Task changed; inspect before requesting a build')
        registry, config = load_task_registry(record['request']['config']['path'])
        if registry != record['request']['registry'] or config != record['request']['config']:
            raise ValueError('Accepted participant configuration changed')
        work_effects.validate_request_effects(record['request'])
        work_effects.require_platform(record['request'].get('effects'))
        roles, _ = work_build.preflight(record['request'])
        for assignment in roles.values():
            participant = registry['participants'][assignment['participant']]
            if participant['adapter'] != 'command' or participant['tools'] or participant.get('review_mode'):
                raise ValueError('GUI build requires configured command worker/reviewer without tools; native/provider dispatch is unavailable')
        run = record.get('build')
        if run:
            work_build.validate_build(run, record['request'])
            work_build.check_build_fresh(record)
            if run['profile'] != work_build.PROFILE or run['permissions'] != {'external': True, 'native': False}:
                raise ValueError('Resume cannot change the saved build authority')
            if run['status'] not in ('running', 'paused'):
                raise ValueError('Inspect the recorded outcome; this build cannot be dispatched again')
            if any(event['phase'] == 'dispatching' for event in run['events']):
                raise ValueError('Uncertain operation: inspect and reconcile through its owner before resuming')
        else:
            check_work_fresh(record)
        return record, roles

    def inspect(self, task):
        self.decisions._record(task)
        future = self.active.get(task)
        running = future is not None and not future.done()
        # The owner may save between reads while the worker is active. Bind
        # projection and detailed review evidence to one unchanged record.
        for _ in range(3):
            record = self.decisions._record(task)
            view = task_view.inspect(self.decisions.tasks[task])
            if digest(record) == digest(self.decisions._record(task)):
                break
        else:
            raise ValueError('Task changed during inspection; refresh saved state')
        error = None
        if future is not None and future.done():
            try:
                future.result()
            except Exception as exc:
                error = str(exc)
        reviews = []
        run = record.get('build', {})
        for event in run.get('events', []):
            if event['kind'] != 'participant_turn' or event['state'] != 'completed':
                continue
            participant = run.get('participants', {}).get('reviewer:final')
            if participant and participant['attempt_id'] == event['attempt_id']:
                reviews.append(work_build.decode(event['result']['action'], record['request'],
                               'reviewer', {'id': 'final'},
                               contract_version=work_build.build_response_contract(run)))
        result = {'running': running, 'view': view, 'reviews': reviews,
                  'available': False, 'error': error}
        if running:
            result['note'] = 'Owner operation running. Refresh inspects it; closing the page does not cancel it.'
        else:
            try:
                self._ready(task, view['checkpoint_digest'])
                result['available'] = True
                result['note'] = 'Preview the accepted command build before granting execution.'
            except (ValueError, OSError, RuntimeError) as exc:
                result['note'] = str(exc)
        return result

    def preview(self, task, checkpoint):
        if any(not future.done() for future in self.active.values()):
            raise ValueError('A build is already running; inspect its outcome first')
        record, roles = self._ready(task, checkpoint)
        request = record['request']
        grant = secrets.token_urlsafe(24)
        self.previews[task] = (grant, digest(record))
        return {'task': task, 'checkpoint': checkpoint, 'grant': grant,
                'goal': request['intent']['goal'], 'resume': 'build' in record,
                'effects': request['effects'], 'tasks': request['tasks'],
                'budgets': request['budgets'], 'participants': [
                    {'role': role, 'id': assignment['participant'],
                     'configuration': request['registry']['participants'][assignment['participant']],
                     'budgets': assignment['budgets']} for role, assignment in roles.items()]}

    def start(self, task, checkpoint, grant, confirmed):
        if confirmed is not True:
            raise ValueError('Explicit command and file-effect confirmation required')
        self.decisions._record(task)  # Validate opaque identity before dict lookup.
        if not isinstance(grant, str):
            raise ValueError('Expected the displayed build grant')
        preview = self.previews.pop(task, None)
        record, _ = self._ready(task, checkpoint)
        if preview != (grant, digest(record)):
            raise ValueError('Build preview expired or changed; inspect and preview again')
        if any(not future.done() for future in self.active.values()):
            raise ValueError('A build is already running; inspect its outcome first')
        self.active[task] = self.executor.submit(
            work_build.build_work, self.decisions.tasks[task], checkpoint=checkpoint,
            allow_external=True, allow_native=False)
        return {'message': 'Command build granted. Inspect recorded progress; never retry an uncertain submission.'}
