"""Working memory: one small backend interface, a file store in the base, Redis under the extra.

Native memory Task 4.2 (D18). Shared scratch is the one memory Harness owns
itself: bounded JSON values under short keys, with an optional time to live.
Two backends implement the same interface and are chosen once, at startup,
from the memory config's ``scratch`` section (N3):

- ``FileScratch``, stdlib only, one JSON file per key under a host-fixed
  directory the config names. It declares no sharing and no signals: it does
  not pretend to be more than a local scratch pad. Expiry is a stamp checked
  on read.
- ``RedisScratch``, under the ``[redis]`` extra, keys
  ``attune:harness:scratch:<namespace>:<key>`` with a Redis time to live,
  outside the ``attune:memory:*`` keyspace the hydration rebuilds. It
  declares sharing across processes and machines.

A configured Redis that cannot be reached makes scratch ``unavailable``; it
is never replaced by the file store at runtime, which is the divert the
adoption spec's Task 3 reproduced as a defect. No ``scratch`` section means
``disabled``. Legacy ``current.json`` and ``kv.json`` are not read: scratch
data has no accumulated value (scoping note).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import quote, unquote

from .features import replace_file
from .memory_redis import MemoryRedisUnavailable, open_client, validate_config as validate_redis
from .review_contract import canonical, parse_json

KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
VALUE_LIMIT = 64 * 1024
TTL_MAX = 30 * 24 * 3600
REDIS_PREFIX = "attune:harness:scratch:"
BACKENDS = ("file", "redis")
_CONFIG_KEYS = frozenset({"backend", "root", "namespace"})
_SCAN_COUNT = 500


@runtime_checkable
class ScratchBackend(Protocol):
    """What every scratch store offers. Values are JSON; keys match ``KEY_RE``."""

    def capabilities(self) -> dict: ...
    def stash(self, key: str, value, ttl_seconds: int | None = None) -> dict: ...
    def retrieve(self, key: str): ...
    def forget(self, key: str) -> bool: ...
    def keys(self, pattern: str = "*") -> list[str]: ...


def _check_key(key):
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise ValueError("Scratch key must be 1 to 128 characters of letters, digits, '_', '.', ':' or '-'")
    return key


def _check_value(value):
    try:
        text = canonical(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Scratch value must be JSON with finite numbers: {error}") from error
    if len(text.encode("utf-8")) > VALUE_LIMIT:
        raise ValueError(f"Scratch value is limited to {VALUE_LIMIT} bytes as canonical JSON")
    return text


def _check_ttl(ttl_seconds):
    if ttl_seconds is None:
        return None
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= TTL_MAX:
        raise ValueError(f"Scratch ttl must be an integer number of seconds between 1 and {TTL_MAX}")
    return ttl_seconds


def _check_pattern(pattern):
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 128 or not re.fullmatch(r"[A-Za-z0-9_.:*?\-]+", pattern):
        raise ValueError("Scratch key pattern may hold key characters plus '*' and '?'")
    return pattern


def _now():
    return datetime.now(timezone.utc)


def validate_config(value):
    """The ``scratch`` section of a memory config, normalized, or None when absent."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Memory config 'scratch' must be an object")
    unknown = sorted(set(value) - _CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Memory config 'scratch' has unknown keys: {unknown}")
    backend = value.get("backend")
    if backend not in BACKENDS:
        raise ValueError(f"Memory config 'scratch.backend' must be one of {', '.join(BACKENDS)}")
    namespace = value.get("namespace", "harness")
    if not isinstance(namespace, str) or not NAMESPACE_RE.match(namespace):
        raise ValueError("Memory config 'scratch.namespace' must be 1 to 32 lowercase letters, digits or '-'")
    settings = {"backend": backend, "namespace": namespace}
    if backend == "file":
        root = value.get("root")
        if not isinstance(root, str) or not root:
            raise ValueError("Memory config 'scratch.root' is required for the file backend")
        settings["root"] = root
    elif "root" in value:
        raise ValueError("Memory config 'scratch.root' applies to the file backend only")
    return settings


class FileScratch:
    """One JSON file per key under ``<root>/scratch/<namespace>/``; no sharing, no signals."""

    backend = "file"

    def __init__(self, root, namespace="harness"):
        directory = Path(root)
        if not directory.is_absolute() or directory != directory.resolve() or not directory.is_dir():
            raise ValueError("Scratch root must be an existing canonical absolute directory")
        if any(part in (".git", ".hg", ".svn") for part in directory.parts):
            raise ValueError("Scratch root cannot use repository metadata")
        if not NAMESPACE_RE.match(namespace):
            raise ValueError("Scratch namespace is invalid")
        self.root = directory
        self.namespace = namespace
        self.directory = directory / "scratch" / namespace

    def capabilities(self):
        return {"backend": "file", "shared": False, "realtime": False, "location": str(self.directory)}

    def _path(self, key):
        # Keys may hold ':' and '.', which some file systems refuse or rewrite;
        # the file name is the key percent-encoded, and the key is kept inside.
        return self.directory / (quote(_check_key(key), safe="") + ".json")

    def stash(self, key, value, ttl_seconds=None):
        path = self._path(key)
        text = _check_value(value)
        ttl = _check_ttl(ttl_seconds)
        now = _now()
        record = {
            "schema_version": 1,
            "key": key,
            "value": json.loads(text),
            "stored_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl)).isoformat() if ttl else None,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError("Scratch entry cannot be a symlink")
        payload = json.dumps(record, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
        handle, name = tempfile.mkstemp(prefix=".scratch-", suffix=".json", dir=self.directory)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
            replace_file(Path(name), path)
        finally:
            if Path(name).exists():
                Path(name).unlink()
        return {"key": key, "stored_at": record["stored_at"], "expires_at": record["expires_at"]}

    def _read(self, key):
        path = self._path(key)
        if path.is_symlink() or not path.is_file():
            return None
        try:
            record = parse_json(path.read_text(encoding="utf-8"), VALUE_LIMIT + 4096)
        except (OSError, ValueError):
            return None
        if not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("key") != key:
            return None
        expires = record.get("expires_at")
        if isinstance(expires, str):
            try:
                if datetime.fromisoformat(expires) <= _now():
                    return None
            except ValueError:
                return None
        return record

    def retrieve(self, key):
        record = self._read(key)
        if record is None:
            return None
        return {key_: record[key_] for key_ in ("key", "value", "stored_at", "expires_at")}

    def forget(self, key):
        path = self._path(key)
        if path.is_symlink() or not path.is_file():
            return False
        path.unlink()
        return True

    def keys(self, pattern="*"):
        _check_pattern(pattern)
        if not self.directory.is_dir():
            return []
        found = []
        for entry in sorted(self.directory.iterdir()):
            if entry.suffix != ".json" or entry.name.startswith(".") or entry.is_symlink():
                continue
            key = unquote(entry.stem)
            if KEY_RE.match(key) and fnmatch.fnmatchcase(key, pattern) and self._read(key) is not None:
                found.append(key)
        return found


class RedisScratch:
    """Keys under ``attune:harness:scratch:<namespace>:`` with a Redis time to live; shared."""

    backend = "redis"

    def __init__(self, client, namespace="harness", *, host="redis", errors=()):
        if not NAMESPACE_RE.match(namespace):
            raise ValueError("Scratch namespace is invalid")
        self.client = client
        self.namespace = namespace
        self.host = host
        self.prefix = f"{REDIS_PREFIX}{namespace}:"
        self.errors = tuple(errors)

    def capabilities(self):
        return {"backend": "redis", "shared": True, "realtime": True, "location": f"{self.host} {self.prefix}*"}

    def _call(self, what, function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except self.errors as error:
            raise MemoryRedisUnavailable(
                f"Redis scratch at {self.host} failed during {what}: {type(error).__name__}: {error}"
            ) from error

    def _name(self, key):
        return self.prefix + _check_key(key)

    def stash(self, key, value, ttl_seconds=None):
        name = self._name(key)
        text = _check_value(value)
        ttl = _check_ttl(ttl_seconds)
        now = _now()
        record = {
            "schema_version": 1,
            "key": key,
            "value": json.loads(text),
            "stored_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl)).isoformat() if ttl else None,
        }
        payload = json.dumps(record, ensure_ascii=True, allow_nan=False)
        if ttl:
            self._call("stash", self.client.set, name, payload, ex=ttl)
        else:
            self._call("stash", self.client.set, name, payload)
        return {"key": key, "stored_at": record["stored_at"], "expires_at": record["expires_at"]}

    def retrieve(self, key):
        raw = self._call("retrieve", self.client.get, self._name(key))
        if raw is None:
            return None
        try:
            record = parse_json(raw if isinstance(raw, str) else str(raw), VALUE_LIMIT + 4096)
        except ValueError as error:
            raise MemoryRedisUnavailable(f"Redis scratch at {self.host} holds a malformed record: {error}") from error
        if not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("key") != key:
            raise MemoryRedisUnavailable(f"Redis scratch at {self.host} holds a record that is not this key's")
        return {key_: record.get(key_) for key_ in ("key", "value", "stored_at", "expires_at")}

    def forget(self, key):
        return bool(self._call("forget", self.client.delete, self._name(key)))

    def keys(self, pattern="*"):
        _check_pattern(pattern)
        found = []
        for name in self._call("keys", lambda: list(self.client.scan_iter(match=self.prefix + pattern, count=_SCAN_COUNT))):
            text = name if isinstance(name, str) else name.decode("utf-8", "replace")
            if text.startswith(self.prefix):
                key = text[len(self.prefix):]
                if KEY_RE.match(key):
                    found.append(key)
        return sorted(found)


def open_scratch(config, *, open_redis=None):
    """The configured backend, chosen once; ``None`` when there is no section.

    A ``redis`` scratch needs the memory config's ``redis`` section for the
    connection. An unreachable Redis raises ``MemoryRedisUnavailable``; the
    file store is never substituted (N3).
    """
    settings = validate_config(config.get("scratch") if isinstance(config, dict) else None)
    if settings is None:
        return None
    if settings["backend"] == "file":
        return FileScratch(settings["root"], settings["namespace"])
    redis_settings = validate_redis(config.get("redis"))
    if redis_settings is None:
        raise ValueError("Memory config 'scratch.backend' is redis but there is no 'redis' section")
    client, host, errors = (open_redis or open_client)(redis_settings)
    return RedisScratch(client, settings["namespace"], host=host, errors=errors)


def run(config, operation, arguments, *, open_with=None):
    """One scratch operation from a memory config, as the CLI's envelope."""
    store = (open_with or open_scratch)(config)
    if store is None:
        return dict(status="disabled", detail="The memory config has no 'scratch' section")
    if operation == "capabilities":
        return dict(status="ok", operation="memory_scratch_capabilities", **store.capabilities())
    if operation == "stash":
        stored = store.stash(arguments["key"], arguments["value"], arguments.get("ttl"))
        return dict(status="ok", operation="memory_scratch_stash", backend=store.backend, **stored)
    if operation == "retrieve":
        found = store.retrieve(arguments["key"])
        if found is None:
            return dict(status="no_results", operation="memory_scratch_retrieve", backend=store.backend, key=arguments["key"])
        return dict(status="ok", operation="memory_scratch_retrieve", backend=store.backend, **found)
    if operation == "forget":
        gone = store.forget(arguments["key"])
        return dict(status="ok" if gone else "no_results", operation="memory_scratch_forget", backend=store.backend,
                    key=arguments["key"], forgotten=gone)
    if operation == "keys":
        found = store.keys(arguments.get("pattern", "*"))
        return dict(status="ok" if found else "no_results", operation="memory_scratch_keys", backend=store.backend,
                    pattern=arguments.get("pattern", "*"), keys=found)
    raise ValueError(f"Unknown scratch operation {operation!r}")
