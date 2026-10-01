#!/usr/bin/env bash
# Prepare a different-model review under docs/review-brief.md: a read-only
# archive of the branch, its diff against the base, and a mutation-table
# scaffold, all outside the working tree so the reviewer never reads a tree
# another session may switch. Usage: scripts/review_prep.sh <branch> [base]
# The base defaults to origin/main; the diff is taken from the merge base.
# REVIEW_PREP_DIR chooses where the directory is made (default: $TMPDIR).
set -euo pipefail
branch=${1:?usage: scripts/review_prep.sh <branch> [base]}
base=${2:-origin/main}
root=$(git rev-parse --show-toplevel)
head=$(git -C "$root" rev-parse --verify --quiet "$branch^{commit}") \
  || { echo "review_prep: no such commit: $branch" >&2; exit 1; }
fork=$(git -C "$root" merge-base "$base" "$head")
short=$(git -C "$root" rev-parse --short "$head")
out=$(mktemp -d "${REVIEW_PREP_DIR:-${TMPDIR:-/tmp}}/review-$short.XXXX")
mkdir "$out/tree"
git -C "$root" archive --format=tar "$head" | tar -x -C "$out/tree"
git -C "$root" diff "$fork" "$head" > "$out/changes.diff"
git -C "$root" diff --stat "$fork" "$head" > "$out/changes.stat"
{
  echo "# Mutation table for $branch at $short (base $(git -C "$root" rev-parse --short "$fork"))"
  echo
  echo "One row per guard the change adds, moves or relies on: remove or invert it"
  echo "in a copy of the tree and run the tests. A mutation no test catches is a"
  echo "finding. Fill the table before the review and paste it into the pull request."
  echo
  echo "| # | Mutation (what is removed or inverted) | Where | Tests that fail | Caught |"
  echo "|---|---|---|---|---|"
  n=0
  while IFS= read -r file; do
    n=$((n + 1))
    echo "| M$n |  | \`$file\` |  |  |"
  done < <(git -C "$root" diff --name-only "$fork" "$head" -- src)
  [[ $n -eq 0 ]] && echo "| M1 |  | (no file under src/ changed) |  |  |"
} > "$out/mutations.md"
# The reviewer writes the report here as well as returning it, so a lost
# hand-back does not lose the review (2026-09-30 retro, item 9).
: > "$out/report.md"
# One mutant per call, in its own full copy of the tree. pyproject's pytest
# `pythonpath = ["src"]` resolves against the rootdir, so a mutated src/ is
# imported only when pytest runs from inside the copy; PYTHONPATH alone does
# not override it (2026-09-30 retro, item 7).
cat > "$out/mutate.sh" <<'MUTATE'
#!/usr/bin/env bash
# Usage: mutate.sh NAME FILE OLD NEW [pytest args...]
# Copies tree/ to mutants/NAME, replaces OLD with NEW in FILE exactly once, and
# runs pytest from inside the copy with $PYTHON (default python3). Prints
# CAUGHT when the tests fail and SURVIVED when they pass. Exit 2 if OLD is not
# found exactly once. Mutate only guards inside the tree: a mutant that drops a
# home-directory or path-root guard can reach outside it.
set -euo pipefail
name=${1:?mutant name}; file=${2:?file in the tree}; old=${3?text to replace}; new=${4?replacement}
shift 4
here=$(cd "$(dirname "$0")" && pwd)
copy="$here/mutants/$name"
rm -rf "$copy"
mkdir -p "$here/mutants"
cp -R "$here/tree" "$copy"
"${PYTHON:-python3}" - "$copy/$file" "$old" "$new" <<'PY' || exit 2
import sys
path, old, new = sys.argv[1:4]
text = open(path, encoding='utf-8').read()
if text.count(old) != 1:
    sys.exit(f'{old!r} occurs {text.count(old)} times in {path}; a mutant needs exactly one')
open(path, 'w', encoding='utf-8').write(text.replace(old, new))
PY
if (cd "$copy" && "${PYTHON:-python3}" -m pytest -q -p no:cacheprovider "$@" > "$copy.log" 2>&1); then
  echo "$name SURVIVED ($(tail -1 "$copy.log"))"
else
  echo "$name CAUGHT ($(tail -1 "$copy.log"))"
fi
MUTATE
chmod +x "$out/mutate.sh"
echo "review of $branch at $short against $(git -C "$root" rev-parse --short "$fork") ($base)"
echo "  tree:      $out/tree"
echo "  diff:      $out/changes.diff"
echo "  mutations: $out/mutations.md, run each with $out/mutate.sh"
echo "  report:    $out/report.md (the reviewer writes it as well as returning it)"
echo "  brief:     $root/docs/review-brief.md, then docs/windows-traps.md"
echo "changed:"
sed 's/^/  /' "$out/changes.stat"
