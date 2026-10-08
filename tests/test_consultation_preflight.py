"""Offline preflight journeys never dispatch providers or configured wrappers."""
# qualify: platform

import copy
import json
import sys

import pytest

from attune_harness import consultation
from attune_harness import consultation_preflight as p
from attune_harness.cli import main
from attune_harness.process import ProcessResult


def config(*adapters):
    return {'schema_version': 1, 'question': 'Review the selected files',
            'author': {'provider': 'chair', 'model': 'chair-1'}, 'rounds': 1,
            'participants': {adapter: {
                'adapter': adapter,
                'identity': {'provider': 'google-antigravity' if adapter == 'antigravity' else adapter,
                             'model': 'explicit-' + adapter + '-1'},
                'timeout': 10,
                **({'effort': 'high'} if adapter == 'antigravity' else {}),
                **({'command': ['custom', '--paid-prompt']} if adapter == 'command' else {}),
            } for adapter in adapters}}


@pytest.fixture(autouse=True)
def no_dispatch(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('preflight crossed the model or run boundary')
    for name in ('prepare', 'load', 'run', 'dispatch', 'NativeExchange', 'AntigravityExchange'):
        monkeypatch.setattr(consultation, name, forbidden)


def stub(monkeypatch, auth=None, *, missing=(), failure=None):
    calls = []
    monkeypatch.setattr(p.shutil, 'which', lambda binary: None if binary in missing else '/bin/' + binary)
    def runner(argv, prompt, **kwargs):
        calls.append(argv)
        assert prompt == ''
        assert kwargs['timeout'] == 10 and kwargs['max_output_bytes'] == 8192
        adapter = argv[0].rsplit('/', 1)[-1]
        if argv[1:] == ('--version',):
            return ProcessResult(argv, 0, '1.2.3\n', '')
        assert argv[1:] in (('auth', 'status', '--json'), ('login', 'status'))
        body, code = auth[adapter] if auth else ('unrecognized', 0)
        return ProcessResult(argv, code, body, '', failure or ('nonzero_exit' if code else None))
    monkeypatch.setattr(p, 'invoke', runner)
    return calls


def test_expired_login_affects_only_its_seat(monkeypatch):
    calls = stub(monkeypatch, {'claude': ('{"loggedIn": false}', 1),
                               'codex': ('Logged in using ChatGPT', 0)})
    original = config('claude', 'codex')
    before = copy.deepcopy(original)
    reports = p.preflight(original)
    assert original == before
    assert reports['claude'] == {'state': 'not_signed_in', 'binary': '/bin/claude',
                                 'version': '1.2.3', 'fix': 'Run claude auth login, then rerun check.'}
    assert reports['codex']['state'] == 'unknown'
    assert 'model availability' in reports['codex']['fix']
    assert len(calls) == 4


@pytest.mark.parametrize('adapter', ['claude', 'codex', 'antigravity', 'command'])
def test_missing_binary_never_launches(monkeypatch, adapter):
    executable = {'antigravity': 'agy', 'command': 'custom'}.get(adapter, adapter)
    calls = stub(monkeypatch, missing=(executable,))
    report = p.preflight(config(adapter))[adapter]
    assert report['state'] == 'missing_binary'
    assert report['binary'] is None and report['version'] is None
    assert executable in report['fix'] and calls == []


@pytest.mark.parametrize('adapter', ['command', 'antigravity'])
def test_unverified_wrappers_and_antigravity_are_never_executed(monkeypatch, adapter):
    calls = stub(monkeypatch)
    report = p.preflight(config(adapter))[adapter]
    assert report['state'] == 'unknown' and report['version'] is None
    assert calls == []


@pytest.mark.parametrize('adapter,body,code,state', [
    ('claude', '{"loggedIn":true,"apiKey":"secret"}', 0, 'unknown'),
    ('claude', '{"loggedIn":false}', 0, 'not_signed_in'),
    ('claude', '{"loggedIn":true}', 1, 'unknown'),
    ('claude', '{"loggedIn":"false"}', 0, 'unknown'),
    ('claude', '{"loggedIn":false,"loggedIn":true}', 0, 'unknown'),
    ('claude', 'OAuth session expired and could not be refreshed', 1, 'unknown'),
    ('codex', 'Not logged in', 1, 'not_signed_in'),
    ('codex', 'Logged in using an API key - secret', 0, 'unknown'),
    ('codex', 'Logged in using ChatGPT', 1, 'unknown'),
    ('codex', 'please login: secret', 1, 'unknown'),
])
def test_recognized_auth_and_unknown_diagnostics(monkeypatch, adapter, body, code, state):
    stub(monkeypatch, {adapter: (body, code)})
    report = p.preflight(config(adapter))[adapter]
    assert report['state'] == state
    assert 'secret' not in json.dumps(report)
    assert set(report) == {'state', 'binary', 'version', 'fix'}


@pytest.mark.parametrize('failure', ['timeout_effects_unknown', 'output_limit', 'launch_failed'])
def test_failed_status_cannot_establish_auth(monkeypatch, failure):
    stub(monkeypatch, {'claude': ('{"loggedIn":false}', 1)}, failure=failure)
    assert p.preflight(config('claude'))['claude']['state'] == 'unknown'


@pytest.mark.parametrize('change', ['rounds', 'identity', 'timeout', 'alias', 'extra'])
def test_validation_happens_before_any_probe(monkeypatch, change):
    calls = stub(monkeypatch)
    value = config('claude', 'codex')
    if change == 'rounds':
        value['rounds'] = 3
    elif change == 'identity':
        value['participants']['codex']['identity'] = value['participants']['claude']['identity']
    elif change == 'timeout':
        value['participants']['claude']['timeout'] = 0
    elif change == 'alias':
        value['participants']['claude']['identity']['model'] = 'opus'
    else:
        value['unexpected'] = True
    with pytest.raises(ValueError):
        p.preflight(value)
    assert calls == []


@pytest.mark.parametrize('operation,adapters', [('source-review', ('claude',)),
                                               ('roundtable', ('claude', 'codex'))])
def test_cli_check_needs_no_run_directory(tmp_path, monkeypatch, capsys, operation, adapters):
    stub(monkeypatch, {'claude': ('{"loggedIn":false}', 1),
                      'codex': ('Logged in using ChatGPT', 0)})
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config(*adapters)))
    assert main([operation, 'check', '--config', str(path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'checked' and result['operation'] == operation
    assert result['authority'] == 'inspection_only' and result['model_calls'] == 0
    assert result['participants']['claude']['state'] == 'not_signed_in'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('state,exitcode', [('ready', 0), ('unknown', 0), ('missing_binary', 2),
                                          ('not_signed_in', 2)])
def test_cli_reports_adapter_states_without_consultation_status_assumptions(
        tmp_path, monkeypatch, capsys, state, exitcode):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config('claude')))
    monkeypatch.setattr(p, 'preflight', lambda config: {'claude': {
        'state': state, 'binary': None, 'version': None, 'fix': 'fixture'}})
    assert main(['source-review', 'check', '--config', str(path)]) == exitcode
    assert json.loads(capsys.readouterr().out)['participants']['claude']['state'] == state


def test_cli_validates_chosen_operation_and_refuses_without_probe(tmp_path, monkeypatch, capsys):
    calls = stub(monkeypatch)
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config('claude', 'codex')))
    assert main(['source-review', 'check', '--config', str(path)]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'refused'
    assert calls == []


def test_version_failure_does_not_hide_detected_missing_login(monkeypatch):
    stub(monkeypatch)
    def probe(binary, *args):
        if args == ('--version',):
            return ProcessResult((), 1, 'secret', '', 'nonzero_exit')
        return ProcessResult((), 1, '{"loggedIn":false}', '', 'nonzero_exit')
    monkeypatch.setattr(p, '_probe', probe)
    result = p.preflight(config('claude'))['claude']
    assert result['version'] is None and result['state'] == 'not_signed_in'


def test_real_process_supervision_with_offline_python_fixture(monkeypatch):
    # Exercise the production supervisor, with only a local Python process.
    monkeypatch.setattr(p.shutil, 'which', lambda executable: sys.executable)
    original = p.invoke
    seen = []
    def runner(argv, prompt, **kwargs):
        seen.append(argv[1:])
        output = '1.2.3' if argv[1:] == ('--version',) else '{"loggedIn":false}'
        return original((sys.executable, '-c', 'print(' + repr(output) + ')'), prompt, **kwargs)
    monkeypatch.setattr(p, 'invoke', runner)
    report = p.preflight(config('claude'))['claude']
    assert report['state'] == 'not_signed_in' and report['version'] == '1.2.3'
    assert seen == [('--version',), ('auth', 'status', '--json')]
