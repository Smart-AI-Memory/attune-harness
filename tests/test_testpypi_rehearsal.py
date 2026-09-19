"""Offline RC routing and artifact provenance; never contacts an index."""

import copy
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location(
    "testpypi_rehearsal",
    Path(__file__).resolve().parents[1] / "scripts/check_testpypi_rehearsal.py",
)
rehearsal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearsal)


class Response(io.BytesIO):
    def __init__(self, data, url="https://test-files.pythonhosted.org/packages/example"):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


def candidate():
    sha = "a" * 40
    return {
        "sha": sha, "version": "0.1.0rc1", "head": sha,
        "project": {"name": "attune-harness", "version": "0.1.0rc1"},
        "changelog": "# Changelog\n\n## 0.1.0rc1 — publishing rehearsal\n",
        "runs": {"workflow_runs": [{
            "id": 123, "head_sha": sha, "event": "push",
            "head_repository": {"full_name": "Smart-AI-Memory/attune-harness"},
            "run_number": 9, "run_attempt": 2, "status": "completed",
            "conclusion": "failure", "html_url": "https://github.test/actions/123",
        }]},
        "repository": "Smart-AI-Memory/attune-harness",
    }


def absent(*args, **kwargs):
    raise HTTPError(args[0], 404, "fixture", None, None)


def test_rc_preflight_records_non_green_qualification_without_upgrading_it():
    value = rehearsal.validate_target(**candidate(), opener=absent)
    assert value["status"] == "provisional_rehearsal_preflight_passed"
    assert value["qualification"]["run_id"] == 123
    assert value["qualification"]["run_attempt"] == 2
    assert value["qualification"]["conclusion"] == "failure"
    data = candidate()
    data["runs"] = {"workflow_runs": []}
    assert rehearsal.validate_target(**data, opener=absent)["qualification"]["status"] == "not_observed"


@pytest.mark.parametrize("change", ["sha", "final", "metadata", "changelog", "occupied", "unavailable"])
def test_rc_preflight_rejects_wrong_target_or_index_state(change):
    data = candidate()
    opener = absent
    if change == "sha":
        data["head"] = "b" * 40
    elif change == "final":
        data["version"] = "0.1.0"
        data["project"]["version"] = "0.1.0"
    elif change == "metadata":
        data["project"]["version"] = "0.1.0rc2"
    elif change == "changelog":
        data["changelog"] = "## 0.1.0rc2"
    elif change == "occupied":
        def opener(*args, **kwargs):
            return Response(json.dumps({"releases": {"0.1.0rc1": []}}).encode())
    else:
        def opener(*args, **kwargs):
            raise HTTPError(args[0], 503, "unavailable", None, None)
    with pytest.raises((ValueError, HTTPError)):
        rehearsal.validate_target(**data, opener=opener)


def distributions(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "attune_harness-0.1.0rc1-py3-none-any.whl").write_bytes(b"wheel bytes")
    (dist / "attune_harness-0.1.0rc1.tar.gz").write_bytes(b"sdist bytes")
    manifest = rehearsal.build_manifest(dist, sha="a" * 40, version="0.1.0rc1",
                                        run_id="77", run_attempt="2")
    return dist, manifest


def test_exact_two_distribution_manifest_and_changed_bytes(tmp_path):
    dist, manifest = distributions(tmp_path)
    rehearsal.verify_manifest(manifest, dist, sha="a" * 40, version="0.1.0rc1",
                              run_id="77", run_attempt="2")
    with pytest.raises(ValueError, match="identity"):
        rehearsal.verify_manifest(manifest, dist, sha="a" * 40, version="0.1.0rc1",
                                  run_id="78", run_attempt="2")
    (dist / "attune_harness-0.1.0rc1.tar.gz").write_bytes(b"substituted")
    with pytest.raises(ValueError, match="bytes"):
        rehearsal.verify_manifest(manifest, dist, sha="a" * 40, version="0.1.0rc1",
                                  run_id="77", run_attempt="2")
    (dist / "extra.txt").write_text("unexpected")
    with pytest.raises(ValueError, match="Exactly"):
        rehearsal.build_manifest(dist, sha="a" * 40, version="0.1.0rc1",
                                 run_id="77", run_attempt="2")


def test_testpypi_file_inventory_host_hash_and_redirect_reject(tmp_path):
    _, manifest = distributions(tmp_path)
    urls = []
    for name, data in manifest["files"].items():
        urls.append({"filename": name, "size": data["size"],
                     "digests": {"sha256": data["sha256"]},
                     "url": "https://test-files.pythonhosted.org/packages/" + name})
    payload = {"info": {"name": "attune-harness", "version": "0.1.0rc1"}, "urls": urls}
    assert set(rehearsal.release_files(manifest, payload)) == set(manifest["files"])
    bad = copy.deepcopy(payload)
    bad["urls"][0]["url"] = bad["urls"][0]["url"].replace("https:", "http:")
    with pytest.raises(ValueError, match="URL"):
        rehearsal.release_files(manifest, bad)
    bad = copy.deepcopy(payload)
    bad["urls"][0]["digests"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="metadata"):
        rehearsal.release_files(manifest, bad)
    contents = {name: (tmp_path / "dist" / name).read_bytes() for name in manifest["files"]}

    def opener(url, timeout):
        if url.endswith("/json"):
            return Response(json.dumps(payload).encode(), url)
        name = url.rsplit("/", 1)[-1]
        return Response(contents[name], url)

    result = rehearsal.fetch(manifest, tmp_path / "download", opener=opener, attempts=1)
    assert result["status"] == "exact_download_verified"
    assert {path.name for path in (tmp_path / "download").iterdir()} == set(manifest["files"])
    with pytest.raises(ValueError, match="exists"):
        rehearsal.fetch(manifest, tmp_path / "download", opener=opener, attempts=1)

    def redirected(url, timeout):
        if url.endswith("/json"):
            return Response(json.dumps(payload).encode(), url)
        name = url.rsplit("/", 1)[-1]
        return Response(contents[name], url.replace("https:", "http:"))

    with pytest.raises(ValueError, match="redirect"):
        rehearsal.fetch(manifest, tmp_path / "redirected", opener=redirected, attempts=1)


def test_workflow_keeps_production_final_and_testpypi_rc_routes_separate():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/publish-pypi.yml").read_text()
    production = (root / "scripts/check_release_candidate.py").read_text()
    assert "if: inputs.publish && inputs.target == 'pypi'" in workflow
    assert "if: inputs.publish && inputs.target == 'testpypi'" in workflow
    assert "environment: pypi" in workflow and "environment: testpypi" in workflow
    assert "repository-url: https://test.pypi.org/legacy/" in workflow
    assert "gh api \"repos/$GITHUB_REPOSITORY/environments/testpypi\"" in workflow
    assert '[[ "$GITHUB_SHA" == "$RELEASE_SHA" ]]' in workflow
    assert workflow.count("PIP_CONFIG_FILE: /dev/null") == 2
    assert "--isolated --disable-pip-version-check install --no-cache-dir --index-url https://pypi.org/simple/" in workflow
    assert "This publication path requires a final release version" in production
    assert "check_release_candidate.py" in workflow
