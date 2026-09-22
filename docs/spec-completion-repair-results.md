# Spec completion evidence repair — results

2026-09-17. Task 2 of the approved release-readiness follow-through is accepted.
Changes are in the isolated Attune AI adoption worktree. They are shared Spec
host behavior, usable while leading Harness work; no existing feature was removed.

Accepted task results now retain task ID, severity, score, probes, detail and
disposition through the existing atomic plan-state store. The terminal view shows
each accepted result and labels the earlier planning artifacts/probes separately.
High severity remains an acknowledged risk; rejected retry attempts are excluded.
Repeated save/load preserves Unicode, backslashes, newlines and comment delimiters.
Invalid supplied receipts fail visibly without resetting completed progress.

The state format adds an optional receipt list. Existing runner-produced progress
and older plans remain compatible. Completed IDs without receipts show
**Execution evidence unavailable**; the display does not invent earlier proof.
The independent reviewer initially proposed requiring a receipt for every
current-format completed ID, then withdrew that finding after tracing the shared
runner contract and the legacy-upgrade path. A new three-task/two-resume regression
retains the newer receipts while preserving the earlier missing-evidence warning.

## Verification

- [Original reproduction](receipts/release-readiness-follow-through/terminal-before.json)
  versus [repaired display](receipts/release-readiness-follow-through/terminal-after.json).
- [Before repair](receipts/release-readiness-follow-through/spec-regressions-before.txt):
  all 19 initial new regressions failed; the existing 60 passed.
- [Final Spec/host suite](receipts/release-readiness-follow-through/spec-suite-compatible.txt):
  **153 passed**, including the additional compatibility regression.
- [Repository gates](receipts/release-readiness-follow-through/ai-gates-final.txt):
  **678 passed**. The new receipt validation was extracted to meet the existing
  complexity limit; no baseline or allowance was weakened. Ruff and Black pass.
- [Changed coverage](receipts/release-readiness-follow-through/changed-coverage.json):
  state **100%**, workspace **97.73%**.
- [Protection removal](receipts/release-readiness-follow-through/protection-removal.json):
  **4/4 detected** in isolated source copies: omit accepted results, omit restored
  results, remove risk-disposition validation, remove comment escaping.
- [Independent review](receipts/release-readiness-follow-through/summary-independent-review.json):
  pass, **80 focused checks**, original finding and withdrawal retained.
  [All 14 reviewed hashes matched](receipts/release-readiness-follow-through/summary-review-binding.json).

The active installed plugin was not replaced. Its existing completion screen can
still exhibit the original defect. Task 3 qualifies the repaired candidate wheel
in a disposable installation; publication and live activation remain separate.
