"""``scripts/merge_when_green.sh``, the merge gate, driven against a fake ``gh``.

Each case scripts what the GitHub API shows, one frame per poll, and checks
what the gate does: waits, refuses, or merges pinned to the head it read and
confirms main's tree is that head's. Found by the 2026-09-30 retro's audit: the
gate hung on a red pull request and on a head with no workflow run, merged
unpinned, never compared trees, and refused a release pull request's two
Qualification runs.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "merge_when_green.sh"
HEAD, MERGED = "a" * 40, "b" * 40

pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None or shutil.which("jq") is None,
    reason="the gate is a bash script, and the fake gh evaluates --jq with jq",
)

# A fake gh: `pr view` answers from the current frame (the frame advances on
# each statusCheckRollup read), `pr merge` records its arguments and flips the
# state, `repo view` and `api .../commits/SHA` answer from the state file.
FAKE_GH = r'''
import json, subprocess, sys
from pathlib import Path
state_path = Path(sys.argv[0]).with_name("state.json")
state = json.loads(state_path.read_text())
args = sys.argv[1:]

def jq(value, query):
    out = subprocess.run(["jq", "-r", query], input=json.dumps(value), capture_output=True, text=True, check=True)
    sys.stdout.write(out.stdout)

if args[:2] == ["pr", "view"]:
    fields, query = args[args.index("--json") + 1].split(","), args[args.index("--jq") + 1]
    if "statusCheckRollup" in fields:
        state["reads"] = state.get("reads", 0) + 1
    index = min(max(state.get("reads", 0) - 1, 0), len(state["frames"]) - 1)
    frame = {"title": "Fix the gate", "headRefName": "fix/gate", "state": "OPEN",
             "mergeCommit": None, **state["frames"][index]}
    if state.get("merged"):
        frame.update(state="MERGED", mergeCommit={"oid": state["merged"]})
    jq({field: frame.get(field) for field in fields}, query)
elif args[:2] == ["pr", "merge"]:
    state["merge_args"] = args
    state["merged"] = state["merge_commit"]
elif args[:2] == ["repo", "view"]:
    print("owner/repo")
elif args[0] == "api":
    sha = args[1].rsplit("/", 1)[1]
    jq({"commit": {"tree": {"sha": state["trees"][sha]}}}, args[args.index("--jq") + 1])
else:
    sys.exit(f"fake gh: unexpected {args}")
state_path.write_text(json.dumps(state))
'''


def check(name, conclusion="SUCCESS"):
    status = "IN_PROGRESS" if conclusion is None else "COMPLETED"
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion}


def frame(*checks, merge_state="CLEAN", head=HEAD):
    return {"headRefOid": head, "mergeStateStatus": merge_state, "statusCheckRollup": list(checks)}


def run_gate(tmp_path, frames, *, trees=None, extra_args=(), wait=30, grace=30):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "fake_gh.py").write_text(FAKE_GH, encoding="utf-8")
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{bin_dir / "fake_gh.py"}" "$@"\n', encoding="utf-8")
    gh.chmod(0o755)
    state = {"frames": frames, "merge_commit": MERGED, "trees": trees or {HEAD: "t1", MERGED: "t1"}}
    (bin_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "MERGE_POLL_SECONDS": "0",
           "MERGE_WAIT_SECONDS": str(wait), "MERGE_RUN_GRACE_SECONDS": str(grace)}
    result = subprocess.run(["bash", str(SCRIPT), "17", *extra_args], cwd=repo, env=env,
                            capture_output=True, text=True, timeout=60)
    return result, json.loads((bin_dir / "state.json").read_text(encoding="utf-8"))


def test_merges_pinned_to_the_head_it_read_and_confirms_the_tree(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("Qualification", None), check("CodeQL")),
                                        frame(check("Qualification"), check("CodeQL"))])
    assert result.returncode == 0, result.stderr
    assert state["merge_args"][state["merge_args"].index("--match-head-commit") + 1] == HEAD
    assert state["merge_args"][state["merge_args"].index("--subject") + 1] == "Fix the gate (#17)"
    assert "same tree" in result.stdout


def test_a_failed_check_exits_one_instead_of_waiting(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("Qualification", None), check("CodeQL", "FAILURE"),
                                              merge_state="BLOCKED")])
    assert result.returncode == 1 and "CodeQL (FAILURE)" in result.stderr, result.stderr
    assert "merge_args" not in state


def test_a_head_with_no_qualification_run_gives_up_after_the_grace(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("CodeQL"), merge_state="BLOCKED")], grace=0)
    assert result.returncode == 3 and "no Qualification check" in result.stderr, result.stderr
    assert "close and reopen" in result.stderr and "merge_args" not in state


def test_a_qualification_check_that_registers_late_is_waited_for(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("CodeQL"), merge_state="BLOCKED"),
                                        frame(check("CodeQL"), check("Qualification"))])
    assert result.returncode == 0, result.stderr
    assert "merge_args" in state


def test_two_qualification_successes_merge_a_release_pull_request(tmp_path):
    result, _ = run_gate(tmp_path, [frame(check("Qualification"), check("Qualification"))])
    assert result.returncode == 0, result.stderr


def test_the_deadline_ends_a_wait_that_never_settles(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("Qualification", None), merge_state="BLOCKED")], wait=0)
    assert result.returncode == 3 and "gave up waiting" in result.stderr, result.stderr
    assert "merge_args" not in state


def test_a_head_that_moves_while_waiting_stops_the_gate(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("Qualification", None)),
                                        frame(check("Qualification"), head="c" * 40)])
    assert result.returncode == 2 and "head moved" in result.stderr, result.stderr
    assert "merge_args" not in state


def test_behind_main_exits_two(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("Qualification"), merge_state="BEHIND")])
    assert result.returncode == 2 and "behind main" in result.stderr, result.stderr
    assert "merge_args" not in state


def test_a_merged_tree_that_differs_from_the_tested_head_exits_four(tmp_path):
    result, _ = run_gate(tmp_path, [frame(check("Qualification"))], trees={HEAD: "t1", MERGED: "t2"})
    assert result.returncode == 4 and "tree differs" in result.stderr, result.stderr


def test_an_expected_head_is_waited_for_first(tmp_path):
    result, state = run_gate(tmp_path, [frame(check("Qualification"))], extra_args=("aaaa",))
    assert result.returncode == 0, result.stderr
