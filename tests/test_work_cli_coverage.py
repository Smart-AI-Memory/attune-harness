"""Public CLI refusals preserve authority, inputs and retained work evidence."""

import json

import pytest

from attune_harness.cli import main
from attune_harness.task_contract import read_task
from attune_harness.work_runtime import plan_work
from test_work_contract import accept, make, work  # noqa: F401


def run(capsys, *arguments):
    code = main([str(argument) for argument in arguments])
    return code, json.loads(capsys.readouterr().out)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize(('options', 'detail'), [
    (['--review-dispositions', 'unused.json'], '--review-dispositions requires --stage'),
    (['--preserve-completed'], '--preserve-completed requires --revise'),
    (['--project', 'unused'], 'Creation options require --request'),
    (['--config', 'unused'], 'Creation options require --request'),
    (['--import-plan', 'unused'], 'Creation options require --request'),
    (['--allow-external'], 'Dispatch options require an explicit --run'),
    (['--allow-native'], 'Dispatch options require an explicit --run'),
    (['--max-operations', '1'], 'Dispatch options require an explicit --run'),
    (['--answers', 'unused.json', '--checkpoint', 'old'], 'Answers carry their own checkpoint'),
    (['--accept'], 'This action requires --checkpoint'),
    (['--stage'], 'This action requires --checkpoint'),
    (['--revise', 'unused.json'], 'This action requires --checkpoint'),
    (['--reimport'], 'This action requires --checkpoint'),
])
def test_invalid_plan_options_do_not_change_retained_work(work, capsys, options, detail):
    record = make(work)
    before = snapshot(work[0].parent)
    code, result = run(capsys, 'plan', '--task-dir', work[2]['directory'], *options)
    assert code == 2 and result['blocking'] is True
    assert detail in result['error']['detail']
    assert result['record_path'] == record['record_path']
    assert snapshot(work[0].parent) == before


@pytest.mark.parametrize('payload', [[], {}, {'intent': {}, 'approved': True}])
def test_malformed_creation_request_cannot_create_an_owner(work, capsys, tmp_path, payload):
    request = tmp_path / 'request.json'
    request.write_text(json.dumps(payload), encoding='utf-8')
    before = snapshot(tmp_path)
    code, result = run(capsys, 'plan', '--task-dir', work[2]['directory'],
                       '--request', request, '--project', work[0], '--config', work[1])
    assert code == 2
    assert 'Request must contain intent and supported authoring fields' in result['error']['detail']
    assert not work[2]['directory'].exists()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('options', [[], ['--project', 'unused'], ['--config', 'unused'],
                                    ['--project', 'unused', '--config', 'unused', '--checkpoint', 'old']])
def test_creation_requires_explicit_project_and_registry_without_old_authority(work, capsys, options):
    before = snapshot(work[0].parent)
    code, result = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--request', 'unused.json', *options)
    assert code == 2
    assert 'New work requires --project and --config, without an old checkpoint' in result['error']['detail']
    assert snapshot(work[0].parent) == before


@pytest.mark.parametrize(('options', 'detail'), [
    (['reconcile-task', '--event', 'unobserved', '--reply', 'unused.json'], 'explicit file observations only'),
    (['reconcile-task', '--event', 'unobserved', '--retry-read-only'], 'explicit file observations only'),
    (['reconcile-task', '--event', 'unobserved', '--observe-file'], 'requires the current --checkpoint'),
    (['cancel-task', '--reason', 'stop'], 'not qualified for feature work'),
    (['transfer-task', '--assessor', 'other', '--reason', 'move'], 'not qualified for feature work'),
])
def test_unqualified_controls_preserve_feature_work(work, capsys, options, detail):
    make(work)
    before = snapshot(work[0].parent)
    code, result = run(capsys, options[0], work[2]['directory'], *options[1:])
    assert code == 2 and result['blocking'] is True
    assert detail in result['error']['detail']
    assert snapshot(work[0].parent) == before


@pytest.mark.parametrize('state', ['accepted', 'planning', 'wrong-checkpoint'])
def test_decision_preview_cannot_replace_inapplicable_authority(work, capsys, state):
    make(work)
    options = []
    if state == 'accepted':
        accept(work)
        detail = 'Decision preview requires a draft'
    elif state == 'planning':
        plan_work(work[2]['directory'])
        detail = 'Resolve or stage the planning run'
    else:
        options = ['--checkpoint', '0' * 64]
        detail = 'Decision preview requires the current checkpoint'
    before = snapshot(work[0].parent)
    code, result = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--decision', *options)
    assert code == 2 and detail in result['error']['detail']
    assert snapshot(work[0].parent) == before


def test_revision_retains_previous_draft_and_presents_new_intent(work, capsys, tmp_path):
    draft = make(work)
    revision = tmp_path / 'revision.json'
    revision.write_text(json.dumps({'intent': {'goal': 'Export findings with stable identifiers'}}), encoding='utf-8')
    project_before = snapshot(work[0])
    code, result = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--revise', revision,
                       '--checkpoint', draft['checkpoint_digest'])
    assert code == 0 and result['status'] == 'draft'
    assert result['intent']['goal'] == 'Export findings with stable identifiers'
    current = read_task(work[2]['directory'])
    assert current['checkpoint_digest'] != draft['checkpoint_digest']
    assert current['acceptance'] is None
    assert current['history'][0]['request'] == draft['request']
    assert snapshot(work[0]) == project_before


def test_stale_status_and_failed_action_retain_evidence_without_repairing_inputs(work, capsys):
    draft = make(work)
    (work[0] / 'source.py').write_text('def value():\n    return 99\n', encoding='utf-8')
    before = snapshot(work[0].parent)
    code, result = run(capsys, 'status', work[2]['directory'])
    assert code == 0 and result['status'] == 'stale'
    assert result['blocking'] is True and result['freshness_error']
    assert result['questions'] is None
    assert result['evidence']['record_path'] == draft['record_path']
    code, failure = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--accept', '--checkpoint', 'wrong')
    assert code == 2 and 'exact displayed work checkpoint' in failure['error']['detail']
    assert failure['freshness_error'] == result['freshness_error']
    assert failure['next_action'] == result['next_action']
    assert snapshot(work[0].parent) == before


def test_creation_and_bound_answers_retain_questions_without_implicit_acceptance(work, capsys, tmp_path):
    request = tmp_path / 'request.json'
    intent = {**work[2]['intent'], 'goal': None, 'acceptance': []}
    request.write_text(json.dumps({'intent': intent, 'assignments': work[2]['assignments']}), encoding='utf-8')
    code, created = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--request', request,
                        '--project', work[0], '--config', work[1])
    assert code == 0 and created['status'] == 'draft'
    assert created['questions']['missing'] == ['goal', 'acceptance']
    assert created['decision']
    answers = tmp_path / 'answers.json'
    answers.write_text(json.dumps({'schema_version': 1,
                                   'checkpoint_digest': created['questions']['checkpoint_digest'],
                                   'answers': {'answer_0': 'Export every finding', 'answer_1': None}}), encoding='utf-8')
    code, revised = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--answers', answers)
    assert code == 0 and revised['status'] == 'draft'
    assert revised['questions']['missing'] == ['acceptance']
    assert revised['intent']['goal'] == 'Export every finding'
    retained = read_task(work[2]['directory'])
    assert retained['acceptance'] is None and 'planning' not in retained
    before = snapshot(work[0].parent)
    code, stale = run(capsys, 'plan', '--task-dir', work[2]['directory'], '--answers', answers)
    assert code == 2 and 'Stale' in stale['error']['detail']
    assert snapshot(work[0].parent) == before
