"""Check the delivered course, download and no-dispatch practice preparation."""

import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"
COURSE = TRAINING / "1.7.0-preparation"


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
    for slug in builder.SLUGS:
        lesson = json.loads((COURSE / slug / "lesson.json").read_text(encoding="utf-8"))
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
    destination = tmp_path / "practice"
    invocation = [sys.executable, str(COURSE / "practice.py"), str(destination)]
    prepared = subprocess.run(invocation, capture_output=True, text=True, timeout=30)
    assert prepared.returncode == 0, prepared.stderr
    result = json.loads(prepared.stdout)
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
