#!/usr/bin/env bash
# Merge one pull request by squash once every check on its head has settled
# green, pinned to that head, then confirm main's tree is the tested tree and
# delete the branch only after the API reports it merged. This is the merge
# gate AGENTS.md describes, as a script.
#
#   scripts/merge_when_green.sh <number> [expected head sha prefix]
#
# With a second argument, wait until the API shows that head first, so a
# just-pushed commit is what gets checked.
#
# Exit 0 merged; 1 a check failed; 2 the branch is behind main, conflicts, or
# its head moved while waiting (update it, then run again); 3 gave up waiting:
# no workflow run appeared for the head (push a commit, or close and reopen
# the pull request), or the deadline passed; 4 merged, but main's tree
# differs from the tested head's.
#
# MERGE_WAIT_SECONDS bounds the whole wait (default 3600); MERGE_RUN_GRACE_SECONDS
# bounds how long a head may go without any workflow run (default 300);
# MERGE_POLL_SECONDS is the polling interval (default 15).
set -euo pipefail
number=${1:?pull request number}
expected=${2:-}
poll=${MERGE_POLL_SECONDS:-15}
start=$(date +%s)
deadline=$((start + ${MERGE_WAIT_SECONDS:-3600}))
grace=$((start + ${MERGE_RUN_GRACE_SECONDS:-300}))

view() { gh pr view "$number" --json "$1" --jq "$2"; }
give_up() { echo "#$number: $1" >&2; exit 3; }
tick() {
  (($(date +%s) < deadline)) || give_up "gave up waiting after ${MERGE_WAIT_SECONDS:-3600}s"
  sleep "$poll"
}

if [[ -n "$expected" ]]; then
  until [[ "$(view headRefOid .headRefOid)" == "$expected"* ]]; do tick; done
fi
head=$(view headRefOid .headRefOid)

# One line per check on the head: its name and a result, PENDING until it has
# one. Check runs and commit statuses report differently; both are folded in.
ROLLUP='.statusCheckRollup[]? | [(.name // .context),
  (if .__typename == "StatusContext" then (.state // "PENDING")
   elif .status == "COMPLETED" then (.conclusion // "PENDING") else "PENDING" end)] | @tsv'

while :; do
  # The head and its checks come from one read, so checks are never judged
  # against a head that moved in between.
  snapshot=$(view headRefOid,statusCheckRollup ".headRefOid, ($ROLLUP)")
  [[ "${snapshot%%$'\n'*}" == "$head" ]] \
    || { echo "#$number: the head moved from ${head:0:7} while waiting; run again" >&2; exit 2; }
  checks=$(tail -n +2 <<<"$snapshot")
  # Closing and reopening a pull request (AGENTS.md's remedy for a stale
  # Classify gate) cancels the duplicate run it starts on the same head. A
  # cancelled run is ignored when another run of that check is not cancelled;
  # a check whose only run was cancelled still fails.
  failed=$(awk -F'\t' '
    { name[NR] = $1; result[NR] = $2; if ($2 != "CANCELLED") rerun[$1] = 1 }
    END {
      for (i = 1; i <= NR; i++) {
        r = result[i]
        if (r == "SUCCESS" || r == "SKIPPED" || r == "NEUTRAL" || r == "PENDING") continue
        if (r == "CANCELLED" && rerun[name[i]]) continue
        print name[i] " (" r ")"
      }
    }' <<<"$checks")
  if [[ -n "$failed" ]]; then
    echo "#$number is not green at ${head:0:7}:" >&2
    printf '  %s\n' "$failed" >&2
    exit 1
  fi
  # The Qualification verdict job waits on the platform jobs (needs:), so its
  # check appears only when they finish; until then, keep waiting. A force-push
  # can leave a head with no workflow run at all (#191), and then nothing will
  # ever appear: stop after the grace if the head has no run.
  if ! grep -q $'^Qualification\t' <<<"$checks"; then
    if [[ "$(gh run list --commit "$head" --json databaseId --jq length)" == 0 ]]; then
      (($(date +%s) < grace)) \
        || give_up "no workflow run for head ${head:0:7}; push a commit, or close and reopen the pull request"
    fi
    tick; continue
  fi
  grep -q $'\tPENDING$' <<<"$checks" || break
  tick
done

# A release branch carries two Qualification runs (push and pull request); any
# number of successes is fine once nothing has failed, which the loop proved.
while :; do
  case "$(view mergeStateStatus .mergeStateStatus)" in
    CLEAN | HAS_HOOKS) break ;;
    BEHIND) echo "#$number is behind main: update the branch, then run again" >&2; exit 2 ;;
    DIRTY) echo "#$number conflicts with main" >&2; exit 2 ;;
    *) tick ;;  # BLOCKED, UNKNOWN or UNSTABLE right after the checks settle
  esac
done

title=$(view title .title)
[[ -n "${title// /}" ]] || { echo "#$number has an empty title; refusing an empty squash subject" >&2; exit 1; }
gh pr merge "$number" --squash --match-head-commit "$head" --subject "$title (#$number)" >/dev/null
until [[ "$(view state .state)" == MERGED ]]; do tick; done

merged=$(view mergeCommit .mergeCommit.oid)
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
tree() { gh api "repos/$repo/commits/$1" --jq .commit.tree.sha; }
# Equal only because branch protection requires the head to be up to date with
# main, so the squash of an up-to-date head is that head's tree.
if [[ "$(tree "$merged")" != "$(tree "$head")" ]]; then
  echo "#$number merged as ${merged:0:7}, but its tree differs from the tested head ${head:0:7}" >&2
  exit 4
fi

branch=$(view headRefName .headRefName)
# The repository deletes the head branch on merge; this covers a repository that does not.
git push origin --delete "$branch" >/dev/null 2>&1 || true
if [[ "$(git branch --show-current 2>/dev/null)" == "$branch" ]]; then
  git switch --detach -q  # a branch cannot be deleted while it is checked out
fi
git branch -D "$branch" >/dev/null 2>&1 || true
echo "#$number merged as ${merged:0:7} at tested head ${head:0:7} (same tree); branch $branch deleted"
