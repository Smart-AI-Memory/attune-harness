# Fresh installation qualification

2026-09-17. Task 3 of the approved release-readiness follow-through.

The local Harness and Attune AI candidates resolve and run together in fresh
disposable environments on **macOS 26.6.2 arm64, Python 3.12.13**. The integrated
profile is Harness **`[review]`** plus Attune AI **`[harness]`**. Public dependency
resolution selected Forms **0.17.0**, Verify **0.6.0**, RAG **1.2.0** and AI's MCP
**1.29.1**. No existing site-packages directory, source path or editable hook was
borrowed. The interpreter audit has user-site disabled and no `.pth` files.

## Executed evidence

| Check | Result |
|---|---|
| Fresh base Harness install | Dependency-free import, full help and explicit unavailable optional-memory route pass |
| Fresh combined resolution | 74 packages installed, including test tooling; all remote downloads from public PyPI distribution URLs; `pip check` passes |
| Installed module identity | All 13 selected module hashes match current source, including the repaired Spec workspace/state |
| Installed memory behavior | 151 checks pass, including both CLI routes and actual AI-host MCP stdio transport |
| Additive route disabled | 24 retained legacy memory checks pass; both CLIs report disabled explicitly |
| Installed Spec behavior | 80 checks pass: accepted evidence, resume, risk, retries, invalid state and legacy compatibility |
| Installed task journey suite | 146 pass, 3 explicitly source-only tests deselected |
| Optional package removal/restoration | Removing Harness preserves AI's original parser routes and reports the optional worker unavailable; restoring the local wheel passes `pip check` |
| Runtime network guard | Zero intercepted connection attempts; no native model/provider campaign or live memory access |

The first outside-tree journey run had four test-fixture failures: an omitted
helper, one `-S` import test that explicitly inserts a repository `src` directory,
and two tests that load a repository experiment script. The helper was included;
the three source-only checks were separated. They passed in Task 1's full
149-check source run. The installed dependency-free environment directly checks
the library import. No production change or constraint weakening was needed.
The [initial transcript](receipts/release-readiness-follow-through/fresh-install/runtime/initial-runtime-commands.json)
remains available alongside the corrected final run.

One existing ModelTier deprecation warning appears in the installed Spec suite.
The wheel build also retains the previously logged setuptools metadata warnings.
Neither was suppressed or treated as a failure.

## Reproducible artifacts

- [Resolver and builder](receipts/release-readiness-follow-through/fresh-install/resolve.py),
  [exact commands](receipts/release-readiness-follow-through/fresh-install/resolution-commands.json),
  [full pip report](receipts/release-readiness-follow-through/fresh-install/pip-report-integrated.json)
  and [resolved package list](receipts/release-readiness-follow-through/fresh-install/pip-freeze-integrated.txt).
- [Outside-tree consumer](receipts/release-readiness-follow-through/fresh-install/qualify.py),
  [final command outputs](receipts/release-readiness-follow-through/fresh-install/runtime/commands.json),
  [module hashes](receipts/release-readiness-follow-through/fresh-install/runtime/module-hashes.json),
  [interpreter audit](receipts/release-readiness-follow-through/fresh-install/runtime/interpreter-audit.json)
  and [summary](receipts/release-readiness-follow-through/fresh-install/runtime/summary.json).
- [Wheel hashes](receipts/release-readiness-follow-through/fresh-install/wheel-hashes.json):
  Harness `e3bcf434a9893e8564a01c17b7eea91c8b091f108ff8b098c86d927eabd0b3ba`;
  AI `fd61ec93c59f5881f75f6bc183734383282bfc84ea5e51e4183967224bc3a6b2`.

The build tool runs in the existing AI build environment; that is distinct from
the fresh runtime environments, whose dependencies were fully resolved and
installed. Package removal/restoration is a rollback check in the combined
environment, not a third fresh dependency resolution.

## Support limits

This qualifies the recorded macOS/Python 3.12 profile and offline paths. The
earlier Python 3.10 result remains valid within its disclosed reused-dependency
limits; fresh Python 3.10 resolution, other platforms and Harness's separate MCP
2.2.0 extra are unqualified. Do not combine that extra with AI's MCP 1.29.1 pin.

This does not qualify native model reliability/economics, managed mutation of
legacy memory stores, automatic context propagation, live Redis collaboration or
general multi-user identity. Existing installations were not activated or
upgraded; no release was published. Broader plan/build wiring remains a separate
release-defining opportunity in the [journey map](release-journey-map.md).
