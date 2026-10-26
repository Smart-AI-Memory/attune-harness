"""Retain slow-test Python stacks without a native asynchronous frame walk.

This watchdog needs the GIL: it cannot diagnose a C extension that holds it.
The qualifier's separate process budget still terminates such a stuck suite.
"""
from concurrent.futures import TimeoutError as FutureTimeoutError
import json
import functools
import hashlib
import os
from pathlib import Path
import runpy
import sys
import threading
import tempfile
import time

import pytest

# Keep journal time independent of tests replacing the shared time module.
_monotonic = time.monotonic
_stack_write_lock = threading.Lock()
MAX_FAILURE_RECORDS = 64
MAX_FAILURE_BYTES = 1024 * 1024
MAX_FAILURE_TEXT = 4096
MAX_FAILURE_NODE = 1024


def pytest_addoption(parser):
    parser.addini('harness_stack_timeout', 'Seconds before retaining slow-test stacks',
                  default='60')
    parser.addoption('--harness-shard-index', type=int, default=0)
    parser.addoption('--harness-shard-count', type=int, default=1)
    parser.addoption('--harness-installed-context', default=None)
    parser.addoption('--harness-windows-listing-witness', default=None)


def _installed_witness(config, *, finished=False):
    """Run the installed-wheel guard in this pytest process, before and after tests."""
    path = config.getoption('--harness-installed-context')
    if path is None:
        return
    output = Path(os.environ['HARNESS_QUALIFICATION_OUTPUT'])
    target = output / 'installed-identity.json'
    witness = json.loads(target.read_text(encoding='utf-8')) if finished else {'schema_version': 1}
    try:
        raw = Path(path).read_bytes()
        context = json.loads(raw)
        index = config.getoption('--harness-shard-index')
        if context.get('schema_version') != 1 or config.getoption('--harness-shard-count') != 2 or index not in (0, 1):
            raise ValueError('Installed witness requires the two-child context')
        worker = context['workers'][index]
        cwd = str(Path.cwd().resolve())
        temporary = str(Path(tempfile.gettempdir()).resolve())
        if (cwd != worker['cwd'] or temporary != worker['temporary_root']
                or any(str(Path(os.environ[name]).resolve()) != temporary for name in
                       ('TMP', 'TEMP', 'TMPDIR', 'PYTEST_DEBUG_TEMPROOT', 'RUNNER_TEMP'))):
            raise ValueError('Installed child does not own its expected temporary namespace')
        qualifier = runpy.run_path(context['qualifier'])
        qualifier['validate_installed_context'](context)
        if (context['checkout'] != str(qualifier['ROOT'].resolve())
                or str(Path(config.getoption('basetemp')).resolve()) != worker['basetemp']):
            raise ValueError('Installed child checkout or basetemp differs from its context')
        identity = qualifier['installed_partition_identity'](context['deadline_monotonic'])
        if identity != context['identity']:
            raise ValueError('Installed pytest child differs from the frozen wheel or inputs')
        witness.update(status='verified', context_sha256=hashlib.sha256(raw).hexdigest(),
                       consumer_cwd=cwd, temporary_root=temporary, pid=os.getpid(),
                       timing_epoch_monotonic=config._harness_timing_epoch,
                       parent_started_monotonic=context['started_monotonic'],
                       parent_deadline_monotonic=context['deadline_monotonic'])
        witness['after' if finished else 'before'] = identity
    except Exception as error:
        witness.update(status='refused', error_type=type(error).__name__)
        target.write_text(json.dumps(witness, indent=2) + '\n', encoding='utf-8')
        raise
    target.write_text(json.dumps(witness, indent=2) + '\n', encoding='utf-8')


@pytest.hookimpl(hookwrapper=True, tryfirst=True, specname='pytest_collection_modifyitems')
def pytest_installed_collection(config, items):
    # An outer wrapper resumes after pytest's -k/-m and every modifying hook.
    # The source runner keeps its existing trylast hook below.
    yield
    if config.getoption('--harness-installed-context') is None:
        return
    count, index = config.getoption('--harness-shard-count'), config.getoption('--harness-shard-index')
    if count != 2 or index not in (0, 1):
        raise pytest.UsageError('Installed coverage requires exactly two partitions')
    collected = [item.nodeid for item in items]
    selected, deselected = [], []
    for item in items:
        module = item.nodeid.split('::', 1)[0]
        owner = hashlib.sha256(module.encode('utf-8')).digest()[0] % 2
        (selected if owner == index else deselected).append(item)
    manifest = {'schema_version': 1, 'shard': {'index': index, 'count': count},
                'admission': 'post_pytest_selection', 'collected': collected,
                'selected': [item.nodeid for item in selected]}
    with (Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'collection.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=True, allow_nan=False, indent=2)
        stream.write('\n')
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    if config.getoption('--harness-installed-context') is not None:
        return
    count = config.getoption('--harness-shard-count')
    index = config.getoption('--harness-shard-index')
    if count not in (1, 2) or not 0 <= index < count:
        raise pytest.UsageError('Invalid source-suite partition')
    if count == 1:
        return
    collected = [item.nodeid for item in items]
    selected, deselected = [], []
    for item in items:
        module = item.nodeid.split('::', 1)[0]
        owner = hashlib.sha256(module.encode('utf-8')).digest()[0] % count
        (selected if owner == index else deselected).append(item)
    manifest = {'schema_version': 1, 'shard': {'index': index, 'count': count},
                'collected': collected, 'selected': [item.nodeid for item in selected]}
    path = Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'collection.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=True, allow_nan=False, indent=2)
        stream.write('\n')
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)


def _shutdown_owner(function):
    @functools.wraps(function)
    def observed(*args, **kwargs):
        # Diagnostic preparation and emission can fail; the owner stays outside
        # those handlers and is called exactly once with its original arguments.
        helper = config = None
        def emit(event, **fields):
            try:
                if helper is not None:
                    helper._child_diagnostic_event(event, **fields)
            except Exception:
                pass
        try:
            helper = sys.modules.get('harness_coverage_diagnostics')
            if (helper is not None and callable(getattr(helper, '_child_sink', None))
                    and helper._child_sink() is not None):
                key = 'session' if function.__name__ == 'pytest_sessionfinish' else 'config'
                subject = args[0] if args else kwargs.get(key)
                config = subject.config if key == 'session' else subject
                emit(function.__name__ + '_owner_enter',
                     observer_entry_monotonic_ns=helper._diagnostic_clock_ns())
            else:
                helper = None
        except Exception:
            helper = None
        try:
            result = function(*args, **kwargs)
        except BaseException as error:
            emit(function.__name__ + '_owner_error', error_type=type(error).__name__)
            raise
        try:
            emit(function.__name__ + '_owner_return',
                 harness_timing_epoch_monotonic=getattr(config, '_harness_timing_epoch', None))
        except Exception:
            pass
        return result
    return observed


def _listing_witness_types():
    from attune_harness.windows_reads import ReadRoot
    from attune_harness.windows_effects import Native
    return ReadRoot, Native


def _configure_listing_witness(config):
    selected = getattr(getattr(config, 'option', None), 'harness_windows_listing_witness', None)
    if selected is None:
        return
    if os.name != 'nt':
        raise pytest.UsageError('Listing witness requires an explicit Windows installed child')
    sink = diagnostic_call = None
    patch = pytest.MonkeyPatch()
    try:
        context_path = config.getoption('--harness-installed-context')
        if context_path is None:
            raise ValueError('Listing witness requires its installed context')
        context = json.loads(Path(context_path).read_text(encoding='utf-8'))
        worker = context['workers'][config.getoption('--harness-shard-index')]
        if selected != worker.get('listing_witness'):
            raise ValueError('Listing witness sink differs from its preselected context')
        from measure_coverage import _DiagnosticSink, _diagnostic_call
        diagnostic_call = _diagnostic_call
        sink = _DiagnosticSink(selected, context['context_token'], 'listing',
                               max_bytes=1024 * 1024, max_row=65536, reserve_summary=True)
        helper = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tests/windows_read_witness.py'))
        reader, native = _listing_witness_types()
        def record(key, value):
            diagnostic_call(sink, 'emit', event=key, details=lambda: {'observation': json.loads(value)})
        witness = helper['ListingWitness'](patch, record, reader, native)
        config._harness_listing_witness = (patch, witness, sink)
        config._harness_listing_call = diagnostic_call
    except Exception as error:
        # Explicit profile/context errors are setup refusals; best-effort observer
        # setup failures cannot replace the original test/software outcome.
        config._harness_listing_setup_error = type(error).__name__
        try:
            patch.undo()
        except Exception:
            pass
        if sink is not None:
            diagnostic_call(sink, 'emit', event='windows_listing_setup_error',
                            details=lambda: {'error_type': type(error).__name__})
            diagnostic_call(sink, 'close')


def _close_listing_witness(config):
    sink = diagnostic_call = None
    try:
        selected = getattr(config, '_harness_listing_witness', None)
        if selected is None:
            return
        patch, witness, sink = selected
        diagnostic_call = config._harness_listing_call
        patch.undo()
        diagnostic_call(sink, 'finish', event='windows_listing_summary', details=lambda: {
            'truncated': bool(witness.truncated or witness.diagnostic_errors or witness.active_invocations),
            'active_invocations': witness.active_invocations,
            'diagnostic_error_types': witness.diagnostic_errors})
    except Exception:
        pass  # Diagnostic cleanup cannot replace the original pytest verdict.
    finally:
        if diagnostic_call is not None:
            diagnostic_call(sink, 'close')


@_shutdown_owner
def pytest_configure(config):
    config._harness_timing_epoch = _monotonic()
    config._harness_stack_log = (
        Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'slow-stacks.txt').open('wb', buffering=0)
    # One main-thread writer, separate from pytest capture and stack timers.
    # Each event is written immediately, including starts whose test is killed.
    config._harness_timing_log = (
        Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'test-timings.jsonl').open('wb', buffering=0)
    try:
        config._harness_failure_records = config._harness_failure_bytes = 0
        config._harness_failure_limited = False
        config._harness_failure_log = (
            Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'failed-phases.jsonl').open('xb', buffering=0)
    except Exception:
        config._harness_failure_log = None
    _timing(config, 'suite_start')
    _installed_witness(config)
    _configure_listing_witness(config)


@_shutdown_owner
def pytest_unconfigure(config):
    _close_listing_witness(config)
    try:
        stream = getattr(config, '_harness_failure_log', None)
        if stream is not None:
            stream.close()
    except Exception:
        pass  # A diagnostic close must not replace pytest's original verdict.
    for name in ('_harness_stack_log', '_harness_timing_log'):
        stream = getattr(config, name, None)
        if stream is not None:
            stream.close()


def _timing(config, event, **details):
    record = {'schema_version': 1, 'event': event,
              'elapsed_seconds': round(_monotonic() - config._harness_timing_epoch, 6),
              **details}
    config._harness_timing_log.write((json.dumps(record, ensure_ascii=True,
                                                allow_nan=False) + '\n').encode('ascii'))


def _failure_text(report, call):
    if call.excinfo is not None:
        # Keep the exception before a long traceback consumes the text cap.
        summary = call.excinfo.exconly()
        trace = call.excinfo.getrepr(showlocals=False, style='short', funcargs=False)
        return summary + '\n' + str(trace)
    return report.longreprtext


def _failed_phase(config, report, call):
    # Keep the original assertion before a later teardown/outer watchdog can
    # prevent final JUnit. Separate from timing events consumed by diagnostics.
    try:
        stream = config._harness_failure_log
        if stream is None or config._harness_failure_limited:
            return
        nodeid = str(report.nodeid)
        record = {'schema_version': 1, 'event': 'failed_phase',
                  'elapsed_seconds': round(_monotonic() - config._harness_timing_epoch, 6),
                  'nodeid': nodeid[:MAX_FAILURE_NODE],
                  'nodeid_truncated': len(nodeid) > MAX_FAILURE_NODE,
                  'phase': report.when, 'outcome': 'failed'}
        try:
            text = _failure_text(report, call)
            record.update(failure=text[:MAX_FAILURE_TEXT],
                          failure_truncated=len(text) > MAX_FAILURE_TEXT)
        except Exception as error:
            record.update(failure='', failure_truncated=False,
                          representation_error_type=type(error).__name__[:80])
        data = (json.dumps(record, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
        # Reserve room for one explicit cap marker; no repeated dropped records.
        if (config._harness_failure_records >= MAX_FAILURE_RECORDS
                or config._harness_failure_bytes + len(data) > MAX_FAILURE_BYTES - 256):
            config._harness_failure_limited = True
            stream.write((json.dumps({'schema_version': 1, 'event': 'failure_log_limit',
                'records_retained': config._harness_failure_records,
                'bytes_retained': config._harness_failure_bytes}) + '\n').encode('ascii'))
            return
        stream.write(data)
        config._harness_failure_records += 1
        config._harness_failure_bytes += len(data)
    except Exception:
        pass  # Open/format/write failures cannot replace the failed test.


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    _timing(item.config, 'phase_start', nodeid=item.nodeid, phase='setup')


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item):
    _timing(item.config, 'phase_start', nodeid=item.nodeid, phase='call')


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item):
    _timing(item.config, 'phase_start', nodeid=item.nodeid, phase='teardown')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield
    report = result.get_result()
    if report.failed:
        _failed_phase(item.config, report, call)
    _timing(item.config, 'phase_end', nodeid=report.nodeid, phase=report.when,
            outcome=report.outcome, duration_seconds=report.duration)
    # A bounded Future can fail before the 60-second watchdog fires. Sample
    # while its worker is still active, before fixture teardown can release it.
    # FutureTimeoutError is distinct from built-in TimeoutError on Python 3.10.
    if call.excinfo is not None and call.excinfo.errisinstance(
            (TimeoutError, FutureTimeoutError)):
        event, details = 'timeout_snapshot', {}
        try:
            _dump(report.nodeid, item.config._harness_stack_log)
        except Exception as error:
            # Diagnostics must not replace the original timeout with an
            # INTERNALERROR. Retain a bounded marker without exception text.
            event = 'timeout_snapshot_failed'
            details = {'error_type': type(error).__name__[:80]}
        try:
            _timing(item.config, event, nodeid=report.nodeid, phase=report.when, **details)
        except Exception:
            pass  # A failed diagnostic journal must preserve the test verdict too.


@_shutdown_owner
def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption('--harness-installed-context') is not None:
        try:
            _installed_witness(session.config, finished=True)
        except Exception:
            # Retain an original failed pytest verdict; identity drift can only
            # change an otherwise-successful installed run to failure.
            session.exitstatus = int(exitstatus) or 1
        terminal = session.config.pluginmanager.get_plugin('terminalreporter')
        reports = []
        categories = ('passed', 'failed', 'error', 'skipped', 'xfailed', 'xpassed', 'subtests passed')
        if terminal is not None:
            for category in categories:
                for report in terminal.stats.get(category, []):
                    reports.append({'category': category, 'nodeid': report.nodeid,
                                    'when': report.when, 'outcome': report.outcome,
                                    'subtest': type(report).__name__ == 'SubtestReport'})
        payload = {'schema_version': 1, 'exit_status': int(session.exitstatus),
                   'shard': {'index': session.config.getoption('--harness-shard-index'), 'count': 2},
                   'reports': reports}
        (Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'terminal.json').write_text(
            json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        exitstatus = session.exitstatus
    _timing(session.config, 'suite_end', exit_status=int(exitstatus))


def _dump(nodeid, stream):
    # Hold strong references while reading frame/code metadata under the GIL.
    # Avoid linecache/source reads: diagnostic collection should not do file IO.
    frames = sys._current_frames()
    lines = [f'\nSlow test Python stacks: {nodeid}\n']
    for ident, frame in list(frames.items())[:100]:
        lines.append(f'Thread {ident} (most recent call first):\n')
        for _ in range(100):
            if frame is None:
                break
            code = frame.f_code
            lines.append(f'  File {code.co_filename!r}, line {frame.f_lineno}, in {code.co_name}\n')
            frame = frame.f_back
        if frame is not None:
            lines.append('  [frames truncated after 100]\n')
    if len(frames) > 100:
        lines.append('[threads truncated after 100]\n')
    lines.append('End slow-test Python stacks\n')
    # The watchdog and a timeout report can arrive together. Keep each
    # bounded snapshot contiguous in their shared retained stream.
    with _stack_write_lock:
        stream.write(''.join(lines).encode('utf-8', errors='backslashreplace'))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    started = _monotonic()
    _timing(item.config, 'case_start', nodeid=item.nodeid)
    delay = float(item.config.getini('harness_stack_timeout'))
    timer = threading.Timer(delay, _dump, (item.nodeid, item.config._harness_stack_log))
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        # A dump already in progress must finish before the log can be closed.
        timer.join()
        _timing(item.config, 'case_end', nodeid=item.nodeid,
                duration_seconds=_monotonic() - started)
