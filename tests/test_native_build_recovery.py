"""# qualify: platform
Explicit retry preserves unknown effects and host stopped-process evidence.
"""

import copy
import json

import pytest

from attune_harness.native import NativeError
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import read_task
from attune_harness.work_build import reconcile_native_build, validate_build
from attune_harness.work_runtime import build_work
from test_work_build import Worker, prepare, work, reset_worker


class TimeoutWorker(Worker):
    def __call__(self, raw):
        from attune_harness.work_build import PROFILE
        self.last_identity = {'adapter': 'codex', 'requested_model': self.config['model'],
                              'profile': PROFILE, 'declared_role': json.loads(raw)['turn']['role'],
                              'user_config_policy': 'requested_isolation',
                              'dispatch_argv': ['codex', 'exec', '--ignore-user-config']}
        raise NativeError('fixture timeout', failure='timeout_effects_unknown', process_stopped=True)


def blocked(work):
    config = json.loads(work[1].read_text())
    config['participants']['local'] = {
        'adapter': 'codex', 'model': 'fixture-model', 'tools': [],
        'max_turns': 1, 'max_tool_calls': 0, 'timeout': 2,
    }
    work[1].write_text(json.dumps(config))
    case = prepare(work)
    result = build_work(case[1], allow_native=True, allow_external=True, exchange_factory=TimeoutWorker)
    assert result['build']['status'] == 'unresolved'
    return case, result


def test_timeout_retry_is_explicit_bounded_and_does_not_replay(work):
    case, record = blocked(work)
    event = copy.deepcopy(record['build']['events'][-1])
    with pytest.raises(UnresolvedOperation):
        build_work(case[1], allow_native=True, allow_external=True, exchange_factory=Worker)
    recovered = reconcile_native_build(case[1], record['checkpoint_digest'], event['event_id'])
    retry = recovered['build']['events'][-1]
    assert retry['native_retry']['previous'] == event
    assert retry['effect_class'] == 'unknown' and retry['attempts'] == 2
    done = build_work(case[1], allow_native=True, allow_external=True, exchange_factory=Worker)
    assert done['build']['status'] == 'completed'
    calls = len(Worker.seen)
    assert build_work(case[1], allow_native=True, allow_external=True, exchange_factory=Worker) == done
    assert len(Worker.seen) == calls
    receipt = next(e for e in done['build']['events'] if 'native_retry' in e)['native_retry']
    assert receipt['previous'] == event
    identity = receipt['previous_participant']['outcome']['last_identity']
    assert identity['requested_model'] == 'fixture-model'
    assert identity['dispatch_argv'] == ['codex', 'exec', '--ignore-user-config']


def test_second_timeout_cannot_be_retried(work):
    case, record = blocked(work)
    event = record['build']['events'][-1]
    reconcile_native_build(case[1], record['checkpoint_digest'], event['event_id'])
    twice = build_work(case[1], allow_native=True, allow_external=True, exchange_factory=TimeoutWorker)
    with pytest.raises(ValueError, match='first Codex timeout'):
        reconcile_native_build(case[1], twice['checkpoint_digest'], event['event_id'])
    assert read_task(case[1]) == twice


@pytest.mark.parametrize('mutation', ['attempt', 'orphan', 'previous', 'binding', 'participant', 'identity'])
def test_retry_receipt_tampering_is_rejected(work, mutation):
    case, record = blocked(work)
    event = record['build']['events'][-1]
    recovered = reconcile_native_build(case[1], record['checkpoint_digest'], event['event_id'])
    run = copy.deepcopy(recovered['build'])
    event = run['events'][-1]
    if mutation == 'attempt':
        event['attempts'] = 1
    elif mutation == 'orphan':
        del event['native_retry']
    elif mutation == 'previous':
        event['native_retry']['previous']['native_failure']['process_stopped'] = False
    elif mutation == 'participant':
        event['native_retry']['previous_participant']['outcome']['attempt_id'] = 'different'
    elif mutation == 'identity':
        event['native_retry']['previous_participant']['outcome']['last_identity']['requested_model'] = 'different'
    else:
        event['native_retry']['previous']['event_id'] = 'different-event'
    with pytest.raises(ValueError):
        validate_build(run, recovered['request'])


@pytest.mark.parametrize('change', ['stale', 'checkout', 'config'])
def test_retry_requires_current_authority_and_unchanged_checkout(work, change):
    case, record = blocked(work)
    event = record['build']['events'][-1]
    checkpoint = record['checkpoint_digest']
    if change == 'stale':
        checkpoint = '0' * 64
    elif change == 'checkout':
        (case[0] / 'source.py').write_text('changed')
    else:
        work[1].write_text(work[1].read_text() + '\n')
    with pytest.raises((ValueError, UnresolvedOperation)):
        reconcile_native_build(case[1], checkpoint, event['event_id'])
    assert read_task(case[1]) == record


@pytest.mark.parametrize('failure,stopped', [(None, False), ('timeout_effects_unknown', False), ('nonzero_exit', True)])
def test_legacy_or_unsafe_native_failure_has_no_retry(work, failure, stopped):
    case, record = blocked(work)
    run = copy.deepcopy(record['build'])
    event = run['events'][-1]
    if failure is None:
        event.pop('native_failure')
    else:
        event['native_failure'] = {'failure': failure, 'process_stopped': stopped}
    # Legacy records remain readable, but are never guessed into retry authority.
    validate_build(run, record['request'])
    from attune_harness.work_build import _retryable_native_event
    with pytest.raises(ValueError, match='saved stopped-process evidence'):
        _retryable_native_event(event, record['request'])


def test_native_retry_cli_requires_checkpoint_and_only_prepares(work, capsys):
    from attune_harness.cli import main
    case, record = blocked(work)
    event = record['build']['events'][-1]
    args = ['reconcile-task', str(case[1]), '--event', event['event_id'], '--retry-native']
    assert main(args) == 2
    assert 'current --checkpoint' in capsys.readouterr().out
    assert read_task(case[1]) == record
    assert main([*args, '--checkpoint', record['checkpoint_digest']]) in (0, 1)
    after = read_task(case[1])
    assert after['build']['status'] == 'paused'
    assert after['build']['events'][-1]['phase'] == 'prepared'


def test_status_explains_native_retry_eligibility_without_authorizing(work):
    from attune_harness.work_cli import present, _guidance
    case, record = blocked(work)
    shown = present(case[1], inspect_only=True)
    assert '--retry-native' in shown['next_action']
    assert read_task(case[1]) == record
    legacy = copy.deepcopy(record)
    legacy['build']['events'][-1].pop('native_failure')
    assert 'unavailable' in _guidance(legacy, shown)[2]
