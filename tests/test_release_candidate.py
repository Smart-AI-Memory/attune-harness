"""Release admission rejects stale CI and unavailable or reused version slots."""

import copy
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location(
    "release_candidate",
    Path(__file__).resolve().parents[1] / "scripts/check_release_candidate.py",
)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def packet():
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
        version="0.1.0",
        head=sha,
        project=dict(name="attune-harness", version="0.1.0"),
        changelog="# Changelog\n\n## 0.1.0 — release\n",
        repository=repo,
        runs=dict(workflow_runs=[run]),
    )


def test_exact_candidate_and_latest_success():
    assert candidate.validate_target(**packet())["version"] == "0.1.0"


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
def test_stale_or_unqualified_candidate_rejected(case):
    data = packet()
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
