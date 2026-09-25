"""Retained displays and correction requests cannot manufacture work authority."""

import copy
import json
from pathlib import Path

import pytest

from attune_harness.review_contract import digest
from attune_harness.task_contract import read_task
from attune_harness.work_contract import bind_work_acceptance, revise_work
from attune_harness.work_decisions import (
    LIMIT, require_current_decision, retain_decision, retain_questions, retained_decision,
)
from attune_harness.work_runtime import planning_questions
from test_work_contract import accept, control, decision, make, work  # noqa: F401


def snapshot(work):
    root = work[0].parent
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def unanswered(work):
    work[2]['intent']['goal'] = None
    record = make(work)
    shown = planning_questions(work[2]['directory'])
    saved = retain_questions(record, shown)
    return record, shown, saved


@pytest.mark.parametrize('corruption', ['digest', 'owner', 'kind', 'markdown'])
def test_tampered_display_is_unavailable_and_cannot_be_collected(work, corruption):
    record, _, saved = unanswered(work)
    altered = copy.deepcopy(saved)
    if corruption == 'digest':
        altered['display']['markdown'] += '\nAltered scope'
    elif corruption == 'owner':
        altered['work']['task_id'] = 'different-owner'
    elif corruption == 'kind':
        altered['display']['kind'] = 'approval'
    else:
        altered['display']['markdown'] = ''
    if corruption != 'digest':
        altered['digest'] = digest({k: v for k, v in altered.items() if k != 'digest'})
    path = Path(record['record_path']).with_name('decision.json')
    path.write_text(json.dumps(altered), encoding='utf-8')
    before = snapshot(work)
    display = retained_decision(record)
    assert display['state'] == 'unavailable' and display['error']
    with pytest.raises(ValueError):
        require_current_decision(record, saved['digest'])
    assert read_task(work[2]['directory'])['acceptance'] is None
    assert snapshot(work) == before


def test_symlinked_decision_never_restores_authority_or_changes_target(work, tmp_path):
    record = make(work)
    target = tmp_path / 'outside-decision.json'
    target.write_text('{}', encoding='utf-8')
    path = Path(record['record_path']).with_name('decision.json')
    try:
        path.symlink_to(target)
    except OSError as exc:
        pytest.skip(f'symlinks unavailable: {exc}')
    before = snapshot(work)
    assert retained_decision(record)['state'] == 'unavailable'
    with pytest.raises(ValueError, match='symlink'):
        require_current_decision(record, 'unknown')
    assert snapshot(work) == before and path.is_symlink()


def test_oversized_unicode_display_cannot_replace_retained_questions(work):
    record, _, saved = unanswered(work)
    display = {**saved['display'], 'markdown': '界' * (LIMIT // 2)}
    before = snapshot(work)
    with pytest.raises(ValueError, match='display byte limit'):
        retain_decision(record, display)
    assert require_current_decision(record, saved['digest']) == saved
    assert snapshot(work) == before


@pytest.mark.parametrize('change', ['accepted', 'revised'])
def test_delayed_display_writer_cannot_overwrite_after_authority_changes(work, change):
    record = make(work)
    saved = retain_decision(record, {'kind': 'spec', 'markdown': 'Original decision'})
    if change == 'accepted':
        accept(work, record)
    else:
        revise_work(work[2]['directory'], checkpoint=record['checkpoint_digest'],
                    changes={'intent': {'goal': 'A corrected scope'}})
    before = snapshot(work)
    with pytest.raises(ValueError, match='Work changed before retaining'):
        retain_decision(record, {'kind': 'spec', 'markdown': 'Delayed obsolete decision'})
    assert retained_decision(read_task(work[2]['directory']))['state'] == 'historical'
    assert retained_decision(record)['digest'] == saved['digest']
    assert snapshot(work) == before


@pytest.mark.parametrize('kind', ['empty', 'stale'])
def test_questions_must_match_current_unanswered_checkpoint(work, kind):
    if kind == 'empty':
        record = make(work)
        shown = planning_questions(work[2]['directory'])
        match = 'No unanswered'
    else:
        record, shown, _ = unanswered(work)
        record = revise_work(work[2]['directory'], checkpoint=record['checkpoint_digest'],
                             changes={'intent': {'context': ['Changed planning context']}})
        match = 'Planning questions changed'
    before = snapshot(work)
    with pytest.raises(ValueError, match=match):
        retain_questions(record, shown)
    assert snapshot(work) == before


def test_returned_display_is_detached_from_inputs_and_saved_bytes(work):
    record, _, saved = unanswered(work)
    displayed = retained_decision(record)
    saved['display']['definition']['title'] = 'Mutated return'
    displayed['display']['definition']['fields'].clear()
    fresh = retained_decision(record)
    assert fresh['display']['definition']['title'] == 'Clarify the work'
    assert len(fresh['display']['definition']['fields']) == 1
    assert read_task(work[2]['directory'])['acceptance'] is None


@pytest.mark.parametrize('bad', ['reference', 'disposition', 'task', 'version'])
def test_inconsistent_collector_receipt_cannot_bind_authority(work, bad):
    record = make(work)
    response = {'action': 'approve_task', 'token': 'synthetic-local-only'}
    accepted = decision(record)
    accepted['source']['reference'] = digest(response)
    receipt = {'response': response, 'result': {'disposition': 'approve_task',
               'completed': [record['request']['task_id']]}, 'adapter_version': 1}
    if bad == 'reference':
        receipt['response']['token'] = 'changed'
    elif bad == 'disposition':
        receipt['result']['disposition'] = 'redo_task'
    elif bad == 'task':
        receipt['result']['completed'] = ['another-task']
    else:
        receipt['adapter_version'] = True
    before = snapshot(work)
    with pytest.raises(ValueError, match='collector receipt differs'):
        bind_work_acceptance(work[2]['directory'], accepted, collector=receipt)
    assert snapshot(work) == before
    assert read_task(work[2]['directory'])['acceptance'] is None


def test_required_human_control_cannot_be_satisfied_by_bare_host_decision(work):
    from attune_harness.work_accept import SPEC_APPROVAL

    work[2]['controls'] = [{**SPEC_APPROVAL, 'required': True, 'phases': ['accept']}]
    record = make(work)
    before = snapshot(work)
    with pytest.raises(ValueError, match='actual collector receipt'):
        bind_work_acceptance(work[2]['directory'], decision(record), supported_controls=[SPEC_APPROVAL])
    assert snapshot(work) == before


def test_duplicate_supported_control_id_cannot_ambiguously_grant_acceptance(work):
    record = make(work)
    identity = {k: v for k, v in control().items() if k in ('id', 'kind', 'owner', 'version')}
    before = snapshot(work)
    with pytest.raises(ValueError, match='Duplicate supported control'):
        bind_work_acceptance(work[2]['directory'], decision(record),
                             supported_controls=[identity, {**identity, 'version': 2}])
    assert snapshot(work) == before


def test_correction_cannot_inject_review_handoff_authority(work):
    record = accept(work, make(work))
    before = snapshot(work)
    with pytest.raises(ValueError, match='derived by fresh planning staging'):
        revise_work(work[2]['directory'], checkpoint=record['checkpoint_digest'],
                    changes={'review_handoff': {'source': 'synthetic-untrusted-review'}})
    assert snapshot(work) == before
    assert read_task(work[2]['directory']) == record


def test_fresh_correction_cannot_swap_captured_input_set(work):
    record = accept(work, make(work))
    before = snapshot(work)
    with pytest.raises(ValueError, match='Stale proposal inputs cannot be rebound'):
        revise_work(work[2]['directory'], checkpoint=record['checkpoint_digest'],
                    changes={'inputs': ['unrelated.txt']}, require_fresh=True)
    assert snapshot(work) == before
    assert read_task(work[2]['directory']) == record
