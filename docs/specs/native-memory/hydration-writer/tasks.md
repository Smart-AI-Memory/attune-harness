# Hydration writer implementation plan

Status: **approved by Patrick, October 24, 2026**. Task 1 is active; later tasks
follow their stated dependencies and retained gates. See
[requirements](requirements.md) and [design](design.md).

## Entry gate and authorized scope

After Patrick approves, refresh `origin/main`, re-read applicable rules and inspect
concurrent changes before each task. Use isolated branches off main and open a
draft PR on first push. Carry only the approved scope. Source changes receive a
different-model or Patrick review covering the final head; source deltas return
for review. Patrick retains merge authority. No paid experiment, workflow dispatch,
release, production Redis write or personal hook edit follows from task approval.

The current planning PR contains only this addendum and documentation index links.
Approval of a documentation merge must not be interpreted as implementation go.

## Sequential tasks

| Task | Deliverable and candidate owners | Acceptance and requirement trace |
| --- | --- | --- |
| 1. Characterize sources and freeze proposed contracts | Synthetic fixtures for all layers; full example configs; proposed result/manifest schema; adopt/adapt/reference/drop record. Candidate new tests: `test_memory_hydration.py`, `test_memory_hydration_publication.py`. | H1–H6: table-driven failures for every new refusal in the README walk; collisions across roots and recursive rules; supported legacy metadata; complete-source secret/placeholder cases; exact schema/ranking expectations; source checksums. No personal source redistribution, fixture regeneration or live production hydration. |
| 2. Add opt-in generation reads first | Extend `memory_redis.py`, `memory_serving.py` and memory CLI plumbing as needed; candidate native module `memory_hydration_redis.py`. Add packaged, versioned Lua assets and package-data configuration. | H1/H3/H4/H5: legacy config and frozen fixture unchanged; malformed/foreign manifests refused; data/filter/provenance stay on one generation; switch-during-read refused; native absence is unavailable without fallback; native read path writes nothing; installed wheel contains assets and imports without attune-ai. The writer must not precede reader support. |
| 3. Implement capture, check and publication | Candidate `memory_hydration.py` owns schema/capture/projection; publication backend owns staging, readiness, CAS, reconciliation and bounded cleanup; `memory_cli.py` adds hydrate arguments/results. | H1–H6: check causes zero Redis mutations; apply handles first run and unchanged input; all four layers round-trip; failed capture/stage/index/function checks preserve active/previous generations; competing publishers cannot both replace the same base; cleanup cannot reclaim selected/publishable data; uncertain effects reconcile without blind retry. |
| 4. Package the hook and qualify the journey | Candidate `memory_hydration_hook.py`; installed CLI and real disposable Redis+Search tests; installed-wheel checks added to existing owners where needed. | H6/H7: exact documented command order, bootstrap from empty Redis, ten-second fail-open wrapper, sanitized output, stale-generation diagnostic, correct filtering and no body leaks. Targeted tests, full suite and `scripts/qualify_platform.py` against the wheel; inspect Windows CI. Separate Claude Code and Codex fresh-session receipts, with any unsupported host surface left explicitly open. |
| 5. Document migration and record completion | README hydration guidance, `docs/cli-guide.md`, `docs/migration-from-attune-ai.md`, applicable `help/` source and `docs/README.md`; source-bound verification record. | H7/H8: fresh install and existing-user paths, explicit opt-in and rollback, no requirement for installed attune-ai, host-specific evidence/limits. Preserve historical specs and receipts. Completion review complete with actual log/draft reference or reasoned no-change outcome. Release/publication and production rollout remain Patrick's. |

Task 1 also establishes the actual supported startup mechanism for each host
through read-only discovery. If Codex has no usable automatic surface, return to
Patrick before Task 2; do not spend the backend implementation effort on an
unachievable accepted journey. No personal settings are changed by that discovery.

Tasks are dependency-ordered, not permission to merge intermediate source PRs.
Prefer independently reviewable PRs in this order. If main integration waits on
Patrick, retain the reviewed handoff rather than silently creating a dependency
stack or widening the task. Changes to `.github/workflows/` are not presumed
necessary; consult retained receipt pins and request a scoped plan change before
adding a new service job or changing qualification policy.

## Verification matrix

| Failure or journey | Required evidence |
| --- | --- |
| Existing legacy consumer | Existing Redis/serve/config tests plus immutable fixture hash unchanged; snapshot proves writer never touches legacy keys, library, scratch or saved-memory state. |
| First install, no attune-ai | Built wheel with Redis extra outside source tree; imports, Lua resources, check/apply/status/serve/prompt sequence using a complete synthetic authority config. |
| Capability absent | Extra missing; plain Redis without Search; missing Functions/ACL access; wrong existing native library; unavailable connection. Explicit direct-command failure, empty hook stdout as appropriate. |
| Invalid sources | Traversal, links, hard links, special files, excess bounds, malformed UTF-8/frontmatter/edges, authority mismatch, duplicate IDs, ambiguous links, secret in body/metadata/edge beyond indexing bound. No publication or secret-bearing diagnostics. |
| Publication failure | Kill/fault before stage, during write, index build, readiness and CAS; network loss before/after acknowledged switch; source/config changes before switch; two real concurrent writers from the same token. Verify active/previous resources and exact reconciled status. |
| Reader/cleanup race | Pause a reader, publish a newer generation and run cleanup; race retirement with publication and expire an abandoned stage. Emit one coherent packet or explicit refusal; never a mixed generation or reclaimed active cache. |
| Real search/function behavior | Exact Redis, Search and redis-py versions/configuration; real index readiness/error handling and packaged-function identity. Distinguish this from double-based command-contract tests. |
| Cross-platform source/CLI behavior | macOS/Linux checks and hosted Windows results exercise real authorized capture and wrapper supervision. Report skipped integration profiles separately; a Windows unit pass is not a Windows desktop-host observation. |
| Receiving agent | Each host/version/startup mechanism; fresh-session provenance banner; relevant prompt where supported; synthetic wrong/inactive examples excluded; unavailable service diagnostic. A manual command is not automatic delivery evidence. |
| Revert selection | Config back to legacy reads unchanged legacy projection; original Markdown/sidecars unchanged. Age/disabled-writer limitations recorded; no promise that an old cache is current. |

## Effort and stopping conditions

Initial planning estimate: **4–7 development days** for the generation-aware reader,
writer, failure tests, packaging and docs, plus host access/review/CI waiting time.
This refines the earlier 3–5-day option estimate after identifying the fixed-key
publication constraint. It is not a measured delivery commitment. Re-estimate at
Task 1 if compatibility or host discovery changes the design.

Stop and return to Patrick for source-format changes, broader data exposure,
unavailable host startup integration requiring a changed journey, new dependencies
or unsupported server semantics. Two failures using the same approach trigger a
strategy review before a third attempt. Preserve the task's actual evidence and
remaining gate; do not weaken assertions to close it.

The smallest implementation unit is Task 1's disposable contract fixtures. The
first complete user outcome spans Tasks 2–4; selecting only the smallest unit
would not close automatic recall. This draft requests approval for the bounded
sequence, not a broad memory-system rewrite.
