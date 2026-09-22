# Task 8 — bounded response-contract correction

The completed native screen accepted 1/24 original replies. The retained
diagnostics establish two interface defects: criterion coverage requires hidden
duplicate strings, and worker `task_id` ambiguously means an accepted step while
the native transport instructs models not to copy control identifiers. Three
worker sources also fail the real CLI oracle; those are separate code defects.

This local correction is covered by the existing Task 8 authorization. It makes
no native calls and does not accept Task 8. The original comparison, prompts,
grades and failed outputs remain frozen.

## Design before source changes

- Give newly created planning/build journals response-contract version 2.
  Missing version means the original contract. Retain the original prompt bytes
  and decoding behavior when reconstructing old journal events, including resume
  and historical records. Unknown versions fail. Version changes on populated
  journals must invalidate their request-digest binding.
- New worker replies contain only schema version 2 and scoped file proposals.
  The host binds step identity and dependencies from the accepted dispatch after
  validating the response envelope. It retains file scope, preimage and evidence
  checks. Legacy version-1 replies remain accepted only with their exact original
  step/dependency checks; ambiguous old replies are not silently repaired.
  For modified files, supply the accepted preimage hash literally in the worker's
  output template; a model without hashing tools must not calculate SHA-256 from
  source prose. The host still independently checks that hash and current bytes.
- New plans retain exact criterion-to-task coverage and substantive task checks.
  The host derives the duplicate accepted-criterion checks when staging the next
  draft. Validate coverage before deriving anything, preserve the raw reply, and
  never infer semantic correctness from that binding.
- Use separate planner/critic and worker/reviewer instructions and schemas. Tell
  planners the supported ordered build constraints: nonempty outputs, one producer
  per file, preceding-step dependency and no reserved `final` step. Required tests
  belong in task checks and protected probes, not outputless build steps. Validate
  those restrictions using the build owner's existing rules.
- Reserve unresolved choices for material intent, scope, compatibility or authority
  decisions. Routine implementation alternatives stay in notes with a selected
  working approach. The host continues to preserve real unresolved human choices;
  it does not suppress them using a keyword heuristic.

## Evidence, checks and limits

Already-run scratch diagnostics appended only bound criterion strings: 11/12
plans then validated structurally. Worker diagnostics changed only copied IDs
and extra envelope notes: nine sources passed the complete CLI oracle and three
failed. All nine completed runs rejected a later source change. These are retained
diagnostics, not successful original native responses.

Before declaring this correction locally qualified, replay the retained payloads
with explicitly labeled v2 projections; preserve rejection of wrong goals, unknown
or omitted criteria, foreign tasks, scope/preimage changes and extra authority.
Exercise actual staging, build effects, protected tests and stale handoffs. Reopen
legacy completed/paused records without re-dispatch and reject version tampering.
Run appropriate source and isolated-wheel regressions plus isolated guard removal.

Rejected alternatives: deleting validation would weaken the evidence boundary;
silently fixing rejected native replies would misstate results; upgrading every
existing journal would break its bound request; adding a stronger router would
spend model work on host-owned metadata. A fresh native comparison still needs a
separate concrete allocation. Startup isolation and provider-turn accounting stay
in the opportunity log for that next comparison; they do not require credential
or installed-integration changes in this correction.
