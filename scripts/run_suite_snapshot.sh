#!/usr/bin/env bash
# Run the full test suite from a snapshot of HEAD, with the CI extras, so the
# working tree stays free for other work while it runs. Extra arguments go to
# pytest. Takes about a minute to build the environment plus the suite.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
snapshot=$(mktemp -d "${TMPDIR:-/tmp}/attune-harness-suite.XXXXXX")
git -C "$root" archive --format=tar HEAD | tar -x -C "$snapshot"
cd "$snapshot"
# One environment per set of lock files, kept between runs; the editable
# install is re-pointed at each snapshot, which is seconds once the
# dependencies are present.
key=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(b"".join(open(f,"rb").read() for f in sys.argv[1:])).hexdigest()[:16])' \
  requirements-workflow.lock requirements-voyage.lock requirements-mcp.lock requirements-tokens.lock requirements-redis.lock pyproject.toml)
venv="${TMPDIR:-/tmp}/attune-harness-suite-venv-$key"
[[ -x "$venv/bin/python" ]] || python3 -m venv "$venv"
"$venv/bin/python" -m pip install -q -c requirements-workflow.lock -c requirements-voyage.lock \
  -c requirements-mcp.lock -c requirements-tokens.lock -c requirements-redis.lock "pytest==9.1.1" -e ".[review,voyage,mcp,redis]"
echo "suite from $(git -C "$root" rev-parse --short HEAD) in $snapshot, environment $venv"
"$venv/bin/python" -m pytest -q -p no:cacheprovider tests "$@"
