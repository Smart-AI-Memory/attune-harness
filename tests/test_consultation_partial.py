"""Offline acceptance journeys for parallel seats and explicit failed-turn recovery."""
# qualify: platform

import copy
import json
import shutil
from threading import Barrier, Event, Thread, get_ident

import pytest

from attune_harness import consultation as c
from attune_harness.cli import main
from attune_harness.native import NativeExchange
from attune_harness.process import ProcessResult
from attune_harness.review_store import PersistenceError, RunStore


def configuration(operation='roundtable', *, rounds=1, seats=2, native=False):
    participants = {}
    for index, name in enumerate(('reviewer', 'critic', 'observer')[:seats]):
        participants[name] = {'adapter': 'command',
            'identity': {'provider': f'offline-{index}', 'model': f'fixture-{index}'},
            'timeout': 1, 'command': ['never-launched']}
    if native:
        participants['reviewer'] = {'adapter': 'claude',
            'identity': {'provider': 'claude', 'model': 'fixture-claude-1'}, 'timeout': 1}
    if operation == 'source-review':
        participants = {'reviewer': participants['reviewer']}
        rounds = 1
    return {'schema_version': 1, 'question': 'Inspect frozen source',
            'author': {'provider': 'codex', 'model': 'gpt-6.1-sol'},
            'participants': participants, 'rounds': rounds}


def prepare(tmp_path, operation='roundtable', **options):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'x.py').write_bytes(b'first = 1\nsecond = 2\n')
    directory = tmp_path / 'run'
    record = c.prepare(operation, source, ['x.py'], configuration(operation, **options), directory)
    return directory, record


def completed(seat, summary='Retained offline answer'):
    return {'status': 'completed',
            'answer': {'verdict': 'uncertain', 'summary': summary, 'evidence': []},
            'error': None, 'identity': {'configured': seat['identity'], 'reported': None,
                'authenticated_model': False}, 'provider_usage': None, 'process': None}


def failed(seat, basis='not_launched', *, failure='not_found'):
    if basis == 'cli_refusal':
        failure, returncode = 'nonzero_exit', 1
        refusal = {'kind': 'claude_structured_error', 'returncode': returncode,
                   'result': 'Offline fixture refusal', 'model_usage': {}}
    else:
        returncode = None if basis == 'not_launched' else -9
        refusal = None
    error = {'type': 'NativeError', 'detail': 'Offline fixture failure',
             'failure': failure, 'refusal': refusal,
             'process_stopped': returncode is not None, 'effects': 'unknown'}
    if basis is not None:
        error['retry_basis'] = basis
    return {'status': 'failed', 'answer': None, 'error': error,
            'identity': {'configured': seat['identity'], 'reported': None,
                'authenticated_model': False}, 'provider_usage': None,
            'process': {'argv': ['offline-cli'], 'returncode': returncode,
                        'stdout': '', 'stderr': 'offline fixture', 'failure': failure}}


def cancelled(seat):
    result = failed(seat, None, failure='cancelled_effects_unknown')
    result['status'] = 'cancelled'
    return result


def run(directory, record, dispatcher, **options):
    return c.run(directory, record['contract_digest'], allow_external=True,
                 allow_native=True, dispatcher=dispatcher, **options)


def stopped(tmp_path, operation='roundtable', basis='not_launched', *, failure='not_found', rounds=1):
    directory, initial = prepare(tmp_path, operation, rounds=rounds, native=basis == 'cli_refusal')
    calls = []
    def dispatch(seat, turn, *args):
        calls.append((turn['round'], turn['participant']))
        if turn['participant'] == 'reviewer' and turn['round'] == rounds - 1:
            return failed(seat, basis, failure=failure)
        return completed(seat, turn['participant'])
    record = run(directory, initial, dispatch)
    return directory, initial, record, calls


def bytes_of(directory):
    return (directory / 'record.json').read_bytes()


def no_dispatch(*args, **kwargs):
    pytest.fail('This inspection or refused recovery dispatched a seat')


def frozen_turn(record):
    return {'attempt_id': 'offline-turn', 'contract_digest': record['contract_digest'],
            'participant': 'reviewer', 'round': 0,
            'question': record['contract']['configuration']['question'],
            'snapshot': record['contract']['snapshot'], 'previous_rounds': []}


@pytest.mark.parametrize('failure,returncode,expected', [
    ('not_found', None, 'not_launched'), ('launch_failed', None, 'not_launched'),
    ('not_found', 1, None), ('launch_failed', 1, None),
    ('timeout_effects_unknown', -9, None), ('output_limit', -9, None),
    ('invalid_utf8', 1, None), ('cancelled_before_start', None, None),
])
def test_dispatch_only_produces_not_launched_from_a_preprocess_failure_receipt(tmp_path, monkeypatch, failure, returncode, expected):
    directory, record = prepare(tmp_path, 'source-review')
    calls = []
    def invoke(argv, raw, **kwargs):
        calls.append(argv)
        return ProcessResult(argv, returncode, '', 'Offline fixture', failure)
    monkeypatch.setattr(c, 'invoke', invoke)
    seat = record['contract']['configuration']['participants']['reviewer']
    result = c.dispatch(seat, frozen_turn(record), directory, Event())
    assert len(calls) == 1
    assert result['error'].get('retry_basis') == expected
    assert result['error']['effects'] == 'unknown'
    assert result['process']['failure'] == failure
    assert result['process']['returncode'] == returncode
    assert result['identity']['authenticated_model'] is False


@pytest.mark.parametrize('case,expected', [
    ('refusal', 'cli_refusal'), ('usage', None), ('missing_usage', None),
    ('structured_output', None), ('timeout', None), ('output_limit', None),
    ('invalid_utf8', None), ('cancelled', None), ('successful_exit_error', None),
])
def test_dispatch_only_produces_cli_refusal_from_native_structured_evidence(tmp_path, monkeypatch, case, expected):
    directory, record = prepare(tmp_path, 'source-review', native=True)
    envelope = {'type': 'result', 'is_error': True, 'result': 'Offline refusal', 'modelUsage': {}}
    failure, returncode = 'nonzero_exit', 1
    if case == 'usage':
        envelope['modelUsage'] = {'fixture-model': {}}
    elif case == 'missing_usage':
        envelope.pop('modelUsage')
    elif case == 'structured_output':
        envelope['structured_output'] = {'text': 'An answer is not a no-usage refusal'}
    elif case in ('timeout', 'output_limit', 'invalid_utf8', 'cancelled'):
        failure = {'timeout': 'timeout_effects_unknown', 'output_limit': 'output_limit',
                   'invalid_utf8': 'invalid_utf8', 'cancelled': 'cancelled_effects_unknown'}[case]
    elif case == 'successful_exit_error':
        failure, returncode = None, 0
    calls = []
    def runner(argv, raw, **kwargs):
        calls.append(argv)
        return ProcessResult(argv, returncode, json.dumps(envelope), '', failure)
    def exchange(*args, **kwargs):
        return NativeExchange(*args, **kwargs, runner=runner)
    monkeypatch.setattr(c, 'NativeExchange', exchange)
    seat = record['contract']['configuration']['participants']['reviewer']
    result = c.dispatch(seat, frozen_turn(record), directory, Event())
    assert len(calls) == 1
    assert result['error'].get('retry_basis') == expected
    assert result['error']['effects'] == 'unknown'
    assert result['identity']['authenticated_model'] is False
    assert result['process']['returncode'] == returncode
    if expected:
        assert result['error']['refusal']['model_usage'] == {}
        assert result['error']['refusal']['kind'] == 'claude_structured_error'
    else:
        assert result['error']['refusal'] is None


def test_cancel_before_first_round_admission_creates_no_dispatch_entry(tmp_path):
    directory, initial = prepare(tmp_path, rounds=2, seats=3)
    cancel = Event()
    cancel.set()
    record = run(directory, initial, no_dispatch, cancel=cancel)
    assert record['status'] == 'cancelled'
    assert record['events'] == record['answers'] == []
    assert c.load(directory) == record


def test_first_round_overlaps_and_journal_writes_stay_ordered_on_host_thread(tmp_path, monkeypatch):
    directory, initial = prepare(tmp_path)
    host = get_ident()
    barrier, critic_returning = Barrier(2, timeout=3), Event()
    calls, saved = [], []
    save = RunStore.save
    def observe_save(store, record):
        assert get_ident() == host
        saved.append(copy.deepcopy(record))
        save(store, record)
    monkeypatch.setattr(RunStore, 'save', observe_save)
    def dispatch(seat, turn, *args):
        assert get_ident() != host
        calls.append(turn['participant'])
        barrier.wait()
        if turn['participant'] == 'critic':
            critic_returning.set()
        else:
            assert critic_returning.wait(3)
        return completed(seat, turn['participant'])
    record = run(directory, initial, dispatch)
    assert record['status'] == 'completed'
    assert set(calls) == {'reviewer', 'critic'}
    assert [a['participant'] for a in record['answers']] == ['reviewer', 'critic']
    assert [e['operation_key'] for e in record['events']] == ['0:reviewer', '0:critic']
    assert any([e['phase'] for e in item['events']] == ['dispatching', 'dispatching'] for item in saved)
    completed_keys = []
    for item in saved:
        for event in item['events']:
            if event['phase'] == 'completed' and event['operation_key'] not in completed_keys:
                completed_keys.append(event['operation_key'])
    assert completed_keys == ['0:reviewer', '0:critic']
    assert c.load(directory) == record


@pytest.mark.parametrize('failed_names,status', [
    ({'reviewer'}, 'partial'), ({'reviewer', 'critic'}, 'partial'),
    ({'reviewer', 'critic', 'observer'}, 'failed'),
])
def test_every_first_round_outcome_is_retained_and_partial_never_starts_round_two(tmp_path, failed_names, status):
    directory, initial = prepare(tmp_path, rounds=2, seats=3)
    barrier, calls = Barrier(3, timeout=3), []
    def dispatch(seat, turn, *args):
        calls.append((turn['round'], turn['participant']))
        barrier.wait()
        return failed(seat) if turn['participant'] in failed_names else completed(seat)
    record = run(directory, initial, dispatch)
    assert record['status'] == status
    expected = [(0, name) for name in ('reviewer', 'critic', 'observer')]
    assert sorted(calls) == sorted(expected)
    assert [(a['round'], a['participant']) for a in record['answers']] == expected
    assert len(record['events']) == 3
    assert all(e['phase'] == 'completed' for e in record['events'])
    assert c.load(directory) == record
    before = bytes_of(directory)
    with pytest.raises(ValueError, match='Terminal'):
        run(directory, initial, no_dispatch)
    assert bytes_of(directory) == before


@pytest.mark.parametrize('limit', [1, 2])
def test_admission_limit_never_journals_unadmitted_seats_and_replay_uses_no_budget(tmp_path, limit):
    directory, initial = prepare(tmp_path, rounds=2, seats=3)
    calls = []
    def dispatch(seat, turn, *args):
        calls.append((turn['round'], turn['participant']))
        return completed(seat)
    first = run(directory, initial, dispatch, max_operations=limit)
    names = ('reviewer', 'critic', 'observer')
    assert first['status'] == 'paused'
    assert sorted(calls) == [(0, name) for name in sorted(names[:limit])]
    assert [e['operation_key'] for e in first['events']] == [f'0:{name}' for name in names[:limit]]
    assert all(e['phase'] == 'completed' for e in first['events'])
    calls.clear()
    second = run(directory, initial, dispatch, max_operations=1)
    assert second['status'] == 'paused'
    assert calls == [(0, names[limit])]
    assert len(second['events']) == limit + 1
    assert all(e['phase'] == 'completed' for e in second['events'])
    calls.clear()
    final = run(directory, initial, dispatch)
    assert final['status'] == 'completed'
    assert len(final['answers']) == len(final['events']) == 6
    assert len(calls) == 6 - limit - 1
    assert (0, 'reviewer') not in calls and (0, 'critic') not in calls
    assert len(set(e['operation_key'] for e in final['events'])) == 6


def test_second_round_waits_for_complete_first_round_and_remains_sequential(tmp_path):
    directory, initial = prepare(tmp_path, rounds=2)
    barrier, reviewer_started, critic_started, release = Barrier(2, timeout=3), Event(), Event(), Event()
    observed_overlap, finished = [], []
    def observer():
        assert reviewer_started.wait(3)
        observed_overlap.append(critic_started.wait(0.2))
        release.set()
    watching = Thread(target=observer, daemon=True)
    watching.start()
    def dispatch(seat, turn, *args):
        if turn['round'] == 0:
            assert turn['previous_rounds'] == []
            barrier.wait()
        else:
            assert [a['participant'] for a in turn['previous_rounds']] == ['reviewer', 'critic']
            assert all(a['round'] == 0 for a in turn['previous_rounds'])
            if turn['participant'] == 'reviewer':
                reviewer_started.set()
                assert release.wait(3)
            else:
                critic_started.set()
                assert (1, 'reviewer') in finished
        finished.append((turn['round'], turn['participant']))
        return completed(seat)
    try:
        record = run(directory, initial, dispatch)
    finally:
        release.set()
        watching.join(timeout=3)
    assert not watching.is_alive()
    assert observed_overlap == [False]
    assert record['status'] == 'completed'
    assert finished[-2:] == [(1, 'reviewer'), (1, 'critic')]


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
@pytest.mark.parametrize('basis,failure', [
    ('not_launched', 'not_found'), ('not_launched', 'launch_failed'), ('cli_refusal', 'nonzero_exit'),
])
def test_explicit_selective_retry_reloads_history_and_preserves_sibling(tmp_path, operation, basis, failure):
    directory, initial, record, calls = stopped(tmp_path, operation, basis, failure=failure)
    assert record['status'] == ('failed' if operation == 'source-review' else 'partial')
    previous = copy.deepcopy(record['events'][0])
    sibling_events, sibling_answers = copy.deepcopy(record['events'][1:]), copy.deepcopy(record['answers'][1:])
    checkpoint = record['checkpoint_digest']
    reopened = c.reconcile(directory, checkpoint, 0, 'reviewer', retry_refused=True)
    event = reopened['events'][0]
    assert reopened['status'] == 'paused'
    assert reopened['contract_digest'] == initial['contract_digest']
    assert reopened['contract'] == initial['contract']
    assert reopened['checkpoint_digest'] != checkpoint
    assert event['attempts'] == 2 and (event['phase'], event['state']) == ('prepared', 'pending')
    assert not set(event) & {'result', 'error', 'effects', 'runtime_origin'}
    assert reopened['events'][1:] == sibling_events
    assert reopened['answers'] == sibling_answers
    history = reopened['recovery']['reconciliations']
    assert len(history) == 1
    assert history[0]['event_id'] == previous['event_id']
    assert history[0]['checkpoint'] == checkpoint
    assert history[0]['previous'] == previous
    assert history[0]['evidence']['retry_basis'] == basis
    assert history[0]['previous']['result']['error']['effects'] == 'unknown'
    assert c.load(directory) == reopened
    before = bytes_of(directory)
    with pytest.raises(ValueError):
        c.reconcile(directory, checkpoint, 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before
    calls.clear()
    def dispatch(seat, turn, *args):
        calls.append((turn['round'], turn['participant']))
        return completed(seat, 'Explicit retry completed')
    final = run(directory, initial, dispatch)
    assert final['status'] == 'completed'
    assert calls == [(0, 'reviewer')]
    assert final['events'][0]['attempts'] == 2
    assert final['events'][1:] == sibling_events
    assert final['recovery']['reconciliations'] == history
    assert c.load(directory) == final


def test_retry_budget_pauses_after_saved_result_then_replays_without_call(tmp_path):
    directory, initial, record, _ = stopped(tmp_path)
    c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    calls = []
    def dispatch(seat, turn, *args):
        calls.append(turn['participant'])
        return completed(seat)
    paused = run(directory, initial, dispatch, max_operations=1)
    assert paused['status'] == 'paused'
    assert paused['events'][0]['phase'] == 'completed'
    assert calls == ['reviewer']
    assert c.load(directory) == paused
    final = run(directory, initial, no_dispatch, max_operations=1)
    assert final['status'] == 'completed'
    assert len(final['events']) == 2


def test_second_round_retry_reuses_identical_complete_first_round_context(tmp_path):
    directory, initial = prepare(tmp_path, rounds=2)
    turns = []
    def dispatch(seat, turn, *args):
        turns.append(copy.deepcopy(turn))
        return failed(seat) if (turn['round'], turn['participant']) == (1, 'reviewer') else completed(seat)
    partial = run(directory, initial, dispatch)
    assert partial['status'] == 'partial'
    assert len(partial['answers']) == 4
    first_attempt = next(t for t in turns if (t['round'], t['participant']) == (1, 'reviewer'))
    c.reconcile(directory, partial['checkpoint_digest'], 1, 'reviewer', retry_refused=True)
    turns.clear()
    def retry(seat, turn, *args):
        turns.append(copy.deepcopy(turn))
        return completed(seat)
    final = run(directory, initial, retry)
    assert final['status'] == 'completed'
    assert turns == [first_attempt]
    assert [e['attempts'] for e in final['events']] == [1, 1, 2, 1]


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_second_refusal_cannot_be_reopened_or_automatically_retried(tmp_path, operation):
    directory, initial, record, _ = stopped(tmp_path, operation)
    c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    calls = []
    def refuse(seat, turn, *args):
        calls.append(turn['participant'])
        return failed(seat)
    second = run(directory, initial, refuse)
    assert calls == ['reviewer']
    assert second['events'][0]['attempts'] == 2
    before = bytes_of(directory)
    with pytest.raises(ValueError):
        c.reconcile(directory, second['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before
    with pytest.raises(ValueError, match='Terminal'):
        run(directory, initial, no_dispatch)
    assert bytes_of(directory) == before


@pytest.mark.parametrize('guard', [
    'stale', 'wrong_round', 'negative_round', 'boolean_round', 'unknown_seat',
    'successful_seat', 'missing_explicit_retry', 'cancelled', 'prepared',
])
def test_reconcile_guards_refuse_before_durable_mutation(tmp_path, monkeypatch, guard):
    directory, _, record, _ = stopped(tmp_path)
    checkpoint, round_number, participant, explicit = record['checkpoint_digest'], 0, 'reviewer', True
    if guard == 'stale':
        checkpoint = '0' * 64
    elif guard in ('wrong_round', 'negative_round', 'boolean_round'):
        round_number = {'wrong_round': 1, 'negative_round': -1, 'boolean_round': False}[guard]
    elif guard == 'unknown_seat':
        participant = 'missing'
    elif guard == 'successful_seat':
        participant = 'critic'
    elif guard == 'missing_explicit_retry':
        explicit = False
    else:
        record['status'] = guard
        RunStore(directory, existing=True).save(record)
        checkpoint = record['checkpoint_digest']
    before = bytes_of(directory)
    monkeypatch.setattr(c, 'dispatch', no_dispatch)
    with pytest.raises(ValueError):
        c.reconcile(directory, checkpoint, round_number, participant, retry_refused=explicit)
    assert bytes_of(directory) == before


@pytest.mark.parametrize('change', [
    'unknown', 'basis_only', 'missing_returncode', 'launched', 'wrong_failure', 'mismatched_error_failure',
    'refusal_usage', 'refusal_missing_usage', 'refusal_kind', 'refusal_returncode', 'refusal_adapter',
    'refusal_timeout', 'refusal_output_limit', 'refusal_error_failure', 'refusal_boolean_returncode',
])
def test_unknown_or_forged_retry_evidence_never_reopens_a_turn(tmp_path, change):
    native = change.startswith('refusal_') and change != 'refusal_adapter'
    basis = 'cli_refusal' if change.startswith('refusal_') else 'not_launched'
    directory, initial = prepare(tmp_path, native=native)
    result = failed(initial['contract']['configuration']['participants']['reviewer'], basis)
    if change == 'unknown':
        result = failed(initial['contract']['configuration']['participants']['reviewer'], None,
                        failure='timeout_effects_unknown')
    elif change == 'basis_only':
        result['process'] = None
    elif change == 'missing_returncode':
        result['process'].pop('returncode')
    elif change == 'launched':
        result['process']['returncode'] = 1
    elif change == 'wrong_failure':
        result['process']['failure'] = result['error']['failure'] = 'timeout_effects_unknown'
    elif change == 'mismatched_error_failure':
        result['error']['failure'] = 'launch_failed'
    elif change == 'refusal_usage':
        result['error']['refusal']['model_usage'] = {'fixture-model': {}}
    elif change == 'refusal_missing_usage':
        result['error']['refusal'].pop('model_usage')
    elif change == 'refusal_kind':
        result['error']['refusal']['kind'] = 'invented'
    elif change == 'refusal_returncode':
        result['error']['refusal']['returncode'] = 2
    elif change in ('refusal_timeout', 'refusal_output_limit'):
        result['process']['failure'] = {'refusal_timeout': 'timeout_effects_unknown',
                                       'refusal_output_limit': 'output_limit'}[change]
    elif change == 'refusal_error_failure':
        result['error']['failure'] = 'timeout_effects_unknown'
    elif change == 'refusal_boolean_returncode':
        result['process']['returncode'] = result['error']['refusal']['returncode'] = True
    def dispatch(seat, turn, *args):
        return copy.deepcopy(result) if turn['participant'] == 'reviewer' else completed(seat)
    record = run(directory, initial, dispatch)
    before = bytes_of(directory)
    with pytest.raises(ValueError):
        c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before


def test_copied_owner_cannot_reconcile_and_original_bytes_stay_unchanged(tmp_path):
    directory, _, record, _ = stopped(tmp_path)
    copied = tmp_path / 'copied'
    shutil.copytree(directory, copied)
    before = bytes_of(directory)
    copied_before = bytes_of(copied)
    with pytest.raises(ValueError, match='Copied'):
        c.reconcile(copied, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before
    assert bytes_of(copied) == copied_before


@pytest.mark.parametrize('change', ['event_id', 'checkpoint', 'previous_attempts', 'retry_basis', 'missing_previous'])
def test_full_reconciliation_history_is_validated_on_load_before_resume(tmp_path, change):
    directory, initial, record, _ = stopped(tmp_path)
    reopened = c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    history = reopened['recovery']['reconciliations'][0]
    if change == 'event_id':
        history['event_id'] = 'unknown-event'
    elif change == 'checkpoint':
        history['checkpoint'] = 'invalid-checkpoint'
    elif change == 'previous_attempts':
        history['previous']['attempts'] = 2
    elif change == 'retry_basis':
        history['evidence']['retry_basis'] = 'unknown'
    else:
        history.pop('previous')
    RunStore(directory, existing=True).save(reopened)
    before = bytes_of(directory)
    with pytest.raises(ValueError):
        c.load(directory)
    with pytest.raises(ValueError):
        run(directory, initial, no_dispatch)
    assert bytes_of(directory) == before


def test_worker_exception_keeps_successful_sibling_and_unresolved_turn_never_repeats(tmp_path):
    directory, initial = prepare(tmp_path)
    barrier, calls = Barrier(2, timeout=3), []
    def dispatch(seat, turn, *args):
        calls.append(turn['participant'])
        barrier.wait()
        if turn['participant'] == 'reviewer':
            raise RuntimeError('Offline worker escaped its dispatcher boundary')
        return completed(seat, 'Retain this sibling')
    with pytest.raises(RuntimeError, match='Offline worker'):
        run(directory, initial, dispatch)
    record = c.load(directory)
    assert record['status'] == 'unresolved'
    assert set(calls) == {'reviewer', 'critic'}
    assert record['events'][0]['phase'] == 'dispatching'
    assert record['events'][0]['effects'] == 'unknown'
    assert record['events'][1]['phase'] == 'completed'
    assert [(a['participant'], a['answer']['summary']) for a in record['answers']] == [('critic', 'Retain this sibling')]
    before = bytes_of(directory)
    with pytest.raises(RuntimeError, match='reconcile'):
        run(directory, initial, no_dispatch)
    assert bytes_of(directory) == before
    with pytest.raises(ValueError):
        c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before


def test_main_thread_interrupt_sets_shared_cancel_drains_workers_and_retains_all_results(tmp_path, monkeypatch):
    directory, initial = prepare(tmp_path)
    cancel, observed_cancel = Event(), Event()
    host, joined = get_ident(), []
    join = Thread.join
    def interrupt_first_join(worker, timeout=None):
        if get_ident() == host and not joined:
            joined.append(True)
            raise KeyboardInterrupt
        return join(worker, timeout)
    monkeypatch.setattr(Thread, 'join', interrupt_first_join)
    def dispatch(seat, turn, directory, shared_cancel):
        assert shared_cancel is cancel
        if turn['participant'] == 'reviewer':
            assert shared_cancel.wait(3)
            observed_cancel.set()
            return cancelled(seat)
        return completed(seat, 'Sibling survived interruption')
    record = run(directory, initial, dispatch, cancel=cancel)
    assert joined == [True] and observed_cancel.is_set()
    assert record['status'] == 'cancelled'
    assert [a['status'] for a in record['answers']] == ['cancelled', 'completed']
    assert all(e['phase'] == 'completed' for e in record['events'])
    assert record['answers'][0]['error']['effects'] == 'unknown'
    assert c.load(directory) == record
    with pytest.raises(ValueError, match='Terminal'):
        run(directory, initial, no_dispatch)


def test_returned_cancelled_turn_keeps_completed_sibling_and_terminal_journal(tmp_path):
    directory, initial = prepare(tmp_path, rounds=2)
    barrier, calls = Barrier(2, timeout=3), []
    def dispatch(seat, turn, *args):
        calls.append((turn['round'], turn['participant']))
        barrier.wait()
        return completed(seat) if turn['participant'] == 'reviewer' else cancelled(seat)
    record = run(directory, initial, dispatch)
    assert record['status'] == 'cancelled'
    assert sorted(calls) == [(0, 'critic'), (0, 'reviewer')]
    assert [a['status'] for a in record['answers']] == ['completed', 'cancelled']
    assert all(e['phase'] == 'completed' for e in record['events'])
    assert record['events'][1]['result']['error']['effects'] == 'unknown'
    assert c.load(directory) == record


def test_stalled_worker_stays_unresolved_and_late_result_cannot_mutate_saved_journal(tmp_path, monkeypatch):
    directory, initial = prepare(tmp_path)
    release, returned, calls = Event(), Event(), []
    monkeypatch.setattr(c, 'JOIN_GRACE_SECONDS', 0)
    def dispatch(seat, turn, *args):
        calls.append(turn['participant'])
        if turn['participant'] == 'reviewer':
            try:
                assert release.wait(5)
            finally:
                returned.set()
        return completed(seat)
    try:
        record = run(directory, initial, dispatch)
        assert record['status'] == 'unresolved'
        assert set(calls) == {'reviewer', 'critic'}
        assert (record['events'][0]['phase'], record['events'][0]['state']) == ('dispatching', 'pending')
        assert record['events'][1]['phase'] == 'completed'
        assert [a['participant'] for a in record['answers']] == ['critic']
        assert c.load(directory) == record
        before = bytes_of(directory)
        with pytest.raises(RuntimeError, match='reconcile'):
            run(directory, initial, no_dispatch)
        assert bytes_of(directory) == before
    finally:
        release.set()
        assert returned.wait(3)
    assert bytes_of(directory) == before


def test_worker_keyboard_interrupt_keeps_dispatch_unresolved_and_completed_sibling(tmp_path):
    directory, initial = prepare(tmp_path)
    barrier, calls = Barrier(2, timeout=3), []
    def dispatch(seat, turn, *args):
        calls.append(turn['participant'])
        barrier.wait()
        if turn['participant'] == 'reviewer':
            raise KeyboardInterrupt
        return completed(seat, 'Sibling evidence survives')
    with pytest.raises(KeyboardInterrupt):
        run(directory, initial, dispatch)
    record = c.load(directory)
    assert record['status'] == 'unresolved'
    assert set(calls) == {'reviewer', 'critic'}
    assert (record['events'][0]['phase'], record['events'][0]['state']) == ('dispatching', 'pending')
    assert record['events'][1]['phase'] == 'completed'
    assert [(a['participant'], a['answer']['summary']) for a in record['answers']] == [('critic', 'Sibling evidence survives')]
    before = bytes_of(directory)
    with pytest.raises(RuntimeError, match='reconcile'):
        run(directory, initial, no_dispatch)
    assert bytes_of(directory) == before
    with pytest.raises(ValueError):
        c.reconcile(directory, record['checkpoint_digest'], 0, 'reviewer', retry_refused=True)
    assert bytes_of(directory) == before


@pytest.mark.parametrize('failed_phase', ['prepared', 'dispatching'])
def test_begin_persistence_failure_launches_no_seat(tmp_path, monkeypatch, failed_phase):
    directory, initial = prepare(tmp_path)
    save, failures = RunStore.save, []
    def fail_once(store, record):
        if not failures and record['events'] and record['events'][0]['phase'] == failed_phase:
            failures.append(failed_phase)
            raise PersistenceError('Offline journal persistence failure')
        return save(store, record)
    monkeypatch.setattr(RunStore, 'save', fail_once)
    with pytest.raises(PersistenceError, match='Offline journal'):
        run(directory, initial, no_dispatch)
    assert failures == [failed_phase]
    record = c.load(directory)
    assert record['status'] == 'unresolved'
    assert len(record['events']) == 1
    assert record['events'][0]['phase'] == failed_phase
    assert record['answers'] == []


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_cli_failure_inspection_reconcile_and_json_compatibility(tmp_path, capsys, monkeypatch, operation):
    directory, _, record, _ = stopped(tmp_path, operation)
    monkeypatch.setattr(c, 'run', no_dispatch)
    before = bytes_of(directory)
    assert main([operation, 'status', str(directory)]) == 2
    assert capsys.readouterr().out == json.dumps(record, indent=2, allow_nan=False) + '\n'
    assert main([operation, 'status', str(directory), '--format', 'markdown']) == 2
    assert '**Status:** ' + record['status'] in capsys.readouterr().out
    assert main([operation, 'evidence', str(directory)]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == record['status']
    assert bytes_of(directory) == before
    args = [operation, 'reconcile', str(directory), '--checkpoint', record['checkpoint_digest'],
            '--round', '0', '--participant', 'reviewer']
    with pytest.raises(SystemExit) as missing_choice:
        main(args)
    assert missing_choice.value.code == 2
    assert '--retry-refused' in capsys.readouterr().err
    assert bytes_of(directory) == before
    assert main(args + ['--retry-refused']) == 0
    reopened = json.loads(capsys.readouterr().out)
    assert reopened['status'] == 'paused'
    assert reopened == c.load(directory)
    before = bytes_of(directory)
    assert main(args + ['--retry-refused']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'refused'
    assert bytes_of(directory) == before


def test_cli_reconcile_operation_mismatch_refuses_without_mutation(tmp_path, capsys, monkeypatch):
    directory, _, record, _ = stopped(tmp_path, 'source-review')
    before = bytes_of(directory)
    monkeypatch.setattr(c, 'run', no_dispatch)
    assert main(['roundtable', 'reconcile', str(directory), '--checkpoint', record['checkpoint_digest'],
                 '--round', '0', '--participant', 'reviewer', '--retry-refused']) == 2
    out = json.loads(capsys.readouterr().out)
    assert out['status'] == 'refused'
    assert 'Command does not match' in out['error']['detail']
    assert bytes_of(directory) == before


@pytest.mark.parametrize('option', ['--allow-external', '--allow-native', '--format'])
def test_cli_reconcile_surface_does_not_gain_dispatch_or_presentation_options(capsys, option):
    args = ['roundtable', 'reconcile', 'unused', '--checkpoint', 'a' * 64,
            '--round', '0', '--participant', 'reviewer', '--retry-refused', option]
    if option == '--format':
        args.append('markdown')
    with pytest.raises(SystemExit) as caught:
        main(args)
    assert caught.value.code == 2
    assert 'unrecognized arguments' in capsys.readouterr().err
