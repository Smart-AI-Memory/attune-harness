"""O-72: bounded refusal continuations, with resulting state checked.

Only fixed argv reaches the public CLI entry point. Printed guidance is compared
with that allowlist, never evaluated or passed to a shell. Draft intake is a
useful next step, not accepted or executed work. Manual path/status instructions
are exercised as explicit operator corrections/inspections, not automatic fixes.
Windows shell, intake, recovery and parity remain with their existing owner.
This module deliberately does not change platform qualification selections.
"""

import hashlib
import io
import json
import os
from pathlib import Path
import shlex

import pytest

from attune_harness.cli import main

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='bounded POSIX audit; Windows has a separate owner')

INSPECT = ('Inspect the error. If a task directory was created, read it with attune-harness status '
           'before running anything again')


@pytest.fixture
def lane(tmp_path, monkeypatch, capsys):
    """Local fixtures and raw command receipts; prohibit participant execution."""
    from attune_harness import task_policies, work_cli

    def no_dispatch(*args, **kwargs):
        pytest.fail('Refusal continuation must not dispatch participants or execute work')

    monkeypatch.setattr(task_policies, 'execute_task', no_dispatch)
    monkeypatch.setattr(work_cli, 'plan_work', no_dispatch)
    monkeypatch.setattr(work_cli, 'build_work', no_dispatch)
    for name in tuple(os.environ):
        if name.startswith('ATTUNE_'):
            monkeypatch.delenv(name)
    monkeypatch.setenv('ATTUNE_USAGE_PING', '0')
    monkeypatch.setenv('ATTUNE_VERSION_CHECK', '0')
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    base = tmp_path.resolve()
    project = base / "project space's"
    project.mkdir()
    monkeypatch.chdir(project)
    calls = []

    def run(argv):
        # All callers below author argv independently of output text. These
        # controls also refuse the flags that could accept/dispatch/overwrite.
        assert argv[0] in ('init', 'review', 'plan', 'status')
        assert not set(argv) & {'--accept', '--run', '--force', '--task-response',
                                '--allow-external', '--allow-native', '--allow-provider'}
        if argv[0] == 'init':
            assert argv == ['init', '--project', str(project)]
        capsys.readouterr()
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code
        out = capsys.readouterr()
        calls.append({'argv': argv, 'cwd': str(Path.cwd()), 'exit': code,
                      'stdout': out.out, 'stderr': out.err})
        # Keep the original failures beside successes, even if an assertion fails.
        (base / f'command-{len(calls):02}.json').write_text(json.dumps(calls[-1], indent=2), encoding='utf-8')
        assert not out.err, calls[-1]
        envelope = json.loads(out.out)
        return code, envelope

    return project, base / 'task', run


def review(project, task, *, config='participants.json', **answers):
    argv = ['review', '--goal', 'Check the guide', '--project', str(project),
            '--config', str(config), '--task-dir', str(task), '--intake-only']
    for name, value in answers.items():
        argv.extend((f'--{name}', str(value)))
    return argv


def init_continuation(run, refusal, project):
    """Match the golden command, then run only our separately constructed argv."""
    assert refusal['next_action'] == (
        f'Create one with: attune-harness init --project {shlex.quote(str(project))} '
        '(offline demo participants), or pass --config with an existing registry')
    code, created = run(['init', '--project', str(project)])
    assert (code, created['status'], created['profile']) == (0, 'created', 'demo')
    registry = json.loads((project / 'participants.json').read_text(encoding='utf-8'))
    assert set(registry['participants']) == {'lead', 'reviewer'}
    assert all(p['adapter'] == 'deterministic' for p in registry['participants'].values())
    return registry


def draft_review(run, argv, task):
    code, envelope = run(argv)
    assert (code, envelope['status'], envelope['operation']) == (1, 'draft', 'task-intake'), envelope
    record = json.loads((task / 'record.json').read_text(encoding='utf-8'))
    assert record['status'] == 'draft' and record['acceptance'] is None
    assert record['events'] == [] and 'execution' not in record
    assert envelope['submission']['accepted'] is False
    assert envelope['submission']['permissions'] == {'external': False, 'provider': False}
    return record


@pytest.mark.parametrize('config_kind', ['default', 'absolute'])
def test_review_missing_registry_init_then_original_intake(lane, config_kind):
    project, task, run = lane
    config = 'participants.json' if config_kind == 'default' else project / 'participants.json'
    argv = review(project, task, config=config)
    code, refused = run(argv)
    assert (code, refused['error']['type']) == (2, 'RegistryMissing')
    assert not task.exists() and not (project / 'participants.json').exists()
    before = json.dumps(refused, sort_keys=True)
    registry = init_continuation(run, refused, project)
    record = draft_review(run, argv, task)
    assert record['request']['registry'] == registry
    assert record['request']['config']['path'] == str(project / 'participants.json')
    assert json.dumps(refused, sort_keys=True) == before


def test_review_other_working_directory_needs_manual_config_selection(lane, monkeypatch):
    project, task, run = lane
    caller = project.parent / 'caller'
    caller.mkdir()
    monkeypatch.chdir(caller)
    argv = review(project, task)
    code, refused = run(argv)
    assert code == 2 and refused['error']['type'] == 'RegistryMissing'
    assert str(caller / 'participants.json') in refused['error']['detail']
    init_continuation(run, refused, project)
    code, repeated = run(argv)
    assert code == 2 and repeated['error'] == refused['error']
    assert not task.exists() and not (caller / 'participants.json').exists()
    # Manual branch explicitly offered by the guidance; init did not fix cwd.
    draft_review(run, review(project, task, config=project / 'participants.json'), task)


def test_plan_missing_config_init_still_requires_manual_config_argument(lane):
    project, task, run = lane
    request = project / 'request.json'
    request.write_text(json.dumps({'intent': {'goal': 'Add a subtract function', 'context': [],
        'scope': ['calc.py'], 'constraints': [], 'acceptance': ['Subtract returns the difference'],
        'questions': []}}), encoding='utf-8')
    argv = ['plan', '--project', str(project), '--task-dir', str(task), '--request', str(request)]
    code, refused = run(argv)
    assert code == 2 and 'requires --project and --config' in refused['error']['detail']
    assert not task.exists()
    init_continuation(run, refused, project)
    code, repeated = run(argv)
    assert code == 2 and repeated['error'] == refused['error']
    assert not task.exists()
    code, draft = run([*argv, '--config', str(project / 'participants.json')])
    assert (code, draft['status']) == (0, 'draft'), draft
    record = json.loads((task / 'record.json').read_text(encoding='utf-8'))
    assert record['status'] == 'draft' and record['acceptance'] is None
    assert record['request']['intent']['goal'] == 'Add a subtract function'
    assert 'planning' not in record and 'build' not in record


@pytest.mark.parametrize('config_kind', ['relative', 'absolute'])
def test_plan_explicit_missing_registry_is_manual_inspection(lane, config_kind):
    project, task, run = lane
    request = project / 'request.json'
    request.write_text(json.dumps({'intent': {'goal': 'Add a subtract function', 'context': [],
        'scope': ['calc.py'], 'constraints': [], 'acceptance': ['Subtract returns the difference'],
        'questions': []}}), encoding='utf-8')
    config = 'participants.json' if config_kind == 'relative' else str(project / 'participants.json')
    argv = ['plan', '--project', str(project), '--task-dir', str(task),
            '--request', str(request), '--config', config]
    code, refused = run(argv)
    assert (code, refused['status']) == (2, 'failed')
    assert 'Not a regular input file' in refused['error']['detail']
    assert refused['next_action'] == ('Inspect the error and any saved journal before choosing a valid action. '
                                     'Do not blindly retry uncertain operations.')
    assert not task.exists() and not (project / 'participants.json').exists()
    # No runnable next action was supplied. This is an independently authored
    # manual correction, not proof that the generic prose gives that recipe.
    code, created = run(['init', '--project', str(project)])
    assert (code, created['status'], created['profile']) == (0, 'created', 'demo')
    code, draft = run(argv)
    assert (code, draft['status']) == (0, 'draft'), draft
    record = json.loads((task / 'record.json').read_text(encoding='utf-8'))
    assert record['request']['config']['path'] == str(project / 'participants.json')
    assert record['acceptance'] is None and 'planning' not in record


def test_review_custom_missing_registry_needs_manual_config_selection(lane):
    project, task, run = lane
    missing = project / 'custom.json'
    argv = review(project, task, config=missing)
    code, refused = run(argv)
    assert code == 2 and refused['error']['type'] == 'RegistryMissing'
    init_continuation(run, refused, project)
    code, repeated = run(argv)
    assert code == 2 and repeated['error'] == refused['error']
    assert not missing.exists() and not task.exists()
    draft_review(run, review(project, task, config=project / 'participants.json'), task)


@pytest.fixture
def evidence_lane(lane):
    project, task, run = lane
    code, created = run(['init', '--project', str(project)])
    assert (code, created['status']) == (0, 'created')
    docs = project / 'docs'
    docs.mkdir()
    (docs / 'guide.md').write_text('# Guide\n\nThe answer is 42.\n', encoding='utf-8')
    return lane


@pytest.mark.parametrize('case', ['relative-document', 'absolute-document', 'outside-document',
                                 'relative-context', 'missing-corpus', 'task-inside-corpus'])
def test_manual_path_correction_reaches_draft_with_bound_evidence(evidence_lane, case):
    project, task, run = evidence_lane
    if case == 'relative-document':
        bad, good = {'document': 'guide.md'}, {'document': 'docs/guide.md'}
        detail = f"document 'guide.md' resolves against --project {project} to {project / 'guide.md'}"
    elif case == 'absolute-document':
        absent = project / 'absent.md'
        bad, good = {'document': absent}, {'document': project / 'docs/guide.md'}
        detail = f"document {str(absent)!r} is absolute to {absent}"
    elif case == 'outside-document':
        bad, good = {'document': '../guide.md'}, {'document': 'docs/guide.md'}
        detail = 'document must be inside the project and outside task state'
    elif case == 'relative-context':
        context = project / 'docs/context.json'
        context.write_text(json.dumps({'schema_version': 1, 'project_root': str(project)}), encoding='utf-8')
        bad, good = {'context': 'context.json'}, {'context': 'docs/context.json'}
        detail = f"context 'context.json' resolves against --project {project} to {project / 'context.json'}"
    elif case == 'missing-corpus':
        bad, good = {'corpus': 'missing'}, {'corpus': 'docs'}
        detail = f"corpus 'missing' resolves against --project {project} to {project / 'missing'}"
    else:
        bad, good = {'corpus': '.'}, {'corpus': '.'}
        task = project / 'task'
        detail = 'Corpus would ingest task state; choose --task-dir outside the corpus'
    code, refused = run(review(project, task, **bad))
    assert code == 2 and detail in refused['error']['detail'], refused
    assert refused['next_action'] == INSPECT  # Manual/prose, no runnable argv.
    assert not task.exists()  # Conditional status advice does not apply.
    if case == 'task-inside-corpus':
        task = project.parent / 'corrected-task'
    record = draft_review(run, review(project, task, **good), task)
    answers, evidence = record['request']['answers'], record['request']['evidence']
    for name, value in good.items():
        assert answers[name] == str(value)
        resolved = (project / value).resolve()
        if name == 'corpus':
            assert evidence['retrieval']['root'] == str(resolved)
        else:
            assert evidence[name] == {'path': str(resolved),
                                     'sha256': hashlib.sha256(resolved.read_bytes()).hexdigest()}


@pytest.mark.parametrize('case', ['absent', 'empty-directory', 'invalid-record'])
def test_failed_status_is_manual_inspection_and_preserves_original_state(lane, case):
    project, task, run = lane
    if case != 'absent':
        task.mkdir()
    if case == 'invalid-record':
        (task / 'record.json').write_text('not json\n', encoding='utf-8')
    before = {p.name: p.read_bytes() for p in task.iterdir()} if task.exists() else None
    code, refused = run(['status', str(task)])
    assert (code, refused['status']) == (2, 'failed')
    assert refused['next_action'] == f'Check that {task} is a Harness task directory holding its record.json'
    # This is a manual instruction. Never manufacture a record to turn it green.
    if case == 'absent':
        assert not task.exists()
    else:
        assert task.is_dir()
        assert {p.name: p.read_bytes() for p in task.iterdir()} == before
        if case == 'empty-directory':
            assert not (task / 'record.json').exists()
        else:
            with pytest.raises(json.JSONDecodeError):
                json.loads((task / 'record.json').read_text(encoding='utf-8'))


def test_manual_status_selection_of_real_draft_is_read_only(evidence_lane):
    project, task, run = evidence_lane
    draft_review(run, review(project, task, document='docs/guide.md'), task)
    code, refused = run(['status', str(task.parent / 'wrong-task')])
    assert (code, refused['status']) == (2, 'failed')
    assert 'holding its record.json' in refused['next_action']
    before = {p.name: p.read_bytes() for p in task.iterdir() if p.is_file()}
    code, inspected = run(['status', str(task)])
    assert (code, inspected['status'], inspected['task_profile']) == (0, 'draft', 'assessment-intake-v1')
    assert inspected['record_path'] == str(task / 'record.json')
    assert inspected['request']['answers']['document'] == 'docs/guide.md'
    assert inspected['events'] == [] and 'execution' not in inspected
    assert {p.name: p.read_bytes() for p in task.iterdir() if p.is_file()} == before
