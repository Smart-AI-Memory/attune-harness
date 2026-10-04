# Shepherd

Say **“Shepherd #222”** to ask the agent to bring that pull request to a verified
merge under the repository's existing rules.

- **Outcome:** the named PR is merged and verified, or a specific blocker is reported.
- **Autonomy:** perform authorized preparation, review coordination, checks and merge
  without asking again for routine steps.
- **Stop:** an unresolved failure, conflict or missing authority prevents progress.
- **Proof:** report the tested head, merge commit, matching tree and actual cleanup
  status, with the evidence in the PR.

Use the existing [repository rules](../../AGENTS.md) and
[merge helper](../../scripts/merge_when_green.sh) for the mechanics. After an
interruption, inspect current state before continuing.

**Example:** [“Shepherd #221”](https://github.com/Smart-AI-Memory/attune-harness/pull/221)
led the agent to wait for all checks, investigate and resolve an incorrect review
finding, then merge and verify the result. Its PR retains the receipt.
