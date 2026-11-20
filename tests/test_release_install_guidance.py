"""The release gate distinguishes stale, missing and historical guidance."""

from pathlib import Path
import re
from zipfile import ZipFile

import pytest

from scripts import check_release_install_guidance as check

VERSION = "7.8.9"
PYPI = f"https://pypi.org/project/attune-harness/{VERSION}/"
RELEASE = f"{check.REPO}/releases/tag/v{VERSION}"
PINS = ["attune-forms==0.17.0", "attune-rag==1.2.0", "attune-verify==0.6.0"]


@pytest.mark.parametrize(("broken", "expected"), [
    ("", None), ("source", "expected"), ("missing", "missing install"), ("link", "stale release"),
    ("description", "Wheel README differs"), ("dependency", "table does not match"),
])
def test_current_source_and_actual_wheel_readme(tmp_path, broken, expected):
    root = Path(__file__).resolve().parents[1]
    version = re.search(r"pypi.org/project/attune-harness/([.0-9]+)/", (root / "README.md").read_text())[1]
    current_pins = check.DEPENDENCY_ROW.findall((root / "help/dependencies.md").read_text())
    for file in ("README.md", "help/get-started.md", "help/dependencies.md", "docs/installation.md"):
        body = (root / file).read_text()
        if file == "help/get-started.md":
            if broken == "source":
                body = body.replace(f"attune-harness=={version}", "attune-harness==0.0.1")
            if broken == "missing":
                body = body.replace("pip install", "setup").replace("tool install", "setup")
        if file == "README.md" and broken == "link":
            body = body.replace(f"/releases/tag/v{version}", "/releases/tag/v0.0.1")
        if file == "help/dependencies.md" and broken == "dependency":
            body = re.sub(r"(\| `attune-rag` \| )`[^ `]+`", r"\g<1>`0.0.1`", body)
        target = tmp_path / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    description = "Not reviewed" if broken == "description" else (tmp_path / "README.md").read_text()
    metadata = f"Name: attune-harness\nVersion: {version}\n"
    metadata += "".join(f"Requires-Dist: {name}=={pin}\n" for name, pin in current_pins)
    wheel = tmp_path / "test.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(f"attune_harness-{version}.dist-info/METADATA", metadata + "\n" + description)
    if expected:
        with pytest.raises(ValueError, match=expected):
            check.candidate(tmp_path, wheel, version)
    else:
        assert len(check.candidate(tmp_path, wheel, version)) == 4
        # The real docs contain separately scoped historic instructions.
        assert "attune-harness==1.7.0" in (tmp_path / "docs/installation.md").read_text()


@pytest.mark.parametrize("broken", ["", "stale", "unchecked", "wrong_link", "unreachable"])
def test_public_completion_requires_current_pages_and_reachable_release(broken):
    def page(extra, *links):
        return (f"<code>pip install &#x27;attune-harness{extra}=={VERSION}&#x27;</code>"
                + "".join(f'<a href="{href}">next</a>' for href in links))

    pages = {
        PYPI: page("", RELEASE, check.GET_STARTED, check.LEARN) + page("[redis]"),
        check.GET_STARTED: page("", PYPI),
        check.DEPENDENCIES: page("[redis]", PYPI),
        check.LEARN: page("", check.GET_STARTED, "/harness/learn/reporting/"),
        RELEASE: "release",
    }
    if not broken:
        assert set(check.public_docs(VERSION, read=pages.__getitem__)) == set(pages) - {RELEASE}
        return
    if broken == "stale":
        pages[check.DEPENDENCIES] = pages[check.DEPENDENCIES].replace(f"=={VERSION}", "==1.5.1")
    elif broken == "unchecked":
        pages[check.LEARN] = pages[check.LEARN].replace("pip install", "nothing")
    elif broken == "wrong_link":
        pages[check.GET_STARTED] += f'<a href="{check.REPO}/blob/v0.0.1/docs/install.md">wrong</a>'
    else:
        del pages[RELEASE]
    with pytest.raises((ValueError, KeyError)):
        check.public_docs(VERSION, read=pages.__getitem__)


def test_post_index_pins_and_receipts_must_match_exactly():
    pins = check.direct_attune_pins(PINS)
    installed = {"attune-harness": VERSION, **pins}

    def read_requires(_):
        return PINS

    assert check.verify_install(VERSION, PINS, read_version=installed.__getitem__, read_requires=read_requires) == pins
    installed["attune-forms"] = "9.9.9"
    with pytest.raises(ValueError, match="Installed Attune versions differ"):
        check.verify_install(VERSION, PINS, read_version=installed.__getitem__, read_requires=read_requires)
    identity = dict(version=VERSION, commit="a" * 40, wheel_sha256="b" * 64)
    base = dict(identity, stage="installed", profile="base", status="passed", pip_check="passed", direct_attune_dependencies=pins)
    redis = dict(base, profile="redis")
    check.completion_inputs(identity, [base, redis], PINS)
    for wrong in ([base], [base, base], [base, dict(redis, pip_check=None)], [base, dict(redis, status="failed")],
                  [base, dict(redis, wheel_sha256="f" * 64)]):
        with pytest.raises(ValueError):
            check.completion_inputs(identity, wrong, PINS)



def test_rendered_html_keeps_syntax_highlighted_and_nested_code():
    page = check.Page("<pre><span>pip install</span> <code>'attune-harness==7.8.9'</code></pre>")
    assert page.commands == ["pip install 'attune-harness==7.8.9'"]


@pytest.mark.parametrize("broken", ["", "bad_receipt", "wrong_wheel", "stale_learn", "wrong_public_readme"])
def test_website_cli_is_fail_closed(tmp_path, monkeypatch, broken):
    import hashlib
    import json
    import sys

    description = (
        f"uv tool install 'attune-harness=={VERSION}'\n"
        f"pip install 'attune-harness[redis]=={VERSION}'\n"
        f"[release]({RELEASE}) [help]({check.GET_STARTED}) [learn]({check.LEARN})\n"
    )
    wheel = tmp_path / f"attune_harness-{VERSION}-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(f"attune_harness-{VERSION}.dist-info/METADATA",
                         f"Name: attune-harness\nVersion: {VERSION}\n\n{description}")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    sha = "9" * 40
    records = []
    for profile in ("base", "redis"):
        path = tmp_path / f"{profile}.json"
        path.write_text(json.dumps({
            "stage": "installed", "version": VERSION, "commit": sha, "wheel_sha256": digest,
            "status": "failed" if profile == "redis" and broken == "bad_receipt" else "passed",
            "profile": profile, "direct_attune_dependencies": check.direct_attune_pins(PINS), "pip_check": "passed",
        }))
        records.append(str(path))
    endpoint = f"https://pypi.org/pypi/attune-harness/{VERSION}/json"
    course = check.SITE + "/harness/learn/reporting/"
    command_version = "1.5.1" if broken == "stale_learn" else VERSION
    pages = {
        endpoint: json.dumps({
            "info": {"version": VERSION, "requires_dist": PINS,
                     "description": "Wrong description" if broken == "wrong_public_readme" else description},
            "urls": [{"filename": wheel.name, "digests": {"sha256": "" if broken == "wrong_wheel" else digest},
                      "yanked": False}],
        }),
        check.GET_STARTED: f'<pre><code>uv tool install attune-harness=={VERSION}</code></pre><a href="{PYPI}">PyPI</a>',
        check.DEPENDENCIES: f'<pre><code>pip install attune-harness[redis]=={VERSION}</code></pre><a href="{PYPI}">PyPI</a>',
        check.LEARN: f'<pre><span>uv pip install</span> <code>attune-harness=={command_version}</code></pre>'
                     f'<a href="{check.GET_STARTED}">Help</a><a href="{course}">Course</a>',
        RELEASE: "release",
    }
    monkeypatch.setattr(check, "read_public", pages.__getitem__)
    report = tmp_path / "website.json"
    monkeypatch.setattr(sys, "argv", [
        "check_release_install_guidance.py", "website", "--version", VERSION, "--release-sha", sha,
        "--wheel", str(wheel), "--installed-evidence", *records, "--report", str(report),
    ])
    if broken:
        with pytest.raises(SystemExit):
            check.main()
        assert json.loads(report.read_text())["status"] == "failed"
    else:
        check.main()
        receipt = json.loads(report.read_text())
        assert receipt["status"] == "passed"
        assert receipt["surfaces"][PYPI]["source"] == "public PyPI JSON description"
        assert receipt["surfaces"][check.LEARN]["source"] == "live HTML"


@pytest.mark.parametrize("redirect, anchor, passed", [
    (check.LEARN_REDIRECT, "set-up-the-practice-folder", True),
    (check.LEARN_REDIRECT, "unrelated", False),
    (check.GET_STARTED, "set-up-the-practice-folder", False),
])
def test_learn_requires_exact_deliberate_redirect_and_anchor(monkeypatch, redirect, anchor, passed):
    from io import BytesIO

    body = BytesIO(f'<h2 id="{anchor}">Set up the practice folder</h2>'.encode())
    body.url = redirect
    monkeypatch.setattr(check, "urlopen", lambda *a, **kw: body)
    if passed:
        assert "Set up the practice folder" in check.read_public(check.LEARN)
    else:
        with pytest.raises(ValueError):
            check.read_public(check.LEARN)
