"""Working memory: one contract, two backends, chosen once and never diverted.

Native memory Task 4.2 (D18). The file store runs for real under ``tmp_path``.
The Redis store runs against ``FakeKV``, an in-process double that answers
only the commands the store may issue (SET with EX, GET, DEL, SCAN) with a
clock the test controls, so expiry is exercised without waiting. A live run
against a real Redis happens only when ``ATTUNE_TEST_REDIS_URL`` is set, under
its own namespace, and removes what it wrote.
"""
# qualify: platform

import fnmatch
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune_harness import memory_cli, memory_redis, memory_scratch
from attune_harness.memory_cli import main as memory_main
from attune_harness.memory_redis import MemoryRedisUnavailable
from attune_harness.memory_scratch import (
    REDIS_PREFIX,
    TTL_MAX,
    VALUE_LIMIT,
    FileScratch,
    RedisScratch,
    ScratchBackend,
    open_scratch,
    run,
    validate_config,
)


class FakeError(Exception):
    pass


class FakeKV:
    """SET/GET/DEL/SCAN with a controllable clock; anything else is outside the contract."""

    def __init__(self):
        self.data = {}   # name -> (value, expires_at or None)
        self.now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
        self.calls = []

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

    def set(self, name, value, ex=None):
        self.calls.append(("SET", name, ex))
        assert ex is None or (isinstance(ex, int) and ex > 0)
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
    for bad in ("", "a b", "[abc]", "x" * 129, "../*"):
        with pytest.raises(ValueError, match="pattern"):
            backend.keys(bad)


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
    assert files == ["k-plan%3Aa.b.json"]  # ':' is percent-encoded so the name is valid everywhere
    record = json.loads((root / "scratch" / "unit" / "k-plan%3Aa.b.json").read_text(encoding="utf-8"))
    assert record["schema_version"] == 1 and record["key"] == "plan:a.b" and record["value"] == {"v": 1}
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
    (folder / "stray.txt").write_text("x", encoding="utf-8")
    (folder / "k-notjson.json").write_text("{", encoding="utf-8")
    (folder / "k-wrongkey.json").write_text(json.dumps({"schema_version": 1, "key": "other", "value": 1, "stored_at": "x", "expires_at": None}), encoding="utf-8")
    (folder / "k-future.json").write_text(json.dumps({"schema_version": 2, "key": "future", "value": 1, "stored_at": "x", "expires_at": None}), encoding="utf-8")
    (folder / "k-novalue.json").write_text(json.dumps({"schema_version": 1, "key": "novalue", "stored_at": "x", "expires_at": None}), encoding="utf-8")
    (folder / "k-extra.json").write_text(json.dumps({"schema_version": 1, "key": "extra", "value": 1, "stored_at": "x", "expires_at": None, "more": 1}), encoding="utf-8")
    assert store.keys() == ["good"]
    for key in ("wrongkey", "notjson", "future", "novalue", "extra", "stray"):
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


def test_a_failing_write_leaves_no_temporary_file(tmp_path, monkeypatch):
    store = FileScratch(str(tmp_path.resolve()), "unit")
    store.stash("seed", 1)
    def refuse(source, target, **kwargs):
        raise OSError("disk says no")
    monkeypatch.setattr(memory_scratch, "replace_file", refuse)
    with pytest.raises(OSError, match="disk says no"):
        store.stash("seed", 2)
    folder = tmp_path.resolve() / "scratch" / "unit"
    assert sorted(p.name for p in folder.iterdir()) == ["k-seed.json"]
    assert json.loads((folder / "k-seed.json").read_text(encoding="utf-8"))["value"] == 1


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
    assert {call[0] for call in kv.calls} <= {"SET", "GET", "DEL", "SCAN"}
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
    assert run(config, "retrieve", {"key": "k"})["value"] == {"a": 1}
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
    assert out["status"] == "ok" and out["expires_at"]
    value_file = tmp_path / "value.json"
    value_file.write_text('["from", "file"]', encoding="utf-8")
    assert memory_main([*base, "stash", "plan:list", "--value-file", str(value_file)]) == 0
    capsys.readouterr()
    assert memory_main([*base, "retrieve", "plan:list"]) == 0
    assert json.loads(capsys.readouterr().out)["value"] == ["from", "file"]
    assert memory_main([*base, "keys", "plan:*"]) == 0
    assert json.loads(capsys.readouterr().out)["keys"] == ["plan:current", "plan:list"]
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
    assert sorted(str(p) for p in Path(root).rglob("*")) == before  # nothing was diverted to the file store
    config.write_text(json.dumps({"roots": []}), encoding="utf-8")
    assert memory_main([*base, "capabilities"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"


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
        store.stash(key, {"ok": True}, ttl_seconds=120)
        assert store.retrieve(key)["value"] == {"ok": True}
        assert key in store.keys("harness:live:*")
        assert store.client.ttl(REDIS_PREFIX + "livetest:" + key) > 0
    finally:
        assert store.forget(key) is True
    assert store.retrieve(key) is None
