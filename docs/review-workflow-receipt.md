# Local coordinated-review receipt — 2026-09-14

The authorized local Phase 2 increment is implemented. One installed CLI journey
accepts a request through attune-forms, retrieves local evidence, runs a selected
lead and independent reviewer with scoped tool access, independently verifies the
reviewed Markdown document, and saves an inspectable run record.

## Changes and acceptance

- `review-form` renders the real library's form and binds submissions to the
  registry revision. Declined, missing, stale and invalid requests stop before
  participant execution. Paths are bound to the accepted request.
- The registry supports deterministic, Claude, Codex and JSON command profiles.
  Tool membership, arguments, response correlation, turn and call budgets are
  enforced. Native/command invocation is explicit, with no provider fallback.
- Both roles can actually call attune-rag and attune-verify. Independent contexts
  keep the lead's narrative out of the reviewer prompt. Native profiles reuse the
  existing translator; an independent command fixture imports no Harness code.
- The coordinator preserves both narratives and native verification findings.
  `completed` describes the journey; document_outcome separately reports
  verified/refuted/unknown. No-source results are also explicit. Review prose is
  not certified by the document's verification result.
- Exclusive run directories and atomic/fsynced records preserve pending work
  before dispatch. Persistence failure stops further operations. Inspection never
  resumes/retries, and stored running work is reported unresolved. Source-change,
  interruption, malformed-response and exhausted-budget tests fail honestly.

See [design note](design-review-increment.md), [commands and contracts](review-workflow.md),
and the [installed example record](../examples/review/installed-run/record.json).

## Verification

Baseline: 170 tests passed, 98.69% statement coverage. Final: **252 tests passed,
98.67% statements** (888/900); [suite output](receipts/review-suite.txt) and
[coverage data](receipts/review-coverage.json). All 82 added cases passed. These
include real feature calls, both native lead journeys with injected process
transports, real local command success/failure/timeout/output limits, forbidden
tool paths, stale/duplicate turns, input changes and uncertain persistence.

The three new CLI tests against the existing dispatch module fail with the review
dispatch branch removed: **3/3**, in a disposable source copy; production source
was never mutated. [Mutation output](receipts/review-cli-mutation.txt). Tests for
new modules were written with their implementations.

**40 installed CLI cases passed** outside the source tree with `python -I`, across
five isolated dependency profiles. The review environment was created fresh; the
four previously isolated feature environments received the final wheel again.

| Profile / suite | Cases | Evidence |
|---|---:|---|
| Core regression | 3 | [receipt](receipts/review-regression-core.json) |
| Verification-only regression | 8 | [receipt](receipts/review-regression-verify.json) |
| Retrieval-only regression | 5 | [receipt](receipts/review-regression-rag.json) |
| Both feature extras regression | 10 | [receipt](receipts/review-regression-all.json) |
| Review extra | 12 | [receipt](receipts/review-installed.json) |
| Core-only form absence and record inspection | 2 | [receipt](receipts/review-core-installed.json) |

Console help checks also passed. The installed example independently completed
with verified document claims; each role made two real feature calls. Stdout,
saved record and `inspect-review` output matched. The independent command peer
completed the installed journey with two real tool calls. No attune-ai, Anthropic,
Claude Agent SDK or OpenAI SDK dependency was present in these test environments.

## Build identity and scope

Harness wheel: `attune_harness-0.1.0.dev0-py3-none-any.whl`  
SHA256: `aeca809c7ff68996fc7a6d27f6ce8ccd383395eabf3aad6ea9d89547802b6e6d`

The new dependency is attune-forms **0.17.0**, built from cached Git commit
`4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7`. Wheel SHA256:
`895ee10adcc292340d66b4a8196a39036fae014a7b4a49584d2e05fc4ca893e2`.
Existing verify 0.6.0 and rag 1.2.0 pins are unchanged. All three dependency wheels
rebuilt to the recorded hashes; [build output](receipts/review-dependency-rebuild.txt).
Exact commits, build tools and all validation packages are in dependency-lock.json
and requirements-workflow.lock. These are local cached-source receipts, not remote
freshness or PyPI-publication claims.

The attune-forms checkout stayed at 976bf91a1b33f2d7a4072beb68fd941861e3f15d,
16 commits behind its cached origin/main, with the same unrelated untracked files.
Sibling source checkouts were not edited. Harness remains a local workspace
without Git metadata; nothing was committed, published or deployed. Validation
ran on macOS/Python 3.10.11. Native/command transports remain POSIX-only; no Windows
runtime qualification is claimed.

**Provider calls in this increment: 0.** No new credential use, account recharge,
different-model review or paid-provider qualification occurred. Native fixtures
are not live model evidence. Claude qualification remains on hold.

This is the bounded local Phase 2 workflow, not completion of all Phase 1 or 2
obligations. Outstanding: supported-protocol/direct-model/runtime comparisons;
live review journeys for both lead choices and an additional model; comparison
with the existing Attune workflow; wider host interaction/help/skill integration;
recovery, transfer and effect reconciliation. The JSON store and synchronous
coordinator are provisional choices for this workflow, not a production substrate
qualification. No automatic retries or dollar-cost guarantees were introduced.
