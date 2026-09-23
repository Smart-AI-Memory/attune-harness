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
comment=${2:-"Approved under Patrick's per-release authorization, recorded in the session"}
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
environment=$(gh api "repos/$repo/environments/pypi" --jq .id)
reply=$(mktemp)
python3 -c 'import json,sys; print(json.dumps({"environment_ids":[int(sys.argv[1])],"state":"approved","comment":sys.argv[2]}))' "$environment" "$comment" \
  | gh api -X POST "repos/$repo/actions/runs/$run/pending_deployments" --input - > "$reply"
python3 - "$reply" <<'PY'
import json, sys
reply = json.load(open(sys.argv[1]))
entries = reply if isinstance(reply, list) else [reply]
names = [str((e.get("environment") or {}).get("name")) for e in entries]
if not names:
    raise SystemExit(f"approval returned no environment: {reply!r}")
print("approved:", ", ".join(names))
PY
