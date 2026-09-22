# Function-body replay — completed without model calls

September 18, 2026. **Both requested checks pass:** replacing only the accepted
function body prevents the observed unrelated renderer edit, while separate
replay-only behavioral checks still detect the known logic failure inside the
function. Every original grade and all 17,216 earlier receipt files remain
byte-identical. The native trial was closed before this replay started.

There were **zero model calls, zero additional worker credits and zero new API
dollars**. Ordinary Codex session work is excluded from those worker figures.
No production code, model route or Task 8 acceptance changed.

## What was replayed

The host selects the accepted file, function and current-source hash. The only
replacement content is the function body. It verifies the actual source hash,
splices into the original body span and rejects any change to the surrounding
module AST or function interface. The original prefix and suffix bytes are
preserved, including imports, constants, decorators, signature and unrelated
definitions. This prototype supports one top-level multiline function with
four-space indentation in UTF-8/LF source. It is an edit boundary, not a sandbox
against arbitrary behavior inside the function.

This is an offline projection from retained full-file replies. It neither asks
Luna for a new response nor measures how reliably Luna would produce the new
body-only contract. Invalid JSON and invalid Python are not repaired or unescaped.

| Witness | Body-only replay | Original grade |
| --- | --- | --- |
| `lb07`: substantive prose repair plus unrelated renderer regression | Correct target body passes; original renderer is preserved byte for byte. Replaying the complete original file still fails preservation. | Failed, unchanged |
| `lb02`: test outcome decision ordering | Supplemental tests pass; protected replay checks reject exit 2 becoming `no_tests` instead of `interrupted`, and exit 4 becoming `no_tests` instead of `blocked`. | Failed, unchanged |
| `lb12`: correct finite-number repair with wrong copied preimage hash | Body passes with trusted host-owned binding and actual-source verification. The original invalid envelope is not reused. | Failed, unchanged |
| `lb15`: rank-fusion logic | Behavioral tests still fail because duplicate rows consume ranks. | Failed, unchanged |
| `lb18`: unchanged defective function | Rejected before effects. | Failed, unchanged |

The `lb02` checks are **post-hoc additions only to the replay fixture**. Removing
them reproduces eight green original checks for the same faulty function body;
the original semantic failure still remains. Body restriction alone does not
detect that logic defect. The new behavioral assertions cause an actual protected
probe failure and `needs_revision` through the installed build/retest path.

## Results and controls

- All 20 reference body repairs pass the installed build/check/resume path.
- All 20 dedented module-code injections and 20 stale-source attempts are rejected.
- Twelve boundary unit tests pass, covering Unicode, multiline strings, decorated
  nested functions, source drift, target mismatch, syntax failure and scope escape.
- Of 21 retained originals, 16 produce evaluated body replacements: 14 pass and
  two fail. One unchanged replacement is rejected before effects; three malformed
  JSON replies and one invalid Python reply are skipped intact. These are separate
  replay outcomes, not a revised native success rate.
- Removing the body boundary reproduces the unrelated renderer regression;
  removing the added logic checks reproduces the original test gap.
- The local run executes 300 supplemental/protected test cases plus the 12 unit
  tests. No-repeat completion and stale-source rejection pass for completed owners.

The closed native trial remains **12 original passes / 9 failures**, costing
7.043789 worker credits across 21 calls, with 19 unused slots. Its two reference-
contaminated passing cases remain flagged; this local replay does not repair that
qualification defect. It establishes neither fresh model reliability nor a
measured cost or speed advantage. Smaller response payloads remain a hypothesis
for any separately scoped future trial.

Evidence: [replay summary](receipts/plan-build-function-body-replay-2026-09-18/summary.json),
[individual replay outcomes](receipts/plan-build-function-body-replay-2026-09-18/replay-results.json),
[actual logic-failure evaluation](receipts/plan-build-function-body-replay-2026-09-18/replays/lb02/evaluation.json),
[original trial](plan-build-luna-broader-results.md),
[final verification](receipts/plan-build-function-body-replay-2026-09-18/closeout-verification.json).
Implementation: [body boundary](../experiments/plan_build/function_body_replacements.py),
[local replay runner](../experiments/plan_build/replay_function_bodies.py),
[boundary tests](../tests/test_plan_build_function_bodies.py).
