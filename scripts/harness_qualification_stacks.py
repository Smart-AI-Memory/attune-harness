"""Retain slow-test Python stacks without a native asynchronous frame walk.

This watchdog needs the GIL: it cannot diagnose a C extension that holds it.
The qualifier's separate process budget still terminates such a stuck suite.
"""
from concurrent.futures import TimeoutError as FutureTimeoutError
import json
import hashlib
import os
from pathlib import Path
import sys
import threading
import time

import pytest

# Keep journal time independent of tests replacing the shared time module.
_monotonic = time.monotonic
_stack_write_lock = threading.Lock()


def pytest_addoption(parser):
    parser.addini('harness_stack_timeout', 'Seconds before retaining slow-test stacks',
                  default='60')
    parser.addoption('--harness-shard-index', type=int, default=0)
    parser.addoption('--harness-shard-count', type=int, default=1)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
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


def pytest_configure(config):
    config._harness_timing_epoch = _monotonic()
    config._harness_stack_log = (
        Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'slow-stacks.txt').open('wb', buffering=0)
    # One main-thread writer, separate from pytest capture and stack timers.
    # Each event is written immediately, including starts whose test is killed.
    config._harness_timing_log = (
        Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'test-timings.jsonl').open('wb', buffering=0)
    _timing(config, 'suite_start')


def pytest_unconfigure(config):
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


def pytest_sessionfinish(session, exitstatus):
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
