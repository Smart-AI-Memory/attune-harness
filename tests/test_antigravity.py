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


def test_real_process_uses_empty_cwd_explicit_effort_and_single_use(tmp_path, record_property):
    binary = tmp_path / ('agy-fixture.cmd' if sys.platform == 'win32' else 'agy-fixture')
    # An injected argument prefix keeps this a portable real subprocess fixture.
    script = tmp_path / 'fixture.py'
    output = encoded(stream())
    script.write_text('import json,pathlib,sys\n'
                      'assert not list(pathlib.Path.cwd().iterdir())\n'
                      'assert "--disable-slash-commands" in sys.argv\n'
                      'assert sys.argv[sys.argv.index("--effort")+1]=="high"\n'
                      'assert sys.argv[sys.argv.index("--print-timeout")+1]=="3s"\n'
                      'assert "--print" not in sys.argv\n'
                      'assert sys.argv[sys.argv.index("--input-format")+1]=="stream-json"\n'
                      'assert sys.argv[sys.argv.index("--output-format")+1]=="stream-json"\n'
                      'event=json.loads(sys.stdin.readline())\n'
                      'assert event["event"]=="user" and set(event)=={"event","message"}\n'
                      'assert set(event["message"])=={"content"}\n'
                      'assert json.loads(event["message"]["content"].split("\\n",1)[1])=='
                      '{"version":1,"attempt":{"accepted":"offline fixture"}}\n'
                      'assert sys.stdin.read()==""\n'
                      f'print({output!r})\n', encoding='utf-8')
    from attune_harness.process import invoke
    seen = []
    def runner(argv, prompt, **kwargs):
        from attune_harness.process import ProcessError
        seen.append(argv)
        try:
            result = invoke((sys.executable, str(script), *argv[1:]), prompt, **kwargs)
        except ProcessError as error:
            result = error.result
            record_property('antigravity_cwd_before_adapter_cleanup', str(kwargs['cwd']))
            record_property('antigravity_runner_observation', json.dumps({
                'returncode': result.returncode, 'failure': result.failure,
                'stdout_bytes': len(result.stdout.encode('utf-8')),
                'stderr_bytes': len(result.stderr.encode('utf-8')),
                'diagnostics': error.diagnostics, 'stop_confirmed': error.process_stopped}))
            raise
        record_property('antigravity_runner_observation', json.dumps({
            'returncode': result.returncode, 'failure': result.failure,
            'stdout_bytes': len(result.stdout.encode('utf-8')),
            'stderr_bytes': len(result.stderr.encode('utf-8'))}))
        record_property('antigravity_cwd_before_adapter_cleanup', str(kwargs['cwd']))
        return result
    exchange = AntigravityExchange(model=MODEL, effort='high', timeout=3, executable=str(binary), runner=runner)
    raw = json.dumps({'version': 1, 'attempt': {'accepted': 'offline fixture'}})
    assert json.loads(json.loads(exchange(raw))['text'])['verdict'] == 'uncertain'
    assert exchange.last_process.returncode == 0 and exchange.identity.reported_models == (MODEL,)
    with pytest.raises(NativeError, match='already dispatched'):
        exchange(raw)
    assert len(seen) == 1


@pytest.mark.parametrize('source', ['x' * 131072, '"' * 65536, '\u00e9' * 32768],
                         ids=['ascii-exact-bound', 'quote-expansion', 'unicode-expansion'])
def test_accepted_large_roundtable_source_reaches_stdin_intact(tmp_path, monkeypatch, source):
    from attune_harness import consultation as c
    from attune_harness.process import invoke

    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text(source, encoding='utf-8')
    script = tmp_path / 'fixture.py'
    script.write_text('import json,pathlib,sys\n'
                      'assert "--print" not in sys.argv\n'
                      'assert sys.argv[sys.argv.index("--input-format")+1]=="stream-json"\n'
                      'assert sys.argv[sys.argv.index("--output-format")+1]=="stream-json"\n'
                      'line=sys.stdin.readline()\n'
                      'assert line.endswith("\\n") and sys.stdin.read()==""\n'
                      'event=json.loads(line)\n'
                      'assert set(event)=={"event","message"} and event["event"]=="user"\n'
                      'assert set(event["message"])=={"content"}\n'
                      'request=json.loads(event["message"]["content"].split("\\n",1)[1])\n'
                      'assert request==json.loads(pathlib.Path(sys.argv[-1]).read_text())\n'
                      f'events=json.loads({json.dumps(stream())!r})\n'
                      'events[0]["init"]["model"]=sys.argv[sys.argv.index("--model")+1]\n'
                      'for output in events: print(json.dumps(output))\n', encoding='utf-8')
    seen = []
    def factory(**kwargs):
        def runner(argv, stdin, **options):
            # The child must read the exact request handed to process supervision.
            request = json.loads(json.loads(stdin)['message']['content'].split('\n', 1)[1])
            seen.append(request)
            assert max(len(arg.encode('utf-8')) for arg in argv) < 4096
            import hashlib
            expected = tmp_path / (hashlib.sha256(stdin.encode('utf-8')).hexdigest() + '.json')
            expected.write_text(json.dumps(request), encoding='utf-8')
            return invoke((sys.executable, str(script), *argv[1:], str(expected)), stdin, **options)
        return AntigravityExchange(**kwargs, runner=runner)
    monkeypatch.setattr(c, 'AntigravityExchange', factory)
    seat = {'adapter': 'antigravity', 'identity': {'provider': 'google-antigravity', 'model': MODEL},
            'timeout': 3, 'effort': 'high'}
    cfg = {'schema_version': 1, 'question': 'Inspect', 'author': {'provider': 'codex', 'model': 'gpt-6'},
           'participants': {'first': seat, 'second': {**seat, 'identity': {
               'provider': 'google-antigravity', 'model': MODEL + '-offline-fixture'}}}, 'rounds': 2}
    directory = tmp_path / 'run'
    prepared = c.prepare('roundtable', root, ['x.py'], cfg, directory)
    (root / 'x.py').write_text('changed after prepare', encoding='utf-8')
    result = c.run(directory, prepared['contract_digest'], allow_external=True, allow_native=True)
    assert result['status'] == 'completed', result.get('answers')
    assert len(seen) == 4
    turns = [json.loads(request['attempt']['task']['objective']) for request in seen]
    assert [len(turn['previous_rounds']) for turn in turns] == [0, 0, 2, 2]
    assert all(turn['snapshot']['files']['x.py']['text'] == source for turn in turns)
    assert all(turn['snapshot'] == prepared['contract']['snapshot'] for turn in turns)
    assert all(turn['contract_digest'] == prepared['contract_digest'] for turn in turns)
    assert turns[2]['previous_rounds'] == turns[3]['previous_rounds']
    with pytest.raises(ValueError, match='Terminal'):
        c.run(directory, prepared['contract_digest'], allow_external=True, allow_native=True)
    assert len(seen) == 4


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


@pytest.mark.parametrize('failure', [None, 'timeout_effects_unknown',
                                     'cancelled_effects_unknown', 'output_limit'])
@pytest.mark.parametrize('cleanup_kind', ['permission', 'recursion'])
def test_adapter_cleanup_preserves_original_result_and_refuses_success(
        tmp_path, monkeypatch, failure, cleanup_kind):
    import attune_harness.antigravity as adapter
    from attune_harness.process import ProcessResult
    from types import SimpleNamespace

    result = ProcessResult(('owned-fixture',), 0 if failure is None else 1,
                           encoded(stream()), 'original diagnostic', failure)
    cleanup_error = (PermissionError(13, 'private cleanup path') if cleanup_kind == 'permission'
                     else RecursionError('synthetic retained cleanup cascade'))
    calls = []

    class Temporary:
        name = str(tmp_path)

        def cleanup(self):
            assert exchange.last_process is result
            calls.append('cleanup')
            raise cleanup_error

    def runner(*args, **kwargs):
        calls.append('dispatch')
        return result

    monkeypatch.setattr(adapter, 'tempfile', SimpleNamespace(TemporaryDirectory=lambda **kwargs: Temporary()))
    monkeypatch.setattr(adapter, 'decode', lambda *args: pytest.fail('decoded success after failed cleanup'))
    exchange = AntigravityExchange(model=MODEL, effort='high', timeout=3, runner=runner)
    with pytest.raises(NativeError) as caught:
        exchange('{"version":1}')
    error = caught.value
    assert error.failure == (failure or 'cleanup_failed_effects_unknown')
    assert error.process_stopped is True
    assert error.process_result is result and exchange.last_process is result
    assert error.original_error is cleanup_error and error.__cause__ is cleanup_error
    assert error.diagnostics[0].startswith('adapter_cleanup:' + type(cleanup_error).__name__)
    assert 'private' not in str(error) and len(error.diagnostics) == 1
    assert exchange.identity is None and exchange.usage is None
    with pytest.raises(NativeError, match='already dispatched'):
        exchange('{"version":1}')
    assert calls == ['dispatch', 'cleanup']


@pytest.mark.parametrize('cleanup_fails', [False, True])
def test_adapter_retains_unconfirmed_supervision_outcome(tmp_path, monkeypatch, cleanup_fails):
    import attune_harness.antigravity as adapter
    from attune_harness.process import ProcessError, ProcessResult
    from types import SimpleNamespace

    result = ProcessResult(('owned-fixture',), 0, 'bounded partial', '', 'timeout_effects_unknown')
    stop_error = OSError(5, 'synthetic job query refusal')
    execution_error = ProcessError(result, ('supervision:OSError:errno=5',),
                                   process_stopped=False, original_error=stop_error)
    calls = []

    class Temporary:
        name = str(tmp_path)

        def cleanup(self):
            assert exchange.last_process is result
            calls.append('cleanup')
            if cleanup_fails:
                raise PermissionError(13, 'synthetic cleanup refusal')

    def runner(*args, **kwargs):
        calls.append('dispatch')
        raise execution_error

    monkeypatch.setattr(adapter, 'tempfile', SimpleNamespace(TemporaryDirectory=lambda **kwargs: Temporary()))
    exchange = AntigravityExchange(model=MODEL, effort='high', timeout=3, runner=runner)
    with pytest.raises(NativeError) as caught:
        exchange('{"version":1}')
    error = caught.value
    assert error.failure == result.failure and error.process_stopped is False
    assert error.original_error is execution_error and error.process_result is result
    assert error.diagnostics[0] == 'supervision:OSError:errno=5'
    assert ('adapter_cleanup:PermissionError:errno=13' in error.diagnostics) == cleanup_fails
    assert exchange.last_process is result and calls == ['dispatch', 'cleanup']
    with pytest.raises(NativeError, match='already dispatched'):
        exchange('{"version":1}')
    assert calls == ['dispatch', 'cleanup']


@pytest.mark.parametrize('kind', ['runner_error', 'interrupt'])
@pytest.mark.parametrize('cleanup_fails', [False, True])
def test_runner_exception_type_survives_adapter_cleanup(tmp_path, monkeypatch, kind, cleanup_fails):
    import attune_harness.antigravity as adapter
    from types import SimpleNamespace

    original = RuntimeError('original runner error') if kind == 'runner_error' else KeyboardInterrupt('original interrupt')
    cleanup_error = PermissionError(13, 'synthetic cleanup refusal')
    calls = []

    class Temporary:
        name = str(tmp_path)

        def cleanup(self):
            calls.append('cleanup')
            if cleanup_fails:
                raise cleanup_error

    def runner(*args, **kwargs):
        calls.append('dispatch')
        raise original

    monkeypatch.setattr(adapter, 'tempfile', SimpleNamespace(TemporaryDirectory=lambda **kwargs: Temporary()))
    exchange = AntigravityExchange(model=MODEL, effort='high', timeout=3, runner=runner)
    with pytest.raises(type(original)) as caught:
        exchange('{"version":1}')
    assert caught.value is original and exchange.last_process is None
    if cleanup_fails:
        assert original.cleanup_diagnostics == ('adapter_cleanup:PermissionError:errno=13',)
        assert original.__cause__ is cleanup_error
    assert calls == ['dispatch', 'cleanup']
    with pytest.raises(NativeError, match='already dispatched'):
        exchange('{"version":1}')
    assert calls == ['dispatch', 'cleanup']
