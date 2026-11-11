"""Check the delivered course, download and no-dispatch practice preparation."""

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from importlib.metadata import PackageNotFoundError
from urllib.parse import unquote, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"
COURSE = TRAINING / "reporting"
ARCHIVE = TRAINING / "1.7.0-preparation"


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if values.get("id"):
            assert values["id"] not in self.ids, values["id"]
            self.ids.add(values["id"])
        self.links += [values[key] for key in ("href", "src", "poster") if values.get(key)]


def test_course_projection_and_static_reading_routes():
    spec = importlib.util.spec_from_file_location("course_projection", TRAINING / "build_course.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    for path, expected in builder.project().items():
        assert path.read_text(encoding="utf-8") == expected, path
    storage = set()
    overview = (COURSE / "index.html").read_text()
    assert 'href="development-paths.html#goal-driven"' in overview
    assert 'href="development-paths.html#spec-driven"' in overview
    setup = (COURSE / "setup.html").read_text(encoding="utf-8")
    continue_link = '<a href="./">Continue to the reporting course</a>'
    assert setup.count('href="./"') == 1
    assert setup.index('assets/reporting-practice.zip') < setup.index('. .venv/bin/activate') < setup.index(continue_link)
    assert 'href="01-define/"' not in setup and 'href="02-build/"' not in setup
    for slug in builder.SLUGS:
        lesson = json.loads((COURSE / slug / "lesson.json").read_text(encoding="utf-8"))
        legacy_lesson = json.loads((ARCHIVE / slug / "lesson.json").read_text(encoding="utf-8"))
        assert lesson["storageKey"] == legacy_lesson["storageKey"]
        assert [s["id"] for s in lesson["sections"]] == [s["id"] for s in legacy_lesson["sections"]]
        for section, legacy_section in zip(lesson["sections"], legacy_lesson["sections"]):
            assert re.findall(r"<textarea\b[^>]*>", section["html"]) == re.findall(
                r"<textarea\b[^>]*>", legacy_section["html"]
            )
        assert lesson["storageKey"] not in storage
        storage.add(lesson["storageKey"])
        assert lesson["courseRoutes"][lesson["coursePosition"] - 1] == f"../{slug}/"
        assert "1.5.1" not in json.dumps(lesson)
        assert lesson.get("sections")
        if slug in {"01-define", "02-build"}:
            assert "../development-paths.html" in "".join(s["html"] for s in lesson["sections"])
        assert any(section.get("check") for section in lesson["sections"])
        assert 'href="read.html"' in (COURSE / slug / "index.html").read_text()
        reading = (COURSE / slug / "read.html").read_text()
        assert "<textarea" not in reading
        assert "does not save answers" in reading
    for page in COURSE.rglob("*.html"):
        if "assets" in page.parts:
            continue
        parsed = Links(page.read_text(encoding="utf-8"))
        for link in parsed.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (page.parent / unquote(url.path)).resolve() if url.path else page.resolve()
            if target.is_dir():
                target /= "index.html"
            assert target.is_file(), (page, link)
            if url.fragment and target.suffix == ".html":
                assert unquote(url.fragment) in Links(target.read_text(encoding="utf-8")).ids, (page, link)


def test_download_runs_the_current_sample(tmp_path):
    example = COURSE / "assets/example"
    with zipfile.ZipFile(COURSE / "assets/reporting-example.zip") as package:
        assert package.testzip() is None
        for name in package.namelist():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            assert package.read(name) == (example / name).read_bytes()
        package.extractall(tmp_path)
    output = tmp_path / "activity-report.html"
    result = subprocess.run([
        sys.executable, str(tmp_path / "report.py"), str(tmp_path / "data/activity.csv"),
        "--format", "html", "--output", str(output),
    ], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == (example / "expected/activity-report.html").read_bytes()
    again = subprocess.run([
        sys.executable, str(tmp_path / "report.py"), str(tmp_path / "data/activity.csv"),
        "--format", "html", "--output", str(output),
    ], capture_output=True, text=True, timeout=10)
    assert again.returncode != 0
    assert output.read_bytes() == (example / "expected/activity-report.html").read_bytes()


def test_practice_prepares_both_oracles_without_acceptance_and_preserves_existing_work(tmp_path):
    destination = tmp_path.resolve() / "practice"
    invocation = [sys.executable, "-I", str(COURSE / "practice.py"), str(destination)]
    installed = subprocess.check_output([
        sys.executable, "-I", "-c",
        "from importlib.metadata import version; print(version('attune-harness'))",
    ], text=True, timeout=10).strip()
    prepared = subprocess.run(invocation, capture_output=True, text=True, timeout=30)
    assert prepared.returncode == 0, prepared.stderr
    result = json.loads(prepared.stdout)
    assert result["runtime"] == installed
    request = json.loads(Path(result["request"]).read_text(encoding="utf-8"))
    assert request["effects"]["allowed"] == ["report.py"]
    protected = request["effects"]["protected"]
    assert len(protected) == 7 and all(not name.endswith(".pyc") for name in protected)
    assert request["intent"]["acceptance"] == [
        "tests/test_report.py passes", "tests/test_html_report.py passes"
    ]
    assert result["accepted"] is False and result["build_started"] is False
    assert not (Path(result["task"]) / "record.json").exists()
    before = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in destination.rglob("*") if p.is_file()}
    refused = subprocess.run(invocation, capture_output=True, text=True, timeout=30)
    assert refused.returncode != 0 and "existing work is preserved" in refused.stderr
    after = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in destination.rglob("*") if p.is_file()}
    assert before == after


def test_archived_170_course_has_original_inventory_and_bytes():
    # The digest binds the sorted relative paths and per-file SHA-256 from e1adfd7.
    archive_files = sorted(
        (path for path in ARCHIVE.rglob("*")
         if path.is_file() and "__pycache__" not in path.parts),
        key=lambda path: path.relative_to(ARCHIVE).as_posix(),
    )
    assert len(archive_files) == 43
    digest = hashlib.sha256()
    for path in archive_files:
        assert not path.is_symlink()
        digest.update(path.relative_to(ARCHIVE).as_posix().encode() + b"\x00")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    assert digest.hexdigest() == "5391a23ce4ef9cd02c8c8b7d22ade61834f736f6d24c53428c603b0fd2e5beee"


def test_practice_bundle_contains_only_exact_safe_source_members():
    expected = {
        "practice.py",
        "requirements-practice.txt",
        "assets/example/report.py",
        "assets/example/pytest.ini",
        "assets/example/data/activity.csv",
        "assets/example/expected/activity-report.html",
        "assets/example/expected/activity-report.txt",
        "assets/example/tests/test_report.py",
        "assets/example/tests/test_html_report.py",
    }
    with zipfile.ZipFile(COURSE / "assets/reporting-practice.zip") as archive:
        assert archive.testzip() is None
        names = [entry.filename for entry in archive.infolist()]
        assert len(names) == len(set(names)) and set(names) == expected
        for entry in archive.infolist():
            member = PurePosixPath(entry.filename)
            assert not member.is_absolute() and ".." not in member.parts
            assert not entry.is_dir() and stat.S_ISREG(entry.external_attr >> 16)
            assert archive.read(entry) == (COURSE / member).read_bytes()
    assert (COURSE / "requirements-practice.txt").read_text().splitlines() == [
        "attune-harness", "pytest==9.1.1",
    ]


@pytest.fixture
def practice_helper():
    spec = importlib.util.spec_from_file_location("reporting_practice", COURSE / "practice.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def test_practice_missing_harness_refuses_before_creating_project(tmp_path, monkeypatch, practice_helper):
    def missing(package):
        raise PackageNotFoundError(package)

    monkeypatch.setattr(practice_helper, "version", missing)
    destination = tmp_path.resolve() / "practice"
    with pytest.raises(ValueError, match="Install Harness in this Python environment"):
        practice_helper.prepare(destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    ("missing_command", "message"),
    [("import pytest", "Install pytest in this Python environment"),
     ("git", "Install Git and make it available on PATH")],
)
def test_practice_missing_dependency_refuses_before_creating_project(
    tmp_path, monkeypatch, practice_helper, missing_command, message,
):
    def run(command, **kwargs):
        if missing_command in command:
            raise FileNotFoundError(missing_command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(practice_helper, "version", lambda _: "2.1.0")
    monkeypatch.setattr(practice_helper.subprocess, "run", run)
    destination = tmp_path.resolve() / "practice"
    with pytest.raises(ValueError, match=message):
        practice_helper.prepare(destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    ("verb", "option", "replacement", "message"),
    [
        ("build", "--allow-external", "  --allow-external-extra\n    Mentions --allow-external\n",
         "build --allow-external"),
        ("init", "--for", "  --for {fix,roundtable}\n", "init --for plan"),
        ("status", "--format", "  --format {json,html}\n", "status --format markdown"),
    ],
)
def test_practice_incompatible_cli_refuses_before_creating_project(
    tmp_path, monkeypatch, practice_helper, verb, option, replacement, message,
):
    def run(command, **kwargs):
        if command[-1] != "--help":
            return subprocess.CompletedProcess(command, 0, stdout="")
        current_verb = command[-2]
        required = {
            name: "  " + name + "\n" for name in practice_helper._COURSE_OPTIONS[current_verb]
        }
        if current_verb == "init":
            required["--for"] = "  --for {fix,plan,roundtable}\n"
        if current_verb == "status":
            required["--format"] = "  --format {json,markdown,html}\n"
        if current_verb == verb:
            required[option] = replacement
        return subprocess.CompletedProcess(command, 0, stdout="  task_dir\n" + "".join(required.values()))

    monkeypatch.setattr(practice_helper, "version", lambda _: "2.1.0")
    monkeypatch.setattr(practice_helper.subprocess, "run", run)
    destination = tmp_path.resolve() / "practice"
    with pytest.raises(ValueError, match=f"Harness 2.1.0 does not expose {message}"):
        practice_helper.prepare(destination)
    assert not destination.exists()


def test_practice_refuses_noncanonical_destination_before_runtime_checks(tmp_path, monkeypatch, practice_helper):
    parent = tmp_path.resolve()
    actual = parent / "actual"
    actual.mkdir()
    alias = parent / "alias"
    try:
        alias.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    monkeypatch.setattr(practice_helper, "_check_runtime", lambda: pytest.fail("unexpected runtime probe"))
    with pytest.raises(ValueError, match="canonical parent directory"):
        practice_helper.prepare(alias / "practice")
    assert not (actual / "practice").exists()


def test_practice_refuses_overlong_worker_before_creating_project(tmp_path, monkeypatch, practice_helper):
    monkeypatch.setattr(practice_helper, "_check_runtime", lambda: "2.1.0")
    monkeypatch.setattr(practice_helper, "_MAX_WORKER_BYTES", 1)
    destination = tmp_path.resolve() / "practice"
    with pytest.raises(ValueError, match="command argument bound"):
        practice_helper.prepare(destination)
    assert not destination.exists()
