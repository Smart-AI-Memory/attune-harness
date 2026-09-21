"""Provisional TestPyPI RC preflight and exact distribution round trip."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen


PROJECT = "attune-harness"
TESTPYPI_API = "https://test.pypi.org/pypi/attune-harness"
WHEEL = re.compile(r"attune_harness-(?P<version>\d+\.\d+\.\d+rc[1-9]\d*)-py3-none-any\.whl")
SDIST = re.compile(r"attune_harness-(?P<version>\d+\.\d+\.\d+rc[1-9]\d*)\.tar\.gz")
RC = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+rc[1-9][0-9]*")
SHA = re.compile(r"[0-9a-f]{40}")


def qualification_observation(runs: dict, sha: str, repository: str) -> dict:
    eligible = [
        row for row in runs.get("workflow_runs", [])
        if row.get("head_sha") == sha
        and row.get("head_repository", {}).get("full_name") == repository
        and row.get("event") in {"push", "workflow_dispatch"}
    ]
    if not eligible:
        return {"status": "not_observed", "run_id": None, "run_attempt": None,
                "conclusion": None}
    latest = max(eligible, key=lambda row: (row["run_number"], row["run_attempt"]))
    return {"status": latest["status"], "run_id": latest["id"],
            "run_attempt": latest["run_attempt"], "conclusion": latest.get("conclusion"),
            "url": latest.get("html_url")}


def version_slot(version: str, *, opener=urlopen) -> dict:
    url = f"{TESTPYPI_API}/json"
    try:
        with opener(url, timeout=30) as response:
            published = json.load(response)
    except HTTPError as error:
        if error.code != 404:
            raise
        return {"url": url, "project_absent": True, "version_available": True}
    if version in published["releases"]:
        raise ValueError("The requested Harness RC version already exists on TestPyPI")
    return {"url": url, "project_absent": False, "version_available": True}


def validate_target(*, sha: str, version: str, head: str, project: dict,
                    changelog: str, runs: dict, repository: str, opener=urlopen) -> dict:
    if not SHA.fullmatch(sha) or head != sha:
        raise ValueError("Rehearsal checkout must match the full reviewed SHA")
    if not RC.fullmatch(version):
        raise ValueError("TestPyPI rehearsal requires an exact rc version")
    if project.get("name") != PROJECT or project.get("version") != version:
        raise ValueError("Package metadata differs from the requested RC")
    if not re.search(r"^## " + re.escape(version) + r"(?:\s|$)", changelog, re.M):
        raise ValueError("The RC needs its own changelog heading")
    return {"schema_version": 1, "status": "provisional_rehearsal_preflight_passed",
            "commit": sha, "version": version, "target": "testpypi",
            "qualification": qualification_observation(runs, sha, repository),
            "testpypi": version_slot(version, opener=opener)}


def build_manifest(dist: Path, *, sha: str, version: str,
                   run_id: str, run_attempt: str) -> dict:
    if not SHA.fullmatch(sha) or not RC.fullmatch(version):
        raise ValueError("Invalid commit or RC version for artifact manifest")
    if not run_id.isdecimal() or not run_attempt.isdecimal():
        raise ValueError("Workflow run identity missing")
    paths = sorted(path for path in dist.iterdir() if path.is_file())
    wheel = [path for path in paths if WHEEL.fullmatch(path.name)
             and WHEEL.fullmatch(path.name).group("version") == version]
    sdist = [path for path in paths if SDIST.fullmatch(path.name)
             and SDIST.fullmatch(path.name).group("version") == version]
    if len(paths) != 2 or len(wheel) != 1 or len(sdist) != 1:
        raise ValueError("Exactly one RC wheel and one matching sdist are required")
    return {"schema_version": 1, "target": "testpypi", "project": PROJECT,
            "commit": sha, "version": version,
            "workflow_run_id": int(run_id), "workflow_run_attempt": int(run_attempt),
            "files": {path.name: {"sha256": sha256(path.read_bytes()).hexdigest(),
                                  "size": path.stat().st_size} for path in paths}}


def verify_manifest(manifest: dict, dist: Path, *, sha: str, version: str,
                    run_id: str, run_attempt: str) -> None:
    if (type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1
            or manifest.get("target") != "testpypi" or manifest.get("project") != PROJECT
            or manifest.get("commit") != sha or manifest.get("version") != version
            or manifest.get("workflow_run_id") != int(run_id)
            or manifest.get("workflow_run_attempt") != int(run_attempt)):
        raise ValueError("Artifact manifest differs from exact workflow identity")
    expected = build_manifest(dist, sha=sha, version=version,
                              run_id=run_id, run_attempt=run_attempt)
    if manifest != expected:
        raise ValueError("Distribution bytes differ from build manifest")


def release_files(manifest: dict, payload: dict) -> dict:
    if payload.get("info", {}).get("name", "").lower().replace("_", "-") != PROJECT:
        raise ValueError("TestPyPI JSON project differs from build")
    if payload["info"]["version"] != manifest["version"]:
        raise ValueError("TestPyPI JSON version differs from build")
    urls = payload.get("urls", [])
    expected = manifest["files"]
    if len(urls) != 2 or {row.get("filename") for row in urls} != set(expected):
        raise ValueError("TestPyPI file inventory differs from exact build")
    for row in urls:
        name = row["filename"]
        if (row.get("digests", {}).get("sha256") != expected[name]["sha256"]
                or row.get("size") != expected[name]["size"]):
            raise ValueError("TestPyPI file metadata differs from exact build")
        parsed = urlparse(row.get("url", ""))
        if (parsed.scheme != "https" or parsed.netloc != "test-files.pythonhosted.org"
                or Path(parsed.path).name != name):
            raise ValueError("TestPyPI file URL is not the expected file host")
    return {row["filename"]: row["url"] for row in urls}


def fetch(manifest: dict, output: Path, *, opener=urlopen,
          attempts: int = 8, delay: float = 15.0) -> dict:
    if output.exists():
        raise ValueError("Fresh download directory already exists")
    if manifest.get("target") != "testpypi":
        raise ValueError("Download manifest target is not TestPyPI")
    url = f"{TESTPYPI_API}/{manifest['version']}/json"
    files = None
    for index in range(attempts):
        try:
            with opener(url, timeout=30) as response:
                payload = json.load(response)
                if len(payload.get("urls", [])) >= 2:
                    files = release_files(manifest, payload)
        except HTTPError as error:
            if error.code != 404:
                raise
        if files is not None:
            break
        if index < attempts - 1:
            time.sleep(delay)
    if files is None:
        raise ValueError("TestPyPI release not visible after bounded polling")
    output.mkdir()
    hashes = {}
    for name, file_url in files.items():
        with opener(file_url, timeout=60) as response:
            redirected = urlparse(response.geturl())
            if (redirected.scheme != "https"
                    or redirected.netloc != "test-files.pythonhosted.org"):
                raise ValueError("TestPyPI file redirect changed host")
            data = response.read(manifest["files"][name]["size"] + 1)
        if (len(data) != manifest["files"][name]["size"]
                or sha256(data).hexdigest() != manifest["files"][name]["sha256"]):
            raise ValueError("Downloaded distribution differs from build")
        (output / name).write_bytes(data)
        hashes[name] = sha256(data).hexdigest()
    return {"schema_version": 1, "status": "exact_download_verified",
            "target": "testpypi", "commit": manifest["commit"],
            "version": manifest["version"], "files_sha256": hashes,
            "workflow_run_id": manifest["workflow_run_id"],
            "workflow_run_attempt": manifest["workflow_run_attempt"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--runs", type=Path, required=True)
    preflight.add_argument("--output", type=Path, required=True)
    manifest = sub.add_parser("manifest")
    manifest.add_argument("--dist", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify-local")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--dist", type=Path, required=True)
    download = sub.add_parser("fetch")
    download.add_argument("--manifest", type=Path, required=True)
    download.add_argument("--output", type=Path, required=True)
    download.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        import tomllib  # The release workflow uses Python 3.12; guard tests support 3.10.

        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
            raise ValueError("Rehearsal checkout must be clean before building")
        receipt = validate_target(
            sha=os.environ["RELEASE_SHA"], version=os.environ["RELEASE_VERSION"], head=head,
            project=tomllib.loads(Path("pyproject.toml").read_text())["project"],
            changelog=Path("CHANGELOG.md").read_text(),
            runs=json.loads(args.runs.read_text()), repository=os.environ["GITHUB_REPOSITORY"],
        )
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "preflight.json").write_text(json.dumps(receipt, indent=2) + "\n")
    elif args.command == "manifest":
        value = build_manifest(args.dist, sha=os.environ["RELEASE_SHA"],
                               version=os.environ["RELEASE_VERSION"],
                               run_id=os.environ["GITHUB_RUN_ID"],
                               run_attempt=os.environ["GITHUB_RUN_ATTEMPT"])
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    elif args.command == "verify-local":
        verify_manifest(json.loads(args.manifest.read_text()), args.dist,
                        sha=os.environ["RELEASE_SHA"], version=os.environ["RELEASE_VERSION"],
                        run_id=os.environ["GITHUB_RUN_ID"],
                        run_attempt=os.environ["GITHUB_RUN_ATTEMPT"])
    else:
        value = fetch(json.loads(args.manifest.read_text()), args.output)
        args.receipt.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
