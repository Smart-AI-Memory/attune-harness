"""Interrupted review intent survives sessions independently of task execution."""
# qualify: platform
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from attune_harness.memory_saved import SavedError, SavedStore
from test_memory_saved import request, SCOPE
from test_memory_saved_cli import configured_store, invoke

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Saved storage initial profile is POSIX')


def pending():
    return dict(status='pending', goal='Find useful follow-up work',
                progress='Reviewed the storage boundary; Windows remains to assess',
                reason='Deferred at session close', next_action='Inspect the Windows evidence',
                evidence=['docs/opportunity-log.md', 'receipts/checks.json'])


def task(key='task', **extra):
    value = request(key)
    value.update(kind='task', next_action='Continue implementation')
    value.update(extra)
    return value


def test_pending_review_survives_completion_and_new_process(tmp_path):
    store = SavedStore(tmp_path / 'store')
    rec = store.save(task(opportunity_review=pending()))['record']
    store.complete(rec['id'], SCOPE, 'complete-task', 1)
    code = '''import json,sys
sys.path.insert(0,sys.argv.pop(1))
from attune_harness.memory_saved import SavedStore
print(json.dumps(SavedStore(sys.argv[1]).get(sys.argv[2], {'kind':'global'})))
'''
    import attune_harness.memory_saved as module
    result = json.loads(subprocess.check_output([sys.executable, '-c', code,
        str(Path(module.__file__).resolve().parents[1]), str(store.root), rec['id']], text=True))
    assert result['status'] == 'completed'
    assert result['opportunity_review'] == pending()
    assert 'pending' in result['opportunity_review_notice']
    assert pending()['next_action'] in result['opportunity_review_notice']
    assert result['history'][0]['record']['opportunity_review'] == pending()
    assert 'opportunity_review_notice' not in json.loads((store.root / 'state.json').read_text())['records'][rec['id']]


def test_revision_closure_replay_and_reopening(tmp_path):
    store = SavedStore(tmp_path / 'store')
    original = store.save(task(opportunity_review=pending()))['record']
    completed = {k:v for k,v in pending().items() if k not in ('reason', 'next_action')}
    completed.update(status='completed', outcome={'kind':'logged', 'summary':'Recorded the Windows follow-up'})
    change = {'opportunity_review':completed}
    result = store.revise(original['id'], change, SCOPE, 'review-done', 1)
    assert result['record']['status'] == 'open'
    store.revise(original['id'], {'opportunity_review':pending()}, SCOPE, 'review-reopen', 2)
    assert store.revise(original['id'], change, SCOPE, 'review-done', 1) == result
    assert store.get(original['id'], SCOPE)['opportunity_review']['status'] == 'pending'
    with pytest.raises(SavedError, match='conflict'):
        store.revise(original['id'], change, SCOPE, 'stale-review', 1)
    with pytest.raises(SavedError):
        store.revise(original['id'], {'opportunity_review':None}, SCOPE, 'clear-review', 3)


def test_no_change_completion_is_explicit_caller_report(tmp_path):
    review = dict(status='completed', goal='Assess follow-ups', progress='Reviewed the current evidence',
                  evidence=[], outcome={'kind':'no_change', 'summary':'Existing entries already cover the findings'})
    store = SavedStore(tmp_path / 'store')
    rec = store.save(task(opportunity_review=review))['record']
    assert 'caller reported' in store.get(rec['id'], SCOPE)['opportunity_review_notice']


@pytest.mark.parametrize('mutate', [
    lambda r:r.update(status='deferred'),
    lambda r:r.pop('next_action'),
    lambda r:r.update(next_action=''),
    lambda r:r.update(evidence=['x'] * 17),
    lambda r:r.update(evidence=['x' * 2049]),
    lambda r:r.update(goal='x' * 8193),
    lambda r:r.update(outcome={'kind':'no_change','summary':'invented'}),
    lambda r:r.update(status='completed'),
])
def test_invalid_checkpoint_refused_before_write(tmp_path, mutate):
    review = pending(); mutate(review)
    store = SavedStore(tmp_path / 'store')
    with pytest.raises(SavedError):
        store.save(task(opportunity_review=review))
    assert not store.root.exists()


def test_logged_completion_needs_reference_and_memory_cannot_have_review(tmp_path):
    store = SavedStore(tmp_path / 'store')
    review = dict(status='completed', goal='Review', progress='Finished', evidence=[],
                  outcome={'kind':'logged','summary':'Claimed an entry'})
    with pytest.raises(SavedError):
        store.save(task(opportunity_review=review))
    with pytest.raises(SavedError):
        store.save(request(opportunity_review=pending()))
    assert not store.root.exists()


def test_existing_task_absence_is_not_inferred_complete(tmp_path):
    store = SavedStore(tmp_path / 'store')
    rec = store.save(task())['record']
    assert 'opportunity_review' not in store.get(rec['id'], SCOPE)
    assert 'opportunity_review_notice' not in store.get(rec['id'], SCOPE)


def test_cli_resume_discovery_is_scoped_and_retains_completed_tasks(tmp_path, capsys):
    config, scope = configured_store(tmp_path)
    store = SavedStore(tmp_path / 'store')
    rec = store.save(task(opportunity_review=pending()))['record']
    store.complete(rec['id'], SCOPE, 'done-task', 1)
    store.save(task('no-review'))
    store.save(task('other-project', scope={'kind':'project','project':str(tmp_path)}, opportunity_review=pending()))
    code, result = invoke(capsys, config, 'list', '--scope', scope, '--pending-review')
    assert code == 0 and [r['id'] for r in result['records']] == [rec['id']]
    assert 'Resume:' in result['records'][0]['opportunity_review_notice']
    show = invoke(capsys, config, 'show', rec['id'], '--scope', scope)[1]
    assert show['opportunity_review']['progress'] == pending()['progress']
    assert 'history' not in show
    store.forget(rec['id'], SCOPE, 'withdraw-task', 2)
    assert invoke(capsys, config, 'list', '--scope', scope, '--pending-review')[1]['records'] == []
    retained = invoke(capsys, config, 'show', rec['id'], '--scope', scope, '--history')[1]
    assert retained['opportunity_review'] == pending()
    assert 'read-only' in retained['opportunity_review_notice']
    assert 'Resume:' not in retained['opportunity_review_notice']


def test_review_text_search_and_unavailable_execution_remain_separate(tmp_path):
    from uuid import uuid4
    scope = {'kind':'project', 'project':str(tmp_path)}
    store = SavedStore(tmp_path / 'store')
    rec = store.save(task(scope=scope, opportunity_review=pending(),
                          execution={'directory':str(tmp_path / 'missing-owner'), 'task_id':str(uuid4())}))['record']
    result = store.search('Windows', scope)
    assert [r['id'] for r in result] == [rec['id']]
    assert result[0]['execution_status'] == 'unavailable'
    assert result[0]['opportunity_review']['status'] == 'pending'
    assert not (tmp_path / 'missing-owner').exists()
    assert store.search('Windows', SCOPE) == []
