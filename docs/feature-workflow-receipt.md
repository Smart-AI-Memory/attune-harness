# Four-step local feature milestone — 2026-09-14

All four requested steps are complete. These are local feature operations toward
Phase 2, not completion of the full review workflow or the earlier qualification
matrix. No model calls, authentication changes, publications or source-checkout
mutations occurred during this milestone.

| Requested step | Result and evidence |
|---|---|
| 1. Pin dependencies and plan | [Design/execution note](design-feature-workflow.md) preceded source edits. [Dependency lock](../dependency-lock.json) records full commits and wheel hashes; [environment lock](../requirements-workflow.lock) pins validation packages. |
| 2. Optional verification adapter and CLI | `verify_document` calls the real public attune-verify API. CLI preserves strict outcomes, claims/findings, document/context hashes and explicit dependency failure. |
| 3. Installed workflow and negative cases | Fresh core-only and verify-only environments passed strict positive/negative/unknown/no-claim cases; [verification checkpoint](verification-checkpoint.md) was saved before retrieval implementation. |
| 4. Checkpoint then local retrieval | `retrieve_sources` uses DirectoryCorpus and KeywordRetriever. Sources carry paths, original-byte hashes, keyword scores, match reasons and excerpts; no match returns no_results. [Runnable workflow](local-workflow.md) and sample reports are retained. |

The dependency source checkouts remain at the original HEADs:
attune-verify `3b9191651ebbd7030d93cd14db009d9cb38f14c8` and attune-rag
`25d2cf00bbe4a71daa7e8894402153ed6465d238`. Their cached origin/main commits were
archived separately for the build; unrelated work in attune-rag was not touched.
Current remote/PyPI freshness was not asserted or needed to identify these pins.
Both wheels rebuilt byte-for-byte using the recorded build tools and commit time
as SOURCE_DATE_EPOCH: [rebuild output](receipts/dependency-rebuild.txt).

## Validation

**170 tests passed, 98.51% statement coverage** on Python 3.10.11. Real library
calls cover supported valid claims, broken references, unknown and empty checks,
nested document paths, source changes, malformed results and missing/incompatible
optional packages. Report output tests protect inputs and clean up failed atomic
writes. Retrieval tests include CRLF source hashes, root escapes, size limits,
no results, invalid hits and source text that contains instructions.

Tests accompany new feature modules and CLI code. Existing participant, native
and process tests remain in the suite. Installed checks also preserve the old
no-argument demo through the updated module entry point. No new existing-code
guard regression tests were added in this milestone; prior native diagnostic
mutation evidence remains in its earlier receipt.

The final wheel passed **26 CLI cases** across four independent configurations,
each from a temporary working directory through isolated Python:

- [Core only: 3 cases](receipts/feature-installed-core.json) — original demo works;
  verify and retrieve are explicitly unavailable.
- [Verify only: 8 cases](receipts/feature-installed-verify.json) — strict checking
  and report output work; retrieval is unavailable.
- [Rag only: 5 cases](receipts/feature-installed-rag.json) — keyword matches,
  no-results and refreshed source versions work; verification is unavailable.
- [Both extras: 10 cases](receipts/feature-installed-all.json) — both actual
  library paths work together with their positive and negative cases.

Each environment also passed a console-entry help check and confirmed attune-ai,
provider SDKs and embedding packages absent. Both fresh extras installs used the
wheel's actual extra metadata and pinned constraints with an offline package
cache. An initial smoke-script error dereferenced the venv interpreter symlink
and selected the base interpreter; correcting the path to preserve the venv
made the actual isolated checks pass. No failed check was suppressed or skipped.

The prepared `.venv-workflow` contains the final installed wheel and both extras.
The documented example journeys were executed and produced:

- [Verification example](../examples/local-workflow/verification-report.json):
  verified, one supported claim, per-claim evidence retained.
- [Retrieval example](../examples/local-workflow/retrieval-report.json):
  retrieved, two source references with hashes and excerpts.

Final wheel: `dist/attune_harness-0.1.0.dev0-py3-none-any.whl`.
SHA256: `1edea086c4113db0d38d767c80d9c0a75bb706a138a9a9f3421517de79a7385c`.
[Machine-readable summary](receipts/feature-suite-summary.json).

## Remaining roadmap work

Claude's live qualification remains paused. Direct-model and supported protocol
comparisons, complete host/handoff inventory and production substrate selection
remain Phase 1 obligations. Phase 2 still needs forms intake, participants with
real authorized feature access, coordinated review and a durable work record.
Retrieval scores do not establish answer correctness; verified status concerns
extracted supported claims only. Reports describe the checked input snapshots,
not immutable external state. This package remains a local development build;
no release or different-model review was performed.
