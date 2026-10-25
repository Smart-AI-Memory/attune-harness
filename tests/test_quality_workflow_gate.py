"""Exercise the actual required verdict with failing and missing lint results."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qualification.yml"


def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def verdict(tmp_path, **overrides):
    if os.name == "nt":
        pytest.skip("The verdict runs in Ubuntu Bash; POSIX jobs exercise its shell controls")
    step = next(
        item for item in workflow()["jobs"]["qualification"]["steps"]
        if item.get("name") == "Report one verdict"
    )
    bash = shutil.which("bash")
    assert bash is not None, "The workflow verdict controls require Bash"
    environment = {
        **os.environ,
        "EVENT_NAME": "pull_request",
        "CLASSIFIED": "success",
        "QUALIFY": "true",
        "REASON": "code",
        "PLATFORMS": "success",
        "SUITE": "success",
        "LINKS": "success",
        "LINT": "success",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        **overrides,
    }
    return subprocess.run(
        [bash, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize("profile", ["code", "docs-only", "release-branch"])
@pytest.mark.parametrize("lint", ["failure", "cancelled", "skipped", "", "unexpected"])
def test_unsuccessful_lint_refuses_every_qualification_profile(tmp_path, profile, lint):
    values = {"LINT": lint, "REASON": profile}
    if profile != "code":
        values.update(QUALIFY="false", PLATFORMS="skipped", SUITE="skipped")
    result = verdict(tmp_path, **values)
    assert result.returncode == 1
    assert "Qualification did not pass" in result.stdout
    assert "correctness lint:" in result.stdout


@pytest.mark.parametrize("profile", ["code", "docs-only", "release-branch"])
def test_successful_lint_preserves_existing_qualification_profiles(tmp_path, profile):
    values = {"REASON": profile}
    if profile != "code":
        values.update(QUALIFY="false", PLATFORMS="skipped", SUITE="skipped")
    result = verdict(tmp_path, **values)
    assert result.returncode == 0, result.stderr
    assert "correctness lint" in result.stdout.lower()
    assert "::error" not in result.stdout
    if profile != "code":
        assert "without qualifying any platform" in result.stdout or "matrix was not run" in result.stdout


@pytest.mark.parametrize("field", ["CLASSIFIED", "PLATFORMS", "SUITE", "LINKS"])
@pytest.mark.parametrize("status", ["failure", "cancelled", ""])
def test_successful_lint_does_not_hide_other_failed_or_missing_gates(tmp_path, field, status):
    result = verdict(tmp_path, **{field: status})
    assert result.returncode == 1
    assert "Qualification did not pass" in result.stdout


@pytest.mark.parametrize("profile", ["docs-only", "release-branch"])
@pytest.mark.parametrize("field", ["CLASSIFIED", "PLATFORMS", "SUITE", "LINKS"])
def test_skipped_platform_path_still_refuses_a_failed_existing_gate(tmp_path, profile, field):
    values = {"QUALIFY": "false", "REASON": profile,
              "PLATFORMS": "skipped", "SUITE": "skipped", field: "failure"}
    assert verdict(tmp_path, **values).returncode == 1


def test_push_cannot_use_a_pull_request_matrix_skip(tmp_path):
    result = verdict(tmp_path, EVENT_NAME="push", QUALIFY="false",
                     PLATFORMS="skipped", SUITE="skipped")
    assert result.returncode == 1


def test_required_verdict_receives_the_actual_lint_job_result():
    jobs = workflow()["jobs"]
    assert "lint" in jobs["qualification"]["needs"]
    step = next(item for item in jobs["qualification"]["steps"]
                if item.get("name") == "Report one verdict")
    assert step["env"]["LINT"] == "${{ needs.lint.result }}"
    assert jobs["qualification"]["if"] == "${{ always() }}"
    assert "if" not in jobs["lint"]


def test_lint_job_keeps_its_approved_runtime_pin_and_path_scope():
    job = workflow()["jobs"]["lint"]
    assert job["runs-on"] == "ubuntu-latest"
    setup = next(step for step in job["steps"]
                 if step.get("uses", "").startswith("actions/setup-python@"))
    assert setup["with"]["python-version"] == "3.12"
    commands = [step["run"] for step in job["steps"] if "run" in step]
    assert commands == ['python -m pip install "ruff==0.14.4"',
                        "ruff check --no-cache --no-fix src scripts"]
