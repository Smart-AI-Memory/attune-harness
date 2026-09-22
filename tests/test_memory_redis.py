"""The Redis memory reads, against an in-process double that knows the contract.

Native memory Task 4.1 (D18). CI has no Redis. ``FakeRedis`` answers exactly
the commands the module may issue and refuses any other, so a new write or a
new command shows up as a failure here. A live run against a real hydrated
Redis Stack happens only when ``ATTUNE_TEST_REDIS_URL`` is set.
"""
# qualify: platform

import json
import os
import sys
import types

import pytest

from attune_harness import memory_cli, memory_redis
from attune_harness.features import FeatureUnavailable
from attune_harness.memory_cli import main as memory_main
from attune_harness.memory_redis import (
    INDEX,
    LAYERS,
    LIBRARY,
    POINTER_FIELDS,
    PREFIX,
    MemoryRedisUnavailable,
    RedisMemory,
    connect,
    read,
    validate_config,
)


class FakeError(Exception):
    pass


class FakeRedis:
    """A hydrated keyspace: two curated nodes, one file pointer, one rule, one lesson; the two functions.

    One key outside the prefix (``other:leak``) matches every query, so the
    reply filter has something to drop.
    """

    def __init__(self, *, index=True, functions=True):
        self.calls = []
        self.has_index = index
        self.has_functions = functions
        self.strings = {f"{PREFIX}hydrated_at": "2026-09-22T12:00:00+00:00", f"{PREFIX}context": "release runbook"}
        self.sets = {f"{PREFIX}status:active": {"n1", "n2"}}
        self.hashes = {
            f"{PREFIX}node:n1": dict(name="Release runbook", description="How a release reaches PyPI", type="reference",
                                     status="active", layer="curated", tags="release,pypi", updated_at="2026-09-21"),
            f"{PREFIX}node:n2": dict(name="Lease rule", description="Never divert a write", type="rule",
                                     status="active", layer="curated", tags="memory", updated_at="2026-09-19"),
            f"{PREFIX}file:proj:state": dict(name="State 09-21", description="What is live", type="project",
                                              layer="file", corpus="proj", path="/home/p/state.md", text="SECRET BODY"),
            f"{PREFIX}rule:cadence": dict(name="cadence", description="Lane cadence cap", layer="rule",
                                           corpus="rules-tail", path="/home/p/rules/cadence.md", text="rule body"),
            f"{PREFIX}lesson:12": dict(name="Read before merge", description="Read before merge", layer="lesson",
                                        corpus="lessons", path="/home/p/lessons.md", line="12", text="lesson body"),
            "other:leak": dict(name="leak", description="release runbook state cadence lease", layer="curated", text="x"),
        }
        self.lists = {f"{PREFIX}edges:n1": [json.dumps({"target": "n2", "type": "relates_to"})]}

    def ping(self):
        self.calls.append(("PING",))
        return True

    def get(self, key):
        self.calls.append(("GET", key))
        return self.strings.get(key)

    def scard(self, key):
        self.calls.append(("SCARD", key))
        return len(self.sets.get(key, ()))

    def hgetall(self, key):
        self.calls.append(("HGETALL", key))
        return dict(self.hashes.get(key, {}))

    def execute_command(self, name, *args):
        self.calls.append((name, *args))
        if name == "FT.INFO":
            if not self.has_index:
                raise FakeError("Unknown index name")
            return ["index_name", args[0]]
        if name == "FUNCTION" and args[:2] == ("LIST", "LIBRARYNAME"):
            return [["library_name", args[2]]] if self.has_functions and args[2] == LIBRARY else []
        if name == "FT.SEARCH":
            return self._search(*args)
        if name == "FCALL_RO":
            if not self.has_functions:
                raise FakeError("Function not found")
            return self._function(args[0], args[2:])
        raise AssertionError(f"command outside the contract: {name}")

    def _search(self, index, query, *rest):
        assert index == INDEX
        rest = list(rest)
        returned = []
        if "RETURN" in rest:
            at = rest.index("RETURN")
            returned = rest[at + 2: at + 2 + int(rest[at + 1])]
        limit = int(rest[rest.index("LIMIT") + 2])
        layer, words = None, []
        for token in query.split():
            if token.startswith("@layer:{"):
                layer = token[len("@layer:{"):-1]
            else:
                words.append(token.replace("\\", "").lower())
        hits = []
        for key, fields in self.hashes.items():
            if layer and fields.get("layer") != layer:
                continue
            hay = " ".join(str(v) for v in fields.values()).lower()
            if all(word in hay for word in words):
                hits.append(key)
        reply = [len(hits)]
        for key in hits[:limit]:
            fields = self.hashes[key]
            pairs = []
            for name in (returned or fields):
                if name in fields:
                    pairs += [name, fields[name]]
            reply += [key, pairs]
        return reply

    def _function(self, function, args):
        if function == "recall_digest":
            out = []
            for ident in sorted(self.sets[f"{PREFIX}status:active"]):
                f = self.hashes[f"{PREFIX}node:{ident}"]
                out.append(json.dumps(dict(id=ident, type=f["type"], name=f["name"], description=f["description"],
                                           updated_at=f["updated_at"], score=1,
                                           edges=self.lists.get(f"{PREFIX}edges:{ident}", []))))
            return out[:int(args[0])]
        if function == "recall_related":
            ident = args[0]
            key = f"{PREFIX}{ident}" if ident.startswith("file:") else f"{PREFIX}node:{ident}"
            if key not in self.hashes:
                return []
            f = self.hashes[key]
            # cjson encodes a missing HMGET field as false.
            out = [json.dumps(dict(id=ident, name=f["name"], description=f["description"], path=f.get("path", False),
                                   layer=f.get("layer"), type=f.get("type", False)))]
            for edge in self.lists.get(f"{PREFIX}edges:{ident}", []):
                target = json.loads(edge)["target"]
                t = self.hashes[f"{PREFIX}node:{target}"]
                out.append(json.dumps(dict(id=target, name=t["name"], description=t["description"], path=False,
                                           layer=t["layer"], type=t["type"], edge_type=json.loads(edge)["type"])))
            return out
        raise AssertionError(f"function outside the contract: {function}")


SETTINGS = {"url": "redis://memory.example:6380/0", "index": INDEX}


def memory(fake=None):
    fake = fake or FakeRedis()
    return RedisMemory(fake, SETTINGS, "memory.example:6380", errors=(FakeError,)), fake


# --- config -------------------------------------------------------------------


def test_config_defaults_and_refusals():
    assert validate_config(None) is None
    assert validate_config({"url": "redis://h"}) == {"url": "redis://h", "index": INDEX}
    assert validate_config({"url_env": "MEMORY_REDIS_URL", "password_env": "MEMORY_REDIS_PASSWORD"})["url_env"] == "MEMORY_REDIS_URL"
    for bad, message in (
        ("redis://h", "must be an object"),
        ({}, "exactly one"),
        ({"url": "redis://h", "url_env": "X"}, "exactly one"),
        ({"url": ""}, "non-empty"),
        ({"url": "redis://h", "extra": 1}, "unknown keys"),
        ({"url": "redis://h", "prefix": "x:"}, "unknown keys"),
        ({"url": "redis://h", "index": "bad name"}, "not an index name"),
    ):
        with pytest.raises(ValueError, match=message):
            validate_config(bad)


def test_layers_agree_between_module_and_cli():
    assert memory_cli.REDIS_LAYERS == LAYERS == ("curated", "file", "lesson", "rule")


def test_url_from_the_environment_only_when_named_and_ports_checked(monkeypatch):
    settings = validate_config({"url_env": "MEMORY_REDIS_URL"})
    monkeypatch.delenv("MEMORY_REDIS_URL", raising=False)
    with pytest.raises(MemoryRedisUnavailable, match="MEMORY_REDIS_URL, which is unset"):
        memory_redis.resolve_url(settings)
    monkeypatch.setenv("MEMORY_REDIS_URL", "rediss://user:pw@host:6380/1")
    assert memory_redis.resolve_url(settings) == "rediss://user:pw@host:6380/1"
    with pytest.raises(MemoryRedisUnavailable, match="redis:// or rediss://"):
        memory_redis.resolve_url({"url": "http://host"})
    for url in ("redis://host:notaport/0", "redis://host:99999/0"):
        with pytest.raises(MemoryRedisUnavailable, match="invalid port"):
            memory_redis.resolve_url({"url": url})


# --- connect ------------------------------------------------------------------


def _library(monkeypatch, factory):
    exceptions = types.SimpleNamespace(RedisError=FakeError)
    library = types.SimpleNamespace(Redis=types.SimpleNamespace(from_url=factory), exceptions=exceptions)
    monkeypatch.setattr(memory_redis, "require_feature", lambda *a, **k: library)
    return library


def test_connect_without_the_extra_names_it(monkeypatch):
    def missing(*args, **kwargs):
        raise FeatureUnavailable("Install attune-harness[redis]; redis is missing")
    monkeypatch.setattr(memory_redis, "require_feature", missing)
    with pytest.raises(FeatureUnavailable, match=r"attune-harness\[redis\]"):
        connect(SETTINGS)


def test_connect_reports_each_way_of_being_unusable_distinctly(monkeypatch):
    def refused(url, **options):
        raise FakeError("Connection refused")
    _library(monkeypatch, refused)
    with pytest.raises(MemoryRedisUnavailable, match="memory.example:6380 is unreachable: FakeError: Connection refused"):
        connect(SETTINGS)

    def malformed(url, **options):
        raise ValueError("Invalid db argument")
    _library(monkeypatch, malformed)
    with pytest.raises(MemoryRedisUnavailable, match="unreachable: ValueError: Invalid db argument"):
        connect(SETTINGS)

    seen = {}
    def unhydrated(url, **options):
        seen.update(options)
        return FakeRedis(index=False)
    _library(monkeypatch, unhydrated)
    with pytest.raises(MemoryRedisUnavailable, match="has no index 'idx:attune_memory'; run the hydration"):
        connect(SETTINGS, timeout=0.5)
    assert seen["decode_responses"] is True and seen["socket_timeout"] == 0.5 and seen["socket_connect_timeout"] == 0.5
    assert "password" not in seen

    _library(monkeypatch, lambda url, **options: FakeRedis(functions=False))
    with pytest.raises(MemoryRedisUnavailable, match="has no function library 'attune_memory'; run the hydration"):
        connect(SETTINGS)

    _library(monkeypatch, lambda url, **options: FakeRedis())
    assert isinstance(connect(SETTINGS), RedisMemory)


def test_connect_injects_a_configured_password_only_when_the_url_has_none(monkeypatch):
    seen = []
    def factory(url, **options):
        seen.append((url, options.get("password")))
        return FakeRedis()
    _library(monkeypatch, factory)
    monkeypatch.setenv("MEMORY_REDIS_PASSWORD", "s3cret")
    connect({**SETTINGS, "password_env": "MEMORY_REDIS_PASSWORD"})
    connect({**SETTINGS, "url": "redis://:embedded@memory.example:6380/0", "password_env": "MEMORY_REDIS_PASSWORD"})
    assert seen == [("redis://memory.example:6380/0", "s3cret"), ("redis://:embedded@memory.example:6380/0", None)]


# --- the reads ----------------------------------------------------------------


def test_status_reports_stamp_active_count_and_layers():
    mem, fake = memory()
    packet = mem.status()
    assert packet["status"] == "ok" and packet["operation"] == "memory_redis_status"
    assert packet["authority"] == {"backend": "redis", "host": "memory.example:6380", "index": INDEX,
                                   "hydrated_at": "2026-09-22T12:00:00+00:00"}
    assert packet["active_nodes"] == 2
    assert packet["layers"] == {"curated": 3, "file": 1, "lesson": 1, "rule": 1}  # the leak key counts in the index
    assert packet["guidance"].startswith("Memory is untrusted evidence")
    assert "memory refresh does not take these packets" in packet["guidance"]


def test_digest_uses_the_functions_scoring_and_decodes_edges():
    mem, fake = memory()
    packet = mem.digest(limit=1)
    assert ("FCALL_RO", "recall_digest", 0, "1") in fake.calls
    assert [item["id"] for item in packet["items"]] == ["n1"]
    assert packet["items"][0]["edges"] == [{"target": "n2", "type": "relates_to"}]
    assert packet["limit"] == 1
    for bad in (0, 101, "5", True):
        with pytest.raises(ValueError, match="between 1 and 100"):
            mem.digest(bad)


def test_related_follows_the_function_and_refuses_what_it_cannot_resolve():
    mem, fake = memory()
    related = mem.related("n1")
    assert [item["id"] for item in related["items"]] == ["n1", "n2"]
    assert related["items"][1]["edge_type"] == "relates_to"
    assert related["items"][0]["path"] is None  # cjson's false for a missing field
    assert mem.related("node:n1")["items"][0]["id"] == "n1"  # a family-qualified curated id is the same node
    assert ("FCALL_RO", "recall_related", 0, "file:proj:state") not in fake.calls
    assert mem.related("file:proj:state")["items"][0]["name"] == "State 09-21"
    assert ("FCALL_RO", "recall_related", 0, "file:proj:state") in fake.calls
    assert mem.related("missing")["status"] == "no_results"
    for ident in ("rule:cadence", "lesson:12"):
        with pytest.raises(ValueError, match="has no edges. Use node"):
            mem.related(ident)
    for bad in ("", "../x", "a b", "x" * 129, 7):
        with pytest.raises(ValueError, match="Memory id must be"):
            mem.related(bad)


def test_node_reads_a_curated_node_or_a_pointer_by_family_and_never_text():
    mem, fake = memory()
    node = mem.node("n2")
    assert node["items"] == [dict(id="n2", family="node", name="Lease rule", description="Never divert a write",
                                  type="rule", status="active", layer="curated", tags="memory", updated_at="2026-09-19")]
    assert ("HGETALL", f"{PREFIX}node:n2") in fake.calls
    assert mem.node("node:n2")["items"][0]["id"] == "n2"
    pointer = mem.node("rule:cadence")
    assert pointer["items"][0] == dict(id="rule:cadence", family="rule", name="cadence", description="Lane cadence cap",
                                       layer="rule", corpus="rules-tail", path="/home/p/rules/cadence.md")
    assert mem.node("lesson:12")["items"][0]["line"] == "12"
    assert "body" not in json.dumps(mem.node("file:proj:state"))
    assert mem.node("absent")["status"] == "no_results"
    for bad in ("", "../x", "a b", "x" * 129, 7):
        with pytest.raises(ValueError, match="Memory id must be"):
            mem.node(bad)


def test_search_returns_addressable_ids_never_text_and_escapes_the_query():
    mem, fake = memory()
    packet = mem.search("state 09-21", k=5)
    call = next(c for c in fake.calls if c[0] == "FT.SEARCH" and "state" in c[2])
    assert call[2] == "state 09\\-21"
    assert call[3:5] == ("RETURN", len(POINTER_FIELDS)) and "text" not in call
    assert call[-5:] == ("LIMIT", 0, 5, "DIALECT", 2)
    assert packet["items"] == [dict(id="file:proj:state", family="file", name="State 09-21", description="What is live",
                                    type="project", layer="file", corpus="proj", path="/home/p/state.md")]
    assert "SECRET" not in json.dumps(packet)
    assert packet["total"] == 1 and packet["status"] == "ok"
    leaky = mem.search("state")  # the out-of-prefix key matches this one: counted by the index, dropped here
    assert leaky["total"] == 2 and [item["id"] for item in leaky["items"]] == ["file:proj:state"]
    by_layer = mem.search("cadence", layer="rule")
    assert next(c for c in fake.calls if c[0] == "FT.SEARCH" and "cadence" in c[2])[2] == "@layer:{rule} cadence"
    assert [item["id"] for item in by_layer["items"]] == ["rule:cadence"]
    curated = mem.search("release", layer="curated")
    assert [(item["id"], item["family"]) for item in curated["items"]] == [("n1", "node")]
    assert mem.search("zyxw9876")["status"] == "no_results"
    with pytest.raises(ValueError, match="needs a query"):
        mem.search("  ")
    with pytest.raises(ValueError, match="limited to 512"):
        mem.search("x" * 513)
    with pytest.raises(ValueError, match="layer must be one of"):
        mem.search("x", layer="secret")
    for bad in (0, 101):
        with pytest.raises(ValueError, match="between 1 and 100"):
            mem.search("x", k=bad)


def test_every_search_id_resolves_through_node_and_related_where_defined():
    """The blocker the reviewer found: a handed-back id must be one the other verbs accept."""
    mem, fake = memory()
    seen = set()
    for layer in LAYERS:
        for item in mem.search("e", layer=layer, k=50)["items"]:
            seen.add(item["id"])
            got = mem.node(item["id"])
            assert got["status"] == "ok" and got["items"][0]["id"] == item["id"], item
            if item["family"] in ("node", "file"):
                assert mem.related(item["id"])["items"][0]["id"] == item["id"]
            else:
                with pytest.raises(ValueError, match="Use node"):
                    mem.related(item["id"])
    assert {"n1", "n2", "file:proj:state", "rule:cadence", "lesson:12"} <= seen
    assert not any(ident.startswith("node:") or ident.startswith("other") for ident in seen)


def test_every_command_issued_is_a_read():
    mem, fake = memory()
    mem.require_hydration(); mem.status(); mem.digest(); mem.related("n1"); mem.node("n1"); mem.search("release")
    names = {call[0] for call in fake.calls}
    assert names == {"GET", "SCARD", "HGETALL", "FT.SEARCH", "FCALL_RO", "FT.INFO", "FUNCTION"}
    assert all(call[1:3] == ("LIST", "LIBRARYNAME") for call in fake.calls if call[0] == "FUNCTION")


def test_a_failure_or_a_malformed_reply_mid_read_is_unavailable():
    mem, fake = memory(FakeRedis(functions=False))
    with pytest.raises(MemoryRedisUnavailable, match="failed during recall_digest: FakeError: Function not found"):
        mem.digest()
    with pytest.raises(MemoryRedisUnavailable, match="malformed digest record"):
        RedisMemory(_Malformed(), SETTINGS, "h", errors=(FakeError,)).digest()
    with pytest.raises(MemoryRedisUnavailable, match="malformed digest record"):
        RedisMemory(_NotJson(), SETTINGS, "h", errors=(FakeError,)).digest()
    with pytest.raises(MemoryRedisUnavailable, match="malformed search reply"):
        RedisMemory(_BadTotal(), SETTINGS, "h", errors=(FakeError,)).search("x")


class _Malformed(FakeRedis):
    def _function(self, function, args):
        return ["[1, 2]"]


class _NotJson(FakeRedis):
    def _function(self, function, args):
        return ["{not json"]


class _BadTotal(FakeRedis):
    def _search(self, *args):
        return ["many"]


# --- read() and the command line ----------------------------------------------


def test_read_is_disabled_without_a_redis_section_and_dispatches_with_one():
    assert read({"roots": []}, "status", {}) == {"status": "disabled", "detail": "The memory config has no 'redis' section"}
    fake = FakeRedis()
    opened = lambda settings: RedisMemory(fake, settings, "h", errors=(FakeError,))
    config = {"redis": SETTINGS}
    assert read(config, "status", {}, connect_with=opened)["active_nodes"] == 2
    assert read(config, "node", {"id": "n1"}, connect_with=opened)["items"][0]["name"] == "Release runbook"
    assert read(config, "search", {"query": "divert", "layer": "curated", "k": 3}, connect_with=opened)["items"][0]["id"] == "n2"
    with pytest.raises(ValueError, match="Unknown Redis memory operation"):
        read(config, "write", {}, connect_with=opened)


def test_cli_redis_verbs(tmp_path, capsys, monkeypatch):
    # configure_process points structlog at the sys.stderr of the moment, which
    # under capture is a stream pytest closes after the test; later tests would
    # then fail with "I/O operation on closed file". It is process start-up
    # work, not part of what this test proves.
    monkeypatch.setattr(memory_cli, "configure_process", lambda: None)
    config = tmp_path / "memory.json"
    config.write_text(json.dumps({"redis": SETTINGS}), encoding="utf-8")
    fake = FakeRedis()
    monkeypatch.setattr(memory_redis, "connect", lambda settings, **k: RedisMemory(fake, settings, "h", errors=(FakeError,)))
    assert memory_main(["--config", str(config), "redis", "digest", "--limit", "2"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["operation"] == "memory_redis_digest" and len(out["items"]) == 2
    assert memory_main(["--config", str(config), "redis", "search", "runbook", "--layer", "curated", "--k", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == "n1"
    assert memory_main(["--config", str(config), "redis", "node", "nobody"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "no_results"
    assert memory_main(["--config", str(config), "redis", "related", "rule:cadence"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    monkeypatch.setattr(memory_redis, "connect", lambda settings, **k: (_ for _ in ()).throw(MemoryRedisUnavailable("Redis memory at h is unreachable: refused")))
    assert memory_main(["--config", str(config), "redis", "status"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out == {"status": "unavailable", "detail": "Redis memory at h is unreachable: refused", "error": "MemoryRedisUnavailable"}
    config.write_text(json.dumps({"roots": []}), encoding="utf-8")
    assert memory_main(["--config", str(config), "redis", "status"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"


def test_importing_the_module_needs_no_redis_package():
    code = ("import sys\nsys.modules['redis'] = None\n"
            "from attune_harness import memory_redis\n"
            "print(memory_redis.REDIS_VERSION)\n")
    import subprocess
    from pathlib import Path
    import attune_harness
    result = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True,
                            env={**os.environ, "PYTHONPATH": str(Path(attune_harness.__file__).resolve().parents[1])})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "5.3.1"


# --- live, only where a hydrated Redis Stack is named ---------------------------


@pytest.mark.skipif(not os.environ.get("ATTUNE_TEST_REDIS_URL"), reason="ATTUNE_TEST_REDIS_URL names no live Redis")
def test_live_hydrated_redis_answers_every_read():
    """What CI cannot check: the module's assumptions against a real hydration."""
    pytest.importorskip("redis")
    mem = connect(validate_config({"url": os.environ["ATTUNE_TEST_REDIS_URL"]}))
    packet = mem.status()
    assert packet["status"] == "ok" and packet["authority"]["hydrated_at"]
    assert packet["layers"]["curated"] > 0 and packet["layers"]["file"] > 0
    digest = mem.digest(limit=3)
    assert digest["status"] == "ok" and digest["items"]
    first = digest["items"][0]["id"]
    assert mem.node(first)["items"][0]["id"] == first
    assert mem.related(first)["items"][0]["id"] == first
    found = mem.search("memory", layer="file", k=5)
    assert found["total"] > 0 and found["items"]
    assert all(item["path"] for item in found["items"])  # path comes back from the hash, not the index schema
    assert "text" not in json.dumps(found)
    for item in found["items"]:
        assert mem.node(item["id"])["status"] == "ok"
