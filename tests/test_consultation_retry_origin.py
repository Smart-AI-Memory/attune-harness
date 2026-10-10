"""Marked-policy retry journeys retain provenance before calls and during inspection."""
# qualify: platform

import copy
import json
from pathlib import Path

import pytest

from attune_harness import consultation as c
from attune_harness import recovery
from attune_harness.cli import main
from attune_harness.review_store import RunStore
from test_consultation_partial import bytes_of, completed, failed, no_dispatch, prepare, run, stopped


OWNER_MODULES = {'attune_harness.consultation', 'attune_harness.recovery', 'attune_harness.process'}


def mark(directory, record):
    record['capture_policy'] = copy.deepcopy(recovery.CAPTURE_POLICY)
    RunStore(directory, existing=True).save(record)
    assert c.load(directory) == record
    return record


def dispatched_event(directory, turn):
    """Inspect the durable boundary before any participant stub produces its result."""
    record = json.loads((Path(directory) / 'record.json').read_text(encoding='utf-8'))
    key = f"{turn['round']}:{turn['participant']}"
    event = next(event for event in record['events'] if event['operation_key'] == key)
    assert event['phase'] == 'dispatching'
    assert 'runtime_origin' in event
    origin = event['runtime_origin']
    assert origin['attempt'] == event['attempts']
    assert {module['name'] for module in origin['modules']} == OWNER_MODULES
    assert c.load(directory) == record
    return copy.deepcopy(event)


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_marked_prepared_dispatch_captures_origin_before_every_stub_call(tmp_path, operation):
    directory, initial = prepare(tmp_path, operation)
    mark(directory, initial)
    observed = []
    def dispatch(seat, turn, *args):
        event = dispatched_event(directory, turn)
        assert event['attempts'] == 1
        observed.append(event)
        return completed(seat)
    record = run(directory, initial, dispatch)
    assert record['status'] == 'completed'
    assert len(observed) == len(initial['contract']['configuration']['participants'])
    assert all(event['runtime_origin']['attempt'] == 1 for event in record['events'])
    assert c.load(directory) == record


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_marked_failed_turn_reconciles_then_fresh_attempt_two_captures_before_dispatch(tmp_path, monkeypatch, operation):
    directory, initial = prepare(tmp_path, operation)
    mark(directory, initial)
    captures = []
    real_factory = recovery.dispatch_origin_callback
    def factory(*names):
        assert set(names) == OWNER_MODULES
        real_capture = real_factory(*names)
        def capture():
            origin = real_capture()
            captures.append(copy.deepcopy(origin))
            return origin
        return capture
    monkeypatch.setattr(recovery, 'dispatch_origin_callback', factory)
    calls = []
    def dispatch(seat, turn, *args):
        event = dispatched_event(directory, turn)
        calls.append((turn['participant'], event['attempts']))
        assert len(captures) >= event['attempts']
        return failed(seat) if turn['participant'] == 'reviewer' else completed(seat)
    first = run(directory, initial, dispatch)
    assert first['status'] == ('failed' if operation == 'source-review' else 'partial')
    assert len(captures) == len(first['events'])
    prior = copy.deepcopy(first['events'][0])
    siblings = copy.deepcopy(first['events'][1:])
    reopened = c.reconcile(directory, first['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert reopened['events'][0]['attempts'] == 2
    assert 'runtime_origin' not in reopened['events'][0]
    assert reopened['recovery']['reconciliations'][0]['previous'] == prior
    assert reopened['events'][1:] == siblings
    assert c.load(directory) == reopened
    captures_before_retry = len(captures)
    calls.clear()
    def retry(seat, turn, *args):
        event = dispatched_event(directory, turn)
        assert len(captures) == captures_before_retry + 1
        assert event['attempts'] == event['runtime_origin']['attempt'] == 2
        assert event['runtime_origin']['modules'] == captures[-1]['modules']
        calls.append((turn['participant'], event['attempts']))
        return completed(seat)
    final = run(directory, initial, retry)
    assert final['status'] == 'completed'
    assert calls == [('reviewer', 2)]
    assert len(captures) == captures_before_retry + 1
    assert final['events'][1:] == siblings
    assert final['recovery']['reconciliations'][0]['previous']['runtime_origin']['attempt'] == 1
    assert final['events'][0]['runtime_origin']['attempt'] == 2
    assert c.load(directory) == final


@pytest.mark.parametrize('operation,fail_on_capture', [('source-review', 1), ('roundtable', 2)])
def test_origin_capture_failure_dispatches_no_admitted_seat(tmp_path, monkeypatch, operation, fail_on_capture):
    directory, initial = prepare(tmp_path, operation)
    mark(directory, initial)
    calls = []
    real_factory = recovery.dispatch_origin_callback
    def factory(*names):
        real_capture = real_factory(*names)
        def capture():
            calls.append(names)
            if len(calls) == fail_on_capture:
                raise ValueError('Offline origin capture failure')
            return real_capture()
        return capture
    monkeypatch.setattr(recovery, 'dispatch_origin_callback', factory)
    with pytest.raises(ValueError, match='Offline origin capture failure'):
        run(directory, initial, no_dispatch)
    assert len(calls) == fail_on_capture
    retained = c.load(directory)
    assert retained['status'] == 'unresolved'
    assert retained['answers'] == []
    assert all(event['phase'] != 'completed' for event in retained['events'])
    assert retained['events'][-1]['phase'] == 'prepared'
    assert 'runtime_origin' not in retained['events'][-1]


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_legacy_unmarked_prepare_and_run_do_not_add_an_origin_policy(tmp_path, monkeypatch, operation):
    directory, initial = prepare(tmp_path, operation)
    assert 'capture_policy' not in initial
    assert initial['recovery'] == {'profile': c.PROFILE}
    assert initial['events'] == initial['answers'] == []
    monkeypatch.setattr(recovery, 'dispatch_origin_callback', no_dispatch)
    record = run(directory, initial, lambda seat, *args: completed(seat))
    assert record['status'] == 'completed'
    assert 'capture_policy' not in record
    assert record['recovery'] == {'profile': c.PROFILE}
    assert record['contract'] == initial['contract']
    assert all('runtime_origin' not in event for event in record['events'])
    assert c.load(directory) == record


def test_reconcile_clears_seeded_current_origin_and_retains_the_prior_attempt_origin(tmp_path):
    directory, _, record, _ = stopped(tmp_path, 'source-review')
    origin = recovery.capture_runtime_origin(tuple(sorted(OWNER_MODULES)))
    origin['attempt'] = 1
    record['events'][0]['runtime_origin'] = copy.deepcopy(origin)
    mark(directory, record)
    previous = copy.deepcopy(record['events'][0])
    try:
        reopened = c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    except Exception as exc:
        pytest.fail(f'Valid seeded-origin retry transition refused: {type(exc).__name__}: {exc}')
    assert 'runtime_origin' not in reopened['events'][0]
    assert reopened['recovery']['reconciliations'][0]['previous'] == previous
    assert c.load(directory) == reopened


def test_retry_cap_refuses_explicitly_before_persistence_or_history_change(tmp_path, monkeypatch):
    directory, initial, record, _ = stopped(tmp_path, 'source-review')
    c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    second = run(directory, initial, lambda seat, *args: failed(seat))
    before = bytes_of(directory)
    history = copy.deepcopy(second['recovery']['reconciliations'])
    monkeypatch.setattr(RunStore, 'save', no_dispatch)
    with pytest.raises(ValueError, match='Refused-turn retry limit exhausted'):
        c.reconcile(directory, second['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before
    assert c.load(directory)['recovery']['reconciliations'] == history


@pytest.mark.parametrize('basis', ['not_launched', 'cli_refusal'])
@pytest.mark.parametrize('view', ['status', 'evidence'])
@pytest.mark.parametrize('completed_retry', [False, True])
def test_markdown_retry_attempt_and_retained_failure_evidence_do_not_mutate_record(tmp_path, capsys, monkeypatch, basis, view, completed_retry):
    directory, initial, record, _ = stopped(tmp_path, 'source-review', basis)
    reopened = c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    if completed_retry:
        record = run(directory, initial, lambda seat, *args: completed(seat))
    else:
        record = reopened
        assert record['answers'] == []
        assert record['events'][0]['phase'] == 'prepared'
    before = bytes_of(directory)
    monkeypatch.setattr(c, 'run', no_dispatch)
    assert main(['source-review', view, str(directory), '--format', 'markdown']) == 0
    output = capsys.readouterr().out
    assert '**Status:** ' + ('completed' if completed_retry else 'paused') in output
    assert '**Attempts:** 2' in output
    assert '**Prior turn status:** failed' in output
    assert '**Retry basis:** ' + basis.replace('_', '\\_') in output
    assert '**Provenance:** ' in output
    assert 'retry authorized by the operator' in output
    assert '**Prior turn error:** type=NativeError' in output
    assert 'Offline fixture failure' in output
    assert 'effects=unknown' in output
    if basis == 'not_launched':
        assert 'Process launch raised before a process existed' in output
    else:
        assert 'CLI structured error result with no reported model usage' in output
        assert 'usage may repeat' in output
    if not completed_retry:
        assert '**Unresolved journal entry:** 0:reviewer; phase prepared; effects remain unknown.' in output
    assert bytes_of(directory) == before
    assert c.load(directory) == record
