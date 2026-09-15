"""Behavioral checks for explicit native model/effort selection; no model calls."""
import json
from pathlib import Path

import pytest

from test_review import case, change, change_config
from attune_harness.cli import main
from attune_harness.native import NativeExchange
from attune_harness.process import ProcessResult
from attune_harness.recovery import resume_review
from attune_harness.review import review
from attune_harness.review_contract import accept_request, load_registry
from attune_harness.review_participants import ReviewExchange

ROOT = Path(__file__).resolve().parents[1]


def as_astra(data):
    for item in data['participants'].values():
        item.update(adapter='codex', model='gpt-6-astra', reasoning_effort='xhigh', timeout=300)


def test_workspace_profile_selects_astra_for_both_roles():
    registry = load_registry(ROOT/'participants.json')
    assert set(registry['participants']) == {'astra-lead', 'astra-reviewer'}
    assert all(c['adapter'] == 'codex' and c['model'] == 'gpt-6-astra'
               and c['reasoning_effort'] == 'xhigh' for c in registry['participants'].values())


def test_accepted_journey_dispatches_model_and_effort_and_records_them(case, monkeypatch):
    from attune_harness import review_participants
    change_config(case, as_astra)
    calls = []
    def runner(argv, prompt, **kwargs):
        calls.append(argv)
        assert argv[argv.index('--model') + 1] == 'gpt-6-astra'
        assert argv[argv.index('-c') + 1] == 'model_reasoning_effort="xhigh"'
        assert argv[argv.index('--sandbox') + 1] == 'read-only'
        assert '--ephemeral' in argv
        request = json.loads(prompt.split('\n', 1)[1])['attempt']['task']['objective']
        action = ReviewExchange({'adapter': 'deterministic'}, kwargs['cwd'])(request)
        raw = '\n'.join(json.dumps(e) for e in [
            {'type': 'thread.started', 'thread_id': 'fixture-session'}, {'type': 'turn.started'},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps({'text': action})}},
            {'type': 'turn.completed', 'usage': {}},
        ])
        return ProcessResult(argv, 0, raw, '')
    monkeypatch.setattr(review_participants, 'NativeExchange',
                        lambda name, **kwargs: NativeExchange(name, **kwargs, runner=runner))
    result = review(*case, allow_external=True)
    assert result['status'] == 'completed', result.get('error')
    assert len(calls) == 6
    for role in ('lead', 'reviewer'):
        identity = result['participants'][role]['last_identity']
        assert identity['requested_model'] == 'gpt-6-astra'
        assert identity['requested_reasoning_effort'] == 'xhigh'
        assert 'model_reasoning_effort="xhigh"' in identity['dispatch_argv']
        assert identity['reported']['reported_models'] == ()  # No server identity invented.


@pytest.mark.parametrize('value', ['', 'extra high', 'XHIGH', 'xhigh;echo bad', None, True, [], {}])
def test_invalid_effort_registry_rejected_before_execution(case, value):
    change_config(case, as_astra)
    change(case[1], lambda d: d['participants']['alpha'].update(reasoning_effort=value))
    with pytest.raises(ValueError, match='reasoning_effort'):
        load_registry(case[1])


@pytest.mark.parametrize('provider', ['claude', 'command', 'deterministic'])
def test_effort_is_not_silently_ignored_by_other_adapters(case, provider):
    def update(data):
        item = data['participants']['alpha']
        item.update(adapter=provider, reasoning_effort='xhigh')
        if provider == 'claude': item.update(model='chosen', timeout=2)
        if provider == 'command': item.update(command=['never-run'], timeout=2)
    change(case[1], update)
    with pytest.raises(ValueError, match='Expected fields'):
        load_registry(case[1])


@pytest.mark.parametrize('provider,effort', [('claude', 'xhigh'), ('codex', 'bad'), ('codex', True)])
def test_direct_native_constructor_rejects_invalid_effort(tmp_path, provider, effort):
    with pytest.raises(ValueError):
        NativeExchange(provider, cwd=tmp_path, reasoning_effort=effort,
                       runner=lambda *_a, **_k: pytest.fail('dispatched'))


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_omitted_effort_preserves_existing_native_command(tmp_path, provider):
    calls = []
    def runner(argv, _prompt, **_kwargs):
        calls.append(argv)
        return ProcessResult(argv, 1, '', 'fixture failure', 'nonzero_exit')
    exchange = NativeExchange(provider, cwd=tmp_path, model='chosen', runner=runner)
    with pytest.raises(RuntimeError):
        exchange('{"version":1}')
    assert len(calls) == 1
    assert not any('model_reasoning_effort' in arg for arg in calls[0])


def test_effort_change_invalidates_accepted_form(case):
    change_config(case, as_astra)
    change(case[1], lambda d: d['participants']['alpha'].update(reasoning_effort='high'))
    with pytest.raises(ValueError, match='Stale form revision'):
        accept_request(case[0], load_registry(case[1]))


def test_effort_change_blocks_paused_continuation(case):
    change_config(case, as_astra)
    factory = lambda _config, cwd: ReviewExchange({'adapter': 'deterministic'}, cwd)
    paused = review(*case, allow_external=True, max_operations=3, exchange_factory=factory)
    assert paused['status'] == 'paused'
    before = (case[2]/'record.json').read_bytes()
    change_config(case, lambda d: d['participants']['alpha'].update(reasoning_effort='high'))
    with pytest.raises(ValueError):
        resume_review(case[2], case[0], case[1], paused['checkpoint_digest'], allow_external=True,
                      exchange_factory=lambda *_: pytest.fail('changed effort dispatched'))
    assert (case[2]/'record.json').read_bytes() == before


def test_new_review_cli_uses_workspace_profile_when_config_omitted(case, monkeypatch, capsys):
    monkeypatch.chdir(case[1].parent)
    Path('participants.json').write_bytes(case[1].read_bytes())
    assert main(['review-form']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'ready'
    assert main(['review', str(case[0]), '--run-dir', str(case[2])]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'completed'


def test_explicit_config_overrides_workspace_default(case, monkeypatch, capsys):
    monkeypatch.chdir(case[1].parent)
    Path('participants.json').write_text('invalid default')
    assert main(['review-form', '--config', str(case[1])]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'ready'
    assert main(['review', str(case[0]), '--config', str(case[1]), '--run-dir', str(case[2])]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'completed'
