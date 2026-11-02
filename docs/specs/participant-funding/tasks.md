# Implement participant funding after approval

**Status: specification and D1–D3 approved on November 2, 2026; T1 discovery and
T2 software verification complete. The API-first revision is approved. T3/T4
candidate implementation and T5 verification are in progress; final review remains open.
Live provider calls remain subject to separately authorized spending scope.**
November 2, 2026. Requirements and the complete review are in the
[specification](README.md). Patrick directed execution to start with T1.
Each source change requires the repository's different-model review before
merge; a review covers only the commit/delta it examined.

## T1: qualify child-only funding selection

Discovery complete in the [support matrix](t1-support-matrix.md). Six final
offline witnesses and 57 existing process/preflight tests pass. Version-bound
Codex source supports a conditional API route; invocation-level enforcement for
the installed subscription routes remains unqualified. Peer evidence review
findings are resolved. This is not live-provider or Windows qualification.

Scope: verify documented native authentication precedence and supported CLI
versions, without a model call or credential mutation. Identify every helper,
backend and managed setting relevant to the supported local routes. Define how
subscription and API modes enforce their route at invocation, including whether
the status command sees an exec-only override. Use inert executable witnesses for
the software contract. Do not make a live paid call to discover how it works.

Done when: a reviewable support matrix names exact versions, selected child
inputs, local evidence, enforcement and refusal cases for all three routes.
Unsupported combinations have a concrete refusal. If a route requires shared
login mutation, report the constraint to Patrick; do not widen scope. This task
is a dependency for T3, not permission to declare actual account access verified.

## T2: add the optional configuration policy

Candidate implemented: both configuration owners accept the approved policy
forms, bind them into existing contracts, and retain omitted legacy fields.
Selected explicit funding refuses before probes, dispatch journaling or native
execution until T3 admission is qualified. Direct callers receive the same
refusal. Forty-one focused cases pass, including actual review-form, task and
work freshness checks for funding-only changes.

The built candidate wheel passes the local installed-platform qualifier: no
failed/error test cases, successful plugin bootstrap, and the accepted
plan/build/review journey. All 112 installed Python modules match candidate
source bytes. The full source suite passes in two disjoint partitions: all 6,182
collected cases are accounted for. The installed run reports 3,421 passed, 201
skipped and two passing subtests. Both used the normal CI dependency profile;
the source runner used short canonical temporary paths and active output stayed
outside the checkout. Earlier failed/interrupted setup runs remain preserved.
The unrelated expanded
native-SDK argument failure also reproduces on unchanged main `069b9f0`.
Windows/Linux CI and different-model merge review are not claimed.

The source changes are in signed commit `cc8651431217fe78a61dbc35dff1a8f6f649346f`
on [draft PR #331](https://github.com/Smart-AI-Memory/attune-harness/pull/331).
Later changes to these status notes do not change the tested source or wheel.

Scope: a shared validator used by `review_contract.validate_registry` and
`consultation.configuration`, supporting R1 and R6. Add fragments and complete
validator fixtures for both formats; preserve provider/model identity rules and
existing digest binding. No changes to `init` defaults or saved configurations.

Done when: positive and negative cases pass in both owners; old registry,
consultation and saved-state compatibility fixtures remain valid; funding changes
make existing acceptance stale through the existing owners. Applies approved D1.

## T3: bind preflight, dispatch and API authorization

The [API-first revision](t3-decision.md) is approved. The candidate adds a separately
selected OpenAI API adapter, fresh spending flags, owner-bound admission before
dispatch, refusal history, normalized usage and readable views. Targeted tests
exercise actual consultation, assessment, planning and build owners with inert
requests. Final full-suite, installed-wheel, hosted platform and source-review
evidence remains to be recorded. This is not a claim of live account access.

Native activation prerequisite remains open: T1 did not establish a nonmutating
invocation-level subscription binding or a safe complete effective-policy
inspection for the conditional Codex API route. The approved revision uses a
direct API adapter instead; it does not relax this native limit. Do not replace that evidence with
a paid success trial or enable a validated policy through inherited auth.

Scope: `consultation_preflight`, `native`, both shared native callers and their
executing/resuming owners. Reuse `process.invoke(environment=...)`. Add the
optional API authorization flag/host argument in R4, without removing existing
gates. Persist per-attempt admission evidence through the existing owner before
launch; admission refusal cannot create a dispatched event that needs retry.
Check each call, including reviewers and resumed turns. Preserve unrelated
command environment policy and all effects/reconciliation rules.

Done when: A2–A4 witness tests cover every executing/resuming entry point and
both shared native paths; a direct explicitly funded library call cannot bypass
admission; mismatched/unknown funding launches no model; concurrent environments
stay independent. Update frozen CLI/envelope fixtures only for deliberate
additions with a changelog entry. Depends on T1 and T2; applies approved D2–D3.

## T4: retain and present funding and usage

Scope: normalized allowlisted native usage metadata, identity/result evidence,
owner validation and existing JSON/readable views. Reuse existing journals;
extend their size/schema checks deliberately. Bind evidence to the correct turn
and retain refusal, prelaunch, completed and uncertain cases. Remove secrets
from new funded process/error paths before saving; do not weaken reply parsing.

Done when: A5–A6 pass; sentinel secrets never appear in persisted records or
views; admission-write failure starts no process; malformed usage never becomes
zero cost; old records render without invented funding data. Depends on T3.

## T5: verify the installed journey and document limits

Scope: extend the existing installed CLI journeys through consultation and
registry workflows using inert native witnesses. Cover new and resumed turns,
rejected API approval, a changed funding contract and interrupted output.
Update the CLI guide, envelopes and supported-route matrix with observed limits.

Done when: focused tests, full suite, built wheel and installed platform checks
pass; hosted Windows results are read; recorded reviews cover final source
changes. These checks establish software behavior, not live billing or model
quality. Live provider qualification is a separately approved bounded follow-up
with explicit call estimates and retained receipts. Do not weaken old evidence or
regenerate frozen experiments to obtain a pass. Depends on T4.

## Completion boundary

Use one coherent implementation PR if it remains reviewable; split only at the
dependencies above. Do not expand this into routing, automatic fallback, a
financial ledger, provider purchasing or a credential migration. Report the
supported and unsupported combinations, unverified account/billing facts and
completion-review result. Patrick retains merge/release authority.
