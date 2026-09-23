#!/bin/bash
# Approve the pypi environment for one publish run, under the per-release
# authorization Patrick gives in words ("approve the deployment for me"), which
# the comment records. Usage: release_approve.sh <run id> ["comment"].
#
# The response to the approval POST is a list of environment objects, not an
# object. Reading it with `--jq` as an object raised a parse error after the
# approval had succeeded, twice; this script reads the file it saved instead.
set -euo pipefail
run=${1:?usage: release_approve.sh <run id> [comment]}
case "$run" in ''|*[!0-9]*) echo "run id must be a number: $run" >&2; exit 2;; esac
comment=${2:-"Approved under Patrick's per-release authorization, recorded in the session"}
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
environment=$(gh api "repos/$repo/environments/pypi" --jq .id)
reply=$(mktemp)
trap 'rm -f "$reply"' EXIT
python3 -c 'import json,sys; print(json.dumps({"environment_ids":[int(sys.argv[1])],"state":"approved","comment":sys.argv[2]}))' "$environment" "$comment" \
  | gh api -X POST "repos/$repo/actions/runs/$run/pending_deployments" --input - > "$reply"
python3 - "$reply" <<'PY'
import json, sys
reply = json.load(open(sys.argv[1]))
entries = reply if isinstance(reply, list) else [reply]
names = [
    name for entry in entries if isinstance(entry, dict)
    for name in [((entry.get("environment") or {}).get("name"))] if name
]
if not names:
    raise SystemExit(f"approval reply names no environment; treat the approval as unknown: {reply!r}")
print("approved:", ", ".join(names))
PY
