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

Full suite, wheel/install qualification, independent source review, Windows GUI,
new native runs, screen-reader audit and real-user usability remain open.
No prior prototype result is relabeled as production qualification. This increment
uses private task_view style/script constants to preserve its CSP hashes; review
that seam before widening the interface. Clipboard behavior inside the sandboxed
snapshot frame is not qualified; select-and-copy remains available.

## Next

Complete source review and packaging/full-suite checks for this increment, then
bind intake and decisions to existing owners. Preserve the prototype interaction
inventory and refusal tests. Experiment 23 identity and model-selection evidence
remain separate pending work; neither is silently replaced with a new trial.
