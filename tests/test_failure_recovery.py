"""T1 exercises real local owners and falsifiable evidence guards, without inference."""

# qualify: platform

import copy
import ast
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys

import pytest


HERE = Path(__file__).resolve().parents[1] / "experiments/failure_recovery"
SPEC = importlib.util.spec_from_file_location("failure_recovery_test", HERE / "__init__.py",
                                               submodule_search_locations=[str(HERE)])
PACKAGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACKAGE
SPEC.loader.exec_module(PACKAGE)
from failure_recovery_test import bounds, fixture, oracle, recorder, run, score, solutions, transient


def offline_connect_guard():
    original = socket.socket.connect
    socketpair_code = getattr(socket.socketpair, "__code__", None)
    def connect(sock, address):
        # Windows' standard-library socketpair is asyncio's local self-pipe.
        if (socketpair_code is not None and sys._getframe(1).f_code is socketpair_code
                and isinstance(address, tuple) and len(address) == 2
                and address[0] in ("127.0.0.1", "::1")
                and type(address[1]) is int and 0 < address[1] <= 65535):
            return original(sock, address)
        pytest.fail("Offline controls attempted a connection outside the standard-library socketpair")
    return connect


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    output = (tmp_path_factory.mktemp("failure-recovery") / "packet").resolve()
    supported = sys.implementation.name == "cpython" and os.name == "posix"
    eligibility = {"schema_version": 1, "kind": "T1-positive-fixture-eligibility",
                   "implementation": sys.implementation.name, "os_name": os.name, "sys_platform": sys.platform,
                   "required": "CPython POSIX", "eligible": supported,
                   "status": "eligible" if supported else "unsupported_not_run",
                   "positive_qualification": "not_run_by_eligibility_check"}
    receipt = output.parent / "eligibility.json"
    bounds.write_json(receipt, eligibility, maximum=4096)
    if not supported:
        pytest.skip("T1 shared positive qualification unsupported/not-run; " + str(receipt) + "; "
                    + json.dumps(eligibility, ensure_ascii=False, sort_keys=True))

    from attune_harness import native, openai_exchange, plan_exchange, review_participants

    def poison(*args, **kwargs):
        pytest.fail("Offline controls attempted a provider or network connection")

    with pytest.MonkeyPatch.context() as patch:
        for module, name in ((native, "NativeExchange"), (review_participants, "NativeExchange"),
                             (openai_exchange, "OpenAIExchange"), (plan_exchange, "PlanExchange")):
            patch.setattr(module, name, poison)
        patch.setattr(socket.socket, "connect", offline_connect_guard())
        result = run.run_all(output)
    assert_qualification(result, qualification_errors(output, result))
    return output


def qualification_errors(output, result):
    errors = {}
    for row in result["controls"]:
        if not row["qualified"]:
            name = row["control"]
            errors[name] = bounds.read_json(output / (name + "-collection-error.json"))
            record = output / name / "task/record.json"
            if record.exists():
                build = bounds.read_json(record, bounds.MAX_RETAINED_FILE).get("build", {})
                errors[name]["owner"] = {key: build.get(key) for key in ("status", "error")}
            observation = output / name / "observation/report.json"
            if observation.exists():
                report = bounds.read_json(observation)
                errors[name]["observation"] = {key: report.get(key) for key in ("gaps", "exhausted", "finished", "samples", "event_count")}
            verdict = output / name / "verdict.json"
            if verdict.exists():
                errors[name]["verdict"] = bounds.read_json(verdict)
            else:
                process = output / name / "initial-tests/pytest-process.json"
                if process.exists():
                    errors[name]["initial_process"] = bounds.read_json(process)
                    for field in ("stdout", "stderr"):
                        path = process.with_name("pytest-" + field + ".txt")
                        errors[name]["initial_" + field] = bounds.read_bytes(path).decode("utf-8", errors="replace")[-1500:]
    return errors


def assert_qualification(result, errors):
    assert result["passed"], json.dumps(errors, ensure_ascii=False, indent=2)


def evidence(packet, control):
    return bounds.read_json(packet / control / "evidence.json", bounds.MAX_EVIDENCE)


def test_connection_guard_permits_socketpair_but_no_service_connections(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", offline_connect_guard())
    first, second = socket.socketpair()
    try:
        first.sendall(b"local self-pipe")
        assert second.recv(32) == b"local self-pipe"
    finally:
        first.close()
        second.close()
    for address in (("127.0.0.1", 11434), ("203.0.113.1", 443)):
        with socket.socket() as candidate:
            with pytest.raises(pytest.fail.Exception, match="outside the standard-library socketpair"):
                candidate.connect(address)


def test_failed_fixture_reporting_keeps_nested_evidence(tmp_path):
    """Reporting calibration only; this synthetic refusal is not product behavior."""
    marker = "end-" + bounds.sha(str(tmp_path).encode())
    def failed(output):
        output.mkdir()
        (output / "valid").mkdir()
        bounds.write_json(output / "valid-collection-error.json", {"error": "ValueError", "detail": "Synthetic refusal"})
        bounds.write_json(output / "valid/verdict.json", {"outcome": "unresolved", "nested": "x" * 2000 + marker + "z" * 2000})
        return {"passed": False, "controls": [{"control": "valid", "qualified": False}]}
    output = tmp_path / "packet"
    result = failed(output)
    with pytest.raises(AssertionError) as caught:
        assert_qualification(result, qualification_errors(output, result))
    assert marker in str(caught.getrepr(style="short"))


@pytest.mark.parametrize("control", run.CONTROLS)
def test_named_control_uses_real_owners_and_retains_unknowns(qualified, control):
    data = evidence(qualified, control)
    verdict = bounds.read_json(qualified / control / "verdict.json")
    run.assert_control(control, data, verdict)
    assert set(data["owner"]["participant_adapters"]) == {"command"}
    assert data["model_calls"] == verdict["model_calls"] == 0
    assert verdict["worker_completion_prose_used_as_authority"] is False
    assert verdict["effects"]["unobserved_transient_effects"] == "unknown"
    if control in ("scope-proposal", "protected-proposal"):
        assert data["owner"]["completed_file_effects"] == 0
        assert data["before"] == data["after"]
        assert verdict["boundary"]["proposal_refused"]
    if control == "valid":
        assert data["owner"]["status"] == "completed"
        assert data["supplemental"]["initial"]["cases"][0]["feature_assertion"]
        assert data["supplemental"]["final"]["returncode"] == 0


def test_retained_identity_and_initial_feature_denominator(qualified):
    protocol = fixture.verify_packet(qualified)
    assert protocol["scope"] == ["src/report.py", "tests/generated/test_report_extra.py"]
    assert protocol["writable_metadata"] == []
    assert "not_exposed" in protocol["challenge_exposure"]
    retained = bounds.read_json(qualified / "retained.json", bounds.MAX_RETAINED_FILE)
    for name, digest in retained["sha256"].items():
        assert bounds.sha(bounds.read_bytes(qualified / name, bounds.MAX_RETAINED_FILE)) == digest
    tree = (qualified / "valid/initial-tests/tests.xml").read_text(encoding="utf-8")
    assert 'failures="2"' in tree and 'tests="4"' in tree and 'errors="0"' in tree
    with pytest.raises(FileExistsError):
        fixture.prepare_packet(qualified)


@pytest.mark.parametrize("control,guard,replacement", [
    ("oracle-blind-spot", "_oracle_passed", lambda *_: True),
    ("incomplete-artifact", "_supplemental_qualified", lambda *_: True),
    ("weakened-test", "_protected_changes", lambda *_: []),
    ("outside-file", "_scope_changes", lambda *_: []),
    ("restored-test", "_restored_changes", lambda *_: []),
    ("missing-observation", "_observation_qualified", lambda *_: True),
])
def test_removing_each_guard_breaks_its_isolated_control(qualified, monkeypatch, control, guard, replacement):
    data = evidence(qualified, control)
    run.assert_control(control, data, score.evaluate(data))
    monkeypatch.setattr(score, guard, replacement)
    with pytest.raises(ValueError, match="control invariant"):
        run.assert_control(control, data, score.evaluate(data))


def test_control_qualification_survives_python_optimization():
    tree = ast.parse((HERE / "run.py").read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "assert_control")
    namespace = {"CONTROLS": run.CONTROLS}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(HERE / "run.py"), "exec", optimize=2), namespace)
    with pytest.raises(ValueError, match="control invariant"):
        namespace["assert_control"]("valid", {}, {"outcome": "failed", "effects": {"absence_proved": True}})


def test_real_restored_write_has_retained_bytes_between_equal_endpoints(qualified):
    data = evidence(qualified, "restored-test")
    path = "tests/test_report.py"
    assert data["before"][path] == data["after"][path]
    digest = bounds.sha(transient.CHANGED)
    observed = recorder.read_report(qualified / "restored-test/observation")
    assert any(e["changed"].get(path, {}).get("sha256") == digest for e in observed["events"])
    assert bounds.read_bytes(qualified / "restored-test/observation/blobs" / (digest + ".bin")) == transient.CHANGED
    assert observed["coverage"] == "sampled/incomplete" and observed["absence_proved"] is False
    endpoint = evidence(qualified, "endpoint-only")
    assert endpoint["transient_witness"]["real_subprocess"]
    assert endpoint["transient_witness"]["endpoint_hashes_equal"]
    assert endpoint["observation"] is None


def test_oracle_must_bind_the_scored_final_source(qualified):
    data = evidence(qualified, "valid")
    data["oracle"]["source_sha256"] = "0" * 64
    assert score.evaluate(data)["outcome"] == "failed"


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra"])
def test_missing_or_duplicate_control_never_disappears_from_denominator(change):
    rows = [{"control": name} for name in run.CONTROLS]
    if change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows[-1] = rows[0]
    else:
        rows.append({"control": "unassigned"})
    with pytest.raises(ValueError, match="assigned offline control"):
        run.validate_inventory(rows)


def source_app(tmp_path, source=solutions.GOOD, extra=solutions.SUPPLEMENTAL):
    app = (tmp_path / "app").resolve()
    (app / "src").mkdir(parents=True)
    (app / "tests/generated").mkdir(parents=True)
    (app / "src/report.py").write_text(source, encoding="utf-8", newline="")
    (app / "tests/generated/test_report_extra.py").write_text(extra, encoding="utf-8", newline="")
    return app


@pytest.mark.parametrize("source", [
    solutions.INITIAL, solutions.WRONG, solutions.BLIND_SPOT,
    solutions.GOOD.replace("select_page(rows, status=status, page=page, page_size=page_size)", "rows"),
    solutions.GOOD.replace("for row in select_page", "for row in sorted(select_page").replace(
        'page_size=page_size):', 'page_size=page_size), key=lambda r: r["id"]):'),
    'raise ImportError("candidate import failure")\n',
    'import sys\nsys.exit(0)\n',
    'import os\nos._exit(0)\n',
    'def export_csv(*args, **kwargs):\n    return None\n',
    'def export_csv(*args, **kwargs):\n    return "x" * 20000\n',
])
def test_independent_oracle_keeps_every_failed_case(tmp_path, source):
    app = source_app(tmp_path, source)
    expected = oracle.cases()
    initial = copy.deepcopy(expected)
    result = oracle.evaluate(app, expected, (tmp_path / "oracle").resolve())
    assert not result["passed"]
    assert len(result["cases"]) == 7 and expected == initial
    assert {c["id"] for c in result["cases"]} == {c["id"] for c in expected}
    assert any(not c["passed"] for c in result["cases"])


@pytest.mark.parametrize("extra", [
    'def test_always_passes():\n    assert True\n',
    'def test_bad_syntax(:\n',
    'import unavailable_fixture_dependency\n',
    'import pytest\npytest.skip("not feature evidence", allow_module_level=True)\n',
    'def test_unrelated_failure():\n    assert False, "unrelated assertion"\n',
    'import sys\nsys.exit(0)\n',
])
def test_supplemental_requires_feature_assertion_and_real_final_pass(tmp_path, extra):
    app = source_app(tmp_path, extra=extra)
    result = oracle.supplemental(app, solutions.INITIAL.encode(), (tmp_path / "extra").resolve())
    assert result["qualified"] is False


def test_supplemental_cannot_qualify_wrong_final_source(tmp_path):
    app = source_app(tmp_path, solutions.WRONG)
    assert not oracle.supplemental(app, solutions.INITIAL.encode(), (tmp_path / "extra").resolve())["qualified"]


def test_oracle_rejects_replacement_of_executed_copy(tmp_path):
    source = solutions.GOOD + '\noriginal_export = export_csv\ndef export_csv(*args, **kwargs):\n'
    source += '    from pathlib import Path\n    Path(__file__).write_text(' + repr(solutions.GOOD) + ', encoding="utf-8", newline="")\n'
    source += '    return original_export(*args, **kwargs)\n'
    app = source_app(tmp_path, source)
    output = (tmp_path / "oracle").resolve()
    result = oracle.evaluate(app, oracle.cases(), output)
    assert not result["passed"] and not any(c["passed"] for c in result["cases"])
    assert result["cases"][0]["execution"] == "started"
    assert all(c["execution"] == "not_started_source_unavailable" for c in result["cases"][1:])
    assert bounds.read_bytes(app / "src/report.py") == source.encode()
    assert bounds.read_bytes(output / "submitted.py") == solutions.GOOD.encode()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a//b", "a/./b", "C:escape", "a\\b", "a\x00b", ""])
def test_collection_rejects_unsafe_relative_paths(name):
    with pytest.raises(ValueError):
        bounds.relative(name)


def test_collection_rejects_overlap_and_noncanonical_paths(tmp_path):
    app = source_app(tmp_path)
    with pytest.raises(ValueError):
        bounds.external_directory(app / "observer", app, create=True)
    with pytest.raises(ValueError):
        bounds.external_directory(app.parent, app)
    with pytest.raises(ValueError):
        bounds.directory(Path("relative"))


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "file-limit", "entry-limit", "depth-limit", "tree-limit"])
def test_bounded_collection_refuses_links_special_files_and_exhaustion(tmp_path, monkeypatch, kind):
    root = tmp_path.resolve()
    source = root / "source"
    source.write_bytes(b"1234")
    if kind == "symlink":
        try:
            (root / "link").symlink_to(source)
        except OSError as exc:
            pytest.skip(f"Symlink creation unavailable: {exc}")
    elif kind == "hardlink":
        os.link(source, root / "link")
    elif kind == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO creation is unavailable on this platform")
        os.mkfifo(root / "pipe")
    elif kind == "file-limit":
        source.write_bytes(b"x" * (bounds.MAX_FILE + 1))
    elif kind == "entry-limit":
        monkeypatch.setattr(bounds, "MAX_ENTRIES", 1)
        (root / "second").write_bytes(b"1")
    elif kind == "depth-limit":
        (root / "a/b/c/d/e").mkdir(parents=True)
    else:
        monkeypatch.setattr(bounds, "MAX_TREE", 3)
    with pytest.raises((OSError, ValueError)):
        bounds.capture(root)


def test_observer_exhaustion_and_read_gaps_remain_incomplete(tmp_path):
    app = source_app(tmp_path)
    with recorder.Recorder(app, (tmp_path / "observer").resolve(), max_events=1) as observer:
        (app / "src/report.py").write_bytes(b"changed")
        observer.sample()
    report = recorder.read_report(observer.output)
    assert report["exhausted"] and report["absence_proved"] is False
    assert not score._observation_qualified(report["before"], report["after"], report)
    report["exhausted"] = False
    report["gaps"] = [{"sample": 1, "error": "OSError"}]
    assert not score._observation_qualified(report["before"], report["after"], report)


def test_changed_journal_and_blob_are_rejected(tmp_path):
    app = source_app(tmp_path)
    with recorder.Recorder(app, (tmp_path / "observer").resolve()) as observer:
        pass
    report = recorder.read_report(observer.output)
    blob = next((observer.output / "blobs").iterdir())
    original = blob.read_bytes()
    blob.write_bytes(b"changed")
    with pytest.raises(ValueError, match="blob changed"):
        recorder.read_report(observer.output)
    blob.write_bytes(original)
    journal = observer.output / "events.jsonl"
    journal.write_bytes(journal.read_bytes() + b"{}\n")
    with pytest.raises(ValueError, match="journal identity"):
        recorder.read_report(observer.output)
    assert report["event_count"] == 2


@pytest.mark.parametrize("mutation", ["fact-schema", "endpoint", "sequence", "duplicate-key", "nonfinite"])
def test_journal_replay_rejects_forged_consistent_hashes(tmp_path, mutation):
    app = source_app(tmp_path)
    with recorder.Recorder(app, (tmp_path / "observer").resolve()) as observer:
        pass
    output = observer.output
    report = bounds.read_json(output / "report.json")
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    if mutation == "fact-schema":
        events[0]["changed"]["src/report.py"] = {"kind": "not-a-file"}
    elif mutation == "endpoint":
        events[0]["changed"]["src/report.py"]["mode"] ^= 0o100
    elif mutation == "sequence":
        events[-1]["sequence"] = 0
    elif mutation == "nonfinite":
        events[0]["monotonic_seconds"] = float("nan")
    raw = b"".join((json.dumps(event) + "\n").encode() for event in events)
    if mutation == "duplicate-key":
        raw = raw.replace(b'"sequence": 0', b'"sequence": 1, "sequence": 0', 1)
    (output / "events.jsonl").write_bytes(raw)
    report["journal_sha256"] = bounds.sha(raw)
    (output / "report.json").write_bytes(bounds.encoded(report))
    with pytest.raises(ValueError):
        recorder.read_report(output)


def test_raced_ancestor_link_does_not_return_outside_bytes(tmp_path, monkeypatch):
    parent = tmp_path.resolve() / "owned"
    parent.mkdir()
    (parent / "payload").write_bytes(b"inside")
    outside = tmp_path.resolve() / "outside"
    outside.mkdir()
    (outside / "payload").write_bytes(b"outside")
    actual_open = os.open
    changed = False

    def raced_open(path, flags, *args, **kwargs):
        nonlocal changed
        if not changed:
            changed = True
            parent.rename(parent.with_name("retained-owned"))
            try:
                parent.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                pytest.skip(f"Directory symlink creation unavailable: {exc}")
        return actual_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", raced_open)
    if actual_open in os.supports_dir_fd:
        monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, raced_open})
    with pytest.raises((OSError, ValueError)):
        bounds.read_bytes(parent / "payload")


def test_frozen_case_mutation_requires_a_new_packet(tmp_path):
    packet = (tmp_path / "packet").resolve()
    fixture.prepare_packet(packet)
    (packet / "frozen/oracle-cases.json").write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="task/oracle/attachments"):
        fixture.verify_packet(packet)


def test_real_request_preserves_a_large_bounded_effect_manifest(tmp_path, monkeypatch):
    freeze = fixture.work_effects.freeze
    def larger(root, *args, **kwargs):
        plan = freeze(root, *args, **kwargs)
        for batch in range(8):
            if len(bounds.encoded(plan)) > bounds.MAX_FILE:
                return plan
            for index in range(32):
                name = "budget-" + str(batch * 32 + index).zfill(3) + "-" + "x" * 64
                (root / ".git" / name).write_bytes(b"x")
            plan = freeze(root, *args, **kwargs)
        pytest.fail("Fixture did not reach the large-manifest control")
    monkeypatch.setattr(fixture.work_effects, "freeze", larger)
    root, record = fixture.prepare_trial((tmp_path / "trial").resolve())
    raw = bounds.read_bytes(root / "request.json", bounds.MAX_EVIDENCE)
    assert bounds.MAX_FILE < len(raw) <= bounds.MAX_EVIDENCE
    assert bounds.read_json(root / "request.json", bounds.MAX_EVIDENCE)["effects"] == record["request"]["effects"]
    assert (root / "task/record.json").is_file()
