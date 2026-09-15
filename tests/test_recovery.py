import copy
import json
import shutil
import subprocess
import sys

import pytest

from test_review import case, change, change_config, scripted
from attune_harness.cli import main
from attune_harness.features import FeatureUnavailable
from attune_harness.review import review
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import PersistenceError, RunStore, inspect_run, read_record
from attune_harness.recovery import (
    UnresolvedOperation, cancel_review,
    reconcile_review, resume_review, transfer_lead,
)


def resume(case, record, **kwargs):
    return resume_review(case[2], case[0], case[1], record['checkpoint_digest'], **kwargs)


@pytest.mark.parametrize('boundary', range(1, 14))
def test_resume_every_completed_operation_without_repeating_calls(case, boundary):
    calls = []
    def factory(config, cwd):
        real = ReviewExchange(config, cwd)
        def invoke(raw):
            calls.append(json.loads(raw)['turn']['turn_id'])
            return real(raw)
        return invoke
    first = review(*case, max_operations=boundary, exchange_factory=factory)
    assert first['status'] == 'paused'
    saved_events = copy.deepcopy(first['events'])
    result = resume(case, first, exchange_factory=factory)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == 'verified'
    assert result['events'][:boundary] == saved_events
    assert len(result['events']) == 13
    assert len(calls) == len(set(calls)) == 6
    assert result['requirement_revision'] == first['requirement_revision']


def test_many_small_resumes_keep_budgets_and_optional_data(case):
    record = review(*case, max_operations=1)
    record['future_note'] = {'unknown_optional': ['preserve']}
    RunStore(case[2], existing=True).save(record)
    ids = []
    for _ in range(13):
        record = resume(case, record, max_operations=1)
        ids.append(record['checkpoint_digest'])
        assert record['future_note'] == {'unknown_optional': ['preserve']}
    assert record['status'] == 'completed'
    assert len(set(ids)) == 13
    assert all(item['tool_calls'] == 2 for item in record['participants'].values())


@pytest.mark.parametrize('boundary', ['prepared', 'dispatching', 'completed'])
def test_persistence_boundaries_distinguish_unstarted_and_uncertain(case, monkeypatch, boundary):
    original = RunStore.save
    calls, replies = [], []
    def factory(config, cwd):
        real = ReviewExchange(config, cwd)
        def invoke(raw):
            calls.append(raw)
            reply = real(raw)
            replies.append(reply)
            return reply
        return invoke
    def fail(store, record):
        if record['events'] and record['events'][-1]['kind'] == 'participant_turn':
            if record['events'][-1]['phase'] == boundary:
                raise PersistenceError('injected crash')
        original(store, record)
    monkeypatch.setattr(RunStore, 'save', fail)
    with pytest.raises(PersistenceError):
        review(*case, exchange_factory=factory)
    monkeypatch.setattr(RunStore, 'save', original)
    record = read_record(case[2])
    assert len(calls) == (1 if boundary == 'completed' else 0)
    if boundary == 'completed':
        with pytest.raises(UnresolvedOperation):
            resume(case, record, exchange_factory=factory)
        assert len(calls) == 1
        reply_file = case[0].parent / 'recovered.json'
        reply_file.write_text(replies[0], encoding='utf-8')
        record = reconcile_review(case[2], record['checkpoint_digest'], record['events'][-1]['event_id'], reply_file=reply_file)
    result = resume(case, record, exchange_factory=factory)
    assert result['status'] == 'completed'
    assert len(calls) == 6


def test_uncertain_external_command_recovered_without_second_effect(case):
    peer = case[0].parent / 'peer.py'
    counter = case[0].parent / 'counter.txt'
    reply = case[0].parent / 'reply.json'
    peer.write_text(
        'import json,sys,pathlib\n'
        'd=json.load(sys.stdin)\n'
        'p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+"effect\\n" if p.exists() else "effect\\n")\n'
        'pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(schema_version=1,request_digest=d["request_digest"],action=dict(kind="final",text="Recovered fixture reply"))))\n'
        'sys.exit(23)\n', encoding='utf-8')
    change_config(case, lambda d: d['participants']['alpha'].update(
        adapter='command', command=[sys.executable, '-I', str(peer), str(counter), str(reply)], timeout=2))
    failed = review(*case, allow_external=True)
    assert failed['status'] == 'failed'
    event = failed['events'][-1]
    assert event['effect_class'] == 'unknown'
    with pytest.raises(UnresolvedOperation):
        resume(case, failed, allow_external=True)
    with pytest.raises(UnresolvedOperation):
        reconcile_review(case[2], failed['checkpoint_digest'], event['event_id'], retry_read_only=True)
    reconciled = reconcile_review(case[2], failed['checkpoint_digest'], event['event_id'], reply_file=reply)
    result = resume(case, reconciled, allow_external=True)
    assert result['status'] == 'completed'
    assert counter.read_text(encoding='utf-8') == 'effect\n'
    assert result['participants']['lead']['text'] == 'Recovered fixture reply'
    assert result['recovery']['reconciliations'][0]['evidence']['sha256']
    with pytest.raises(ValueError):
        reconcile_review(case[2], result['checkpoint_digest'], event['event_id'], reply_file=reply)


def test_read_only_retry_requires_explicit_decision_and_is_bounded(case, monkeypatch):
    import importlib
    module = importlib.import_module('attune_harness.review')
    original = module.retrieve_sources
    def fail(*args, **kwargs):
        raise OSError('transient read error')
    monkeypatch.setattr(module, 'retrieve_sources', fail)
    first = review(*case)
    event = first['events'][-1]
    assert event['effect_class'] == 'read_only'
    with pytest.raises(UnresolvedOperation):
        resume(case, first)
    allowed = reconcile_review(case[2], first['checkpoint_digest'], event['event_id'], retry_read_only=True)
    second = resume(case, allowed)
    assert second['status'] == 'failed'
    assert second['events'][-1]['attempts'] == 2
    with pytest.raises(ValueError, match='limit'):
        reconcile_review(case[2], second['checkpoint_digest'], event['event_id'], retry_read_only=True)
    monkeypatch.setattr(module, 'retrieve_sources', original)
    with pytest.raises(UnresolvedOperation):
        resume(case, second)


def test_read_only_retry_can_complete(case, monkeypatch):
    import importlib
    module = importlib.import_module('attune_harness.review')
    original = module.retrieve_sources
    def fail(*args, **kwargs):
        raise OSError('transient read error')
    monkeypatch.setattr(module, 'retrieve_sources', fail)
    first = review(*case)
    allowed = reconcile_review(case[2], first['checkpoint_digest'], first['events'][-1]['event_id'], retry_read_only=True)
    monkeypatch.setattr(module, 'retrieve_sources', original)
    assert resume(case, allowed)['status'] == 'completed'


@pytest.mark.parametrize('change_kind', ['document', 'context', 'source', 'new_source', 'request', 'config'])
def test_changed_inputs_or_scope_cannot_resume(case, change_kind):
    record = review(*case, max_operations=2)
    if change_kind in ('document', 'context', 'source', 'new_source'):
        path = {'document': 'project/guide.md', 'context': 'context.json',
                'source': 'project/reference.md', 'new_source': 'project/added.md'}[change_kind]
        (case[0].parent / path).write_text('changed', encoding='utf-8')
    elif change_kind == 'request':
        change(case[0], lambda d: d['answers'].update(objective='new objective'))
    else:
        change_config(case, lambda d: d['participants']['alpha'].update(max_tool_calls=3))
    before = (case[2] / 'record.json').read_bytes()
    with pytest.raises(ValueError, match='changed'):
        resume(case, record)
    assert (case[2] / 'record.json').read_bytes() == before


def test_stale_checkpoint_and_copied_run_refused(case):
    first = review(*case, max_operations=2)
    second = resume(case, first, max_operations=1)
    with pytest.raises(ValueError, match='Stale'):
        resume(case, first)
    copied = case[2].with_name('copy')
    shutil.copytree(case[2], copied)
    with pytest.raises(ValueError, match='Copied'):
        resume_review(copied, case[0], case[1], second['checkpoint_digest'])


def test_concurrent_owner_refused_and_lock_released_after_process_death(case):
    record = review(*case, max_operations=2)
    script = ('from pathlib import Path; import sys; from attune_harness.review_store import RunStore; '
              's=RunStore(Path(sys.argv[1]).parent,existing=True); lease=s.lease(); lease.__enter__(); '
              'print("locked",flush=True); sys.stdin.read()')
    process = subprocess.Popen([sys.executable, '-c', script, str(case[2] / '.writer.lock')],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == 'locked'
        with pytest.raises(PersistenceError, match='busy'):
            resume(case, record)
        with pytest.raises(PersistenceError, match='busy'):
            cancel_review(case[2], record['checkpoint_digest'], 'stop')
    finally:
        process.kill()
        process.wait()
        process.stdin.close()
        process.stdout.close()
    assert resume(case, record)['status'] == 'completed'


def test_old_future_corrupt_records_are_inspect_only_or_rejected(case):
    record = review(*case, max_operations=1)
    store = RunStore(case[2], existing=True)
    record['recovery']['profile']['version'] = 99
    store.save(record)
    with pytest.raises(FeatureUnavailable):
        resume(case, record)
    assert inspect_run(case[2])['recovery']['profile']['version'] == 99
    record.pop('recovery')
    record.pop('checkpoint_digest')
    store.save(record)
    assert inspect_run(case[2])['status'] == 'paused'
    with pytest.raises(FeatureUnavailable):
        resume_review(case[2], case[0], case[1], 'old')


def test_checkpoint_content_change_is_detected(case):
    review(*case, max_operations=1)
    change(case[2] / 'record.json', lambda d: d.update(status='completed'))
    with pytest.raises(ValueError, match='digest'):
        inspect_run(case[2])


def add_transfer_candidate(case):
    change_config(case, lambda d: d['participants'].update(gamma=copy.deepcopy(d['participants']['alpha'])))


@pytest.mark.parametrize('document,query,outcome', [
    ('[Quartz](reference.md)', 'quartz retention policy', 'verified'),
    ('[missing](absent.md)', 'quartz retention policy', 'refuted'),
    ('No supported claims', 'quartz retention policy', 'unknown'),
    ('[Quartz](reference.md)', 'nonmatchingzzzz', 'verified'),
])
@pytest.mark.parametrize('boundary', [1, 4, 7])
@pytest.mark.parametrize('direction', [('alpha', 'gamma'), ('gamma', 'alpha')])
def test_transfer_matrix_preserves_constraints_and_evidence(case, document, query, outcome, boundary, direction):
    add_transfer_candidate(case)
    (case[0].parent / 'project/guide.md').write_text(document, encoding='utf-8')
    change(case[0], lambda d: d['answers'].update(lead=direction[0], query=query))
    first = review(*case, max_operations=boundary)
    accepted = copy.deepcopy(first['accepted'])
    transferred = transfer_lead(case[2], first['checkpoint_digest'], direction[1], 'Continue the same accepted review')
    assert transferred['requirement_revision'] == first['requirement_revision']
    assert transferred['accepted'] == accepted
    prior = transferred['recovery']['transfers'][0]['prior_events']
    seen = []
    def factory(config, cwd):
        real = ReviewExchange(config, cwd)
        # A custom observer is conservatively classified as potentially effectful.
        class Observer:
            def __call__(self, raw):
                seen.append(json.loads(raw)['turn'])
                return real(raw)
        return Observer()
    # New lead has no previously executed turns; reviewer starts independently.
    result = resume(case, transferred, exchange_factory=factory)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == outcome
    assert result['retrieval_outcome'] == ('no_results' if query == 'nonmatchingzzzz' else 'retrieved')
    assert result['accepted'] == accepted
    assert result['participants']['lead']['participant_id'] == direction[1]
    assert result['recovery']['transfers'][0]['prior_events'] == prior
    assert seen[0]['continuation']['accepted_submission'] == accepted['submission']
    assert seen[0]['continuation']['artifacts'] == first['artifacts']
    assert all('continuation' not in turn for turn in seen if turn['role'] == 'reviewer')


def test_two_way_transfer_uses_new_attempts_and_has_a_bound(case):
    add_transfer_candidate(case)
    first = review(*case, max_operations=4)
    second = transfer_lead(case[2], first['checkpoint_digest'], 'gamma', 'First transfer')
    third = resume(case, second, max_operations=2)
    fourth = transfer_lead(case[2], third['checkpoint_digest'], 'alpha', 'Return transfer')
    assert len({first['recovery']['assignments']['lead']['attempt_id'], second['recovery']['assignments']['lead']['attempt_id'],
                fourth['recovery']['assignments']['lead']['attempt_id']}) == 3
    with pytest.raises(ValueError, match='limit'):
        transfer_lead(case[2], fourth['checkpoint_digest'], 'gamma', 'Too many')
    assert resume(case, fourth)['status'] == 'completed'


def test_transfer_denies_unresolved_work_reviewer_overlap_and_unknown_identity(case):
    add_transfer_candidate(case)
    first = review(*case, max_operations=1)
    for selected in ('alpha', 'beta', 'unknown'):
        with pytest.raises(ValueError):
            transfer_lead(case[2], first['checkpoint_digest'], selected, 'invalid')
    later = resume(case, first, max_operations=7)
    with pytest.raises(ValueError, match='reviewer'):
        transfer_lead(case[2], later['checkpoint_digest'], 'gamma', 'Too late')


def test_cancellation_does_not_erase_effect_uncertainty(case):
    def fail(*args):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'never'}, fail))
    record = read_record(case[2])
    cancelled = cancel_review(case[2], record['checkpoint_digest'], 'Abandon this attempt')
    assert cancelled['status'] == 'cancelled'
    assert cancelled['events'][-1]['phase'] == 'dispatching'
    with pytest.raises(ValueError, match='cancelled'):
        resume(case, cancelled)


def test_completed_resume_and_late_cancel_have_no_effect(case):
    record = review(*case)
    before = (case[2] / 'record.json').read_bytes()
    assert resume(case, record, exchange_factory=lambda *a: pytest.fail('rerun')) == record
    assert cancel_review(case[2], record['checkpoint_digest'], 'too late') == record
    assert (case[2] / 'record.json').read_bytes() == before


def test_cli_pause_transfer_resume_cancel(case, capsys):
    add_transfer_candidate(case)
    request, config, directory = map(str, case)
    assert main(['review', request, '--config', config, '--run-dir', directory, '--max-operations', '4']) == 1
    first = json.loads(capsys.readouterr().out)
    assert first['status'] == 'paused'
    assert main(['transfer-review', directory, '--checkpoint', first['checkpoint_digest'], '--lead', 'gamma', '--reason', 'Continue']) == 1
    transferred = json.loads(capsys.readouterr().out)
    assert main(['resume-review', directory, '--request', request, '--config', config, '--checkpoint', transferred['checkpoint_digest']]) == 0
    complete = json.loads(capsys.readouterr().out)
    assert main(['cancel-review', directory, '--checkpoint', complete['checkpoint_digest'], '--reason', 'too late']) == 0
    assert json.loads(capsys.readouterr().out) == complete


def test_new_source_during_run_invalidates_original_snapshot(case):
    def change_sources(data):
        (case[0].parent / 'project/new.md').write_text('new evidence', encoding='utf-8')
    result = review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'done'}, change_sources))
    assert result['status'] == 'failed'
    assert 'snapshot changed' in result['error']['detail']


def test_recovery_control_rejects_stale_decisions(case):
    add_transfer_candidate(case)
    first = review(*case, max_operations=1)
    second = resume(case, first, max_operations=1)
    before = (case[2] / 'record.json').read_bytes()
    with pytest.raises(ValueError, match='Stale'):
        transfer_lead(case[2], first['checkpoint_digest'], 'gamma', 'late decision')
    with pytest.raises(ValueError, match='Stale'):
        cancel_review(case[2], first['checkpoint_digest'], 'late decision')
    with pytest.raises(ValueError, match='Stale'):
        reconcile_review(case[2], first['checkpoint_digest'], second['events'][-1]['event_id'], retry_read_only=True)
    assert (case[2] / 'record.json').read_bytes() == before


def test_unresolved_transfer_and_wrong_recovered_reply_are_rejected(case, capsys):
    add_transfer_candidate(case)
    def stop(data):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'never'}, stop))
    record = read_record(case[2])
    event = record['events'][-1]
    with pytest.raises(UnresolvedOperation):
        transfer_lead(case[2], record['checkpoint_digest'], 'gamma', 'not safe yet')
    reply = case[0].parent / 'wrong-reply.json'
    reply.write_text(json.dumps({'schema_version': 1, 'request_digest': 'old',
                                 'action': {'kind': 'final', 'text': 'unrelated'}}), encoding='utf-8')
    assert main(['reconcile-review', str(case[2]), '--checkpoint', record['checkpoint_digest'],
                 '--event', event['event_id'], '--reply', str(reply)]) == 2
    assert 'current turn' in json.loads(capsys.readouterr().out)['error']['detail']
    assert read_record(case[2]) == record


@pytest.mark.parametrize('mutation,match', [
    (lambda d: d['events'].append(copy.deepcopy(d['events'][0])), 'Duplicate'),
    (lambda d: d['events'][0].update(state='pending'), 'Invalid saved'),
    (lambda d: d.update(status='future_state'), 'Unsupported recovery'),
])
def test_incompatible_control_fields_do_not_resume(case, mutation, match):
    record = review(*case, max_operations=1)
    mutation(record)
    RunStore(case[2], existing=True).save(record)
    with pytest.raises(ValueError, match=match):
        resume(case, record)


def test_changed_replayed_request_is_rejected(case):
    record = review(*case, max_operations=3)
    record['events'][-1]['request_digest'] = 'wrong'
    RunStore(case[2], existing=True).save(record)
    result = resume(case, record)
    assert result['status'] == 'failed'
    assert 'reconstructed' in result['error']['detail']


def test_recovered_reply_does_not_grant_its_requested_tool(case):
    def stop(data):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'never'}, stop))
    record = read_record(case[2])
    event = record['events'][-1]
    reply = case[0].parent / 'reply.json'
    reply.write_text(json.dumps({'schema_version': 1, 'request_digest': event['request_digest'],
                                 'action': {'kind': 'tool', 'name': 'shell', 'arguments': {}}}), encoding='utf-8')
    updated = reconcile_review(case[2], record['checkpoint_digest'], event['event_id'], reply_file=reply)
    # Keep the same injected factory classification; completed reply is replayed.
    result = resume(case, updated, exchange_factory=scripted({'kind': 'final', 'text': 'unused'}))
    assert result['status'] == 'failed'
    assert 'not granted' in result['error']['detail']
    assert not any(item['kind'] == 'tool' for item in result['events'])
