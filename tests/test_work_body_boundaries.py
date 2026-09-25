"""Refused body edits preserve accepted authority and bytes outside the function."""

import copy
import json
import os

import pytest

from attune_harness import repair, work_effects
from attune_harness.task_contract import read_task
from attune_harness.work_contract import revise_work
from attune_harness.work_runtime import build_work
from test_work_function_bodies import (
    BodyWorker, bounded, prepare_body_build, proposal, work,
)

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX file-effect fixture")


@pytest.fixture(autouse=True)
def exclusive_fixture_checkout(monkeypatch):
    # A fixture commit must not leave Git maintenance writing behind the owner.
    count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    monkeypatch.setenv("GIT_CONFIG_KEY_" + str(count), "maintenance.auto")
    monkeypatch.setenv("GIT_CONFIG_VALUE_" + str(count), "false")
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(count + 1))


@pytest.mark.parametrize(
    "fault",
    ["extra_manifest_field", "version", "bindings_type", "missing_binding",
     "extra_binding_field", "symbol", "source_type", "source_size", "preimage"],
)
def test_invalid_body_authority_cannot_replace_an_accepted_revision(work, fault):
    root, directory, _ = prepare_body_build(work)
    before = read_task(directory)
    plan = copy.deepcopy(before["request"]["effects"])
    extension = plan["function_bodies"]
    binding = extension["bindings"]["source.py"]
    if fault == "extra_manifest_field":
        extension["allow_globals"] = True
    elif fault == "version":
        extension["version"] = True
    elif fault == "bindings_type":
        extension["bindings"] = []
    elif fault == "missing_binding":
        extension["bindings"] = {}
    elif fault == "extra_binding_field":
        binding["allow_signature"] = True
    elif fault == "symbol":
        binding["symbol"] = "value.other"
    elif fault == "source_type":
        binding["source"] = [binding["source"]]
    elif fault == "source_size":
        binding["source"] = "é" * (repair.MAX_FILE // 2 + 1)
    else:
        binding["source"] = binding["source"].replace("return 1", "return 99")
    source = (root / "source.py").read_bytes()
    with pytest.raises(ValueError):
        revise_work(directory, checkpoint=before["checkpoint_digest"], changes={"effects": plan})
    assert read_task(directory) == before
    assert (root / "source.py").read_bytes() == source
    assert repair.snapshot(before["request"]["effects"]) == before["request"]["effects"]["before"]


@pytest.mark.parametrize(
    "raw,name",
    [
        (b"# coding: unknown-codec\ndef target():\n    return 1\n", "subject.py"),
        (b"\xef\xbb\xbfdef target():\n    return 1\n", "subject.py"),
        (b"def target():\n    return 1", "subject.py"),
        (b"# coding: latin-1\ndef target():\n    return '\xe9'\n", "subject.py"),
        (b"def target():\n    return 1\n", "subject.js"),
    ],
)
def test_unsupported_retained_source_never_creates_body_authority(tmp_path, raw, name):
    root, state = tmp_path / "checkout", tmp_path / "state"
    root.mkdir()
    state.mkdir()
    (root / ".git").mkdir()
    (root / name).write_bytes(raw)
    (root / "guard.txt").write_bytes(b"protected\n")
    with pytest.raises((ValueError, UnicodeError)):
        work_effects.freeze(root, [name], [], ["guard.txt"], [], state,
                            function_bodies={name: "target"})
    assert (root / name).read_bytes() == raw
    assert (root / "guard.txt").read_bytes() == b"protected\n"
    assert list(state.iterdir()) == []


@pytest.mark.parametrize("boundary", ["write", "reconcile"])
@pytest.mark.parametrize("fault", ["creation", "wrong_preimage", "nontext", "oversize"])
def test_full_file_effect_rechecks_body_authority_before_touching_bytes(bounded, boundary, fault):
    root, plan = bounded
    original = (root / "subject.py").read_bytes()
    item = work_effects.operations(plan, proposal())[0]
    if fault == "creation":
        item["kind"] = "creation"
    elif fault == "wrong_preimage":
        item["before_sha256"] = "0" * 64
    elif fault == "nontext":
        item["text"] = None
    else:
        item["text"] = "é" * (repair.MAX_FILE // 2 + 1)
    event = dict(event_id="interrupted", kind="file_effect", state="pending",
                 phase="dispatching", attempts=1, item=item)
    retained = copy.deepcopy(event)
    with pytest.raises(ValueError):
        if boundary == "write":
            work_effects.write_effect(plan, item)
        else:
            work_effects.reconcile_effect(plan, [event], "interrupted", retry_before=True)
    assert event == retained
    assert (root / "subject.py").read_bytes() == original
    assert repair.snapshot(plan) == plan["before"]


@pytest.mark.parametrize(
    "body",
    ["", "    return 42", "\treturn 42\n", "    return 42\r\n",
     "    return 42\nOWNER_VALUE = 9\n", "# escaped\n    return 42\n"],
)
def test_invalid_worker_body_is_retained_without_write_or_repeat(work, monkeypatch, body):
    root, directory, _ = prepare_body_build(work)
    accepted = read_task(directory)
    snapshot = repair.snapshot(accepted["request"]["effects"])
    monkeypatch.setattr(BodyWorker, "body", body)
    monkeypatch.setattr(BodyWorker, "calls", 0)
    failed = build_work(directory, exchange_factory=BodyWorker)
    assert failed["build"]["status"] == "failed"
    assert len(failed["build"]["events"]) == 1
    event = failed["build"]["events"][0]
    saved = json.loads(event["result"]["action"]["text"])
    assert saved["bodies"] == [{"path": "source.py", "body": body}]
    assert (root / "source.py").read_bytes() == b"def value():\n    return 1\n"
    assert repair.snapshot(accepted["request"]["effects"]) == snapshot
    resumed = build_work(directory, exchange_factory=BodyWorker)
    assert resumed == read_task(directory)
    assert resumed["build"]["events"] == failed["build"]["events"]
    assert BodyWorker.calls == 1


@pytest.mark.parametrize("mutation", ["header_comment", "decorator", "signature", "tail_comment"])
def test_full_file_cannot_change_even_nonsemantic_outside_bytes(bounded, mutation):
    root, plan = bounded
    before = (root / "subject.py").read_bytes()
    item = work_effects.operations(plan, proposal())[0]
    edits = {
        "header_comment": ("# café", "# other café"),
        "decorator": ("@decorator", "@other_decorator"),
        "signature": ("value: int = 3", "value: int = 4"),
        "tail_comment": ("# untouched tail", "# changed tail"),
    }
    item["text"] = item["text"].replace(*edits[mutation])
    with pytest.raises(ValueError, match="accepted function body boundary"):
        work_effects.write_effect(plan, item)
    assert (root / "subject.py").read_bytes() == before
    assert repair.snapshot(plan) == plan["before"]


def test_async_body_with_decorated_nested_function_preserves_interface_bytes(tmp_path):
    prefix = b"# caf\xc3\xa9\nMARKER = 7\n\nasync def target(value: int = 3) -> int:\n"
    old_body = b"    def decorate(fn):\n        return fn\n\n    @decorate\n    def nested():\n        return value - 1\n    return nested()\n"
    suffix = b"\n# untouched trailing comment\ndef other():\n    return MARKER\n"
    root, state = tmp_path / "checkout", tmp_path / "state"
    root.mkdir()
    state.mkdir()
    (root / ".git").mkdir()
    (root / "subject.py").write_bytes(prefix + old_body + suffix)
    (root / "guard.txt").write_bytes(b"protected\n")
    plan = work_effects.freeze(root, ["subject.py"], [], ["guard.txt"], [], state,
                               function_bodies={"subject.py": "target"})
    body = "    # naïve replacement\n    return value + 1\n"
    item = work_effects.operations(plan, proposal(body))[0]
    work_effects.write_effect(plan, item)
    assert (root / "subject.py").read_bytes() == prefix + body.encode() + suffix
    import asyncio
    namespace = {}
    exec(compile((root / "subject.py").read_bytes(), "subject.py", "exec"), namespace)
    assert asyncio.run(namespace["target"]()) == 4
    assert namespace["other"]() == 7
    assert (root / "guard.txt").read_bytes() == b"protected\n"


def test_entire_body_batch_is_validated_before_first_file_effect(work, monkeypatch):
    root, directory, _ = prepare_body_build(work, two_steps=True)
    accepted = read_task(directory)
    before = repair.snapshot(accepted["request"]["effects"])
    # The first task cannot claim the later task's accepted output as its own.
    class ExpandedWorker(BodyWorker):
        def __call__(self, raw):
            wire = json.loads(super().__call__(raw))
            payload = json.loads(wire["action"]["text"])
            payload["bodies"].append({"path": "second.py", "body": "    return 42\n"})
            wire["action"]["text"] = json.dumps(payload)
            return json.dumps(wire)

    monkeypatch.setattr(ExpandedWorker, "body", "    return 42\n")
    monkeypatch.setattr(ExpandedWorker, "calls", 0)
    failed = build_work(directory, exchange_factory=ExpandedWorker)
    assert failed["build"]["status"] == "failed"
    assert ExpandedWorker.calls == 1
    assert all(e["kind"] != "file_effect" for e in failed["build"]["events"])
    assert repair.snapshot(accepted["request"]["effects"]) == before
    assert (root / "source.py").read_text() == "def value():\n    return 1\n"
    assert (root / "second.py").read_text() == "def second():\n    return 1\n"


def test_utf8_body_budget_counts_bytes_before_any_materialization_effect(bounded):
    root, plan = bounded
    before = (root / "subject.py").read_bytes()
    body = "    return '" + "💡" * 17000 + "'\n"
    assert len(body) < repair.MAX_FILE < len(body.encode("utf-8"))
    with pytest.raises(ValueError, match="UTF-8 byte limit"):
        work_effects.operations(plan, proposal(body))
    assert (root / "subject.py").read_bytes() == before
    assert repair.snapshot(plan) == plan["before"]


def test_nested_first_statement_decorator_is_removed_with_its_function(bounded):
    root, _ = bounded
    source = "def target(value=3):\n    @str\n    def nested():\n        return value\n    return nested\n\n# tail\n"
    (root / "subject.py").write_text(source, encoding="utf-8")
    plan = work_effects.freeze(root, ["subject.py"], [], ["guard.txt"], [],
                               root.parent / "state", function_bodies={"subject.py": "target"})
    item = work_effects.operations(plan, proposal("    return value + 1\n"))[0]
    work_effects.write_effect(plan, item)
    assert (root / "subject.py").read_bytes() == b"def target(value=3):\n    return value + 1\n\n# tail\n"
    assert (root / "guard.txt").read_bytes() == b"fixed\n"
