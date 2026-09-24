"""Accepted task text stays bound across later state writes."""
# qualify: platform
import json
import pytest
from attune_harness import spec_state as state_module
from attune_harness.spec_state import SpecState, load_state, save_state
from test_spec_tasks import FULL


def receipt(task_id='1'):
    return {'task_id': task_id, 'test_evidence': {'fixture': 'state-writer-only'}}


def test_progress_save_preserves_first_acceptance_and_binds_next(tmp_path):
    plan = tmp_path / 'plan.md'
    plan.write_text(FULL + FULL.replace('id="1"', 'id="2"'))
    first = SpecState(str(plan), completed=['1'], task_receipts=[receipt()])
    save_state(first)
    original = first.task_content_digests['1']
    second = SpecState(str(plan), completed=['1', '2'], task_receipts=[receipt(), receipt('2')])
    save_state(second)
    assert second.task_content_digests['1'] == original
    assert set(second.task_content_digests) == {'1', '2'}
    before = plan.read_bytes()
    second.task_receipts[0]['test_evidence'] = {'fixture': 'replacement'}
    with pytest.raises(ValueError, match='receipt changed'):
        save_state(second)
    assert plan.read_bytes() == before


@pytest.mark.parametrize('prior', ['{"schema_version":2,"completed":false}', '{broken json}'])
def test_unreadable_history_cannot_be_restamped(tmp_path, prior):
    plan = tmp_path / 'plan.md'
    plan.write_text(FULL + '\n<!-- spec-state: ' + prior + ' -->\n')
    before = plan.read_bytes()
    state = SpecState(str(plan), completed=['1'], task_receipts=[receipt()])
    with pytest.raises(ValueError, match='unreadable prior'):
        save_state(state)
    assert plan.read_bytes() == before and state.task_content_digests == {}


def test_duplicate_task_cannot_acquire_binding(tmp_path):
    plan = tmp_path / 'plan.md'
    plan.write_text(FULL + FULL)
    with pytest.raises(ValueError, match='unique task'):
        save_state(SpecState(str(plan), completed=['1'], task_receipts=[receipt()]))
    assert load_state(str(plan)) is None


def test_caller_cannot_override_binding_or_mint_it_on_failed_write(tmp_path, monkeypatch):
    plan = tmp_path / 'plan.md'
    plan.write_text(FULL)
    state = SpecState(str(plan), completed=['1'], task_receipts=[receipt()],
                      task_content_digests={'1': '0' * 64})
    with pytest.raises(ValueError, match='conflicts'):
        save_state(state)
    state.task_content_digests = {}
    def fail(*args):
        raise OSError('fixture disk failure')
    monkeypatch.setattr(state_module, '_atomic_write_text', fail)
    with pytest.raises(OSError, match='disk failure'):
        save_state(state)
    assert state.task_content_digests == {} and load_state(str(plan)) is None


@pytest.mark.parametrize('bindings', [[], {'1': False}, {'1':'short'}, {'2':'0'*64}])
def test_invalid_saved_content_bindings_refused(tmp_path, bindings):
    plan = tmp_path / 'plan.md'
    plan.write_text(FULL + '\n<!-- spec-state: ' + json.dumps({
        'schema_version':2, 'completed':['1'], 'task_content_digests':bindings}) + ' -->\n')
    with pytest.raises(ValueError, match='task_content_digests'):
        load_state(str(plan))
