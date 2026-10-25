"""Bounded input-read refusals; deterministic on every platform.

# qualify: platform
"""

from pathlib import Path

import pytest

from attune_harness import features


class Clock:
    def __init__(self):
        self.now, self.sleeps = 0.0, []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def setup_retry(monkeypatch, *, windows=True):
    clock = Clock()
    monkeypatch.setattr(features, 'RETRY_REFUSED_READ', windows)
    monkeypatch.setattr(features.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(features.time, 'sleep', clock.sleep)
    return clock


def refuse_opens(monkeypatch, source, failures, error):
    original, calls = Path.open, []

    def opening(path, *args, **kwargs):
        if path == source:
            calls.append((args, kwargs))
            if failures is None or len(calls) <= failures:
                raise error
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', opening)
    return calls


def test_transient_windows_denial_repeats_complete_read(tmp_path, monkeypatch):
    source = tmp_path / 'record.json'
    source.write_bytes('café\r\n'.encode())
    clock = setup_retry(monkeypatch)
    calls = refuse_opens(monkeypatch, source, 1, PermissionError(13, 'owned record busy'))
    assert features.read_text(source) == 'café\r\n'
    assert len(calls) == 2 and clock.sleeps == [.005]
    assert all(args == ('rb',) and kwargs == {} for args, kwargs in calls)


def test_persistent_windows_denial_preserves_exception_at_bound(tmp_path, monkeypatch):
    source = tmp_path / 'record.json'
    source.write_bytes(b'{}')
    clock = setup_retry(monkeypatch)
    error = PermissionError(13, 'still denied')
    calls = refuse_opens(monkeypatch, source, None, error)
    with pytest.raises(PermissionError) as caught:
        features.read_text(source)
    assert caught.value is error
    assert clock.now == pytest.approx(features.READ_RETRY_SECONDS)
    assert 1 < len(calls) <= 402 and all(0 < value <= .005 for value in clock.sleeps)


@pytest.mark.parametrize('wake_at', [2.0, 2.25], ids=['exact-deadline', 'scheduler-oversleep'])
def test_expired_sleep_does_not_start_a_new_attempt(tmp_path, monkeypatch, wake_at):
    source = tmp_path / 'record.json'
    source.write_bytes(b'{}')
    clock = setup_retry(monkeypatch)
    error = PermissionError(13, 'first open denied')
    calls = refuse_opens(monkeypatch, source, 1, error)

    def delayed_wake(seconds):
        clock.sleeps.append(seconds)
        clock.now = wake_at

    monkeypatch.setattr(features.time, 'sleep', delayed_wake)
    with pytest.raises(PermissionError) as caught:
        features.read_text(source)
    assert caught.value is error and len(calls) == 1 and clock.sleeps == [.005]


@pytest.mark.parametrize('windows', [False, True])
def test_zero_budget_and_non_windows_do_not_retry(tmp_path, monkeypatch, windows):
    source = tmp_path / 'record.json'
    source.write_bytes(b'{}')
    clock = setup_retry(monkeypatch, windows=windows)
    monkeypatch.setattr(features, 'READ_RETRY_SECONDS', 0)
    error = PermissionError(13, 'denied')
    calls = refuse_opens(monkeypatch, source, None, error)
    with pytest.raises(PermissionError) as caught:
        features.read_text(source)
    assert caught.value is error and len(calls) == 1 and clock.sleeps == []


@pytest.mark.parametrize('data,limit,error', [
    (b'oversized', 3, ValueError), (b'\xff', 3, UnicodeDecodeError),
])
def test_retry_does_not_bypass_content_refusals(tmp_path, monkeypatch, data, limit, error):
    source = tmp_path / 'record.json'
    source.write_bytes(data)
    clock = setup_retry(monkeypatch)
    calls = refuse_opens(monkeypatch, source, 1, PermissionError(13, 'busy'))
    with pytest.raises(error):
        features.read_text(source, limit)
    assert len(calls) == 2 and clock.sleeps == [.005]
    assert source.read_bytes() == data


@pytest.mark.parametrize('error', [OSError(5, 'device failure'), FileNotFoundError(2, 'removed')])
def test_other_open_errors_are_not_retried(tmp_path, monkeypatch, error):
    source = tmp_path / 'record.json'
    source.write_bytes(b'{}')
    clock = setup_retry(monkeypatch)
    calls = refuse_opens(monkeypatch, source, None, error)
    with pytest.raises(type(error)) as caught:
        features.read_text(source)
    assert caught.value is error and len(calls) == 1 and clock.sleeps == []


def test_missing_and_nonregular_inputs_keep_original_refusal(tmp_path, monkeypatch):
    clock = setup_retry(monkeypatch)
    for source in (tmp_path / 'missing', tmp_path):
        with pytest.raises(ValueError, match='Not a regular input file'):
            features.read_text(source)
    assert clock.sleeps == []


def test_every_retry_rechecks_regular_file(tmp_path, monkeypatch):
    source = tmp_path / 'record.json'
    source.write_bytes(b'{}')
    clock = setup_retry(monkeypatch)
    calls = refuse_opens(monkeypatch, source, None, PermissionError(13, 'busy'))
    original_sleep = clock.sleep

    def remove_after_denial(seconds):
        source.unlink()
        original_sleep(seconds)

    monkeypatch.setattr(features.time, 'sleep', remove_after_denial)
    with pytest.raises(ValueError, match='Not a regular input file'):
        features.read_text(source)
    assert len(calls) == 1 and clock.sleeps == [.005]
