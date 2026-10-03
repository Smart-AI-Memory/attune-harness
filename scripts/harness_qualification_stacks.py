"""Retain slow-test Python stacks without a native asynchronous frame walk.

This watchdog needs the GIL: it cannot diagnose a C extension that holds it.
The qualifier's separate process budget still terminates such a stuck suite.
"""
import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest


def pytest_addoption(parser):
    parser.addini('harness_stack_timeout', 'Seconds before retaining slow-test stacks',
                  default='60')


def pytest_configure(config):
    config._harness_timing_epoch = time.monotonic()
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
              'elapsed_seconds': round(time.monotonic() - config._harness_timing_epoch, 6),
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
    stream.write(''.join(lines).encode('utf-8', errors='backslashreplace'))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    started = time.monotonic()
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
                duration_seconds=time.monotonic() - started)
