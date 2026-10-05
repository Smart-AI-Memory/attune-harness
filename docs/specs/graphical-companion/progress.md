# GUI program progress

**Approved release boundary (October 5):** GUI delivery is deferred to 1.4.0.
The 1.3.0 candidate refuses module launch/server construction before task,
listener or browser effects; internal experimental GUI code remains inert.
The progress/receipts below describe development, not available 1.3.0 features.
M2/M3/M4 gates remain; full M2 implementation is not required for the bounded
non-GUI 1.3.0 candidate. S3/S6/S9 observations remain open for explicit disposition,
not closed by GUI deferral. October 6–11 publication needs an explicit decision;
October 12 remains the scope review, with no automatic M3.

Contract: four milestones approved; preserve and integrate existing journeys.
Baseline: origin/main bd517064507bac1264b0dbf01287837b25b4df0c.

- M1: discovery/specification checkpoint complete. Sixteen journey rows, reuse
  inventory, architecture, command-owner walk and preservation gate recorded.
- M2: first increment implemented: `python -m attune_harness.gui --task PATH`
  serves existing owner-rendered snapshots behind a loopback capability boundary.
  Multiple explicit task directories are supported. It has no write/action endpoint.
- M3/M4: not started. The M2 read-only increment merged in #219; the overall
  GUI is not production-ready. Merge status is distinct from qualification.
- Completion review: complete for M1 and the bounded read-only M2 increment;
  private review notes retained. The larger milestone remains in progress.

## Verified

Existing-owner source checks: 203 passed in the platforms environment; two MCP
checks failed there because MCP was absent. All 21 workspace MCP checks passed
in the existing environment with the pinned SDK. The first generic-interpreter
attempt also lacked forms, and two collection attempts named nonexistent files;
these were setup errors, not passing evidence. No environment was upgraded.

New companion: 11 focused tests pass. They cover real owner rendering, unchanged
records, denied writes, missing/wrong capabilities, foreign Host/Origin, arbitrary
path refusal, invalid refreshed records and registration limits.

Browser: six checks passed against a disposable real Harness owner: opening a
briefing, removing the capability from the address bar, reload/reconnect, explicit
refresh, 360/1100px outer layout and no JavaScript errors. An initial srcdoc anchor
navigation failure was corrected by using bounded blob snapshots. The owner
renderer supplies content; the companion does not infer completion.

## Not verified

Full suite, wheel/install qualification, Windows GUI,
new native runs, screen-reader audit and real-user usability remain open.
No prior prototype result is relabeled as production qualification. This increment
uses private task_view style/script constants to preserve its CSP hashes; review
that seam before widening the interface. Clipboard behavior inside the sandboxed
snapshot frame is not qualified; select-and-copy remains available.

## Next

Complete packaging/full-suite checks for this increment, then
bind intake and decisions to existing owners. Preserve the prototype interaction
inventory and refusal tests. Experiment 23 identity and model-selection evidence
remain separate pending work; neither is silently replaced with a new trial.

## Qualification repair

The documentation index now includes both specification files. A different-model
review (requested GPT-6 Astra, high reasoning) inspected the original source at
e6e7c1c and the final source delta. It approved this bounded read-only increment
after two corrections: authenticated manual/browser-failure launch instructions,
and non-ASCII invalid session headers returning 403 rather than raising TypeError.
The reviewer independently ran all 15 companion tests and a real loopback probe.

Reviewed source SHA-256: c9e9eca7d79b5466e4396379b3e1463b64ebea3c55b05680c7824fe8c1675d2e.
Reviewed test SHA-256: 5cc26eb9b3dbe3a4c45f350172f49573f6a345486bdea08fd57cbd55ca4ae056.
Documentation links and 15 focused tests passed locally. The attempted full local
suite stopped during collection because the selected environment lacks requests;
no dependency was added to a retained environment. The fresh CI run is required
for complete-suite/platform status. Approval is not production readiness.

## Delivery sequence

The [project plan](../../project-plan.md#delivery-phases) owns scheduling around
the publication hold: stabilize/observe, prepare 1.3.0, review on October 12,
complete M2, broaden through M3, then qualify M4. The first two phases permit
bounded M2 work without displacing defects or release acceptance. M3 needs the
scope review and M2 exit evidence. Prior verification entries above are historical
receipts, not claims about final CI or a subsequently published artifact.

Completion review: complete for phase alignment; no new GUI execution evidence.
The next user-facing evidence is a voluntary installed walkthrough. Preliminary
feedback is recorded in the project plan without claiming S6 completion.

Parallel-work clarification: release preparation starts now, while publication
remains held. One stabilization/release effort and one GUI effort can proceed
alongside voluntary user feedback. This is scheduling, not a claim that workers
have been dispatched. Check accessibility, security and recovery per increment;
M4 remains the final candidate qualification. Completion review: complete for
this clarification; it resolves sequencing ambiguity without adding a new gate
or opportunity log entry.


## M2: existing-draft intake and decisions

The second bounded increment adds explicit `--edit` mode to the same local
companion. The default remains read-only. Registered feature-work drafts can
complete missing goal/scope/acceptance, material questions and choices, save
partial responses, inspect the owner-selected review, reconsider, and accept
intent. Opening a form is an explicit write; GET inspection remains read-only.
Each response is bound to the exact live decision and checkpoint. No request
can select an arbitrary path, launch a participant, or invoke build. Restart,
a replaced decision or an uncertain submission requires inspection and reopening.

Forty focused tests pass against real owners. The independent GPT-6 Astra review
found a stale-refresh warning that could be overwritten by success; the fix is
re-reviewed and five deterministic JavaScript regression probes pass. The tests
now join installed-platform qualification. Full-suite and wheel qualification
are recorded in the pull request before this increment is ready for merge.

Browser verification exercises partial intake, full option wording, remaining
questions, readable intent review, reconsideration, explicit acceptance and
retained state. Chrome renders the existing owner snapshot; Codex's embedded
browser leaves its blob frame blank while the new controls work. The page gives
an explicit Chrome fallback. This is a remaining embedded-browser qualification
gap, not a platform-completion claim.

New-task creation, build dispatch/recovery controls, the shared author gallery,
M3 research/memory/opportunity execution and M4 accessibility/user/platform
qualification remain separate increments. Earlier prototypes and receipts are
preserved. Completion review for this increment is retained with the PR handoff.

## M2: accepted command build and evidence

This bounded increment adds `--edit --allow-build-commands`. Registered accepted
feature work can preview its commands, tasks, effects, protected checks and budgets,
then separately grant the full build. One background worker runs the existing
build owner while HTTP inspection remains available. Plain launch remains
read-only, and `--edit` alone cannot dispatch a build.

The GUI shows saved progress, checks and final reviewer findings. A fresh preview
and grant can resume eligible saved work with its original authority. Stale or
replayed grants, changed inputs, terminal outcomes and uncertain dispatched
operations refuse execution. Closing the page does not cancel an operation;
normal shutdown waits for the owner, and restart neither restores grants nor
dispatches automatically. There are no GUI pause/cancel/reconciliation controls.

Command adapters are allowed; native/provider adapters are refused. Commands are
not network-sandboxed, so the operational mode is not described as guaranteed
offline. `tests/test_gui_build.py` uses the installed-journey subprocess peer for
the real offline chain, with protected probes and retained review evidence. Its
cases cover duplicate/replaced grants, drift, responsive inspection, paused
resume, lost acknowledgements, consistent evidence revisions and high findings.
The final build reviewer is not J06's standalone document/corpus assessment.

Local validation passes: 61 focused GUI tests, 3,979 full-suite tests plus five
subtests (53 skipped), and 2,150 installed-wheel tests (nine skipped). Wheel build,
metadata checks, dependency checks and core-only installation pass. Independent
GPT-6 Astra source and task-card delta reviews found no remaining material issue.
Two evidence/completion races found during review are covered by regressions.

The Codex browser exercised the real offline command fixture: preview, explicit
grant, polling to completed checks/reviewer evidence, and reload/inspection without
a new dispatch. The task card and result now agree after completion. Its existing
snapshot frame remains blank with an explicit fallback; Claude content/interactions,
Windows CI for this head, accessibility and real-user acceptance remain unverified.
New-task creation, standalone assessment, the shared author gallery, M3 and final
M4 qualification remain open. Completion review is retained in the PR handoff;
this increment does not complete M2.
