"""R4, reading another project's spec state, through the real command line.

Spec authority Task 5 (plan task 3.2; D4, D20.3). ``plan --import-plan``
with ``--allow-outside-project`` accepts a plan file outside the project when
it is named explicitly, reads it once through ``spec_state`` (schema versions
1 and 2; anything else refused with the next action) and ``spec_legacy``,
converts it exactly as the implicit import does, and appends one receipt line
to ``import-receipts.jsonl`` beside the record. The originals are only read;
the tests prove it by digest, by modification time and by the modes the
readers open them with.

The fixtures under ``tests/fixtures/plans`` are one plan from attune-ai's own
``.claude/plans`` and the seven Harness plans of the Task 2 differential, each
copied from a named commit with its origin in a sidecar. Two of the Harness
plans name their outputs as absolute paths into a second checkout, which the
work store's intent rule can never scope, on either path; both readers read
them, and the conversion is refused in the store's own words, the same words
the implicit import refuses them with. Every test that edits a plan works on a
copy.
"""

# qualify: platform

import builtins
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.spec_legacy import legacy_plan, read_plan
from attune_harness.spec_state import load_state, read_state
from attune_harness.task_contract import read_task
from attune_harness.work_accept import RECEIPTS, import_plan
from test_work_cli_plan_import import PLAN, edit_before_the_state_comment
from test_work_contract import work  # noqa: F401  (fixture)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "plans"
PLANS = sorted(FIXTURES.glob("*/*.md"))
IDS = [f"{p.parent.name}/{p.stem}" for p in PLANS]
ORIGIN_KEYS = {
    "repository",
    "branch",
    "commit",
    "path",
    "copied",
    "sha256",
    "bytes",
    "schema_version",
    "tasks",
}
# The plans the store cannot take, and why: their outputs are absolute paths
# into another checkout, so no intent scope can cover them. The refusal is the
# intent validator's, in its own words, before anything is written.
UNSCOPED = {"release-readiness-follow-through", "shared-memory-adoption"}
UNSCOPED_TEXT = "Expected a canonical relative file path outside metadata"
STATE_PLACEHOLDER = '{"schema_version": 2, "completed": []}'


def origin(plan):
    return json.loads(plan.with_name(plan.stem + ".origin.json").read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outputs(plan):
    return {
        f["path"]
        for task in legacy_plan(plan)["tasks"]
        for key in ("files_to_create", "files_to_modify")
        for f in task[key]
    }


def request_file(tmp_path, data, scope):
    intent = {**data["intent"], "scope": sorted(set(data["intent"]["scope"]) | set(scope))}
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps({"intent": intent, "assignments": data["assignments"]}), encoding="utf-8"
    )
    return path


def run(argv, capsys):
    code = main([str(a) for a in argv])
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip() else None


def receipts(directory):
    lines = (directory / RECEIPTS).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def import_argv(work, request, directory, plan, *flags):
    root, config, _ = work
    return [
        "plan",
        "--task-dir",
        directory,
        "--project",
        root,
        "--config",
        config,
        "--request",
        request,
        "--import-plan",
        plan,
        *flags,
    ]


def imported(work, tmp_path, capsys, plan, *flags, scope=None, name="work"):
    """Import ``plan`` into ``tmp_path / name`` with the request's scope covering its outputs."""
    directory = tmp_path / name
    request = request_file(tmp_path, work[2], outputs(plan) if scope is None else scope)
    return directory, run(import_argv(work, request, directory, plan, *flags), capsys)


def written_plan(tmp_path, state, name="plan.md"):
    """The two-task probe plan of the import tests, with its state comment replaced."""
    target = tmp_path / "elsewhere" / name
    target.parent.mkdir(exist_ok=True)
    target.write_text(PLAN.replace(STATE_PLACEHOLDER, state), encoding="utf-8")
    return target


# --- the fixtures ---------------------------------------------------------------


@pytest.mark.parametrize("plan", PLANS, ids=IDS)
def test_every_fixture_is_byte_identical_to_its_origin(plan):
    recorded = origin(plan)
    assert ORIGIN_KEYS <= set(recorded)
    assert len(recorded["commit"]) == 40 and recorded["path"] == f".claude/plans/{plan.name}"
    # .gitattributes keeps the checkout free of line-ending rewrites; the
    # normalisation is the backstop for a clone made without it (Windows trap 6).
    raw = plan.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == recorded["sha256"]
    assert len(raw) == recorded["bytes"]


def test_the_fixture_set_is_the_ruled_one():
    """D20.3: one plan from attune-ai's own plans, the seven Harness plans as regression."""
    assert IDS == [
        "attune-ai/chart-widget-kernel",
        "harness/connected-journey-qualification",
        "harness/plan-build",
        "harness/release-readiness-follow-through",
        "harness/shared-memory-adoption",
        "harness/test-this-change",
        "harness/unified-task-execution",
        "harness/voyage-validation-reuse",
    ]
    assert origin(PLANS[0])["repository"].endswith("/attune-ai")
    assert all(origin(p)["branch"] == "wip/local-snapshot-2026-09-19" for p in PLANS[1:])


@pytest.mark.parametrize("plan", PLANS, ids=IDS)
def test_both_readers_read_every_fixture_and_the_text_reader_agrees_with_the_file_reader(plan):
    """R4's readability, and the one-read seam: the text half equals the file half."""
    recorded = origin(plan)
    raw = read_plan(plan)
    state = read_state(raw, str(plan))
    assert state == load_state(str(plan))
    assert state.schema_version == recorded["schema_version"]
    legacy = legacy_plan(plan, raw=raw)
    assert legacy == legacy_plan(plan)
    assert [t["task_id"] for t in legacy["tasks"]] == recorded["tasks"]
    assert legacy["source_sha256"] == hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --- the R4 receipts -----------------------------------------------------------


@pytest.mark.parametrize("plan", PLANS, ids=IDS)
def test_r4_receipt_for_every_fixture_plan(work, tmp_path, capsys, monkeypatch, plan):
    recorded = origin(plan)
    # Named as typed: a bare file name from the plan's own directory, which the
    # import resolves; the receipt records both spellings.
    monkeypatch.chdir(plan.parent)
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, Path(plan.name), "--allow-outside-project"
    )
    if plan.stem in UNSCOPED:
        assert code == 2 and envelope["status"] == "failed"
        assert envelope["error"]["detail"] == UNSCOPED_TEXT
        assert not directory.exists()  # no task, so no receipt
        return
    assert code == 0, envelope
    assert envelope["status"] == "draft"
    record = read_task(directory)
    assert record["status"] == "draft" and record["acceptance"] is None  # completed grants nothing
    assert [t["id"] for t in record["request"]["tasks"]] == recorded["tasks"]
    assert envelope["import_disclosures"] == record["request"]["legacy"]["unsupported"]

    [receipt] = receipts(directory)
    assert receipt["receipt"] == "legacy-plan-conversion" and receipt["schema_version"] == 1
    assert receipt["conversion"] == "import"
    assert receipt["source"]["sha256"] == sha256(plan) == recorded["sha256"]
    assert receipt["source"]["content_sha256"] == record["request"]["legacy"]["content_sha256"]
    assert receipt["source"]["given"] == plan.name
    assert (
        receipt["source"]["resolved"] == str(plan.resolve()) == record["request"]["legacy"]["path"]
    )
    assert receipt["source"]["bytes"] == plan.stat().st_size == recorded["bytes"]
    assert receipt["source"]["inside_project"] is False
    assert receipt["spec_state"]["schema_version"] == recorded["schema_version"]
    assert receipt["spec_state"]["completed"] == load_state(str(plan)).completed
    assert [m["id"] for m in receipt["mapped"]] == recorded["tasks"]
    assert len(receipt["mapped"]) == len(record["request"]["tasks"])
    assert all(m["checks"] >= 1 and m["objective"] for m in receipt["mapped"])
    assert receipt["unmapped"]["disclosures"] == record["request"]["legacy"]["unsupported"]
    assert receipt["approval_imported"] is False
    assert receipt["task"] == {
        "task_id": record["request"]["task_id"],
        "revision": 1,
        "record_path": record["record_path"],
        "checkpoint_digest": record["checkpoint_digest"],
    }
    assert receipt["time"].endswith("+00:00")


def test_the_receipt_names_what_the_store_has_no_place_for(work, tmp_path, capsys):
    """Names, risks and file descriptions stay in the record's legacy block; the receipt says so."""
    plan = FIXTURES / "harness" / "plan-build.md"
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    [receipt] = receipts(directory)
    assert receipt["unmapped"]["fields"] == {
        str(n): ["name", "risks", "file descriptions"] for n in range(1, 9)
    }
    legacy = read_task(directory)["request"]["legacy"]
    assert legacy["tasks"][0]["risks"] and legacy["tasks"][0]["name"] != "1"
    assert receipt["spec_state"] == {
        "schema_version": 2,
        "completed": ["1", "2", "3", "4", "5", "6", "7"],
        "current": "8",
        "auto_run": True,
        "last_updated": load_state(str(plan)).last_updated,
        "task_receipts": 7,
    }


@pytest.mark.parametrize("plan", PLANS, ids=IDS)
def test_the_original_is_only_read(work, tmp_path, capsys, monkeypatch, plan):
    before = (sha256(plan), plan.stat().st_mtime_ns, plan.stat().st_size)
    modes = []
    real_path_open, real_open = Path.open, builtins.open

    def same(file):
        try:
            return Path(os.fspath(file)).resolve() == plan.resolve()
        except (TypeError, OSError):
            return False  # a descriptor, or something that is not a path

    def path_open(self, mode="r", *args, **kwargs):
        if same(self):
            modes.append(mode)
        return real_path_open(self, mode, *args, **kwargs)

    def builtin_open(file, mode="r", *args, **kwargs):
        if same(file):
            modes.append(mode)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", path_open)
    monkeypatch.setattr(builtins, "open", builtin_open)
    directory, (code, envelope) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == (2 if plan.stem in UNSCOPED else 0), envelope
    assert modes and all(mode in ("r", "rb") for mode in modes), modes
    assert (sha256(plan), plan.stat().st_mtime_ns, plan.stat().st_size) == before


@pytest.mark.parametrize("plan", PLANS, ids=IDS)
def test_the_explicit_import_reads_the_plan_once(work, tmp_path, monkeypatch, plan):
    """One read serves both readers: the state and the tasks come from the same bytes."""
    root, config, data = work
    intent = {**data["intent"], "scope": sorted(set(data["intent"]["scope"]) | outputs(plan))}
    opened = []
    real_open = Path.open

    def path_open(self, mode="r", *args, **kwargs):
        if self.resolve() == plan.resolve():
            opened.append(mode)
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", path_open)
    try:
        import_plan(
            root,
            config,
            path=plan,
            directory=tmp_path / "work",
            intent=intent,
            assignments=data["assignments"],
            allow_outside_project=True,
        )
    except ValueError as exc:
        assert plan.stem in UNSCOPED and str(exc) == UNSCOPED_TEXT
    assert opened == ["rb"], opened


# --- the refusals ----------------------------------------------------------------


@pytest.mark.parametrize(
    "state, expected",
    [
        (
            '{"schema_version": 3, "completed": []}',
            ("newer than this Harness reads", "Update Harness"),
        ),
        ('{"completed": []}', ("schema_version none", "Remove the spec-state comment")),
        (
            '{"schema_version": "2", "completed": []}',
            ('schema_version "2"', "Remove the spec-state comment"),
        ),
    ],
)
def test_an_unknown_schema_version_is_refused_with_a_next_action_and_no_task(
    work, tmp_path, capsys, state, expected
):
    plan = written_plan(tmp_path, state)
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, plan, "--allow-outside-project", scope=["alpha.py", "source.py"]
    )
    assert code == 2 and envelope["status"] == "failed"
    detail = envelope["error"]["detail"]
    assert detail.startswith("Unsupported Spec state comment in ")
    assert all(phrase in detail for phrase in expected), detail
    assert not directory.exists()


def test_the_implicit_import_keeps_its_own_refusal_for_an_unknown_version(work, tmp_path, capsys):
    """Inside the project, without the flag, the reader's contract text is unchanged (D20.1)."""
    root, _, _ = work
    inside = root / "plans" / "probe.md"
    inside.parent.mkdir(exist_ok=True)
    inside.write_text(
        PLAN.replace(STATE_PLACEHOLDER, '{"schema_version": 3, "completed": []}'), encoding="utf-8"
    )
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, inside, scope=["alpha.py", "source.py"]
    )
    assert code == 2
    assert envelope["error"]["detail"] == "Unsupported Spec state comment"
    assert not directory.exists()


def test_the_implicit_refusals_for_outside_and_symlinked_plans_are_unchanged(
    work, tmp_path, capsys
):
    root, _, _ = work
    outside = written_plan(tmp_path, STATE_PLACEHOLDER)
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, outside, scope=["alpha.py", "source.py"]
    )
    assert code == 2
    assert envelope["error"]["detail"] == "Legacy plan must be a regular file inside the project"
    assert not directory.exists()

    link = root / "plans" / "link.md"
    link.parent.mkdir(exist_ok=True)
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:  # no symlink privilege here
        pytest.skip(f"symlinks unavailable: {exc}")
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, link, scope=["alpha.py", "source.py"], name="linked"
    )
    assert code == 2
    assert envelope["error"]["detail"] == "Legacy plan must be a regular file inside the project"
    assert not directory.exists()


def test_the_explicit_path_follows_a_symlink_and_records_both_paths(work, tmp_path, capsys):
    target = FIXTURES / "attune-ai" / "chart-widget-kernel.md"
    link = tmp_path / "link.md"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:  # no symlink privilege here
        pytest.skip(f"symlinks unavailable: {exc}")
    directory, (code, _) = imported(
        work, tmp_path, capsys, link, "--allow-outside-project", scope=outputs(target)
    )
    assert code == 0
    [receipt] = receipts(directory)
    assert receipt["source"]["given"] == str(link)
    assert receipt["source"]["resolved"] == str(target.resolve())
    assert read_task(directory)["request"]["legacy"]["path"] == str(target.resolve())


def test_the_flag_without_import_plan_is_refused(work, tmp_path, capsys):
    root, config, data = work
    request = request_file(tmp_path, data, [])
    code, envelope = run(
        [
            "plan",
            "--task-dir",
            tmp_path / "work",
            "--project",
            root,
            "--config",
            config,
            "--request",
            request,
            "--allow-outside-project",
        ],
        capsys,
    )
    assert code == 2
    assert envelope["error"]["detail"] == "--allow-outside-project requires --import-plan"
    assert not (tmp_path / "work").exists()


# --- the conversion, twice ---------------------------------------------------------


def test_a_second_conversion_appends_a_second_receipt(work, tmp_path, capsys):
    """A reimport of a receipted task is a second line; the first line is untouched."""
    plan = tmp_path / "elsewhere" / "chart-widget-kernel.md"
    plan.parent.mkdir()
    shutil.copyfile(FIXTURES / "attune-ai" / "chart-widget-kernel.md", plan)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    first = (directory / RECEIPTS).read_text(encoding="utf-8")
    checkpoint = read_task(directory)["checkpoint_digest"]

    edit_before_the_state_comment(plan, "<!-- edited after import -->\n")
    edited = sha256(plan)
    code, envelope = run(
        ["plan", "--task-dir", directory, "--reimport", "--checkpoint", checkpoint], capsys
    )
    assert code == 0, envelope
    text = (directory / RECEIPTS).read_text(encoding="utf-8")
    assert text.startswith(first)  # appended, never overwritten
    one, two = receipts(directory)
    assert one["conversion"] == "import" and two["conversion"] == "reimport"
    record = read_task(directory)
    assert two["source"]["sha256"] == edited != one["source"]["sha256"]
    assert (
        two["source"]["given"] == two["source"]["resolved"] == record["request"]["legacy"]["path"]
    )
    assert two["task"]["revision"] == record["request"]["revision"] == 2
    assert two["task"]["checkpoint_digest"] == record["checkpoint_digest"] != checkpoint
    assert sha256(plan) == edited  # the reimport only read it


def test_a_reimport_of_an_implicit_import_leaves_no_receipt(work, tmp_path, capsys):
    """The receipt file marks a receipted task; the implicit import is as before."""
    root, _, _ = work
    inside = root / "plans" / "probe.md"
    inside.parent.mkdir(exist_ok=True)
    inside.write_text(PLAN, encoding="utf-8")
    directory, (code, _) = imported(work, tmp_path, capsys, inside, scope=["alpha.py", "source.py"])
    assert code == 0
    assert not (directory / RECEIPTS).exists()
    edit_before_the_state_comment(inside, "<!-- edited after import -->\n")
    checkpoint = read_task(directory)["checkpoint_digest"]
    code, _ = run(
        ["plan", "--task-dir", directory, "--reimport", "--checkpoint", checkpoint], capsys
    )
    assert code == 0
    assert not (directory / RECEIPTS).exists()


def test_a_receipt_the_writer_refuses_is_reported_after_the_conversion_landed(
    work, tmp_path, capsys
):
    """The record is the authority and is saved first; a refused receipt is an error, never silent."""
    plan = tmp_path / "elsewhere" / "chart-widget-kernel.md"
    plan.parent.mkdir()
    shutil.copyfile(FIXTURES / "attune-ai" / "chart-widget-kernel.md", plan)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    checkpoint = read_task(directory)["checkpoint_digest"]
    os.remove(directory / RECEIPTS)
    (directory / RECEIPTS).mkdir()  # the writer's open fails on every platform
    edit_before_the_state_comment(plan, "<!-- edited after import -->\n")
    code, envelope = run(
        ["plan", "--task-dir", directory, "--reimport", "--checkpoint", checkpoint], capsys
    )
    assert code == 2 and envelope["status"] == "failed"
    assert RECEIPTS in envelope["error"]["detail"]
    assert read_task(directory)["request"]["revision"] == 2


# --- the differential: explicit against implicit -----------------------------------


@pytest.mark.parametrize("plan", PLANS, ids=IDS)
def test_the_explicit_path_converts_exactly_as_the_implicit_one(work, tmp_path, capsys, plan):
    root, _, _ = work
    inside = root / "plans" / plan.name
    inside.parent.mkdir(exist_ok=True)
    shutil.copyfile(plan, inside)
    scope = outputs(plan)
    implicit, (code_a, envelope_a) = imported(
        work, tmp_path, capsys, inside, scope=scope, name="implicit"
    )
    explicit, (code_b, envelope_b) = imported(
        work, tmp_path, capsys, plan, "--allow-outside-project", scope=scope, name="explicit"
    )
    assert code_a == code_b
    if plan.stem in UNSCOPED:
        assert envelope_a["error"]["detail"] == envelope_b["error"]["detail"] == UNSCOPED_TEXT
        assert not implicit.exists() and not explicit.exists()
        return
    assert code_a == 0
    a, b = read_task(implicit)["request"], read_task(explicit)["request"]
    assert a["tasks"] == b["tasks"]
    assert {k: v for k, v in a["legacy"].items() if k != "path"} == {
        k: v for k, v in b["legacy"].items() if k != "path"
    }
    assert a["legacy"]["path"] == str(inside.resolve()) and b["legacy"]["path"] == str(
        plan.resolve()
    )
    assert envelope_a["import_disclosures"] == envelope_b["import_disclosures"]
    assert envelope_a["tasks"] == envelope_b["tasks"]
    assert sorted(envelope_a) == sorted(envelope_b)  # the envelope's keys do not change
    assert not (implicit / RECEIPTS).exists() and (explicit / RECEIPTS).is_file()
