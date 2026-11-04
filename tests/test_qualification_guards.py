"""Qualification evidence must come from a wheel and retain every failed gate."""

# qualify: platform

import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('partition_exit', [0, 1, 124])
def test_installed_partition_postchecks_run_once_only_after_success(wheel_install, tmp_path, monkeypatch, partition_exit):
    qualifier = load('qualify_platform')
    monkeypatch.setattr(qualifier, 'platform', SimpleNamespace(
        system=lambda: 'Windows', machine=lambda: 'AMD64', python_version=lambda: '3.12-control'))
    output = tmp_path / 'qualification-partitions'
    calls = []
    def partitions(folder, argv, budget):
        calls.append('partitions')
        assert folder == output and budget == 2520
        if partition_exit == 0:
            (folder / 'plugin-probe.json').write_bytes(probe_bytes(qualifier, 'passed'))
        return subprocess.CompletedProcess(argv, partition_exit)
    def postcheck(argv, **kwargs):
        calls.append('postcheck')
        assert partition_exit == 0 and str(ROOT / 'scripts/check_installed.py') in argv
        (output / 'memory-redis.json').write_text(json.dumps({
            'memory': {'native_reader': 'available', 'tiers_read': ['raw', 'personal', 'curated'], 'reader_named': 'native'},
            'journey': {'accept': 'accepted', 'build': 'completed', 'review': 'completed'}}))
        return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')
    monkeypatch.setattr(qualifier, 'run_installed_partitions', partitions)
    monkeypatch.setattr(qualifier.subprocess, 'run', postcheck)
    assert qualifier.qualify(output, coverage_instrumented=True,
                             installed_coverage_partitions=True) == partition_exit
    receipt = json.loads((output / 'platform.json').read_text())
    assert calls == (['partitions', 'postcheck'] if partition_exit == 0 else ['partitions'])
    assert receipt['execution_topology'] == 'two_supervised_installed_module_partitions'
    assert receipt['native_process_and_recovery'] == 'not_qualified_instrumented'
    if partition_exit:
        assert all(receipt[name] == 'unrun' for name in ('memory_redis', 'native_memory_reader', 'r2_journey'))


@pytest.mark.parametrize('system,instrumented', [('Windows', False), ('Linux', True), ('Darwin', True)])
def test_installed_partition_mode_cannot_change_other_qualification_profiles(tmp_path, monkeypatch, system, instrumented):
    qualifier = load('qualify_platform')
    monkeypatch.setattr(qualifier, 'platform', SimpleNamespace(system=lambda: system))
    def forbidden():
        raise AssertionError('Invalid mode reached installed dispatch')
    monkeypatch.setattr(qualifier, 'installed_source', forbidden)
    output = tmp_path / 'uncreated'
    with pytest.raises(ValueError, match='Windows instrumented'):
        qualifier.qualify(output, coverage_instrumented=instrumented, installed_coverage_partitions=True)
    assert not output.exists()


def load(name):
    path = ROOT/'scripts'/f'{name}.py'
    spec = importlib.util.spec_from_file_location('review_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wheel_install(tmp_path, monkeypatch):
    """Real distribution metadata and RECORD parsing, without invoking an installer."""
    import attune_harness
    site = tmp_path/'site-packages'
    source = site/'attune_harness'
    source.mkdir(parents=True)
    metadata = site/'attune_harness-1.3.0.dist-info'
    metadata.mkdir()
    (metadata/'METADATA').write_text('Name: attune-harness\nVersion: 1.3.0\n')
    (metadata/'WHEEL').write_text('Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
    rows = []
    for name in ('__init__.py', 'worker.py'):
        path = source/name
        path.write_text('VALUE = 1\n')
        digest = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=')
        rows.append(f'attune_harness/{name},sha256={digest},{path.stat().st_size}')
    (metadata/'RECORD').write_text('\n'.join(rows)+'\n')
    distribution = importlib.metadata.PathDistribution(metadata)
    monkeypatch.setattr(importlib.metadata, 'distribution', lambda _: distribution)
    monkeypatch.setattr(attune_harness, '__file__', str(source/'__init__.py'))
    return source, metadata


def test_noneditable_wheel_sources_are_accepted(wheel_install):
    source, metadata = wheel_install
    qualifier = load('qualify_platform')
    assert qualifier.installed_source() == source
    # A normal local-wheel URL is allowed; only editable directory provenance refuses.
    (metadata/'direct_url.json').write_text(json.dumps({'url': 'file:///candidate.whl'}))
    assert qualifier.installed_source() == source


@pytest.mark.parametrize('case', ['other-source', 'editable', 'no-wheel', 'changed',
                                 'unrecorded', 'missing-hash', 'symlink'])
def test_invalid_install_is_refused_before_output_or_dispatch(wheel_install, tmp_path, monkeypatch, case):
    import attune_harness
    source, metadata = wheel_install
    qualifier = load('qualify_platform')
    if case == 'other-source':
        other = tmp_path/'second-checkout'/'src'/'attune_harness'
        other.mkdir(parents=True)
        (other/'__init__.py').write_text('VALUE = 1\n')
        monkeypatch.setattr(attune_harness, '__file__', str(other/'__init__.py'))
    elif case == 'editable':
        (metadata/'direct_url.json').write_text(json.dumps({'url': 'file:///second-checkout',
                                                         'dir_info': {'editable': True}}))
    elif case == 'no-wheel':
        (metadata/'WHEEL').unlink()
    elif case == 'changed':
        (source/'worker.py').write_text('VALUE = 2\n')
    elif case == 'unrecorded':
        (source/'extra.py').write_text('VALUE = 1\n')
    elif case == 'missing-hash':
        text = (metadata/'RECORD').read_text().splitlines()
        text[1] = 'attune_harness/worker.py,,'
        (metadata/'RECORD').write_text('\n'.join(text)+'\n')
    else:
        target = tmp_path/'worker.py'
        target.write_text((source/'worker.py').read_text())
        (source/'worker.py').unlink()
        try:
            (source/'worker.py').symlink_to(target)
        except OSError:
            pytest.skip('Platform cannot create symlinks')

    def forbidden(*args, **kwargs):
        raise AssertionError('Qualification dispatched before refusing the install')

    monkeypatch.setattr(qualifier.subprocess, 'run', forbidden)
    output = tmp_path/'uncreated-output'
    with pytest.raises(ValueError):
        qualifier.qualify(output)
    assert not output.exists()


def probe_bytes(qualifier, case):
    """Existing-child probe payloads; no probe or native process is executed."""
    if case == 'missing':
        return None
    if case == 'malformed':
        return b'{"steps": {"discovery": '
    if case == 'nonobject':
        return b'[]'
    if case == 'invalid-utf8':
        return b'\xff'
    steps = {name: {'outcome': 'passed'} for name in qualifier.PROBE_STEPS}
    if case == 'partial':
        steps = {'discovery': steps['discovery']}
    elif case == 'failed':
        steps['bootstrap']['outcome'] = 'failed: injected'
    elif case == 'bad-steps':
        steps = []
    elif case == 'bad-step':
        steps['discovery'] = None
    return json.dumps({'schema_version': 1, 'steps': steps}).encode()


@pytest.mark.parametrize('pytest_exit,memory_exit,probe,expected', [
    (0, 0, 'passed', 0), (0, 3, 'passed', 3),
    (0, 0, 'missing', 1), (0, 0, 'failed', 1),
    (5, 0, 'passed', 5), (5, 3, 'missing', 5),
    *[(0, 0, state, 1) for state in ('partial', 'malformed', 'nonobject',
                                   'invalid-utf8', 'bad-steps', 'bad-step', 'unreadable')],
])
def test_receipt_exit_matches_final_verdict(tmp_path, monkeypatch, pytest_exit, memory_exit, probe, expected):
    qualifier = load('qualify_platform')
    source = tmp_path/'installed'
    source.mkdir()
    monkeypatch.setattr(qualifier, 'installed_source', lambda: source)
    monkeypatch.setattr(qualifier.importlib.metadata, 'version', lambda _: '1.3.0')
    output = tmp_path/'qualification'
    calls = []
    original_read_text = Path.read_text
    def read_text(path, *args, **kwargs):
        if probe == 'unreadable' and path == output/'plugin-probe.json':
            raise PermissionError(13, 'injected existing probe read failure')
        return original_read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read_text)

    def run(argv, **kwargs):
        calls.append(tuple(argv))
        if '-m' in argv and 'pytest' in argv:
            payload = probe_bytes(qualifier, probe)
            if payload is not None:
                (output/'plugin-probe.json').write_bytes(payload)
            return subprocess.CompletedProcess(argv, pytest_exit)
        if memory_exit == 0:
            memory = {'native_reader': 'available',
                      'tiers_read': ['raw', 'personal', 'curated'],
                      'reader_named': 'native'}
            journey = {'accept': 'accepted', 'build': 'completed', 'review': 'completed'}
            (output/'memory-redis.json').write_text(json.dumps({'memory': memory, 'journey': journey}))
        return subprocess.CompletedProcess(argv, memory_exit, stdout='injected', stderr='')

    monkeypatch.setattr(qualifier.subprocess, 'run', run)
    observed = qualifier.qualify(output)
    receipt = json.loads((output/'platform.json').read_text())
    assert observed == receipt['exit'] == expected
    assert receipt['pytest_exit'] == pytest_exit
    assert receipt['status'] == ('checks_passed' if expected == 0 else 'failed')
    assert len(calls) == (1 if pytest_exit else 2)
    assert calls[0][1:3] == ('-m', 'pytest')
    if pytest_exit == 0:
        assert str(ROOT/'scripts/check_installed.py') in calls[1]
    if probe in ('passed', 'partial', 'failed'):
        assert receipt['plugin_probe'] == json.loads(probe_bytes(qualifier, probe))
    elif probe == 'missing':
        assert receipt['plugin_probe'].startswith('missing:')
    else:
        assert receipt['plugin_probe'].startswith('unreadable:')


@pytest.mark.parametrize('name', ['check_installed', 'qualify_platform'])
@pytest.mark.parametrize('optimization,flag', [(1, 0), (0, 1)])
def test_optimized_driver_function_refuses_before_effects(tmp_path, name, optimization, flag):
    path = ROOT/'scripts'/f'{name}.py'
    namespace = {'__name__': 'optimized_guard_test', '__file__': str(path)}
    exec(compile(path.read_text(), str(path), 'exec', optimize=optimization), namespace)
    namespace['sys'] = SimpleNamespace(flags=SimpleNamespace(optimize=flag))

    def forbidden(*args, **kwargs):
        raise AssertionError('Optimized checks performed an effect')

    namespace['gui_release_checks'] = forbidden
    namespace['installed_source'] = forbidden
    output = tmp_path/'uncreated-output'
    with pytest.raises(ValueError, match='unoptimized Python'):
        if name == 'check_installed':
            namespace['check'](Path(sys.executable), 'core')
        else:
            namespace['qualify'](output)
    assert not output.exists()


@pytest.mark.parametrize('name', ['check_installed', 'qualify_platform'])
@pytest.mark.parametrize('selection', ['flag', 'environment'])
def test_optimized_cli_refuses_without_receipt(tmp_path, name, selection):
    output = tmp_path/'uncreated-output'
    options = (['--output', str(output)] if name == 'qualify_platform' else
               ['--python', str(tmp_path/'missing-python'), '--mode', 'core', '--report', str(output)])
    flags = ['-O'] if selection == 'flag' else []
    env = dict(os.environ, PYTHONOPTIMIZE='1' if selection == 'environment' else '0')
    result = subprocess.run([sys.executable, *flags, str(ROOT/'scripts'/f'{name}.py'), *options],
                            cwd=tmp_path, env=env, text=True, capture_output=True,
                            timeout=30 if sys.platform == 'win32' else 10)
    assert result.returncode != 0
    assert 'require' in result.stderr and 'unoptimized Python' in result.stderr
    assert not result.stdout and not output.exists()


@pytest.mark.parametrize('platform,expected_timeout', [('win32', 30), ('linux', 10), ('darwin', 10)])
@pytest.mark.parametrize('name', ['check_installed', 'qualify_platform'])
@pytest.mark.parametrize('selection', ['flag', 'environment'])
def test_optimized_cli_deadline_is_platform_specific(tmp_path, monkeypatch, platform,
                                                    expected_timeout, name, selection):
    calls = []

    def child(argv, **kwargs):
        calls.append(argv)
        assert kwargs['timeout'] == expected_timeout
        assert kwargs['cwd'] == tmp_path
        assert kwargs['text'] is True and kwargs['capture_output'] is True
        assert kwargs['env']['PYTHONOPTIMIZE'] == ('1' if selection == 'environment' else '0')
        assert ('-O' in argv) == (selection == 'flag')
        return SimpleNamespace(returncode=1, stderr='requires unoptimized Python', stdout='')

    # Replace this test module's bindings, not the host interpreter's platform.
    monkeypatch.setitem(globals(), 'sys', SimpleNamespace(executable=sys.executable, platform=platform))
    monkeypatch.setitem(globals(), 'subprocess', SimpleNamespace(run=child))
    test_optimized_cli_refuses_without_receipt(tmp_path, name, selection)
    assert len(calls) == 1


@pytest.mark.parametrize('pytest_outcome', [1, 2, 'timeout'])
@pytest.mark.parametrize('instrumented', [False, True])
@pytest.mark.parametrize('probe_case', ['passed', 'partial', 'failed', 'missing', 'malformed',
                                      'nonobject', 'bad-steps', 'bad-step', 'unreadable', 'invalid-utf8'])
def test_unsuccessful_platform_suite_stops_before_post_suite_native_dispatch(
        wheel_install, tmp_path, monkeypatch, pytest_outcome, instrumented, probe_case):
    """Actual qualifier orchestration, with every child dispatch intercepted."""
    qualifier = load('qualify_platform')
    monkeypatch.setattr(qualifier, 'platform', SimpleNamespace(
        system=lambda: 'Windows', machine=lambda: 'AMD64',
        python_version=lambda: '3.12-control'))
    output = tmp_path/'qualification-failed-suite'
    original_xml = (
        b'<testsuites><testsuite tests="1" failures="1" errors="0" skipped="0">'
        b'<testcase name="original_immediate_child_wait"><properties>'
        b'<property name="runner_terminal_cleanup" '
        b'value="{&quot;resources_unconfirmed&quot;: true}"/></properties>'
        b'<failure>original immediate wait was258; retain this first failure</failure>'
        b'</testcase></testsuite></testsuites>')
    original_log = b'original immediate wait failure; disposal unconfirmed\n'
    calls = []
    expected_timeout = 2520 if instrumented else 1800
    payload = probe_bytes(qualifier, probe_case)
    original_read_text = Path.read_text
    def read_text(path, *args, **kwargs):
        if probe_case == 'unreadable' and path == output/'plugin-probe.json':
            raise PermissionError(13, 'injected existing probe read failure')
        return original_read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read_text)

    def child(argv, **kwargs):
        if calls:
            raise AssertionError('post-suite child dispatched after unsuccessful pytest')
        calls.append(tuple(argv))
        assert argv[1:3] == ['-m', 'pytest']
        assert kwargs['timeout'] == expected_timeout
        assert kwargs['env']['HARNESS_QUALIFICATION_OUTPUT'] == str(output)
        assert kwargs['cwd'] == output
        (output/'tests.xml').write_bytes(original_xml)
        kwargs['stdout'].write(original_log)
        kwargs['stdout'].flush()
        if payload is not None:
            (output/'plugin-probe.json').write_bytes(payload)
        if pytest_outcome == 'timeout':
            raise subprocess.TimeoutExpired(argv, expected_timeout)
        return subprocess.CompletedProcess(argv, pytest_outcome)

    # Replace the driver's binding, not the host subprocess module or OS identity.
    monkeypatch.setattr(qualifier, 'subprocess', SimpleNamespace(
        run=child, CompletedProcess=subprocess.CompletedProcess,
        TimeoutExpired=subprocess.TimeoutExpired, STDOUT=subprocess.STDOUT))
    expected_exit = 124 if pytest_outcome == 'timeout' else pytest_outcome
    observed = qualifier.qualify(output, coverage_instrumented=instrumented)
    receipt = json.loads((output/'platform.json').read_text())
    assert observed == receipt['exit'] == receipt['pytest_exit'] == expected_exit
    assert len(calls) == 1 and receipt['command'] == list(calls[0])
    assert receipt['suite_timeout_seconds'] == expected_timeout
    assert (output/'tests.xml').read_bytes() == original_xml
    assert (output/'tests.txt').read_bytes() == original_log
    assert all(receipt[name] == 'unrun'
               for name in ('memory_redis', 'native_memory_reader', 'r2_journey'))
    assert receipt['status'] == ('instrumented_failed' if instrumented else 'failed')
    assert receipt['native_process_and_recovery'] == (
        'not_qualified_instrumented' if instrumented else 'failed')
    assert not (output/'memory-redis.json').exists()
    assert not (output/'memory-redis.txt').exists()
    if pytest_outcome == 'timeout':
        assert receipt['failure'] == 'suite_timeout'
    else:
        assert 'failure' not in receipt

    if payload is None:
        assert not (output/'plugin-probe.json').exists()
        assert receipt['plugin_probe'].startswith('missing:')
        assert 'plugin probe receipt missing' in receipt['checks']
    else:
        assert (output/'plugin-probe.json').read_bytes() == payload
        if probe_case in ('passed', 'partial', 'failed'):
            assert receipt['plugin_probe'] == json.loads(payload)
            if probe_case == 'partial':
                assert any('missing ' in check for check in receipt['checks'])
            if probe_case == 'failed':
                assert receipt['plugin_probe']['steps']['bootstrap']['outcome'] == 'failed: injected'
        else:
            assert receipt['plugin_probe'].startswith('unreadable:')
            assert 'plugin probe receipt unreadable; see plugin-probe.json' in receipt['checks']


def listing_control(monkeypatch, *, observed=True, mode='changed', record=None, **bounds):
    """Portable forwarding control over the actual listing/stat implementations."""
    from attune_harness.windows_reads import ReadRoot
    from windows_read_witness import ListingWitness
    calls, records = [], []
    refusal = OSError('synthetic original observation failure')
    class API:
        Basic = SimpleNamespace
        def __init__(self):
            self.calls, self.creations = [], [1] * 3 + ([1] * 3 if mode == 'stable' else [9] * 3)
            self.info_calls, self.volume_result, self.child_result = 0, 1, 2
            self.barrier = None
        def volume_handle(self, anchor):
            self.calls.append(('volume', anchor)); return self.volume_result
        def child(self, parent, name, **kwargs):
            self.calls.append(('child', parent, name, kwargs)); return self.child_result
        def info(self, handle, kind, cls):
            self.calls.append(('info', handle, kind, cls)); self.info_calls += 1
            if (mode == 'first_stat' and self.info_calls == 1) or (mode == 'second_stat' and self.info_calls == 4):
                raise refusal
            return SimpleNamespace(CreationTime=self.creations.pop(0), LastAccessTime=1,
                                   LastWriteTime=2, ChangeTime=3, FileAttributes=16)
        def metadata(self, handle, parent_identity=None):
            self.calls.append(('metadata', handle, parent_identity)); basic = self.info(handle, self.Basic, 0)
            return {'attributes': basic.FileAttributes, 'kind': 'directory',
                    'nested': {'value': basic.CreationTime}}, 12, True
        def iter_names(self, handle):
            self.calls.append(('iter_names', handle))
            if self.barrier is not None: self.barrier.wait(timeout=5)
            if mode == 'enumeration': raise refusal
            return ('leaf',)
    class Reader:
        def __init__(self, api): self._api, self.result, self.error, self.first, self.stats = api, None, None, None, 0
        def _stat(self, handle, *args, **kwargs):
            result = ReadRoot._stat(self, handle, *args, **kwargs); self.stats += 1
            if self.stats == 1: self.first = result
            elif mode == 'mutate_before_return': self.first.entry['nested']['value'] = 2
            return result
        def _listing(self, handle):
            try:
                self.result = ReadRoot._listing(self, handle)
                return self.result
            except Exception as error:
                self.error = error
                raise
    recorder = record if record is not None else lambda key, value: records.append((key, value))
    observer = ListingWitness(monkeypatch, recorder, Reader, API, **bounds) if observed else None
    api = API(); parent = api.volume_handle('C:\\'); handle = api.child(parent, 'fixture', writable=False)
    return SimpleNamespace(observer=observer, root=Reader(api), handle=handle, records=records,
                           error=refusal, api_type=API, reader_type=Reader)


@pytest.mark.parametrize('mode', ['stable', 'changed'])
def test_listing_witness_preserves_original_call_map_return_and_exception(monkeypatch, mode):
    baseline = listing_control(monkeypatch, observed=False, mode=mode)
    actual = listing_control(monkeypatch, mode=mode)
    if mode == 'stable':
        expected = baseline.root._listing(baseline.handle)
        result = actual.root._listing(actual.handle)
        assert result is actual.root.result and result == expected and actual.records == []
    else:
        with pytest.raises(ValueError, match='Source directory changed'):
            baseline.root._listing(baseline.handle)
        with pytest.raises(ValueError, match='Source directory changed') as caught:
            actual.root._listing(actual.handle)
        assert caught.value is actual.root.error
        record = json.loads(actual.records[0][1])
        assert record['path'] == 'C:\\fixture' and record['complete_pair']
        assert [x['times']['creation'] for x in record['states']] == [1, 9]
    assert actual.root._api.calls == baseline.root._api.calls
    assert [x[0] for x in actual.root._api.calls] == [
        'volume', 'child', 'info', 'metadata', 'info', 'info', 'iter_names',
        'info', 'metadata', 'info', 'info']
    assert actual.observer.frames() == []


@pytest.mark.parametrize('mode,count', [('first_stat', 0), ('enumeration', 1), ('second_stat', 1)])
def test_listing_witness_marks_incomplete_original_observations(monkeypatch, mode, count):
    baseline = listing_control(monkeypatch, observed=False, mode=mode)
    actual = listing_control(monkeypatch, mode=mode)
    with pytest.raises(OSError) as first: baseline.root._listing(baseline.handle)
    with pytest.raises(OSError) as caught: actual.root._listing(actual.handle)
    assert first.value is baseline.error and caught.value is actual.error
    assert actual.root._api.calls == baseline.root._api.calls
    record = json.loads(actual.records[0][1])
    assert not record['complete_pair'] and len(record['states']) == count
    assert record['error_type'] == 'OSError' and actual.observer.frames() == []


def test_listing_witness_copies_nested_states_at_the_original_return(monkeypatch):
    actual = listing_control(monkeypatch, mode='mutate_before_return')
    with pytest.raises(ValueError): actual.root._listing(actual.handle)
    record = json.loads(actual.records[0][1])
    assert actual.root.first.entry['nested']['value'] == 2
    assert [x['entry']['nested']['value'] for x in record['states']] == [1, 9]


def test_listing_witness_sink_failure_does_not_replace_original_refusal(monkeypatch):
    def broken(*args): raise RuntimeError('synthetic diagnostic sink failure')
    actual = listing_control(monkeypatch, record=broken)
    with pytest.raises(ValueError, match='Source directory changed') as caught:
        actual.root._listing(actual.handle)
    assert caught.value is actual.root.error
    assert actual.observer.diagnostic_errors == ['RuntimeError'] and actual.observer.frames() == []


def test_listing_witness_isolates_interleaved_same_handle_readers(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    actual = listing_control(monkeypatch)
    second_api = actual.api_type(); second_api.creations = [10] * 3 + [90] * 3
    parent = second_api.volume_handle('D:\\'); second_handle = second_api.child(parent, 'other', writable=False)
    second = actual.reader_type(second_api)
    barrier = Barrier(2); actual.root._api.barrier = second_api.barrier = barrier
    def call(reader, handle):
        try: reader._listing(handle)
        except ValueError as error: return error
        raise AssertionError('Original changed directory was not refused')
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda pair: call(*pair), [(actual.root, actual.handle), (second, second_handle)]))
    assert values == [actual.root.error, second.error]
    records = [json.loads(value) for _, value in actual.records]
    assert len({x['thread'] for x in records}) == len({x['invocation'] for x in records}) == 2
    assert {x['path']: [s['times']['creation'] for s in x['states']] for x in records} == {
        'C:\\fixture': [1, 9], 'D:\\other': [10, 90]}


def test_listing_witness_bounds_records_and_relabels_reused_handles(monkeypatch):
    actual = listing_control(monkeypatch, max_records=2)
    api = actual.root._api
    for n in range(300):
        api.volume_result = n + 10; api.volume_handle('X:' + str(n))
    assert len(actual.observer.labels) <= 256
    api.volume_result = 1; api.child_result = 2
    api.volume_handle('Z:\\'); api.child(1, 'fresh', writable=False)
    for _ in range(3):
        api.creations = [1] * 3 + [9] * 3
        with pytest.raises(ValueError): actual.root._listing(actual.handle)
    assert len(actual.records) == 2 and actual.observer.truncated
    assert all(json.loads(value)['path'] == 'Z:\\fresh' for _, value in actual.records)


def test_listing_witness_explicitly_refuses_missing_owner_without_changing_default(monkeypatch):
    from windows_read_witness import ListingWitness
    from test_windows_read_witness_diagnostics import Root, API
    with pytest.raises(ValueError, match='original listing owner'):
        ListingWitness(monkeypatch, lambda *args: None, Root, API)


def test_listing_witness_default_plugin_path_performs_no_diagnostic_setup(monkeypatch):
    plugin = load('harness_qualification_stacks')
    def forbidden(*args): raise AssertionError('Default path performed diagnostic setup')
    monkeypatch.setattr(plugin, '_listing_witness_types', forbidden)
    config = SimpleNamespace()
    plugin._configure_listing_witness(config)
    plugin._close_listing_witness(config)
    assert not hasattr(config, '_harness_listing_witness')


@pytest.mark.parametrize('installed', [False, True])
def test_listing_option_cannot_enable_ordinary_or_posix_qualification(tmp_path, monkeypatch, installed):
    qualifier = load('qualify_platform')
    monkeypatch.setattr(qualifier, 'platform', SimpleNamespace(system=lambda: 'Linux'))
    def forbidden(): raise AssertionError('Unsupported diagnostics reached installed import')
    monkeypatch.setattr(qualifier, 'installed_source', forbidden)
    with pytest.raises(ValueError, match='Windows instrumented'):
        qualifier.qualify(tmp_path / 'uncreated', coverage_instrumented=True,
                          installed_coverage_partitions=installed, windows_listing_witness=tmp_path / 'diagnostics')


def test_listing_observer_missing_label_and_nested_invocation_do_not_cross_pair(monkeypatch):
    actual = listing_control(monkeypatch)
    actual.observer.labels.clear()
    original_iter = actual.root._api.iter_names
    nested = False
    def interleaved(handle):
        nonlocal nested
        if not nested:
            nested = True
            # A separate reader with the same API/handle must have its own frame.
            other = actual.reader_type(actual.root._api)
            try: other._listing(handle)
            except ValueError: pass
        return original_iter(handle)
    actual.root._api.iter_names = interleaved
    actual.root._api.creations = [1] * 3 + [2] * 3 + [3] * 3 + [4] * 3
    with pytest.raises(ValueError): actual.root._listing(actual.handle)
    records = [json.loads(value) for _, value in actual.records]
    assert len(records) == 2 and len({x['invocation'] for x in records}) == 2
    assert all(x['path'] == '<unknown>' and x['complete_pair'] for x in records)
    assert [x['times']['creation'] for x in records[-1]['states']] == [1, 4]
    assert actual.observer.frames() == []


@pytest.mark.parametrize('failure', ['copy', 'json', 'byte_limit'])
def test_listing_diagnostic_representation_failure_is_secondary(monkeypatch, failure):
    actual = listing_control(monkeypatch, **({'max_bytes': 1} if failure == 'byte_limit' else {}))
    if failure == 'copy':
        class Broken:
            def __deepcopy__(self, memo): raise RuntimeError('synthetic copy failure')
        original_metadata = actual.root._api.metadata
        def metadata(handle, *args):
            entry, size, times = original_metadata(handle, *args)
            entry['opaque'] = Broken()
            return entry, size, times
        actual.root._api.metadata = metadata
    elif failure == 'json':
        original_metadata = actual.root._api.metadata
        def metadata(handle, *args):
            entry, size, times = original_metadata(handle, *args)
            entry['opaque'] = object()
            return entry, size, times
        actual.root._api.metadata = metadata
    with pytest.raises(ValueError, match='Source directory changed') as caught:
        actual.root._listing(actual.handle)
    assert caught.value is actual.root.error and actual.observer.frames() == []
    if failure == 'byte_limit':
        assert actual.records == [] and actual.observer.truncated
    elif failure == 'copy':
        record = json.loads(actual.records[0][1])
        assert record['copy_errors'] == ['RuntimeError', 'RuntimeError'] and not record['complete_pair']
    else:
        assert actual.records == [] and actual.observer.diagnostic_errors == ['TypeError']


def test_explicit_listing_plugin_uses_preopened_sink_and_same_original_guard(tmp_path, monkeypatch):
    plugin = load('harness_qualification_stacks')
    measurement = load('measure_coverage')
    actual = listing_control(monkeypatch, observed=False)
    sink = tmp_path / 'precreated.jsonl'; sink.touch()
    context_path = tmp_path / 'context.json'
    context_path.write_text(json.dumps({'workers': [{'listing_witness': str(sink)}], 'context_token': 'synthetic'}))
    options = {'--harness-installed-context': str(context_path), '--harness-shard-index': 0}
    config = SimpleNamespace(option=SimpleNamespace(harness_windows_listing_witness=str(sink)),
                             getoption=options.__getitem__)
    monkeypatch.setattr(plugin, 'os', SimpleNamespace(name='nt'))  # explicit portable adapter, not native Windows
    monkeypatch.setattr(plugin, '_listing_witness_types', lambda: (actual.reader_type, actual.api_type))
    monkeypatch.setitem(sys.modules, 'measure_coverage', measurement)
    plugin._configure_listing_witness(config)
    patch, witness, output = config._harness_listing_witness
    assert output.fd is not None and sink.read_bytes() == b''
    with pytest.raises(ValueError, match='Source directory changed') as caught:
        actual.root._listing(actual.handle)
    assert caught.value is actual.root.error
    calls = list(actual.root._api.calls)
    plugin._close_listing_witness(config)
    assert calls == actual.root._api.calls and output.fd is None
    rows = [json.loads(line) for line in sink.read_text().splitlines()]
    assert [row['event'] for row in rows] == ['windows_listing_refusal', 'windows_listing_summary']
    assert rows[0]['observation']['complete_pair'] and rows[-1]['diagnostic_error_types'] == []


def test_listing_sink_setup_failure_does_not_replace_original_software_outcome(tmp_path, monkeypatch):
    plugin = load('harness_qualification_stacks')
    actual = listing_control(monkeypatch, observed=False)
    sink = tmp_path / 'missing.jsonl'
    context_path = tmp_path / 'context.json'
    context_path.write_text(json.dumps({'workers': [{'listing_witness': str(sink)}], 'context_token': 'synthetic'}))
    options = {'--harness-installed-context': str(context_path), '--harness-shard-index': 0}
    config = SimpleNamespace(option=SimpleNamespace(harness_windows_listing_witness=str(sink)), getoption=options.__getitem__)
    monkeypatch.setattr(plugin, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(plugin, '_listing_witness_types', lambda: (actual.reader_type, actual.api_type))
    plugin._configure_listing_witness(config)
    with pytest.raises(ValueError, match='Source directory changed') as caught:
        actual.root._listing(actual.handle)
    assert caught.value is actual.root.error and not sink.exists()
    plugin._close_listing_witness(config)
    assert not sink.exists()


def configured_listing_sink(tmp_path, monkeypatch):
    plugin, measurement = load('harness_qualification_stacks'), load('measure_coverage')
    actual = listing_control(monkeypatch, observed=False)
    path = tmp_path / 'listing.jsonl'; path.touch()
    context = tmp_path / 'context.json'
    context.write_text(json.dumps({'workers': [{'listing_witness': str(path)}], 'context_token': 'synthetic'}))
    options = {'--harness-installed-context': str(context), '--harness-shard-index': 0}
    config = SimpleNamespace(option=SimpleNamespace(harness_windows_listing_witness=str(path)), getoption=options.__getitem__)
    monkeypatch.setattr(plugin, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(plugin, '_listing_witness_types', lambda: (actual.reader_type, actual.api_type))
    monkeypatch.setitem(sys.modules, 'measure_coverage', measurement)
    plugin._configure_listing_witness(config)
    return plugin, measurement, actual, path, config


@pytest.mark.parametrize('count', [63, 64, 65])
def test_listing_summary_is_reserved_at_refusal_limit(tmp_path, monkeypatch, count):
    plugin, measurement, actual, path, config = configured_listing_sink(tmp_path, monkeypatch)
    for _ in range(count):
        actual.root._api.creations = [1] * 3 + [9] * 3
        with pytest.raises(ValueError): actual.root._listing(actual.handle)
    plugin._close_listing_witness(config)
    rows = [json.loads(row) for row in path.read_text().splitlines()]
    summary = rows[-1]
    assert len(rows) == min(count, 64) + 1
    assert summary['event'] == 'windows_listing_summary'
    assert summary['truncated'] == (count > 64)
    assert summary['delivery_complete'] == (count <= 64)
    assert summary['sink_errors'] == summary['sink_dropped_records'] == summary['sink_short_writes'] == 0
    assert path.stat().st_size <= 1024 * 1024


@pytest.mark.parametrize('fault', ['write_error', 'short_write'])
def test_listing_summary_retains_sink_delivery_failure_and_partial_prefix(tmp_path, monkeypatch, fault):
    plugin, measurement, actual, path, config = configured_listing_sink(tmp_path, monkeypatch)
    original = measurement.os.write
    def failed(fd, raw):
        if fault == 'write_error': raise OSError('synthetic sink refusal')
        return original(fd, raw[:8])
    with monkeypatch.context() as patch:
        patch.setattr(measurement.os, 'write', failed)
        with pytest.raises(ValueError) as caught: actual.root._listing(actual.handle)
        assert caught.value is actual.root.error
    prefix = path.read_bytes()
    plugin._close_listing_witness(config)
    raw = path.read_bytes(); summary = json.loads(raw.splitlines()[-1])
    assert raw.startswith(prefix)
    if fault == 'short_write': assert len(prefix) == 8
    else: assert prefix == b''
    assert summary['event'] == 'windows_listing_summary' and not summary['delivery_complete']
    assert summary['truncated'] and summary['sink_errors'] > 0 and summary['sink_dropped_records'] == 1
    assert summary['sink_short_writes'] == int(fault == 'short_write')
    assert len(raw) <= 1024 * 1024


def test_listing_summary_preserves_one_mib_limit_even_when_payload_byte_budget_is_full(tmp_path, monkeypatch):
    plugin, measurement, actual, path, config = configured_listing_sink(tmp_path, monkeypatch)
    patch, witness, sink = config._harness_listing_witness
    for _ in range(64): sink.emit('synthetic_large_record', payload='x' * 64000)
    plugin._close_listing_witness(config)
    raw = path.read_bytes(); summary = json.loads(raw.splitlines()[-1])
    assert len(raw) <= 1024 * 1024 and summary['event'] == 'windows_listing_summary'
    assert not summary['delivery_complete'] and summary['sink_dropped_records'] > 0


def test_listing_summary_is_incomplete_when_an_original_invocation_remains_active(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    plugin, measurement, actual, path, config = configured_listing_sink(tmp_path, monkeypatch)
    entered, release = Event(), Event()
    original = actual.root._api.iter_names
    def blocked(handle):
        entered.set()
        assert release.wait(5), 'synthetic observer control was not released'
        return original(handle)
    actual.root._api.iter_names = blocked
    def call():
        try: actual.root._listing(actual.handle)
        except ValueError as error: return error
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(call)
        try:
            assert entered.wait(5), 'original listing did not enter'
            plugin._close_listing_witness(config)
            summary = json.loads(path.read_bytes().splitlines()[-1])
            assert summary['active_invocations'] == 1 and summary['truncated'] and not summary['delivery_complete']
        finally:
            release.set()
        assert future.result(timeout=5) is actual.root.error


@pytest.mark.parametrize('fault', ['emit_call', 'field_factory'])
def test_listing_summary_reports_outer_diagnostic_boundary_failure(tmp_path, monkeypatch, fault):
    plugin, measurement, actual, path, config = configured_listing_sink(tmp_path, monkeypatch)
    patch, witness, sink = config._harness_listing_witness
    def broken(*args, **kwargs): raise OSError('synthetic outer diagnostic failure')
    if fault == 'emit_call':
        with monkeypatch.context() as fault_patch:
            fault_patch.setattr(sink, 'emit', broken)
            with pytest.raises(ValueError) as caught: actual.root._listing(actual.handle)
            assert caught.value is actual.root.error
    else:
        assert measurement._diagnostic_call(sink, 'emit', event='synthetic', details=broken) is None
    plugin._close_listing_witness(config)
    summary = json.loads(path.read_bytes().splitlines()[-1])
    assert not summary['delivery_complete'] and summary['truncated']
    assert summary['sink_errors'] > 0 and summary['sink_dropped_records'] == 1
