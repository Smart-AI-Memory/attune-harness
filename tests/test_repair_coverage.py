"""Active POSIX repair boundaries: reject unsafe probes and preserve changed bytes."""

import copy
import os

import pytest

from attune_harness import repair
from attune_harness.recovery import UnresolvedOperation
from test_task_repair_effects import effect_case, patch

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX repair profile")


@pytest.mark.parametrize(
    "change",
    [
        {"cwd": ".."},
        {"timeout": True},
        {"timeout": 121},
        {"max_output_bytes": 0},
        {"max_output_bytes": True},
        {"environment": {"PYTHONDONTWRITEBYTECODE": "1"}},
        {"oracle_paths": []},
        {"argv": ["python", "probe.py"]},
    ],
)
def test_invalid_probe_cannot_freeze_effect_authority(effect_case, change):
    root, plan, store, _ = effect_case
    probe = {**copy.deepcopy(plan["probe"]), **change}
    with pytest.raises(ValueError):
        repair.freeze(root, plan["allowed"], probe, store.directory)
    assert repair.snapshot(plan) == plan["before"]


def test_editable_checkout_cannot_supply_trusted_executable(effect_case):
    root, plan, store, _ = effect_case
    probe = copy.deepcopy(plan["probe"])
    probe["argv"] = [str(root / "probe.py")]
    with pytest.raises(ValueError, match="outside editable checkout"):
        repair.freeze(root, plan["allowed"], probe, store.directory)
    assert repair.snapshot(plan) == plan["before"]


def test_missing_accepted_file_does_not_create_repair_authority(effect_case):
    root, plan, store, _ = effect_case
    with pytest.raises(ValueError, match="existing regular files"):
        repair.freeze(root, ["missing.py"], plan["probe"], store.directory)
    assert not (root / "missing.py").exists()


@pytest.mark.parametrize("allowed", [[], ["app.py", "app.py"]])
def test_empty_or_duplicate_scope_cannot_freeze(effect_case, allowed):
    root, plan, store, _ = effect_case
    with pytest.raises(ValueError, match="distinct replacement paths"):
        repair.freeze(root, allowed, plan["probe"], store.directory)
    assert repair.snapshot(plan) == plan["before"]


def test_changed_probe_executable_is_not_dispatched(effect_case, tmp_path, monkeypatch):
    root, plan, store, _ = effect_case
    executable = tmp_path / "trusted-check"
    executable.write_bytes(b"original executable")
    probe = copy.deepcopy(plan["probe"])
    probe["argv"] = [str(executable)]
    frozen = repair.freeze(root, plan["allowed"], probe, store.directory)
    executable.write_bytes(b"changed executable")
    from attune_harness import process

    monkeypatch.setattr(process, "invoke", lambda *a, **kw: pytest.fail("dispatched changed probe"))
    with pytest.raises(ValueError, match="executable changed"):
        repair.run_probe(frozen, frozen["before"])
    assert repair.snapshot(plan) == plan["before"]


@pytest.mark.parametrize("boundary", ["before_read", "before_commit"])
def test_replacement_preserves_new_owner_bytes(effect_case, monkeypatch, boundary):
    root, plan, _, _ = effect_case
    item = patch(plan)["replacements"][0]
    original = repair.read_file
    reads = 0

    def changed(parent, leaf, **kwargs):
        nonlocal reads
        if leaf == "app.py":
            reads += 1
            if reads == (1 if boundary == "before_read" else 2):
                (root / "app.py").write_bytes(b"new owner bytes\n")
        return original(parent, leaf, **kwargs)

    monkeypatch.setattr(repair, "read_file", changed)
    with pytest.raises(UnresolvedOperation, match="preimage changed"):
        repair.replace_file(plan, item)
    assert (root / "app.py").read_bytes() == b"new owner bytes\n"
    assert not list(root.glob(".harness-replace-*"))
    assert (root / "other.py").read_bytes() == b"VALUE = 1\n"


def test_reconciliation_does_not_accept_correct_bytes_with_changed_permissions(effect_case):
    root, plan, _, _ = effect_case
    item = patch(plan)["replacements"][0]
    repair.replace_file(plan, item)
    (root / "app.py").chmod(0o700)
    event = dict(kind="replacement", phase="dispatching", state="pending", attempts=1, patch=item)
    before = copy.deepcopy(event)
    with pytest.raises(UnresolvedOperation, match="mode changed"):
        repair.reconcile_replacement(plan, event)
    assert event == before
    assert (root / "app.py").read_text() == item["text"]
    assert (root / "app.py").stat().st_mode & 0o777 == 0o700


def test_snapshot_rejects_file_changed_during_read(effect_case, monkeypatch):
    root, plan, _, _ = effect_case
    original = os.read
    changed = False

    def read_then_change(fd, count):
        nonlocal changed
        block = original(fd, count)
        if block.startswith(b"def add") and not changed:
            changed = True
            (root / "app.py").write_bytes(b"replacement during read\n")
        return block

    monkeypatch.setattr(os, "read", read_then_change)
    with pytest.raises(ValueError, match="changed while reading"):
        repair.snapshot(plan)
    assert (root / "app.py").read_bytes() == b"replacement during read\n"
