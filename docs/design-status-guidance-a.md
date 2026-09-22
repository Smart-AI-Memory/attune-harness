# A — plan/build status guidance

September 18, 2026. Implementation contract: clearer current outcomes and valid
next actions in the existing plan/build CLI; no execution-policy changes.

Cases: incomplete and ready drafts; completed planning proposals (still drafts);
planning critique, paused and failed planning; accepted work with incomplete build
configuration; paused builds; failed required controls and protected checks;
optional unavailable/failed checks and reviewer notes; high reviewer findings;
uncertain operations, including lost acknowledgments; completed dependent builds
and the older file-effect profile. Stale draft/proposal/accepted/build evidence
must suppress ordinary acceptance, staging, execution and completion advice.
Uncertainty must suppress retry advice even when freshness also fails.

Disposable probes ran against current source with the retained Python 3.12
runtime and existing local worker fixtures, with native dispatch poisoned:

- Stale draft: `status=stale` but `next_action` still offered `plan --accept`.
- Required runner absent: `ValueError`, zero worker calls, no saved build;
  status inspection still reported accepted authority without guidance.
- Optional runner absent: completed build, saved `extra: unavailable` advisory,
  no next action in the CLI output.
- Ordinary completed build: verified journal, no next action in CLI output.

Raw baseline and disposable records are under
`/private/tmp/status-guidance-a/baseline.json`; the original presentation source
is copied there as `work_cli.before.py`. These are local probes, not native model
qualification or changes to prior experiment receipts.

Design: retain existing JSON fields and exit-code mapping. Add a concise summary,
phase, blocking indicator, optional-advice references and evidence pointers into
the full saved record. Choose guidance from validated owner/run evidence, with
uncertainty and freshness ahead of ordinary progression. Use existing read-only
freshness/preflight functions; never dispatch, acquire a writer lease or save
during status. Keep completed check evidence distinct from reviewer judgments.
An exception before a saved build still gets blocking guidance and, when readable,
the saved record reference. Preserve its exception type/detail and exit code.

Rejected: another persisted status model (would compete with the execution owner),
new acceptance/retry controls (outside A), and a new UI framework or mandatory
optional dependency (the existing JSON summary/action/evidence convention suffices).
Verification will use real CLI/local subprocess journeys, read-only snapshots,
failure injection for uncertain acknowledgments, and a baseline regression run.
A is already authorized; the design note introduces no additional approval gate.
