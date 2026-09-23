"""Working memory: one contract, two backends, chosen once and never diverted.

Native memory Task 4.2 (D18) and Task 5 (3.4, D21.6). The file store runs for
real under ``tmp_path``. The Redis store runs against ``FakeKV``, an in-process
double that answers only the commands the store may issue (SET with EX and NX,
GET, DEL, SCAN, and WATCH, MULTI, EXEC through a pipeline) with a clock the
test controls, so expiry is exercised without waiting. A live run against a
real Redis happens only when ``ATTUNE_TEST_REDIS_URL`` is set, under its own
namespace, and removes what it wrote.

The versioned record: ``tests/fixtures/scratch_legacy_v1/`` holds two files
the 0.5.0-era code on ``main`` (8495a29) wrote with a frozen clock, pinned by
digest; the legacy test proves this code reads them in place and never
rewrites them on a read.
"""
# qualify: platform

import errno
import fnmatch
import hashlib
import json
import os
import sys
import threading
import time
import types
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path

import pytest

from attune_harness import memory_cli, memory_redis, memory_scratch
from attune_harness.memory_cli import main as memory_main
from attune_harness.memory_redis import MemoryRedisUnavailable
from attune_harness.memory_scratch import (
    FORMAT,
    FORMAT_VERSION,
    REDIS_PREFIX,
    TTL_MAX,
    VALUE_LIMIT,
    FileScratch,
    RedisScratch,
    ScratchBackend,
    ScratchRefused,
    ScratchUncertain,
    open_scratch,
    run,
    validate_config,
)

LEGACY = Path(__file__).parent / "fixtures" / "scratch_legacy_v1"
# SHA-256 of each legacy file as main's code wrote it (Windows trap 6: the
# bytes are compared after normalising line endings, the backstop for a clone
# made without the .gitattributes entry).
LEGACY_DIGESTS = {
    "k-plan%3Acurrent.json": "8443d3a768600f949cca15cc7163312f3c3035bb947b33790794ee4716a70596",
    "k-ephemeral.json": "acc0cce1f13ae25f314c4293cc718c0f7b83aa4f1301d36a475a5f0de2a2c5f6",
}


class FakeError(Exception):
    pass


class WatchError(FakeError):
    """Named as redis-py names it: the store knows it by name, since the base never imports redis."""


class FakeKV:
    """SET (EX, NX), GET, DEL, SCAN and a WATCH/MULTI/EXEC pipeline with a controllable clock.

    Anything else is outside the contract. ``after_read`` is another client's
    write, run by the pipeline right after its GET, so a WATCH conflict can be
    staged.
    """

    def __init__(self):
        self.data = {}   # name -> (value, expires_at or None)
        self.now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
        self.calls = []
        self.after_read = None

    def _live(self, name):
        item = self.data.get(name)
        if item is None:
            return None
        if item[1] is not None and item[1] <= self.now:
            del self.data[name]
            return None
        return item[0]

    def ping(self):
        self.calls.append(("PING",))
        return True

    def set(self, name, value, ex=None, nx=False):
        self.calls.append(("SET", name, ex, "NX") if nx else ("SET", name, ex))
        assert ex is None or (isinstance(ex, int) and ex > 0)
        if nx and self._live(name) is not None:
            return None
        self.data[name] = (value, self.now + timedelta(seconds=ex) if ex else None)
        return True

    def get(self, name):
        self.calls.append(("GET", name))
        return self._live(name)

    def delete(self, name):
        self.calls.append(("DEL", name))
        return 1 if self._live(name) is not None and self.data.pop(name, None) else 0

    def scan_iter(self, match="*", count=10):
        self.calls.append(("SCAN", match, count))
        for name in sorted(self.data):
            if self._live(name) is not None and fnmatch.fnmatchcase(name, match):
                yield name

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    """WATCH one key, GET it at once, MULTI, queue SET, EXEC; EXEC refuses when the watched key moved."""

    def __init__(self, kv):
        self.kv = kv
        self.watched = None
        self.queued = None  # a list once MULTI has been called

    def watch(self, name):
        self.kv.calls.append(("WATCH", name))
        self.watched = (name, self.kv.data.get(name))

    def get(self, name):
        assert self.watched is not None and self.queued is None, "GET runs at once, after WATCH and before MULTI"
        value = self.kv.get(name)
        if self.kv.after_read is not None:
            self.kv.after_read()
        return value

    def multi(self):
        self.kv.calls.append(("MULTI",))
        self.queued = []

    def set(self, name, value, ex=None, nx=False):
        assert self.queued is not None, "SET is queued under MULTI"
        self.queued.append((name, value, ex, nx))

    def execute(self):
        self.kv.calls.append(("EXEC",))
        name, before = self.watched
        if self.kv.data.get(name) != before:
            raise WatchError("Watched variable changed.")
        return [self.kv.set(*queued[:2], ex=queued[2], nx=queued[3]) for queued in self.queued]

    def reset(self):
        self.kv.calls.append(("RESET",))
        self.watched, self.queued = None, None


class Clock:
    """Moves memory_scratch's clock and the double's together."""

    def __init__(self, monkeypatch, kv=None):
        self.now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
        self.kv = kv
        monkeypatch.setattr(memory_scratch, "_now", lambda: self.now)

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)
        if self.kv is not None:
            self.kv.now = self.now


@pytest.fixture(params=["file", "redis"])
def store(request, tmp_path, monkeypatch):
    if request.param == "file":
        clock = Clock(monkeypatch)
        yield FileScratch(str(tmp_path.resolve()), "unit"), clock, None
    else:
        kv = FakeKV()
        clock = Clock(monkeypatch, kv)
        yield RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,)), clock, kv


def stored_bytes(backend, kv, key):
    """The record as the backend holds it, for a digest or a look at its header."""
    if backend.backend == "file":
        return backend._path(key).read_bytes()
    value = kv.data[REDIS_PREFIX + "unit:" + key][0]
    return value if isinstance(value, bytes) else value.encode("utf-8")


def header(payload):
    """The record's header as written: the format, its version, the writer and the record version."""
    return payload.decode("utf-8").split(',"key":', 1)[0]


# --- the contract, both backends -------------------------------------------------


def test_backends_satisfy_the_protocol_and_declare_themselves(store):
    backend, _, _ = store
    assert isinstance(backend, ScratchBackend)
    caps = backend.capabilities()
    assert set(caps) == {"backend", "shared", "realtime", "location"}
    if backend.backend == "file":
        assert caps["shared"] is False and caps["realtime"] is False and caps["location"].endswith(os.sep + "unit")
    else:
        assert caps["shared"] is True and caps["realtime"] is True and REDIS_PREFIX + "unit:" in caps["location"]


def test_round_trip_forget_and_keys(store):
    backend, _, _ = store
    assert backend.retrieve("plan:current") is None
    stored = backend.stash("plan:current", {"task": "4.2", "n": 1.5, "tags": ["a", "b"]})
    assert stored["key"] == "plan:current" and stored["expires_at"] is None and stored["stored_at"].endswith("+00:00")
    found = backend.retrieve("plan:current")
    assert found["value"] == {"task": "4.2", "n": 1.5, "tags": ["a", "b"]}
    assert found["stored_at"] == stored["stored_at"] and found["expires_at"] is None
    backend.stash("plan:next", "text value")
    backend.stash("note.1", [1, 2, 3])
    assert backend.keys() == ["note.1", "plan:current", "plan:next"]
    for key in ("a:b", "a-b", "a.b", "aZ"):
        backend.stash(key, 0)
    assert backend.keys("a*") == ["a-b", "a.b", "a:b", "aZ"]  # the same order from both backends
    for key in ("a:b", "a-b", "a.b", "aZ"):
        backend.forget(key)
    assert backend.keys("plan:*") == ["plan:current", "plan:next"]
    assert backend.keys("note.?") == ["note.1"]
    assert backend.forget("plan:next") is True
    assert backend.forget("plan:next") is False
    assert backend.keys() == ["note.1", "plan:current"]
    backend.stash("plan:current", "replaced")
    assert backend.retrieve("plan:current")["value"] == "replaced"


def test_time_to_live_expires_and_keys_hide_the_expired(store):
    backend, clock, _ = store
    stored = backend.stash("ephemeral", {"x": 1}, ttl_seconds=60)
    assert stored["expires_at"] == (clock.now + timedelta(seconds=60)).isoformat()
    clock.advance(59)
    assert backend.retrieve("ephemeral")["value"] == {"x": 1}
    assert backend.keys() == ["ephemeral"]
    clock.advance(2)
    assert backend.retrieve("ephemeral") is None
    assert backend.keys() == []


def test_key_value_ttl_and_pattern_bounds(store):
    backend, _, _ = store
    for bad in ("", "../x", "a b", "x" * 129, 7, "/etc", "a/b", "a\\b"):
        with pytest.raises(ValueError, match="Scratch key must be"):
            backend.stash(bad, 1)
        with pytest.raises(ValueError, match="Scratch key must be"):
            backend.retrieve(bad)
        with pytest.raises(ValueError, match="Scratch key must be"):
            backend.forget(bad)
    with pytest.raises(ValueError, match="limited to 65536 bytes"):
        backend.stash("big", "x" * (VALUE_LIMIT + 1))
    backend.stash("edge", "x" * (VALUE_LIMIT - 2))  # exactly at the limit with its quotes
    assert backend.retrieve("edge")["value"] == "x" * (VALUE_LIMIT - 2)
    # A separator-dense value near the limit: the reviewer found the indented
    # file record and the spaced Redis record grew past what retrieve read.
    dense = {f"k{i:05d}": i for i in range(5000)}
    while len(memory_scratch.canonical(dense).encode()) > VALUE_LIMIT:
        dense.popitem()
    assert len(memory_scratch.canonical(dense).encode()) > VALUE_LIMIT - 20
    backend.stash("dense", dense)
    assert backend.retrieve("dense")["value"] == dense
    assert "dense" in backend.keys("dens?")
    for bad in (float("nan"), {1: 2}.keys(), object()):
        with pytest.raises(ValueError, match="must be JSON"):
            backend.stash("k", bad)
    for bad in (0, -1, TTL_MAX + 1, True, "60"):
        with pytest.raises(ValueError, match="ttl must be"):
            backend.stash("k", 1, ttl_seconds=bad)
    for bad in (-1, True, "1", 1.0):
        with pytest.raises(ValueError, match="expected version must be an integer of 0 or more"):
            backend.stash("k", 1, expected_version=bad)
    for bad in ("", "a b", "[abc]", "x" * 129, "../*"):
        with pytest.raises(ValueError, match="pattern"):
            backend.keys(bad)


# --- the versioned record: format, writer, version (Task 5, D21.6) -----------------


def test_the_record_opens_with_its_format_and_writer_and_counts_its_versions(store):
    backend, _, kv = store
    stored = backend.stash("plan:current", {"b": 2, "a": 1})
    assert stored["format"] == FORMAT == "attune-harness/scratch" and stored["format_version"] == FORMAT_VERSION == 2
    assert stored["writer"] == memory_scratch.writer() == f"attune-harness {metadata.version('attune-harness')}"
    assert stored["version"] == 1
    assert list(stored) == ["format", "format_version", "writer", "version", "key", "stored_at", "expires_at"]
    # The header opens the stored bytes, in the declared order; the value's keys are canonical.
    payload = stored_bytes(backend, kv, "plan:current")
    assert payload.startswith(b'{"format":"attune-harness/scratch","format_version":2,"writer":"attune-harness ')
    assert header(payload).endswith(',"version":1')
    assert b'"value":{"a":1,"b":2}' in payload
    found = backend.retrieve("plan:current")
    assert list(found) == ["format", "format_version", "writer", "version", "key", "value", "stored_at", "expires_at"]
    assert found["version"] == 1 and found["writer"] == stored["writer"] and found["value"] == {"a": 1, "b": 2}
    assert backend.stash("plan:current", "again")["version"] == 2
    assert backend.stash("plan:current", "and again")["version"] == 3
    assert backend.retrieve("plan:current")["version"] == 3
    backend.forget("plan:current")
    assert backend.stash("plan:current", "fresh")["version"] == 1  # the count restarts once the key was absent


def test_a_version_counter_survives_expiry_as_absence(store):
    backend, clock, _ = store
    assert backend.stash("brief", 1, ttl_seconds=10)["version"] == 1
    assert backend.stash("brief", 2, ttl_seconds=10)["version"] == 2
    clock.advance(11)
    assert backend.stash("brief", 3)["version"] == 1  # what had lapsed is absent, not version 2


def test_compare_and_set_lands_on_the_expected_version_and_refuses_a_lost_update(store):
    backend, clock, kv = store
    # 0 is "no record": a create that only creates.
    assert backend.stash("plan:current", "first", expected_version=0)["version"] == 1
    stored = backend.stash("plan:current", "second", ttl_seconds=60, expected_version=1)
    assert stored["version"] == 2 and stored["expires_at"] == (clock.now + timedelta(seconds=60)).isoformat()
    before = hashlib.sha256(stored_bytes(backend, kv, "plan:current")).hexdigest()
    # The lost update: a writer that read version 1 and stashes against it after version 2 landed.
    with pytest.raises(ScratchRefused) as refused:
        backend.stash("plan:current", "stale", expected_version=1)
    assert str(refused.value) == (
        "Scratch stash of key 'plan:current' was refused: expected version 1, found version 2; "
        "nothing was written. Retrieve the key and stash with the version it reports."
    )
    assert refused.value.key == "plan:current" and refused.value.expected_version == 1 and refused.value.found == 2
    assert hashlib.sha256(stored_bytes(backend, kv, "plan:current")).hexdigest() == before
    assert backend.retrieve("plan:current")["value"] == "second"
    with pytest.raises(ScratchRefused, match=r"expected no record \(version 0\), found version 2; nothing was written"):
        backend.stash("plan:current", "create", expected_version=0)
    assert hashlib.sha256(stored_bytes(backend, kv, "plan:current")).hexdigest() == before
    with pytest.raises(ScratchRefused) as absent:
        backend.stash("plan:missing", "x", expected_version=3)
    assert str(absent.value) == (
        "Scratch stash of key 'plan:missing' was refused: expected version 3, found no record; "
        "nothing was written. Stash without an expected version, or with 0, to create it."
    )
    assert absent.value.found == 0 and backend.retrieve("plan:missing") is None
    # The TTL a compare-and-set carries behaves as any other.
    clock.advance(61)
    assert backend.retrieve("plan:current") is None
    assert backend.stash("plan:current", "after expiry", expected_version=0)["version"] == 1


def test_run_reports_a_refusal_as_failed_with_what_was_expected_and_found(store):
    backend, _, _ = store
    config, opener = {"scratch": {"backend": backend.backend}}, lambda config: backend
    assert run(config, "stash", {"key": "k", "value": 1}, open_with=opener)["version"] == 1
    envelope = run(config, "stash", {"key": "k", "value": 2, "expected_version": 7}, open_with=opener)
    assert envelope == {
        "status": "failed", "operation": "memory_scratch_stash", "backend": backend.backend, "key": "k",
        "expected_version": 7, "version": 1, "error": "ScratchRefused",
        "detail": "Scratch stash of key 'k' was refused: expected version 7, found version 1; "
                  "nothing was written. Retrieve the key and stash with the version it reports.",
    }
    assert run(config, "retrieve", {"key": "k"}, open_with=opener)["value"] == 1
    landed = run(config, "stash", {"key": "k", "value": 2, "expected_version": 1}, open_with=opener)
    assert landed["status"] == "ok" and landed["version"] == 2 and landed["format_version"] == 2


def test_the_writer_is_read_from_the_package_metadata_and_is_the_bare_name_without_it(store, monkeypatch):
    backend, _, _ = store
    assert memory_scratch.writer() == f"attune-harness {metadata.version('attune-harness')}"
    assert backend.stash("k", 1)["writer"] == memory_scratch.writer()

    def missing(distribution):
        raise metadata.PackageNotFoundError(distribution)
    monkeypatch.setattr(memory_scratch, "metadata",
                        types.SimpleNamespace(version=missing, PackageNotFoundError=metadata.PackageNotFoundError))
    assert memory_scratch.writer() == "attune-harness"
    assert backend.stash("k", 2)["writer"] == "attune-harness"
    assert backend.retrieve("k")["writer"] == "attune-harness" and backend.retrieve("k")["version"] == 2


# --- the uncertain receipt: reported once, never retried, never diverted -------------


def test_a_replace_that_raises_after_the_record_was_written_is_uncertain_and_not_retried(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    store = FileScratch(str(root), "unit")
    folder = root / "scratch" / "unit"
    store.stash("seed", 1)
    replaces = []

    def landed_then_raised(source, target, **kwargs):
        replaces.append(target.name)
        os.replace(source, target)  # the replace took effect and the call still raised: what is stored is not known
        raise PermissionError(errno.EACCES, "Access is denied")
    monkeypatch.setattr(memory_scratch, "replace_file", landed_then_raised)
    with pytest.raises(ScratchUncertain) as receipt:
        store.stash("seed", 2)
    assert str(receipt.value) == (
        "Scratch stash of key 'seed' may or may not have landed: the record was written and the replace raised "
        "(PermissionError: [Errno 13] Access is denied). Retrieve the key; a record at version 2 means it did. "
        "No retry was performed and nothing was diverted."
    )
    assert receipt.value.key == "seed" and receipt.value.version == 2 and receipt.value.error == "PermissionError"
    assert replaces == ["k-seed.json"]  # one attempt
    assert sorted(p.name for p in folder.iterdir()) == ["k-seed.json"]  # no temporary file left, nothing else written
    assert store.retrieve("seed")["version"] == 2  # this time it did land, as the receipt says how to learn

    def refused(source, target, **kwargs):
        replaces.append(target.name)
        raise OSError("disk says no")
    monkeypatch.setattr(memory_scratch, "replace_file", refused)
    with pytest.raises(ScratchUncertain, match=r"replace raised \(OSError: disk says no\)"):
        store.stash("seed", 3, expected_version=2)
    assert replaces == ["k-seed.json", "k-seed.json"]
    assert sorted(p.name for p in folder.iterdir()) == [".scratch.lock", "k-seed.json"]
    assert json.loads((folder / "k-seed.json").read_text(encoding="utf-8"))["value"] == 2  # and this time it did not
    envelope = run({"scratch": {"backend": "file"}}, "stash", {"key": "seed", "value": 4}, open_with=lambda c: store)
    assert envelope == {
        "status": "uncertain", "operation": "memory_scratch_stash", "backend": "file", "key": "seed", "version": 3,
        "error": "OSError", "detail": (
            "Scratch stash of key 'seed' may or may not have landed: the record was written and the replace raised "
            "(OSError: disk says no). Retrieve the key; a record at version 3 means it did. "
            "No retry was performed and nothing was diverted."),
    }


def test_a_write_to_the_temporary_file_that_fails_is_a_plain_failure(tmp_path, monkeypatch):
    """Nothing could have landed, so this is not uncertain: the error is the caller's, as before."""
    store = FileScratch(str(tmp_path.resolve()), "unit")
    store.stash("seed", 1)

    def refuse(*args, **kwargs):
        raise OSError("no space left")
    monkeypatch.setattr(memory_scratch.tempfile, "mkstemp", refuse)
    with pytest.raises(OSError, match="no space left"):
        store.stash("seed", 2)
    assert store.retrieve("seed")["value"] == 1


def test_a_lost_redis_reply_is_uncertain_and_not_retried_or_diverted(tmp_path, monkeypatch):
    class LostReply(FakeKV):
        def set(self, name, value, ex=None, nx=False):
            super().set(name, value, ex=ex, nx=nx)  # the server applied it; the reply never came back
            raise FakeError("Connection lost")
    kv = LostReply()
    Clock(monkeypatch, kv)
    store = RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,))
    with pytest.raises(ScratchUncertain) as receipt:
        store.stash("k", 1)
    assert str(receipt.value) == (
        "Scratch stash of key 'k' may or may not have landed: the write was sent to Redis at fake:6379 and its "
        "reply was lost (FakeError: Connection lost). Retrieve the key; a record at version 1 means it did. "
        "No retry was performed and nothing was diverted."
    )
    assert receipt.value.version == 1 and receipt.value.error == "FakeError"
    assert [call for call in kv.calls if call[0] == "SET"] == [("SET", REDIS_PREFIX + "unit:k", None)]  # one attempt
    assert store.retrieve("k")["version"] == 1
    kv.calls.clear()
    with pytest.raises(ScratchUncertain, match="a record at version 2 means it did"):
        store.stash("k", 2, expected_version=1)  # the EXEC's reply is lost the same way
    assert [call[0] for call in kv.calls] == ["WATCH", "GET", "MULTI", "EXEC", "SET", "RESET"]
    assert not list(tmp_path.iterdir())  # nothing went to any file store
    envelope = run({"scratch": {"backend": "redis"}}, "stash", {"key": "k", "value": 3}, open_with=lambda c: store)
    assert envelope["status"] == "uncertain" and envelope["version"] == 3 and envelope["error"] == "FakeError"
    assert set(envelope) == {"status", "operation", "backend", "key", "version", "error", "detail"}


def test_a_redis_failure_before_the_write_is_unavailable_not_uncertain():
    class Broken(FakeKV):
        def get(self, name):
            raise FakeError("Connection lost")
    store = RedisScratch(Broken(), "unit", host="fake:6379", errors=(FakeError,))
    with pytest.raises(MemoryRedisUnavailable, match="fake:6379 failed during stash: FakeError: Connection lost"):
        store.stash("k", 1)
    with pytest.raises(MemoryRedisUnavailable, match="failed during stash"):
        store.stash("k", 1, expected_version=1)


# --- the redis compare-and-set: WATCH, MULTI, EXEC and SET NX ------------------------


def test_redis_compare_and_set_is_one_transaction_and_refuses_when_the_key_moves(monkeypatch):
    kv = FakeKV()
    Clock(monkeypatch, kv)
    store = RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,))
    name = REDIS_PREFIX + "unit:k"
    store.stash("k", 1)
    kv.calls.clear()
    assert store.stash("k", 2, ttl_seconds=30, expected_version=1)["version"] == 2
    assert kv.calls == [("WATCH", name), ("GET", name), ("MULTI",), ("EXEC",), ("SET", name, 30), ("RESET",)]
    # Another client writes between the read and the EXEC: Redis refuses the transaction.
    kv.after_read = lambda: kv.set(name, '{"other": "client"}')
    kv.calls.clear()
    with pytest.raises(ScratchRefused) as refused:
        store.stash("k", 3, expected_version=2)
    assert str(refused.value) == (
        "Scratch stash of key 'k' was refused: expected version 2, but the record changed while the stash was "
        "being prepared; nothing was written. Retrieve the key and stash with the version it reports."
    )
    assert refused.value.found is None
    assert [call[0] for call in kv.calls] == ["WATCH", "GET", "SET", "MULTI", "EXEC", "RESET"]  # one attempt, no retry
    assert kv.data[name][0] == '{"other": "client"}'  # the other client's write stands
    kv.after_read = None

    class Appears(FakeKV):
        """The key is created by another client between the read and the SET NX."""
        def get(self, name):
            raw = super().get(name)
            if raw is None:
                super().set(name, '{"other": "client"}')
            return raw
    kv = Appears()
    Clock(monkeypatch, kv)
    store = RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,))
    with pytest.raises(ScratchRefused, match=r"expected no record \(version 0\), but the record changed"):
        store.stash("k", 1, expected_version=0)
    assert [call for call in kv.calls if call[0] == "SET"][-1] == ("SET", name, None, "NX")
    assert kv.data[name][0] == '{"other": "client"}'


def test_redis_stash_with_no_expectation_writes_over_what_it_cannot_read_as_before():
    kv = FakeKV()
    store = RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,))
    kv.data[REDIS_PREFIX + "unit:bad"] = ("{not json", None)
    assert store.stash("bad", 1)["version"] == 1
    assert store.retrieve("bad")["value"] == 1
    kv.data[REDIS_PREFIX + "unit:bad"] = ("{not json", None)
    with pytest.raises(MemoryRedisUnavailable, match="malformed record"):
        store.stash("bad", 2, expected_version=1)  # a compare has nothing to compare against
    assert kv.data[REDIS_PREFIX + "unit:bad"][0] == "{not json"


# --- the legacy record: read in place, never rewritten by a read ---------------------


def legacy_files(destination):
    """Copy the fixture main's code wrote into a scratch namespace; return its digests as pinned."""
    destination.mkdir(parents=True)
    digests = {}
    for name, digest in LEGACY_DIGESTS.items():
        raw = (LEGACY / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(raw).hexdigest() == digest, f"{name} is not the file main's code wrote"
        (destination / name).write_bytes(raw)
        digests[name] = digest
    return digests


def folder_digests(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.name.startswith("k-")}


def test_the_legacy_file_record_is_read_in_place_and_reported_as_version_1(tmp_path, monkeypatch):
    clock = Clock(monkeypatch)
    root = tmp_path.resolve()
    folder = root / "scratch" / "legacy"
    digests = legacy_files(folder)
    store = FileScratch(str(root), "legacy")
    found = store.retrieve("plan:current")
    assert found == {
        "format": FORMAT, "format_version": 1, "writer": None, "version": None, "key": "plan:current",
        "value": {"n": 1.5, "tags": ["a", "b"], "task": "3.4"},
        "stored_at": "2026-09-23T12:00:00+00:00", "expires_at": None,
    }
    assert store.retrieve("ephemeral")["expires_at"] == "2026-09-23T13:00:00+00:00"
    assert store.keys() == ["ephemeral", "plan:current"]
    assert folder_digests(folder) == digests  # a read never rewrites a legacy record
    envelope = run({"scratch": {"backend": "file"}}, "retrieve", {"key": "plan:current"}, open_with=lambda c: store)
    assert envelope["status"] == "ok" and envelope["format_version"] == 1 and envelope["version"] is None
    # A compare-and-set has nothing to compare against; nothing is written.
    with pytest.raises(ScratchRefused) as refused:
        store.stash("plan:current", "cas", expected_version=1)
    assert str(refused.value) == (
        "Scratch stash of key 'plan:current' was refused: expected version 1, found a legacy record, which carries "
        "no version; nothing was written. Stash without an expected version to write the current format, which "
        "starts at version 1."
    )
    assert refused.value.found is None
    with pytest.raises(ScratchRefused, match=r"expected no record \(version 0\), found a legacy record"):
        store.stash("plan:current", "cas", expected_version=0)
    assert folder_digests(folder) == digests
    # The first stash over it writes the current format at version 1; the other legacy file is untouched.
    stored = store.stash("plan:current", {"task": "3.4", "step": "b"})
    assert stored["format_version"] == 2 and stored["version"] == 1 and stored["writer"] == memory_scratch.writer()
    payload = (folder / "k-plan%3Acurrent.json").read_bytes()
    assert payload.startswith(b'{"format":"attune-harness/scratch","format_version":2,')
    assert b"schema_version" not in payload
    assert store.retrieve("plan:current")["version"] == 1
    assert folder_digests(folder)["k-ephemeral.json"] == digests["k-ephemeral.json"]
    assert store.stash("plan:current", "next", expected_version=1)["version"] == 2
    # Expiry of a legacy record is the same stamp, checked on read; keys() clears it as before.
    clock.advance(2 * 24 * 3600)
    assert store.retrieve("ephemeral") is None
    assert store.keys() == ["plan:current"] and not (folder / "k-ephemeral.json").exists()


def test_the_legacy_redis_record_is_read_in_place_and_reported_as_version_1(monkeypatch):
    kv = FakeKV()
    Clock(monkeypatch, kv)
    store = RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,))
    legacy = (LEGACY / "k-plan%3Acurrent.json").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    kv.data[REDIS_PREFIX + "unit:plan:current"] = (legacy, None)
    found = store.retrieve("plan:current")
    assert found["format_version"] == 1 and found["version"] is None and found["writer"] is None
    assert found["value"] == {"n": 1.5, "tags": ["a", "b"], "task": "3.4"}
    assert kv.data[REDIS_PREFIX + "unit:plan:current"][0] == legacy
    with pytest.raises(ScratchRefused, match="found a legacy record, which carries no version"):
        store.stash("plan:current", "cas", expected_version=1)
    assert kv.data[REDIS_PREFIX + "unit:plan:current"][0] == legacy
    assert store.stash("plan:current", "new")["version"] == 1
    assert store.retrieve("plan:current")["format_version"] == 2


# --- the file store's own edges -------------------------------------------------


def test_file_store_root_rules_and_layout(tmp_path):
    root = tmp_path.resolve()
    with pytest.raises(ValueError, match="canonical absolute"):
        FileScratch("relative/dir")
    with pytest.raises(ValueError, match="canonical absolute"):
        FileScratch(str(root / "missing"))
    (root / ".git").mkdir()
    with pytest.raises(ValueError, match="repository metadata"):
        FileScratch(str(root / ".git"))
    with pytest.raises(ValueError, match="namespace"):
        FileScratch(str(root), "Bad Name")
    store = FileScratch(str(root), "unit")
    store.stash("plan:a.b", {"v": 1})
    files = sorted(p.name for p in (root / "scratch" / "unit").iterdir())
    assert files == ["k-plan%3Aa.b.json"]  # ':' is percent-encoded so the name is valid everywhere; no lock for a plain stash
    text = (root / "scratch" / "unit" / "k-plan%3Aa.b.json").read_text(encoding="utf-8")
    record = json.loads(text)
    assert record["format"] == FORMAT and record["format_version"] == 2 and record["version"] == 1
    assert record["key"] == "plan:a.b" and record["value"] == {"v": 1} and "schema_version" not in record
    assert list(record) == ["format", "format_version", "writer", "version", "key", "value", "stored_at", "expires_at"]
    assert text.endswith("}\n") and "\n" not in text[:-1]  # one compact line
    assert not [p for p in (root / "scratch" / "unit").iterdir() if p.name.startswith(".scratch-")]  # no temp left


def test_file_names_are_one_to_one_with_keys_everywhere(tmp_path):
    """Case, reserved device names and length: each was a way for two keys to be one file, or none."""
    name = FileScratch._name
    assert name("a") == "k-a.json" and name("A") == "k-%41.json"           # case is encoded, never folded
    assert name("CON") == "k-%43%4F%4E.json" and name("nul") == "k-nul.json"  # the prefix keeps NUL from being a device
    long_key = "a" + ":" * 127
    assert len(name(long_key)) <= 207 and name(long_key) != name("a" + ":" * 126)  # 200 encoded + "k-" + ".json"
    assert name(long_key).endswith(".json") and "-" in name(long_key)[-22:]
    store = FileScratch(str(tmp_path.resolve()), "unit")
    store.stash("A", "upper")
    store.stash("a", "lower")
    assert store.retrieve("A")["value"] == "upper" and store.retrieve("a")["value"] == "lower"
    assert store.keys() == ["A", "a"]
    store.stash(long_key, {"long": True})
    assert store.retrieve(long_key)["value"] == {"long": True}
    assert long_key in store.keys("a:*")
    for reserved in ("CON", "NUL", "com1", "LPT9"):
        store.stash(reserved, reserved.lower())
        assert store.retrieve(reserved)["value"] == reserved.lower()


def test_file_store_ignores_foreign_or_tampered_files(tmp_path, monkeypatch):
    Clock(monkeypatch)
    root = tmp_path.resolve()
    store = FileScratch(str(root), "unit")
    store.stash("good", 1)
    folder = root / "scratch" / "unit"
    current = json.loads((folder / "k-good.json").read_text(encoding="utf-8"))
    (folder / "stray.txt").write_text("x", encoding="utf-8")
    (folder / "k-notjson.json").write_text("{", encoding="utf-8")
    (folder / "k-wrongkey.json").write_text(json.dumps({"schema_version": 1, "key": "other", "value": 1, "stored_at": "x", "expires_at": None}), encoding="utf-8")
    (folder / "k-future.json").write_text(json.dumps({"schema_version": 2, "key": "future", "value": 1, "stored_at": "x", "expires_at": None}), encoding="utf-8")
    (folder / "k-novalue.json").write_text(json.dumps({"schema_version": 1, "key": "novalue", "stored_at": "x", "expires_at": None}), encoding="utf-8")
    (folder / "k-extra.json").write_text(json.dumps({"schema_version": 1, "key": "extra", "value": 1, "stored_at": "x", "expires_at": None, "more": 1}), encoding="utf-8")
    # The current format's shape, damaged: a later format version, a version that is not a count, a foreign format name.
    (folder / "k-later.json").write_text(json.dumps({**current, "key": "later", "format_version": 3}), encoding="utf-8")
    (folder / "k-uncounted.json").write_text(json.dumps({**current, "key": "uncounted", "version": 0}), encoding="utf-8")
    (folder / "k-boolean.json").write_text(json.dumps({**current, "key": "boolean", "version": True}), encoding="utf-8")
    (folder / "k-foreign.json").write_text(json.dumps({**current, "key": "foreign", "format": "other/format"}), encoding="utf-8")
    (folder / "k-nowriter.json").write_text(json.dumps({**current, "key": "nowriter", "writer": None}), encoding="utf-8")
    assert store.keys() == ["good"]
    for key in ("wrongkey", "notjson", "future", "novalue", "extra", "stray", "later", "uncounted", "boolean", "foreign", "nowriter"):
        assert store.retrieve(key) is None, key
    assert store.forget("novalue") is False and not (folder / "k-novalue.json").exists()  # housekeeping, never a live entry
    assert store.retrieve("other") is None  # the record under k-wrongkey.json names "other"; neither name finds it
    assert store.forget("wrongkey") is False and not (folder / "k-wrongkey.json").exists()
    try:
        (folder / "k-link.json").symlink_to(folder / "k-good.json")
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    assert store.retrieve("link") is None and "link" not in store.keys()
    with pytest.raises(ValueError, match="symlink"):
        store.stash("link", 2)
    assert store.forget("link") is False and (folder / "k-link.json").is_symlink()


def test_file_store_refuses_a_symlinked_scratch_directory(tmp_path):
    root = (tmp_path / "root").resolve()
    root.mkdir()
    elsewhere = (tmp_path / "elsewhere").resolve()
    elsewhere.mkdir()
    try:
        (root / "scratch").symlink_to(elsewhere, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    store = FileScratch(str(root), "unit")
    with pytest.raises(ValueError, match="cannot be, or sit in, a symlink"):
        store.stash("escaped", {"secret": 1})
    assert not list(elsewhere.rglob("*.json"))


def test_expired_entries_are_reclaimed_and_forget_says_so(tmp_path, monkeypatch):
    clock = Clock(monkeypatch)
    store = FileScratch(str(tmp_path.resolve()), "unit")
    folder = tmp_path.resolve() / "scratch" / "unit"
    store.stash("gone", 1, ttl_seconds=10)
    store.stash("stays", 2)
    clock.advance(11)
    assert store.forget("gone") is False and not (folder / "k-gone.json").exists()
    store.stash("gone2", 1, ttl_seconds=10)
    clock.advance(11)
    assert store.keys() == ["stays"]
    assert not (folder / "k-gone2.json").exists()  # keys() removed what had lapsed


def hold_lock(path, taken, released):
    """Hold the store's lock from another thread on its own descriptor, so it really conflicts."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        memory_scratch._lock_once(fd)
        taken.set()
        released.wait(10)
    finally:
        os.close(fd)


def test_file_compare_and_set_waits_for_the_store_lock_within_the_bound(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    store = FileScratch(str(root), "unit")
    store.stash("k", 1)
    monkeypatch.setattr(memory_scratch, "LOCK_RETRY_SECONDS", 0.2)
    taken, released = threading.Event(), threading.Event()
    holder = threading.Thread(target=hold_lock, args=(root / "scratch" / "unit" / ".scratch.lock", taken, released))
    holder.start()
    try:
        assert taken.wait(5)
        started = time.monotonic()
        with pytest.raises(ScratchRefused) as busy:
            store.stash("k", 2, expected_version=1)
        assert 0.2 <= time.monotonic() - started < 1.5
        assert str(busy.value) == (
            "Scratch stash of key 'k' was refused: another writer has held the store's lock for 0.2 seconds; "
            "nothing was written. Stash again once it lets go."
        )
        assert busy.value.found is None and store.retrieve("k")["value"] == 1
        assert store.stash("k", 2)["version"] == 2  # a stash with no expectation takes no lock
        monkeypatch.setattr(memory_scratch, "LOCK_RETRY_SECONDS", 2.0)  # the codebase bound, as shipped
        threading.Timer(0.1, released.set).start()
        assert store.stash("k", 3, expected_version=2)["version"] == 3  # the brief overlap becomes a grant
    finally:
        released.set()
        holder.join(5)

    def no_locks(fd):
        raise OSError(errno.ENOLCK, "No locks available")
    monkeypatch.setattr(memory_scratch, "_lock_once", no_locks)
    with pytest.raises(ScratchRefused, match=r"the file system refuses locks \(ENOLCK\), so the version cannot be compared"):
        store.stash("k", 4, expected_version=3)
    assert store.retrieve("k")["value"] == 3


# --- the redis store's own edges ------------------------------------------------


def test_redis_store_uses_ttl_and_scan_never_keys_and_stays_in_its_namespace():
    kv = FakeKV()
    store = RedisScratch(kv, "unit", host="fake:6379", errors=(FakeError,))
    store.stash("a", 1, ttl_seconds=30)
    store.stash("b", 2)
    assert ("SET", REDIS_PREFIX + "unit:a", 30) in kv.calls and ("SET", REDIS_PREFIX + "unit:b", None) in kv.calls
    kv.data["attune:memory:node:n1"] = ('{"not": "ours"}', None)
    kv.data[REDIS_PREFIX + "other:c"] = ('{"schema_version": 1, "key": "c", "value": 3}', None)
    assert store.keys() == ["a", "b"]
    assert all(call[1].startswith(REDIS_PREFIX + "unit:") for call in kv.calls if call[0] in ("SET", "GET", "DEL"))
    assert all(call[1] == REDIS_PREFIX + "unit:*" and call[2] == 500 for call in kv.calls if call[0] == "SCAN")
    assert {call[0] for call in kv.calls} <= {"SET", "GET", "DEL", "SCAN"}  # a plain stash is a GET and a SET
    kv.data[REDIS_PREFIX + "unit:bad"] = ("{not json", None)
    with pytest.raises(MemoryRedisUnavailable, match="malformed record"):
        store.retrieve("bad")
    kv.data[REDIS_PREFIX + "unit:swap"] = ('{"schema_version": 1, "key": "other", "value": 1, "stored_at": "x", "expires_at": null}', None)
    with pytest.raises(MemoryRedisUnavailable, match="not this key's"):
        store.retrieve("swap")
    kv.data[REDIS_PREFIX + "unit:novalue"] = ('{"schema_version": 1, "key": "novalue", "stored_at": "x", "expires_at": null}', None)
    with pytest.raises(MemoryRedisUnavailable, match="not this key's"):
        store.retrieve("novalue")
    kv.data[REDIS_PREFIX + "unit:raw"] = (b'{"schema_version":1,"key":"raw","value":7,"stored_at":"x","expires_at":null}', None)
    assert store.retrieve("raw")["value"] == 7  # a bytes reply is decoded, not repr'd


def test_redis_store_reports_a_failing_server_as_unavailable():
    class Broken(FakeKV):
        def get(self, name):
            raise FakeError("Connection lost")
    store = RedisScratch(Broken(), "unit", host="fake:6379", errors=(FakeError,))
    with pytest.raises(MemoryRedisUnavailable, match="fake:6379 failed during retrieve: FakeError: Connection lost"):
        store.retrieve("a")


# --- startup selection, and never a divert ---------------------------------------


def test_config_rules():
    assert validate_config(None) is None
    assert validate_config({"backend": "file", "root": "/x"}) == {"backend": "file", "root": "/x", "namespace": "harness"}
    assert validate_config({"backend": "redis", "namespace": "team-a"}) == {"backend": "redis", "namespace": "team-a"}
    for bad, message in (
        ("file", "must be an object"),
        ({}, "backend' must be one of"),
        ({"backend": "sqlite"}, "backend' must be one of"),
        ({"backend": "file"}, "root' is required"),
        ({"backend": "redis", "root": "/x"}, "applies to the file backend only"),
        ({"backend": "file", "root": "/x", "namespace": "Bad"}, "namespace"),
        ({"backend": "file", "root": "/x", "extra": 1}, "unknown keys"),
    ):
        with pytest.raises(ValueError, match=message):
            validate_config(bad)


def test_open_scratch_chooses_once_and_never_diverts(tmp_path):
    assert open_scratch({"roots": []}) is None
    root = str(tmp_path.resolve())
    assert isinstance(open_scratch({"scratch": {"backend": "file", "root": root}}), FileScratch)
    with pytest.raises(ValueError, match="no 'redis' section"):
        open_scratch({"scratch": {"backend": "redis"}})
    config = {"scratch": {"backend": "redis", "namespace": "unit"}, "redis": {"url": "redis://h:6379/0"}}

    def down(settings):
        raise MemoryRedisUnavailable("Redis memory at h:6379 is unreachable: refused")
    with pytest.raises(MemoryRedisUnavailable, match="unreachable"):
        open_scratch(config, open_redis=down)
    assert not (tmp_path / "scratch").exists()  # nothing was written anywhere
    kv = FakeKV()
    store = open_scratch(config, open_redis=lambda settings: (kv, "h:6379", (FakeError,)))
    assert isinstance(store, RedisScratch) and store.prefix == REDIS_PREFIX + "unit:"


def test_open_scratch_uses_the_shared_client_opener(monkeypatch):
    seen = {}
    def opener(settings, **kwargs):
        seen.update(settings)
        return FakeKV(), "h:6379", (FakeError,)
    monkeypatch.setattr(memory_scratch, "open_client", opener)
    store = open_scratch({"scratch": {"backend": "redis"}, "redis": {"url": "redis://h:6379/0"}})
    assert isinstance(store, RedisScratch) and seen["url"] == "redis://h:6379/0"


# --- run() and the command line ---------------------------------------------------


def test_run_envelopes(tmp_path):
    root = str(tmp_path.resolve())
    config = {"scratch": {"backend": "file", "root": root}}
    assert run({"roots": []}, "capabilities", {}) == {"status": "disabled", "detail": "The memory config has no 'scratch' section"}
    caps = run(config, "capabilities", {})
    assert caps["status"] == "ok" and caps["backend"] == "file" and caps["shared"] is False
    stored = run(config, "stash", {"key": "k", "value": {"a": 1}, "ttl": 60})
    assert stored["status"] == "ok" and stored["backend"] == "file" and stored["expires_at"]
    assert stored["format"] == FORMAT and stored["format_version"] == 2 and stored["version"] == 1
    assert stored["writer"] == memory_scratch.writer()
    found = run(config, "retrieve", {"key": "k"})
    assert found["value"] == {"a": 1} and found["version"] == 1 and found["writer"] == stored["writer"]
    assert run(config, "retrieve", {"key": "missing"}) == {"status": "no_results", "operation": "memory_scratch_retrieve", "backend": "file", "key": "missing"}
    assert run(config, "keys", {})["keys"] == ["k"]
    assert run(config, "forget", {"key": "k"})["forgotten"] is True
    assert run(config, "forget", {"key": "k"})["status"] == "no_results"
    assert run(config, "keys", {"pattern": "k*"})["status"] == "no_results"
    with pytest.raises(ValueError, match="Unknown scratch operation"):
        run(config, "flush", {})


def test_cli_scratch_verbs(tmp_path, capsys, monkeypatch):
    root = str((tmp_path / "root").resolve())
    Path(root).mkdir()
    config = tmp_path / "memory.json"
    config.write_text(json.dumps({"scratch": {"backend": "file", "root": root}}), encoding="utf-8")
    base = ["--config", str(config), "scratch"]
    assert memory_main([*base, "capabilities"]) == 0
    assert json.loads(capsys.readouterr().out)["backend"] == "file"
    assert memory_main([*base, "stash", "plan:current", "--value", '{"task": "4.2"}', "--ttl", "120"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok" and out["expires_at"] and out["version"] == 1 and out["format_version"] == 2
    value_file = tmp_path / "value.json"
    value_file.write_text('["from", "file"]', encoding="utf-8")
    assert memory_main([*base, "stash", "plan:list", "--value-file", str(value_file)]) == 0
    capsys.readouterr()
    assert memory_main([*base, "retrieve", "plan:list"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["value"] == ["from", "file"] and out["version"] == 1 and out["writer"] == memory_scratch.writer()
    assert memory_main([*base, "keys", "plan:*"]) == 0
    assert json.loads(capsys.readouterr().out)["keys"] == ["plan:current", "plan:list"]
    # --expected-version: the compare-and-set from the command line.
    assert memory_main([*base, "stash", "plan:list", "--value", "2", "--expected-version", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == 2
    assert memory_main([*base, "stash", "plan:list", "--value", "3", "--expected-version", "1"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "failed" and out["error"] == "ScratchRefused"
    assert out["expected_version"] == 1 and out["version"] == 2 and "found version 2; nothing was written" in out["detail"]
    assert memory_main([*base, "stash", "plan:list", "--value", "3", "--expected-version", "0"]) == 2
    assert "expected no record (version 0), found version 2" in json.loads(capsys.readouterr().out)["detail"]
    assert memory_main([*base, "stash", "plan:new", "--value", "1", "--expected-version", "0"]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == 1
    assert memory_main([*base, "stash", "plan:new", "--value", "1", "--expected-version", "-1"]) == 2
    assert "expected version must be an integer of 0 or more" in json.loads(capsys.readouterr().out)["detail"]
    assert memory_main([*base, "retrieve", "plan:list"]) == 0
    assert json.loads(capsys.readouterr().out)["value"] == 2
    assert memory_main([*base, "forget", "plan:list"]) == 0
    capsys.readouterr()
    assert memory_main([*base, "retrieve", "plan:list"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "no_results"
    assert memory_main([*base, "stash", "bad key", "--value", "1"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    assert memory_main([*base, "stash", "k", "--value", "{not json"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    config.write_text(json.dumps({"scratch": {"backend": "redis"}, "redis": {"url": "redis://h:6379/0"}}), encoding="utf-8")
    monkeypatch.setattr(memory_scratch, "open_client", lambda settings, **k: (_ for _ in ()).throw(MemoryRedisUnavailable("Redis memory at h:6379 is unreachable: refused")))
    before = sorted(str(p) for p in Path(root).rglob("*"))
    assert memory_main([*base, "capabilities"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "unavailable" and "unreachable" in out["detail"]
    assert memory_main([*base, "stash", "k", "--value", "1"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unavailable"
    assert memory_main([*base, "stash", "k", "--value", "1", "--expected-version", "0"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unavailable"
    assert sorted(str(p) for p in Path(root).rglob("*")) == before  # nothing was diverted to the file store
    config.write_text(json.dumps({"roots": []}), encoding="utf-8")
    assert memory_main([*base, "capabilities"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"


def test_cli_reports_an_uncertain_stash_with_exit_2(tmp_path, capsys, monkeypatch):
    root = str((tmp_path / "root").resolve())
    Path(root).mkdir()
    config = tmp_path / "memory.json"
    config.write_text(json.dumps({"scratch": {"backend": "file", "root": root}}), encoding="utf-8")
    base = ["--config", str(config), "scratch"]
    assert memory_main([*base, "stash", "k", "--value", "1"]) == 0
    capsys.readouterr()

    def refuse(source, target, **kwargs):
        raise PermissionError(errno.EACCES, "Access is denied")
    monkeypatch.setattr(memory_scratch, "replace_file", refuse)
    assert memory_main([*base, "stash", "k", "--value", "2"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "uncertain" and out["version"] == 2 and out["error"] == "PermissionError"
    assert out["detail"].startswith("Scratch stash of key 'k' may or may not have landed")


def test_importing_the_module_needs_no_redis_package():
    import subprocess
    import attune_harness
    code = "import sys\nsys.modules['redis'] = None\nfrom attune_harness import memory_scratch\nprint(memory_scratch.VALUE_LIMIT)\n"
    result = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True,
                            env={**os.environ, "PYTHONPATH": str(Path(attune_harness.__file__).resolve().parents[1])})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(VALUE_LIMIT)


# --- live, only where a Redis is named -----------------------------------------------


@pytest.mark.skipif(not os.environ.get("ATTUNE_TEST_REDIS_URL"), reason="ATTUNE_TEST_REDIS_URL names no live Redis")
def test_live_redis_scratch_round_trips_under_its_own_namespace():
    pytest.importorskip("redis")
    config = {"scratch": {"backend": "redis", "namespace": "livetest"}, "redis": {"url": os.environ["ATTUNE_TEST_REDIS_URL"]}}
    store = open_scratch(config)
    key = "harness:live:" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    try:
        stored = store.stash(key, {"ok": True}, ttl_seconds=120)
        assert stored["version"] == 1 and stored["format_version"] == 2
        assert store.retrieve(key)["value"] == {"ok": True}
        assert key in store.keys("harness:live:*")
        assert store.client.ttl(REDIS_PREFIX + "livetest:" + key) > 0
        # The compare-and-set against a real server: WATCH/MULTI/EXEC, then SET NX.
        assert store.stash(key, {"ok": 2}, ttl_seconds=120, expected_version=1)["version"] == 2
        with pytest.raises(ScratchRefused, match="expected version 1, found version 2"):
            store.stash(key, {"ok": 3}, expected_version=1)
        with pytest.raises(ScratchRefused, match=r"expected no record \(version 0\), found version 2"):
            store.stash(key, {"ok": 3}, expected_version=0)
        assert store.retrieve(key)["value"] == {"ok": 2} and store.client.ttl(REDIS_PREFIX + "livetest:" + key) > 0
    finally:
        assert store.forget(key) is True
    assert store.retrieve(key) is None
