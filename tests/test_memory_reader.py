"""The native memory reader against the accepted fixture, and against the adapter where it exists.

Native memory Phase 2, step 2.2 (D19). The fixture is seeded the way
``test_memory_compatibility.py`` seeds it, into roots the reader is given
with explicit authority; the assertions are the adapter's contract as the
Phase 2 design note records it. The differential at the end runs only where
``ATTUNE_TEST_ADAPTER_ROOT`` names the attune-ai checkout that carries the
unreleased adapter, and compares result sets and the top result (D19).
"""
# qualify: platform

import json
import os
from pathlib import Path
import sys
import time

import pytest

from attune_harness import memory_cli, memory_reader
from attune_harness.memory_cli import main as memory_main
from attune_harness.memory_reader import CAPABILITIES, NativeReader, roots_config
from attune_harness.review_contract import digest

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "memory_compatibility.json").read_text(encoding="utf-8"))
posix_only = pytest.mark.skipif(os.name != "posix", reason="the reader is POSIX-only at 0.5.0 (D19)")


def config_for(*roots):
    return {"schema_version": 1, "actor": "patrick", "owners": ["patrick"], "scopes": ["project-a", "global"],
            "classifications": ["internal"], "profiles": ["claude"],
            "roots": [dict(id=rid, path=str(Path(path).resolve()), tier=tier, scope=scope, owner="patrick",
                           classification="internal") for rid, path, tier, scope in roots]}


def seed_raw(root, rows=None, *, ts=None):
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.time() if ts is None else ts  # one stamp for every row, so ties keep file order
    records = [dict(id=r["id"], text=r["text"], session_id="synthetic-session",
                    topics=[f"type:{r['type']}", f"cwd:{r['cwd']}"], cwd=r["cwd"],
                    ts=stamp, future_field={"keep": True})
               for r in (rows or FIXTURE["raw"])]
    (root / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return records


def seed_documents(root, which="global"):
    root.mkdir(parents=True, exist_ok=True)
    written = {}
    for entry in FIXTURE["documents"]:
        if entry["root"] != which:
            continue
        path = root / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (entry["body"] + "\n\n") * entry.get("repeat", 1) + entry.get("tail", "")
        path.write_text("# Aurora\n\n" + body, encoding="utf-8")
        written[entry["path"]] = (entry["query"], path.read_bytes())
    return written


# --- construction and authority ------------------------------------------------------


def test_config_is_validated_in_the_adapters_words_and_bound_by_digest(tmp_path):
    good = config_for(("r", tmp_path, "raw", "project-a"))
    reader = NativeReader(good)
    assert reader.binding == digest(good) and reader.capabilities() == CAPABILITIES
    assert reader.capabilities() is not CAPABILITIES
    cases = [
        (lambda c: c.pop("actor"), "Expected fields"),
        (lambda c: c.update(schema_version=2), "Requires integer schema_version 1"),
        (lambda c: c.update(classifications=["secret"]), "Unknown security classification"),
        (lambda c: c.update(roots=[]), "At least one explicit memory root is required"),
        (lambda c: c["roots"][0].update(id="bad id"), "Invalid root identity"),
        (lambda c: c["roots"].append(dict(c["roots"][0])), "Duplicate root identity"),
        (lambda c: c["roots"][0].update(tier="lessons"), "Tier uses its existing governed path"),
        (lambda c: c["roots"][0].update(scope="elsewhere"), "Memory root is outside host authority"),
        (lambda c: c["roots"][0].update(path="relative/path"), "canonical absolute path without symlinks"),
    ]
    if os.name == "posix":  # on Windows the POSIX path resolves under the drive first and fails as non-canonical
        cases.append((lambda c: c["roots"][0].update(path="/private/etc"), "system directory"))
    for mutate, text in cases:
        bad = json.loads(json.dumps(good))
        mutate(bad)
        with pytest.raises(ValueError, match=text):
            NativeReader(bad)
    with pytest.raises(ValueError, match="Invalid memory query or result bound"):
        reader.query("x", k=0)
    with pytest.raises(ValueError, match="Invalid memory query or result bound"):
        reader.query("x", k=True)
    with pytest.raises(ValueError, match="Foreign or stale source authority"):
        reader.resolve({"authority": "other", "locator": {}})


def test_roots_config_sets_the_other_sections_aside():
    assert roots_config({"roots": [], "redis": {}, "scratch": {}, "reader": "native"}) == {"roots": []}
    assert roots_config("not a dict") == "not a dict"


# --- the raw tier --------------------------------------------------------------------


@posix_only
def test_raw_recall_returns_the_scope_rows_with_kinds_and_whole_records(tmp_path):
    root = tmp_path / "raw"
    records = seed_raw(root)
    reader = NativeReader(config_for(("r", root, "raw", "project-a")))
    packet = reader.query("Aurora", k=10)
    assert packet["status"] == "available" and packet["problems"] == []
    assert [i["id"] for i in packet["items"]] == ["r:N1", "r:N2", "r:N3", "r:N4"]  # file order on equal scores
    by_id = {i["locator"]["record_id"]: i for i in packet["items"]}
    assert {rid: i["kind"] for rid, i in by_id.items()} == {"N1": "note", "N2": "decision", "N3": "pattern", "N4": "bug"}
    assert by_id["N1"]["text"] == records[0]["text"] and by_id["N1"]["metadata"]["future_field"] == {"keep": True}
    assert "N5" not in by_id  # project-b is another scope, not a lower rank
    assert set(by_id["N1"]) == {"id", "locator", "version", "authority", "text", "kind", "metadata",
                                "scope", "owner", "classification"}
    assert by_id["N1"]["authority"] == reader.binding and by_id["N1"]["scope"] == "project-a"
    # A blank query lists newest first.
    assert [i["id"] for i in reader.query("", k=10)["items"]] == ["r:N1", "r:N2", "r:N3", "r:N4"]
    # No token overlap, no items; a query of one-character tokens has no terms at all.
    assert reader.query("zephyr", k=10)["status"] == "empty"
    assert reader.query("a b", k=10)["status"] == "empty"
    # k bounds the packet across roots.
    assert len(reader.query("Aurora", k=2)["items"]) == 2


@posix_only
def test_raw_ranking_prefers_overlap_then_recency_and_drops_expired_rows(tmp_path):
    root = tmp_path / "raw"
    now = time.time()
    rows = [dict(id="old", text="Aurora Aurora quartz", type="note", cwd="p"),
            dict(id="new", text="Aurora", type="note", cwd="p"),
            dict(id="gone", text="Aurora quartz", type="note", cwd="p")]
    root.mkdir()
    records = []
    for row, ts in zip(rows, (now - 5 * 86400, now, now - 40 * 86400)):
        records.append(dict(id=row["id"], text=row["text"], topics=[f"type:{row['type']}"], cwd="p", ts=ts))
    (root / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    config = config_for(("r", root, "raw", "p"))
    config["scopes"].append("p")
    reader = NativeReader(config)
    ids = [i["locator"]["record_id"] for i in reader.query("Aurora quartz", k=10)["items"]]
    assert ids == ["old", "new"]  # two overlapping terms beat one recent term; the expired row is gone
    assert [i["locator"]["record_id"] for i in reader.query("Aurora", k=10)["items"]] == ["new", "old"]


@posix_only
def test_raw_resolve_round_trips_and_refuses_change_expiry_and_scope(tmp_path):
    root = tmp_path / "raw"
    seed_raw(root)
    reader = NativeReader(config_for(("r", root, "raw", "project-a")))
    item = next(i for i in reader.query("Aurora", k=5)["items"] if i["id"] == "r:N1")
    handle = {k: item[k] for k in ("id", "locator", "version", "authority")}
    assert reader.resolve(handle)["text"] == item["text"]
    with pytest.raises(ValueError, match="corrected, deleted or replaced"):
        reader.resolve(dict(handle, version="stale"))
    with pytest.raises(KeyError):
        reader.resolve(dict(handle, locator={"root_id": "r", "record_id": "N9"}, id="r:N9"))
    rows = [dict(r, cwd="project-b") if r["id"] == "N1" else r for r in FIXTURE["raw"]]
    seed_raw(root, rows)
    with pytest.raises(ValueError, match="Raw source scope changed"):
        reader.resolve(handle)
    seed_raw(root, ts=time.time() - 31 * 86400)
    with pytest.raises(ValueError, match="Raw source expired"):
        reader.resolve(handle)
    assert reader.query("Aurora", k=5)["status"] == "empty"  # all expired
    # An unreadable timestamp is expired too, in the adapter's words, never a TypeError.
    (root / "findings.jsonl").write_text(json.dumps(dict(id="N1", text="Aurora", cwd="project-a", topics=[], ts=None)) + "\n")
    with pytest.raises(ValueError, match="Raw source expired"):
        reader.resolve(handle)


@posix_only
def test_raw_refusals_become_root_problems(tmp_path):
    root = tmp_path / "raw"
    root.mkdir()
    (root / "findings.jsonl").write_text('{"id": "N1", "text": "Aurora", "topics": []}\n{"id": "N1", "text": "x", "topics": []}\n')
    reader = NativeReader(config_for(("r", root, "raw", "project-a")))
    packet = reader.query("Aurora", k=5)
    assert packet["status"] == "unavailable" and packet["items"] == []
    assert packet["problems"] == [{"root_id": "r", "reason": "ValueError",
                                   "detail": "Malformed or duplicate raw identity; exact retrieval unavailable"}]
    (root / "findings.jsonl").write_text('{"id": "N1", "topics": []}\n')
    assert reader.query("Aurora", k=5)["problems"][0]["detail"] == "Malformed raw record"
    # A row with no topics key is legal in the adapter; a row with two type topics has kind unknown.
    (root / "findings.jsonl").write_text(json.dumps(dict(id="N1", text="Aurora", cwd="project-a", ts=time.time())) + "\n"
                                         + json.dumps(dict(id="N2", text="Aurora", cwd="project-a", ts=time.time(),
                                                           topics=["type:a", "type:b"])) + "\n")
    packet = reader.query("Aurora", k=5)
    assert packet["status"] == "available" and [i["kind"] for i in packet["items"]] == ["unknown", "unknown"]
    # A dangling findings.jsonl symlink is an absent file, not a refusal.
    (root / "findings.jsonl").unlink()
    (root / "findings.jsonl").symlink_to(root / "nowhere.jsonl")
    assert reader.query("Aurora", k=5) ["status"] == "empty"
    missing = NativeReader(config_for(("r", tmp_path / "absent", "raw", "project-a")))
    assert missing.query("Aurora", k=5)["problems"][0]["detail"] == "Explicit memory root is unavailable"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert NativeReader(config_for(("r", empty, "raw", "project-a"))).query("Aurora", k=5)["status"] == "empty"


# --- the document tiers -----------------------------------------------------------------


@posix_only
def test_documents_are_found_by_their_queries_with_the_whole_source(tmp_path):
    root = tmp_path / "personal"
    written = seed_documents(root, "global")
    reader = NativeReader(config_for(("p", root, "personal", "global")))
    for relative, (query, source) in written.items():
        packet = reader.query(query, k=5)
        assert packet["status"] == "available", (relative, packet["problems"])
        found = {i["locator"]["path"]: i for i in packet["items"]}
        assert relative in found, (query, sorted(found))
        assert found[relative]["text"].encode("utf-8") == source  # the excerpt is bounded, the source is not
        assert found[relative]["kind"] == Path(relative).stem
        assert list(found[relative]["metadata"]) == ["path", "summary", "excerpt", "score", "unverified_days",
                                                     "staleness", "status", "provenance"]
        assert found[relative]["metadata"]["provenance"]["tier"] == "curated"
        assert found[relative]["metadata"]["staleness"] == "⟨verified today⟩"
        assert len(found[relative]["metadata"]["excerpt"]) <= 200
    long = next(i for i in reader.query("Aurora manual", k=5)["items"] if i["locator"]["path"] == "manual/reference.md")
    assert long["text"].endswith("rollback requires the original record and operation identity.")
    blank = reader.query("   ", k=5)
    assert blank["status"] == "unavailable" and blank["problems"][0]["detail"] == "query must be a non-empty string"


@posix_only
def test_document_handles_follow_the_source_and_its_sidecars(tmp_path):
    root = tmp_path / "personal"
    seed_documents(root, "global")
    reader = NativeReader(config_for(("p", root, "personal", "global")))
    item = next(i for i in reader.query("Aurora procedure", k=5)["items"] if i["locator"]["path"] == "safety/pattern.md")
    handle = {k: item[k] for k in ("id", "locator", "version", "authority")}
    assert reader.resolve(handle)["text"] == item["text"]
    (root / "summaries_by_path.json").write_text(json.dumps({"safety/pattern.md": "Aurora procedure summary"}))
    with pytest.raises(ValueError, match="corrected, deleted or replaced"):
        reader.resolve(handle)  # a sidecar is part of the version
    again = next(i for i in reader.query("Aurora procedure", k=5)["items"] if i["locator"]["path"] == "safety/pattern.md")
    assert again["version"] != item["version"]
    (root / "safety" / "pattern.md").write_text("# Aurora\n\nchanged", encoding="utf-8")
    with pytest.raises(ValueError, match="corrected, deleted or replaced"):
        reader.resolve({k: again[k] for k in ("id", "locator", "version", "authority")})


@posix_only
def test_curated_frontmatter_is_read_and_a_conflicting_label_refuses(tmp_path):
    root = tmp_path / "curated"
    root.mkdir()
    (root / FIXTURE["curated"]["path"]).write_text(FIXTURE["curated"]["content"], encoding="utf-8")
    reader = NativeReader(config_for(("c", root, "curated", "global")))
    packet = reader.query("Aurora policy", k=5)
    assert packet["status"] == "available" and packet["items"][0]["locator"]["path"] == FIXTURE["curated"]["path"]
    assert "future_field: retain-me" in packet["items"][0]["text"]
    (root / "other.md").write_text("---\nowner: someone-else\n---\n\nAurora policy again\n", encoding="utf-8")
    packet = reader.query("Aurora policy", k=5)
    assert packet["status"] == "unavailable"
    assert packet["problems"][0]["detail"] == "Source security metadata conflicts with root authority"
    (root / "other.md").write_text("---\nowner: [unterminated\n\nAurora policy again\n", encoding="utf-8")
    assert reader.query("Aurora policy", k=5)["problems"][0]["detail"] in (
        "Unterminated source security metadata", "Unreadable source security metadata")


def test_the_frontmatter_subset_parser_agrees_with_pyyaml_on_the_fixture():
    block = FIXTURE["curated"]["content"].split("---")[1]
    yaml = pytest.importorskip("yaml")
    reference = yaml.safe_load(block)
    import builtins
    real_import = builtins.__import__

    def no_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = no_yaml
    try:
        parsed = memory_reader._frontmatter(block)
    finally:
        builtins.__import__ = real_import
    assert parsed["name"] == reference["name"] and parsed["description"] == reference["description"]
    assert set(parsed) == set(reference)
    assert memory_reader._frontmatter("owner: patrick\ntags: [a, b]\nlinks:\n  - x\n  - y\nflag: true\n") == {
        "owner": "patrick", "tags": ["a", "b"], "links": ["x", "y"], "flag": True}


@posix_only
def test_bounds_symlinks_and_unsafe_strings_refuse_the_root(tmp_path, monkeypatch):
    root = tmp_path / "personal"
    seed_documents(root, "global")
    reader = NativeReader(config_for(("p", root, "personal", "global")))
    monkeypatch.setattr(memory_reader, "SNAPSHOT_FILES", 1)
    assert reader.query("Aurora", k=5)["problems"][0]["detail"] == "Corpus exceeds snapshot file limit; narrow the root"
    monkeypatch.undo()
    monkeypatch.setattr(memory_reader, "FILE_LIMIT", 64)
    assert reader.query("Aurora", k=5)["problems"][0]["detail"] == "Source exceeds read limit; select a narrower source"
    monkeypatch.undo()
    (root / "link.md").symlink_to(root / "manual" / "reference.md")
    assert reader.query("Aurora", k=5)["problems"][0]["detail"] == "Document corpus contains symlinks"
    (root / "link.md").unlink()
    (root / "leak.md").write_text("# Aurora\n\nAurora manual api_key = " + "A1b2" * 8 + "\n", encoding="utf-8")
    packet = reader.query("Aurora manual", k=5)
    assert packet["status"] == "unavailable"
    assert packet["problems"][0]["detail"] == "Source is unsafe or requires redaction; governed exposure refused"
    (root / "leak.md").unlink()
    (root / "pii.md").write_text("# Aurora\n\nAurora manual contact someone@example.com\n", encoding="utf-8")
    assert reader.query("Aurora manual", k=5)["status"] == "unavailable"


def test_non_posix_reads_are_reported_not_attempted(tmp_path, monkeypatch):
    root = tmp_path / "raw"
    seed_raw(root)
    reader = NativeReader(config_for(("r", root, "raw", "project-a")))
    monkeypatch.setattr(memory_reader, "_posix", lambda: False)
    packet = reader.query("Aurora", k=5)
    assert packet["status"] == "unavailable"
    assert packet["problems"][0]["detail"] == "Scoped descriptor reads are currently qualified only on POSIX"


@posix_only
def test_partial_status_and_nothing_from_attune_ai(tmp_path):
    raw, docs = tmp_path / "raw", tmp_path / "docs"
    seed_raw(raw)
    docs.mkdir()
    (docs / "aurora").mkdir()
    (docs / "aurora" / "decision.md").write_text("---\nowner: other\n---\nAurora reminder is 09:15.\n", encoding="utf-8")
    reader = NativeReader(config_for(("r", raw, "raw", "project-a"), ("p", docs, "personal", "global")))
    packet = reader.query("Aurora reminder", k=10)
    assert packet["status"] == "partial" and len(packet["items"]) == 4 and packet["problems"][0]["root_id"] == "p"
    if not os.environ.get("ATTUNE_TEST_ADAPTER_ROOT"):  # the differential imports the adapter on purpose
        assert not any(name == "attune" or name.startswith("attune.") for name in sys.modules)


# --- through the host and the CLI ---------------------------------------------------------


@posix_only
def test_cli_native_reader_prints_the_pinned_success_envelopes(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(memory_cli, "configure_process", lambda: None)
    root = tmp_path / "raw"
    seed_raw(root)
    config = tmp_path / "memory.json"
    config.write_text(json.dumps(dict(config_for(("r", root, "raw", "project-a")), reader="native",
                                      redis={"url": "redis://127.0.0.1:1/0"})), encoding="utf-8")
    base = ["--config", str(config)]
    assert memory_main([*base, "capabilities"]) == 0
    assert sorted(json.loads(capsys.readouterr().out)) == ["context_refresh", "mutation_status", "native_worker",
                                                          "read", "retained_paths", "worker_execution", "worker_mutations"]
    assert memory_main([*base, "recall", "Aurora", "--k", "3"]) == 0
    packet = json.loads(capsys.readouterr().out)
    assert sorted(packet) == ["authority", "guidance", "items", "k", "max_chars", "operation", "problems", "query",
                              "schema_version", "status"]
    assert packet["status"] == "available" and len(packet["items"]) == 3
    handle = tmp_path / "handle.json"
    handle.write_text(json.dumps(packet["items"][0]["handle"]))
    assert memory_main([*base, "resolve", str(handle)]) == 0
    assert sorted(json.loads(capsys.readouterr().out)) == ["authority", "classification", "id", "kind", "locator",
                                                          "metadata", "owner", "scope", "text", "version"]
    context = tmp_path / "context.json"
    context.write_text(json.dumps(packet))
    assert memory_main([*base, "refresh", str(context)]) == 0
    refreshed = json.loads(capsys.readouterr().out)
    assert sorted(refreshed) == ["context", "invalidated_ids", "replaces", "status"] and refreshed["invalidated_ids"] == []
    config.write_text(json.dumps(dict(config_for(("r", root, "raw", "project-a")), reader="bogus")), encoding="utf-8")
    assert memory_main([*base, "capabilities"]) == 2
    assert json.loads(capsys.readouterr().out)["detail"] == "Memory reader must be 'native' or 'adapter'"


# --- the differential, where the adapter exists (D19) ---------------------------------------


@posix_only
@pytest.mark.skipif(not os.environ.get("ATTUNE_TEST_ADAPTER_ROOT"), reason="ATTUNE_TEST_ADAPTER_ROOT names no adapter checkout")
def test_differential_against_the_adapter(tmp_path, monkeypatch):
    """Same roots, same queries: identical id sets and identical top result (D19); order below is reported."""
    checkout = Path(os.environ["ATTUNE_TEST_ADAPTER_ROOT"]).resolve()
    monkeypatch.syspath_prepend(str(checkout / "src"))
    adapter_module = pytest.importorskip("attune.memory.harness_adapter")
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    raw, docs, curated = tmp_path / "raw", tmp_path / "docs", tmp_path / "curated"
    seed_raw(raw)
    written = seed_documents(docs, "global")
    curated.mkdir()
    (curated / FIXTURE["curated"]["path"]).write_text(FIXTURE["curated"]["content"], encoding="utf-8")
    config = config_for(("r", raw, "raw", "project-a"), ("p", docs, "personal", "global"), ("c", curated, "curated", "global"))
    native, adapter = NativeReader(config), adapter_module.CompatibilityAdapter(config)
    assert native.binding == adapter.binding and native.capabilities() == adapter.capabilities()
    queries = ["Aurora", "", "Aurora reminder", "Aurora procedure", "Aurora recovery", "Aurora manual", "Aurora policy", "zephyr"]
    report = []
    for query in queries:
        ours, theirs = native.query(query, k=10), adapter.query(query, k=10)
        assert ours["status"] == theirs["status"], (query, ours["problems"], theirs["problems"])
        assert {i["id"] for i in ours["items"]} == {i["id"] for i in theirs["items"]}, query
        if theirs["items"]:
            assert ours["items"][0]["id"] == theirs["items"][0]["id"], query
            for mine, its in zip(ours["items"], theirs["items"]):
                assert (mine["text"], mine["kind"], mine["version"], mine["locator"]) == (its["text"], its["kind"], its["version"], its["locator"])
                assert mine["metadata"] == its["metadata"], (query, mine["id"])
        report.append((query, [i["id"] for i in ours["items"]] == [i["id"] for i in theirs["items"]]))
        for item in theirs["items"]:
            handle = {k: item[k] for k in ("id", "locator", "version", "authority")}
            assert native.resolve(handle)["text"] == adapter.resolve(handle)["text"]
    (tmp_path / "differential.json").write_text(json.dumps({"adapter_checkout": str(checkout), "order_identical": dict(report)}, indent=2))
    print("\nORDER IDENTICAL BELOW THE TOP:", dict(report))


# --- the controls the reviewer found untested ---------------------------------------------


@posix_only
def test_capture_refuses_symlinks_hard_links_and_a_read_race(tmp_path, monkeypatch):
    root = tmp_path / "personal"
    seed_documents(root, "global")
    reader = NativeReader(config_for(("p", root, "personal", "global")))
    real = root / "manual" / "reference.md"
    (root / "alias.md").symlink_to(real)
    with pytest.raises(ValueError, match="Symlink source is not authorized"):
        reader._capture(reader.config["roots"][0], "alias.md")
    (root / "alias.md").unlink()
    os.link(real, root / "twin.md")
    with pytest.raises(ValueError, match="regular file without hard links"):
        reader._capture(reader.config["roots"][0], "twin.md")
    (root / "twin.md").unlink()
    with pytest.raises(ValueError, match="Source must be a regular file"):
        reader._capture(reader.config["roots"][0], "manual")  # a directory
    real_fstat, calls = os.fstat, []

    def racing(fd):
        result = real_fstat(fd)
        calls.append(fd)
        if len(calls) % 2 == 0:  # the second look sees a different size
            return os.stat_result((result.st_mode, result.st_ino, result.st_dev, result.st_nlink, result.st_uid,
                                   result.st_gid, result.st_size + 1, result.st_atime, result.st_mtime, result.st_ctime))
        return result

    monkeypatch.setattr(memory_reader.os, "fstat", racing)
    with pytest.raises(ValueError, match="Source changed while being read"):
        reader._capture(reader.config["roots"][0], "manual/reference.md")


@posix_only
def test_documents_detect_changes_during_the_query_and_keep_mtimes(tmp_path, monkeypatch):
    root = tmp_path / "personal"
    seed_documents(root, "global")
    reader = NativeReader(config_for(("p", root, "personal", "global")))
    source = root / "safety" / "pattern.md"
    real_rank = memory_reader._rank_documents
    seen = {}

    def snapshot_keeps_mtimes(snapshot, query, k):
        seen["k"] = k
        seen["mtime_equal"] = (snapshot / "safety" / "pattern.md").stat().st_mtime_ns == source.stat().st_mtime_ns
        return real_rank(snapshot, query, k)

    monkeypatch.setattr(memory_reader, "_rank_documents", snapshot_keeps_mtimes)
    assert reader.query("Aurora procedure", k=3)["status"] == "available"
    assert seen["mtime_equal"] and seen["k"] == 3

    def sidecar_appears(snapshot, query, k):
        (root / "summaries_by_path.json").write_text("{}")
        return real_rank(snapshot, query, k)

    monkeypatch.setattr(memory_reader, "_rank_documents", sidecar_appears)
    assert reader.query("Aurora procedure", k=3)["problems"][0]["detail"] == "Retrieval metadata changed; refresh context"
    (root / "summaries_by_path.json").unlink()

    def source_changes(snapshot, query, k):
        hits = real_rank(snapshot, query, k)
        source.write_text("# Aurora\n\nAurora procedure rewritten mid-query\n", encoding="utf-8")
        return hits

    monkeypatch.setattr(memory_reader, "_rank_documents", source_changes)
    assert reader.query("Aurora procedure", k=3)["problems"][0]["detail"] == "Source changed during retrieval; refresh context"
    monkeypatch.undo()
    monkeypatch.setattr(memory_reader, "SNAPSHOT_BYTES", 100)
    assert reader.query("Aurora", k=3)["problems"][0]["detail"] == "Corpus exceeds 64 MiB query snapshot limit; narrow the root"


@posix_only
def test_the_retriever_is_asked_for_twice_k(tmp_path, monkeypatch):
    root = tmp_path / "personal"
    seed_documents(root, "global")
    reader = NativeReader(config_for(("p", root, "personal", "global")))
    asked = []
    real_require = memory_reader.require_feature

    def spying(distribution, module, expected, extra):
        loaded = real_require(distribution, module, expected, extra)
        if module.endswith("retrieval"):
            import types
            real_cls = loaded.KeywordRetriever

            class Spy(real_cls):
                def retrieve(self, query, corpus, k=3):
                    asked.append(k)
                    return super().retrieve(query, corpus, k=k)

            return types.SimpleNamespace(KeywordRetriever=Spy)
        return loaded

    monkeypatch.setattr(memory_reader, "require_feature", spying)
    reader.query("Aurora procedure", k=4)
    assert asked == [8]


@posix_only
def test_raw_reread_after_ranking_catches_a_rewrite(tmp_path, monkeypatch):
    root = tmp_path / "raw"
    seed_raw(root)
    reader = NativeReader(config_for(("r", root, "raw", "project-a")))
    real_rank = memory_reader._rank_raw

    def rewriting(content, query, *, limit):
        hits = real_rank(content, query, limit=limit)
        seed_raw(root, ts=time.time() + 1)
        return hits

    monkeypatch.setattr(memory_reader, "_rank_raw", rewriting)
    assert reader.query("Aurora", k=5)["problems"][0]["detail"] == "Raw source changed during retrieval"


@posix_only
def test_a_conflicting_label_and_a_secret_refuse_in_the_gates_words_first(tmp_path):
    root = tmp_path / "curated"
    root.mkdir()
    (root / "doc.md").write_text("---\nowner: other\n---\nAurora policy api_key = " + "A1b2" * 6 + "\n", encoding="utf-8")
    reader = NativeReader(config_for(("c", root, "curated", "global")))
    assert reader.query("Aurora policy", k=5)["problems"][0]["detail"] == "Source is unsafe or requires redaction; governed exposure refused"


def test_the_subset_parser_strips_comments_and_reads_block_scalars():
    block = "owner: patrick # the owner\nnote: |\n  first\n  second\nflag: yes\nquoted: 'a # b'\nfolded: >\n  one\n  two\n"
    import builtins
    real_import = builtins.__import__

    def no_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = no_yaml
    try:
        parsed = memory_reader._frontmatter(block)
    finally:
        builtins.__import__ = real_import
    assert parsed == {"owner": "patrick", "note": "first\nsecond\n", "flag": True, "quoted": "a # b", "folded": "one two\n"}
    yaml = pytest.importorskip("yaml")
    assert parsed == yaml.safe_load(block)


# --- the adversarial differential (2.3): odd inputs through both readers, metadata included ---------


ADVERSARIAL_QUERIES = [
    "Aurora", "aurora!!! reminder???", "AURORA-REMINDER", "Aurora, reminder; 09:15", "reminder", "ré-minder Aurora",
    "Aurora " * 40, "a", "09:15", "Aurora\treminder\nprocedure", "✨ Aurora ✨", "manual END_OF_SOURCE",
]


def adversarial_roots(tmp_path):
    """Roots built to exercise the seams: odd timestamps, frontmatter variants, punctuation in bodies."""
    raw = tmp_path / "raw"
    raw.mkdir()
    now = time.time()
    rows = [
        dict(id="fresh", text="Aurora reminder at 09:15", topics=["type:note"], cwd="project-a", ts=now),
        dict(id="older", text="Aurora reminder, older", topics=["type:note"], cwd="project-a", ts=now - 4 * 86400),
        dict(id="edge", text="Aurora reminder at the edge", topics=["type:note"], cwd="project-a", ts=now - 29.9 * 86400),
        dict(id="gone", text="Aurora reminder expired", topics=["type:note"], cwd="project-a", ts=now - 31 * 86400),
        dict(id="future", text="Aurora reminder from the future", topics=["type:note"], cwd="project-a", ts=now + 86400),
        dict(id="notopics", text="Aurora reminder without topics", cwd="project-a", ts=now),
        dict(id="twotypes", text="Aurora reminder twice typed", topics=["type:a", "type:b"], cwd="project-a", ts=now),
        dict(id="strts", text="Aurora reminder string ts", topics=["type:note"], cwd="project-a", ts=str(now)),
        dict(id="other", text="Aurora reminder elsewhere", topics=["type:note"], cwd="project-b", ts=now),
        dict(id="unicode", text="Aurora ré-minder ✨ 09:15", topics=["type:note", "cwd:project-a"], cwd="project-a", ts=now),
    ]
    (raw / "findings.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    docs = tmp_path / "docs"
    (docs / "aurora").mkdir(parents=True)
    (docs / "notes").mkdir()
    (docs / "aurora" / "decision.md").write_text("---\nowner: patrick\nscope: global\ntags: [a, b]\n---\n\n# Aurora\n\nAurora reminder is 09:15; see the manual.\n", encoding="utf-8")
    (docs / "aurora" / "pattern.md").write_text("﻿---\nname: 'quoted: colon'\n---\r\n\r\nAurora procedure with CRLF and a BOM.\r\n", encoding="utf-8")
    (docs / "notes" / "reference.md").write_text("# Aurora\n\nAurora manual END_OF_SOURCE with punctuation!!! and ✨ unicode.\n\n---\n\nA rule inside the body.\n", encoding="utf-8")
    (docs / "notes" / "troubleshooting.md").write_text("---\nlinks:\n  - one\n  - two\ndescription: |\n  Aurora recovery\n  block scalar\n---\n\nAurora recovery text.\n", encoding="utf-8")
    (docs / "summaries_by_path.json").write_text(json.dumps({"notes/reference.md": "Aurora manual summary"}), encoding="utf-8")
    return raw, docs


@posix_only
@pytest.mark.skipif(not os.environ.get("ATTUNE_TEST_ADAPTER_ROOT"), reason="ATTUNE_TEST_ADAPTER_ROOT names no adapter checkout")
def test_adversarial_differential_against_the_adapter(tmp_path, monkeypatch):
    """Odd inputs through both readers: same statuses, id sets, top results, texts, and item metadata (2.3)."""
    checkout = Path(os.environ["ATTUNE_TEST_ADAPTER_ROOT"]).resolve()
    monkeypatch.syspath_prepend(str(checkout / "src"))
    adapter_module = pytest.importorskip("attune.memory.harness_adapter")
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    raw, docs = adversarial_roots(tmp_path)
    config = config_for(("r", raw, "raw", "project-a"), ("p", docs, "personal", "global"))
    native, adapter = NativeReader(config), adapter_module.CompatibilityAdapter(config)
    metadata_gaps = {}
    for query in ADVERSARIAL_QUERIES:
        ours, theirs = native.query(query, k=10), adapter.query(query, k=10)
        assert ours["status"] == theirs["status"], (query, ours["problems"], theirs["problems"])
        assert ours["problems"] == theirs["problems"], query
        assert [i["id"] for i in ours["items"]] == [i["id"] for i in theirs["items"]], query
        for mine, its in zip(ours["items"], theirs["items"]):
            assert (mine["text"], mine["kind"], mine["version"], mine["locator"], mine["scope"]) == (
                its["text"], its["kind"], its["version"], its["locator"], its["scope"]), (query, mine["id"])
            if mine["metadata"] != its["metadata"]:
                metadata_gaps[mine["id"]] = sorted(set(its["metadata"]) ^ set(mine["metadata"]))
    print("\nMETADATA GAPS:", json.dumps(metadata_gaps, sort_keys=True))
    assert metadata_gaps == {}, "item metadata differs from the adapter's"
