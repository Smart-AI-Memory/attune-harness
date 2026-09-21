"""Check a final release candidate in CI (Python 3.12); never publish."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.request import urlopen


def validate_target(*, sha, version, head, project, changelog, runs, repository):
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or head != sha:
        raise ValueError("The checkout must match the full approved commit SHA")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("This publication path requires a final release version")
    if project.get("name") != "attune-harness" or project.get("version") != version:
        raise ValueError("Package metadata differs from the requested release")
    if not re.search(r"^## " + re.escape(version) + r"(?:\s|$)", changelog, re.M):
        raise ValueError("The requested version needs its own changelog heading")
    eligible = [
        run
        for run in runs.get("workflow_runs", [])
        if run.get("head_sha") == sha
        and run.get("event") in ("push", "workflow_dispatch")
        and run.get("head_repository", {}).get("full_name") == repository
    ]
    if not eligible:
        raise ValueError("No qualification run exists for this repository and SHA")
    latest = max(eligible, key=lambda run: (run["run_number"], run["run_attempt"]))
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        raise ValueError("Latest qualification for the release SHA did not pass")
    return {
        "commit": sha,
        "version": version,
        "qualification_run": latest["html_url"],
        "qualification_attempt": latest["run_attempt"],
    }


def check_version_slot(version, *, opener=urlopen):
    url = "https://pypi.org/pypi/attune-harness/json"
    try:
        with opener(url, timeout=30) as response:
            published = json.load(response)
    except HTTPError as error:
        if error.code != 404:
            raise
        return {"url": url, "project_absent": True, "version_available": True}
    if version in published["releases"]:
        raise ValueError("The requested Harness version is already on PyPI")
    return {"url": url, "project_absent": False, "version_available": True}


def main():
    import tomllib  # Release workflow runs Python 3.12; pure guards support 3.10.

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
            raise ValueError("Release checkout must be clean before building")
        receipt = validate_target(
            sha=os.environ["RELEASE_SHA"],
            version=os.environ["RELEASE_VERSION"],
            head=head,
            project=tomllib.loads(Path("pyproject.toml").read_text())["project"],
            changelog=Path("CHANGELOG.md").read_text(encoding="utf-8"),
            runs=json.loads(args.runs.read_text(encoding="utf-8")),
            repository=os.environ["GITHUB_REPOSITORY"],
        )
        receipt["pypi"] = check_version_slot(receipt["version"])
        receipt["status"] = "passed"
    except Exception as error:
        (args.output / "preflight.json").write_text(
            json.dumps({"status": "failed", "error": str(error)}, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    (args.output / "preflight.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
