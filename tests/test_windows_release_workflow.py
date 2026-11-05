"""Keep publication behind same-run exact-artifact Windows consumers."""

import os
from pathlib import Path
import re
import subprocess
import sys

import yaml


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/publish-pypi.yml"


def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_both_publication_routes_require_the_windows_matrix():
    value = workflow()
    triggers = value.get("on", value.get(True))
    assert triggers["workflow_dispatch"]["inputs"]["publish"]["type"] == "boolean"
    jobs = value["jobs"]
    consumer = jobs["windows-release-wheel"]
    assert consumer["needs"] == "build"
    assert "if" not in consumer, "Rehearsals must exercise the same consumer gate"
    assert set(consumer["strategy"]["matrix"]["os"]) == {"windows-2022", "windows-2025"}
    for name, target in (("publish", "pypi"), ("publish_testpypi", "testpypi")):
        assert set(jobs[name]["needs"]) == {"build", "windows-release-wheel"}
        assert jobs[name]["if"] == f"inputs.publish && inputs.target == '{target}'"
        assert jobs[name]["environment"] == target
    assert jobs["verify_testpypi"]["needs"] == "publish_testpypi"


def test_consumer_uses_same_run_artifact_ids_and_lf_checkout():
    jobs = workflow()["jobs"]
    consumer = jobs["windows-release-wheel"]
    steps = consumer["steps"]
    checkout = next(i for i, step in enumerate(steps) if step.get("uses", "").startswith("actions/checkout@"))
    assert any("git config --global core.autocrlf false" in step.get("run", "") for step in steps[:checkout])
    assert steps[checkout]["with"]["ref"] == "${{ github.sha }}"
    downloads = [step["with"] for step in steps if step.get("uses", "").startswith("actions/download-artifact@")]
    assert len(downloads) == 2
    assert {step["artifact-ids"] for step in downloads} == {
        "${{ needs.build.outputs.distributions_id }}",
        "${{ needs.build.outputs.release_evidence_id }}",
    }
    assert all(step["digest-mismatch"] == "error" and "run-id" not in step and "github-token" not in step for step in downloads)
    assert all(step["path"].startswith("${{ env.WINDOWS_RELEASE_") for step in downloads)
    uploads = {step["id"]: step for step in jobs["build"]["steps"] if step.get("id") in {"distributions", "release-evidence"}}
    assert set(uploads) == {"distributions", "release-evidence"}
    assert jobs["build"]["outputs"]["distributions_id"] == "${{ steps.distributions.outputs.artifact-id }}"
    assert jobs["build"]["outputs"]["release_evidence_id"] == "${{ steps.release-evidence.outputs.artifact-id }}"


def test_runtime_paths_initialize_before_consumption_without_job_runner_context(tmp_path):
    jobs = workflow()["jobs"]
    for job in jobs.values():
        assert all(not re.search(r"\$\{\{\s*runner\.", str(value))
                   for value in job.get("env", {}).values())
    steps = jobs["windows-release-wheel"]["steps"]
    initializer = next(i for i, step in enumerate(steps)
                       if step.get("name") == "Initialize owned release evidence paths")
    first_download = next(i for i, step in enumerate(steps)
                          if step.get("uses", "").startswith("actions/download-artifact@"))
    assert initializer < first_download
    assert steps[initializer]["shell"] == "python"
    temporary = tmp_path / "runner temp Å"
    github_env = tmp_path / "github-env"
    subprocess.run([sys.executable, "-I", "-c", steps[initializer]["run"]], check=True,
                   env={**os.environ, "RUNNER_TEMP": str(temporary), "GITHUB_ENV": str(github_env)})
    actual = dict(line.split("=", 1) for line in github_env.read_text(encoding="utf-8").splitlines())
    assert actual == {
        "WINDOWS_RELEASE_DIST": str(temporary / "release-windows-distributions"),
        "WINDOWS_RELEASE_BUILD_EVIDENCE": str(temporary / "release-windows-build-evidence"),
        "WINDOWS_RELEASE_EVIDENCE": str(temporary / "release-windows-evidence"),
        "WINDOWS_RELEASE_NATIVE_OUTPUT": str(temporary / "release-windows-evidence/native"),
    }
