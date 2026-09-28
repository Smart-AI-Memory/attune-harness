"""Release admission rejects stale CI and unavailable or reused version slots."""

import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location(
    "release_candidate",
    Path(__file__).resolve().parents[1] / "scripts/check_release_candidate.py",
)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def packet(version="0.1.0"):
    sha = "a" * 40
    repo = "Smart-AI-Memory/attune-harness"
    run = dict(
        head_sha=sha,
        event="push",
        head_repository=dict(full_name=repo),
        run_number=10,
        run_attempt=1,
        status="completed",
        conclusion="success",
        html_url="https://github.com/Smart-AI-Memory/attune-harness/actions/runs/123",
    )
    return dict(
        sha=sha,
        version=version,
        head=sha,
        project=dict(name="attune-harness", version=version),
        changelog=f"# Changelog\n\n## {version} — release\n",
        repository=repo,
        runs=dict(workflow_runs=[run]),
    )


@pytest.mark.parametrize("version", ["0.1.0", "1.0.0rc1", "1.0.0rc12"])
def test_exact_candidate_and_latest_success(version):
    assert candidate.validate_target(**packet(version))["version"] == version


@pytest.mark.parametrize(
    "case",
    [
        "sha",
        "version",
        "metadata",
        "changelog",
        "foreign_repo",
        "old_sha",
        "pull_request",
        "new_failure",
        "rerun_pending",
    ],
)
@pytest.mark.parametrize("version", ["0.1.0", "1.0.0rc1"])
def test_stale_or_unqualified_candidate_rejected(case, version):
    data = packet(version)
    run = data["runs"]["workflow_runs"][0]
    if case == "sha":
        data["head"] = "b" * 40
    elif case == "version":
        data["version"] = "0.1.0.dev13"
    elif case == "metadata":
        data["project"]["version"] = "0.0.9"
    elif case == "changelog":
        data["changelog"] = "## 0.1.0.dev13\nDiscuss 0.1.0 later"
    elif case == "foreign_repo":
        run["head_repository"]["full_name"] = "other/fork"
    elif case == "old_sha":
        run["head_sha"] = "b" * 40
    elif case == "pull_request":
        run["event"] = "pull_request"
    else:
        newer = copy.deepcopy(run)
        if case == "new_failure":
            newer.update(run_number=11, conclusion="failure")
        else:
            newer.update(run_attempt=2, status="in_progress", conclusion=None)
        data["runs"]["workflow_runs"].append(newer)
    with pytest.raises(ValueError):
        candidate.validate_target(**data)


def test_version_lookup_distinguishes_absent_from_unavailable_and_existing():
    def failed(code):
        def open_url(*args, **kwargs):
            raise HTTPError(args[0], code, "fixture", None, None)

        return open_url

    assert candidate.check_version_slot("0.1.0", opener=failed(404))["project_absent"]
    with pytest.raises(HTTPError):
        candidate.check_version_slot("0.1.0", opener=failed(503))
    with pytest.raises(ValueError, match="already"):
        candidate.check_version_slot(
            "0.1.0",
            opener=lambda *a, **k: io.StringIO(json.dumps({"releases": {"0.1.0": []}})),
        )


@pytest.mark.parametrize(
    "version",
    [
        "1.0.0rc0",
        "1.0.0rc01",
        "1.0.0rc",
        "1.0.0a1",
        "1.0.0b1",
        "1.0.0.dev1",
        "1.0.0.post1",
        "1.0.0+local",
        "v1.0.0",
        "1.0.0rc1\n",
    ],
)
def test_unsupported_release_versions_rejected(version):
    with pytest.raises(ValueError, match="requires a final or release-candidate"):
        candidate.validate_target(**packet(version))


@pytest.mark.skipif(shutil.which("bash") is None, reason="workflow runs on Ubuntu Bash")
@pytest.mark.parametrize("bash_path", ["bash", "/bin/bash"] if sys.platform == "darwin" else ["bash"])
@pytest.mark.parametrize(
    "target,version,matching_sha,accepted",
    [
        ("pypi", "1.0.0", True, True),
        ("pypi", "1.0.0rc1", True, True),
        ("pypi", "1.0.0rc12", True, True),
        ("testpypi", "1.0.0rc1", True, True),
        ("testpypi", "1.0.0", True, False),
        ("pypi", "1.0.0rc0", True, False),
        ("pypi", "1.0.0rc01", True, False),
        ("pypi", "1.0.0.dev1", True, False),
        ("pypi", "1.0.0+local", True, False),
        ("pypi", "1.0.0rc1", False, False),
        ("unknown", "1.0.0rc1", True, False),
    ],
)
def test_workflow_immutable_target_guard(target, version, matching_sha, accepted, bash_path):
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/publish-pypi.yml"
    ).read_text()
    step = workflow.split("- name: Validate immutable target\n", 1)[1]
    script = step.split("        run: |\n", 1)[1].split("      - uses:", 1)[0]
    script = "\n".join(line[10:] for line in script.splitlines())
    env = dict(
        os.environ,
        RELEASE_TARGET=target,
        RELEASE_VERSION=version,
        RELEASE_SHA="a" * 40,
        GITHUB_SHA=("a" if matching_sha else "b") * 40,
    )
    result = subprocess.run([bash_path, "-e", "-c", script], env=env, capture_output=True)
    assert (result.returncode == 0) is accepted, result.stderr.decode()
