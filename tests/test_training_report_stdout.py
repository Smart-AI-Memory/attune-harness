"""Check the report CLI's exact bytes under a legacy output encoding."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


EXAMPLE = Path(__file__).resolve().parents[1] / "training/reporting/assets/example"
SAMPLE = EXAMPLE / "data/activity.csv"


def run_report(tmp_path, source, *options):
    environment = {
        "PATH": str(Path(sys.executable).parent),
        "PYTHONIOENCODING": "cp1252:strict",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in ("SystemRoot", "WINDIR"):
        if name in os.environ:
            environment[name] = os.environ[name]
    return subprocess.run([
        sys.executable, "-B", str(EXAMPLE / "report.py"), str(source),
        *(str(option) for option in options),
    ], cwd=tmp_path, env=environment, capture_output=True, timeout=3, check=False)


@pytest.mark.parametrize(("options", "golden"), [
    ((), "activity-report.txt"),
    (("--format", "text"), "activity-report.txt"),
    (("--format", "html"), "activity-report.html"),
], ids=["default-text", "explicit-text", "html"])
def test_report_stdout_matches_exact_utf8_lf_fixture_under_cp1252(tmp_path, options, golden):
    result = run_report(tmp_path, SAMPLE, *options)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout == (EXAMPLE / "expected" / golden).read_bytes()


def test_report_stdout_preserves_unicode_labels_under_cp1252(tmp_path):
    source = tmp_path / "activity.csv"
    source.write_bytes("date,project,category,minutes\n2026-10-19,東京,Ωμέγα,7\n".encode("utf-8"))
    result = run_report(tmp_path, source)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout == (
        "Project activity report\nEntries: 1\nTotal minutes: 7\n\n"
        "By project\n- 東京: 7\n\nBy category\n- Ωμέγα: 7\n"
    ).encode("utf-8")


@pytest.mark.parametrize(("format_name", "golden"), [
    ("html", "activity-report.html"),
    ("text", "activity-report.txt"),
])
def test_unicode_output_path_has_utf8_lf_confirmation_and_unchanged_file(tmp_path, format_name, golden):
    output = tmp_path / f"résumé 東京.{format_name}"
    result = run_report(tmp_path, SAMPLE, "--format", format_name, "--output", output)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout == f"Saved report to {output}\n".encode("utf-8")
    assert output.read_bytes() == (EXAMPLE / "expected" / golden).read_bytes()
