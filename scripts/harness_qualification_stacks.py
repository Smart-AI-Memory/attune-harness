"""Retain slow-test Python stacks without a native asynchronous frame walk.

This watchdog needs the GIL: it cannot diagnose a C extension that holds it.
The qualifier's separate process budget still terminates such a stuck suite.
"""
import os
from pathlib import Path
import sys
import threading

import pytest


def pytest_addoption(parser):
    parser.addini('harness_stack_timeout', 'Seconds before retaining slow-test stacks',
                  default='60')


def pytest_configure(config):
    config._harness_stack_log = (
        Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'tests.txt').open('ab', buffering=0)


def pytest_unconfigure(config):
    stream = getattr(config, '_harness_stack_log', None)
    if stream is not None:
        stream.close()


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
