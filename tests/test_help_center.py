"""Exercise the static Help Center artifact and its failure boundaries."""

import importlib.util
import json
from pathlib import Path
import shutil

import pytest

pytest.importorskip(
    "markdown", reason="Install help/requirements.txt for the documentation build"
)
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "build_help", ROOT / "scripts/build_help.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_all_current_routes_and_contents_links_work(tmp_path):
    record = builder.build_site(tmp_path / "site")
    assert record["version"] == "1.5.1"
    assert record["status"] == "preparation"
    assert record["published_version"] == "1.5.0"
    assert record["pages"] == 12
    directory = tmp_path / "site/harness/help"
    files = list(directory.rglob("index.html"))
    assert len(files) == 12
    for page in files:
        text = page.read_text()
        assert text.count("<h1>") == 1
        assert (
            'class="goal-index"'
            if page.parent.name == "goals"
            else 'aria-label="On this page"'
        ) in text
        assert 'id="main-content" tabindex="-1"' in text
        if page.parent.name == "goals":
            assert "Preparation only; this version is not yet released" in text
        else:
            assert (
                "published <strong>Harness 1.5.0</strong>"
                if page.parent.name == "1-5-0"
                else "Guidance target: <strong>Harness 1.5.1</strong> preparation"
            ) in text
    reference = (directory / "ai-tools-and-integrations/index.html").read_text()
    for anchor in (
        "plan-accept-then-build",
        "preview-approve-then-test",
        "memory-subcommands",
    ):
        assert f'id="{anchor}"' in reference
        assert f'href="#{anchor}"' in reference
    assert "--session-dir SESSION_DIR" in reference
    planning = (directory / "plan-and-accept/index.html").read_text()
    assert 'id="how-does-a-sample-plan-become-accepted"' in planning
    assert (
        "Approve this work request"
        in (directory / "start-and-continue/index.html").read_text()
    )
    assert (directory / "verification.json").is_file()


def test_goal_projection_preserves_navigation_controls_and_historical_evidence(
    tmp_path,
):
    builder.build_site(tmp_path / "site")
    root = tmp_path / "site/harness/help"
    text = (root / "goals/index.html").read_text()
    assert text.count('class="goal-item"') == 21
    assert text.count('class="testing-goal"') == 6
    assert text.index('href="#research-question"') < text.index(
        'href="#feature-request"'
    )
    assert "Learn before you build" in text
    assert 'src="/harness/help/goals/controls.js"' in text
    assert 'type="application/json" id="goal-guide-data"' in text
    assert "unapproved" in text and "captured from Harness 1.5.0" in text
    state = json.loads((root / "assets/state-check.json").read_text())
    assert state["acceptance"] is None and state["status"] == "draft"
    assert state["planning_or_build_present"] is False
    for name in builder.GOAL_ASSETS:
        assert (root / "assets" / name).read_bytes() == (
            ROOT / "help/assets" / name
        ).read_bytes()
    assert (root / "verification.json").read_bytes() == (
        ROOT / "help/verification.json"
    ).read_bytes()
    assert 'href="/harness/help/goals/"' in (root / "index.html").read_text()


@pytest.mark.parametrize(
    "defect", ["script", "event", "binding", "count", "asset", "source"]
)
def test_invalid_goal_source_refuses_before_export(tmp_path, defect):
    content = tmp_path / "content"
    shutil.copytree(ROOT / "help", content)
    master = content / "goals/guide.html"
    text = master.read_text()
    if defect == "script":
        text += "<script>window.invalid = true</script>"
    elif defect == "event":
        text += '<button onclick="run()">Bad control</button>'
    elif defect == "binding":
        text = text.replace('id="wording-choices"', 'id="missing-choices"')
    elif defect == "count":
        text = text.replace('class="goal-item"', 'class="removed-goal"', 1)
    elif defect == "asset":
        text = text.replace(
            "/harness-help-assets/intake-filled.jpg", "/harness-help-assets/missing.jpg"
        )
    elif defect == "source":
        manifest = json.loads((content / "manifest.json").read_text())
        manifest["topics"][0]["source"] = "../outside.html"
        (content / "manifest.json").write_text(json.dumps(manifest))
    master.write_text(text)
    with pytest.raises(ValueError):
        builder.build_site(tmp_path / "site", content)
    assert not (tmp_path / "site").exists()


def test_worksheet_data_cannot_close_its_json_script(tmp_path):
    content = tmp_path / "content"
    shutil.copytree(ROOT / "help", content)
    data = json.loads((content / "goals/data.json").read_text())
    data["initial"] += '</script><script id="injected">bad()</script>'
    (content / "goals/data.json").write_text(json.dumps(data))
    builder.build_site(tmp_path / "site", content)
    text = (tmp_path / "site/harness/help/goals/index.html").read_text()
    assert '<script id="injected">' not in text
    assert "\\u003c/script>" in text


def test_invalid_legacy_heading_alias_refuses_a_build(tmp_path):
    content = tmp_path / "content"
    shutil.copytree(ROOT / "help", content)
    manifest = json.loads((content / "manifest.json").read_text())
    manifest["overview_anchors"] = {"old": "missing"}
    (content / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Missing target"):
        builder.build_site(tmp_path / "site", content)


def test_broken_local_route_and_fragment_refuse_before_writing(tmp_path):
    for href in ("/harness/help/missing/", "/harness/help/#missing"):
        with pytest.raises(ValueError, match="Broken Help Center link"):
            builder.validate_pages({"": f'<a href="{href}">Go</a>'})
    assert not (tmp_path / "site").exists()


def test_existing_output_and_symlink_parent_are_refused(tmp_path):
    output = tmp_path / "site"
    output.mkdir()
    receipt = output / "receipt.txt"
    receipt.write_text("retained")
    with pytest.raises(ValueError, match="existing evidence"):
        builder.build_site(output)
    assert receipt.read_text() == "retained"
    link = tmp_path / "alias"
    try:
        link.symlink_to(output, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(ValueError, match="canonical"):
        builder.build_site(link / "new-output")


@pytest.mark.parametrize("slug", ["../outside", "a/b", "duplicate"])
def test_manifest_path_escape_and_duplicate_routes_are_refused(tmp_path, slug):
    content = tmp_path / "content"
    content.mkdir()
    (content / "manifest.json").write_text(
        json.dumps({"topics": [{"slug": slug}, {"slug": slug}]})
    )
    with pytest.raises(ValueError, match="unique, simple"):
        builder.build_site(tmp_path / "site", content)
    assert not (tmp_path / "site").exists()


def test_nested_duplicate_and_fenced_headings_have_correct_anchors(tmp_path):
    content = tmp_path / "content"
    shutil.copytree(ROOT / "help", content)
    (content / "get-started.md").write_text(
        "## Same\n\n### Nested\n\n## Same\n\n```text\n## Fenced\n```\n"
    )
    builder.build_site(tmp_path / "site", content)
    text = (tmp_path / "site/harness/help/get-started/index.html").read_text()
    assert 'id="same"' in text and 'id="same_1"' in text and 'id="nested"' in text
    assert 'id="fenced"' not in text
    assert "## Fenced" in text


def test_export_is_reproducible(tmp_path):
    first = builder.build_site(tmp_path / "first")
    second = builder.build_site(tmp_path / "second")
    assert first == second
    for path in (tmp_path / "first").rglob("*"):
        if path.is_file():
            assert (
                path.read_bytes()
                == (
                    tmp_path / "second" / path.relative_to(tmp_path / "first")
                ).read_bytes()
            )
