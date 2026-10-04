# GUI program progress

Contract: four milestones approved; preserve and integrate existing journeys.
Baseline: origin/main bd517064507bac1264b0dbf01287837b25b4df0c.

- M1: discovery/specification checkpoint complete. Sixteen journey rows, reuse
  inventory, architecture, command-owner walk and preservation gate recorded.
- M2: first increment implemented: `python -m attune_harness.gui --task PATH`
  serves existing owner-rendered snapshots behind a loopback capability boundary.
  Multiple explicit task directories are supported. It has no write/action endpoint.
- M3/M4: not started. This draft is not production-ready or merge-ready.
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
