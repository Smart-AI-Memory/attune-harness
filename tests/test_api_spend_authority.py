"""API spending permission belongs to one invocation, never a saved grant.

The transport boundaries below are local spies. No API or native model runs.
"""
# qualify: platform

import importlib
import json
import os

import pytest

from attune_harness.cli import build_parser, main
from attune_harness.task_contract import accept_task, read_task
from test_review import case, scripted
from test_task_contract import draft, response
from test_task_repair_effects import effect_case
from test_work_contract import work


@pytest.mark.parametrize('command', ['review', 'resume-review', 'fix', 'resume', 'resume-feature', 'plan', 'build'])
@pytest.mark.parametrize('allowed', [False, True])
def test_cli_execution_paths_forward_fresh_spending_permission(tmp_path, monkeypatch, capsys, command, allowed):
    """Exercise real parsing and routing, with dispatch replaced at the owner."""
    review = importlib.import_module('attune_harness.review')
    recovery = importlib.import_module('attune_harness.recovery')
    review_cli = importlib.import_module('attune_harness.review_cli')
    task_cli = importlib.import_module('attune_harness.task_cli')
    policies = importlib.import_module('attune_harness.task_policies')
    store = importlib.import_module('attune_harness.review_store')
    work_cli = importlib.import_module('attune_harness.work_cli')
    seen = []

    def execute(*args, allow_api_spend=False, **kwargs):
        seen.append(allow_api_spend)
        return {'status': 'ready' if command in ('review', 'resume-review') else 'completed'}

    for module in (review_cli, task_cli):
        monkeypatch.setattr(module, 'annotate', lambda result, _: result)
        monkeypatch.setattr(module, 'selected_configurations', lambda _: {})
    monkeypatch.setattr(work_cli, 'present', lambda *args, **kwargs: {'status': 'completed'})
    directory = str(tmp_path / 'task')
    if command == 'review':
        monkeypatch.setattr(review, 'review', execute)
        argv = ['review', 'request.json', '--run-dir', directory]
    elif command == 'resume-review':
        monkeypatch.setattr(recovery, 'resume_review', execute)
        argv = ['resume-review', directory, '--request', 'request.json',
                '--config', 'participants.json', '--checkpoint', 'checkpoint']
    elif command == 'fix':
        saved = {'request': {'repair': {}}, 'record_path': str(tmp_path / 'task' / 'record.json')}
        submitted = tmp_path / 'response.json'
        submitted.write_text('{}', encoding='utf-8')
        monkeypatch.setattr(task_cli, 'read_task', lambda _: saved)
        monkeypatch.setattr(task_cli, 'accept_task', lambda *args: saved)
        monkeypatch.setattr(task_cli, 'present_task', lambda *args, **kwargs: {'status': 'accepted'})
        monkeypatch.setattr(policies, 'execute_task', execute)
        argv = ['fix', '--task-dir', directory, '--task-response', str(submitted)]
    elif command in ('resume', 'resume-feature'):
        profile = 'feature-work-v1' if command == 'resume-feature' else 'assessment-intake-v1'
        monkeypatch.setattr(store, 'read_record', lambda _: {'task_profile': profile})
        monkeypatch.setattr(policies, 'execute_task', execute)
        argv = ['resume', directory]
    else:
        monkeypatch.setattr(work_cli, 'plan_work' if command == 'plan' else 'build_work', execute)
        argv = (['plan', '--task-dir', directory, '--run'] if command == 'plan'
                else ['build', directory])
    if allowed:
        argv.append('--allow-api-spend')
    assert main(argv) == 0, capsys.readouterr().out
    assert seen == [allowed]


def test_new_review_intake_does_not_save_spending_permission(case, monkeypatch, capsys):
    policies = importlib.import_module('attune_harness.task_policies')
    seen = []

    def execute(directory, *, max_operations=None, allow_api_spend=False):
        seen.append(allow_api_spend)
        return read_task(directory)

    monkeypatch.setattr(policies, 'execute_task', execute)
    assert main([
        'review', '--goal', 'Check evidence', '--project', str(case[0].parent),
        '--config', str(case[1]), '--task-dir', str(case[2]), '--criteria', 'Preserve uncertainty',
        '--query', 'quartz', '--document', 'project/guide.md', '--context', 'context.json',
        '--corpus', 'project', '--assessor', 'alpha', '--accept', '--allow-api-spend',
    ]) == 0, capsys.readouterr().out
    assert seen == [True]
    saved = read_task(case[2])
    assert saved['acceptance']['permissions'] == {'external': False, 'provider': False}
    assert 'allow_api_spend' not in json.dumps(saved)


@pytest.mark.parametrize('allowed', [False, True])
def test_review_task_response_uses_invocation_permission(tmp_path, monkeypatch, capsys, allowed):
    """Accepted response files do not replace the fresh execution permission."""
    task_cli = importlib.import_module('attune_harness.task_cli')
    policies = importlib.import_module('attune_harness.task_policies')
    submitted = tmp_path / 'response.json'
    submitted.write_text('{}', encoding='utf-8')
    saved = {'request': {}, 'record_path': str(tmp_path / 'task' / 'record.json')}
    monkeypatch.setattr(task_cli, 'read_task', lambda _: saved)
    monkeypatch.setattr(task_cli, 'accept_task', lambda *args: saved)
    monkeypatch.setattr(task_cli, 'present_task', lambda *args, **kwargs: {'status': 'accepted'})
    monkeypatch.setattr(task_cli, 'annotate', lambda result, _: result)
    monkeypatch.setattr(task_cli, 'selected_configurations', lambda _: {})
    seen = []

    def execute(*args, allow_api_spend=False, **kwargs):
        seen.append(allow_api_spend)
        return {'status': 'completed'}

    monkeypatch.setattr(policies, 'execute_task', execute)
    argv = ['review', '--task-response', str(submitted), '--task-dir', str(tmp_path / 'task')]
    assert main(argv + (['--allow-api-spend'] if allowed else [])) == 0, capsys.readouterr().out
    assert seen == [allowed]


def test_inspection_and_test_commands_do_not_offer_api_spending(capsys):
    parser = build_parser()
    for argv in (['status', 'task'], ['inspect-review', 'run'], ['test', '--task-dir', 'task']):
        with pytest.raises(SystemExit):
            parser.parse_args([*argv, '--allow-api-spend'])
    assert '--allow-api-spend' in capsys.readouterr().err


def test_plan_requires_run_for_api_spending_permission(tmp_path, monkeypatch, capsys):
    work_cli = importlib.import_module('attune_harness.work_cli')
    monkeypatch.setattr(work_cli, 'present', lambda *args, **kwargs: None)
    monkeypatch.setattr(work_cli, 'plan_work', lambda *args, **kwargs: pytest.fail('Unexpected planning dispatch'))
    assert main(['plan', '--task-dir', str(tmp_path / 'task'), '--allow-api-spend']) == 2
    assert 'Dispatch options require an explicit --run' in capsys.readouterr().out


@pytest.mark.parametrize('owner', [
    ('review', 'review'), ('review', 'execute_review'), ('recovery', 'resume_review'),
    ('task_policies', 'execute_task'), ('task_policies', 'execute_repair'),
    ('work_runtime', 'plan_work'), ('work_build', 'build_work'),
])
@pytest.mark.parametrize('invalid', [1, 'true', None])
def test_host_execution_owners_require_a_boolean_before_storage(owner, invalid):
    function = getattr(importlib.import_module('attune_harness.' + owner[0]), owner[1])
    arguments = {
        'review': (None, None, None), 'execute_review': (None, None, None),
        'resume_review': (None, None, None, None), 'execute_repair': (None, None),
    }.get(owner[1], (None,))
    with pytest.raises(ValueError, match='boolean'):
        function(*arguments, allow_api_spend=invalid)


def _spy_authorization(monkeypatch, module):
    original = module.authorize_external
    seen = []

    def authorize(selected, allow_external, allow_api_spend=False):
        seen.append(allow_api_spend)
        return original(selected, allow_external)

    monkeypatch.setattr(module, 'authorize_external', authorize)
    return seen


def _spy_assessment(monkeypatch):
    runtime = importlib.import_module('attune_harness.task_runtime')
    original = runtime.execute_assessment
    seen = []

    def execute(*args, allow_api_spend=False, **kwargs):
        seen.append(allow_api_spend)
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime, 'execute_assessment', execute)
    return seen


def test_legacy_review_resume_requires_fresh_permission_and_preserves_record(case, monkeypatch):
    review = importlib.import_module('attune_harness.review')
    recovery = importlib.import_module('attune_harness.recovery')
    _spy_authorization(monkeypatch, review)
    calls = _spy_assessment(monkeypatch)
    paused = review.review(*case, allow_api_spend=True, max_operations=2)
    assert paused['status'] == 'paused'
    completed = recovery.resume_review(case[2], case[0], case[1], paused['checkpoint_digest'])
    assert completed['status'] == 'completed'
    assert calls == [True, False]
    assert 'allow_api_spend' not in json.dumps(completed)


def test_assessment_resume_does_not_reuse_api_permission(case, monkeypatch):
    review = importlib.import_module('attune_harness.review')
    policies = importlib.import_module('attune_harness.task_policies')
    _spy_authorization(monkeypatch, review)
    calls = _spy_assessment(monkeypatch)
    draft(case)
    accept_task(case[2], response(case[2]))
    paused = policies.execute_task(case[2], allow_api_spend=True, max_operations=2)
    assert paused['status'] == 'paused'
    assert paused['acceptance']['permissions'] == {'external': False, 'provider': False}
    completed = policies.execute_task(case[2])
    assert completed['status'] == 'completed'
    assert calls == [True, False]
    assert 'allow_api_spend' not in json.dumps(read_task(case[2]))


@pytest.mark.parametrize('phase', ['plan', 'build'])
def test_feature_task_router_forwards_fresh_permission(monkeypatch, phase):
    policies = importlib.import_module('attune_harness.task_policies')
    runtime = importlib.import_module('attune_harness.work_runtime')
    saved = {'task_profile': 'feature-work-v1', 'status': 'accepted' if phase == 'build' else 'draft',
             'request': {'effects': {1: 2}} if phase == 'build' else {}}
    monkeypatch.setattr(policies, 'read_task', lambda _: saved)
    calls = []

    def execute(*args, allow_api_spend=False, **kwargs):
        calls.append(allow_api_spend)
        return saved

    monkeypatch.setattr(runtime, phase + '_work', execute)
    assert policies.execute_task('task', allow_api_spend=True) is saved
    assert policies.execute_task('task') is saved
    assert calls == [True, False]


def _spy_assignment(monkeypatch, module):
    original = module.dispatch_assignment
    seen = []

    def dispatch(*args, allow_api_spend=False, **kwargs):
        seen.append(allow_api_spend)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, 'dispatch_assignment', dispatch)
    return seen


def test_planning_forwards_to_each_turn_without_changing_factory_or_saved_permissions(work, monkeypatch):
    from test_work_contract import make
    from test_work_planning import Scripted

    runtime = importlib.import_module('attune_harness.work_runtime')
    _spy_authorization(monkeypatch, runtime)
    calls = _spy_assignment(monkeypatch, runtime)
    make(work)
    result = runtime.plan_work(work[2]['directory'], allow_api_spend=True, exchange_factory=Scripted)
    assert result['planning']['status'] == 'completed', result['planning'].get('error')
    assert calls == [True]
    assert result['planning']['permissions'] == {'external': False, 'native': False}
    assert 'allow_api_spend' not in json.dumps(read_task(work[2]['directory']))


@pytest.mark.skipif(os.name != 'posix', reason='POSIX build profile only')
def test_build_forwards_to_each_turn_without_changing_factory_or_saved_permissions(work, monkeypatch):
    from test_work_build import prepare, Worker

    build = importlib.import_module('attune_harness.work_build')
    _spy_authorization(monkeypatch, build)
    calls = _spy_assignment(monkeypatch, build)
    prepared = prepare(work)
    result = build.build_work(prepared[1], allow_api_spend=True, exchange_factory=Worker)
    assert result['build']['status'] == 'completed', result['build'].get('error')
    assert calls == [True, True, True]
    assert result['build']['permissions'] == {'external': False, 'native': False}
    assert 'allow_api_spend' not in json.dumps(read_task(prepared[1]))


@pytest.mark.skipif(os.name != 'posix', reason='POSIX repair profile only')
def test_repair_forwards_to_each_turn_without_changing_factory_or_saved_grants(effect_case, monkeypatch):
    from test_task_repair import prepare, proposal

    review = importlib.import_module('attune_harness.review')
    policies = importlib.import_module('attune_harness.task_policies')
    runtime = importlib.import_module('attune_harness.task_runtime')
    _spy_authorization(monkeypatch, review)
    calls = _spy_assignment(monkeypatch, runtime)
    directory = prepare(effect_case)
    result = policies.execute_task(directory, allow_api_spend=True, exchange_factory=scripted(proposal))
    assert result['status'] == 'completed', result['execution'].get('error')
    assert calls == [True, True]
    assert result['acceptance']['permissions'] == {'external': True, 'provider': False}
    assert 'allow_api_spend' not in json.dumps(read_task(directory))
