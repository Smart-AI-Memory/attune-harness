"""Offline contracts, stale context and stop behavior; no native model calls."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import ValidationError
import campaign as runner
from memory_contracts import host_route, normalize, router_prompt, worker_prompt
from attune_harness.process import ProcessResult

CASES = runner.cases()


def replacement(case, status=None):
    expected = case['expected']
    return {'status': status or expected['status'], 'record_version': case['input']['record']['version'],
            'reason': 'Fixture', 'replacements': [
                {'fact_id': target, 'source_id': source} for target, source in expected['replacements'].items()]}


def test_source_replacement_preserves_exception_and_does_not_mutate_input():
    case = deepcopy(CASES[0])
    before = deepcopy(case)
    result = normalize(case, replacement(case), 'replace')
    assert result['facts'][0]['text'] == case['input']['sources'][2]['text']
    assert result['facts'][1] == case['input']['record']['facts'][1]
    assert result['version'] == 5 and case == before


@pytest.mark.parametrize('change', ['version', 'same_version_content'])
def test_stale_snapshot_cannot_apply_after_current_memory_changes(change):
    case = CASES[0]
    current = deepcopy(case['input']['record'])
    if change == 'version':
        current['version'] += 1
    else:
        current['facts'][0]['text'] = 'Changed independently'
    with pytest.raises(ValueError, match='Stale'):
        normalize(case, replacement(case), 'replace', current)


def test_shared_store_update_needs_explicit_context_refresh():
    case = CASES[0]
    worker_snapshot = deepcopy(case['input']['record'])
    lead_snapshot = deepcopy(worker_snapshot)
    store = normalize(case, replacement(case), 'replace')
    assert lead_snapshot['version'] == 4 and store['version'] == 5
    with pytest.raises(ValueError, match='Stale'):
        normalize(case, replacement(case), 'replace', store)
    lead_snapshot = deepcopy(store)
    assert lead_snapshot == store and worker_snapshot != lead_snapshot


@pytest.mark.parametrize('edits', [
    [], [{'fact_id': 'unknown', 'source_id': 'S3'}],
    [{'fact_id': 'routine', 'source_id': 'unknown'}],
    [{'fact_id': 'payments', 'source_id': 'S3'}],
    [{'fact_id': 'routine', 'source_id': 'S3'}] * 2,
    [{'fact_id': 'routine', 'source_id': 'S3', 'text': 'Invented explanation'}],
])
def test_bad_bindings_and_invented_replacement_text_rejected(edits):
    value = replacement(CASES[0])
    value['replacements'] = edits
    with pytest.raises((ValueError, ValidationError)):
        normalize(CASES[0], value, 'replace')


def test_correct_binding_is_not_semantic_correctness():
    case = CASES[2]
    value = replacement(case, 'update')
    value['replacements'] = [{'fact_id': 'window', 'source_id': 'S2'}]
    result = normalize(case, value, 'replace')
    assert result['facts'][0]['text'] == 'Schedule the release for 10:00 UTC.'
    assert case['expected']['status'] == 'needs_review'


def test_previous_unsupported_claim_still_passes_rewrite_fields():
    path = runner.ROOT / 'docs/receipts/luna-stage-contract-2026-09-16/05-answer_preserve_exception-stage.json'
    old = json.loads(path.read_text())['assessment']['payload']['memory']
    assert 'because it costs less' in old
    case = CASES[0]
    facts = deepcopy(case['input']['record']['facts'])
    facts[0].update(text='Prefer Finch when detection is comparable because it costs less.', source_ids=['S3'])
    value = {'status': 'update', 'record_version': 4, 'reason': 'Fixture', 'facts': facts}
    result = normalize(case, value, 'rewrite')
    assert 'because it costs less' in result['facts'][0]['text']


@pytest.mark.parametrize('arm', ['rewrite', 'replace'])
def test_nonupdate_preserves_record_and_prohibits_changes(arm):
    case = CASES[1]
    value = {'status': 'no_change', 'record_version': 2, 'reason': 'Not accepted',
             'facts' if arm == 'rewrite' else 'replacements': []}
    assert normalize(case, value, arm) == case['input']['record']
    value['facts' if arm == 'rewrite' else 'replacements'] = (
        case['input']['record']['facts'] if arm == 'rewrite' else [{'fact_id': 'format', 'source_id': 'S2'}])
    with pytest.raises(ValueError, match='Non-update'):
        normalize(case, value, arm)


def test_private_grades_do_not_enter_prompts_or_host_rules():
    for case in CASES:
        for prompt in (worker_prompt(case, 'rewrite'), worker_prompt(case, 'replace'), router_prompt(case)):
            assert 'expected' not in prompt and 'rubric' not in prompt and 'id' not in prompt
        changed = deepcopy(case)
        changed['expected'] = {'route': 'arbitrary'}
        changed['rubric'] = 'Private grading changed'
        assert host_route(case) == host_route(changed)
        assert worker_prompt(case, 'replace') == worker_prompt(changed, 'replace')


def test_host_rules_miss_content_conflict_without_private_oracle():
    assert [host_route(case) for case in CASES[4:]] == ['luna', 'astra', 'luna']
    assert CASES[-1]['expected']['route'] == 'astra'


def test_luna_abstention_escalates_once_with_original_evidence():
    case = CASES[-1]
    calls = []
    def call(role, model, prompt, schema):
        calls.append((role, model, prompt))
        return {'value': replacement(case)}
    result = runner.execute_job(case, 'rules', call)
    assert [(c[0], c[1]) for c in calls] == [('worker', 'luna'), ('escalation', 'astra')]
    assert calls[1][2]['sources'] == case['input']['sources']
    assert 'previous_attempt' in calls[1][2]
    assert result['escalated'] and result['final']['response']['status'] == 'needs_review'


def test_routine_luna_success_has_no_stronger_repeat():
    case = CASES[4]
    calls = []
    def call(role, model, prompt, schema):
        calls.append(model)
        return {'value': replacement(case)}
    result = runner.execute_job(case, 'rules', call)
    assert calls == ['luna'] and not result['escalated']


def test_invalid_router_does_not_dispatch_worker():
    calls = []
    def call(*args):
        calls.append(args)
        return {'value': {'route': 'made_up'}}
    result = runner.execute_job(CASES[4], 'model', call)
    assert len(calls) == 1 and not result['final']['accepted']


def packet():
    return {'order': runner.schedule(), 'max_native_calls': 26,
            'campaign_timeout': 1800, 'per_call_timeout': 180}


def events(*, extra=None, usage=True):
    rows = [] if extra is None else [extra]
    rows += [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{}'}},
             {'type': 'turn.completed', 'usage': {'input_tokens': 2, 'output_tokens': 1} if usage else {}}]
    return '\n'.join(json.dumps(row) for row in rows)


@pytest.mark.parametrize('failure', ['tool', 'unknown_error', 'missing_usage', 'process'])
def test_native_boundary_stops_campaign_and_retains_receipt(tmp_path, monkeypatch, failure):
    calls = []
    def invoke(argv, prompt, **kwargs):
        calls.append(argv)
        if failure == 'process':
            return ProcessResult(argv, 1, '', 'failed', 'nonzero_exit')
        kind = 'command_execution' if failure == 'tool' else 'error'
        extra = None if failure == 'missing_usage' else {'type': 'item.completed', 'item': {'type': kind, 'message': 'Unknown failure'}}
        return ProcessResult(argv, 0, events(extra=extra, usage=failure != 'missing_usage'), '')
    monkeypatch.setattr(runner, 'invoke', invoke)
    trial = runner.Campaign(packet(), tmp_path)
    with pytest.raises(RuntimeError):
        trial.run()
    assert len(calls) == 1 and trial.ledger['status'] == 'stopped'
    assert len(list(tmp_path.glob('00-*.json'))) == 1
    with pytest.raises(FileExistsError):
        runner.Campaign(packet(), tmp_path)


@pytest.mark.parametrize('remaining', [0, 1])
def test_campaign_deadline_constrains_active_dispatch(tmp_path, monkeypatch, remaining):
    now = [0.0]
    monkeypatch.setattr(runner, 'time', SimpleNamespace(monotonic=lambda: now[0]))
    trial = runner.Campaign(packet(), tmp_path)
    now[0] = 1800 - remaining
    calls = []
    def invoke(argv, prompt, **kwargs):
        calls.append(kwargs['timeout'])
        return ProcessResult(argv, 0, events(), '')
    monkeypatch.setattr(runner, 'invoke', invoke)
    if remaining:
        trial.call('fixture', 'worker', 'luna', {}, runner.REPLACE)
        assert calls == [1]
    else:
        with pytest.raises(RuntimeError, match='Deadline'):
            trial.call('fixture', 'worker', 'luna', {}, runner.REPLACE)
        assert calls == []


def test_native_cap_prevents_dispatch(tmp_path, monkeypatch):
    trial = runner.Campaign(packet(), tmp_path)
    trial.ledger['attempts'] = [{}] * 26
    monkeypatch.setattr(runner, 'invoke', lambda *args, **kwargs: pytest.fail('Must not dispatch'))
    with pytest.raises(RuntimeError, match='limit'):
        trial.call('fixture', 'worker', 'luna', {}, runner.REPLACE)


def test_schedule_has_eight_authoring_and_nine_routing_jobs():
    plan = runner.schedule()
    assert len(plan) == 17
    assert sum(item['arm'] in ('rewrite', 'replace') for item in plan) == 8
    assert sum(item['arm'] in ('direct', 'rules', 'model') for item in plan) == 9
