"""Native Google decoding and supervision without provider inference."""
# qualify: platform

import copy
import json
from pathlib import Path
import sys
from threading import Event

import pytest

from attune_harness.antigravity import AntigravityExchange, decode
from attune_harness.native import NativeError

MODEL = 'gemini-3.1-pro-high'


def stream():
    return [
        {'event': 'init', 'conversation_id': 'session', 'init': {'model': MODEL, 'permission_mode': 'request-review'}},
        {'event': 'step_update', 'step_update': {'conversation_id': 'session', 'step_type': 'tool', 'state': 'ACTIVE', 'step_index': 2,
         'tool_name': 'finish', 'tool_info': {'name': 'finish', 'parameters': {'summary': 'Observed'}}}},
        {'event': 'step_update', 'step_update': {'conversation_id': 'session', 'step_type': 'finish', 'state': 'DONE', 'step_index': 2}},
        {'event': 'result', 'result': {'status': 'SUCCESS', 'conversation_id': 'session',
         'structured_output': {'verdict': 'uncertain', 'summary': 'Observed', 'evidence': []},
         'usage': {'input_tokens': 5, 'output_tokens': 3}}}]


def encoded(events):
    return '\n'.join(json.dumps(event) for event in events)


def test_completion_and_usage_are_retained():
    text, identity, usage = decode(encoded(stream()), MODEL)
    assert json.loads(text)['summary'] == 'Observed'
    assert identity.reported_models == (MODEL,) and identity.session_id == 'session'
    assert usage == {'input_tokens': 5, 'output_tokens': 3}


@pytest.mark.parametrize('mutation', ['model', 'permission', 'session', 'failure', 'partial', 'repeated_init',
                                    'repeated_result', 'external_tool', 'subagent', 'finish_index',
                                    'finish_start', 'finish_done', 'extra_fields', 'duplicate_key',
                                    'step_session', 'missing_step_session', 'finish_session', 'event_session'])
def test_malformed_or_uncertain_provider_output_refuses(mutation):
    events = copy.deepcopy(stream())
    if mutation in ('model', 'permission'):
        events[0]['init']['model' if mutation == 'model' else 'permission_mode'] = 'other'
    elif mutation == 'session':
        events[-1]['result']['conversation_id'] = 'other'
    elif mutation == 'step_session':
        events[1]['step_update']['conversation_id'] = 'other'
    elif mutation == 'missing_step_session':
        events[1]['step_update'].pop('conversation_id')
    elif mutation == 'finish_session':
        events[2]['step_update']['conversation_id'] = 'other'
    elif mutation == 'event_session':
        events[1]['conversation_id'] = 'other'
    elif mutation == 'failure':
        events[-1]['result']['status'] = 'FAILED'
    elif mutation == 'partial':
        events.pop()
    elif mutation == 'repeated_init':
        events.insert(1, events[0])
    elif mutation == 'repeated_result':
        events.append(events[-1])
    elif mutation == 'external_tool':
        events[1]['step_update']['tool_name'] = 'run_command'
    elif mutation == 'subagent':
        events[1]['step_update']['subagent_info'] = {}
    elif mutation == 'finish_index':
        events[2]['step_update']['step_index'] = True
    elif mutation == 'finish_start':
        events.pop(1)
    elif mutation == 'finish_done':
        events.pop(2)
    elif mutation == 'extra_fields':
        events[-1]['result']['structured_output']['authority'] = True
    raw = encoded(events)
    if mutation == 'duplicate_key':
        raw = raw.replace('"event": "init"', '"event": "init", "event": "init"', 1)
    with pytest.raises(ValueError):
        decode(raw, MODEL)


def test_real_process_uses_empty_cwd_explicit_effort_and_single_use(tmp_path):
    binary = tmp_path / ('agy-fixture.cmd' if sys.platform == 'win32' else 'agy-fixture')
    # An injected argument prefix keeps this a portable real subprocess fixture.
    script = tmp_path / 'fixture.py'
    output = encoded(stream())
    script.write_text('import pathlib,sys\n'
                      'assert not list(pathlib.Path.cwd().iterdir())\n'
                      'assert "--disable-slash-commands" in sys.argv\n'
                      'assert sys.argv[sys.argv.index("--effort")+1]=="high"\n'
                      'assert sys.argv[sys.argv.index("--print-timeout")+1]=="3s"\n'
                      f'print({output!r})\n', encoding='utf-8')
    from attune_harness.process import invoke
    seen = []
    def runner(argv, prompt, **kwargs):
        seen.append(argv)
        return invoke((sys.executable, str(script), *argv[1:]), prompt, **kwargs)
    exchange = AntigravityExchange(model=MODEL, effort='high', timeout=3, executable=str(binary), runner=runner)
    raw = json.dumps({'version': 1, 'attempt': {'accepted': 'offline fixture'}})
    assert json.loads(json.loads(exchange(raw))['text'])['verdict'] == 'uncertain'
    assert exchange.last_process.returncode == 0 and exchange.identity.reported_models == (MODEL,)
    with pytest.raises(NativeError, match='already dispatched'):
        exchange(raw)
    assert len(seen) == 1


def test_pre_cancel_never_launches_and_does_not_claim_no_external_effects(tmp_path):
    cancel = Event()
    cancel.set()
    exchange = AntigravityExchange(model=MODEL, effort='high', cancel=cancel, executable='does-not-exist')
    with pytest.raises(NativeError) as caught:
        exchange(json.dumps({'version': 1}))
    assert caught.value.failure == 'cancelled_before_start'
    assert exchange.last_process.returncode is None


def test_shared_owner_requires_native_authority_and_replays_google_without_new_process(tmp_path, monkeypatch):
    from attune_harness import consultation as c
    from attune_harness.process import invoke

    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text('x=1\n')
    script = tmp_path / 'fixture.py'
    script.write_text(f'print({encoded(stream())!r})\n', encoding='utf-8')
    seen = []
    def factory(**kwargs):
        def runner(argv, prompt, **options):
            seen.append(argv)
            return invoke((sys.executable, str(script), *argv[1:]), prompt, **options)
        return AntigravityExchange(**kwargs, runner=runner)
    monkeypatch.setattr(c, 'AntigravityExchange', factory)
    cfg = {'schema_version': 1, 'question': 'Inspect', 'author': {'provider': 'codex', 'model': 'gpt-6'},
           'participants': {'google': {'adapter': 'antigravity', 'identity': {'provider': 'google-antigravity', 'model': MODEL},
                                      'timeout': 3, 'effort': 'high'}}, 'rounds': 1}
    directory = tmp_path / 'run'
    prepared = c.prepare('source-review', root, ['x.py'], cfg, directory)
    with pytest.raises(ValueError, match='native authority'):
        c.run(directory, prepared['contract_digest'], allow_external=True)
    assert seen == []
    paused = c.run(directory, prepared['contract_digest'], allow_external=True, allow_native=True, max_operations=1)
    assert paused['status'] == 'paused'
    assert paused['answers'][0]['identity']['reported']['reported_models'] == (MODEL,)
    assert paused['answers'][0]['provider_usage'] == {'input_tokens': 5, 'output_tokens': 3}
    assert c.run(directory, prepared['contract_digest'], allow_external=True, allow_native=True)['status'] == 'completed'
    assert len(seen) == 1


@pytest.mark.parametrize('change', ['missing_effort', 'bad_effort', 'bad_provider'])
def test_google_configuration_refuses_before_prepare(change):
    from attune_harness import consultation as c
    cfg = {'schema_version': 1, 'question': 'Inspect', 'author': {'provider': 'codex', 'model': 'gpt-6'},
           'participants': {'google': {'adapter': 'antigravity', 'identity': {'provider': 'google-antigravity', 'model': MODEL},
                                      'timeout': 3, 'effort': 'high'}}, 'rounds': 1}
    seat = cfg['participants']['google']
    if change == 'missing_effort': seat.pop('effort')
    if change == 'bad_effort': seat['effort'] = 'highest'
    if change == 'bad_provider': seat['identity']['provider'] = 'claude'
    with pytest.raises(ValueError):
        c.configuration(cfg, 'source-review')
