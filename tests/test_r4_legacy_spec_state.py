"""R4, reading another project's spec state, through the real command line.

Spec authority Task 5 (plan task 3.2; D4, D20.3). ``plan --import-plan``
with ``--allow-outside-project`` accepts a plan file outside the project when
it is named explicitly, reads it once through ``spec_state`` (schema versions
1 and 2; anything else refused with the next action) and ``spec_legacy``,
converts it exactly as the implicit import does, and appends one receipt line
to ``import-receipts.jsonl`` beside the record, its room checked before the
record is saved. A plan the flag names that resolves inside the project is
refused, so whether a task's conversions leave receipts follows the record,
the bound plan outside the project, and never a file on disk. The originals
are only read; the tests prove it by digest, by modification time and by the
modes the readers open them with.

The fixtures under ``tests/fixtures/plans`` are one plan from attune-ai's own
``.claude/plans`` and the seven Harness plans of the Task 2 differential, each
copied from a named commit with its origin in a sidecar. Two of the Harness
plans name their outputs as absolute paths into a second checkout, which the
work store's intent rule can never scope, on either path; both readers read
them, and the conversion is refused in the store's own words, the same words
the implicit import refuses them with. Every test that edits a plan works on a
copy. The tests on the receipts file's obstacles, the landed-but-unreceipted
revision, the deleted and the planted receipts file and the ignored state
comment come from the different-model review of #115.
"""

# qualify: platform

import builtins
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from attune_harness import work_accept
from attune_harness.cli import main
from attune_harness.review_contract import digest
from attune_harness.spec_legacy import legacy_plan, read_plan
from attune_harness.spec_state import load_state, read_state
from attune_harness.task_contract import read_task
from attune_harness.work_accept import RECEIPT_LIMIT, RECEIPTS, import_plan
from test_work_cli_plan_import import PLAN, edit_before_the_state_comment
from test_work_contract import work  # noqa: F401  (fixture)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "plans"
PLANS = sorted(FIXTURES.glob("*/*.md"))
IDS = [f"{p.parent.name}/{p.stem}" for p in PLANS]
EXTERNAL = FIXTURES / "attune-ai" / "chart-widget-kernel.md"
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
PROBE_SCOPE = ["alpha.py", "source.py"]


def origin(plan):
    return json.loads(plan.with_name(plan.stem + ".origin.json").read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outputs_by_task(plan):
    """Each task's outputs as the store should hold them: files to create, then to modify."""
    return [
        [f["path"] for key in ("files_to_create", "files_to_modify") for f in task[key]]
        for task in legacy_plan(plan)["tasks"]
    ]


def outputs(plan):
    return {path for paths in outputs_by_task(plan) for path in paths}


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


def reimported(directory, capsys):
    checkpoint = read_task(directory)["checkpoint_digest"]
    return run(["plan", "--task-dir", directory, "--reimport", "--checkpoint", checkpoint], capsys)


def written_plan(tmp_path, state, name="plan.md"):
    """The two-task probe plan of the import tests, with its state comment replaced."""
    target = tmp_path / "elsewhere" / name
    target.parent.mkdir(exist_ok=True)
    target.write_text(PLAN.replace(STATE_PLACEHOLDER, state), encoding="utf-8")
    return target


def inside_plan(work, name="probe.md"):
    """The probe plan written inside the project, where the implicit import takes it."""
    root, _, _ = work
    target = root / "plans" / name
    target.parent.mkdir(exist_ok=True)
    target.write_text(PLAN, encoding="utf-8")
    return target


def external_copy(tmp_path):
    """A copy of the attune-ai fixture outside the project, for the tests that edit it."""
    target = tmp_path / "elsewhere" / EXTERNAL.name
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(EXTERNAL, target)
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
    before = datetime.now(timezone.utc)
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, Path(plan.name), "--allow-outside-project"
    )
    after = datetime.now(timezone.utc)
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
    # Every task's outputs are its files to create and its files to modify, in that order.
    expected = outputs_by_task(plan)
    assert [t["outputs"] for t in record["request"]["tasks"]] == expected
    unsupported = record["request"]["legacy"]["unsupported"]
    assert envelope["import_disclosures"] == unsupported

    [receipt] = receipts(directory)
    assert receipt["receipt"] == "legacy-plan-conversion" and receipt["schema_version"] == 1
    assert receipt["conversion"] == "import"
    # The receipt against the file; the origin test ties the file to its sidecar.
    assert receipt["source"]["sha256"] == sha256(plan)
    assert receipt["source"]["content_sha256"] == record["request"]["legacy"]["content_sha256"]
    assert receipt["source"]["given"] == plan.name
    assert (
        receipt["source"]["resolved"] == str(plan.resolve()) == record["request"]["legacy"]["path"]
    )
    assert receipt["source"]["bytes"] == plan.stat().st_size
    assert set(receipt["source"]) == {"given", "resolved", "sha256", "content_sha256", "bytes"}
    assert receipt["state_comment"] == {
        "present": True,
        "schema_version": recorded["schema_version"],
        "ignored": None,
    }
    assert receipt["spec_state"]["schema_version"] == recorded["schema_version"]
    assert receipt["spec_state"]["completed"] == load_state(str(plan)).completed
    assert [m["id"] for m in receipt["mapped"]] == recorded["tasks"]
    assert [m["outputs"] for m in receipt["mapped"]] == [len(paths) for paths in expected]
    assert all(m["checks"] >= 1 and m["objective"] for m in receipt["mapped"])
    disclosures = receipt["unmapped"]["disclosures"]
    assert disclosures["count"] == len(unsupported) == sum(disclosures["kinds"].values())
    assert disclosures["sha256"] == digest(unsupported)
    assert receipt["approval_imported"] is False
    assert receipt["task"] == {
        "task_id": record["request"]["task_id"],
        "revision": 1,
        "record_path": record["record_path"],
        "checkpoint_digest": record["checkpoint_digest"],
    }
    assert before <= datetime.fromisoformat(receipt["time"]) <= after


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


def test_the_receipt_counts_the_disclosures_by_kind_and_digests_them(work, tmp_path, capsys):
    """The record keeps the disclosures in full; the receipt keeps their count, kinds and digest."""
    plan = tmp_path / "elsewhere" / "plan.md"
    plan.parent.mkdir()
    plan.write_text(
        "# Prose before the task\n\n"
        '<task id="1" name="t" priority="high"><objective>x</objective>'
        '<files-to-create><file path="alpha.py">m</file></files-to-create>'
        "<validation><check>c</check></validation><notes>keep</notes>"
        '<risks><risk severity="low"><b>nested</b></risk></risks></task>\n',
        encoding="utf-8",
    )
    directory, (code, _) = imported(
        work, tmp_path, capsys, plan, "--allow-outside-project", scope=PROBE_SCOPE
    )
    assert code == 0
    unsupported = read_task(directory)["request"]["legacy"]["unsupported"]
    assert len(unsupported) == 4
    [receipt] = receipts(directory)
    assert receipt["unmapped"]["disclosures"] == {
        "count": 4,
        "kinds": {"surrounding": 1, "nested": 1, "attributes": 1, "elements": 1},
        "sha256": digest(unsupported),
    }
    assert receipt["unmapped"]["fields"] == {"1": ["name", "risks", "file descriptions"]}


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


def test_the_given_path_is_recorded_as_typed_and_normalised(work, tmp_path, capsys, monkeypatch):
    """The command line's Path normalises what was typed; the receipt records that spelling."""
    plan = external_copy(tmp_path)
    monkeypatch.chdir(tmp_path)
    typed = "./elsewhere//" + plan.name
    directory, (code, _) = imported(
        work, tmp_path, capsys, typed, "--allow-outside-project", scope=outputs(plan)
    )
    assert code == 0
    [receipt] = receipts(directory)
    assert receipt["source"]["given"] == str(Path(typed))
    assert receipt["source"]["resolved"] == str(plan.resolve())


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
        work, tmp_path, capsys, plan, "--allow-outside-project", scope=PROBE_SCOPE
    )
    assert code == 2 and envelope["status"] == "failed"
    detail = envelope["error"]["detail"]
    assert detail.startswith("Unsupported Spec state comment in ")
    assert all(phrase in detail for phrase in expected), detail
    assert not directory.exists()


def test_the_implicit_import_keeps_its_own_refusal_for_an_unknown_version(work, tmp_path, capsys):
    """Inside the project, without the flag, the reader's contract text is unchanged (D20.1)."""
    inside = inside_plan(work)
    inside.write_text(
        PLAN.replace(STATE_PLACEHOLDER, '{"schema_version": 3, "completed": []}'), encoding="utf-8"
    )
    directory, (code, envelope) = imported(work, tmp_path, capsys, inside, scope=PROBE_SCOPE)
    assert code == 2
    assert envelope["error"]["detail"] == "Unsupported Spec state comment"
    assert not directory.exists()


def test_the_implicit_refusals_for_outside_and_symlinked_plans_are_unchanged(
    work, tmp_path, capsys
):
    root, _, _ = work
    outside = written_plan(tmp_path, STATE_PLACEHOLDER)
    directory, (code, envelope) = imported(work, tmp_path, capsys, outside, scope=PROBE_SCOPE)
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
        work, tmp_path, capsys, link, scope=PROBE_SCOPE, name="linked"
    )
    assert code == 2
    assert envelope["error"]["detail"] == "Legacy plan must be a regular file inside the project"
    assert not directory.exists()


def test_the_flag_on_a_plan_inside_the_project_is_refused(work, tmp_path, capsys):
    """The flag names a plan outside the project; one inside it is the implicit import's."""
    inside = inside_plan(work)
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, inside, "--allow-outside-project", scope=PROBE_SCOPE
    )
    assert code == 2 and envelope["status"] == "failed"
    assert envelope["error"]["detail"] == (
        f"Legacy plan resolves inside the project: {inside.resolve()}. "
        "Import that path without --allow-outside-project."
    )
    assert not directory.exists()
    # A symlink outside the project to a plan inside it resolves inside it too;
    # the refusal names the target, the path the implicit import takes.
    link = tmp_path / "link.md"
    try:
        link.symlink_to(inside)
    except (OSError, NotImplementedError) as exc:  # no symlink privilege here
        pytest.skip(f"symlinks unavailable: {exc}")
    directory, (code, envelope) = imported(
        work, tmp_path, capsys, link, "--allow-outside-project", scope=PROBE_SCOPE, name="linked"
    )
    assert code == 2
    assert str(inside.resolve()) in envelope["error"]["detail"]
    assert not directory.exists()


def test_the_explicit_path_follows_a_symlink_and_records_both_paths(work, tmp_path, capsys):
    link = tmp_path / "link.md"
    try:
        link.symlink_to(EXTERNAL)
    except (OSError, NotImplementedError) as exc:  # no symlink privilege here
        pytest.skip(f"symlinks unavailable: {exc}")
    directory, (code, _) = imported(
        work, tmp_path, capsys, link, "--allow-outside-project", scope=outputs(EXTERNAL)
    )
    assert code == 0
    [receipt] = receipts(directory)
    assert receipt["source"]["given"] == str(link)
    assert receipt["source"]["resolved"] == str(EXTERNAL.resolve())
    assert read_task(directory)["request"]["legacy"]["path"] == str(EXTERNAL.resolve())


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


# --- the state comment, read, ignored or absent -----------------------------------


@pytest.mark.parametrize(
    "comment, expected",
    [
        (
            '{"schema_version": 2, "completed": "T1"}',
            {"present": True, "schema_version": 2, "ignored": "'completed' is not list[str]"},
        ),
        (
            '{"schema_version": 2, "completed": [], "current": 5}',
            {"present": True, "schema_version": 2, "ignored": "'current' is not str|None"},
        ),
        (None, {"present": False, "schema_version": None, "ignored": None}),
    ],
)
def test_a_comment_the_reader_ignores_and_a_plan_without_one_are_told_apart(
    work, tmp_path, capsys, comment, expected
):
    """``spec_state`` is null in both cases, as the carried reader has it; the receipt says which."""
    plan = tmp_path / "elsewhere" / "plan.md"
    plan.parent.mkdir()
    body = PLAN.split("<!-- spec-state:")[0]
    plan.write_text(
        body + (f"<!-- spec-state: {comment} -->\n" if comment is not None else ""),
        encoding="utf-8",
    )
    directory, (code, _) = imported(
        work, tmp_path, capsys, plan, "--allow-outside-project", scope=PROBE_SCOPE
    )
    assert code == 0
    [receipt] = receipts(directory)
    assert receipt["spec_state"] is None
    assert receipt["state_comment"] == expected


# --- the conversion, twice ---------------------------------------------------------


def test_a_second_conversion_appends_a_second_receipt(work, tmp_path, capsys):
    """A reimport of an outside-project plan is a second line; the first line is untouched."""
    plan = external_copy(tmp_path)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    first = (directory / RECEIPTS).read_text(encoding="utf-8")
    checkpoint = read_task(directory)["checkpoint_digest"]

    edit_before_the_state_comment(plan, "<!-- edited after import -->\n")
    edited = sha256(plan)
    code, envelope = reimported(directory, capsys)
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
    # The state was read again, on the edited bytes, through spec_state.
    state = load_state(str(plan))
    assert two["spec_state"] == {
        "schema_version": state.schema_version,
        "completed": state.completed,
        "current": state.current,
        "auto_run": state.auto_run,
        "last_updated": state.last_updated,
        "task_receipts": len(state.task_receipts),
    }
    assert two["state_comment"] == {"present": True, "schema_version": 1, "ignored": None}
    assert two["task"]["revision"] == record["request"]["revision"] == 2
    assert two["task"]["checkpoint_digest"] == record["checkpoint_digest"] != checkpoint
    assert sha256(plan) == edited  # the reimport only read it


def test_a_reimport_refuses_an_unknown_schema_version_in_spec_state_s_words(work, tmp_path, capsys):
    """The reimport reads the state through spec_state too: exit 2, nothing changed."""
    plan = external_copy(tmp_path)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    checkpoint = read_task(directory)["checkpoint_digest"]
    text = plan.read_text(encoding="utf-8")
    assert text.count('"schema_version": 1') == 1
    plan.write_text(text.replace('"schema_version": 1', '"schema_version": 3'), encoding="utf-8")
    code, envelope = reimported(directory, capsys)
    assert code == 2 and envelope["status"] == "failed"
    detail = envelope["error"]["detail"]
    assert detail.startswith("Unsupported Spec state comment in ")
    assert "newer than this Harness reads" in detail
    record = read_task(directory)
    assert record["request"]["revision"] == 1 and record["checkpoint_digest"] == checkpoint
    assert len(receipts(directory)) == 1


def test_a_reimport_recreates_a_deleted_receipts_file(work, tmp_path, capsys):
    """The record decides: a bound plan outside the project is receipted, file or no file."""
    plan = external_copy(tmp_path)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    os.remove(directory / RECEIPTS)
    edit_before_the_state_comment(plan, "<!-- edited after import -->\n")
    code, envelope = reimported(directory, capsys)
    assert code == 0, envelope
    [receipt] = receipts(directory)
    assert receipt["conversion"] == "reimport"
    assert receipt["task"]["revision"] == read_task(directory)["request"]["revision"] == 2


def test_a_planted_receipts_file_gives_an_implicit_reimport_no_receipt(work, tmp_path, capsys):
    """The record decides the other way too: a plan inside the project is never receipted."""
    inside = inside_plan(work)
    directory, (code, _) = imported(work, tmp_path, capsys, inside, scope=PROBE_SCOPE)
    assert code == 0
    (directory / RECEIPTS).write_bytes(b"")
    edit_before_the_state_comment(inside, "<!-- edited after import -->\n")
    code, envelope = reimported(directory, capsys)
    assert code == 0, envelope
    assert read_task(directory)["request"]["revision"] == 2
    assert (directory / RECEIPTS).read_bytes() == b""


def test_a_reimport_of_an_implicit_import_leaves_no_receipt(work, tmp_path, capsys):
    inside = inside_plan(work)
    directory, (code, _) = imported(work, tmp_path, capsys, inside, scope=PROBE_SCOPE)
    assert code == 0
    assert not (directory / RECEIPTS).exists()
    edit_before_the_state_comment(inside, "<!-- edited after import -->\n")
    code, _ = reimported(directory, capsys)
    assert code == 0
    assert not (directory / RECEIPTS).exists()


# --- the receipts file's obstacles ---------------------------------------------------


@pytest.mark.parametrize("obstacle", ["a directory", "a full file", "a symlink", "a hard link"])
def test_a_receipts_file_that_cannot_take_the_line_refuses_before_the_record_is_saved(
    work, tmp_path, capsys, obstacle
):
    plan = external_copy(tmp_path)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    target = directory / RECEIPTS
    first = target.read_bytes()
    checkpoint = read_task(directory)["checkpoint_digest"]
    kept = target
    if obstacle == "a directory":
        os.remove(target)
        target.mkdir()
        expected = "is not a regular file"
    elif obstacle == "a full file":
        # Room for less than one line: the first line, then a padding line to
        # sixteen bytes short of the bound.
        room = RECEIPT_LIMIT - 16 - len(first) - 12
        target.write_bytes(first + b'{"pad": "' + b"x" * room + b'"}\n')
        assert target.stat().st_size == RECEIPT_LIMIT - 16
        expected = "would pass"
    elif obstacle == "a symlink":
        kept = target.with_name("elsewhere.jsonl")
        target.rename(kept)
        try:
            target.symlink_to(kept)
        except (OSError, NotImplementedError) as exc:  # no symlink privilege here
            pytest.skip(f"symlinks unavailable: {exc}")
        expected = "is, or sits in, a symlink"
    else:
        try:
            os.link(target, target.with_name("other.jsonl"))
        except (OSError, NotImplementedError, AttributeError) as exc:
            pytest.skip(f"hard links unavailable: {exc}")
        expected = "has more than one link"
    edit_before_the_state_comment(plan, "<!-- edited after import -->\n")
    code, envelope = reimported(directory, capsys)
    assert code == 2 and envelope["status"] == "failed"
    detail = envelope["error"]["detail"]
    assert detail.startswith("Conversion receipt") and expected in detail, detail
    assert "Nothing was changed" in detail
    record = read_task(directory)
    assert record["request"]["revision"] == 1 and record["checkpoint_digest"] == checkpoint
    if obstacle == "a full file":
        assert target.stat().st_size == RECEIPT_LIMIT - 16
    elif obstacle != "a directory":
        assert kept.read_bytes() == first


def test_a_receipt_refused_after_the_save_names_the_landed_revision(
    work, tmp_path, capsys, monkeypatch
):
    """What the room check cannot foresee, a race or the lock, is reported with the revision."""
    plan = external_copy(tmp_path)
    directory, (code, _) = imported(work, tmp_path, capsys, plan, "--allow-outside-project")
    assert code == 0
    checkpoint = read_task(directory)["checkpoint_digest"]

    def refusing_writer(path, **kwargs):
        def write(event):
            raise OSError("the lock timed out")

        return write

    monkeypatch.setattr(work_accept, "jsonl_event_writer", refusing_writer)
    edit_before_the_state_comment(plan, "<!-- edited after import -->\n")
    code, envelope = reimported(directory, capsys)
    assert code == 2 and envelope["status"] == "failed"
    record = read_task(directory)
    assert record["request"]["revision"] == 2 and record["checkpoint_digest"] != checkpoint
    detail = envelope["error"]["detail"]
    assert detail.startswith(
        f"The conversion landed as revision 2 with checkpoint {record['checkpoint_digest']}, "
        "but its receipt was not written: the lock timed out."
    )
    assert "reimport with this checkpoint" in detail
    assert len(receipts(directory)) == 1


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
