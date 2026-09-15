# Checks, handoffs and repair economics

These interfaces produce reviewable decisions. They make no model calls and do
not modify GitHub or dispatch an agent.

## GitHub

Fetch check results for the exact commit being reviewed using your existing GitHub
CLI sign-in, then import the saved response:

```sh
gh api 'repos/OWNER/REPO/commits/FULL_SHA/check-runs?per_page=100' > checks.json
attune-harness github-checks checks.json --repository OWNER/REPO --revision FULL_SHA
```

Quote the API path in shells that expand `?`. If `total_count` exceeds the returned
array length, the importer rejects the response: collect all pages and combine
their `check_runs` arrays with the correct `total_count` first. The caller supplies
the repository and exact SHA and is responsible for authenticated retrieval.
This command is not a webhook endpoint. Unknown, skipped and neutral conclusions
do not establish success. A timeout requires reconciliation of possible effects.
All exported checks passing still does not prove all required checks were present.

The parser uses check app identity and name in its deduplication key. It does not
infer a code defect from a failed GitHub check; a trusted diagnosis must distinguish
test, infrastructure and unknown failures before proposing a repair team.

The adapter was exercised against this repository's real Actions results during
qualification: running checks produced `wait`, successful checks produced `observe`,
and the initial Windows test failure produced `human_review`, with zero model calls.

## Deterministic triage

`attune-harness triage-check event.json` accepts:

```json
{
  "event": {
    "repository": "example/project",
    "revision": "accepted-revision",
    "check": "unit-tests",
    "run_id": "run-1",
    "status": "failed",
    "failure_kind": "test",
    "effects": "none",
    "attempts": 0
  },
  "handled_keys": [],
  "max_attempts": 2
}
```

The two-attempt cap here is an example operator policy. Suggestions distinguish
waiting, passed checks, duplicate events, reconciliation, infrastructure review,
repair-team proposals and human review. The key spans repeated runs of the same
check at one revision. An executor must atomically claim/persist the key and bind
its accepted scope before dispatch; this pure function is not a durable queue.
LLM log summaries are advisory and cannot override trusted check status.

## Cost per verified repair

`attune-harness repair-economics ledger.json` totals each repair's initial attempt,
retries and escalations under one strategy. Each verified repair requires an
independent passing check and an evidence digest. A completed worker is insufficient.
Every row records model cost, checking cost, human minutes and hourly rate. Missing
values are `null`; missing costs prevent price ranking. Recorded USD values are
operator/provider attestations, not prices inferred from model names.

Only strategies meeting the supplied quality floor and complete cost accounting
appear in `eligible_cost_ranking`. Tokens include failed attempts; reasoning tokens
are already part of output tokens. This is a comparison among eligible strategies,
not certification that an excluded or unmeasured strategy is worse.

See `tests/test_operations.py` for a complete synthetic ledger with a failed initial
attempt and a verified escalation. The qualification campaign writes a real measured
token ledger for synthetic configuration repairs, leaving unavailable USD and human
costs null. It does not establish economics for production code repair.
