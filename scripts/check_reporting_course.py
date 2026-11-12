"""Exercise the published reporting lesson with an exact wheel in a fresh folder."""

import argparse
import hashlib
from html import unescape
import json
import os
from pathlib import Path
import platform
import re
import subprocess
from zipfile import ZipFile

from build_help import build_site


COURSE = Path(__file__).resolve().parents[1] / "training/reporting"
CHECKPOINT = "replace-with-your-full-preview-digest"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def code_blocks(source):
    return [unescape(block) for block in re.findall(r"<pre><code(?: [^>]*)?>(.*?)</code></pre>", source, re.S)]


def check_course(wheel, expected_digest, output):
    require(digest(wheel) == expected_digest, "Wheel does not match the supplied SHA-256")
    output.mkdir()
    help_site = output / "help-site"
    build_site(help_site)
    start = (help_site / "harness/help/get-started/index.html").read_text(encoding="utf-8")
    practice_section = start.split('<h2 id="set-up-the-practice-folder">', 1)[1].split('<h2 ', 1)[0]
    setup, = code_blocks(practice_section)
    lesson_dir = COURSE / "02-build"
    copies = {
        copy["label"]: copy["text"]
        for section in load(lesson_dir / "lesson.json")["sections"]
        for copy in section.get("copies", [])
    }
    require(list(copies.values()) == code_blocks((lesson_dir / "read.html").read_text(encoding="utf-8")),
            "Interactive copy commands differ from the reading view")

    bundle = output / "bundle"
    bundle.mkdir()
    archive_path = COURSE / "assets/reporting-practice.zip"
    with ZipFile(archive_path) as archive:
        for name in archive.namelist():
            source = COURSE / name
            require(not Path(name).is_absolute() and ".." not in Path(name).parts
                    and source.resolve().is_relative_to(COURSE) and source.is_file(),
                    f"Unexpected ZIP member {name}")
            data = archive.read(name)
            require(data == source.read_bytes(), f"ZIP member differs from source: {name}")
            destination = bundle / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as member:
                member.write(data)

    constraint = output / "constraint.txt"
    constraint.write_text(f"attune-harness @ {wheel.as_uri()}\n", encoding="utf-8")
    env = dict(os.environ, UV_CONSTRAINT=str(constraint), UV_NO_PROGRESS="1",
               ATTUNE_USAGE_PING="0", ATTUNE_VERSION_CHECK="0", PYTHONDONTWRITEBYTECODE="1",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)

    def run(label, command, *, expected=(0,)):
        result = subprocess.run(["bash", "-ec", command], cwd=bundle, env=env,
                                text=True, capture_output=True, timeout=240)
        (output / f"{label}.out").write_text(result.stdout, encoding="utf-8")
        (output / f"{label}.err").write_text(result.stderr, encoding="utf-8")
        require(result.returncode in expected, f"{label} exited {result.returncode}; see {output}")
        return result.stdout

    run("setup", setup)
    env.pop("UV_CONSTRAINT")
    env["UV_OFFLINE"] = "1"
    activate = 'COURSE_WORK="$(pwd -P)"\n. .venv/bin/activate\n'
    practice = bundle / "practice"
    project = practice / "project"
    run("prepare", activate + copies["practice setup"])
    prepared = load(practice / "prepared.json")
    require(prepared["accepted"] is False and prepared["build_started"] is False
            and not (practice / "task").exists(), "Preparation created or accepted a saved task")
    protected = {name: digest(project / name) for name in prepared["protected"]}
    seats = load(project / "participants.json")["participants"]
    require(len(protected) == 7 and set(seats) == {"lead", "reviewer"} and
            all(seat["adapter"] == "command" and seat["tools"] == [] for seat in seats.values()),
            "Practice must protect seven inputs and use the two fixed local seats")

    resume = activate + 'PRACTICE="$COURSE_WORK/practice"\n'
    preview = json.loads(run("preview", resume + copies["plan preview"], expected=(0, 1)))
    checkpoint = preview["checkpoint_digest"]
    require(preview["status"] == "draft" and preview["questions"]["missing"] == []
            and re.fullmatch(r"[0-9a-f]{64}", checkpoint), "Preview did not return a ready draft")
    accept = json.loads(run("accept", resume + copies["scope acceptance"].replace(CHECKPOINT, checkpoint)))
    require(accept["status"] == "accepted" and accept["checkpoint_digest"] != checkpoint,
            "Scope acceptance did not advance the checkpoint")
    built = json.loads(run("build", resume + copies["offline build"]))
    require(built["status"] == "completed", "Build did not complete")
    record = load(Path(built["record_path"]))
    events = {event["operation_key"]: event for event in record["build"]["events"]}
    checks = {}
    for name in ("probe:change", "probe:final"):
        result = events[name]["result"]
        require(result["passed"] and result["returncode"] == 0
                and re.search(r"\b77 passed\b", result["stdout"]), f"{name} did not pass 77 cases")
        checks[name] = 77
    status = run("status", resume + copies["saved task inspection"])
    require(all(f"**{name}:** Passed" in status for name in checks), "Status omitted the passing probes")
    run("report", resume + copies["report command"])
    actual_report = practice / "activity-report.html"
    require(actual_report.read_bytes() == (project / "expected/activity-report.html").read_bytes(),
            "The report differs from the expected HTML")
    require(all(digest(project / name) == before for name, before in protected.items()),
            "A protected file changed")
    changed = subprocess.check_output(["git", "status", "--porcelain"], cwd=project, text=True)
    require(changed.splitlines() == [" M report.py"], f"Unexpected project changes: {changed!r}")

    runtime = json.loads(run("runtime", activate + """python - <<'PY'
import importlib.metadata as metadata
import json
import platform
harness = metadata.distribution("attune-harness")
print(json.dumps({"harness": harness.version, "pytest": metadata.version("pytest"),
    "python": platform.python_version(), "source": json.loads(harness.read_text("direct_url.json"))}))
PY
"""))
    require(runtime.pop("source")["url"] == wheel.as_uri() and runtime["harness"] == prepared["runtime"],
            "The practice environment did not use the selected wheel")
    return {
        **runtime,
        "platform": f"{platform.system()} {platform.machine()}",
        "wheel_sha256": expected_digest,
        "practice_zip_sha256": digest(archive_path),
        "report_sha256": digest(actual_report),
        "protected_files_unchanged": len(protected),
        "changed_files": ["report.py"],
        "passing_cases": checks,
        "model_calls": 0,
        "status": built["status"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True, type=Path, help="New directory for evidence")
    args = parser.parse_args()
    output = args.output.resolve()
    result = check_course(args.wheel.resolve(), args.sha256, output)
    evidence = json.dumps(result, indent=2) + "\n"
    (output / "result.json").write_text(evidence, encoding="utf-8")
    print(evidence, end="")


if __name__ == "__main__":
    main()
