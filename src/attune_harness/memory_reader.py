"""Read the three legacy memory tiers with nothing from attune-ai: the native reader.

Native memory Phase 2, step 2.2 (D19). ``MemoryHost`` consumes four members of
whatever answers for a memory root config: ``binding``, ``capabilities()``,
``query(query, k)`` and ``resolve(handle)``. Until now the only thing that did
was ``attune.memory.harness_adapter.CompatibilityAdapter``, a module attune-ai
never released. This class answers the same contract from the standard
library, plus attune-rag's keyword retriever for the document tiers, which
the base install already carries, so every envelope the host prints keeps
its shape.

What is reproduced is the adapter's observable contract, read from its
source on the ``codex/shared-memory-adoption`` branch on 2026-09-22 and
written down in the Phase 2 design note: the config validation and its
words; the binding as the digest of the whole config; the descriptor walk
with ``O_NOFOLLOW`` on every component, POSIX only; the bounds (8 MiB a
file, 4,096 files and 64 MiB a query, 30 days for a raw row); the raw tier's
ranking (token overlap plus a three-day recency half-life, stable, file
order on ties; newest first for a blank query) and its exact ``cwd`` scope;
the document tiers' ranking (attune-rag's keyword retriever over a snapshot
that keeps the sources' mtimes, twice ``k`` then de-duplicated by path);
the frontmatter authority check; the strict content gate; the statuses
``available``, ``partial``, ``unavailable`` and ``empty``; and every refusal
text. D19 asks for identical result sets and an identical top result; order
below the top is reported by the differential, not enforced.

Not reproduced here, by design: the telemetry line the adapter's document
query appends under the user's home (a write), and anything else that
writes. The provenance fields and the staleness annotations the adapter's
document metadata carries are produced by ``memory_controls`` (step 2.3). The adapter stays
selectable with ``"reader": "adapter"`` until Task 9.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time

from .features import FeatureUnavailable, require_feature
from .memory_contract import CLASSIFICATIONS, bounded_json, strings
from .memory_controls import AUTHOR_CURATED, guard, latest_verdicts, provenance_fields, staleness
from .paths import validate_file_path
from .review_contract import bounded_text, digest, fields, parse_json, versioned

TIERS = ("raw", "personal", "curated")
FILE_LIMIT = 8 * 1024 * 1024
SNAPSHOT_FILES = 4096
SNAPSHOT_BYTES = 64 * 1024 * 1024
RAW_TTL_SECONDS = 30 * 24 * 3600
RECENCY_HALF_LIFE_SECONDS = 259200  # three days, as the file stash scores it
RAG_VERSION = "1.2.0"
SIDECARS = ("summaries_by_path.json", ".verdicts.jsonl")
CAPABILITIES = {
    "read": list(TIERS),
    "worker_mutations": [],
    "mutation_status": "unavailable: legacy writers lack qualified versioned serialization",
    "retained_paths": ["keyed working memory", "governed persisted patterns", "existing memory commands"],
}
# Sections of the one memory config file that belong to other verbs, not to the roots contract.
OTHER_SECTIONS = ("redis", "scratch", "reader")
_ROOT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)  # alnum runs; str.isalnum() semantics come close enough


def roots_config(config):
    """The roots contract's keys from the one memory config file, the other sections set aside."""
    if not isinstance(config, dict):
        return config
    return {key: value for key, value in config.items() if key not in OTHER_SECTIONS}


class NativeReader:
    """The four-member contract over the three file tiers."""

    def __init__(self, config):
        bounded_json(config, 65536)
        fields(config, ("schema_version", "actor", "owners", "scopes", "classifications", "profiles", "roots"))
        versioned(config)
        bounded_text(config["actor"], "actor", 512)
        for name in ("owners", "scopes", "classifications", "profiles"):
            strings(config[name], name, nonempty=True)
        if not set(config["classifications"]) <= set(CLASSIFICATIONS):
            raise ValueError("Unknown security classification")
        roots = config["roots"]
        if not isinstance(roots, list) or not roots:
            raise ValueError("At least one explicit memory root is required")
        seen = set()
        for root in roots:
            fields(root, ("id", "path", "tier", "scope", "owner", "classification"))
            if not isinstance(root["id"], str) or not _ROOT_ID.fullmatch(root["id"]):
                raise ValueError("Invalid root identity")
            if root["id"] in seen:
                raise ValueError("Duplicate root identity")
            seen.add(root["id"])
            if root["tier"] not in TIERS:
                raise ValueError("Tier uses its existing governed path; no new adapter capability")
            if (root["scope"] not in config["scopes"] or root["owner"] not in config["owners"]
                    or root["classification"] not in config["classifications"]):
                raise ValueError("Memory root is outside host authority")
            bounded_text(root["path"], "root path")
            path = Path(root["path"])
            if not path.is_absolute() or path != path.resolve() or path.is_symlink():
                raise ValueError("Memory root must be a canonical absolute path without symlinks")
            validate_file_path(str(path / ".scope-validation"))
        self.config = deepcopy(config)
        self.binding = digest(config)

    # -- authority and files ------------------------------------------------------

    def capabilities(self):
        return deepcopy(CAPABILITIES)

    def _root(self, root_id):
        if digest(self.config) != self.binding:
            raise ValueError("Adapter authority changed; construct a new adapter")
        for root in self.config["roots"]:
            if root["id"] == root_id:
                return root
        raise ValueError("Unknown root identity")

    def _capture(self, root, relative, *, limit=None):
        """Read one file under a root through a descriptor walk: (bytes, version, mtime_ns)."""
        limit = FILE_LIMIT if limit is None else limit
        if type(limit) is not int or not 1 <= limit <= FILE_LIMIT:
            raise ValueError("Source read limit is outside the file bound")
        relative = Path(relative)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("Source escapes its authorized root")
        path = Path(root["path"])
        if path != path.resolve() or not path.is_dir():
            raise ValueError("Root changed or unavailable")
        target = path / relative
        probe = target
        while probe != path.parent:
            if probe.is_symlink():
                raise ValueError("Symlink source is not authorized")
            probe = probe.parent
        validate_file_path(str(target))
        if not _posix():
            raise ValueError("Scoped descriptor reads are currently qualified only on POSIX")
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in list(path.parts[1:]) + list(relative.parts[:-1]):
                nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            leaf = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        finally:
            os.close(fd)
        try:
            before = os.fstat(leaf)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("Source must be a regular file without hard links")
            chunks, size = [], 0
            while size <= limit:
                chunk = os.read(leaf, limit + 1 - size)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            content = b"".join(chunks)
            if len(content) > limit:
                raise ValueError("Source exceeds read limit; select a narrower source")
            after = os.fstat(leaf)
        finally:
            os.close(leaf)
        if (before.st_mtime_ns, before.st_ctime_ns, before.st_size) != (after.st_mtime_ns, after.st_ctime_ns, after.st_size):
            raise ValueError("Source changed while being read")
        version = digest({"sha256": hashlib.sha256(content).hexdigest(), "device": before.st_dev,
                          "inode": before.st_ino, "mtime_ns": before.st_mtime_ns,
                          "ctime_ns": before.st_ctime_ns, "size": before.st_size})
        return content, version, before.st_mtime_ns

    def _sidecars(self, root):
        found = {}
        for name in SIDECARS:
            try:
                found[name] = self._capture(root, name)
            except FileNotFoundError:
                found[name] = (b"", "absent", 0)
        return found

    @staticmethod
    def _document_version(source_version, sidecars):
        return digest({"source": source_version, "sidecars": {name: token for name, (_, token, _) in sidecars.items()}})

    # -- items ---------------------------------------------------------------------

    def _item(self, root, locator, text, version, kind, metadata):
        guard(text, metadata)  # the adapter guards before it reads the labels
        labels = metadata
        if root["tier"] != "raw":
            body = text[1:] if text.startswith("\ufeff") else text
            body = body.replace("\r\n", "\n").replace("\r", "\n")
            if re.match(r"^---[ \t]*\n", body):
                parts = re.split(r"(?m)^---[ \t]*$", body, maxsplit=2)
                if len(parts) != 3:
                    raise ValueError("Unterminated source security metadata")
                loaded = _frontmatter(parts[1])
                if loaded is not None and not isinstance(loaded, dict):
                    raise ValueError("Source security metadata must be an object")
                labels = loaded or {}
        for key in ("owner", "scope", "classification"):
            if key in labels and labels[key] != root[key]:
                raise ValueError("Source security metadata conflicts with root authority")
        first = next(iter(locator.values()))
        return dict(id=f"{root['id']}:{first}", locator={"root_id": root["id"], **locator}, version=version,
                    authority=self.binding, text=text, kind=kind, metadata=deepcopy(metadata),
                    scope=root["scope"], owner=root["owner"], classification=root["classification"])

    # -- the raw tier -----------------------------------------------------------------

    def _raw(self, root):
        if not (Path(root["path"]) / "findings.jsonl").exists():  # a dangling symlink is absent, as in the adapter
            return b"", {}, "absent"
        content, version, _ = self._capture(root, "findings.jsonl")
        rows = {}
        for line in content.decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = parse_json(line, FILE_LIMIT)
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in rows:
                raise ValueError("Malformed or duplicate raw identity; exact retrieval unavailable")
            if not isinstance(row.get("text"), str) or not isinstance(row.get("topics", []), list):
                raise ValueError("Malformed raw record")
            rows[row["id"]] = row
        return content, rows, version

    def _raw_items(self, root, query):
        content, rows, version = self._raw(root)
        if not rows:
            return []
        hits = _rank_raw(content, query, limit=max(1, len(rows)))
        items = []
        for hit in hits:
            row = rows.get(hit["id"])
            if row is None or row.get("cwd") != root["scope"]:
                continue
            items.append(self._item(root, {"record_id": row["id"]}, row["text"], version, _kind(row), row))
        if self._raw(root)[2] != version:
            raise ValueError("Raw source changed during retrieval")
        return items

    # -- the document tiers ---------------------------------------------------------

    def _documents(self, root, query, k):
        path = Path(root["path"])
        sidecars = self._sidecars(root)
        with tempfile.TemporaryDirectory(prefix="attune-memory-query-") as temporary:
            snapshot = Path(temporary)
            total = 0
            for name, (content, token, mtime_ns) in sidecars.items():
                if token == "absent":
                    continue
                target = snapshot / name
                target.write_bytes(content)
                os.utime(target, ns=(mtime_ns, mtime_ns))
                total += len(content)
            captured = {}
            for index, source in enumerate(path.glob("**/*.md")):
                if index >= SNAPSHOT_FILES:
                    raise ValueError("Corpus exceeds snapshot file limit; narrow the root")
                relative = source.relative_to(path)
                content, version, mtime_ns = self._capture(root, relative)
                total += len(content)
                if total > SNAPSHOT_BYTES:
                    raise ValueError("Corpus exceeds 64 MiB query snapshot limit; narrow the root")
                target = snapshot / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                os.utime(target, ns=(mtime_ns, mtime_ns))
                captured[relative.as_posix()] = (content, version)
            hits = _rank_documents(snapshot, query, k)
        if {name: token for name, (_, token, _) in self._sidecars(root).items()} != {
                name: token for name, (_, token, _) in sidecars.items()}:
            raise ValueError("Retrieval metadata changed; refresh context")
        items = []
        for hit in hits:
            relative = hit["path"]
            content, version = captured[relative]
            if self._capture(root, relative)[1] != version:
                raise ValueError("Source changed during retrieval; refresh context")
            items.append(self._item(root, {"path": relative}, content.decode("utf-8"),
                                    self._document_version(version, sidecars), Path(relative).stem, hit))
        return items

    # -- the reads ------------------------------------------------------------------

    def query(self, query, *, k=10):
        if not isinstance(query, str) or type(k) is not int or not 1 <= k <= 100:
            raise ValueError("Invalid memory query or result bound")
        items, problems = [], []
        for declared in self.config["roots"]:
            root = self._root(declared["id"])  # re-checks the binding on every root, as the adapter does
            try:
                if not Path(root["path"]).is_dir():
                    raise FileNotFoundError("Explicit memory root is unavailable")
                if root["tier"] == "raw":
                    found = self._raw_items(root, query)
                else:
                    if any(p.is_symlink() for p in Path(root["path"]).rglob("*")):
                        raise ValueError("Document corpus contains symlinks")
                    found = self._documents(root, query, k)
                items.extend(found)
            except (OSError, ValueError, ImportError, FeatureUnavailable) as error:
                problems.append({"root_id": root["id"], "reason": type(error).__name__, "detail": str(error)})
        if problems and items:
            status = "partial"
        elif problems:
            status = "unavailable"
        elif items:
            status = "available"
        else:
            status = "empty"
        return {"status": status, "items": items[:k], "problems": problems,
                "authority": self.binding, "capabilities": self.capabilities()}

    def resolve(self, handle):
        if not isinstance(handle, dict) or handle.get("authority") != self.binding:
            raise ValueError("Foreign or stale source authority")
        locator = handle["locator"]
        root = self._root(locator["root_id"])
        if root["tier"] == "raw":
            fields(locator, ("root_id", "record_id"))
            _, rows, version = self._raw(root)
            row = rows[locator["record_id"]]
            ts = _timestamp(row)
            if ts is None or ts < time.time() - RAW_TTL_SECONDS:
                raise ValueError("Raw source expired; refresh context")
            if row.get("cwd") != root["scope"]:
                raise ValueError("Raw source scope changed")
            item = self._item(root, {"record_id": row["id"]}, row["text"], version, _kind(row), row)
        else:
            fields(locator, ("root_id", "path"))
            content, version, _ = self._capture(root, locator["path"])
            item = self._item(root, {"path": locator["path"]}, content.decode("utf-8"),
                              self._document_version(version, self._sidecars(root)), Path(locator["path"]).stem, {})
        if item["version"] != handle.get("version") or item["id"] != handle.get("id"):
            raise ValueError("Source was corrected, deleted or replaced; refresh context")
        return item

    def apply(self, *args, **kwargs):
        raise ValueError("Worker mutations unavailable for legacy stores; use existing governed memory commands")


# -- ranking -----------------------------------------------------------------------


def _posix():
    """Descriptor reads need dir_fd and O_NOFOLLOW; D19 keeps them POSIX-only at 0.5.0."""
    return os.name == "posix"


def _tokenize(text):
    """The file stash's tokens: lower-cased alphanumeric runs of two or more characters, as a set."""
    return {token for token in _TOKEN.findall(str(text).lower()) if len(token) >= 2}


def _kind(row):
    """The kind a raw row declares: exactly one ``type:`` topic, else ``unknown``."""
    kinds = [t[len("type:"):] for t in row.get("topics", []) if isinstance(t, str) and t.startswith("type:")]
    return kinds[0] if len(kinds) == 1 else "unknown"


def _timestamp(row):
    try:
        return float(row.get("ts", 0.0))
    except (TypeError, ValueError):
        return None


def _rank_raw(content, query, *, limit):
    """The file stash's recall over the rows of ``findings.jsonl``, or its recent list for a blank query."""
    now = time.time()
    records = []
    for line in content.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        ts = _timestamp(record)
        if ts is None or ts < now - RAW_TTL_SECONDS:
            continue
        records.append((ts, record))
    if not query.strip():
        ordered = sorted(records, key=lambda pair: pair[0], reverse=True)
        return [dict(record, score=None) for _, record in ordered[:limit]]
    terms = _tokenize(query)
    if not terms:
        return []
    scored = []
    for ts, record in records:
        doc_terms = _tokenize(record.get("text", ""))
        for topic in record.get("topics") or ():
            doc_terms |= _tokenize(topic)
        overlap = len(terms & doc_terms)
        if not overlap:
            continue
        recency = 0.5 ** (max(0.0, now - ts) / RECENCY_HALF_LIFE_SECONDS)
        scored.append((overlap + recency, record))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(record, score=round(score, 4)) for score, record in scored[:limit]]


def _rank_documents(snapshot, query, k):
    """PersonalMemory.query's selection over the snapshot: attune-rag's keyword retriever, twice k, de-duplicated."""
    if not query.strip():
        raise ValueError("query must be a non-empty string")
    retrieval = require_feature("attune-rag", "attune_rag.retrieval", RAG_VERSION, "rag")
    corpus_module = require_feature("attune-rag", "attune_rag.corpus", RAG_VERSION, "rag")
    corpus = corpus_module.DirectoryCorpus(snapshot, summaries_file=SIDECARS[0], glob="**/*.md",
                                            warn_alias_overlap=False)
    hits = retrieval.KeywordRetriever().retrieve(query, corpus, k=k * 2)
    best = {}
    for hit in hits:
        path = hit.entry.path
        excerpt = str(hit.entry.content).strip()[:200]
        entry = {"path": path, "summary": excerpt, "excerpt": excerpt, "score": float(hit.score)}
        if path not in best or entry["score"] > best[path]["score"]:
            best[path] = entry
    ordered = sorted(best.values(), key=lambda entry: entry["score"], reverse=True)[:k]
    # The annotations PersonalMemory.query adds, in its order: staleness from the snapshot's
    # preserved mtimes and the .verdicts.jsonl sidecar, then the provenance fields. Every
    # document tier is "curated" to the adapter, personal roots included.
    verdicts = latest_verdicts(snapshot)  # one read of the sidecar for every hit
    for entry in ordered:
        annotated = staleness(snapshot / entry["path"], snapshot, verdicts=verdicts)
        if annotated is not None:
            entry.update(annotated)
        entry["provenance"] = provenance_fields(tier="curated", source=str(entry.get("path", "curated")),
                                                author_class=AUTHOR_CURATED,
                                                text=str(entry.get("excerpt") or entry.get("summary") or ""))
    return ordered


def _frontmatter(block):
    """The frontmatter as a dict: PyYAML when the install has it, a subset parser otherwise.

    The subset, for a ``--no-deps`` install: ``key: scalar`` with an unquoted
    ``#`` comment stripped, inline ``[a, b]`` lists, ``- item`` lists, ``|`` and
    ``>`` block scalars, YAML 1.1 booleans and nulls. A nested mapping reads as
    absent, which is never an ``owner``, ``scope`` or ``classification`` label.
    """
    try:
        import yaml  # a transitive dependency of the base install, absent from a --no-deps one
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            return yaml.safe_load(block)
        except yaml.YAMLError as error:
            raise ValueError("Unreadable source security metadata") from error
    result, key, block_join = {}, None, None

    def close_block():  # YAML's clip chomping keeps one trailing newline on a block scalar
        if block_join is not None and key is not None and result.get(key):
            result[key] = result[key] + "\n"

    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) or line.startswith("-"):
            if key is None:
                raise ValueError("Unreadable source security metadata")
            item = line.strip()
            if block_join is not None:
                result[key] = (result[key] + block_join + item) if result[key] else item
                continue
            if item.startswith("- "):
                result.setdefault(key, [])
                if isinstance(result[key], list):
                    result[key].append(_scalar(item[2:]))
            continue  # a nested mapping; not a label the check reads
        close_block()
        block_join = None
        name, sep, value = line.partition(":")
        if not sep or not name.strip():
            raise ValueError("Unreadable source security metadata")
        key = name.strip()
        value = _uncommented(value.strip())
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            result[key], block_join = "", ("\n" if value.startswith("|") else " ")
        elif value.startswith("[") and value.endswith("]"):
            result[key] = [_scalar(part.strip()) for part in value[1:-1].split(",") if part.strip()]
        elif value:
            result[key] = _scalar(value)
        else:
            result[key] = None
    close_block()
    return result


def _uncommented(value):
    """Drop an unquoted `` #`` comment, as YAML does."""
    if value[:1] in "\"'":
        return value
    at = value.find(" #")
    return value[:at].rstrip() if at >= 0 else value


def _scalar(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
