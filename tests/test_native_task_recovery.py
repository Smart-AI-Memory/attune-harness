"""Native review turns refused before any answer: one explicit retry from saved evidence (#182)."""
import json

import pytest

from attune_harness.cli import main
from attune_harness.native import NativeError
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import control_task, execute_task
from test_review import case, change
from test_task_contract import draft, response


def native(case, adapter='claude'):
    change(case[1], lambda value: value.update(participants={
        name: {'adapter': adapter, 'model': 'configured-model', 'review_mode': 'evidence',
               'timeout': 10, 'tools': ['retrieve', 'verify'], 'max_turns': 3, 'max_tool_calls': 2}
        for name in ('alpha', 'beta')}))
    draft(case, plan='independent-review')
    submission = response(case[2])
    submission['permissions']['external'] = True
    accept_task(case[2], submission)


def refusing(calls, *, fail=('beta',), failure='nonzero_exit', stopped=True):
    """Answer finally, except each named participant's first call, which the CLI refuses."""
    def factory(config, cwd):
        def exchange(raw):
            data = json.loads(raw)
            participant = data['turn']['participant_id']
            calls.append(participant)
            if participant in fail and calls.count(participant) == 1:
                raise NativeError('claude: nonzero_exit: fixture refusal',
                                  failure=failure, process_stopped=stopped)
            return json.dumps({'schema_version': 1, 'request_digest': data['request_digest'],
                               'action': {'kind': 'final', 'text': f'{participant} assessment'}})
        return exchange
    return factory


def failed_turn(task):
    return next(e for e in task['execution']['events']
                if e['kind'] == 'participant_turn' and e['state'] == 'failed')


def test_refused_native_turn_saves_evidence_and_retries_once(case):
    native(case)
    calls = []
    failed = execute_task(case[2], exchange_factory=refusing(calls))
    assert failed['status'] == 'failed'
    event = failed_turn(failed)
    assert event['participant_id'] == 'beta' and event['effects'] == 'unknown'
    assert event['native_failure'] == {'failure': 'nonzero_exit', 'process_stopped': True}
    # The completed assessor turn is kept; the refusal alone blocks continuation.
    with pytest.raises(UnresolvedOperation):
        execute_task(case[2], exchange_factory=refusing(calls))
    with pytest.raises(UnresolvedOperation, match='read-only'):
        control_task(case[2], 'reconcile', event_id=event['event_id'], retry_read_only=True)

    control_task(case[2], 'reconcile', event_id=event['event_id'], retry_native=True)
    paused = read_task(case[2])
    assert paused['status'] == 'paused'
    receipt = paused['execution']['recovery']['reconciliations'][-1]
    assert receipt['evidence'] == {'kind': 'explicit_native_retry', 'effects': 'unknown',
                                   'native_failure': event['native_failure']}
    assert receipt['previous'] == event

    done = execute_task(case[2], exchange_factory=refusing(calls))
    assert done['status'] == 'completed'
    assert calls == ['alpha', 'beta', 'beta']  # the assessor is not paid for twice
    retried = next(e for e in done['execution']['events'] if e['event_id'] == event['event_id'])
    assert retried['attempts'] == 2 and 'native_failure' not in retried


def test_second_refusal_exhausts_the_retry(case):
    native(case)
    calls = []
    failed = execute_task(case[2], exchange_factory=refusing(calls))
    event = failed_turn(failed)
    control_task(case[2], 'reconcile', event_id=event['event_id'], retry_native=True)
    again = execute_task(case[2], exchange_factory=refusing([]))  # refuses beta again
    event = failed_turn(again)
    assert event['attempts'] == 2
    before = read_task(case[2])
    with pytest.raises(ValueError, match='limit exhausted'):
        control_task(case[2], 'reconcile', event_id=event['event_id'], retry_native=True)
    assert read_task(case[2]) == before


@pytest.mark.parametrize('failure,stopped', [
    ('nonzero_exit', False),            # exit code unknown: the process may still run
    ('cancelled_effects_unknown', True),
    ('output_limit', True),
])
def test_retry_needs_stopped_process_evidence(case, failure, stopped):
    native(case)
    failed = execute_task(case[2], exchange_factory=refusing([], failure=failure, stopped=stopped))
    before = read_task(case[2])
    with pytest.raises(UnresolvedOperation, match='stopped-process evidence'):
        control_task(case[2], 'reconcile', event_id=failed_turn(failed)['event_id'], retry_native=True)
    assert read_task(case[2]) == before


def test_record_without_saved_evidence_stays_unresolved(case):
    """Records written before this evidence was saved cannot be retried from error text."""
    native(case)
    failed = execute_task(case[2], exchange_factory=refusing([]))
    from attune_harness.review_store import RunStore
    record = read_task(case[2])
    for event in record['execution']['events']:
        event.pop('native_failure', None)
    RunStore(case[2], existing=True).save(record)
    with pytest.raises(UnresolvedOperation, match='stopped-process evidence'):
        control_task(case[2], 'reconcile', event_id=failed_turn(failed)['event_id'], retry_native=True)


def test_deterministic_turn_is_not_a_native_retry(case, monkeypatch):
    from attune_harness import retrieval
    draft(case)
    accept_task(case[2], response(case[2]))
    with monkeypatch.context() as m:
        m.setattr(retrieval, 'retrieve_sources',
                  lambda *a, **k: (_ for _ in ()).throw(RuntimeError('read failed')))
        failed = execute_task(case[2])
    event = failed['execution']['events'][-1]
    with pytest.raises(UnresolvedOperation, match='native participant turn'):
        control_task(case[2], 'reconcile', event_id=event['event_id'], retry_native=True)


def test_reconcile_task_cli_retries_review_turn(case, capsys):
    native(case)
    failed = execute_task(case[2], exchange_factory=refusing([]))
    event = failed_turn(failed)
    assert main(['reconcile-task', str(case[2]), '--event', event['event_id'],
                 '--stop-observation', str(case[2] / 'none.json'), '--retry-native']) != 0
    assert 'feature builds' in capsys.readouterr().out
    # An authorized retry pauses the task for resume; paused exits 1 by design.
    assert main(['reconcile-task', str(case[2]), '--event', event['event_id'], '--retry-native']) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'paused'
    assert result['execution']['recovery']['reconciliations'][-1]['evidence']['kind'] == 'explicit_native_retry'
