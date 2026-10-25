"""The host payload is data, not a shell command or an instruction to run a model."""
import io
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'memory_prompt_hook.py'


@pytest.mark.parametrize('raw,dispatch', [(b'{"prompt":"release"}', True), (b'{"prompt":"--help"}', True),
    (b'{"prompt":"$(touch /tmp/not-a-command)"}', True),
    (b'{"prompt":""}', False), (b'{}', False), (b'bad json', False),
    (b'{"prompt":"' + b'x' * 513 + b'"}', False), pytest.param(b'x' * 65537, False, id='oversized-input'),
    pytest.param(b'{"prompt":"release","extra":[[0]]}', True, id='ignored-extra')])
def test_bridge_bounds_input_and_preserves_prompt_as_one_argument(monkeypatch, raw, dispatch):
    calls = []
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--config', '/fixture/memory.json'])
    monkeypatch.setattr(sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw)))
    stdout, stderr = io.TextIOWrapper(io.BytesIO()), io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(sys, 'stdout', stdout)
    monkeypatch.setattr(sys, 'stderr', stderr)
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b'banner\n', b'')
    monkeypatch.setattr(subprocess, 'run', run)
    assert runpy.run_path(str(SCRIPT))['main']() == 0
    stdout.flush()
    assert bool(calls) == dispatch
    if dispatch:
        assert calls[0][0][:5] == [sys.executable, '-m', 'attune_harness', 'memory', '--config']
        assert calls[0][0][-1].startswith('--for=')
        assert calls[0][1] == {'capture_output': True, 'timeout': 10, 'check': False}
        assert stdout.buffer.getvalue() == b'banner\n'
    else:
        assert stdout.buffer.getvalue() == b''


def test_decoder_recursion_error_skips_without_dispatch_or_payload_log(monkeypatch):
    raw = b'{"prompt":"private-query","extra":"private-extra"}'
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--config', '/fixture/memory.json'])
    monkeypatch.setattr(sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw)))
    stdout, stderr = io.TextIOWrapper(io.BytesIO()), io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(sys, 'stdout', stdout)
    monkeypatch.setattr(sys, 'stderr', stderr)
    main = runpy.run_path(str(SCRIPT))['main']

    def refuse(value):
        assert value == raw
        raise RecursionError('private-query private-extra')

    # Decoder depth limits differ between supported Python patch versions.
    # Exercise the hook's error boundary without relying on that runtime limit.
    monkeypatch.setitem(main.__globals__, 'json', SimpleNamespace(loads=refuse))
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: pytest.fail(
        'A decoder failure must not dispatch the memory command'))
    assert main() == 0
    stdout.flush()
    stderr.flush()
    assert stdout.buffer.getvalue() == b''
    assert stderr.buffer.getvalue() == (
        b'[attune-harness memory] prompt hook skipped: RecursionError\n')


def test_backend_error_cannot_echo_prompt_into_hook_log(monkeypatch):
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--config', '/fixture/memory.json'])
    monkeypatch.setattr(sys, 'stdin', io.TextIOWrapper(io.BytesIO(b'{"prompt":"private-query"}')))
    stdout, stderr = io.TextIOWrapper(io.BytesIO()), io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(sys, 'stdout', stdout)
    monkeypatch.setattr(sys, 'stderr', stderr)
    monkeypatch.setattr(subprocess, 'run', lambda argv, **kw: subprocess.CompletedProcess(
        argv, 0, b'', b'backend refused private-query'))
    assert runpy.run_path(str(SCRIPT))['main']() == 0
    stdout.flush()
    stderr.flush()
    assert stdout.buffer.getvalue() == b''
    assert b'private-query' not in stderr.buffer.getvalue()
    assert b'no memory served' in stderr.buffer.getvalue()
