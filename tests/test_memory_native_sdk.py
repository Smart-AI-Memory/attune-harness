"""Real pinned SDK in a supervised child with external sockets blocked.

# qualify: platform
This qualifies software transport behavior, never live provider/model quality.
"""

import base64
from copy import deepcopy
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest

from attune_harness import memory_native as native
from attune_harness.features import FeatureUnavailable
from attune_harness.memory_worker import WorkerStore, run, validated_proposal
from attune_harness.memory_context import MemoryHost
from attune_harness.process import invoke
from attune_harness.review_contract import canonical, digest, parse_json
from test_memory_native_boundaries import config, message  # noqa: F401
from test_memory_worker import packet, proposal  # noqa: F401
from test_memory_host_coverage import host  # noqa: F401


@pytest.fixture
def sdk():
    absent = [name for name in ('anthropic', 'httpx2') if importlib.util.find_spec(name) is None]
    if absent:
        if os.environ.get('HARNESS_REQUIRE_NATIVE_SDK') == '1':
            pytest.fail('Required optional SDK is absent: ' + ', '.join(absent))
        pytest.skip('Install the optional memory-native extra for real SDK checks')
    # Installed but unqualified versions are failures, not optional skips.
    return native.runtime_identity()


def effective_environment(environment):
    expected = {k.upper() if os.name == 'nt' else k: v for k, v in environment.items()}
    if sys.platform == 'darwin':
        # The witnessed Darwin startup profile regenerates this metadata even
        # when omitted or supplied as a canary. Derive it from the real UID,
        # never from the target's reported environment.
        expected['__CF_USER_TEXT_ENCODING'] = f'0x{os.getuid():X}:0x0:0x0'
    if os.name == 'nt':
        # This exact AMD64-on-ARM64 runtime adds AMD64 metadata even to a finite
        # map. Identify it independently of mutable environment/platform text.
        with Path(sys.executable).open('rb') as stream:
            header = stream.read(64)
            assert header[:2] == b'MZ'
            stream.seek(int.from_bytes(header[60:64], 'little'))
            image = stream.read(6)
        assert image[:4] == b'PE\0\0'
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.GetCurrentProcess.restype = wintypes.HANDLE
        api.GetCurrentProcess.argtypes = []
        api.IsWow64Process2.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ushort),
                                       ctypes.POINTER(ctypes.c_ushort)]
        api.IsWow64Process2.restype = wintypes.BOOL
        process, host = ctypes.c_ushort(), ctypes.c_ushort()
        assert api.IsWow64Process2(api.GetCurrentProcess(), ctypes.byref(process), ctypes.byref(host))
        profile = (int.from_bytes(image[4:6], 'little'), process.value, host.value)
        if profile == (0x8664, 0, 0xaa64):
            expected['PROCESSOR_ARCHITECTURE'] = 'AMD64'
    return expected


def validate_child_argv(value, requested, runtime):
    assert len(requested) == 5 and value['runtime'] == runtime
    assert runtime['python'] == requested[0]
    assert value['base_executable'] == sys._base_executable
    assert value['prefix'] == sys.prefix and value['base_prefix'] == sys.base_prefix
    expected = list(requested)
    if (os.name == 'nt' and sys.implementation.name == 'cpython'
            and sys.version_info[:2] in ((3, 10), (3, 12)) and sys.prefix != sys.base_prefix):
        # CPython's standard Windows venv redirector launches the configured
        # base executable as argv[0]. Derive it from the parent and pyvenv.cfg,
        # never from the target's reported argv. Every other argument is exact.
        launcher = Path(requested[0])
        base = Path(sys._base_executable)
        assert launcher == Path(sys.prefix) / 'Scripts' / 'python.exe'
        assert launcher.is_file() and not launcher.is_symlink()
        assert base == Path(sys.base_prefix) / 'python.exe' and base.is_file()
        config = {}
        for line in (Path(sys.prefix) / 'pyvenv.cfg').read_text(encoding='utf-8').splitlines():
            if '=' in line:
                key, setting = line.split('=', 1)
                config[key.strip()] = setting.strip()
        assert Path(config['home']) == base.parent
        expected[0] = str(base)
    assert value['interpreter_argv'] == expected


@pytest.mark.parametrize('version', [(3, 10), (3, 12)], ids=['cpython310', 'cpython312'])
def test_windows_venv_argv_validation_uses_independent_parent_files(monkeypatch, tmp_path, version):
    base = tmp_path / 'base' / 'python.exe'
    launcher = tmp_path / 'venv' / 'Scripts' / 'python.exe'
    base.parent.mkdir()
    launcher.parent.mkdir(parents=True)
    base.write_bytes(b'base interpreter fixture')
    launcher.write_bytes(b'venv launcher fixture')
    prefix = launcher.parent.parent
    (prefix / 'pyvenv.cfg').write_text('home = ' + str(base.parent) + '\n', encoding='utf-8')
    module = sys.modules[__name__]
    monkeypatch.setattr(module, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(module, 'sys', SimpleNamespace(
        implementation=SimpleNamespace(name='cpython'), version_info=version,
        prefix=str(prefix), base_prefix=str(base.parent), _base_executable=str(base)))
    requested = [str(launcher), '-I', '-B', '-c', 'trusted helper']
    runtime = {'python': str(launcher)}
    value = dict(runtime=runtime, base_executable=str(base), prefix=str(prefix),
                 base_prefix=str(base.parent), interpreter_argv=[str(base), *requested[1:]])
    validate_child_argv(value, requested, runtime)
    for index in range(5):
        changed = deepcopy(value)
        changed['interpreter_argv'][index] = 'substituted-argv-entry'
        with pytest.raises(AssertionError):
            validate_child_argv(changed, requested, runtime)
    (prefix / 'pyvenv.cfg').write_text('home = ' + str(tmp_path / 'other') + '\n', encoding='utf-8')
    with pytest.raises(AssertionError):
        validate_child_argv(value, requested, runtime)


@pytest.fixture
def offline(monkeypatch, tmp_path, sdk, request):
    for name in native.DENIED_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'offline-native-test-key')
    for name in ('ANTHROPIC_AUTH_TOKEN_UNUSED', 'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY',
                 'PATH', 'PYTHONPATH', 'UNRELATED_SECRET', 'PROCESSOR_ARCHITECTURE'):
        monkeypatch.setenv(name, 'ambient-must-not-inherit')
    environment = native._helper_environment('offline-native-test-key')
    expected = effective_environment(environment)
    before = deepcopy(environment)
    receipts = []
    arguments = {}
    original_argv = native._helper_argv()

    def install(message, *, mode='reply', status=200, force_windows_client=False, audit_cwd=None):
        path = tmp_path / f'child-{len(receipts)}.json'
        receipts.append(path)
        raw = json.dumps(message, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        options = dict(receipt=str(path), expected_environment=list(expected),
                       raw_base64=base64.b64encode(raw).decode('ascii'), mode=mode, status=status,
                       descendant_marker=str(tmp_path / 'escaped'),
                       descendant_gate=str(tmp_path / 'supervisor-returned'),
                       descendant_started=str(tmp_path / 'descendant-started'),
                       audit_cwd=str(audit_cwd) if audit_cwd else None,
                       force_windows_client=force_windows_client)
        code = ('import sys,runpy;sys.path.insert(0,' + repr(str(Path(native.__file__).resolve().parents[1])) + ');'
                'from attune_harness.memory_native import helper_main;'
                'raise SystemExit(runpy.run_path(' + repr(str(Path(__file__).with_name('native_memory_offline_child.py'))) + ')["main"]('
                + repr(options) + '))')
        argv = (*original_argv[:4], code)
        arguments[path] = list(argv)
        monkeypatch.setattr(native, '_helper_argv', lambda: argv)
        return argv

    def read(index=-1):
        value = json.loads(receipts[index].read_bytes())
        validate_child_argv(value, arguments[receipts[index]], sdk)
        assert value['environment_keys'] == sorted(expected)
        assert value['environment_values'] == expected
        assert value['sdk_import_environment_keys'] == sorted(expected)
        if value['offline_sdk_requests']:
            assert value['dispatch_environment_keys'] == sorted(expected)
            assert value['dispatch_environment_values'] == expected
        assert value['network_guard_checks'] == ['connect', 'connect_ex', 'create_connection', 'dns']
        assert value['external_network_attempts'] == value['live_provider_model_calls'] == 0
        assert value['home_lookups'] == 0
        assert value['cwd_file_open_attempts'] == 0
        assert value['http_transport_constructed_and_closed'] is True
        assert value['sdk_source_sha256'] == {
            '_client.py': '69819477054ffebb9daa9a935b137cb37cd05c5c5e2f80a3928d14c6903ff02c',
            'lib/credentials/_constants.py': 'f24748cbfce141773158e7919b4dcffef4f0fe54394094dc940359def7da247a',
        }
        if os.name == 'nt':
            assert value['home_lookup_guard'] is True
        if value['offline_sdk_requests']:
            assert value['explicit_key_header'] is True
            assert value['authorization_header_present'] is False
        if not value.get('descendant_spawned'):
            wire = base64.b64decode(value['helper_stdout_base64'], validate=True)
            assert wire.endswith(b'\n') and b'\r' not in wire
            assert parse_json(wire.decode('utf-8'))['state'] in ('completed', 'unresolved')
        assert environment == before
        return value

    yield SimpleNamespace(install=install, read=read, paths=receipts, environment=environment,
                          original_argv=original_argv)
    output = os.environ.get('HARNESS_NATIVE_MEMORY_OUTPUT')
    if output:
        destination = Path(output)
        destination.mkdir(parents=True, exist_ok=True)
        for index, path in enumerate(receipts):
            assert path.is_file(), 'Supervised child wrote no offline witness'
            value = json.loads(path.read_bytes())
            value['supervisor_requested_argv'] = arguments[path]
            (destination / f'{request.node.name}-{index}.json').write_bytes(
                (json.dumps(value, sort_keys=True) + '\n').encode('utf-8'))


def test_real_sdk_helper_unicode_receipt_replays(config, message, offline, sdk):
    message['content'][0]['text'] = json.dumps({'outcome': 'café 東京 🚀'}, ensure_ascii=False)
    argv = offline.install(message)
    actor = native.NativeParticipant(config)
    descriptor = actor.descriptor()
    assert len(descriptor['helper_argv']) == 5
    assert native.validate_descriptor(descriptor) == config
    prompt = {'source': 'Untrusted café 東京 🚀'}
    body = native.request_body('worker', 'routine', prompt, {}, config)
    reply = actor('worker', 'routine', prompt, {})
    witness = offline.read()
    assert witness['offline_sdk_requests'] == 1
    assert witness['request']['method'] == 'POST'
    assert witness['request']['url'] == native.ENDPOINT + '/v1/messages'
    assert witness['request']['body'] == body
    assert reply['value'] == {'outcome': 'café 東京 🚀'}
    assert reply['evidence']['attempted_argv'] == list(argv)
    assert reply['evidence']['runtime_digest'] == digest(sdk)
    assert reply['evidence']['identity']['usage'] == {'input_tokens': 12, 'output_tokens': 5}
    assert native.validate_evidence(reply['evidence'], body) == reply['value']
    raw = base64.b64decode(reply['evidence']['provider']['raw_base64'])
    assert b'\xc3\xa9' in raw
    assert hashlib.sha256(raw).hexdigest() == reply['evidence']['provider']['raw_sha256']


def test_helper_binary_utf8_ignores_text_locale(config, message, offline, sdk):
    message['content'][0]['text'] = json.dumps({'outcome': 'café 東京 🚀'}, ensure_ascii=False)
    argv = offline.install(message)
    # Explicit binary I/O also accepts literal UTF-8 input under ASCII wrappers.
    utf8_body = native.request_body('worker', 'routine', {'source': 'café 東京 🚀'}, {}, config)
    utf8_body['messages'][0]['content'] = json.dumps(parse_json(utf8_body['messages'][0]['content']), ensure_ascii=False)
    packet = dict(schema_version=1, body=utf8_body, phase_timeout_seconds=10,
                  response_byte_limit=2048, runtime=sdk)
    assert '東京' in json.dumps(packet, ensure_ascii=False)
    result = invoke(argv, json.dumps(packet, ensure_ascii=False), cwd=Path.cwd(),
                    environment=offline.environment)
    assert result.failure is None and result.returncode == 0 and result.stderr == ''
    assert '\r' not in result.stdout and result.stdout.endswith('\n')
    assert native.decode_provider(parse_json(result.stdout), utf8_body)[0] == {'outcome': 'café 東京 🚀'}
    assert offline.read()['offline_sdk_requests'] == 1


def test_windows_explicit_key_client_does_not_discover_home(config, message, offline):
    offline.install(message, force_windows_client=True)
    result = native.NativeParticipant(config)('worker', 'routine', {}, {})
    assert result['value'] == {'outcome': 'proposal'}
    witness = offline.read()
    assert witness['home_lookup_guard'] is True and witness['home_lookups'] == 0
    assert witness['offline_sdk_requests'] == 1


def test_real_sdk_ignores_and_never_opens_cwd_decoys(config, message, offline, sdk, tmp_path):
    directory = tmp_path / "decoy cwd café's 東京"
    directory.mkdir()
    imported = tmp_path / 'decoy-imported'
    decoy = ('from pathlib import Path\n'
             f'Path({str(imported)!r}).write_bytes(b"imported")\n'
             'raise RuntimeError("Imported cwd decoy")\n')
    for name in ('anthropic.py', 'httpx2.py', 'sitecustomize.py', 'usercustomize.py'):
        (directory / name).write_text(decoy, encoding='utf-8')
    argv = offline.install(message, audit_cwd=directory)
    body = native.request_body('worker', 'routine', {}, {}, config)
    packet = dict(schema_version=1, body=body, phase_timeout_seconds=10,
                  response_byte_limit=2048, runtime=sdk)
    result = invoke(argv, canonical(packet), cwd=directory, environment=offline.environment)
    assert result.failure is None and result.returncode == 0 and result.stderr == ''
    assert native.decode_provider(parse_json(result.stdout), body)[0] == {'outcome': 'proposal'}
    witness = offline.read()
    assert witness['offline_sdk_requests'] == 1
    assert Path(witness['child_cwd']) == directory
    assert witness['cwd_read_guard_checks'] == ['open']
    assert witness['cwd_file_open_attempts'] == 0
    assert not imported.exists()


def test_child_argv_witness_rejects_every_substituted_entry(config, message, offline, sdk):
    requested = offline.install(message)
    native.NativeParticipant(config)('worker', 'routine', {}, {})
    value = offline.read()
    for index in range(5):
        changed = deepcopy(value)
        changed['interpreter_argv'][index] = 'substituted-argv-entry'
        with pytest.raises(AssertionError):
            validate_child_argv(changed, requested, sdk)


@pytest.mark.parametrize('mode', ['bad-message', 'oversize', 'http-error'])
def test_real_sdk_failure_is_retained_without_retry(config, message, offline, mode):
    if mode == 'bad-message':
        message['stop_reason'] = 'max_tokens'
    elif mode == 'oversize':
        message['content'][0]['text'] = 'x' * 4096
    offline.install(message, status=503 if mode == 'http-error' else 200)
    with pytest.raises(native.NativeMemoryError) as raised:
        native.NativeParticipant(config)('worker', 'routine', {}, {})
    assert offline.read()['offline_sdk_requests'] == 1
    evidence = raised.value.evidence
    assert evidence['returncode'] == 0
    if mode == 'oversize':
        receipt = parse_json(evidence['stdout'])
        assert receipt['state'] == 'unresolved' and receipt['truncated'] is True
        assert receipt['observed_bytes'] == 2048


def test_real_helper_runtime_mismatch_refuses_before_sdk(config, message, offline, sdk):
    argv = offline.install(message)
    packet = dict(schema_version=1, body={}, phase_timeout_seconds=10,
                  response_byte_limit=2048, runtime={**sdk, 'python_version': 'changed'})
    result = invoke(argv, canonical(packet), cwd=Path.cwd(), environment=offline.environment)
    receipt = parse_json(result.stdout)
    assert result.failure is None and result.returncode == 0
    assert receipt['state'] == 'unresolved' and receipt['failure'] == 'FeatureUnavailable'
    assert 'differs from claimed descriptor' in receipt['detail']
    assert offline.read()['offline_sdk_requests'] == 0


def test_supervised_sdk_timeout_kills_descendant(config, message, offline, tmp_path):
    offline.install(message, mode='timeout')
    config.update(phase_timeout_seconds=2, wall_timeout_seconds=8)
    with pytest.raises(native.NativeMemoryError) as raised:
        native.NativeParticipant(config)('worker', 'routine', {}, {})
    assert raised.value.evidence['failure'] == 'timeout_effects_unknown'
    witness = offline.read()
    assert witness['offline_sdk_requests'] == 1 and witness['descendant_spawned'] is True
    assert witness['descendant_started'] is witness['descendant_alive_before_timeout'] is True
    assert witness['descendant_pid'] > 0
    (tmp_path / 'supervisor-returned').write_bytes(b'returned')
    time.sleep(0.8)
    assert not (tmp_path / 'escaped').exists()


def test_production_bootstrap_refuses_missing_key_without_dispatch(config, sdk, monkeypatch):
    # Unmodified production argv. A missing key refuses before sdk_exchange.
    environment = native._helper_environment('unused-synthetic-key')
    del environment['ANTHROPIC_API_KEY']
    packet = dict(schema_version=1, body={}, phase_timeout_seconds=1,
                  response_byte_limit=2048, runtime=sdk)
    result = invoke(native._helper_argv(), canonical(packet), cwd=Path.cwd(), environment=environment)
    receipt = parse_json(result.stdout)
    assert result.failure is None and result.returncode == 0 and result.stderr == ''
    assert receipt['state'] == 'unresolved' and receipt['failure'] == 'ValueError'
    assert receipt['detail'] == 'Missing native API key'


def test_real_sdk_worker_preserves_claim_and_no_redispatch(config, message, offline, packet, tmp_path):
    envelope, policy = packet
    config['profiles']['astra'] = deepcopy(config['profiles'].pop('routine'))
    config['profiles']['luna'] = deepcopy(config['profiles']['astra'])
    message['content'][0]['text'] = canonical(proposal(envelope))
    offline.install(message)
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    result = run(store, 'job', native.NativeParticipant(config))
    assert result['status'] == 'proposal_ready'
    assert len(result['attempts']) == 1
    assert validated_proposal(store, 'job')['version'] == 8
    assert store.read()['envelope'] == envelope
    with pytest.raises(ValueError, match='already claimed'):
        run(store, 'job', native.NativeParticipant(config))
    assert offline.read()['offline_sdk_requests'] == 1


def test_offline_host_create_execute_inspect_preserves_transmission_uncertainty(
    config, message, offline, packet, host,
):
    envelope, policy = packet
    config['profiles'] = {name: deepcopy(config['profiles']['routine']) for name in ('luna', 'astra')}
    message['content'][0]['text'] = canonical(proposal(envelope))
    offline.install(message)
    host = MemoryHost(host.config, jobs=host.jobs, native=config)
    assert host.invoke('create', dict(run_id='run', envelope=envelope, policy=policy)) == {
        'status': 'created', 'mode': 'proposal_worker', 'generation': 0}
    assert WorkerStore(host.jobs / 'run').read()['jobs'] == {}
    result = host.invoke('execute', dict(run_id='run', job_id='job'))
    assert result['status'] == 'proposal_ready' and result['dispatch_attempts'] == 1
    assert result['provider_transmission'] == 'unknown; see per-attempt transport evidence'
    assert host.invoke('inspect', dict(run_id='run', job_id='job')) == result['result']
    assert offline.read()['offline_sdk_requests'] == 1


def test_uncertain_real_sdk_job_is_never_redispatched(config, message, offline, packet, tmp_path):
    envelope, policy = packet
    config['profiles'] = {name: deepcopy(config['profiles']['routine']) for name in ('luna', 'astra')}
    offline.install(message, status=503)
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    with pytest.raises(native.NativeMemoryError):
        run(store, 'job', native.NativeParticipant(config))
    result = store.inspect('job')
    assert result['status'] == 'unresolved' and len(result['attempts']) == 1
    before = store.read()
    with pytest.raises(ValueError, match='already claimed'):
        run(store, 'job', native.NativeParticipant(config))
    assert store.read() == before
    assert offline.read()['offline_sdk_requests'] == 1


@pytest.mark.parametrize('refusal', ['missing-key', 'override', 'profiles', 'authority', 'missing-sdk'])
def test_host_refusals_never_claim_or_launch(config, sdk, monkeypatch, packet, host, refusal):
    envelope, policy = deepcopy(packet)
    config['profiles'] = {name: deepcopy(config['profiles']['routine']) for name in ('luna', 'astra')}
    for name in native.DENIED_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'offline-native-test-key')
    monkeypatch.setattr(native, 'invoke', lambda *a, **k: pytest.fail('Refused host launched a child'))
    host = MemoryHost(host.config, jobs=host.jobs, native=config)
    if refusal == 'authority':
        envelope['access']['owners'].append('foreign')
        with pytest.raises(ValueError, match='host authority'):
            host.invoke('create', dict(run_id='run', envelope=envelope, policy=policy))
        assert not (host.jobs / 'run').exists()
        return
    host.invoke('create', dict(run_id='run', envelope=envelope, policy=policy))
    if refusal == 'missing-key':
        monkeypatch.delenv('ANTHROPIC_API_KEY')
    elif refusal == 'override':
        monkeypatch.setenv('ANTHROPIC_BASE_URL', 'https://must-refuse.invalid')
    elif refusal == 'profiles':
        host.native.config['profiles'].pop('astra')
    else:
        def unavailable():
            raise FeatureUnavailable('Native memory requires the qualified Anthropic SDK')
        monkeypatch.setattr(native, 'runtime_identity', unavailable)
    if refusal == 'profiles':
        with pytest.raises(ValueError, match='profile map differs'):
            host.invoke('execute', dict(run_id='run', job_id='job'))
    else:
        result = host.invoke('execute', dict(run_id='run', job_id='job'))
        assert result['status'] == 'unavailable'
        assert result['dispatch_attempts'] == 0 and result['provider_transmission'] == 'none'
    assert WorkerStore(host.jobs / 'run').read()['jobs'] == {}
