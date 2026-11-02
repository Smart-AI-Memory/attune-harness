"""Legacy reply accounting and URL controls, without opening a Redis socket."""
# qualify: platform

import json

import pytest

from attune_harness import memory_redis
from attune_harness.review_contract import canonical
from test_memory_redis import PREFIX, SETTINGS, _library, memory


@pytest.mark.parametrize("operation", ["node", "search", "digest", "related"])
@pytest.mark.parametrize("character", ["x", "é", "🦊", "\n"])
def test_complete_packet_exact_boundary_and_one_byte_over(operation, character):
    mem, fake = memory()
    fake.lists.clear()
    fields = fake.hashes[PREFIX + "node:n1"]
    fields["description"] = ""
    call = {"node": lambda: mem.node("n1"), "search": lambda: mem.search("runbook", k=1),
            "digest": lambda: mem.digest(1), "related": lambda: mem.related("n1")}[operation]
    room = memory_redis.REPLY_LIMIT - len(canonical(call()).encode("utf-8"))
    unit = len(canonical(character).encode("utf-8")) - 2
    fields["description"] = character * (room // unit) + "x" * (room % unit)
    packet = call()
    assert len(canonical(packet).encode("utf-8")) == memory_redis.REPLY_LIMIT
    assert packet["items"][0]["description"] == fields["description"]
    fields["description"] += "x"
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match="1 MiB packet bound"):
        call()


@pytest.mark.parametrize("operation", ["status", "node", "search", "digest", "related"])
def test_authority_metadata_is_included_in_the_limit(operation):
    mem, fake = memory()
    fake.strings[PREFIX + "hydrated_at"] = "x" * memory_redis.REPLY_LIMIT
    call = {"status": mem.status, "node": lambda: mem.node("n1"),
            "search": lambda: mem.search("runbook"), "digest": mem.digest,
            "related": lambda: mem.related("n1")}[operation]
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match="1 MiB packet bound"):
        call()


@pytest.mark.parametrize("operation", ["digest", "related", "search"])
def test_aggregate_refuses_before_decoding_or_retaining_later_items(operation):
    mem, fake = memory()
    # Each record is admitted on its own; their aggregate is too large. A late
    # malformed row must remain unprocessed once the cumulative bound is crossed.
    big = "x" * 600_000
    if operation == "search":
        class LateRow(list):
            def __iter__(self):
                raise AssertionError("read after packet bound")
            def __getitem__(self, key):
                raise AssertionError("read after packet bound")
        fake._search = lambda *args: [3, PREFIX + "node:a", ["description", big],
                                     PREFIX + "node:b", ["description", big],
                                     PREFIX + "node:c", LateRow()]
        call = lambda: mem.search("anything")
    else:
        raw = [json.dumps({"description": big}), json.dumps({"description": big}), "malformed"]
        fake._function = lambda *args: raw
        call = mem.digest if operation == "digest" else lambda: mem.related("n1")
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match="1 MiB packet bound"):
        call()


def test_nested_digest_edges_and_envelope_count_toward_limit():
    mem, fake = memory()
    edge = json.dumps({"target": "x" * 500_000})
    fake._function = lambda *args: [json.dumps({"edges": [edge]}), json.dumps({"edges": [edge]})]
    packet = mem.digest()
    assert len(canonical(packet).encode("utf-8")) < memory_redis.REPLY_LIMIT
    fake._function = lambda *args: [json.dumps({"edges": [edge]})] * 3
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match="1 MiB packet bound"):
        mem.digest()


@pytest.mark.parametrize("value", [float("nan"), {"invalid"}, b"invalid"])
def test_unserializable_or_nonfinite_reply_refuses_whole(value):
    mem, fake = memory()
    fake.hashes[PREFIX + "node:n1"]["description"] = value
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match="reply is malformed"):
        mem.node("n1")


@pytest.mark.parametrize("query", [
    "socket_timeout=0", "socket_timeout=99", "socket_connect_timeout=500",
    "decode_responses=false", "encoding=latin-1", "encoding_errors=ignore",
    "%73ocket_timeout=99", "socket_timeout=&socket_timeout=99", "socket_timeout=",
    "socket_timeout", "db=2&encoding=utf-8", "encoding_errors=strict",
])
def test_host_owned_url_options_refuse_before_creating_a_client(monkeypatch, query):
    def forbidden(*args, **kwargs):
        pytest.fail("client created for refused URL")
    _library(monkeypatch, forbidden)
    settings = {**SETTINGS, "url": "redis://user:secret@host/0?" + query}
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match="remove socket_timeout") as caught:
        memory_redis.open_client(settings)
    assert "secret" not in str(caught.value)


def test_real_pinned_client_url_precedence_and_preserved_connection_options(monkeypatch):
    redis = pytest.importorskip("redis")
    assert redis.__version__ == memory_redis.REDIS_VERSION
    # This uses redis-py's real URL parser and connection pool, but no socket.
    monkeypatch.setattr(redis.Redis, "ping", lambda self: True)
    overridden = redis.Redis.from_url("redis://example.invalid/0?socket_timeout=99", socket_timeout=2)
    assert overridden.connection_pool.connection_kwargs["socket_timeout"] == 99
    client, host, _ = memory_redis.open_client({"url": (
        "rediss://example.invalid:6380/1?db=2&ssl_cert_reqs=required"
        "&ssl_check_hostname=true&health_check_interval=10&retry_on_timeout=true"
    )}, timeout=0.7)
    options = client.connection_pool.connection_kwargs
    assert options["db"] == 2 and options["ssl_cert_reqs"] == "required"
    assert options["ssl_check_hostname"] is True
    assert options["health_check_interval"] == 10 and options["retry_on_timeout"] is True
    assert options["socket_timeout"] == options["socket_connect_timeout"] == 0.7
    assert options["decode_responses"] is True
    assert options["encoding"] == "utf-8" and options["encoding_errors"] == "strict"
    assert host == "example.invalid:6380"


@pytest.mark.parametrize("operation", ["digest", "related"])
def test_parser_recursion_error_is_reported_as_unavailable(monkeypatch, operation):
    mem, fake = memory()
    raw = '{"id":"n1"}'
    failure = RecursionError("parser nesting exhausted")
    seen = []
    def exhausted(value, limit):
        seen.append((value, limit))
        raise failure
    monkeypatch.setattr(memory_redis, "parse_json", exhausted)
    fake._function = lambda *args: [raw]
    call = mem.digest if operation == "digest" else lambda: mem.related("n1")
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match=f"malformed {operation} record") as caught:
        call()
    assert seen == [(raw, memory_redis.REPLY_LIMIT)]
    assert "check the hydrated records" in str(caught.value)
    assert caught.value.__cause__ is failure
