"""Real disposable files/checks and process death; no live models or memory stores."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import test_work_contract as contracts
from attune_harness import repair, work_effects
from attune_harness.features import FeatureUnavailable
from attune_harness.recovery import UnresolvedOperation
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.task_contract import read_task
from attune_harness.work_contract import create_work, revise_work
from attune_harness.work_runtime import apply_work_effects, reconcile_work_effect

work = contracts.work


def prepare(
    work,
    *,
    script="print('ready')",
    required=True,
    runner=True,
    kind="check",
    controls=None,
    accept=True,
):
    root, config, data = work
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "oracle.py").write_text(script)
    control = dict(
        id="preflight",
        kind=kind,
        owner="trusted-host",
        version=1,
        required=required,
        phases=["build"],
    )
    data = copy.deepcopy(data)
    data["intent"]["scope"] = ["source.py", "pkg/sub/new.py"]
    data["controls"] = controls if controls is not None else [control]
    probe = dict(
        argv=[sys.executable, "-B", "oracle.py"],
        cwd=".",
        timeout=2,
        max_output_bytes=2048,
        environment={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
        oracle_paths=["oracle.py"],
    )
    data["effects"] = work_effects.freeze(
        root,
        data["intent"]["scope"],
        ["pkg", "pkg/sub"],
        ["plan.md", "oracle.py"],
        [{"control": work_effects.identity(control), "probe": probe}] if runner else [],
        data["directory"],
    )
    record = create_work(root, config, **data)
    if accept:
        record = contracts.accept(
            (root, config, data),
            record,
            supported_controls=[work_effects.identity(c) for c in data["controls"]],
        )
    proposal = {
        "schema_version": 1,
        "files": [
            {
                "path": "source.py",
                "before_sha256": record["request"]["evidence"]["source.py"],
                "text": "def value():\n    return 2\n",
            },
            {"path": "pkg/sub/new.py", "before_sha256": None, "text": "answer = 42\n"},
        ],
    }
    return root, data["directory"], record, proposal


def execute(case, **kwargs):
    root, directory, _, proposal = case
    record = read_task(directory)
    return apply_work_effects(
        directory, record["checkpoint_digest"], proposal, **kwargs
    )


def reconcile(case, **kwargs):
    record = read_task(case[1])
    event = record["build"]["events"][-1]
    return reconcile_work_effect(
        case[1], record["checkpoint_digest"], event["event_id"], **kwargs
    )


def test_actual_new_files_parents_replacements_and_no_repeat(work):
    case = prepare(work)
    root = case[0]
    before = repair.snapshot(case[2]["request"]["effects"])
    result = execute(case)
    assert result["build"]["status"] == "completed"
    assert (root / "pkg/sub/new.py").read_text() == "answer = 42\n"
    assert (root / "source.py").read_text().endswith("return 2\n")
    after = repair.snapshot(case[2]["request"]["effects"])
    assert {k: v for k, v in before.items() if k != "source.py"} == {
        k: v for k, v in after.items() if k in before and k != "source.py"
    }
    assert (root / "unrelated.txt").read_text() == "Keep my dirty work\n"
    files = [root / "source.py", root / "pkg/sub/new.py"]
    inodes = [p.stat().st_ino for p in files]
    again = execute(case)
    assert [p.stat().st_ino for p in files] == inodes
    assert len(again["build"]["events"]) == 5
    assert again["build"]["events"][0]["result"]["stdout"] == "ready\n"
    # An independent execution confirms actual source behavior.
    assert (
        subprocess.check_output(
            [
                sys.executable,
                "-B",
                "-c",
                "from source import value;from pkg.sub.new import answer;assert value()==2 and answer==42",
            ],
            cwd=root,
        )
        == b""
    )


@pytest.mark.parametrize("kind", ["check", "hook"])
def test_required_failed_control_runs_before_first_write(work, kind):
    case = prepare(work, script="raise SystemExit(3)", kind=kind)
    with pytest.raises(UnresolvedOperation, match="Build control failed"):
        execute(case)
    assert not (case[0] / "pkg").exists()
    assert (case[0] / "source.py").read_text().endswith("return 1\n")
    run = read_task(case[1])["build"]
    assert len(run["events"]) == 1
    assert run["events"][0]["result"]["returncode"] == 3
    with pytest.raises(UnresolvedOperation):
        execute(case)
    assert len(read_task(case[1])["build"]["events"]) == 1


def test_missing_required_control_blocks_before_any_command(work):
    case = prepare(work, runner=False)
    with pytest.raises(
        ValueError, match="Required build control has no qualified runner"
    ):
        execute(case)
    assert "build" not in read_task(case[1])
    assert not (case[0] / "pkg").exists()


@pytest.mark.parametrize("phase", ["plan", "accept"])
def test_prior_phase_control_support_is_not_mistaken_for_execution(work, phase):
    case = prepare(
        work,
        controls=[
            dict(
                id="prior",
                kind="host",
                owner="trusted-host",
                version=1,
                required=True,
                phases=[phase],
            )
        ],
        runner=False,
    )
    with pytest.raises(ValueError, match="control execution is not qualified"):
        execute(case)
    assert "build" not in read_task(case[1])


def test_manifest_protects_acceptance_inputs_even_inside_the_intent_scope(work):
    case = prepare(work, accept=False)
    plan = copy.deepcopy(case[2]["request"]["effects"])
    plan["allowed"].append("oracle.py")
    with pytest.raises(
        ValueError, match="Protected acceptance inputs cannot be edited"
    ):
        work_effects.validate_manifest(plan)


def test_manifest_requires_explicit_parent_authority(work):
    case = prepare(work, accept=False)
    plan = copy.deepcopy(case[2]["request"]["effects"])
    plan["parents"] = []
    with pytest.raises(ValueError, match="parents must be explicitly"):
        work_effects.validate_manifest(plan)


@pytest.mark.parametrize("kind", ["host", "human", "guidance"])
def test_unsupported_required_control_is_not_satisfied_by_declared_support(work, kind):
    case = prepare(work, runner=False, kind=kind)
    with pytest.raises(ValueError, match="no qualified runner"):
        execute(case)


@pytest.mark.parametrize("runner", [True, False])
def test_advisory_control_remains_visible_without_becoming_a_new_gate(work, runner):
    case = prepare(work, required=False, runner=runner, script="raise SystemExit(1)")
    result = execute(case)
    assert result["build"]["status"] == "completed"
    assert result["build"]["advisory"][0]["status"] == (
        "failed" if runner else "unavailable"
    )


@pytest.mark.parametrize(
    "script,failure",
    [
        ("import time;time.sleep(4)", "timeout_effects_unknown"),
        ("print('x'*10000)", "output_limit"),
        ("import os;os.write(1,b'\\xff')", "invalid_utf8"),
    ],
)
def test_uncertain_check_blocks_even_when_advisory(work, script, failure):
    case = prepare(work, required=False, script=script)
    with pytest.raises(UnresolvedOperation):
        execute(case)
    assert not (case[0] / "pkg").exists()
    assert read_task(case[1])["build"]["events"][0]["result"]["failure"] == failure


def test_mutating_check_is_detected_before_worker_effects(work):
    case = prepare(
        work, script="from pathlib import Path;Path('source.py').write_text('changed')"
    )
    with pytest.raises(UnresolvedOperation):
        execute(case)
    assert not (case[0] / "pkg").exists()
    assert read_task(case[1])["build"]["events"][0]["effects"] == "unknown"


def test_explicit_check_environment_does_not_inherit_secrets(work, monkeypatch):
    monkeypatch.setenv("HARNESS_SYNTHETIC_SENTINEL", "not-a-secret")
    case = prepare(
        work, script="import os;assert 'HARNESS_SYNTHETIC_SENTINEL' not in os.environ"
    )
    assert execute(case)["build"]["status"] == "completed"


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "/tmp/out.py",
        "./source.py",
        "pkg//new.py",
        "pkg/../new.py",
        "pkg\\new.py",
        ".git/config",
        "oracle.py",
        "plan.md",
        "outside_scope.py",
    ],
)
def test_proposal_cannot_expand_scope_or_edit_protected_inputs(work, path):
    case = prepare(work)
    case[3]["files"][1]["path"] = path
    with pytest.raises(ValueError):
        execute(case)
    assert "build" not in read_task(case[1])
    assert (case[0] / "source.py").read_text().endswith("return 1\n")


@pytest.mark.parametrize(
    "bad", ["duplicate", "stale", "oversize", "surrogate", "extra", "empty", "no_op"]
)
def test_entire_proposal_is_validated_before_first_effect(work, bad):
    case = prepare(work)
    proposal = case[3]
    if bad == "duplicate":
        proposal["files"].append(copy.deepcopy(proposal["files"][0]))
    elif bad == "stale":
        proposal["files"][1]["before_sha256"] = "0" * 64
    elif bad == "oversize":
        proposal["files"][1]["text"] = "é" * 40000
    elif bad == "surrogate":
        proposal["files"][1]["text"] = "\ud800"
    elif bad == "extra":
        proposal["files"][1]["delete"] = True
    elif bad == "empty":
        proposal["files"] = []
    else:
        proposal["files"][0]["text"] = (case[0] / "source.py").read_text()
    with pytest.raises((ValueError, UnicodeError)):
        execute(case)
    assert not (case[0] / "pkg").exists()
    assert "build" not in read_task(case[1])


@pytest.mark.parametrize(
    "changed", ["source.py", "oracle.py", "plan.md", "unrelated.txt", ".git/config"]
)
def test_changed_source_protected_or_unrelated_files_invalidate_authority(
    work, changed
):
    case = prepare(work)
    (case[0] / changed).write_text("changed\n")
    with pytest.raises((ValueError, UnresolvedOperation)):
        execute(case)
    assert not (case[0] / "pkg").exists()


def test_creation_collision_after_acceptance_is_preserved(work):
    case = prepare(work)
    (case[0] / "pkg/sub").mkdir(parents=True)
    (case[0] / "pkg/sub/new.py").write_text("someone else's file")
    with pytest.raises(UnresolvedOperation):
        execute(case)
    assert (case[0] / "pkg/sub/new.py").read_text() == "someone else's file"


def test_exclusive_create_refuses_last_moment_collision(work, monkeypatch):
    case = prepare(work)
    original = work_effects.write_effect

    def collide(plan, item):
        if item["kind"] == "creation":
            (case[0] / item["path"]).write_text("collision")
        return original(plan, item)

    monkeypatch.setattr(work_effects, "write_effect", collide)
    with pytest.raises(FileExistsError):
        execute(case)
    assert (case[0] / "pkg/sub/new.py").read_text() == "collision"
    with pytest.raises(UnresolvedOperation):
        reconcile(case)


@pytest.mark.parametrize("link", ["symlink", "hardlink", "parent_symlink"])
def test_links_cannot_enter_the_snapshot_or_effect_scope(work, link):
    root = work[0]
    if link == "symlink":
        (root / "evil").symlink_to(root / "source.py")
    elif link == "hardlink":
        os.link(root / "source.py", root / "evil")
    else:
        (root / "pkg").symlink_to(root.parent, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        prepare(work)


@pytest.mark.parametrize(
    "bad", ["parents", "protected", "directory", "file_parent", "scope", "artifact"]
)
def test_manifest_rejects_unsafe_or_implicit_effect_authority(work, bad):
    case = prepare(work, accept=False)
    record = case[2]
    plan = copy.deepcopy(record["request"]["effects"])
    if bad == "parents":
        plan["parents"] = []
    elif bad == "protected":
        plan["allowed"].append("oracle.py")
    elif bad == "directory":
        plan["allowed"].append(".git")
    elif bad == "file_parent":
        plan["allowed"].append("source.py/child.py")
    elif bad == "scope":
        plan["allowed"].append("outside_scope.py")
    else:
        plan["protected"].remove("plan.md")
    with pytest.raises(ValueError):
        revise_work(
            case[1], checkpoint=record["checkpoint_digest"], changes={"effects": plan}
        )


def test_draft_old_acceptance_copied_owner_and_no_manifest_cannot_grant_effects(
    work, tmp_path
):
    case = prepare(work, accept=False)
    with pytest.raises(ValueError, match="current accepted"):
        execute(case)
    supported = [work_effects.identity(c) for c in case[2]["request"]["controls"]]
    accepted = contracts.accept(work, supported_controls=supported)
    with pytest.raises(ValueError, match="current accepted"):
        apply_work_effects(case[1], case[2]["checkpoint_digest"], case[3])
    import shutil

    copied = tmp_path / "copied"
    shutil.copytree(case[1], copied)
    with pytest.raises(ValueError, match="another owner"):
        read_task(copied)
    revised = revise_work(
        case[1], checkpoint=accepted["checkpoint_digest"], changes={"effects": None}
    )
    contracts.accept(work, revised, supported_controls=supported)
    with pytest.raises(ValueError, match="No accepted effect manifest"):
        execute(case)


def test_pause_reuses_completed_check_and_requires_same_proposal(work):
    case = prepare(work)
    paused = execute(case, max_operations=1)
    assert paused["build"]["status"] == "paused"
    assert not (case[0] / "pkg").exists()
    changed = copy.deepcopy(case[3])
    changed["files"][1]["text"] = "different"
    with pytest.raises(ValueError, match="cannot change during recovery"):
        apply_work_effects(case[1], paused["checkpoint_digest"], changed)
    with pytest.raises(ValueError, match="Retain the effect journal"):
        revise_work(
            case[1], checkpoint=paused["checkpoint_digest"], changes={"effects": None}
        )
    assert execute(case)["build"]["status"] == "completed"


@pytest.mark.parametrize("kind", ["directory", "creation", "replacement"])
def test_lost_ack_requires_explicit_reconciliation_and_never_repeats_write(
    work, monkeypatch, kind
):
    case = prepare(work)
    original = RunStore.save

    def lose_ack(store, record):
        events = record.get("build", {}).get("events", [])
        if (
            events
            and events[-1].get("item", {}).get("kind") == kind
            and events[-1]["state"] == "completed"
        ):
            raise PersistenceError("synthetic lost acknowledgment")
        return original(store, record)

    with monkeypatch.context() as m:
        m.setattr(RunStore, "save", lose_ack)
        with pytest.raises(PersistenceError):
            execute(case)
    event = read_task(case[1])["build"]["events"][-1]
    assert event["phase"] == "dispatching"
    path = case[0] / event["item"]["path"]
    inode = path.stat().st_ino
    with pytest.raises(UnresolvedOperation, match="explicit reconciliation"):
        execute(case)
    reconciled = reconcile(case)
    assert reconciled["build"]["events"][-1]["reconciliations"]
    assert execute(case)["build"]["status"] == "completed"
    assert path.stat().st_ino == inode


@pytest.mark.parametrize("stage", ["before", "after", "partial"])
def test_real_process_death_retains_uncertainty(work, stage):
    case = prepare(work)
    code = """import os,json,sys
from pathlib import Path
from attune_harness import work_effects
from attune_harness.task_contract import read_task
from attune_harness.work_runtime import apply_work_effects
directory=Path(sys.argv[1]);proposal=json.loads(sys.argv[2]);stage=sys.argv[3]
original=work_effects.write_effect
def die(plan,item):
    if item['kind']=='creation':
        if stage=='after': original(plan,item)
        elif stage=='partial': (Path(plan['root'])/item['path']).write_text('partial')
        os._exit(23)
    return original(plan,item)
work_effects.write_effect=die
r=read_task(directory)
apply_work_effects(directory,r['checkpoint_digest'],proposal)
"""
    proc = subprocess.run(
        [sys.executable, "-B", "-c", code, str(case[1]), json.dumps(case[3]), stage],
        env={**os.environ, "PYTHONPATH": str(Path(work_effects.__file__).parents[1])},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 23, proc.stderr
    assert read_task(case[1])["build"]["events"][-1]["phase"] == "dispatching"
    with pytest.raises(UnresolvedOperation):
        execute(case)
    if stage == "partial":
        with pytest.raises(UnresolvedOperation):
            reconcile(case, retry_before=True)
        assert (case[0] / "pkg/sub/new.py").read_text() == "partial"
    else:
        if stage == "before":
            with pytest.raises(UnresolvedOperation):
                reconcile(case)
        reconcile(case, retry_before=stage == "before")
        assert execute(case)["build"]["status"] == "completed"


def test_fsync_failure_does_not_turn_visible_bytes_into_success(work, monkeypatch):
    case = prepare(work)
    original = work_effects.write_effect

    def fail_sync(plan, item):
        if item["kind"] != "creation":
            return original(plan, item)
        with monkeypatch.context() as m:

            def fail(fd):
                raise OSError("synthetic fsync failure")

            m.setattr(os, "fsync", fail)
            return original(plan, item)

    with monkeypatch.context() as m:
        m.setattr(work_effects, "write_effect", fail_sync)
        with pytest.raises(OSError, match="fsync failure"):
            execute(case)
    assert read_task(case[1])["build"]["status"] == "unresolved"
    reconcile(case)
    assert execute(case)["build"]["status"] == "completed"


def test_completed_result_is_stale_after_later_source_change(work):
    case = prepare(work)
    execute(case)
    (case[0] / "source.py").write_text("later change")
    with pytest.raises(UnresolvedOperation):
        execute(case)


def test_unsupported_platform_refuses_handles_before_effects(work, monkeypatch):
    case = prepare(work)
    # Remove the required primitive rather than changing global os.name/Path behavior.
    monkeypatch.delattr(os, "O_NOFOLLOW")
    with pytest.raises(FeatureUnavailable, match="POSIX"):
        execute(case)


def test_operation_budget_cannot_expand_with_file_parent_count(work):
    case = prepare(work, accept=False)
    r = revise_work(
        case[1],
        checkpoint=case[2]["checkpoint_digest"],
        changes={
            "budgets": {**contracts.BUDGET, "max_operations": 3},
            "assignments": [
                {
                    **case[2]["request"]["assignments"][0],
                    "budgets": {**contracts.BUDGET, "max_operations": 3},
                }
            ],
        },
    )
    contracts.accept(
        work, r, supported_controls=[work_effects.identity(r["request"]["controls"][0])]
    )
    with pytest.raises(ValueError, match="operation budget"):
        execute(case)
    assert not (case[0] / "pkg").exists()


def test_empty_creation_and_short_writes_are_complete(work, monkeypatch):
    case = prepare(work)
    case[3]["files"][1]["text"] = ""
    assert execute(case)["build"]["status"] == "completed"
    assert (case[0] / "pkg/sub/new.py").read_bytes() == b""


def test_partial_os_writes_are_drained(work, monkeypatch):
    case = prepare(work)
    original = os.write
    monkeypatch.setattr(os, "write", lambda fd, data: original(fd, data[:2]))
    assert execute(case)["build"]["status"] == "completed"
    assert (case[0] / "pkg/sub/new.py").read_text() == "answer = 42\n"


def test_no_progress_write_retains_partial_file(work, monkeypatch):
    case = prepare(work)
    monkeypatch.setattr(os, "write", lambda fd, data: 0)
    with pytest.raises(OSError, match="no write progress"):
        execute(case)
    with pytest.raises(UnresolvedOperation):
        reconcile(case, retry_before=True)
    assert (case[0] / "pkg/sub/new.py").read_bytes() == b""


def test_before_state_retry_has_explicit_two_attempt_ceiling(work, monkeypatch):
    case = prepare(work)

    def stop(plan, item):
        raise OSError("before the effect")

    with monkeypatch.context() as m:
        m.setattr(work_effects, "write_effect", stop)
        with pytest.raises(OSError):
            execute(case)
        with pytest.raises(UnresolvedOperation):
            reconcile(case)
        reconciled = reconcile(case, retry_before=True)
        assert reconciled["build"]["events"][-1]["attempts"] == 2
        with pytest.raises(OSError):
            execute(case)
        with pytest.raises(UnresolvedOperation):
            reconcile(case, retry_before=True)
    assert not (case[0] / "pkg").exists()


def test_store_failure_before_dispatch_prevents_effect(work, monkeypatch):
    case = prepare(work)
    original = RunStore.save

    def fail(store, record):
        events = record.get("build", {}).get("events", [])
        if (
            events
            and events[-1]["kind"] == "file_effect"
            and events[-1]["phase"] == "dispatching"
        ):
            raise PersistenceError("dispatch not persisted")
        return original(store, record)

    with monkeypatch.context() as m:
        m.setattr(RunStore, "save", fail)
        with pytest.raises(PersistenceError):
            execute(case)
    assert not (case[0] / "pkg").exists()
    assert read_task(case[1])["build"]["events"][-1]["phase"] == "prepared"
    assert execute(case)["build"]["status"] == "completed"


def test_configuration_changed_by_control_blocks_first_file_effect(work):
    config = work[1]
    case = prepare(
        work,
        script=f"from pathlib import Path;Path({str(config)!r}).write_text('changed')",
    )
    with pytest.raises(ValueError):
        execute(case)
    assert not (case[0] / "pkg").exists()


def test_changed_executable_cannot_reuse_a_completed_control(work, monkeypatch):
    case = prepare(work)
    execute(case, max_operations=1)
    original = work_effects.repair.sha
    expected = case[2]["request"]["effects"]["checks"][0]["executable_sha256"]
    # Change only the observation of the interpreter bytes; never alter Python itself.
    monkeypatch.setattr(
        repair,
        "sha",
        lambda raw: "0" * 64 if original(raw) == expected else original(raw),
    )
    with pytest.raises(ValueError, match="Accepted control executable changed"):
        execute(case)
    assert not (case[0] / "pkg").exists()


def test_post_write_corruption_cannot_receive_success(work, monkeypatch):
    case = prepare(work)
    original = work_effects.write_effect

    def corrupt(plan, item):
        result = original(plan, item)
        if item["kind"] == "creation":
            (case[0] / item["path"]).write_text("corrupt")
        return result

    monkeypatch.setattr(work_effects, "write_effect", corrupt)
    with pytest.raises(UnresolvedOperation):
        execute(case)
    assert read_task(case[1])["build"]["status"] == "unresolved"


@pytest.mark.parametrize(
    "bad",
    [
        "request",
        "order",
        "result",
        "control_result",
        "control_pass",
        "incomplete",
        "uncertain",
    ],
)
def test_altered_journal_is_rejected_even_with_recomputed_checkpoint(work, bad):
    case = prepare(work)
    r = execute(case)
    run = r["build"]
    if bad == "request":
        run["request_digest"] = "0" * 64
    elif bad == "order":
        run["events"][1:3] = run["events"][1:3][::-1]
    elif bad == "result":
        run["events"][-1]["result"]["entry"]["sha256"] = "0" * 64
    elif bad == "control_result":
        run["events"][0]["result"]["artifact_digest"] = "0" * 64
    elif bad == "control_pass":
        run["events"][0]["result"].update(
            returncode=1, failure="nonzero_exit", passed=False
        )
    elif bad == "incomplete":
        run["events"].pop()
    else:
        run["events"][1].update(phase="dispatching", state="pending")
    store = RunStore(case[1], existing=True)
    with store.lease():
        store.save(r)
    with pytest.raises(ValueError):
        read_task(case[1])


def test_reconciliation_refuses_non_file_control_and_wrong_checkpoint(work):
    case = prepare(work)
    r = execute(case, max_operations=1)
    with pytest.raises(ValueError, match="current accepted"):
        reconcile_work_effect(case[1], case[2]["checkpoint_digest"], "unknown")
    with pytest.raises(ValueError, match="Only an unresolved file"):
        reconcile(case)
    with pytest.raises(ValueError, match="Retry policy"):
        reconcile_work_effect(
            case[1], r["checkpoint_digest"], "unknown", retry_before="yes"
        )


def test_new_file_only_proposal_does_not_modify_existing_sources(work):
    case = prepare(work)
    case[3]["files"] = case[3]["files"][1:]
    assert execute(case)["build"]["status"] == "completed"
    assert (case[0] / "source.py").read_text().endswith("return 1\n")


def test_root_identity_change_is_not_accepted_as_same_checkout(work):
    case = prepare(work)
    import shutil

    moved = case[0].with_name("moved")
    case[0].rename(moved)
    shutil.copytree(moved, case[0])
    with pytest.raises(ValueError, match="Checkout identity changed"):
        execute(case)
    assert not (case[0] / "pkg").exists()


@pytest.mark.parametrize(
    "bad",
    [
        "state_inside",
        "not_git",
        "scope_metadata",
        "bad_probe",
        "unknown_control",
        "changed_evidence",
    ],
)
def test_freeze_and_work_linkage_reject_unsafe_host_configuration(work, bad):
    case = prepare(work, accept=False)
    plan = copy.deepcopy(case[2]["request"]["effects"])
    if bad in ("state_inside", "not_git", "scope_metadata", "bad_probe"):
        state = case[0] / "state" if bad == "state_inside" else case[1]
        if bad == "not_git":
            import shutil

            shutil.rmtree(case[0] / ".git")
        allowed = [".git/config"] if bad == "scope_metadata" else plan["allowed"]
        checks = [{k: c[k] for k in ("control", "probe")} for c in plan["checks"]]
        if bad == "bad_probe":
            checks[0]["probe"]["environment"]["PYTHONPATH"] = "."
        with pytest.raises(ValueError):
            work_effects.freeze(
                case[0], allowed, plan["parents"], plan["protected"], checks, state
            )
    else:
        if bad == "unknown_control":
            plan["checks"][0]["control"]["owner"] = "different-host"
        else:
            plan["before"]["source.py"]["sha256"] = "0" * 64
        with pytest.raises(ValueError):
            revise_work(
                case[1],
                checkpoint=case[2]["checkpoint_digest"],
                changes={"effects": plan},
            )
