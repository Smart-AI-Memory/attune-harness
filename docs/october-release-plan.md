# October release and complete-journey plan

Prepared September 18, 2026, for Patrick's **October 1, 9 a.m. Eastern** reminder.
This plans the release and complete-journey group from the
[opportunity log](opportunity-log.md), plus C's experiment safeguards needed
before another paid trial. The reminder replaces the September 25 review.
It does not start implementation, activate an installation or authorize spending.

## Outcome and budget

Connect the remaining intended journeys, verify their supported installations
and recovery paths, and prepare an evidence-backed release candidate. Preserve
useful capabilities and original experiment grades. Report unresolved work
explicitly rather than declaring the release complete because a budget is used.

**Recommended additional budget: 270,000 working tokens**, comprising **225,000
for planned work and 45,000 for rework**. This is a proposed allocation, not an
accurate prediction or a user-approved spending cap. We have no measured
per-phase token baseline that would justify a precise completion forecast.

The earlier release estimate was 140–265k before contingency, or 175–330k with
contingency. Adding C's previously estimated 15–25k gives a broad **190–355k**
planning range with contingency. The 270k proposal sits within that range; it
is not evidence that the uncertainty has narrowed.

“Working tokens” retains the earlier planning meaning: assistant reasoning,
relevant inspection, edits, verification and documentation. It is not a forecast
of provider-billed input/output tokens or account usage percentages. Repeated
context, caching and model choice can change those quantities. Fresh paid worker
calls and their credits are estimated separately once cases and models are fixed.

## Phased work

Targets below sum to 225k. They include focused verification and documentation.
Phases follow dependencies; finishing one does not add a new routine approval
gate. Existing Spec, spending, publication and activation requirements still apply.

| Phase | Work and completion evidence | Target |
|---|---|---:|
| 1. Refresh the baseline | Check current code, candidate worktrees, accepted results and installed versions. Refresh the capability map and identify exact remaining callers, package profiles and release criteria. Remove completed work from the estimate and revise each remaining phase. | 10k |
| 2. Prepare the verified Spec repair for rollout | Locate the accepted source, reconcile intervening changes, package it and verify accepted-result display, old saved plans, resume and rollback. Prepare the concrete deployment change; active rollout follows existing authorization. | 15k |
| 3. Qualify packaging and installations | Resolve availability of the optional Spec owner. Exercise clean installs and actual outside-tree callers for the intended macOS/Linux/Windows profiles, with optional dependencies absent and restored. Keep incompatible MCP profiles separate. Record unsupported behavior explicitly. | 35k |
| 4. Repair specialist testing backends | Trace the retained maintenance, generation, verifier, alias and write-contract defects. Fix actual caller/result/effect boundaries while preserving useful specialist routes. Prove failures, empty discovery and scope violations cannot become successful results. | 45k |
| 5. Complete handoffs | Connect assessment findings to bounded repair and the existing test/Spec owners; consolidate shared terminal evidence validation where needed. Exercise stale evidence, preserved completed work, failure, interruption and recovery through actual installed entry points. | 35k |
| 6. Complete C before fresh trials | Check reference delivery and all model-visible inputs for leaked answers. Reuse grader context, known bad artifacts and the no-model launcher check. Demonstrate rejection of the retained contaminated fixture without changing its original grades. | 20k |
| 7. Qualify native journeys | Freeze cases for live memory delegation and plan/build repair/retest/resume, final review and a genuinely new user requirement. Prepare a separate call/credit estimate. After authorized dispatch, retain every result and test completion against the unchanged criteria. A failed trial remains a failure with remaining work reported. | 50k |
| 8. Prepare and verify the release | Run applicable release checks, reconcile the full documentation set, publish accurate support limits and prepare package/version/rollback instructions. Execute publication and activation only under their existing authorization, then verify the installed artifact. | 15k |
| **Planned work** | | **225k** |
| **Rework allowance** | Unexpected compatibility, integration or qualification corrections; not an allocation for repeatedly trying native calls until green. | **45k** |
| **Recommended total** | | **270k** |

Phase 2 supplies the candidate for phase 3. Local integration in phases 4–5 and
the clean-input checks in phase 6 precede phase 7. Phase 8 uses their evidence.
The first concrete milestone is phases 1–2, targeting **25k**, leaving a refreshed
estimate and a verified, reviewable Spec rollout candidate.

## What could change the estimate

- The current [installed plan/build profile](plan-build-task7-results.md) is a
  bounded POSIX chain. A clean Windows installation does not prove Windows
  feature execution. If the intended journey requires new platform support,
  scope and estimate that work explicitly; do not hide it in installation checks.
- The [Spec repair](spec-completion-repair-results.md) and
  [fresh macOS installation](fresh-installation-results.md) already have evidence.
  Reuse it, check intervening changes and avoid reconstructing completed work.
- Specialist backends and native journey failures carry the greatest uncertainty.
  Local correctness alone cannot guarantee fresh model reliability or cost.
- Phase 5 may share work with D's review-to-builder handoff or F's evidence
  inspection. Count shared changes once. D and F as complete opportunity groups
  remain separately deferred unless explicitly included in the revised scope.

At each phase closeout, record completed scope, available token-usage evidence,
remaining work and the revised forecast in the existing work record. If actual
per-task token usage is unavailable, say so; do not substitute account percentages
or worker credits. Surface an expected overrun when discovered, before assuming
the additional work is affordable. Preserve completed work if Patrick defers more.

## Boundaries and October 1 reminder

A/B's separate 25–40k estimate is excluded; check their actual completion on
October 1 rather than assuming they shipped. E's function-body integration,
general performance work, ownership/sharing changes, optional AI packaging
cleanup and blog/website publication remain on the deferred list. This estimate
does not promise completion of every opportunity in that list.

On October 1, present this plan and the complete deferred groups, distinguish the
proposed 270k allocation from measured usage, and check the available allotment
before proposing the next step. The date is a reminder to review the plan, not an
automatic work start. Blog integration still requires Patrick's content approval.
Use the [documentation maintenance checklist](documentation-maintenance.md)
during the full documentation review.
