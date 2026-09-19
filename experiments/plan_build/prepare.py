"""Plan/build pre-code probes in disposable roots; never dispatch a provider."""

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from attune_harness import repair, review_participants
from attune_harness.recovery import RecoveryCursor, UnresolvedOperation
from attune_harness.review_contract import canonical
from attune_harness.review_store import RunStore, PersistenceError, read_record
from attune_harness.task_contract import read_task

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def rejected(call):
    try:
        call()
    except (ValueError, OSError, UnresolvedOperation) as error:
        return {"error": type(error).__name__, "detail": str(error)}
    raise AssertionError("The expected unsupported operation was accepted")


def fixture(directory):
    root = directory / "checkout"
    (root / "src/attune_harness").mkdir(parents=True)
    for name in ("__init__.py", "documentation.py"):
        shutil.copy2(
            REPO / "src/attune_harness" / name, root / "src/attune_harness" / name
        )
    (root / "samples").mkdir()
    (root / "samples/api.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "samples/empty.py").write_text("# No public declarations.\n")
    (root / "tests").mkdir()
    (root / "tests/README.md").write_text(
        "Generated tests supplement the protected acceptance.py oracle.\n"
    )
    shutil.copy2(HERE / "fixtures/acceptance.py", root / "acceptance.py")
    captured = {}
    for module in ("samples/api.py", "samples/empty.py"):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "attune_harness.documentation", module],
            cwd=root,
            env={
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str(root / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            },
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        captured[module] = result.stdout
    oracle = root / "acceptance.py"
    template = oracle.read_text()
    marker = "CAPTURED_DEFAULT_OUTPUTS = {}"
    if template.count(marker) != 1:
        raise ValueError("Protected oracle needs one pre-change capture marker")
    oracle.write_text(
        template.replace(marker, f"CAPTURED_DEFAULT_OUTPUTS = {captured!r}")
    )
    (root / "pytest.ini").write_text("[pytest]\n")
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
    for command in (
        ["git", "init", "-q", str(root)],
        ["git", "-C", str(root), "add", "."],
        [
            "git",
            "-C",
            str(root),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Harness fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Captured documentation baseline",
        ],
    ):
        subprocess.run(command, check=True, capture_output=True)
    (root / "unrelated.txt").write_text("Unrelated dirty work must survive.\n")
    return root


def acceptance(root, output, baseline):
    command = [
        sys.executable,
        "-B",
        "acceptance.py",
        *(["--baseline"] if baseline else []),
    ]
    run = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output.write_text(run.stdout + run.stderr)
    return {
        "command": command,
        "cwd": str(root),
        "returncode": run.returncode,
        "output": str(output),
        "output_sha256": sha(output),
    }


def exclusive_create(path, content):
    """Scratch primitive: completed staging bytes, exclusive publication, fsync.

    This experiment has a trusted, existing parent. Production containment,
    parent creation and effect validation must be qualified in task 4.
    """
    fd, temporary = tempfile.mkstemp(prefix=".create-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"sha256": sha(path)}


def run(output):
    from attune.pipeline.spec_reader import read_spec

    started = time.monotonic()
    output.mkdir(parents=True)
    root = fixture(output)
    baseline = acceptance(root, output / "baseline.log", True)
    feature = acceptance(root, output / "feature-before.log", False)
    assert baseline["returncode"] == 0 and feature["returncode"] == 1

    store = RunStore(output / "envelope")
    record = {
        "schema_version": 1,
        "operation": "task",
        "task_profile": "feature-work-v1",
        "status": "draft",
        "request": {},
        "events": [],
        "history": [],
        "acceptance": None,
        "bindings": {},
        "recovery": {},
        "record_path": str(store.path),
    }
    with store.lease():
        store.save(record)
    assert read_record(store.directory) == record
    envelope = rejected(lambda: read_task(store.directory))
    # Task 1 retained the original unsupported-profile receipt. Once the profile
    # is implemented, this deliberately incomplete record must still fail closed.
    assert envelope["error"] == "ValueError"

    probe = {
        "argv": [sys.executable, "-B", "acceptance.py"],
        "cwd": ".",
        "timeout": 30,
        "max_output_bytes": 32768,
        "oracle_paths": ["acceptance.py", "samples/api.py", "samples/empty.py"],
        "environment": {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
    }
    creation = rejected(
        lambda: repair.freeze(
            root,
            ["src/attune_harness/documentation_export.py"],
            probe,
            output / "future-state",
        )
    )
    assert "existing regular files" in creation["detail"]

    roles = {}
    for role in ("planner", "critic", "worker", "reviewer"):
        calls = []

        class NoNative:
            def __init__(self, *args, **kwargs):
                self.identity = None
                self.last_process = None

        class CaptureParticipant:
            def __init__(self, attempt, exchange):
                calls.append(asdict(attempt))

            def run(self, task):
                raise ValueError("Stopped at native transport boundary; no inference")

        request = {
            "request_digest": "0" * 64,
            "turn": {
                "task_id": "feature",
                "turn_id": "one",
                "requirement_revision": "1",
                "participant_id": "fixture",
                "role": role,
            },
        }
        with (
            patch.object(review_participants, "NativeExchange", NoNative),
            patch.object(review_participants, "JsonParticipant", CaptureParticipant),
        ):
            error = rejected(
                lambda: review_participants.ReviewExchange(
                    {
                        "adapter": "codex",
                        "model": "fixture-not-dispatched",
                        "timeout": 1,
                    },
                    output,
                )(canonical(request))
            )
        roles[role] = {"error": error, "attempt": calls}

    plan = output / "import.md"
    plan.write_text(
        '<tasks><task id="1" name="export"><objective>Add export</objective>'
        '<files-to-create><file path="src/new.py">New module</file></files-to-create>'
        "<validation><check>Behavioral test rejects filtered unknowns</check></validation></task>"
        '<task id="2" name="connect"><objective>Connect CLI</objective>'
        "<dependencies><dep>1</dep></dependencies></task></tasks>\n"
    )
    parsed = [item.to_dict() for item in read_spec(str(plan))]
    assert len(parsed) == 2 and parsed[1]["dependencies"] == ["1"]
    assert parsed[0]["files_to_create"][0]["path"] == "src/new.py"
    plan.write_text(
        plan.read_text().replace(
            "</task>", "<unsupported>silently lost</unsupported></task>", 1
        )
    )
    unsupported_ignored = [item.to_dict() for item in read_spec(str(plan))] == parsed
    plan.write_text("not an executable XML plan")
    empty_returned = read_spec(str(plan)) == []

    effects = RunStore(output / "effects")
    state = {"schema_version": 1, "events": [], "recovery": {}}
    effects.save(state)
    target = output / "new-file.txt"
    save = effects.save

    def lose_ack(value):
        if value["events"] and value["events"][0]["state"] == "completed":
            raise PersistenceError("Injected lost completion acknowledgment")
        save(value)

    with patch.object(effects, "save", lose_ack):
        failure = rejected(
            lambda: RecoveryCursor(state, effects).perform(
                "create:new-file",
                "file_creation",
                lambda: exclusive_create(target, b"complete artifact\n"),
                effect_class="file_creation",
                path=str(target),
            )
        )
    durable = read_record(effects.directory)
    assert durable["events"][0]["phase"] == "dispatching"
    assert target.read_bytes() == b"complete artifact\n"
    duplicate = rejected(
        lambda: RecoveryCursor(durable, effects).perform(
            "create:new-file",
            "file_creation",
            lambda: exclusive_create(target, b"complete artifact\n"),
            effect_class="file_creation",
            path=str(target),
        )
    )
    collision = rejected(lambda: exclusive_create(target, b"overwrite"))
    assert target.read_bytes() == b"complete artifact\n"
    # Scratch reconciliation of our observed write, within the trusted-parent
    # boundary. It exercises cursor reuse, not a production creation validator.
    observed = {"sha256": sha(target)}
    durable["events"][0].update(state="completed", phase="completed", result=observed)
    save(durable)

    def must_not_repeat():
        raise AssertionError("Reconciled creation was executed twice")

    assert (
        RecoveryCursor(durable, effects).perform(
            "create:new-file",
            "file_creation",
            must_not_repeat,
            effect_class="file_creation",
            path=str(target),
        )
        == observed
    )
    result = {
        "status": "pre-code-baseline-captured; production plan/build absent",
        "native_calls": 0,
        "baseline": baseline,
        "feature_before": feature,
        "envelope": envelope,
        "existing_repair_creation": creation,
        "roles": roles,
        "legacy_import": {
            "supported_fields": parsed,
            "unknown_information_silently_ignored": unsupported_ignored,
            "non_task_document_returns_empty": empty_returned,
        },
        "scratch_creation": {
            "lost_ack": failure,
            "blind_resume_rejected": duplicate,
            "collision_rejected": collision,
            "complete_bytes_preserved": True,
            "observed_result_reused_without_second_write": True,
            "limits": "Trusted existing parent, scratch primitive only; no production containment or directory-creation claim.",
        },
        "elapsed_seconds": time.monotonic() - started,
        "source_sha256": {
            name: sha(REPO / name)
            for name in (
                "src/attune_harness/documentation.py",
                "src/attune_harness/task_contract.py",
                "src/attune_harness/repair.py",
                "src/attune_harness/review_participants.py",
                "src/attune_harness/recovery.py",
                "src/attune_harness/spec_handoff.py",
            )
        },
    }
    write(output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output.resolve()), indent=2))
