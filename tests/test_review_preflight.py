"""Invalid fresh-review limits leave the retry path and existing owners usable."""
# qualify: platform

import pytest

from attune_harness.recovery import resume_review
from attune_harness.review import review
from attune_harness.task_contract import accept_task
from attune_harness.task_policies import execute_task
from test_review import case
from test_task_contract import draft, response


def no_dispatch(*args, **kwargs):
    pytest.fail('Invalid limit or replay dispatched a participant')


def snapshot(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


@pytest.mark.parametrize('limit', [0, -1, 101, True, False, 1.0, '1', [], {}])
def test_invalid_fresh_limit_allows_corrected_retry_at_same_path(case, limit):
    with pytest.raises(ValueError, match=r'max_operations must be an integer in 1\.\.100'):
        review(*case, max_operations=limit, exchange_factory=no_dispatch)
    assert not case[2].exists()

    corrected = review(*case, max_operations=1, exchange_factory=no_dispatch)
    assert corrected['status'] == 'paused'
    assert corrected['events'][0]['state'] == 'completed'
    assert (case[2] / 'record.json').is_file()


@pytest.mark.parametrize('limit,status', [(None, 'completed'), (1, 'paused'), (100, 'completed')])
def test_valid_fresh_limit_boundaries_preserve_execution(case, limit, status):
    result = review(*case, max_operations=limit)
    assert result['status'] == status
    assert len(result['events']) == (1 if limit == 1 else 13)


@pytest.mark.parametrize('paused', [False, True], ids=['accepted', 'paused'])
def test_invalid_task_limit_preserves_existing_owner_and_retry(case, paused):
    draft(case)
    accept_task(case[2], response(case[2]))
    if paused:
        assert execute_task(case[2], max_operations=1)['status'] == 'paused'
    (case[2] / 'retained-receipt.json').write_text('{"fixture":"preserve"}', encoding='utf-8')
    original = snapshot(case[2])

    with pytest.raises(ValueError, match='max_operations'):
        execute_task(case[2], max_operations=0, exchange_factory=no_dispatch)
    assert case[2].is_dir()
    assert snapshot(case[2]) == original
    assert execute_task(case[2])['status'] == 'completed'


def test_invalid_resume_limit_preserves_existing_owner_and_retry(case):
    first = review(*case, max_operations=1, exchange_factory=no_dispatch)
    (case[2] / 'retained-receipt.json').write_text('{"fixture":"preserve"}', encoding='utf-8')
    original = snapshot(case[2])

    with pytest.raises(ValueError, match='max_operations'):
        resume_review(case[2], case[0], case[1], first['checkpoint_digest'],
                      max_operations=0, exchange_factory=no_dispatch)
    assert case[2].is_dir()
    assert snapshot(case[2]) == original
    assert resume_review(case[2], case[0], case[1], first['checkpoint_digest'])['status'] == 'completed'


@pytest.mark.parametrize('owner', ['review', 'task'])
def test_completed_owner_replays_without_applying_fresh_limit_preflight(case, owner):
    if owner == 'review':
        completed = review(*case)
        def replay():
            return resume_review(case[2], case[0], case[1], completed['checkpoint_digest'],
                                 max_operations=0, exchange_factory=no_dispatch)
    else:
        draft(case)
        accept_task(case[2], response(case[2]))
        completed = execute_task(case[2])
        def replay():
            return execute_task(case[2], max_operations=0, exchange_factory=no_dispatch)
    original = snapshot(case[2])

    assert replay() == completed
    assert snapshot(case[2]) == original
