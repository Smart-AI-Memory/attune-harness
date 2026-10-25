"""Finite command grants at both real child boundaries; no provider calls."""
# qualify: platform

import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from threading import Event

import pytest

from attune_harness import command_environment as ce, consultation
from attune_harness.review_contract import digest, validate_registry
from attune_harness.review_participants import ReviewExchange, protect_command_scope


def configuration(*names):
    return {'adapter': 'command', 'command': [sys.executable], 'timeout': 5,
            'tools': [], 'max_turns': 1, 'max_tool_calls': 0,
            'environment': {'profile': ce.PROFILE, 'passthrough': list(names)}}


def parent(tmp_path, **values):
    return {'TMPDIR': str(tmp_path), 'TEMP': str(tmp_path), 'SystemRoot': r'C:\Windows', **values}


@pytest.fixture
def cwd(tmp_path):
    value = tmp_path / 'work'
    value.mkdir()
    return value


@pytest.mark.parametrize('policy', [None, {}, {'profile': 'unknown', 'passthrough': []},
    {'profile': ce.PROFILE, 'passthrough': '*'},
    {'profile': ce.PROFILE, 'passthrough': ['TOKEN', 'token']},
    {'profile': ce.PROFILE, 'passthrough': ['BAD=synthetic-secret']},
    {'profile': ce.PROFILE, 'passthrough': ['*']},
    {'profile': ce.PROFILE, 'passthrough': [], 'values': {'TOKEN': 'synthetic-secret'}},
    {'profile': ce.PROFILE, 'passthrough': ['A' * 129]},
    {'profile': ce.PROFILE, 'passthrough': [f'V{i}' for i in range(65)]},
], ids=['null', 'empty', 'profile', 'list', 'duplicate', 'invalid-name', 'wildcard', 'values', 'long-name', 'many'])
def test_policy_refusals_do_not_display_input(policy):
    with pytest.raises(ValueError) as error:
        ce.validate(policy)
    assert 'synthetic-secret' not in str(error.value)


def test_map_grants_only_named_values_and_cleans_up(tmp_path, cwd):
    cfg = configuration('ALLOW', 'EMPTY')
    source = parent(tmp_path, ALLOW='synthetic-allow', EMPTY='', DENY='synthetic-deny')
    before = copy.deepcopy(source)
    with ce.invocation(cfg, cwd=cwd, parent=source) as (environment, audit):
        assert environment['ALLOW'] == 'synthetic-allow' and environment['EMPTY'] == ''
        assert 'DENY' not in environment
        home = Path(environment['HOME'])
        scratch = Path(environment['TMPDIR'])
        assert home.is_dir() and scratch.is_dir() and not home.is_relative_to(cwd)
        assert audit == {'profile': ce.PROFILE, 'policy_digest': digest(cfg['environment']), 'keys': sorted(environment)}
        assert 'synthetic-' not in json.dumps(audit)
        assert source == before
    assert not home.exists() and not scratch.exists()


@pytest.mark.parametrize('values,reason', [({}, 'missing'), ({'ALLOW': 'canary\x00private'}, 'invalid')])
def test_missing_or_invalid_grant_refuses_before_scratch(tmp_path, cwd, values, reason):
    before = set(tmp_path.iterdir())
    with pytest.raises(ValueError, match=reason) as error:
        with ce.invocation(configuration('ALLOW'), cwd=cwd, parent=parent(tmp_path, **values)):
            pytest.fail('dispatched')
    assert 'canary' not in str(error.value) and set(tmp_path.iterdir()) == before


@pytest.mark.parametrize('location', ['cwd', 'source', 'state'])
def test_scratch_refuses_protected_roots_before_writing(tmp_path, cwd, location):
    protected = cwd if location == 'cwd' else tmp_path / location
    protected.mkdir(exist_ok=True)
    before = list(protected.iterdir())
    with pytest.raises(ValueError, match='outside the work scope'):
        with ce.invocation(configuration(), cwd=cwd, excluded_roots=(protected,),
                           parent=parent(protected)):
            pytest.fail('dispatched')
    assert list(protected.iterdir()) == before


def test_cached_tempfile_directory_cannot_redirect_scratch(tmp_path, cwd, monkeypatch):
    monkeypatch.setattr(tempfile, 'tempdir', str(cwd))
    with ce.invocation(configuration(), cwd=cwd, parent=parent(tmp_path)) as (environment, _):
        assert not Path(environment['HOME']).is_relative_to(cwd)
    assert list(cwd.iterdir()) == []


@pytest.mark.parametrize('nested', [False, True], ids=['root', 'descendant'])
def test_case_alias_cannot_put_scratch_inside_protected_scope(tmp_path, nested):
    protected = tmp_path / 'FrozenScope'
    protected.mkdir()
    alias = tmp_path / 'fROZENsCOPE'
    if not alias.exists() or not alias.samefile(protected):
        pytest.skip('Volume uses case-sensitive directory names')
    target = alias
    if nested:
        target = alias / 'nested'
        target.mkdir()
    before = sorted(str(path) for path in protected.rglob('*'))
    with pytest.raises(ValueError, match='outside the work scope'):
        with ce.invocation(configuration(), cwd=protected, parent=parent(target)):
            pytest.fail('dispatched')
    assert sorted(str(path) for path in protected.rglob('*')) == before


@pytest.mark.parametrize('executable', [r'C:python.exe', r'\python.exe', 'python.exe'])
def test_windows_executable_must_have_drive_and_root(tmp_path, cwd, executable):
    cfg = configuration()
    cfg['command'] = [executable]
    with pytest.raises(ValueError, match='absolute initial executable'):
        with ce.invocation(cfg, cwd=cwd, platform='nt', parent=parent(tmp_path)):
            pytest.fail('dispatched')


def test_windows_map_has_absolute_baseline_and_casefolded_grants(tmp_path, cwd):
    cfg = configuration('Path', 'token')
    cfg['command'] = [r'C:\Python\python.exe']
    source = {'systemroot': r'C:\Windows', 'temp': str(tmp_path), 'PATH': 'explicit-path', 'TOKEN': 'synthetic-token'}
    with ce.invocation(cfg, cwd=cwd, parent=source, platform='nt') as (environment, audit):
        assert environment['PATH'] == 'explicit-path' and 'Path' not in environment
        assert environment['token'] == 'synthetic-token'
        assert environment['SystemRoot'] == r'C:\Windows'
        assert environment['USERPROFILE'] == environment['HOME']
        assert len({k.casefold() for k in environment}) == len(environment)
        assert 'synthetic-token' not in json.dumps(audit)
    cfg['environment']['passthrough'] = []
    with ce.invocation(cfg, cwd=cwd, parent=source, platform='nt') as (environment, _):
        assert environment['PATH'] == r'C:\Windows\System32;C:\Windows'


@pytest.mark.parametrize('system_root', ['', r'Windows', r'\Windows', r'C:Windows', r'C:\Windows;.', 'C:\\Windows;'])
def test_windows_system_root_cannot_make_relative_path(tmp_path, cwd, system_root):
    cfg = configuration()
    cfg['command'] = [r'C:\Python\python.exe']
    before = list(tmp_path.iterdir())
    with pytest.raises(ValueError, match='absolute SystemRoot'):
        with ce.invocation(cfg, cwd=cwd, parent=parent(tmp_path, SystemRoot=system_root), platform='nt'):
            pytest.fail('dispatched')
    assert list(tmp_path.iterdir()) == before


def test_windows_selected_ambiguous_names_refuse(tmp_path, cwd):
    cfg = configuration('TOKEN')
    cfg['command'] = [r'C:\Python\python.exe']
    with pytest.raises(ValueError, match='ambiguous: TOKEN'):
        with ce.invocation(cfg, cwd=cwd, parent=parent(tmp_path, TOKEN='one', Token='two'), platform='nt'):
            pytest.fail('dispatched')


def test_dispatch_snapshot_and_independent_maps(tmp_path, cwd):
    source = parent(tmp_path, TOKEN='first')
    with ce.invocation(configuration('TOKEN'), cwd=cwd, parent=source) as (first, _):
        source['TOKEN'] = 'second'
        with ce.invocation(configuration('TOKEN'), cwd=cwd, parent=source) as (second, _):
            assert first['TOKEN'] == 'first' and second['TOKEN'] == 'second'
            assert first['HOME'] != second['HOME']
            second['TOKEN'] = 'changed-child-map'
            assert source['TOKEN'] == 'second'


PEER = '''import hashlib,json,os,sys
raw=sys.stdin.read();request=json.loads(raw)
observed=json.dumps({'allowed':os.environ.get('ATTUNE_TEST_ALLOW'),
 'denied':os.environ.get('ATTUNE_TEST_DENY'),'home':os.environ.get('HOME')})
if 'attempt' in request:
 answer={'verdict':'uncertain','summary':observed,'evidence':[]}
 response={'version':1,'request_digest':hashlib.sha256(raw.encode()).hexdigest(),'text':json.dumps(answer)}
else:
 response={'schema_version':1,'request_digest':request.get('request_digest','test'),'action':{'kind':'final','text':observed}}
print(json.dumps(response))
'''


@pytest.mark.parametrize('route', ['consultation', 'harness-review-v1', 'feature-planning-v1', 'feature-build-v1'])
@pytest.mark.parametrize('grant', [False, True], ids=['excluded', 'granted'])
def test_real_children_receive_only_named_canary(tmp_path, cwd, monkeypatch, route, grant):
    peer = tmp_path / 'peer.py'
    peer.write_text(PEER)
    monkeypatch.setenv('ATTUNE_TEST_ALLOW', 'synthetic-allow')
    monkeypatch.setenv('ATTUNE_TEST_DENY', 'synthetic-deny')
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    monkeypatch.setenv('TEMP', str(tmp_path))
    cfg = configuration(*(['ATTUNE_TEST_ALLOW'] if grant else []))
    cfg['command'] = [sys.executable, '-I', '-B', str(peer)]
    if route == 'consultation':
        cfg['identity'] = {'provider': 'synthetic', 'model': 'peer-1'}
        turn = {'attempt_id': 'probe', 'contract_digest': 'a'*64, 'participant': 'peer',
                'snapshot': {'root': str(cwd), 'files': {}}}
        result = consultation.dispatch(cfg, turn, cwd, Event())
        assert result['status'] == 'completed', result
        observed = json.loads(result['answer']['summary'])
        audit = result['identity']['environment']
    else:
        exchange = ReviewExchange(cfg, cwd, profile=route)
        role = 'planner' if route == 'feature-planning-v1' else 'worker'
        raw = exchange(json.dumps({'turn': {'operation_profile': route, 'role': role, 'tools': []}}))
        observed = json.loads(json.loads(raw)['action']['text'])
        audit = exchange.last_identity['environment']
    assert observed['allowed'] == ('synthetic-allow' if grant else None)
    assert observed['denied'] is None and not Path(observed['home']).exists()
    assert 'synthetic-' not in json.dumps(audit)


def test_registry_policy_is_command_only_and_changes_identity(tmp_path):
    cfg = configuration()
    registry = {'schema_version': 1, 'participants': {'a': cfg, 'b': copy.deepcopy(cfg)}}
    assert validate_registry(registry, tmp_path/'registry.json') is registry
    original = digest(registry)
    registry['participants']['a']['environment']['passthrough'].append('TOKEN')
    assert digest(registry) != original
    native = {'adapter': 'codex', 'model': 'synthetic-model', 'timeout': 5,
              'tools': [], 'max_turns': 1, 'max_tool_calls': 0, 'environment': cfg['environment']}
    with pytest.raises(ValueError, match='Expected fields'):
        validate_registry({'schema_version': 1, 'participants': {'a': native, 'b': cfg}}, tmp_path/'registry.json')


def test_protected_scope_keeps_custom_factory_contract(cwd):
    custom = lambda raw: raw
    assert protect_command_scope(custom, cwd) is custom
    exchange = ReviewExchange(configuration(), cwd)
    assert protect_command_scope(exchange, cwd.parent) is exchange
    assert exchange.protected_roots == (cwd.parent,)


def test_cleanup_error_does_not_mask_call_error(tmp_path, cwd, monkeypatch):
    original = tempfile.TemporaryDirectory.cleanup
    def failure(instance):
        original(instance)
        raise OSError('synthetic-sensitive-cleanup-detail')
    monkeypatch.setattr(tempfile.TemporaryDirectory, 'cleanup', failure)
    with pytest.raises(RuntimeError, match='original call outcome'):
        with ce.invocation(configuration(), cwd=cwd, parent=parent(tmp_path)) as (_, audit):
            raise RuntimeError('original call outcome')
    assert audit['scratch_cleanup'] == 'failed' and 'synthetic-sensitive' not in json.dumps(audit)


@pytest.mark.skipif(os.name == 'nt', reason='Reproduced POSIX recursive cleanup boundary')
def test_real_recursive_cleanup_preserves_owned_outcome(tmp_path):
    script = '''
import json,sys
from pathlib import Path
from attune_harness.command_environment import invocation
root=Path(sys.argv[1])
cfg={'command':[sys.executable],'environment':{'profile':'command-env-v1','passthrough':[]}}
try:
 with invocation(cfg,cwd=root/'work',parent={'TMPDIR':str(root)}) as (environment,audit):
  path=Path(environment['HOME'])
  for _ in range(140):
   path=path/'d';path.mkdir()
  sys.setrecursionlimit(80)
  raise RuntimeError('owned-call-outcome')
except BaseException as exc:
 sys.setrecursionlimit(1000)
 print(json.dumps({'type':type(exc).__name__,'detail':str(exc),'audit':audit}))
'''
    result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(tmp_path)],
                            capture_output=True, text=True, timeout=20, check=True)
    receipt = json.loads(result.stdout)
    assert receipt['type'] == 'RuntimeError' and receipt['detail'] == 'owned-call-outcome'
    assert receipt['audit']['scratch_cleanup'] == 'failed'


def test_notice_uses_only_selected_configs_and_never_mutates_record():
    finite = configuration()
    legacy = {key: value for key, value in finite.items() if key != 'environment'}
    record = {'request': {'registry': {'participants': {'used': finite, 'unused': legacy}},
                          'answers': {'assessor': 'used'}}, 'checkpoint_digest': 'unchanged'}
    original = copy.deepcopy(record)
    assert ce.annotate(record, ce.selected_configurations(record)) == record
    assert 'deprecations' not in record
    record['request']['answers']['assessor'] = 'unused'
    display = ce.annotate(record, ce.selected_configurations(record))
    assert display['deprecations'] == [ce.NOTICE] and 'deprecations' not in record
    display['request']['answers']['assessor'] = 'changed-display'
    assert record['request']['answers']['assessor'] == 'unused'
    assert record['checkpoint_digest'] == original['checkpoint_digest']
