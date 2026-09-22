# Connected journey qualification — results

2026-09-17. The approved three-step sequence is complete within its documented
software boundary: capability inventory, installed representative journey, and
extended profiles plus a concrete native follow-through decision. This is not a
whole-product release or native-quality acceptance. The existing repaired installed
Spec host recorded [all three executor receipts](receipts/connected-journey-qualification/spec-closeout.json)
under the authorized unattended sequence; no new human response was manufactured.

## What changed

`attune-harness test --from-task /path/to/completed-repair` now derives the checkout
and actual replacement paths from a completed repair. A new test task binds its
producer's task/request/checkpoint, artifact and probe evidence. Test acceptance
stays separate; the completed repair remains immutable. Existing standalone tests
and specialist routes remain available.

The host rejects incomplete, failed, stale or missing producers, caller overrides,
contradictory probe evidence and reviewer responses that disagree with the saved
summary. It checks currentness before preview, acceptance, dispatch and reuse.
A previously passing result becomes visibly blocked when its producer is no longer
current, while the historical receipt remains intact.

The [installed journey](receipts/connected-journey-qualification/installed-journey/journey-summary.json)
uses actual CLI processes, four synthetic participant calls, real file repair and
pytest, then the real installed AI Spec collector. Pause/resume repeats neither
participant calls nor completed replacement/test effects. Current synthetic
approval persists its exact evidence; stale/replayed decisions fail. A passing
repair probe followed by failing tests reaches the existing high-severity gate;
ordinary approval is refused. These are simulated interaction-contract checks,
not real human acceptance or a usability study.

Assessment→repair remains explicit executor selection of goal/scope. Test→Spec
remains trusted executor publication of the actual test record. Only repair→test
is a new product provenance edge. The [capability map](specs/connected-journey-qualification/capability-map.md)
identifies all these owners and remaining links. It does not present the current
verbs as an autonomous plan/build engine.

## Executed evidence

Counts describe separate suites and may overlap; do not add them into a unique
test count or model-quality score.

| Profile / check | Result | Evidence |
|---|---|---|
| Source core regression, including 29 new connected checks | **336 passed** | [Source log](receipts/connected-journey-qualification/source-regression.stdout.txt) |
| Same installed core suite outside source tree | **333 passed, 3 source-only exclusions** | [Installed log](receipts/connected-journey-qualification/installed-regression.stdout.txt) |
| Shared AI/Harness memory, Python3.12, AI MCP1.29.1 | **107 passed** against source and installed Harness | [Installed memory](receipts/connected-journey-qualification/installed-memory-qualified.stdout.txt) |
| Harness retrieval/extensions/MCP2.2, native adapter software and legacy review | Source **393 passed, 7 profile skips**; installed **392 passed, 7 skips, 1 source-only exclusion** | [Source](receipts/connected-journey-qualification/source-services-current.txt), [installed](receipts/connected-journey-qualification/installed-services-qualified.stdout.txt) |
| AI code-retrieval bridge with matching Voyage dependencies, Python3.10 | **17 passed**; includes the seven AI-host cases skipped in the Harness-only profile | [Bridge log](receipts/connected-journey-qualification/installed-code-host.stdout.txt) |
| Real synthetic A2A loopback server | **38 passed** against source and installed Harness | [Source](receipts/connected-journey-qualification/source-a2a-loopback.txt), [installed](receipts/connected-journey-qualification/installed-a2a.txt) |
| Removal of individual handoff protections in disposable copies | **4/4 detected**: probe journal, reviewer journal, producer checkpoint, caller scope/root | [Mutation receipts](receipts/connected-journey-qualification/mutations.json) |
| Independent implementation review and central closure | **Two reproduced findings repaired; no remaining material finding in scope**; 27 inspected hashes matched centrally | [Review](receipts/connected-journey-qualification/connected-journey-implementation-review.json), [central hash check](receipts/connected-journey-qualification/review-hash-check.json) |
| Installed runtime identity | **52 modules match current source** | [Installation receipt](receipts/connected-journey-qualification/installation.json) |
| Original native retained-data audit | **revise**, 48/60 correct, six unsupported allegations, zero critical misses | [Unchanged auditor output](receipts/connected-journey-qualification/native-retained-audit.json) |
| Original/corrected native artifact preservation | **941 original and 212 corrected files unchanged**; all six assistant grading artifacts match | [Preservation check](receipts/connected-journey-qualification/native-preservation.json) |

Tasks/execution lifecycle checks passed before implementation, without waivers;
[their receipt](receipts/connected-journey-qualification/lifecycle.jsonl) explicitly
shows symbol-reality checked zero cited tokens. Ruff and Black pass for the changed
runtime/tests. A provider-backed pipeline runner was not executed; no score here
claims that pipeline or semantic/native qualification.

Wheel: `attune_harness-0.1.0.dev13-py3-none-any.whl`, SHA256
`ba57ea1b62a288767124efe12e4c965cfad93b4b1bbf7cd1b7533e83022875a4`.
Installed under `/private/tmp/attune-connected-h_i2dp77/installed`. This is a fresh
Harness target install with reused qualified dependency environments, not another
fresh dependency resolution. Runtime module hashes match; final explanatory
README/report edits followed the wheel build. No active installation, AI checkout,
plugin, account configuration or release was changed.

## Disclosed failures and limits

Early journey fixture errors were corrected against existing contracts and are
recorded in the [reflection](reflections/connected-journey-qualification-2026-09-17.md).
Independent review also found **two actual handoff defects**: probe summary versus
journal disagreement and reviewer summary versus journal disagreement. Both have
central negative cases and targeted protection-removal checks.

One broader installed run incorrectly selected Voyage-dependent tests in the
memory environment; it reported one failure/eight setup errors due to absent
LanceDB. The qualified memory run passes 107; code retrieval runs in its existing
matching environment. Harness MCP2.2 and AI MCP1.29.1 remain separate profiles.
One installed service test explicitly passes `--source` to an experimental script;
it is now disclosed as source-only and passed in the source suite. The other three
source-only exclusions concern source import isolation and frozen campaign tools.
[Exact exclusions](receipts/connected-journey-qualification/installed-exclusions.json)
are retained. A receipt-copy glob was corrected after pytest truncated its fixture
directory name; the already-passing tests did not need rerunning for that copy.
The AI bridge emitted one existing deprecated ModelTier import warning.

Sandboxed A2A startup initially failed because local socket binding was denied.
The permitted synthetic `127.0.0.1` runs passed. This does not qualify authenticated
remote production agents. No live model or Voyage API calls occurred in these
qualification suites; independent review used the existing delegated assistant.

Repair remains bounded to existing regular UTF-8 replacements in its dedicated
POSIX checkout. Test execution remains the supported local Git working-tree/default
pytest profile. Trusted probes/tests may have external effects; this is not a
security sandbox. Other platforms, active memory delegation, form visibility and
the unimplemented plan/build/ship/reflect journeys retain their own gaps.

The tiny installed fixture measured 0.33s test preview, 0.72s acceptance plus test
execution/pause, 0.33s recovery, 0.28s completed replay and 0.24s status. These are
single observations, not representative workload benchmarks, native-form latency
or economic comparisons. Human reading time was not measured.

## Native work and next steering

The native runner and corrected required-review contract are **already implemented
and exercised**. Task 8 remains unaccepted because its original quality comparison
failed and its chosen human grading is still pending. The corrected 8/8 follow-up
remains a separate bounded result. This slice starts native follow-through with an
unchanged audit and preservation checks rather than another provider campaign.

The [native schedule and prepared decision](specs/connected-journey-qualification/native-follow-through.md)
puts the remaining assessment-quality contract and prospective grading protocol
immediately after this slice, before broad native promotion. It preserves Patrick's
no-repeat decision and prepares any later admission as an exact reviewable packet.
Missing billing/human-effort measurements still block economic claims.

[O-12 and O-13](opportunity-log.md) record the shared work-identity and reusable
receipt-validation opportunities. Plan/build's scoping draft remains unapproved;
feature preservation, current human control and a learnable verb interface remain
the requirements for its next bounded design.
