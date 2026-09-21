"""Failure-sensitive intake checks use real forms and storage, with poisoned dispatch."""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from attune_harness import review_participants, voyage_provider
from attune_harness.cli import main
from attune_harness.review_contract import load_registry
from attune_harness.review_store import RunStore, PersistenceError
from attune_harness.task_contract import (accept_task, check_fresh, create_task,
                                         read_task, revise_task)
from attune_harness.task_cli import (clear_template_cache, present_task, task_template)
from test_review import case, change


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def poison(*args, **kwargs):
        pytest.fail('Intake attempted participant/provider dispatch')
    monkeypatch.setattr(review_participants, 'NativeExchange', poison)
    monkeypatch.setattr(review_participants, 'ReviewExchange', poison)
    monkeypatch.setattr(voyage_provider, 'VoyageProvider', poison)
    clear_template_cache()


def draft(case, *, directory=None, **kwargs):
    answers = {'criteria': 'Identify unsupported claims and preserve uncertainty',
               'query': 'quartz retention policy', 'document': 'project/guide.md',
               'context': 'context.json', 'corpus': 'project', 'assessor': 'alpha'}
    if kwargs.get('plan') == 'independent-review':
        answers['reviewer'] = 'beta'
    answers.update(kwargs.pop('answers', {}))
    return create_task(case[0].parent, case[1], goal='Check the guide',
                       directory=directory or case[2], answers=answers, **kwargs)


def response(directory):
    value = present_task(directory)['submission']
    value['accepted'] = True
    return value


@pytest.mark.parametrize('plan,count', [('solo', 1), ('independent-review', 2)])
def test_intake_binds_one_identity_and_does_not_claim_execution(case, plan, count):
    record = draft(case, plan=plan)
    shown = present_task(case[2])
    assert shown['status'] == 'draft' and shown['submission']['accepted'] is False
    assert shown['execution_status'] == 'not_started'
    accepted = accept_task(case[2], response(case[2]))
    assert accepted == read_task(case[2]) and accepted['status'] == 'accepted'
    req = accepted['request']
    assignments = accepted['bindings']['assessment']['assignments']
    assert len(assignments) == count
    for binding in [accepted['bindings']['retrieval'], accepted['bindings']['assessment'], *assignments.values()]:
        assert binding['task_id'] == record['request']['task_id'] == req['task_id']
        assert binding['revision'] == 1
        assert binding['request_digest'] == accepted['acceptance']['request_digest']
    assert len({a['assignment_id'] for a in assignments.values()}) == count
    assert accepted['events'] == []
    assert present_task(case[2])['submission'] is None
    assert present_task(case[2])['execution_status'] == 'not_started'


def test_single_member_registry_is_new_task_only(case):
    change(case[1], lambda value: value['participants'].pop('beta'))
    with pytest.raises(ValueError, match='2–16'):
        load_registry(case[1])
    draft(case)
    assert accept_task(case[2], response(case[2]))['status'] == 'accepted'


@pytest.mark.parametrize('update', [
    lambda v: v.update(accepted=False),
    lambda v: v.update(accepted=1),
    lambda v: v.update(task_id='another-task'),
    lambda v: v.update(revision=True),
    lambda v: v.update(revision=2),
    lambda v: v.update(form_revision='stale'),
    lambda v: v.update(checkpoint_digest='stale'),
    lambda v: v.update(unrecognized=True),
    lambda v: v['answers'].update(goal=''),
    lambda v: v['answers'].update(criteria=None),
    lambda v: v['answers'].update(assessor='unknown'),
    lambda v: v['answers'].update(extra='not permitted'),
    lambda v: v['permissions'].update(external=1),
    lambda v: v['permissions'].update(repair=True),
])
def test_invalid_response_leaves_draft_unchanged(case, update):
    draft(case)
    before = (case[2] / 'record.json').read_bytes()
    value = response(case[2]); update(value)
    with pytest.raises((ValueError, TypeError)):
        accept_task(case[2], value)
    assert (case[2] / 'record.json').read_bytes() == before


def test_independent_review_cannot_alias_assessor(case):
    draft(case, plan='independent-review')
    value = response(case[2]); value['answers']['reviewer'] = 'alpha'
    with pytest.raises(ValueError, match='distinct'):
        accept_task(case[2], value)


@pytest.mark.parametrize('target', ['document', 'context', 'corpus', 'registry'])
def test_changes_after_presentation_require_revision(case, target):
    draft(case)
    value = response(case[2])
    root = case[0].parent
    if target == 'document':
        (root / 'project/guide.md').write_text('Changed same selected input', encoding='utf-8')
    elif target == 'context':
        with (root / 'context.json').open('a') as stream:
            stream.write('\n')
    elif target == 'corpus':
        (root / 'project/new.md').write_text('New evidence', encoding='utf-8')
    else:
        change(case[1], lambda v: v['participants']['alpha'].update(max_turns=4))
    with pytest.raises(ValueError, match='Stale'):
        accept_task(case[2], value)
    old = read_task(case[2])
    revised = revise_task(case[2], checkpoint=old['checkpoint_digest'])
    assert revised['request']['revision'] == 2
    with pytest.raises(ValueError, match='Stale'):
        accept_task(case[2], value)
    assert accept_task(case[2], response(case[2]))['status'] == 'accepted'


def test_revision_clears_permissions_and_changes_assignment_identity(case):
    draft(case)
    value = response(case[2]); value['permissions']['external'] = True
    accepted = accept_task(case[2], value)
    old_assignment = accepted['bindings']['assessment']['assignments']['assessor']['assignment_id']
    revised = revise_task(case[2], checkpoint=accepted['checkpoint_digest'], answers={'goal': 'A different goal'})
    assert revised['status'] == 'draft' and revised['acceptance'] is None and revised['bindings'] == {}
    assert revised['history'][0]['acceptance'] == accepted['acceptance']
    shown = present_task(case[2])
    assert shown['submission']['permissions'] == {'external': False, 'provider': False}
    assert shown['submission']['accepted'] is False
    new = accept_task(case[2], response(case[2]))
    assert new['bindings']['assessment']['assignments']['assessor']['assignment_id'] != old_assignment


def test_unchanged_answers_reuse_acceptance_without_reapproval(case):
    draft(case)
    submitted = response(case[2])
    accepted = accept_task(case[2], submitted)
    before = (case[2] / 'record.json').read_bytes()
    assert revise_task(case[2], checkpoint=accepted['checkpoint_digest'],
                       answers={'query': accepted['request']['answers']['query']}) == accepted
    assert (case[2] / 'record.json').read_bytes() == before
    with pytest.raises(ValueError, match='already accepted'):
        accept_task(case[2], submitted)


def test_changed_budget_invalidates_prior_acceptance(case):
    draft(case)
    accepted = accept_task(case[2], response(case[2]))
    revised = revise_task(case[2], checkpoint=accepted['checkpoint_digest'],
                          budget={'max_operations': 20, 'max_attempts': 1, 'max_output_bytes': 4096})
    assert revised['request']['revision'] == 2 and revised['bindings'] == {}


@pytest.mark.parametrize('budget', [
    {'max_operations': True, 'max_attempts': 1, 'max_output_bytes': 32768},
    {'max_operations': 101, 'max_attempts': 1, 'max_output_bytes': 32768},
    {'max_operations': 100, 'max_attempts': 2, 'max_output_bytes': 32768},
    {'max_operations': 100, 'max_attempts': 1, 'max_output_bytes': 32769},
    {},
])
def test_invalid_budget_creates_no_task(case, budget):
    with pytest.raises(ValueError):
        draft(case, budget=budget)
    assert not case[2].exists()


def test_task_state_cannot_be_ingested_as_evidence(case):
    target = case[0].parent / 'project/task'
    with pytest.raises(ValueError, match='ingest task state'):
        draft(case, directory=target)
    assert not target.exists()


def test_task_state_overlap_from_headless_response_is_rejected(case):
    create_task(case[0].parent, case[1], goal='Review', directory=case[2])
    value = response(case[2])
    value['answers'].update(goal='Review', criteria='Check sources', query='quartz',
                            document='project/guide.md', context='context.json', corpus='.', assessor='alpha')
    with pytest.raises(ValueError, match='ingest task state'):
        accept_task(case[2], value)
    assert read_task(case[2])['status'] == 'draft'


@pytest.mark.parametrize('field,path', [('document', '../escape.md'), ('context', '../outside.json'), ('corpus', '..')])
def test_input_scope_cannot_escape_project(case, field, path):
    with pytest.raises(ValueError, match='inside the project'):
        draft(case, answers={field: path})
    assert not case[2].exists()


def test_copy_and_modified_bindings_cannot_be_accepted(case):
    draft(case)
    original = response(case[2])
    copied = case[0].parent / 'copy'
    shutil.copytree(case[2], copied)
    with pytest.raises(ValueError, match='Copied task'):
        accept_task(copied, original)
    accepted = accept_task(case[2], original)
    accepted['bindings']['retrieval']['task_id'] = 'foreign'
    store = RunStore(case[2], existing=True)
    with store.lease():
        store.save(accepted)
    with pytest.raises(ValueError, match='bindings differ'):
        read_task(case[2])


def test_cache_is_unbound_equivalent_and_isolated_between_tasks(case):
    draft(case)
    cold = present_task(case[2]); warm = present_task(case[2]); bypass = present_task(case[2], bypass=True)
    assert [x['intake_metrics']['cache'] for x in (cold, warm, bypass)] == ['miss', 'hit', 'bypass']
    assert cold['submission'] == warm['submission'] == bypass['submission']
    assert cold['definition'] == warm['definition'] == bypass['definition']
    warm['definition']['fields'][0]['text'] = 'mutated'
    assert present_task(case[2])['definition'] == cold['definition']
    other = case[0].parent / 'other'
    draft(case, directory=other)
    second = present_task(other)
    assert second['intake_metrics']['cache'] == 'hit'
    assert second['task_id'] != cold['task_id']
    assert second['submission']['accepted'] is False
    with pytest.raises(ValueError, match='foreign'):
        accept_task(other, response(case[2]))


def test_cache_corruption_and_eviction_are_legible(case, monkeypatch):
    from attune_harness import task_contract as task_cli
    monkeypatch.setattr(task_cli, 'CACHE_LIMIT', 1)
    draft(case)
    original = present_task(case[2])
    key = next(iter(task_cli._TEMPLATES))
    task_cli._TEMPLATES[key] = ('broken', 'not-a-checksum')
    rebuilt = present_task(case[2])
    assert rebuilt['intake_metrics']['cache'] == 'corrupt'
    assert rebuilt['definition'] == original['definition']
    other = case[0].parent / 'other'
    draft(case, directory=other, plan='independent-review')
    assert present_task(other)['intake_metrics']['cache'] == 'miss'
    assert len(task_cli._TEMPLATES) == 1
    assert present_task(case[2])['intake_metrics']['cache'] == 'miss'
    clear_template_cache()
    assert not task_cli._TEMPLATES


@pytest.mark.parametrize('dependency', ['registry', 'evidence', 'project', 'policy'])
def test_template_dependencies_invalidate_cache(case, dependency):
    record = draft(case)
    req = record['request']
    assert task_template(req)[1]['cache'] == 'miss'
    changed = copy.deepcopy(req)
    if dependency == 'registry':
        changed['registry']['participants']['alpha']['max_turns'] = 4
    elif dependency == 'evidence':
        changed['evidence']['document']['sha256'] = 'different'
    elif dependency == 'project':
        changed['project_root'] = str(case[0].parent / 'other-project')
    else:
        changed['budgets']['max_operations'] = 20
    assert task_template(changed)[1]['cache'] == 'miss'


@pytest.mark.parametrize('default', ['accepted', 'goal', 'permissions', 'api_key', 'budgets'])
def test_profiles_cannot_supply_authority_or_free_text_goals(case, default):
    profile = case[0].parent / 'profile.json'
    profile.write_text(json.dumps({'schema_version': 1, 'project_root': str(case[0].parent),
                                   'defaults': {default: 'untrusted'}}), encoding='utf-8')
    with pytest.raises(ValueError, match='Profile may contain only'):
        draft(case, profile=profile)
    assert not case[2].exists()


def test_explicit_profile_origin_and_corrections_are_visible(case):
    profile = case[0].parent / 'profile.json'
    profile.write_text(json.dumps({'schema_version': 1, 'project_root': str(case[0].parent),
                                   'defaults': {'assessor': 'alpha', 'query': 'profile query'}}), encoding='utf-8')
    create_task(case[0].parent, case[1], goal='New goal', directory=case[2],
                 profile=profile, answers={'query': 'explicit correction'})
    shown = present_task(case[2])
    assert shown['defaults_origin']['path'] == str(profile)
    assert shown['submission']['answers']['assessor'] == 'alpha'
    assert shown['submission']['answers']['query'] == 'explicit correction'
    assert shown['defaults_origin']['fields'] == ['assessor']
    assert shown['submission']['accepted'] is False


def test_persistence_failure_never_looks_accepted(case, monkeypatch):
    draft(case)
    value = response(case[2])
    def fail(*args):
        raise PersistenceError('injected disk failure')
    monkeypatch.setattr(RunStore, 'save', fail)
    with pytest.raises(PersistenceError):
        accept_task(case[2], value)
    assert read_task(case[2])['status'] == 'draft'


def test_cli_goal_intake_and_headless_response(case, capsys, monkeypatch):
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    args = ['review', '--goal', 'Check guide', '--project', str(case[0].parent),
            '--config', str(case[1]), '--task-dir', str(case[2]),
            '--criteria', 'Preserve uncertainty', '--query', 'quartz',
            '--document', 'project/guide.md', '--context', 'context.json',
            '--corpus', 'project', '--assessor', 'alpha']
    assert main(args) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'draft' and result['execution_status'] == 'not_started'
    submission = result['submission']; submission['accepted'] = True
    path = case[0].parent / 'task-response.json'
    path.write_text(json.dumps(submission), encoding='utf-8')
    assert main(['review', '--task-response', str(path), '--task-dir', str(case[2]), '--intake-only']) == 0
    accepted = json.loads(capsys.readouterr().out)
    assert accepted['status'] == 'accepted' and accepted['execution_status'] == 'not_started'
    assert accepted['task_id'] == result['task_id']


def test_cli_accept_incomplete_intake_never_dispatches(case, capsys, monkeypatch):
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    assert main(['review', '--goal', 'Check guide', '--project', str(case[0].parent),
                 '--config', str(case[1]), '--task-dir', str(case[2]), '--accept']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
    assert read_task(case[2])['status'] == 'draft'


@pytest.mark.parametrize('extra', [
    ['--goal', 'A goal'], ['--accept'], ['--task-dir', 'another'],
])
def test_cli_rejects_ambiguous_legacy_and_task_modes(case, capsys, extra):
    with pytest.raises(SystemExit) as error:
        main(['review', str(case[0]), '--config', str(case[1]), '--run-dir', str(case[2]), *extra])
    assert error.value.code == 2 and not case[2].exists()


def test_core_still_imports_with_only_standard_library(tmp_path):
    source = str(Path(__file__).resolve().parents[1] / 'src')
    code = f'import sys;sys.path.insert(0,{source!r});from attune_harness import Task;assert Task("x","y",("z",)).schema_version==1'
    run = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


def test_existing_project_task_state_excluded_with_external_new_task(case):
    state = case[0].parent / '.attune-harness/tasks/prior'
    state.mkdir(parents=True)
    (state / 'evidence.md').write_text('Prior private task evidence', encoding='utf-8')
    target = case[0].parent.parent / (case[0].parent.name + '-external-task')
    with pytest.raises(ValueError, match='existing project task state'):
        draft(case, directory=target, answers={'corpus': '.'})
    assert not target.exists()


def test_presentation_reuses_answers_but_never_approval(case):
    draft(case)
    value = response(case[2])
    accepted = accept_task(case[2], value)
    shown = present_task(case[2])
    assert shown['answers'] == accepted['request']['answers']
    assert shown['submission'] is None


@pytest.mark.parametrize('target', ['registry', 'document'])
def test_change_during_form_validation_cannot_accept(case, monkeypatch, target):
    import attune_forms
    draft(case)
    submitted = response(case[2])
    collect = attune_forms.collect_form_response
    def race(*args, **kwargs):
        result = collect(*args, **kwargs)
        if target == 'registry':
            change(case[1], lambda v: v['participants']['alpha'].update(max_turns=4))
        else:
            (case[0].parent / 'project/guide.md').write_text('Changed while validating', encoding='utf-8')
        return result
    monkeypatch.setattr(attune_forms, 'collect_form_response', race)
    with pytest.raises(ValueError, match='Stale'):
        accept_task(case[2], submitted)
    assert read_task(case[2])['status'] == 'draft'


def test_profile_project_and_participant_are_validated(case):
    profile = case[0].parent / 'profile.json'
    data = {'schema_version': 1, 'project_root': str(case[0].parent / 'other'),
            'defaults': {'assessor': 'alpha'}}
    profile.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='another project'):
        draft(case, profile=profile)
    data['project_root'] = str(case[0].parent); data['defaults']['assessor'] = 'missing'
    profile.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='Unknown assessor'):
        draft(case, profile=profile)


def test_response_cannot_override_saved_registry_with_cli(case, capsys):
    draft(case)
    with pytest.raises(SystemExit) as error:
        main(['review', '--task-response', 'reply.json', '--task-dir', str(case[2]), '--config', 'other.json'])
    assert error.value.code == 2


def test_existing_writer_lease_blocks_acceptance(case):
    draft(case)
    submitted = response(case[2])
    store = RunStore(case[2], existing=True)
    with store.lease(), pytest.raises(PersistenceError, match='busy'):
        accept_task(case[2], submitted)
    assert read_task(case[2])['status'] == 'draft'


def test_symlink_task_storage_is_rejected(case):
    root = case[0].parent
    real = root / 'real'; real.mkdir()
    alias = root / 'alias'
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip('Host lacks symlink creation permission')
    with pytest.raises(ValueError, match='symlink'):
        draft(case, directory=alias / 'task')
    assert not (real / 'task').exists()


def test_declined_interactive_intake_remains_unaccepted(case, monkeypatch, capsys):
    import builtins
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    supplied = iter(['Useful evidence assessment', 'quartz', 'project/guide.md', 'context.json',
                     'project', 'alpha', 'n'])
    monkeypatch.setattr(builtins, 'input', lambda _: next(supplied))
    assert main(['review', '--goal', 'Check guide', '--project', str(case[0].parent),
                 '--config', str(case[1]), '--task-dir', str(case[2])]) == 1
    assert read_task(case[2])['status'] == 'draft'


def test_interactive_complete_intake_is_accepted_without_dispatch(case, monkeypatch, capsys):
    import builtins
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    supplied = iter(['Useful evidence assessment', 'quartz', 'project/guide.md', 'context.json',
                     'project', 'alpha', 'yes'])
    monkeypatch.setattr(builtins, 'input', lambda _: next(supplied))
    assert main(['review', '--intake-only', '--goal', 'Check guide', '--project', str(case[0].parent),
                 '--config', str(case[1]), '--task-dir', str(case[2])]) == 0
    record = read_task(case[2])
    assert record['status'] == 'accepted' and record['events'] == []


def test_changed_form_meaning_invalidates_a_bound_response(case, monkeypatch):
    from attune_harness import task_contract as task_cli
    draft(case)
    submitted = response(case[2])
    original = task_cli.task_template
    def changed(*args, **kwargs):
        template, metrics = original(*args, **kwargs)
        template['definition']['fields'][0]['text'] = 'Changed meaning requiring new acceptance'
        return template, metrics
    monkeypatch.setattr(task_cli, 'task_template', changed)
    with pytest.raises(ValueError, match='Stale'):
        accept_task(case[2], submitted)
    assert read_task(case[2])['status'] == 'draft'
