# qualify: platform
"""Real process controls for browser-test outcome and evidence preservation."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from browser_process import read_browser_output, run_browser_process


def child(source):
    return [sys.executable, '-S', '-c', source]


def test_browser_process_preserves_success_and_unicode_output(tmp_path):
    result = run_browser_process(child(
        "import os; os.write(1, 'client regressions passed 雪\\n'.encode('utf-8')); "
        "os.write(2, b'entry marker\\n')"), tmp_path)
    assert result.returncode == 0
    assert result.stdout == 'client regressions passed 雪\n'
    assert result.stderr == 'entry marker\n'
    receipt = json.loads((tmp_path / 'browser-process.json').read_text())
    assert receipt['status'] == 'completed'
    assert receipt['returncode'] == 0
    assert receipt['pid'] > 0
    assert receipt['timeout_seconds'] == 30


def test_browser_process_preserves_nonzero_outcome(tmp_path):
    result = run_browser_process(child(
        "import os,sys; os.write(2,b'assertion failed\\n'); sys.exit(7)"),
        tmp_path)
    assert result.returncode == 7
    assert result.stderr == 'assertion failed\n'


def test_browser_process_timeout_keeps_early_output_and_original_failure(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        run_browser_process(child(
            "import os,time; os.write(1,b'entered\\n'); "
            "os.write(2,b'before blocking\\n'); time.sleep(30)"),
            tmp_path, timeout=2)
    assert caught.value.timeout == 2
    assert caught.value.stdout == b'entered\n'
    assert caught.value.stderr == b'before blocking\n'
    receipt = json.loads((tmp_path / 'browser-process.json').read_text())
    assert receipt['status'] == 'timeout'
    assert receipt['returncode'] != 0
    assert receipt['timeout_seconds'] == 2


def test_browser_process_diagnostic_failure_does_not_mask_nonzero(tmp_path, monkeypatch):
    write_text = Path.write_text

    def refuse_receipt(path, *args, **kwargs):
        if path.name == 'browser-process.json':
            raise PermissionError('diagnostic control')
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', refuse_receipt)
    result = run_browser_process(child("raise SystemExit(9)"), tmp_path)
    assert result.returncode == 9
    assert read_browser_output(tmp_path / 'absent') == '<unreadable: FileNotFoundError>'


def test_browser_process_bounds_retained_output(tmp_path):
    output = tmp_path / 'output'
    output.write_bytes(b'a' * 20000 + b'last')
    value = read_browser_output(output)
    assert len(value) == 16384
    assert value.endswith('last')


def test_browser_process_launch_failure_is_preserved(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_browser_process([str(tmp_path / 'missing-executable')], tmp_path)
    receipt = json.loads((tmp_path / 'browser-process.json').read_text())
    assert receipt['status'] == 'launch_failed'
    assert receipt['returncode'] is None

def test_browser_process_interrupted_wait_terminates_child(tmp_path, monkeypatch):
    wait = subprocess.Popen.wait
    children = []

    def interrupt_wait(process, timeout=None):
        if timeout is not None:
            children.append(process)
            raise RuntimeError('interrupted wait control')
        return wait(process, timeout=timeout)

    monkeypatch.setattr(subprocess.Popen, 'wait', interrupt_wait)
    with pytest.raises(RuntimeError, match='interrupted wait control'):
        run_browser_process(child(
            'import time; time.sleep(30)'), tmp_path)
    assert len(children) == 1
    assert children[0].poll() is not None
    receipt = json.loads((tmp_path / 'browser-process.json').read_text())
    assert receipt['status'] == 'interrupted'
    assert receipt['returncode'] != 0
