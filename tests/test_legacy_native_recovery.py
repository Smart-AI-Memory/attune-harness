"""# qualify: platform
Legacy timeout recovery retains attributed observations without inventing host evidence.
"""
import copy
import hashlib
import json

import pytest

from attune_harness.native import NativeError
from attune_harness.task_contract import read_task
from attune_harness.work_build import reconcile_native_build, validate_build
from attune_harness.work_runtime import build_work
from test_work_build import Worker, prepare, work, reset_worker


class LegacyTimeout(Worker):
    def __call__(self, raw):
        raise NativeError('codex: timeout_effects_unknown: fixture diagnostic')


def blocked(work):
    config = json.loads(work[1].read_text())
    config['participants']['local'] = {
        'adapter': 'codex', 'model': 'fixture-model', 'tools': [],
        'max_turns': 1, 'max_tool_calls': 0, 'timeout': 2,
    }
    work[1].write_text(json.dumps(config))
    case = prepare(work)
    record = build_work(case[1], allow_native=True, allow_external=True,
                        exchange_factory=LegacyTimeout)
    # Reproduce the historical journal: older hosts did not retain this field.
    record['build']['events'][-1].pop('native_failure', None)
    from attune_harness.review_store import RunStore
    RunStore(case[1], existing=True).save(record)
    observation = {
        'schema_version': 1, 'task_id': record['request']['task_id'],
        'checkpoint': record['checkpoint_digest'],
        'event_id': record['build']['events'][-1]['event_id'],
        'observer': 'fixture operator', 'observed_at': '2026-09-26T10:00:00+00:00',
        'statement': 'direct_process_stopped',
        'evidence': 'Test fixture observed the direct process exit.',
        'acknowledge_unknown_effects': True,
    }
    path = case[1].parent / 'observation.json'
    path.write_text(json.dumps(observation))
    return case, record, path, observation


def reconcile(case, record, path):
    return reconcile_native_build(case[1], record['checkpoint_digest'],
                                  record['build']['events'][-1]['event_id'],
                                  stop_observation=path)


def test_legacy_stop_observation_preserves_evidence_and_retries_once(work):
    case, original, path, observation = blocked(work)
    with pytest.raises(ValueError, match='saved stopped-process evidence'):
        reconcile(case, original, None)
    recovered = reconcile(case, original, path)
    event = recovered['build']['events'][-1]
    receipt = event['native_retry']
    assert event['attempts'] == 2 and event['effect_class'] == 'unknown'
    assert 'native_failure' not in receipt['previous']
    assert receipt['previous'] == original['build']['events'][-1]
    assert receipt['kind'] == 'explicit_legacy_native_timeout_retry'
    evidence = receipt['stop_observation']
    assert evidence['text'] == path.read_text()
    assert evidence['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert evidence['provenance'] == 'operator_assertion'
    assert recovered['build']['status'] == 'paused'
    assert not Worker.seen  # Reconciliation never dispatches.
    path.write_text('no longer available')
    validate_build(recovered['build'], recovered['request'])
    done = build_work(case[1], allow_native=True, allow_external=True, exchange_factory=Worker)
    assert done['build']['status'] == 'completed'
    calls = len(Worker.seen)
    assert build_work(case[1], allow_native=True, allow_external=True, exchange_factory=Worker) == done
    assert len(Worker.seen) == calls


@pytest.mark.parametrize('change', ['task_id', 'checkpoint', 'event_id', 'observer', 'evidence',
                                    'acknowledge_unknown_effects', 'statement', 'observed_at',
                                    'schema_version', 'extra', 'oversize', 'malformed'])
def test_invalid_observation_cannot_mutate_task(work, change):
    case, record, path, observation = blocked(work)
    changes = {'task_id': 'other', 'checkpoint': '0' * 64, 'event_id': 'other',
               'observer': ' ', 'evidence': '', 'acknowledge_unknown_effects': False,
               'statement': 'probably_stopped', 'observed_at': '2026-09-26T10:00:00',
               'schema_version': True, 'extra': 'not allowed'}
    if change in changes:
        observation[change] = changes[change]
    path.write_text('x' * 16385 if change == 'oversize' else '{' if change == 'malformed'
                    else json.dumps(observation))
    with pytest.raises(ValueError):
        reconcile(case, record, path)
    assert read_task(case[1]) == record


@pytest.mark.parametrize('change', ['stale', 'checkout', 'registry', 'not_timeout', 'native_receipt'])
def test_legacy_recovery_preserves_authority_and_eligibility(work, change):
    case, record, path, observation = blocked(work)
    if change == 'stale':
        supplied = copy.deepcopy(record)
        supplied['checkpoint_digest'] = '0' * 64
    else:
        supplied = record
    if change == 'checkout':
        (case[0] / 'source.py').write_text('changed')
    elif change == 'registry':
        work[1].write_text(work[1].read_text() + '\n')
    elif change in ('not_timeout', 'native_receipt'):
        event = record['build']['events'][-1]
        if change == 'not_timeout':
            event['error']['detail'] = 'codex: nonzero_exit: timeout_effects_unknown'
        else:
            event['native_failure'] = {'failure': 'timeout_effects_unknown', 'process_stopped': False}
        from attune_harness.review_store import RunStore
        RunStore(case[1], existing=True).save(record)
    with pytest.raises((ValueError, RuntimeError)):
        reconcile(case, supplied, path)
    assert read_task(case[1]) == record


@pytest.mark.parametrize('change', ['hash', 'binding', 'provenance', 'orphan', 'previous', 'kind'])
def test_legacy_receipt_tampering_rejected(work, change):
    case, record, path, observation = blocked(work)
    recovered = reconcile(case, record, path)
    event = recovered['build']['events'][-1]
    receipt = event['native_retry']
    evidence = receipt['stop_observation']
    if change == 'hash':
        evidence['text'] += ' '
    elif change == 'binding':
        observation['event_id'] = 'different'
        evidence['text'] = json.dumps(observation)
        evidence['sha256'] = hashlib.sha256(evidence['text'].encode()).hexdigest()
    elif change == 'provenance':
        evidence['provenance'] = 'host_verified'
    elif change == 'orphan':
        event.pop('native_retry')
    elif change == 'previous':
        receipt['previous']['native_failure'] = {'failure': 'timeout_effects_unknown', 'process_stopped': True}
    else:
        receipt['kind'] = 'explicit_native_timeout_retry'
    with pytest.raises(ValueError):
        validate_build(recovered['build'], recovered['request'])


def test_cli_legacy_observation_requires_retry_and_only_prepares(work, capsys):
    from attune_harness.cli import main
    case, record, path, observation = blocked(work)
    args = ['reconcile-task', str(case[1]), '--event', observation['event_id'],
            '--checkpoint', record['checkpoint_digest'], '--stop-observation', str(path)]
    assert main([*args, '--retry-before']) == 2
    assert '--stop-observation requires --retry-native' in capsys.readouterr().out
    assert read_task(case[1]) == record
    assert main([*args, '--retry-native']) in (0, 1)
    assert read_task(case[1])['build']['status'] == 'paused'
    assert not Worker.seen


def test_legacy_recovery_cannot_authorize_a_second_retry(work):
    case, original, path, observation = blocked(work)
    reconcile(case, original, path)
    failed_again = build_work(case[1], allow_native=True, allow_external=True,
                              exchange_factory=LegacyTimeout)
    with pytest.raises(ValueError, match='first Codex timeout'):
        reconcile(case, failed_again, path)
    assert read_task(case[1]) == failed_again


def test_legacy_guidance_requires_independent_observation(work):
    from attune_harness.work_cli import present
    case, original, path, observation = blocked(work)
    shown = present(case[1], inspect_only=True)
    assert '--stop-observation' in shown['next_action']
    assert 'operator assertion' in shown['next_action']
    assert 'unavailable' in shown['next_action']
    assert read_task(case[1]) == original
