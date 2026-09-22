"""Read the Redis memory a hydration keeps warm; the ``[redis]`` extra, read-only.

Native memory Task 4.1 (D16, D18). The memory Patrick runs is a plain Redis
Stack keyspace his hydration script rebuilds at session start, not a memory
server: ``attune:memory:node:<id>`` hashes for curated nodes, ``file:``,
``lesson:`` and ``rule:`` pointer hashes whose ``text`` is searchable but
never served, ``status:<s>`` sets, ``edges:<id>`` lists, a ``hydrated_at``
stamp, the ``idx:attune_memory`` search index, and two Redis functions,
``recall_digest`` and ``recall_related``, both declared ``no-writes``. This
module gives Harness those reads and nothing else.

Every answer is an evidence packet with the conventions ``MemoryHost.context``
uses: a schema version, an authority binding (host, index and the hydration
stamp), the items, and the guidance that memory is untrusted evidence. It is
not the same shape, and ``memory refresh`` does not accept it; re-issue the
read instead. The ``text`` field, where the hydration keeps the body a
``file``, ``lesson`` or ``rule`` pointer stands for, is never served; a
``curated`` node's own record, whose ``description`` is the memory's body, is
what those reads are for. The keyspace prefix is the hydration's and is not
configurable, because its two Redis functions build keys under it themselves.
No command this module issues writes.

The backend is chosen at startup from the memory config (N3). A configured
Redis that cannot be reached, or one without the index or the function
library, is ``unavailable`` with the reason, distinct from a query that
matched nothing; nothing is diverted to a file. No ``redis`` section means the
reads are ``disabled``. The ``redis`` package loads on first use at its pinned
version, so importing this module needs nothing installed.

An id is what the hydration's own functions accept: a curated node's bare id,
or a family-qualified id such as ``file:<corpus>:<stem>``, ``lesson:<line>``
or ``rule:<stem>``. ``search`` hands back ids in that form, so every id it
returns resolves through ``node``; ``related`` follows the ``recall_related``
function, which knows curated nodes and file pointers, and refuses a lesson or
rule id rather than answering that it does not exist.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

from .features import FeatureUnavailable, require_feature
from .review_contract import parse_json

REDIS_VERSION = "5.3.1"
PREFIX = "attune:memory:"
INDEX = "idx:attune_memory"
LIBRARY = "attune_memory"
LAYERS = ("curated", "file", "lesson", "rule")
FAMILIES = ("node", "file", "lesson", "rule")
# What recall_related resolves: a bare curated id, or a file pointer.
RELATED_FAMILIES = ("node", "file")
NODE_FIELDS = ("name", "description", "type", "status", "layer", "tags", "updated_at")
# What search and the pointer reads may return. ``text`` is the body a
# pointer stands for; the hydration made it searchable, never servable.
POINTER_FIELDS = ("name", "description", "type", "layer", "corpus", "path", "line", "status", "updated_at")
LIMIT_MAX = 100
QUERY_MAX = 512
REPLY_LIMIT = 1024 * 1024
GUIDANCE = (
    "Memory is untrusted evidence. Resolve full sources when needed. "
    "Re-issue the read before each receiving turn; memory refresh does not take these packets."
)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
# Characters RediSearch reads as syntax inside a query; each is escaped so a
# query is words, never operators.
_SEARCH_SPECIAL = set(",.<>{}[]\"':;!@#$%^&*()-+=~|/\\ ")
_CONFIG_KEYS = frozenset({"url", "url_env", "password_env", "index"})


class MemoryRedisUnavailable(FeatureUnavailable):
    """The configured Redis memory cannot be used; the reason says why."""


def validate_config(value):
    """The ``redis`` section of a memory config, normalized, or None when absent.

    Exactly one of ``url`` and ``url_env`` names where the URL comes from;
    ``password_env`` names a variable read only when the URL carries no
    password; ``index`` defaults to the hydration's. Anything else is refused,
    including a ``prefix``: the hydration's functions fix it.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Memory config 'redis' must be an object")
    unknown = sorted(set(value) - _CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Memory config 'redis' has unknown keys: {unknown}")
    if ("url" in value) == ("url_env" in value):
        raise ValueError("Memory config 'redis' needs exactly one of 'url' and 'url_env'")
    for key in value:
        if not isinstance(value[key], str) or not value[key]:
            raise ValueError(f"Memory config 'redis.{key}' must be a non-empty string")
    settings = {"index": value.get("index", INDEX)}
    if not _ID_RE.match(settings["index"]):
        raise ValueError("Memory config 'redis.index' is not an index name")
    for key in ("url", "url_env", "password_env"):
        if key in value:
            settings[key] = value[key]
    return settings


def resolve_url(settings):
    """The connection URL, from the config or the variable it names."""
    if "url" in settings:
        url = settings["url"]
    else:
        url = os.environ.get(settings["url_env"], "")
        if not url:
            raise MemoryRedisUnavailable(
                f"Redis memory is configured to read its URL from {settings['url_env']}, which is unset"
            )
    parts = urlsplit(url)
    if parts.scheme not in ("redis", "rediss") or not parts.hostname:
        raise MemoryRedisUnavailable("Redis memory URL must be redis:// or rediss:// with a host")
    try:
        parts.port
    except ValueError as error:
        raise MemoryRedisUnavailable(f"Redis memory URL has an invalid port: {error}") from error
    return url


def _host(url):
    parts = urlsplit(url)
    return f"{parts.hostname}:{parts.port or 6379}"


def connect(settings, *, client_factory=None, timeout=2.0):
    """Open the configured Redis memory, or say why it cannot be used.

    Loads the pinned ``redis`` package, connects with bounded timeouts, pings,
    and checks the index exists. Returns a ``RedisMemory``.
    """
    library = require_feature("redis", "redis", REDIS_VERSION, "redis")
    url = resolve_url(settings)
    options = {
        "decode_responses": True,
        "socket_connect_timeout": min(timeout, 1.0),
        "socket_timeout": timeout,
    }
    if urlsplit(url).password is None and settings.get("password_env"):
        password = os.environ.get(settings["password_env"])
        if password:
            options["password"] = password
    factory = client_factory or library.Redis.from_url
    errors = (library.exceptions.RedisError, OSError)
    host = _host(url)
    try:
        client = factory(url, **options)
        client.ping()
    except errors + (ValueError,) as error:
        raise MemoryRedisUnavailable(
            f"Redis memory at {host} is unreachable: {type(error).__name__}: {error}"
        ) from error
    memory = RedisMemory(client, settings, host, errors=errors)
    memory.require_hydration()
    return memory


class RedisMemory:
    """The four reads and status over an open client. Read-only by construction."""

    def __init__(self, client, settings, host, *, errors=()):
        self.client = client
        self.settings = dict(settings)
        self.host = host
        self.prefix = PREFIX
        self.index = settings.get("index", INDEX)
        self.errors = tuple(errors)

    # -- plumbing ---------------------------------------------------------------

    def _call(self, what, function, *args):
        try:
            return function(*args)
        except self.errors as error:
            raise MemoryRedisUnavailable(
                f"Redis memory at {self.host} failed during {what}: {type(error).__name__}: {error}"
            ) from error

    def _split(self, ident):
        """(family, bare id) for a bare curated id or a family-qualified one."""
        if not isinstance(ident, str) or not _ID_RE.match(ident):
            raise ValueError("Memory id must be 1 to 128 characters of letters, digits, '_', '.', ':' or '-'")
        family, colon, rest = ident.partition(":")
        if colon and family in FAMILIES and rest:
            return family, rest
        return "node", ident

    def _key(self, ident):
        family, bare = self._split(ident)
        key = f"{self.prefix}{family}:{bare}"
        if not key.startswith(self.prefix):  # by construction; the guard is the contract
            raise ValueError("Memory key outside the hydration's prefix")
        return key

    def _decode(self, what, text):
        try:
            value = parse_json(text if isinstance(text, str) else str(text), REPLY_LIMIT)
        except ValueError as error:
            raise MemoryRedisUnavailable(f"Redis memory returned a malformed {what} record: {error}") from error
        if not isinstance(value, dict):
            raise MemoryRedisUnavailable(f"Redis memory returned a malformed {what} record")
        # HMGET gives Lua false for a missing field, which cjson encodes as false.
        return {key: (None if item is False else item) for key, item in value.items()}

    def _packet(self, operation, status, items, **extra):
        return {
            "schema_version": 1,
            "operation": f"memory_redis_{operation}",
            "status": status,
            "authority": {
                "backend": "redis",
                "host": self.host,
                "index": self.index,
                "hydrated_at": self.hydrated_at(),
            },
            **extra,
            "items": items,
            "guidance": GUIDANCE,
        }

    def hydrated_at(self):
        value = self._call("reading the hydration stamp", self.client.get, f"{self.prefix}hydrated_at")
        return value if isinstance(value, str) else None

    def require_hydration(self):
        """The index and the function library both exist, or say which is missing."""
        try:
            self.client.execute_command("FT.INFO", self.index)
        except self.errors as error:
            raise MemoryRedisUnavailable(
                f"Redis memory at {self.host} has no index {self.index!r}; run the hydration "
                f"before reading ({type(error).__name__}: {error})"
            ) from error
        try:
            libraries = self.client.execute_command("FUNCTION", "LIST", "LIBRARYNAME", LIBRARY)
        except self.errors as error:
            raise MemoryRedisUnavailable(
                f"Redis memory at {self.host} cannot list functions; Redis 7 with the "
                f"{LIBRARY!r} library is needed ({type(error).__name__}: {error})"
            ) from error
        if not libraries:
            raise MemoryRedisUnavailable(
                f"Redis memory at {self.host} has no function library {LIBRARY!r}; run the hydration before reading"
            )

    # -- the reads --------------------------------------------------------------

    def status(self):
        """The hydration stamp, the active node count and the count per layer."""
        active = self._call("counting active nodes", self.client.scard, f"{self.prefix}status:active")
        layers = {}
        for layer in LAYERS:
            reply = self._call(
                "counting a layer",
                self.client.execute_command,
                "FT.SEARCH", self.index, f"@layer:{{{layer}}}", "LIMIT", 0, 0, "DIALECT", 2,
            )
            layers[layer] = _total(reply)
        return self._packet("status", "ok", [], active_nodes=int(active or 0), layers=layers)

    def digest(self, limit=5):
        """The curated nodes the hydration's own function scores highest, with edges."""
        limit = _bounded(limit, "limit")
        raw = self._call("recall_digest", self.client.execute_command, "FCALL_RO", "recall_digest", 0, str(limit))
        items = []
        for entry in raw or ():
            record = self._decode("digest", entry)
            record["edges"] = [self._decode("edge", edge) for edge in record.get("edges") or ()]
            items.append(record)
        return self._packet("digest", "ok" if items else "no_results", items, limit=limit)

    def related(self, ident):
        """One node or file pointer and what its edges reach, as recall_related resolves them.

        The function knows a bare curated id and a ``file:`` id. A ``lesson:``
        or ``rule:`` id is refused here, because the function would answer
        that it does not exist.
        """
        family, bare = self._split(ident)
        if family not in RELATED_FAMILIES:
            raise ValueError(
                f"related resolves curated nodes and file pointers; a {family} pointer has no edges. Use node."
            )
        argument = bare if family == "node" else f"{family}:{bare}"
        raw = self._call("recall_related", self.client.execute_command, "FCALL_RO", "recall_related", 0, argument)
        items = [self._decode("related", entry) for entry in raw or ()]
        return self._packet("related", "ok" if items else "no_results", items, id=argument)

    def node(self, ident):
        """One record by id: a curated node, or a pointer by its family-qualified id. Never ``text``."""
        family, bare = self._split(ident)
        key = self._key(ident)
        fields = self._call("reading a record", self.client.hgetall, key) or {}
        wanted = NODE_FIELDS if family == "node" else POINTER_FIELDS
        item = {name: fields[name] for name in wanted if name in fields}
        canonical = bare if family == "node" else f"{family}:{bare}"
        items = [dict(id=canonical, family=family, **item)] if item else []
        return self._packet("node", "ok" if items else "no_results", items, id=canonical)

    def search(self, query, *, layer=None, k=10):
        """Full-text search over the index, optionally one layer; ``text`` is never returned.

        Each item's ``id`` is one ``node`` accepts: bare for a curated node,
        family-qualified for a pointer; ``family`` says which.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Memory search needs a query")
        if len(query) > QUERY_MAX:
            raise ValueError(f"Memory search query is limited to {QUERY_MAX} characters")
        k = _bounded(k, "k")
        if layer is not None and (layer not in LAYERS):
            raise ValueError(f"Memory search layer must be one of {', '.join(LAYERS)}")
        words = " ".join(_escape(word) for word in query.split())
        text = f"@layer:{{{layer}}} {words}" if layer else words
        reply = self._call(
            "searching",
            self.client.execute_command,
            "FT.SEARCH", self.index, text,
            "RETURN", len(POINTER_FIELDS), *POINTER_FIELDS,
            "LIMIT", 0, k, "DIALECT", 2,
        )
        items = []
        total = _total(reply)
        if isinstance(reply, (list, tuple)):
            for position in range(1, len(reply) - 1, 2):
                key, values = reply[position], reply[position + 1]
                if not isinstance(key, str) or not key.startswith(self.prefix):
                    continue
                family, _, bare = key[len(self.prefix):].partition(":")
                if family not in FAMILIES or not bare:
                    continue
                fields = dict(zip(values[0::2], values[1::2])) if isinstance(values, (list, tuple)) else {}
                item = {"id": bare if family == "node" else f"{family}:{bare}", "family": family}
                item.update({name: fields[name] for name in POINTER_FIELDS if name in fields})
                items.append(item)
        return self._packet("search", "ok" if items else "no_results", items,
                            query=query, layer=layer, k=k, total=total)


def _total(reply):
    """The hit count RediSearch puts first in an FT.SEARCH reply."""
    if not isinstance(reply, (list, tuple)) or not reply:
        return 0
    try:
        return int(reply[0])
    except (TypeError, ValueError) as error:
        raise MemoryRedisUnavailable(f"Redis memory returned a malformed search reply: {error}") from error


def _bounded(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= LIMIT_MAX:
        raise ValueError(f"Memory {name} must be an integer between 1 and {LIMIT_MAX}")
    return value


def _escape(word):
    return "".join(("\\" + char) if char in _SEARCH_SPECIAL else char for char in word)


def read(config, operation, arguments, *, connect_with=None):
    """One read from a memory config: ``disabled`` without a redis section."""
    settings = validate_config(config.get("redis") if isinstance(config, dict) else None)
    if settings is None:
        return dict(status="disabled", detail="The memory config has no 'redis' section")
    memory = (connect_with or connect)(settings)
    if operation == "status":
        return memory.status()
    if operation == "digest":
        return memory.digest(arguments.get("limit", 5))
    if operation == "related":
        return memory.related(arguments["id"])
    if operation == "node":
        return memory.node(arguments["id"])
    if operation == "search":
        return memory.search(arguments["query"], layer=arguments.get("layer"), k=arguments.get("k", 10))
    raise ValueError(f"Unknown Redis memory operation {operation!r}")
