"""Supplemental coverage in a disposable venv; never a qualification replacement."""
import argparse
import hashlib
import functools
import inspect
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import runpy
import subprocess
import sys
import sysconfig
import time
import threading
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/attune_harness'
VERSION = '7.13.5'
INPUT_TREES = ('tests', 'scripts', 'examples', 'experiments', 'docs',
               'plugin', '.agents', '.claude', '.github/workflows')
IGNORED_INPUT_DIRS = {'__pycache__', '.pytest_cache'}
ROOT_INPUTS = ('pyproject.toml', 'pytest.ini', '.pytest.ini', 'pytest.toml',
               '.pytest.toml', 'tox.ini', 'setup.cfg', 'setup.py', 'conftest.py',
               'MANIFEST.in', 'README.md', 'participants.json',
               'dependency-lock.json', '.github/workflows/coverage.yml')


def hashes(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*.py'))}


def _deadline_kwargs(deadline):
    if deadline is None:
        return {}
    if isinstance(deadline, bool) or not math.isfinite(deadline):
        raise ValueError('Installed-suite deadline must be a finite monotonic clock value')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Shared installed-suite identity deadline expired')
    return {'timeout': min(10, remaining)}


def input_hashes(*, deadline=None):
    """Bind tracked checkout bytes and untracked test/driver/fixture inputs."""
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--cached'], cwd=ROOT,
                                     **_deadline_kwargs(deadline))
    paths = {ROOT / os.fsdecode(name) for name in tracked.split(b'\0') if name}
    for name in INPUT_TREES:
        _deadline_kwargs(deadline)
        tree = ROOT / name
        if tree.is_symlink() or (tree.exists() and not tree.is_dir()):
            raise ValueError('Coverage input tree must be a real directory: ' + str(tree))
        if not tree.exists():
            continue
        for path in sorted(tree.rglob('*')):
            if any(part in IGNORED_INPUT_DIRS for part in path.relative_to(tree).parts):
                continue
            if path.is_symlink():
                raise ValueError('Coverage inputs cannot contain symlinks: ' + str(path))
            if path.is_file():
                paths.add(path)
    paths.update(path for path in (ROOT / name for name in ROOT_INPUTS)
                 if path.exists() or path.is_symlink())
    paths.update(ROOT.glob('requirements*.lock'))
    paths.update(ROOT.glob('requirements*.txt'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Coverage inputs cannot contain symlinks')
    result = {}
    for path in sorted(paths):
        _deadline_kwargs(deadline)
        result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def identity(*, deadline=None):
    return {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                                text=True, **_deadline_kwargs(deadline)).strip(),
            'sources': hashes(SOURCE), 'input_hashes': input_hashes() if deadline is None else input_hashes(deadline=deadline),
            'coverage_version': VERSION, 'pytest_version': importlib.metadata.version('pytest')}


def inputs_stable(frozen, installed):
    try:
        return identity() == frozen and hashes(installed) == frozen['sources']
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False


def compatible(receipts, expected):
    for receipt in receipts:
        if any(receipt.get(key) != value for key, value in expected.items()):
            raise ValueError('Coverage requires matching revision, source and executed input bytes, and tool versions')
        if receipt.get('test_exit') != 0 or receipt.get('input_drift') is not False:
            raise ValueError('Cannot combine a failed, unfinished or input-drifted test run')


def configuration(output, aliases):
    # Include both source and wheel at collection; combine maps identical wheel
    # bytes back to the checkout. No production module or branch is excluded.
    paths = [SOURCE.as_posix(), *dict.fromkeys(aliases)]
    config = output / 'coverage.ini'
    config.write_text('[run]\nbranch = true\nparallel = true\ndisable_warnings = no-data-collected\ndata_file = '
                      + (output / '.coverage').as_posix() + '\nsource =\n    '
                      + '\n    '.join(paths) + '\n[paths]\npackage =\n    '
                      + '\n    '.join(paths) + '\n', encoding='utf-8')
    return config


# Diagnostic clocks are independent of tests replacing the shared time module.
_diagnostic_clock_ns = time.monotonic_ns
_diagnostic_run_lock = threading.Lock()
_child_diagnostic_context = _child_diagnostic_sink = None


class _DiagnosticSink:
    """Best-effort append to an owned precreated file; never create during tests."""

    def __init__(self, path, token, role, *, max_rows=64, max_bytes=32768, max_row=2048,
                 reserve_summary=False):
        self.token, self.role = token, role
        self.creator_pid = os.getpid()
        self.rows = self.bytes = self.errors = self.attempts = 0
        self.dropped = self.short_writes = 0
        self.max_rows, self.max_bytes, self.max_row = max_rows, max_bytes, max_row
        self.summary_bytes = 2048 if reserve_summary else 0
        self.sealed = self.partial_line = False
        self.fd = None
        self.lock = threading.RLock()
        try:
            self.fd = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0))
        except Exception:
            self.errors += 1

    def _write(self, event, fields, *, summary=False):
        # Called under the lock. Preserve any old partial prefix; a delimiter
        # lets a later complete summary remain independently readable.
        try:
            data = (json.dumps({'schema_version': 1, 'event': event,
                'run_token': self.token, 'role': self.role, 'pid': os.getpid(),
                'ppid': os.getppid(), 'monotonic_ns': _diagnostic_clock_ns(), **fields},
                ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
            if self.partial_line:
                data = b'\n' + data
            limit = self.max_bytes if summary else self.max_bytes - self.summary_bytes
            row_limit = self.summary_bytes if summary else self.max_row
            if self.fd is None or len(data) > row_limit or self.bytes + len(data) > limit:
                self.dropped += 1
                return False
            written = os.write(self.fd, data)
            if type(written) is not int or not 0 <= written <= len(data):
                raise OSError('Invalid diagnostic write count')
            self.bytes += written
            if written != len(data):
                self.errors += 1
                self.short_writes += 1
                self.dropped += 1
                self.partial_line = True
                return False
            self.partial_line = False
            self.rows += 1
            return True
        except Exception:
            self.errors += 1
            self.dropped += 1
            self.partial_line = True
            return False

    def emit(self, event, **fields):
        # A fork may inherit both object and FD. Do not acquire an inherited lock.
        try:
            if os.getpid() != self.creator_pid:
                return False
            with self.lock:
                if self.sealed or self.attempts >= self.max_rows:
                    self.dropped += 1
                    return False
                self.attempts += 1
                return self._write(event, fields)
        except Exception:
            self.errors += 1
            return False

    def finish(self, event, **fields):
        """Use the listing-only reserved row/bytes, even after its payload cap."""
        try:
            if os.getpid() != self.creator_pid:
                return False
            with self.lock:
                if self.sealed or not self.summary_bytes:
                    return False
                self.sealed = True
                incomplete = bool(self.errors or self.dropped or self.short_writes or self.fd is None)
                fields.update(sink_errors=self.errors, sink_dropped_records=self.dropped,
                              sink_short_writes=self.short_writes, sink_payload_attempts=self.attempts,
                              sink_payload_rows=self.rows, sink_bytes_before_summary=self.bytes,
                              record_delimiter_recovery=self.partial_line,
                              delivery_complete=not incomplete and not fields.get('truncated', False))
                fields['truncated'] = bool(fields.get('truncated', False) or incomplete)
                return self._write(event, fields, summary=True)
        except Exception:
            self.errors += 1
            return False

    def close(self):
        try:
            if os.getpid() != self.creator_pid:
                return
            if self.fd is not None:
                os.close(self.fd)
        except Exception:
            self.errors += 1
        self.fd = None


def _prepare_diagnostic_directory(directory, output, names):
    """Create a separate namespace before any observed fixture is running."""
    directory = Path(directory).resolve()
    output = Path(output).resolve()
    if (directory.is_relative_to(output) or output.is_relative_to(directory)
            or directory.is_relative_to(ROOT.resolve()) or ROOT.resolve().is_relative_to(directory)):
        raise ValueError('Diagnostic directory must be separate from evidence, fixtures and checkout')
    directory.mkdir(parents=True, exist_ok=False)
    for name in names:
        with (directory / name).open('xb'):
            pass
    return directory


def _retain_diagnostics(directory, output, names, *, max_bytes):
    """Copy only preselected bounded files after owned processes have reaped."""
    result = {}
    for name in names:
        try:
            with (directory / name).open('rb') as stream:
                raw = stream.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValueError('Diagnostic output exceeded its bound')
            with (output / name).open('xb') as stream:
                stream.write(raw)
            result[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        except Exception as error:
            result[name] = {'error_type': type(error).__name__}
    return result


def _diagnostic_call(target, method, *, event=None, details=None):
    """Contain optional method lookup, field construction and invocation."""
    try:
        operation = getattr(target, method)
        if event is None:
            return operation()
        return operation(event, **({} if details is None else details()))
    except Exception:
        try:
            target.errors += 1
            if method in ('emit', 'finish'):
                target.dropped += 1
                target.partial_line = True
        except Exception:
            pass  # Missing/broken error metadata remains missing, never success.
        return None  # Preserve normal interruption semantics and the owner outcome.


def _configure_child_diagnostics(context):
    global _child_diagnostic_context, _child_diagnostic_sink
    # A direct-child check is repeated on every access, including after fork.
    if os.getppid() != context['parent_pid']:
        return
    _child_diagnostic_context = dict(context)
    _child_diagnostic_sink = _DiagnosticSink(context['child_sink'], context['token'], 'child')


def _child_sink():
    context = _child_diagnostic_context
    if context is None or os.getppid() != context['parent_pid']:
        return None
    sink = _child_diagnostic_sink
    return sink if sink is not None and sink.creator_pid == os.getpid() else None


def _child_diagnostic_event(event, **fields):
    try:
        sink = _child_sink()
        if sink is not None:
            sink.emit(event, **fields)
    except Exception:
        pass  # Diagnostic failures cannot replace the original owner/save result.


def _wrap_coverage_save(save):
    """Forward the SAME bound save; the factory registers no callback."""
    if _child_sink() is None:
        return save
    @functools.wraps(save)
    def observed(*args, **kwargs):
        _child_diagnostic_event('coverage_explicit_save_enter')
        try:
            result = save(*args, **kwargs)
        except BaseException as error:
            _child_diagnostic_event('coverage_explicit_save_error', error_type=type(error).__name__)
            raise
        else:
            _child_diagnostic_event('coverage_explicit_save_return')
            return result
        finally:
            try:
                sink = _child_sink()
                if sink is not None:
                    _diagnostic_call(sink, 'close')
            except Exception:
                pass  # Optional cleanup cannot replace the original save outcome.
    return observed


def _observed_run(argv, *, sink, **kwargs):
    """Forward original run; observe its own timeout/kill/reap path unchanged.

    Enabled only for the single Linux/full parent launcher. The private POSIX
    communicate signature is checked before launch; no concurrent launcher is supported.
    """
    original_run, original_popen = subprocess.run, subprocess.Popen
    if tuple(inspect.signature(original_popen._communicate).parameters) != (
            'self', 'input', 'endtime', 'orig_timeout'):
        raise ValueError('Unsupported stdlib communicate diagnostic boundary')
    if not _diagnostic_run_lock.acquire(blocking=False):
        raise ValueError('Shutdown diagnostics require a single parent launcher')

    class ObservedPopen(original_popen):
        def __init__(self, *args, **kw):
            _diagnostic_call(sink, 'emit', event='parent_launch_begin')
            try:
                super().__init__(*args, **kw)
            except BaseException as error:
                _diagnostic_call(sink, 'emit', event='parent_launch_error', details=lambda error=error: {'error_type': type(error).__name__})
                raise
            _diagnostic_call(sink, 'emit', event='parent_launch_return', details=lambda: {'child_pid': self.pid})

        def communicate(self, input=None, timeout=None):
            _diagnostic_call(sink, 'emit', event='parent_communicate_enter', details=lambda: {'timeout_seconds': timeout})
            try:
                result = super().communicate(input=input, timeout=timeout)
            except BaseException as error:
                _diagnostic_call(sink, 'emit', event='parent_communicate_error', details=lambda error=error: {'error_type': type(error).__name__})
                raise
            _diagnostic_call(sink, 'emit', event='parent_communicate_return', details=lambda: {'returncode': self.returncode})
            return result

        def _communicate(self, input, endtime, orig_timeout):
            _diagnostic_call(sink, 'emit', event='parent_stdlib_deadline', details=lambda: {'deadline_monotonic': endtime, 'timeout_seconds': orig_timeout})
            return super()._communicate(input, endtime, orig_timeout)

        def wait(self, timeout=None):
            _diagnostic_call(sink, 'emit', event='parent_wait_enter', details=lambda: {'timeout_seconds': timeout})
            try:
                result = super().wait(timeout=timeout)
            except BaseException as error:
                _diagnostic_call(sink, 'emit', event='parent_wait_error', details=lambda error=error: {'error_type': type(error).__name__})
                raise
            _diagnostic_call(sink, 'emit', event='parent_wait_return', details=lambda: {'returncode': result})
            return result

        def kill(self):
            _diagnostic_call(sink, 'emit', event='parent_kill_enter')
            try:
                result = super().kill()
            except BaseException as error:
                _diagnostic_call(sink, 'emit', event='parent_kill_error', details=lambda error=error: {'error_type': type(error).__name__})
                raise
            _diagnostic_call(sink, 'emit', event='parent_kill_return', details=lambda: {'returncode': self.returncode})
            return result

        def __exit__(self, exc_type, value, traceback):
            _diagnostic_call(sink, 'emit', event='parent_context_exit_enter', details=lambda: {'error_type': None if exc_type is None else exc_type.__name__})
            try:
                result = super().__exit__(exc_type, value, traceback)
            except BaseException as error:
                _diagnostic_call(sink, 'emit', event='parent_context_exit_error', details=lambda error=error: {'error_type': type(error).__name__})
                raise
            _diagnostic_call(sink, 'emit', event='parent_context_exit_return', details=lambda: {'returncode': self.returncode})
            return result

    try:
        subprocess.Popen = ObservedPopen
        try:
            result = original_run(argv, **kwargs)
        except BaseException as error:
            _diagnostic_call(sink, 'emit', event='parent_run_error', details=lambda error=error: {'error_type': type(error).__name__})
            raise
        _diagnostic_call(sink, 'emit', event='parent_run_return', details=lambda: {'returncode': result.returncode})
        return result
    finally:
        subprocess.Popen = original_popen
        _diagnostic_run_lock.release()


def startup_hook(config, diagnostic_context=None):
    # Runs even with -I or a replaced child environment. -S and forcibly killed
    # processes remain blind spots. Only installed in a dedicated measurement venv.
    code = ('import atexit, coverage\n'
            'if coverage.Coverage.current() is None:\n'
            f'    collector = coverage.Coverage(config_file={str(config)!r})\n'
            '    collector.start()\n'
            '    atexit.register(collector.save)\n')
    if diagnostic_context is not None:
        # Check direct ownership BEFORE importing the stdlib-only helper. An
        # inherited descendant keeps the original save and registration order.
        replacement = ('    save = collector.save\n'
            '    try:\n'
            '        import os\n'
            f'        if os.getppid() == {diagnostic_context["parent_pid"]!r}:\n'
            '            import importlib.util, sys\n'
            f'            spec = importlib.util.spec_from_file_location("harness_coverage_diagnostics", {str(Path(__file__).resolve())!r})\n'
            '            helper = importlib.util.module_from_spec(spec)\n'
            '            sys.modules[spec.name] = helper\n'
            '            spec.loader.exec_module(helper)\n'
            f'            helper._configure_child_diagnostics({diagnostic_context!r})\n'
            '            save = helper._wrap_coverage_save(save)\n'
            '    except Exception:\n'
            '        pass\n'
            '    atexit.register(save)\n')
        code = code.replace('    atexit.register(collector.save)\n', replacement)
    return f'import builtins; exec({code!r})\n'


def report(config, directories=None):
    import coverage
    collector = coverage.Coverage(config_file=str(config))
    collector.combine(data_paths=directories, strict=True, keep=True)
    collector.save()
    output = config.parent
    collector.json_report(outfile=str(output / 'coverage.json'))
    collector.html_report(directory=str(output / 'html'))
    totals = json.loads((output / 'coverage.json').read_text(encoding='utf-8'))['totals']
    summary = {'line_percent': 100 * totals['covered_lines'] / totals['num_statements'],
               'branch_percent': 100 * totals['covered_branches'] / totals['num_branches'],
               'covered_lines': totals['covered_lines'], 'statements': totals['num_statements'],
               'covered_branches': totals['covered_branches'], 'branches': totals['num_branches']}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))


def _validate_partition_junit(folder, selected):
    root = ET.parse(folder / 'tests.xml').getroot()
    suites, cases = list(root.iter('testsuite')), list(root.iter('testcase'))
    keys = ('tests', 'failures', 'errors', 'skipped')
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in keys}
    if (root.tag not in ('testsuites', 'testsuite') or not suites or not cases
            or len(cases) < len(selected)
            or any(int(s.get(key, 0)) < 0 for s in suites for key in keys)
            or counts['failures'] or counts['errors']
            or any(element.tag in ('failure', 'error') for element in root.iter())
            or counts['skipped'] != sum(c.find('skipped') is not None for c in cases)):
        raise ValueError('Partition JUnit does not retain successful selected cases')
    difference = counts['tests'] - len(cases)
    if difference:
        # Pytest 9 counts successful subtests without emitting testcase elements.
        transcript = (folder / 'stdout.txt').read_text(encoding='utf-8')
        summaries = re.findall(r'(?m)^.*\b(\d+) subtests passed.* in [0-9.]+s.*$', transcript)
        if difference < 0 or not summaries or difference != int(summaries[-1]):
            raise ValueError('Partition JUnit count lacks matching passing-subtest summary')


def _darwin_full(output, budget):
    """Share one deadline and retain live diagnostics in an already-uploaded directory."""
    deadline = time.monotonic() + budget
    spec = importlib.util.spec_from_file_location('coverage_source_suite', ROOT / 'scripts/run_source_suite.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # This entire directory is already included by coverage.yml, including
    # partial journals when an outer kill prevents Python finally blocks.
    partitions = output / 'instrumented-platform'
    code = runner.run_suite(partitions, budget, root=ROOT, shards=2, deadline=deadline)
    if code == 0:
        for index in range(2):
            folder = partitions / f'shard-{index}'
            selected = json.loads((folder / 'collection.json').read_text())['selected']
            _validate_partition_junit(folder, selected)
    return code


def _partitioned_full(suite):
    return suite == 'full' and platform.system() == 'Darwin'


def _prepare_installed_runtime(output):
    """Keep Windows fixture and consumer writes outside measured evidence."""
    candidate = output.with_name(output.name + '-runtime')
    runtime = candidate.resolve()
    evidence = output.resolve()
    checkout = ROOT.resolve()
    if (runtime.is_relative_to(evidence) or evidence.is_relative_to(runtime)
            or runtime.is_relative_to(checkout) or checkout.is_relative_to(runtime)):
        raise ValueError('Installed runtime must be outside evidence and checkout ancestry')
    candidate.mkdir(exist_ok=False)
    return runtime


def _validate_installed_aggregate(output, frozen, runtime_root=None):
    """Read back the completed parent's proof without extending its test deadline."""
    folder = output / 'instrumented-platform'
    receipt = json.loads((folder / 'installed-suite.json').read_text(encoding='utf-8'))
    raw = (folder / 'partition-context.json').read_bytes()
    context = json.loads(raw)
    context['context_sha256'] = hashlib.sha256(raw).hexdigest()
    qualifier = runpy.run_path(str(ROOT / 'scripts/qualify_platform.py'))
    qualifier['validate_installed_parent_receipt'](receipt, context, successful=True)
    if context['budget_seconds'] != 2520 or context['identity']['measurement'] != frozen:
        raise ValueError('Installed aggregate differs from the measurement budget or inputs')
    if runtime_root is not None:
        runtime = Path(runtime_root).resolve()
        evidence = output.resolve()
        if runtime.is_relative_to(evidence) or evidence.is_relative_to(runtime):
            raise ValueError('Installed runtime overlaps measured evidence ancestry')
        qualifier['validate_installed_namespace'](context, evidence_root=folder, runtime_root=runtime_root)
        copied_context = Path(context['namespace']['consumer_artifact_root']) / 'partition-context.json'
        if copied_context.read_bytes() != raw:
            raise ValueError('Retained consumer context differs from its original input bytes')
    # Active verification already finished under the serialized shared deadline.
    # This is static proof readback after the parent's once-only postchecks.
    accounting = qualifier['verify_installed_partitions'](folder, context, None, parent_receipt=receipt)
    if (accounting != receipt['accounting']
            or hashlib.sha256((folder / 'plugin-probe.json').read_bytes()).hexdigest()
            != accounting['plugin_probe_sha256']):
        raise ValueError('Installed aggregate or copied probe differs from child evidence')
    return accounting


def measure(output, suite, *, windows_listing_witness=None, shutdown_boundary_diagnostics=None):
    if windows_listing_witness is not None and (suite != 'platform' or platform.system() != 'Windows'):
        raise ValueError('Listing diagnostics require Windows instrumented installed partitions')
    if shutdown_boundary_diagnostics is not None and (suite != 'full' or platform.system() != 'Linux'):
        raise ValueError('Shutdown diagnostics require Linux full measurement')
    if sys.prefix == sys.base_prefix:
        raise ValueError('Use a dedicated disposable virtualenv')
    import attune_harness
    installed = Path(attune_harness.__file__).resolve().parent
    if installed == SOURCE or hashes(installed) != hashes(SOURCE):
        raise ValueError('Install a wheel with exactly the current source bytes')
    frozen = identity()
    hook = Path(sysconfig.get_path('purelib')) / 'harness_measure_coverage.pth'
    if hook.exists():
        raise ValueError('Measurement hook already exists; use a fresh virtualenv')
    output.mkdir(parents=True, exist_ok=False)
    installed_partitions = suite == 'platform' and platform.system() == 'Windows'
    temporary = _prepare_installed_runtime(output) if installed_partitions else output / 'tmp'
    if not installed_partitions:
        temporary.mkdir()
    config = configuration(output, [installed.as_posix()])
    receipt = {**frozen, 'system': platform.system(), 'python': platform.python_version(),
               'suite': suite, 'aliases': [SOURCE.as_posix(), installed.as_posix()],
               'test_exit': None, 'input_drift': True,
               'limits': ['no-site (-S) children', 'abrupt termination before save',
                          'instrumented run is not platform qualification']}
    manifest = output / 'manifest.json'
    def save():
        manifest.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    partitioned = _partitioned_full(suite)
    if partitioned:
        receipt['execution_topology'] = 'two_supervised_module_partitions'
        receipt['shared_test_budget_seconds'] = 1500
        receipt['partition_evidence'] = [f'instrumented-platform/shard-{index}' for index in range(2)]
        receipt['partition_supervisor'] = 'instrumented-platform/source-suite.json'
    if installed_partitions:
        receipt['execution_topology'] = 'two_supervised_installed_module_partitions'
        receipt['installed_runtime_root'] = str(temporary)
        receipt['shared_test_budget_seconds'] = 2520
        receipt['partition_evidence'] = [f'instrumented-platform/shard-{index}' for index in range(2)]
        receipt['partition_supervisor'] = 'instrumented-platform/installed-suite.json'
    diagnostic_context = diagnostic_directory = parent_sink = None
    diagnostic_names = ('shutdown-parent.jsonl', 'shutdown-child.jsonl')
    if shutdown_boundary_diagnostics is not None:
        diagnostic_directory = _prepare_diagnostic_directory(shutdown_boundary_diagnostics, output, diagnostic_names)
        diagnostic_context = {'parent_pid': os.getpid(), 'token': os.urandom(16).hex(),
                              'child_sink': str(diagnostic_directory / diagnostic_names[1])}
        parent_sink = _DiagnosticSink(diagnostic_directory / diagnostic_names[0],
                                      diagnostic_context['token'], 'parent')
        receipt['shutdown_diagnostics'] = 'opt-in owner boundaries; not process completion or a cause'
    save()
    argv = ([sys.executable, '-m', 'pytest', '-q', '-p', 'harness_qualification_stacks',
             '-o', 'faulthandler_timeout=0', '--junitxml=' + str(output / 'tests.xml')]
            if suite == 'full' else
            [sys.executable, '-I', str(ROOT / 'scripts/qualify_platform.py'),
             '--output', str(output / 'instrumented-platform'), '--coverage-instrumented'])
    if installed_partitions:
        argv.append('--installed-coverage-partitions')
        if windows_listing_witness is not None:
            argv += ['--windows-listing-witness', str(windows_listing_witness)]
    environment = {**os.environ, 'TMPDIR': str(temporary), 'TMP': str(temporary),
                   'TEMP': str(temporary), 'PYTHONUTF8': '1'}
    if suite == 'full':
        # Retain the active case/phase even when the independent outer deadline
        # kills pytest before it writes JUnit. Reuse qualification's Python
        # watchdog; the native timed frame walker is deliberately disabled.
        environment['HARNESS_QUALIFICATION_OUTPUT'] = str(output)
        environment['PYTHONPATH'] = os.pathsep.join(filter(None, (
            str(ROOT / 'scripts'), environment.get('PYTHONPATH', ''))))
    stream = hook.open('x', encoding='utf-8')
    try:
        with stream:
            stream.write(startup_hook(config) if diagnostic_context is None else startup_hook(config, diagnostic_context))
        with (output / 'tests.txt').open('w', encoding='utf-8') as log:
            if partitioned:
                log.write('Two supervised module partitions; see instrumented-platform/shard-* diagnostics.\n')
                log.flush()
                receipt['test_exit'] = _darwin_full(output, 1500)
            else:
                launcher = subprocess.run if parent_sink is None else functools.partial(_observed_run, sink=parent_sink)
                run = launcher(argv, cwd=ROOT, env=environment, stdout=log,
                                     stderr=subprocess.STDOUT,
                                     timeout=(2700 if platform.system() == 'Windows' else 1080)
                                     if suite == 'platform' else
                                     (1500 if platform.system() == 'Darwin' else 1200))
                receipt['test_exit'] = run.returncode
    finally:
        if parent_sink is not None:
            _diagnostic_call(parent_sink, 'close')
            try:
                receipt['shutdown_diagnostic_files'] = _retain_diagnostics(
                    diagnostic_directory, output, diagnostic_names, max_bytes=32768)
            except Exception as error:
                receipt['shutdown_diagnostic_files'] = {'retention_error_type': type(error).__name__}
        hook.unlink(missing_ok=True)
        receipt['input_drift'] = not inputs_stable(frozen, installed)
        save()
    if (partitioned or installed_partitions) and (receipt['test_exit'] != 0 or receipt['input_drift']):
        return receipt['test_exit'] or 1
    if installed_partitions:
        try:
            receipt['partition_accounting'] = _validate_installed_aggregate(output, frozen, temporary)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            receipt.update(test_exit=1, aggregate_failure=type(error).__name__)
            save()
            return 1
        save()
    report(config)
    return 1 if receipt['input_drift'] else receipt['test_exit']


def combine(output, directories):
    receipts = [json.loads((p / 'manifest.json').read_text(encoding='utf-8')) for p in directories]
    expected = identity()
    compatible(receipts, expected)
    output.mkdir(parents=True, exist_ok=False)
    aliases = [path for receipt in receipts for path in receipt['aliases']]
    config = configuration(output, aliases)
    report(config, [str(p / '.coverage') for p in directories])
    (output / 'manifest.json').write_text(json.dumps({**expected, 'test_exit': 0,
        'input_drift': False, 'inputs': receipts}, indent=2) + '\n', encoding='utf-8')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--suite', choices=['full', 'platform'], default='full')
    parser.add_argument('--combine', type=Path, nargs='+')
    parser.add_argument('--windows-listing-witness', type=Path,
                        help='Opt-in listing samples in a fresh external diagnostic directory')
    parser.add_argument('--shutdown-boundary-diagnostics', type=Path,
                        help='Opt-in Linux/full owner boundaries in a fresh external directory')
    args = parser.parse_args()
    if importlib.metadata.version('coverage') != VERSION:
        raise ValueError('Install coverage==' + VERSION)
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Keep coverage evidence outside the measured checkout')
    if args.combine and (args.windows_listing_witness is not None or args.shutdown_boundary_diagnostics is not None):
        raise ValueError('Diagnostic options apply only to a new measurement')
    options = {}
    if args.windows_listing_witness is not None:
        options['windows_listing_witness'] = args.windows_listing_witness
    if args.shutdown_boundary_diagnostics is not None:
        options['shutdown_boundary_diagnostics'] = args.shutdown_boundary_diagnostics
    return combine(output, args.combine) if args.combine else measure(output, args.suite, **options)


if __name__ == '__main__':
    raise SystemExit(main())
