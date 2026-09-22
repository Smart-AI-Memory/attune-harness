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
echo "review of $branch at $short against $(git -C "$root" rev-parse --short "$fork") ($base)"
echo "  tree:      $out/tree"
echo "  diff:      $out/changes.diff"
echo "  mutations: $out/mutations.md"
echo "  brief:     $root/docs/review-brief.md, then docs/windows-traps.md"
echo "changed:"
sed 's/^/  /' "$out/changes.stat"
