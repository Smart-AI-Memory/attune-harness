# Ordered implementation tasks

**Status: proposed, non-executable until spec approval.** Checkboxes denote future
work, not current authorization. Planning documents are the only deliverable of
this phase. See [decisions D1–D5](README.md) and [requirements R1–R7](design.md).

## Sequence

T1 → T2 and T4 → T3 → T5. T4 can proceed independently after T1; integration
must consume each owning repository's merged work, never another agent's shared
checkout snapshot. Forms work gets its own branch/PR in Forms. No Forms code is
vendored into Harness. Use sequential PRs unless independent work is explicitly
assigned; maintainers own merges/releases under each repository's rules.

- [ ] **T1 — Lock the journey contract against current owners.**
  Owner: Harness. Requirements: R1/R3/R4; evidence: J2/J4. Scope:
  `tests/test_work_contract.py`, `tests/test_work_build.py`,
  `tests/test_task_view.py`, plus a proposed deterministic journey fixture/test.
  First recheck latest merged source and overlapping task-view work. Establish
  CSV intake, all-records→current-page correction, old-decision refusal,
  unchanged accepted handoff, unresolved effect and post-start correction cases.
  Use real owners and temporary local files; no live providers. Existing behavior
  tests should pass; missing presentation/adapter behavior remains explicitly
  pending rather than masked with a vacuous success test.
  Done when each baseline assertion has a named test or an evidence-backed gap,
  and accepted scope/permissions remain unchanged on read-only host handoff.
  Risk: low/medium; no production changes. Dependencies: approved decisions and
  fresh baseline. Estimate: one bounded verification/review increment.

- [ ] **T2 — Add explicit Forms host selection and fallback.**
  Owner: Forms. Requirements: R2. Scope: proposed
  `src/attune_forms/interaction_selection.py`, root exports, existing
  `conformance.py`, `host_question.py`, `renderer_registry.py`, relevant MCP
  configuration only if necessary, `stability.py`, tests and user documentation.
  Reuse existing renderers/validators; preserve the legacy router unchanged.
  Implement the decision shape/selection order from R2. Add only profiles backed
  by actual host evidence; test unknown/inadmissible profiles through portable or
  unsupported outcomes. Reconcile stability prose encountered by this API change.
  Done when every route preserves typed answers or refuses with an actionable
  reason, old callers pass, and the installed Forms wheel passes its conformance
  fixtures. Risk: medium (public API). Dependencies: T1 and approved R2 contract.
  Rollback: revert adoption/pin; no state migration. Estimate: one or two PRs.

- [ ] **T3 — Integrate the corrected-decision and handoff lifecycle.**
  Owner: Harness plus its host integration instructions. Requirements: R1–R5.
  Scope: proposed `src/attune_harness/journey_session.py` only if existing host
  helpers cannot supply the seam; `command_workspace.py`, `work_cli.py`,
  `task_continuation.py`, workflow skill/references and integration tests.
  Keep work_contract/work_runtime authoritative; changes there require a
  demonstrated baseline gap, not refactoring for this interface's convenience.
  Session seam: open by explicit task locator/capabilities, collect against a
  retained display binding, propose correction to the current checkpoint, and
  reopen/inspect. Route mutation to existing owner functions; keep session state
  ephemeral. Document exact host capability configuration and response mapping.
  Do not add workspace MCP execution support. Pin the released Forms addition
  and update required locks in this task, after separate release authorization.
  Done when correction persists before continuation, restart reads it, host
  switch alone never reaccepts, retries/cancellation obey R5, and broader
  post-effect edits visibly require new scope rather than mutating old evidence.
  Risk: high (authority integration). Dependencies: T1/T2, Forms release and D2.
  Rollback: remove new integration entry/pin; retain old records. Estimate:
  two independently reviewed increments (session seam, host instructions).

- [ ] **T4 — Add the outcome evidence summary.**
  Owner: Harness. Requirements: R6. Scope: `task_view.py`,
  `execution_evidence.py`, tests, CLI guide and existing return-to-work design
  notes only where needed for alignment. Implement one Inspect results action
  over existing record evidence; keep raw detail available below it. Avoid a
  second viewer or a new local server. Preserve default JSON and saved formats.
  Test verified/unverified criterion associations, historical scope, stale and
  failed checks, missing artifacts, hostile text and read-only behavior. Manually
  inspect keyboard/narrow-screen presentation before claiming usability.
  Done when one action opens the understandable summary and no unsupported
  completion claim or active arbitrary link is introduced. Risk: medium.
  Dependencies: T1 and coordination with task-opportunities presentation work.
  Rollback: restore previous rendering; no stored data rewrite. Estimate: one PR.

- [ ] **T5 — Observe and qualify named hosts.**
  Owners: integration maintainer and user observer. Requirements: R7 and all
  journey criteria. Scope: a new dated qualification report, redacted receipts,
  host-specific instructions and truthful qualification matrix. Begin with
  scripted seam tests, then actual installed host interaction. Run each host as
  both source and destination of at least one handoff in a Codex→Claude→
  Antigravity→Codex cycle, preserving the same saved task. Separately exercise
  cancellation, correction, native-inadmissible fallback and evidence opening on
  each. This cycle is bounded coverage, not proof of all host/version pairs.
  Done when each host's capabilities, versions, observations and limits are
  recorded; failures remain failures and unobserved cells remain unqualified.
  Risk: medium; external host availability. Dependencies: T2/T3/T4, installed
  artifacts, named observer, and separate approval for any paid calls. Estimate:
  one exploratory observation pass plus separately scoped fixes, if warranted.

## Acceptance matrix

| Case | Expected result | Primary task |
|---|---|---|
| Fully specified request | No question; explicit scope available to inspect | T1/T3 |
| One unresolved dimension | One semantic question; known facts retained | T1/T2/T3 |
| Native surface cannot carry form | Equivalent validated fallback or explicit unsupported | T2/T5 |
| Correction before acceptance | New effective intent/criteria, old revision retained | T1/T3 |
| Correction after acceptance | Old grant invalidated; only revised scope can be accepted | T1/T3 |
| Concurrent stale reply | Refused without task mutation | T1/T3 |
| Same-machine host switch | Current state loaded; unchanged acceptance retained | T3/T5 |
| Different accepted provider/config | Existing freshness/authorization gate applies | T1/T3 |
| Unresolved execution | Reconcile; no automatic replay | T1/T3 |
| Post-start wider correction | Existing journal retained; explicit successor scope | T3/T5 |
| Click Inspect results | Read-only summary, criterion coverage and limits visible | T4/T5 |
| Missing or stale supporting evidence | Unverified/stale, never manufactured success | T4 |

## Verification and handoff requirements

Every source PR requires its owner's targeted and full tests, an installed wheel
qualification where prescribed, and independent source review. Read Windows CI
results before claiming Windows support. Deterministic adapter tests do not
qualify a live host or a model's reasoning. Retain mutations/failure cases proving
that stale acceptance, question duplication, evidence mislabeling and replay are
detected. Use new temporary fixtures, never rewrite retained campaigns.

Each PR handoff lists requirements covered, exact package/source versions,
tests actually run, review findings, unsupported cases and how to resume. Any new
public compatibility surface needs deliberate fixture/changelog treatment under
the owning repository's policy. Do not silently expand scope to change platform
limits, release timing, provider choice or budget.

Before implementation, record approval of D1–D5 and selected tasks in this package
or the implementation task's direct user instructions. Discovering that a task
already exists closes/reduces it with primary evidence; it does not justify a
parallel replacement. Approval to implement still does not grant merge, publish,
force-push, workflow-dispatch or paid-call authority.
