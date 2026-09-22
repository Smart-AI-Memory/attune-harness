#!/usr/bin/env bash
# Run the full test suite from a snapshot of HEAD, with the CI extras, so the
# working tree stays free for other work while it runs. Extra arguments go to
# pytest. Takes about a minute to build the environment plus the suite.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
snapshot=$(mktemp -d "${TMPDIR:-/tmp}/attune-harness-suite.XXXXXX")
git -C "$root" archive --format=tar HEAD | tar -x -C "$snapshot"
cd "$snapshot"
python3 -m venv .venv
.venv/bin/python -m pip install -q -c requirements-workflow.lock -c requirements-voyage.lock \
  -c requirements-mcp.lock "pytest==9.1.1" -e ".[review,voyage,mcp]"
echo "suite from $(git -C "$root" rev-parse --short HEAD) in $snapshot"
.venv/bin/python -m pytest -q -p no:cacheprovider tests "$@"
