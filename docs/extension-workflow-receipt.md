# Local extension implementation receipt

2026-09-14. Bounded Phase 4 increment implemented; the full phase is **open**.
[Design before implementation](design-extension-increment.md),
[contract and runnable workflow](extension-workflow.md),
[machine-readable summary](receipts/extensions-summary.json).

- **366 tests passed**, 1,349/1,387 statements covered (**97.26%**).
- **90 installed CLI cases passed**: 63 prior feature/review/recovery checks plus
  22 extension checks with the separately built plugin wheel and five core-only checks.
- **10/11 targeted new tests fail with their guard removed**. Seven extension
  integration pins fail; three of four process-cleanup pins fail. The live-process
  permission-denial negative pin passes as designed. New-module tests are outside
  that targeted mutation denominator. Mutations ran in disposable source copies.
- **Zero provider calls**; no credential changes, remote writes or publishing.

The data-only example contributes `SKILL.md` and `evidence.search`, which invokes
real attune-rag against the accepted corpus. Both Claude and Codex lead paths pass
injected-transport tests using their real native translators. An independently
implemented subprocess participant passes the installed journey without importing
Harness. This proves the command boundary, not another model or protocol standard.

Lifecycle receipts cover disabled installation, activation/dependency checks,
artifact-bound discovery, collisions, unknown bindings, same-version byte changes,
replacement, stale controls, removal and preserved user data. A separate process
held an invocation lease while disabling correctly failed busy; disabling then
succeeded after completion. Paused reviews refuse disabled/removed/changed
artifacts. Re-enabling the same artifact resumes without repeating the saved tool
call. New grants cannot supply a different corpus or exceed existing budgets.
A no-results call remains no-results; activation/listing is never verified availability.

The explicit BasePlugin bridge was exercised with installed Harness, attune-ai
16.4.0 and attune-rag 1.2.0 in an environment inheriting the existing host packages.
Metadata, initialize, activation and real search passed; a disabled call was refused.
This is an explicit bridge receipt, not an isolated Attune install, automatic host
discovery, global skill installation or host MCP registration. No sibling checkout
was modified.

## Cleanup defect found and corrected

Initial full-suite runs exposed intermittent process-group `PermissionError`
during rapid child exit. It also occurred outside the execution sandbox, so it
was not dismissed as sandbox-only. The retained
[sandbox failure](receipts/extensions-sandbox-failure.txt) and
[elevated failure](receipts/extensions-elevated-failure.txt) precede the fix.
A [disposable probe](receipts/extensions-cleanup-probe.py) made 100 local child
runs; [12 initial denials](receipts/extensions-cleanup-probe.json) resolved after
bounded parent reaping, with the group then absent.

Cleanup now waits at most 100 ms after an initial denial and retries group cleanup
once. A still-live denied parent or a second denied group remains an error.
Parent exit is never taken as proof that descendants stopped. New tests exercise
rapid exit, real live-process denial, persistent group denial and descendant
cleanup. The final full suite passed under the normal execution sandbox; no tests
were skipped to obtain the result.

## Artifacts and reproducibility

| Artifact | SHA-256 |
|---|---|
| Harness wheel `0.1.0.dev0` | `d4f2c7821e05a1a66a30fb18c65bf1407a225023d8b797bad183336fda787807` |
| Example data-only plugin wheel `0.1.0` | `b62bfb4fa6c142b54c4116715ef578982fd48539c17724667923ff89312fa758` |
| Manifest + skill content identity | `a362119464924325c12b14cded6ede0df8e215d119686af786b2a963060e4c63` |

Built with local Python 3.10.11, build 1.5.0 and the existing setuptools/wheel
builder; `SOURCE_DATE_EPOCH=1789344000`. Runtime dependencies remain optional and
pinned. Core requirements remain empty. The example plugin wheel contains package
data with no mandatory dependencies. Workflow, core, verify, rag, all-feature,
review and explicit Attune bridge environments were updated to the final wheel.
The builder is the base interpreter; the workflow test environment does not carry
`build`. No package version/release or remote availability claim is implied.

Validation commands (run from the checkout):

```sh
.venv-workflow/bin/python -m pytest tests -q --cov=attune_harness --cov-report=json:docs/receipts/extensions-coverage.json --cov-report=term-missing
.venv-workflow/bin/python scripts/check_extension_mutations.py
python3 scripts/check_extensions_installed.py --python .venv-review-check/bin/python --report docs/receipts/extensions-installed.json
python3 scripts/check_extensions_installed.py --python .venv-core-check/bin/python --core --report docs/receipts/extensions-core.json
.venv-attune-bridge-check/bin/python -I scripts/check_attune_bridge.py
```

The bridge environment intentionally inherits host site-packages; other validation
environments retain their separate dependency profiles. Retained outputs:
[suite](receipts/extensions-suite.txt), [mutations](receipts/extensions-mutations.json),
[installed extensions](receipts/extensions-installed.json),
[core-only extensions](receipts/extensions-core.json),
[Attune bridge](receipts/extensions-attune-bridge.json),
[recovery regression](receipts/extensions-recovery-regression.json),
[final installed example](../examples/extensions/qualified-example/summary.json).
The summary lists all remaining regression case files.

## Remaining plan obligations

Phase 4 still requires supported MCP interoperability, an independent A2A peer's
identity/access/task/artifact/disconnect/cancellation cases, wider host/executable
plugin support and E2's declaration-only versus evidence comparison. The current
receipt makes no MCP/A2A claim and introduces no MCP SDK dependency. Windows and
cross-machine lifecycle remain unqualified. Earlier live-model, E1 and broader
phase acceptance obligations remain open. Phases 5 (collaboration evaluation) and
6 (pilot/migration) follow; neither was started by this increment.
