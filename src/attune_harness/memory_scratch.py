"""Working memory: one small backend interface, a file store in the base, Redis under the extra.

Native memory Task 4.2 (D18) and Task 5 (3.4, D21.6). Shared scratch is the
one memory Harness owns itself: bounded JSON values under short keys, with an
optional time to live. Two backends implement the same interface and are
chosen once, at startup, from the memory config's ``scratch`` section (N3):

- ``FileScratch``, stdlib only, one JSON file per key under a host-fixed
  directory the config names. It declares no sharing and no signals: it does
  not pretend to be more than a local scratch pad. Expiry is a stamp checked
  on read.
- ``RedisScratch``, under the ``[redis]`` extra, keys
  ``attune:harness:scratch:<namespace>:<key>`` with a Redis time to live,
  outside the ``attune:memory:*`` keyspace the hydration rebuilds. It
  declares sharing across processes and machines.

The stored record is a named, versioned format, ``attune-harness/scratch``
version 2 (Task 5, D21.6). Its header opens the record: the format's name and
version, the ``writer`` (this distribution and its installed version, read
from the package metadata) and a per-record ``version`` that counts the
successful stashes since the key was last absent. ``stash`` takes an
``expected_version`` and refuses, writing nothing, when the stored version is
not that one: a lost update is reported, not overwritten. A write whose
effect cannot be known, the record written and the replace raised, or the
write sent to Redis and its reply lost, is reported as ``ScratchUncertain``
with what is known; it is never retried and never diverted (N3, R5). The
version 1 record that 0.4.0 and 0.5.0 wrote, ``schema_version`` 1 and no
header, is read in place and reported as version 1 of the format; the first
stash over it writes version 2 at record version 1. ``docs/envelopes.md``
lists the format under "Stored formats".

A configured Redis that cannot be reached makes scratch ``unavailable``; it
is never replaced by the file store at runtime, which is the divert the
adoption spec's Task 3 reproduced as a defect. No ``scratch`` section means
``disabled``. Legacy ``current.json`` and ``kv.json`` are not read: scratch
data has no accumulated value (scoping note).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import errno
import fnmatch
import hashlib
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import unquote

from .features import replace_file
from .memory_redis import MemoryRedisUnavailable, open_client, validate_config as validate_redis
from .review_contract import canonical, parse_json

KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
VALUE_LIMIT = 64 * 1024
TTL_MAX = 30 * 24 * 3600
REDIS_PREFIX = "attune:harness:scratch:"
BACKENDS = ("file", "redis")
# The stored format: its name and the version this module writes. Version 1
# is the record 0.4.0 and 0.5.0 wrote, ``schema_version`` 1 and no header.
FORMAT = "attune-harness/scratch"
FORMAT_VERSION = 2
DISTRIBUTION = "attune-harness"
# How long a compare-and-set on the file store waits for the store's lock
# before it reports busy: the codebase's bound, as the run store's lease.
LOCK_RETRY_SECONDS = 2.0
# Room for the record around the value: the header, the key and two stamps.
RECORD_LIMIT = VALUE_LIMIT + 4096
_CONFIG_KEYS = frozenset({"backend", "root", "namespace"})
_SCAN_COUNT = 500
# The fields of a version 2 record, in the order they are written: the
# header first, so a reader that opens the file sees what it is.
_RECORD_FIELDS = ("format", "format_version", "writer", "version", "key", "value", "stored_at", "expires_at")
_LEGACY_FIELDS = ("schema_version", "key", "value", "stored_at", "expires_at")
_LOCK_HELD = frozenset(getattr(errno, name) for name in ("EWOULDBLOCK", "EAGAIN", "EACCES") if hasattr(errno, name))
# Characters a file name keeps as they are; every other one, including an
# upper-case letter, is percent-encoded, so two keys that differ only in case
# are two files on a case-insensitive file system.
_PLAIN = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_.-")
_NAME_MAX = 200


class ScratchRefused(ValueError):
    """A stash refused before anything was written.

    The message says what was expected, what was found and what to do.
    ``found`` is the stored record's version: an integer, 0 for no live
    record, None for a legacy record (which carries none) or when it was not
    read.
    """

    def __init__(self, message, *, key, expected_version, found):
        super().__init__(message)
        self.key = key
        self.expected_version = expected_version
        self.found = found


class ScratchUncertain(RuntimeError):
    """A stash whose effect cannot be known; never retried, never diverted (N3, R5).

    ``version`` is the record version the write carried: a record at that
    version, read back, means the write landed. ``error`` names the exception.
    """

    def __init__(self, message, *, key, version, error):
        super().__init__(message)
        self.key = key
        self.version = version
        self.error = error


@runtime_checkable
class ScratchBackend(Protocol):
    """What every scratch store offers. Values are JSON; keys match ``KEY_RE``."""

    def capabilities(self) -> dict: ...
    def stash(self, key: str, value, ttl_seconds: int | None = None, *, expected_version: int | None = None) -> dict: ...
    def retrieve(self, key: str): ...
    def forget(self, key: str) -> bool: ...
    def keys(self, pattern: str = "*") -> list[str]: ...


def writer():
    """What writes the record: this distribution and its installed version, read, never hard-coded.

    Without the package metadata (a source tree that was never installed)
    the name alone is what is known, and that is what is written.
    """
    try:
        installed = metadata.version(DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return DISTRIBUTION
    return f"{DISTRIBUTION} {installed}"


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


def _check_expected_version(expected):
    if expected is None:
        return None
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        raise ValueError("Scratch expected version must be an integer of 0 or more: 0 for no record, "
                         "otherwise the version retrieve reports")
    return expected


def _check_pattern(pattern):
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 128 or not re.fullmatch(r"[A-Za-z0-9_.:*?\-]+", pattern):
        raise ValueError("Scratch key pattern may hold key characters plus '*' and '?'")
    return pattern


def _now():
    return datetime.now(timezone.utc)


def _record(key, text, ttl, record_version):
    now = _now()
    record = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "writer": writer(),
        "version": record_version,
        "key": key,
        "value": json.loads(text),
        "stored_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl)).isoformat() if ttl else None,
    }
    # Compact, in the order declared above, so the header opens the record,
    # what is written is what the bound measured plus the envelope, and a
    # value inside the limit always reads back. The value's own keys are
    # already canonical, sorted by ``_check_value``.
    payload = json.dumps(record, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > RECORD_LIMIT:
        raise ValueError(f"Scratch value is limited to {VALUE_LIMIT} bytes as canonical JSON")
    return record, payload


def _well_formed(record, key):
    """(record, format version) when the stored record is complete and this key's; (None, None) otherwise.

    Version 2 is the format this module writes. Version 1 is the record 0.4.0
    and 0.5.0 wrote, ``schema_version`` 1 and no header: it is read in place
    and a read never rewrites it. A record of any other shape, including a
    later version of the format, is foreign, and nothing is inferred from it.
    """
    if not isinstance(record, dict) or record.get("key") != key:
        return None, None
    if set(record) == set(_LEGACY_FIELDS):
        format_version = 1 if record["schema_version"] == 1 else None
    elif set(record) == set(_RECORD_FIELDS):
        counted = isinstance(record["version"], int) and not isinstance(record["version"], bool) and record["version"] >= 1
        current = record["format"] == FORMAT and record["format_version"] == FORMAT_VERSION and isinstance(record["writer"], str)
        format_version = FORMAT_VERSION if current and counted else None
    else:
        return None, None
    if format_version is None:
        return None, None
    if record["expires_at"] is not None and not isinstance(record["expires_at"], str):
        return None, None
    if not isinstance(record["stored_at"], str):
        return None, None
    return record, format_version


def _view(record, format_version, *, with_value=True):
    """What retrieve and stash report of a record: its header, then the entry.

    A legacy record carries no writer and no version; both are reported as
    None, and its format version as 1.
    """
    legacy = format_version == 1
    view = {
        "format": FORMAT,
        "format_version": format_version,
        "writer": None if legacy else record["writer"],
        "version": None if legacy else record["version"],
        "key": record["key"],
    }
    if with_value:
        view["value"] = record["value"]
    view["stored_at"] = record["stored_at"]
    view["expires_at"] = record["expires_at"]
    return view


def _expired(record):
    expires = record["expires_at"]
    if expires is None:
        return False
    try:
        return datetime.fromisoformat(expires) <= _now()
    except ValueError:
        return True


def _stored_version(found, format_version):
    """The version a stash compares against: 0 with no live record, None for a legacy record."""
    if found is None:
        return 0
    if format_version == 1:
        return None
    return found["version"]


def _next_version(key, expected, found, format_version):
    """The version the stash writes, or ``ScratchRefused`` when ``expected`` is not what is stored.

    A key with no live record is at version 0, so an expected 0 creates. A
    legacy record carries no version and matches no expectation; a stash
    without one writes the current format at version 1 over it.
    """
    current = _stored_version(found, format_version)
    if expected is not None and current != expected:
        raise ScratchRefused(_refusal(key, expected, current), key=key, expected_version=expected, found=current)
    return 1 if not current else current + 1


def _expected_text(expected):
    return "no record (version 0)" if expected == 0 else f"version {expected}"


def _refusal(key, expected, current):
    if current is None:
        found = "a legacy record, which carries no version"
        action = "Stash without an expected version to write the current format, which starts at version 1."
    elif current == 0:
        found = "no record"
        action = "Stash without an expected version, or with 0, to create it."
    else:
        found = f"version {current}"
        action = "Retrieve the key and stash with the version it reports."
    return (f"Scratch stash of key {key!r} was refused: expected {_expected_text(expected)}, found {found}; "
            f"nothing was written. {action}")


def _changed(key, expected):
    return (f"Scratch stash of key {key!r} was refused: expected {_expected_text(expected)}, but the record "
            f"changed while the stash was being prepared; nothing was written. "
            f"Retrieve the key and stash with the version it reports.")


def _uncertain(key, version, what, error):
    return (f"Scratch stash of key {key!r} may or may not have landed: {what} ({type(error).__name__}: {error}). "
            f"Retrieve the key; a record at version {version} means it did. "
            f"No retry was performed and nothing was diverted.")


def _lock_once(fd):
    """One non-blocking attempt at the store's lock, as the run store takes its writer lock."""
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


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

    @staticmethod
    def _name(key):
        """A file name that is one-to-one with the key on every file system.

        Lower-case letters, digits, '_', '.' and '-' stay; everything else,
        including an upper-case letter and ':', is percent-encoded, so keys
        that differ only in case are different files where names fold case.
        The 'k-' prefix keeps a name such as CON or NUL from being a Windows
        device. A name that would pass 200 characters is cut and given the
        key's digest, since ':' costs three characters encoded and file
        systems stop near 255; the key itself is kept inside the record.
        """
        encoded = "".join(char if char in _PLAIN else f"%{ord(char):02X}" for char in key)
        if len(encoded) > _NAME_MAX:
            encoded = encoded[:_NAME_MAX - 17] + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return f"k-{encoded}.json"

    def _path(self, key):
        return self.directory / self._name(_check_key(key))

    def _ensure_directory(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.directory.resolve() != self.directory:
            raise ValueError("Scratch directory cannot be, or sit in, a symlink")

    @contextmanager
    def _lock(self, key, expected):
        """The compare and the replace as one step for every process on this machine.

        A lock another writer holds is retried for ``LOCK_RETRY_SECONDS`` and
        then refused in the stash's own words; a file system that grants no
        lock is refused at once. Only a compare-and-set takes it: a stash
        without an expected version writes as it always has.
        """
        lock = self.directory / ".scratch.lock"
        if os.name == "nt":
            from .windows import open_lock
            fd = open_lock(lock)
        else:
            fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            deadline = time.monotonic() + LOCK_RETRY_SECONDS
            while True:
                try:
                    _lock_once(fd)
                    break
                except OSError as error:
                    if error.errno not in _LOCK_HELD:
                        raise ScratchRefused(
                            f"Scratch stash of key {key!r} was refused: the file system refuses locks "
                            f"({errno.errorcode.get(error.errno, error.errno)}), so the version cannot be compared; "
                            f"nothing was written. Stash without an expected version, which takes no lock.",
                            key=key, expected_version=expected, found=None) from error
                    if time.monotonic() >= deadline:
                        raise ScratchRefused(
                            f"Scratch stash of key {key!r} was refused: another writer has held the store's lock "
                            f"for {LOCK_RETRY_SECONDS:g} seconds; nothing was written. Stash again once it lets go.",
                            key=key, expected_version=expected, found=None) from error
                    time.sleep(0.005)
            yield
        finally:
            os.close(fd)

    def stash(self, key, value, ttl_seconds=None, *, expected_version=None):
        path = self._path(key)
        text = _check_value(value)
        ttl = _check_ttl(ttl_seconds)
        expected = _check_expected_version(expected_version)
        self._ensure_directory()
        if path.is_symlink():
            raise ValueError("Scratch entry cannot be a symlink")
        if expected is None:
            return self._write(path, key, text, ttl, expected)
        with self._lock(key, expected):
            return self._write(path, key, text, ttl, expected)

    def _write(self, path, key, text, ttl, expected):
        found, format_version = self._live(key, path)
        record, payload = _record(key, text, ttl, _next_version(key, expected, found, format_version))
        handle, name = tempfile.mkstemp(prefix=".scratch-", suffix=".json", dir=self.directory)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload + "\n")
            try:
                replace_file(Path(name), path)
            except OSError as error:
                # The record is written and the replace raised: on Windows a
                # replace can fail after the target is gone, so what is stored
                # is not known. Reported, never retried (N3, R5).
                raise ScratchUncertain(
                    _uncertain(key, record["version"], "the record was written and the replace raised", error),
                    key=key, version=record["version"], error=type(error).__name__) from error
        finally:
            if Path(name).exists():
                Path(name).unlink()
        return _view(record, FORMAT_VERSION, with_value=False)

    def _load(self, path):
        """(record, format version, state) for one file: state is 'live', 'expired' or 'foreign'."""
        if path.is_symlink() or not path.is_file():
            return None, None, "foreign"
        try:
            raw = parse_json(path.read_text(encoding="utf-8"), RECORD_LIMIT)
        except (OSError, ValueError):
            return None, None, "foreign"
        if not isinstance(raw, dict) or not isinstance(raw.get("key"), str):
            return None, None, "foreign"
        record, format_version = _well_formed(raw, raw["key"])
        if record is None or path.name != self._name(record["key"]):
            return None, None, "foreign"  # a record under another key's name can never be retrieved
        return record, format_version, ("expired" if _expired(record) else "live")

    def _live(self, key, path):
        """(record, format version) when the file holds a live record for ``key``; (None, None) otherwise."""
        record, format_version, state = self._load(path)
        if state != "live" or record["key"] != key:
            return None, None
        return record, format_version

    def retrieve(self, key):
        record, format_version = self._live(key, self._path(key))
        if record is None:
            return None
        return _view(record, format_version)

    def forget(self, key):
        path = self._path(key)
        record, _, state = self._load(path)
        if state == "foreign" and not path.is_file():
            return False
        if path.is_symlink():
            return False
        path.unlink()
        # A foreign or expired file is removed as housekeeping but was never a live entry.
        return state == "live" and record["key"] == key

    def keys(self, pattern="*"):
        _check_pattern(pattern)
        if not self.directory.is_dir():
            return []
        found = []
        for entry in sorted(self.directory.iterdir()):
            if entry.suffix != ".json" or not entry.name.startswith("k-") or entry.is_symlink():
                continue
            record, _, state = self._load(entry)
            if state == "expired":
                entry.unlink()  # the directory clears itself of what has lapsed
                continue
            if state == "live" and fnmatch.fnmatchcase(record["key"], pattern):
                found.append(record["key"])
        return sorted(found)


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

    def _parse(self, key, raw):
        """(record, format version) from one reply; (None, None) when the key is absent.

        A reply that is not a record of this key's is refused as the server
        holding something this code cannot read, as ``retrieve`` reports it.
        """
        if raw is None:
            return None, None
        text = raw if isinstance(raw, str) else bytes(raw).decode("utf-8", "replace")
        try:
            parsed = parse_json(text, RECORD_LIMIT)
        except ValueError as error:
            raise MemoryRedisUnavailable(f"Redis scratch at {self.host} holds a malformed record: {error}") from error
        record, format_version = _well_formed(parsed, key)
        if record is None:
            raise MemoryRedisUnavailable(f"Redis scratch at {self.host} holds a record that is not this key's")
        return record, format_version

    def _uncertain(self, key, version, error):
        return ScratchUncertain(
            _uncertain(key, version, f"the write was sent to Redis at {self.host} and its reply was lost", error),
            key=key, version=version, error=type(error).__name__)

    def stash(self, key, value, ttl_seconds=None, *, expected_version=None):
        name = self._name(key)
        text = _check_value(value)
        ttl = _check_ttl(ttl_seconds)
        expected = _check_expected_version(expected_version)
        options = {"ex": ttl} if ttl else {}
        if expected is None or expected == 0:
            # A plain SET, as before, or SET NX when the key must be absent.
            # The read before it only counts the version, so a failure there
            # is unavailable: no write was sent. A stash with no expectation
            # writes over what it cannot read, as it always has.
            raw = self._call("stash", self.client.get, name)
            try:
                found, format_version = self._parse(key, raw)
            except MemoryRedisUnavailable:
                if expected is not None:
                    raise
                found, format_version = None, None
            record, payload = _record(key, text, ttl, _next_version(key, expected, found, format_version))
            try:
                reply = self.client.set(name, payload, **options, **({"nx": True} if expected == 0 else {}))
            except self.errors as error:
                raise self._uncertain(key, record["version"], error) from error
            if expected == 0 and not reply:
                raise ScratchRefused(_changed(key, expected), key=key, expected_version=expected, found=None)
            return _view(record, FORMAT_VERSION, with_value=False)
        # The compare and the set as one transaction: WATCH the key, read it,
        # queue the SET under MULTI, EXEC. Redis refuses the EXEC when the key
        # changed after the WATCH, which is reported as the refusal it is.
        pipe = self.client.pipeline()
        try:
            self._call("stash", pipe.watch, name)
            found, format_version = self._parse(key, self._call("stash", pipe.get, name))
            record, payload = _record(key, text, ttl, _next_version(key, expected, found, format_version))
            pipe.multi()
            pipe.set(name, payload, **options)
            try:
                pipe.execute()
            except self.errors as error:
                # The base never imports redis, so its WatchError is known by name.
                if type(error).__name__ == "WatchError":
                    raise ScratchRefused(_changed(key, expected), key=key, expected_version=expected, found=None) from error
                raise self._uncertain(key, record["version"], error) from error
        finally:
            try:
                pipe.reset()
            except self.errors:
                pass  # the outcome above stands; releasing a dead connection changes nothing
        return _view(record, FORMAT_VERSION, with_value=False)

    def retrieve(self, key):
        record, format_version = self._parse(key, self._call("retrieve", self.client.get, self._name(key)))
        if record is None:
            return None
        return _view(record, format_version)

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
        try:
            stored = store.stash(arguments["key"], arguments["value"], arguments.get("ttl"),
                                 expected_version=arguments.get("expected_version"))
        except ScratchRefused as refusal:
            return dict(status="failed", operation="memory_scratch_stash", backend=store.backend, key=refusal.key,
                        expected_version=refusal.expected_version, version=refusal.found,
                        error=type(refusal).__name__, detail=str(refusal))
        except ScratchUncertain as receipt:
            return dict(status="uncertain", operation="memory_scratch_stash", backend=store.backend, key=receipt.key,
                        version=receipt.version, error=receipt.error, detail=str(receipt))
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
