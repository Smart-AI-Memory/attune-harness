# Harness release journey map

Latest: the [connected capability map](specs/connected-journey-qualification/capability-map.md)
and [qualification results](connected-journey-qualification-results.md) add the
bound repair-to-test edge and the installed executor-led Spec journey. The
evidence below remains the earlier follow-through baseline.

2026-09-17. First task of the approved [follow-through plan](../.claude/plans/release-readiness-follow-through.md).
This maps executable behavior and gaps; it does not approve or implement the
separate plan/build draft. Existing capabilities remain intact.

## The connected journey

| Step | Current implementation | Evidence and boundary |
|---|---|---|
| Human goal and acceptance | `task_cli.py`, `task_contract.py`: goal intake freezes inputs and binds an explicit accepted response to task, revision, participants, permissions and evidence | Current intake tests; acceptance alone is distinct from execution |
| Assessment | `task_policies.py`, `task_runtime.py`: durable verification, retrieval and correlated participant assignments | Current assessment tests; completed narratives remain unverified, including disagreement |
| Scoped repair | `repair.py`, `task_policies.py`: failed baseline, worker proposal, host-applied existing-file replacement, passing probe and bound review | Actual command-peer CLI fixture starts `fix --goal ... --accept`, pauses and resumes; verified only within the frozen probe's scope |
| Inspection and recovery | `task_cli.py`, `recovery.py`: read-only status, journaled operations, checkpoint-bound resume and explicit reconciliation | Current recovery tests cover every boundary, replay without duplicate calls/writes and uncertain effects |
| Human Spec controls | Attune AI `spec/workspace.py`, `spec/state.py`: approval, task gates, progress and saved state | 60 current baseline checks. Workspace delegates work to the lead; it does not implement Harness plan/build |

The primary Harness verbs are `review`, `fix`, `status`, `resume`. The legacy
catalog remains available through `--help-all`; compatibility checks preserve its
18 commands. The portable library `run()/Check/Receipt` API is a separate execution
surface from the durable CLI. Native participant transport reuses `Task` and
`JsonParticipant.run()`, but CLI integration owns its own acceptance record.

## Current central evidence

- [Qualified profile suite](receipts/release-readiness-follow-through/journey-qualified-profile.txt):
  **149 passed** across task contract, assessment, repair, recovery and compatibility.
  Python 3.12.13, Forms 0.17.0, Verify **0.6.0**, RAG 1.2.0 in the existing
  `.venv-voyage312` environment; synthetic participants, no provider campaign.
- [CLI observations](receipts/release-readiness-follow-through/journey-cli.json):
  normal and complete help succeed; `plan --help` and `build --help` exit 2 because
  those commands are absent.
- [Spec baseline](receipts/release-readiness-follow-through/spec-baseline.txt):
  **60 passed**; [AI preflight](receipts/release-readiness-follow-through/ai-preflight.txt):
  **87 passed**, two disclosed pre-existing dirty-tree warnings.
- [Independent source/test map](receipts/release-readiness-follow-through/independent-journey-map.json)
  is passive advice, not an executed suite. The [central hash report](receipts/release-readiness-follow-through/journey-map-hash-check.json)
  verifies its 29 files and corrects one 63-character hash transcription error.
- The [initial wrong-profile run](receipts/release-readiness-follow-through/journey-checks.txt)
  produced 79 failures and 70 passes using AI's installed Verify 0.6.1. Harness
  correctly rejected that version. The 149-pass rerun uses its declared 0.6.0;
  these are not 79 independent product defects. Patrick explicitly endorsed using
  the available qualified version. Fresh installation must resolve it explicitly.

## Concrete gaps and implications

1. **Goal → prompt/XML/spec → plan/build is not implemented.** The
   [plan/build tasks](specs/plan-build/tasks.md) are an eight-task, non-executable
   scoping draft. No authoring-tier selector, plan/build parser, accepted-spec
   import, planning/build policy or new-file effect profile is implemented.
   `--plan solo|independent-review` selects collaboration policy. It is not a
   human plan verb. These are blockers for a release promising the complete
   feature-building journey, rather than reasons to remove current features.
2. **The ordinary review CLI's continuous journey gap is now closed.** After
   completing the three-task ladder, Patrick's next-opportunity authorization
   funded one additional test: actual `review --goal ... --accept` → pause →
   status → resume → completed replay, with two synthetic Python command peers.
   It passes against source and the fresh installed wheel; status changes neither
   task state nor calls, each participant runs once, and the task identity stays
   constant. Narrative semantics remain explicitly unverified. The
   [separate follow-up receipt](receipts/release-readiness-follow-through/review-cli-followup.json)
   does not retroactively change the earlier 149/146-check suite totals.
3. **Spec completion loses accepted task evidence.** The
   [two-task reproduction](receipts/release-readiness-follow-through/terminal-before.json)
   completes both tasks but shows neither execution proof; saved state also omits
   them. Task 2 has now [repaired and verified this behavior](spec-completion-repair-results.md)
   in the candidate; the active installed plugin remains unchanged.
4. **Fresh combined installation is now qualified for macOS/Python 3.12.**
   Task 3 [resolved and exercised](fresh-installation-results.md) Harness `[review]`
   with AI `[harness]`, preserving Verify 0.6.0. AI's MCP 1.29.1 profile is distinct from Harness `[mcp]`'s 2.2.0 profile;
   combining those mutually exclusive pins is not a supported installation claim.
5. **Native reliability/economics and other host platforms remain separate.**
   The unified-task verification document still marks its broad native Task 8
   unaccepted. Historical narrow corrections do not qualify the whole product.

Attune AI's Spec runner delegates task implementation to the lead and wraps
quality enforcement; `PipelineOrchestrator` explicitly does not implement tasks.
The current repair profile supports existing regular UTF-8 files in a dedicated
checkout; it cannot create/delete/rename files or stand in for feature building.

## Next steering checkpoint

The shared summary repair and fresh installation now have passing execution
evidence. Patrick wants to pursue logged opportunities next. Prioritize documented Harness
release blockers and shared value; retain deferred access-separation and native
activation boundaries. This map supplies the evidence for selecting that next
bounded journey; it is not an aggregate release-readiness verdict.
