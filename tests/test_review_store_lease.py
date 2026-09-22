"""The run store's lease waits a bounded time for the writer lock before it reports busy."""
# qualify: platform

import threading
import time

import pytest

from attune_harness import review_store
from attune_harness.review_store import LEASE_RETRY_SECONDS, PersistenceError, RunStore


def hold(store, seconds, taken, released):
    """Hold the lease from another thread: its own descriptor, so the lock really conflicts."""
    with store.lease(retry_seconds=0):
        taken.set()
        released.wait(seconds)


def test_the_bound_is_the_codebase_bound():
    assert LEASE_RETRY_SECONDS == 2.0 == review_store.REPLACE_RETRY_SECONDS


def test_a_brief_overlap_becomes_a_grant(tmp_path):
    store = RunStore(tmp_path / "run")
    taken, released = threading.Event(), threading.Event()
    holder = threading.Thread(target=hold, args=(store, 10, taken, released))
    holder.start()
    try:
        assert taken.wait(5)
        with pytest.raises(PersistenceError, match="Run is busy; another owner holds the writer lock"):
            with store.lease(retry_seconds=0):
                pass
        threading.Timer(0.3, released.set).start()
        started = time.monotonic()
        with store.lease():  # the default bound; the holder lets go after 0.3 s
            elapsed = time.monotonic() - started
        assert 0.25 <= elapsed < LEASE_RETRY_SECONDS, elapsed
    finally:
        released.set()
        holder.join(5)


def test_a_holder_past_the_bound_is_still_busy_in_the_same_words(tmp_path):
    store = RunStore(tmp_path / "run")
    taken, released = threading.Event(), threading.Event()
    holder = threading.Thread(target=hold, args=(store, 10, taken, released))
    holder.start()
    try:
        assert taken.wait(5)
        started = time.monotonic()
        with pytest.raises(PersistenceError, match="^Run is busy; another owner holds the writer lock$"):
            with store.lease(retry_seconds=0.2):
                pass
        elapsed = time.monotonic() - started
        assert 0.2 <= elapsed < 1.5, elapsed
    finally:
        released.set()
        holder.join(5)
    with store.lease(retry_seconds=0):  # released: granted at once
        pass


def test_the_module_bound_is_read_at_call_time(tmp_path, monkeypatch):
    """A test that wants the old immediate refusal can shrink the bound without touching callers."""
    store = RunStore(tmp_path / "run")
    taken, released = threading.Event(), threading.Event()
    holder = threading.Thread(target=hold, args=(store, 10, taken, released))
    holder.start()
    try:
        assert taken.wait(5)
        monkeypatch.setattr(review_store, "LEASE_RETRY_SECONDS", 0)
        started = time.monotonic()
        with pytest.raises(PersistenceError, match="busy"):
            with store.lease():
                pass
        assert time.monotonic() - started < 0.5
    finally:
        released.set()
        holder.join(5)
