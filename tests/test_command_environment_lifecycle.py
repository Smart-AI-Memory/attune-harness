"""Real command lifetime and retained authority; synthetic peers only."""
# qualify: platform

import copy
import json
import os
from pathlib import Path
import sys
from threading import Event, Thread
import time

import pytest

from attune_harness import command_environment as ce, consultation
from attune_harness.cli import main
from attune_harness.review import review
from attune_harness.review_participants import ReviewExchange
from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import execute_task
from test_command_environment import configuration, PEER
from test_consultation import config as consultation_config
from test_review import case, change_config, change
from test_task_contract import draft, response
from test_work_contract import work, make
from test_work_planning import command_peer
from test_task_repair_effects import effect_case


@pytest.mark.parametrize('mode', ['timeout', 'cancel', 'output-limit'])
def test_owned_child_lifetime_and_cleanup(tmp_path, monkeypatch, mode):
    cwd = tmp_path / 'work'; cwd.mkdir()
    marker = tmp_path / 'started.json'
    script = tmp_path / 'waiting.py'
    script.write_text('''import json,os,pathlib,sys,time
sys.stdin.read()
pathlib.Path(sys.argv[1]).write_text(json.dumps({'home':os.environ['HOME'],'pid':os.getpid()}))
if sys.argv[2]=='output-limit':
 print('x'*70000,flush=True)
while True:time.sleep(60)
''', encoding='utf-8')
    monkeypatch.setenv('TMPDIR', str(tmp_path)); monkeypatch.setenv('TEMP', str(tmp_path))
    cfg = configuration()
    cfg.update(command=[sys.executable, '-I', '-B', str(script), str(marker), mode], timeout=1)
    cfg['identity'] = {'provider': 'synthetic', 'model': 'peer-1'}
    turn = {'attempt_id': 'lifetime', 'contract_digest': 'a'*64, 'participant': 'peer',
            'snapshot': {'root': str(cwd), 'files': {}}}
    cancel, finished = Event(), Event()
    observed = []
    def observe():
        deadline = time.monotonic() + 10
        while not finished.is_set() and time.monotonic() < deadline:
            if marker.exists():
                try:
                    item = json.loads(marker.read_text())
                except ValueError:
                    continue
                observed.append(Path(item['home']).is_dir())
                if mode == 'cancel':
                    cancel.set()
                return
            finished.wait(.005)
    thread = Thread(target=observe, daemon=True); thread.start()
    try:
        result = consultation.dispatch(cfg, turn, cwd, cancel)
    finally:
        finished.set(); thread.join(timeout=2)
    assert not thread.is_alive()
    marker_value = json.loads(marker.read_text())
    if mode != 'output-limit':
        assert observed == [True]
    assert not Path(marker_value['home']).exists()
    assert result['status'] == ('cancelled' if mode == 'cancel' else 'failed')
    assert result['process']['returncode'] is not None
    assert result['error']['effects'] == 'unknown'
    assert result['identity']['environment']['profile'] == ce.PROFILE


def test_review_timeout_keeps_identity_after_scratch_cleanup(tmp_path, monkeypatch):
    cwd = tmp_path / 'work'; cwd.mkdir()
    marker = tmp_path / 'home.txt'
    script = tmp_path / 'sleep.py'
    script.write_text('import os,pathlib,sys,time\nsys.stdin.read()\n'
                      'pathlib.Path(sys.argv[1]).write_text(os.environ["HOME"])\ntime.sleep(60)\n')
    monkeypatch.setenv('TMPDIR', str(tmp_path)); monkeypatch.setenv('TEMP', str(tmp_path))
    cfg = configuration(); cfg.update(command=[sys.executable, '-I', str(script), str(marker)], timeout=1)
    exchange = ReviewExchange(cfg, cwd)
    with pytest.raises(RuntimeError, match='command failed'):
        exchange(json.dumps({'turn': {}}))
    assert exchange.last_identity['returncode'] is not None
    assert exchange.last_identity['environment']['profile'] == ce.PROFILE
    assert not Path(marker.read_text()).exists()


@pytest.mark.parametrize('route', ['review', 'assessment'])
def test_real_owner_finite_commands_and_replay_do_not_rebuild_environment(case, monkeypatch, capsys, route):
    peer = case[0].parent / 'peer.py'; peer.write_text(PEER)
    cfg = configuration(); cfg['command'] = [sys.executable, '-I', '-B', str(peer)]
    change_config(case, lambda data: data.update(participants={'alpha': cfg, 'beta': copy.deepcopy(cfg)}))
    if route == 'review':
        result = review(*case, allow_external=True)
    else:
        draft(case, plan='independent-review')
        submission = response(case[2]); submission['permissions']['external'] = True
        accept_task(case[2], submission)
        result = execute_task(case[2])
    assert result['status'] == 'completed'
    before = (case[2] / 'record.json').read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail('Inspection/replay rebuilt a child environment')
    monkeypatch.setattr('attune_harness.review_participants.command_environment', forbidden)
    if route == 'assessment':
        assert execute_task(case[2]) == result == read_task(case[2])
        assert main(['status', str(case[2])]) == 0
    else:
        assert main(['inspect-review', str(case[2])]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert 'deprecations' not in shown
    assert (case[2] / 'record.json').read_bytes() == before
    run = result.get('execution', result)
    assert all(item['last_identity']['environment']['profile'] == ce.PROFILE
               for item in run['participants'].values())


@pytest.mark.parametrize('route', ['review', 'assessment'])
def test_actual_owner_protects_state_before_command_dispatch(case, monkeypatch, route):
    cfg = configuration(); cfg['command'] = [sys.executable, '-I', '-c', 'raise AssertionError("launched")']
    change_config(case, lambda data: data.update(participants={'alpha': cfg, 'beta': copy.deepcopy(cfg)}))
    if route == 'assessment':
        draft(case)
        submission = response(case[2]); submission['permissions']['external'] = True
        accept_task(case[2], submission)
    monkeypatch.setenv('TMPDIR', str(case[2])); monkeypatch.setenv('TEMP', str(case[2]))
    result = review(*case, allow_external=True) if route == 'review' else execute_task(case[2])
    assert result['status'] != 'completed'
    assert 'outside the work scope' in json.dumps(result)
    assert not list(case[2].glob('harness-command-*'))


def test_planning_factory_gets_state_exclusion_without_signature_change(work, monkeypatch):
    from attune_harness.work_runtime import plan_work
    command_peer(work)
    change(work[1], lambda data: [item.update(environment={'profile': ce.PROFILE, 'passthrough': []})
                                 for item in data['participants'].values()])
    make(work)
    monkeypatch.setenv('TMPDIR', str(work[2]['directory']))
    monkeypatch.setenv('TEMP', str(work[2]['directory']))
    calls = []
    def factory(config, cwd, *, profile):
        calls.append(profile)
        return ReviewExchange(config, cwd, profile=profile)
    result = plan_work(work[2]['directory'], allow_external=True, exchange_factory=factory)
    assert calls == ['feature-planning-v1']
    assert result['status'] != 'completed' and 'outside the work scope' in json.dumps(result)
    assert not list(work[2]['directory'].glob('harness-command-*'))


def test_environment_is_read_at_each_dispatch_after_exchange_construction(tmp_path, monkeypatch):
    cwd = tmp_path / 'work'; cwd.mkdir()
    peer = tmp_path / 'peer.py'; peer.write_text(PEER)
    monkeypatch.setenv('TMPDIR', str(tmp_path)); monkeypatch.setenv('TEMP', str(tmp_path))
    cfg = configuration('ATTUNE_TEST_ALLOW'); cfg['command'] = [sys.executable, '-I', str(peer)]
    exchange = ReviewExchange(cfg, cwd)
    for value in ('rotated-first', 'rotated-second'):
        monkeypatch.setenv('ATTUNE_TEST_ALLOW', value)
        result = json.loads(exchange(json.dumps({'turn': {}})))
        assert json.loads(result['action']['text'])['allowed'] == value
        assert value not in json.dumps(exchange.last_identity)


def test_legacy_api_warns_and_keeps_original_inheritance_shape(tmp_path, monkeypatch):
    from attune_harness.process import ProcessResult
    cfg = configuration(); cfg.pop('environment')
    def runner(argv, raw, **kwargs):
        assert 'environment' not in kwargs
        return ProcessResult(argv, 0, 'legacy-response', '')
    monkeypatch.setattr('attune_harness.review_participants.invoke', runner)
    exchange = ReviewExchange(cfg, tmp_path)
    with pytest.warns(ce.CommandEnvironmentDeprecationWarning, match='full parent'):
        assert exchange(json.dumps({'turn': {}})) == 'legacy-response'
    assert exchange.last_identity == {'adapter': 'command', 'returncode': 0, 'failure': None, 'stderr': ''}


def test_preflight_finite_executable_never_uses_ambient_search(tmp_path, monkeypatch):
    from attune_harness.consultation_preflight import preflight
    config = consultation_config()
    seat = config['participants']['reviewer']
    seat.update(command=[sys.executable], environment={'profile': ce.PROFILE, 'passthrough': ['MISSING_CANARY']})
    def forbidden(*args, **kwargs):
        pytest.fail('Finite command preflight searched PATH or dispatched a wrapper')
    monkeypatch.setattr('attune_harness.consultation_preflight.shutil.which', forbidden)
    monkeypatch.setattr('attune_harness.consultation_preflight.invoke', forbidden)
    assert preflight(config)['reviewer']['binary'] == sys.executable
    seat['command'] = [str(tmp_path / 'absent-executable')]
    report = preflight(config)['reviewer']
    assert report['state'] == 'missing_binary' and 'add it to PATH' not in report['fix']
    seat['command'] = ['python']
    with pytest.raises(ValueError, match='absolute initial executable'):
        preflight(config)


def test_transferred_assignment_drives_notice_selection():
    finite = configuration(); legacy = {k:v for k,v in finite.items() if k != 'environment'}
    record = {'request': {'registry': {'participants': {'original': legacy, 'current': finite}},
                          'answers': {'assessor': 'original'}},
              'execution': {'recovery': {'assignments': {'assessor': {'participant_id': 'current'}}}}}
    assert ce.selected_configurations(record) == [finite]
    assert 'deprecations' not in ce.annotate(record, ce.selected_configurations(record))


@pytest.mark.parametrize('route', ['consultation', 'review'])
def test_native_route_does_not_enter_command_environment(tmp_path, monkeypatch, route):
    calls = []
    def forbidden(*args, **kwargs):
        pytest.fail('Native adapter entered the command environment policy')
    def native(adapter, **kwargs):
        calls.append((adapter, kwargs))
        raise RuntimeError('native-construction-spy')
    module = consultation if route == 'consultation' else __import__(
        'attune_harness.review_participants', fromlist=['ReviewExchange'])
    monkeypatch.setattr(module, 'command_environment', forbidden)
    monkeypatch.setattr(module, 'NativeExchange', native)
    with pytest.raises(RuntimeError, match='native-construction-spy'):
        if route == 'consultation':
            cfg = {'adapter': 'claude', 'identity': {'provider': 'claude', 'model': 'synthetic-native'}, 'timeout': 5}
            turn = {'attempt_id': 'probe', 'contract_digest': 'a'*64, 'participant': 'peer', 'snapshot': {}}
            consultation.dispatch(cfg, turn, tmp_path, Event())
        else:
            cfg = {'adapter': 'claude', 'model': 'synthetic-native', 'timeout': 5, 'tools': []}
            ReviewExchange(cfg, tmp_path)(json.dumps({'turn': {'task_id': 'probe'}}))
    assert calls[0][0] == 'claude' and 'environment' not in calls[0][1]


@pytest.mark.skipif(os.name != 'posix', reason='Existing repair profile is POSIX only')
def test_repair_factory_keeps_signature_and_protects_task_state(effect_case, monkeypatch):
    from test_task_repair import prepare
    cfg = configuration()
    directory = prepare(effect_case, config={'schema_version': 1, 'participants': {'worker': cfg, 'reviewer': cfg}})
    monkeypatch.setenv('TMPDIR', str(directory))
    calls = []
    def factory(config, cwd):
        calls.append(cwd)
        return ReviewExchange(config, cwd)
    result = execute_task(directory, exchange_factory=factory)
    assert len(calls) == 1 and result['status'] != 'completed'
    assert 'outside the work scope' in json.dumps(result)
    assert not list(directory.glob('harness-command-*'))


def test_build_factory_keeps_signature_and_protects_task_state(work, monkeypatch):
    from test_work_build import prepare
    from attune_harness.work_build import build_work
    cfg = configuration()
    change(work[1], lambda data: data.update(participants={'local': cfg, 'critic': cfg}))
    _, directory, _ = prepare(work)
    monkeypatch.setenv('TMPDIR', str(directory)); monkeypatch.setenv('TEMP', str(directory))
    calls = []
    def factory(config, cwd, *, profile):
        calls.append(profile)
        return ReviewExchange(config, cwd, profile=profile)
    result = build_work(directory, allow_external=True, exchange_factory=factory)
    assert calls == ['feature-build-v1'] and result['status'] != 'completed'
    assert 'outside the work scope' in json.dumps(result)
    assert not list(directory.glob('harness-command-*'))
