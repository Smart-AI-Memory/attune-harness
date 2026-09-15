# Phase 6 — local documentation-review pilot

2026-09-14. Execute Patrick's selected evidence/documentation workflow in
attune-harness, after disposing of the Phase 5 research. Completion means a
fresh installation reproduces the documented review, interruption/resume,
extension upgrade/removal, failed-upgrade recovery and package rollback, with
the required earlier installed checks rerun. This is an opt-in local pilot;
Patrick's preference and broader native-provider qualification remain separate.

Design note first. The disposable pre-implementation verification probe reviewed
the real `docs/e2-revision-receipt.md` through the previously installed package.
It returned **unknown**, with 9 verified, 0 refuted and 25 unknown extracted claims
out of 34. Unknown command flags/counts must survive the pilot; neither a model
narrative nor a successful process can turn them into verified claims. Retained
probe: `receipts/phase6/verification-probe.json`. The actual docs corpus currently
contains 421 Markdown files, within the existing 1,000-file limit. A separate
installed E3 calibration completed its three calls but produced wrong arithmetic;
that is evidence against relying on this model's unreviewed conclusions.

Use the dependency-free pinned Ollama adapter from dev1 behind a new packaged
command peer. Request each granted retrieval/verification tool, then generate one
independent narrative per role. Project the complete document, retrieved excerpts
and all extracted claim subjects/statuses/locations into bounded model context;
retain full native tool evidence in the coordinator record. Explicitly disclose
the projection and excerpt scope. Reject an oversized prompt before generation,
never silently truncate. Pin model digest/server/settings in command arguments
and retain the raw generation and exact prompt in a separate local receipt per
turn. A duplicate turn receipt is refused before another generation. Review
narratives remain unverified proposals. Tools and evidence supply no authority.

Cases: valid read-only review; unknown/refuted evidence stays visible; independent
reviewer has no lead narrative; disabled/changed/removed extensions refuse new
work; resume preserves accepted inputs and completed events; changed corpus or
stale checkpoint fails; failed replacement preserves the disabled old artifact;
rollback re-enables the exact retained bundle; removal preserves user data;
package rollback can inspect the new local review and complete the old fixture
journey. Actual process-death/ambiguous-effect cases remain covered by the earlier
installed recovery suite, rerun on this artifact. The pilot itself pauses at a
durable checkpoint between tools and model generation and explicitly resumes.

Package dev2 separately, preserving dev0 and dev1 artifacts/environments. Build
a complete pinned wheelhouse, install offline into fresh core/feature/review/MCP
profiles, run pip checks and the prior 110 installed cases, then an explicit
BasePlugin bridge check against the existing host packages. No base environment
upgrade, data conversion, shared-state dual writers, global default switch or
publication. The supported pilot platform is only the actual macOS arm64 /
Python 3.10.11 / POSIX host; Linux and Windows have no platform receipts here.

Rejected: calling paid native providers while authorization is absent; relabeling
deterministic participants as live models; treating unknown document claims as
pilot failure to hide; replacing the old environment in place; migrating or
deleting attune-ai data before the selected workflow proves useful. A command
peer reuses the existing portable boundary without modifying orchestration,
grants, lifecycle or recovery behavior.
