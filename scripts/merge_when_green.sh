#!/usr/bin/env bash
# Merge one pull request by squash once every check has settled green, then
# delete its branch only after the API reports it merged. This is the merge
# gate AGENTS.md describes, as a script.
#
#   scripts/merge_when_green.sh <number> [expected head sha prefix]
#
# With a second argument, wait until the API shows that head first, so a
# just-pushed commit is what gets checked. Exit 2 when the branch is behind
# main or conflicts (update it, then run again); exit 1 when a check failed.
set -euo pipefail
number=${1:?pull request number}
expected=${2:-}

view() { gh pr view "$number" --json "$1" --jq "$2"; }

if [[ -n "$expected" ]]; then
  until [[ "$(view headRefOid .headRefOid)" == "$expected"* ]]; do sleep 10; done
fi

gh pr checks "$number" --watch --fail-fast >/dev/null 2>&1 || true

while :; do
  state=$(view mergeStateStatus .mergeStateStatus)
  case "$state" in
    CLEAN) break ;;
    BEHIND) echo "#$number is behind main: update the branch, then run again" >&2; exit 2 ;;
    DIRTY) echo "#$number conflicts with main" >&2; exit 2 ;;
    *) sleep 20 ;;
  esac
done

unsettled=$(view statusCheckRollup '[.statusCheckRollup[]? | select((.conclusion // "") != "SUCCESS" and (.conclusion // "") != "SKIPPED")] | length')
verdict=$(view statusCheckRollup '[.statusCheckRollup[]? | select(.name == "Qualification" and .conclusion == "SUCCESS")] | length')
if [[ "$unsettled" != 0 || "$verdict" != 1 ]]; then
  echo "#$number is not green: $unsettled check(s) not passed, Qualification passed=$verdict" >&2
  exit 1
fi

title=$(view title .title)
gh pr merge "$number" --squash --subject "$title (#$number)" >/dev/null
until [[ "$(view state .state)" == MERGED ]]; do sleep 5; done
branch=$(view headRefName .headRefName)
# The repository deletes the head branch on merge; this covers a repository that does not.
git push origin --delete "$branch" >/dev/null 2>&1 || true
git branch -D "$branch" >/dev/null 2>&1 || true
echo "#$number merged as $(view mergeCommit '.mergeCommit.oid[0:7]'); branch $branch deleted"
