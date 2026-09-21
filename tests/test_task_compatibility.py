"""Frozen legacy behavior before unified task intake/runtime is introduced."""
import json
from pathlib import Path
import re
import runpy

import pytest

from attune_harness.cli import main
from attune_harness import review_participants, voyage_provider
from attune_harness.recovery import resume_review
from attune_harness.review import review
from attune_harness.review_contract import load_registry, review_form
from test_review import case, change


LEGACY_COMMANDS = {
    'review-form', 'review', 'inspect-review', 'resume-review', 'reconcile-review',
    'transfer-review', 'cancel-review', 'extension', 'code-config', 'index',
    'retrieval-task', 'triage-check', 'repair-economics', 'github-checks',
    'mcp-serve', 'mcp-inspect', 'verify', 'retrieve',
}


@pytest.fixture(autouse=True)
def no_live_providers(monkeypatch):
    def poison(*args, **kwargs):
        pytest.fail('A deterministic compatibility test attempted live dispatch')
    monkeypatch.setattr(review_participants, 'NativeExchange', poison)
    monkeypatch.setattr(voyage_provider, 'VoyageProvider', poison)


def test_all_legacy_names_remain_discoverable(capsys):
    with pytest.raises(SystemExit) as error:
        main(['--help'])
    assert error.value.code == 0
    output = capsys.readouterr()
    assert not output.err
    assert all(title in output.out for title in ('Task execution:', 'Task controls:', 'AI tools and integration:'))
    assert '--help-all' in output.out
    options = set(re.findall(r'^  ([a-z][a-z-]*)\s', output.out, re.MULTILINE))
    assert options == {'plan', 'build', 'review', 'fix', 'test', 'status', 'resume'}
    assert not any(name in output.out for name in LEGACY_COMMANDS - {'review'})

    with pytest.raises(SystemExit) as error:
        main(['--help-all'])
    assert error.value.code == 0
    output = capsys.readouterr()
    assert not output.err
    assert 'Compatibility commands (existing scripts):' in output.out
    options = set(re.findall(r'^  ([a-z][a-z-]*)\s', output.out, re.MULTILINE))
    assert LEGACY_COMMANDS <= options
    assert {'fix', 'status', 'resume', 'reconcile-task', 'transfer-task', 'cancel-task'} <= options


@pytest.mark.parametrize('command', sorted(LEGACY_COMMANDS))
def test_every_legacy_command_has_model_free_help(command, capsys):
    with pytest.raises(SystemExit) as error:
        main([command, '--help'])
    assert error.value.code == 0
    output = capsys.readouterr()
    assert f'attune-harness {command}' in output.out and not output.err


@pytest.mark.parametrize('content,query,document,retrieval,exit_code', [
    ('[Quartz retention policy](reference.md)', 'quartz retention policy', 'verified', 'retrieved', 0),
    ('[broken](missing.md)', 'quartz retention policy', 'refuted', 'retrieved', 1),
    ('No supported claims.', 'quartz retention policy', 'unknown', 'retrieved', 1),
    ('[Quartz retention policy](reference.md)', 'zzzznotfound', 'verified', 'no_results', 1),
])
def test_legacy_review_exit_distinguishes_completion_from_acceptance(
        case, capsys, content, query, document, retrieval, exit_code):
    (case[0].parent / 'project/guide.md').write_text(content, encoding='utf-8')
    change(case[0], lambda value: value['answers'].update(query=query))
    assert main(['review', str(case[0]), '--config', str(case[1]), '--run-dir', str(case[2])]) == exit_code
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == document
    assert result['retrieval_outcome'] == retrieval
    assert result['accepted']['submission']['accepted'] is True
    assert len(result['events']) == 13
    assert [event['kind'] for event in result['events']] == [
        'preflight_verification', 'initial_retrieval',
        'participant_turn', 'tool', 'participant_turn', 'tool', 'participant_turn',
        'participant_turn', 'tool', 'participant_turn', 'tool', 'participant_turn',
        'final_verification',
    ]
    assert all(event['phase'] == 'completed' for event in result['events'])
    assert all('No model judgment was performed.' in value['text']
               for value in result['participants'].values())


def test_legacy_form_is_unaccepted_and_registry_bound(case):
    registry = load_registry(case[1])
    rendered = review_form(registry)
    assert rendered['submission']['accepted'] is False
    assert list(rendered['submission']['answers']) == [
        'objective', 'query', 'document', 'context', 'corpus', 'lead', 'reviewer',
    ]
    assert all(value is None for value in rendered['submission']['answers'].values())
    registry['participants']['alpha']['max_turns'] = 4
    assert review_form(registry)['form_revision'] != rendered['form_revision']


def test_saved_completed_record_replays_without_new_dispatch(case):
    result = review(*case)
    original_bytes = (case[2] / 'record.json').read_bytes()

    def poison(*args, **kwargs):
        pytest.fail('Completed record attempted another participant invocation')

    replay = resume_review(case[2], case[0], case[1], result['checkpoint_digest'], exchange_factory=poison)
    assert replay == result
    assert (case[2] / 'record.json').read_bytes() == original_bytes


def test_paused_record_preserves_operation_identity_on_resume(case):
    paused = review(*case, max_operations=2)
    completed = resume_review(case[2], case[0], case[1], paused['checkpoint_digest'])
    assert paused['status'] == 'paused' and completed['status'] == 'completed'
    assert completed['events'][:2] == paused['events']
    assert completed['run_id'] == paused['run_id']
    assert completed['requirement_revision'] == paused['requirement_revision']
    assert completed['recovery']['assignments'] == paused['recovery']['assignments']


def test_baseline_poison_stops_both_live_boundaries(tmp_path):
    # Test the measurement safety boundary itself, not just its caller's choices.
    probe = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                              'experiments/task_execution/baseline.py'))
    for constructor in (lambda: review_participants.NativeExchange('codex', cwd=tmp_path),
                        lambda: voyage_provider.VoyageProvider()):
        with pytest.raises(probe['LiveDispatchForbidden']):
            with probe['offline']():
                constructor()


def test_baseline_never_overwrites_existing_evidence(tmp_path):
    probe = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                              'experiments/task_execution/baseline.py'))
    marker = tmp_path / 'retained.txt'
    marker.write_text('original evidence', encoding='utf-8')
    with pytest.raises(FileExistsError):
        probe['baseline'](tmp_path, samples=1, process_samples=1)
    assert list(tmp_path.iterdir()) == [marker]
    assert marker.read_text(encoding='utf-8') == 'original evidence'
