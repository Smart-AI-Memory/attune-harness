# Subscription software evidence and remaining qualification

**Status: S2–S4 implemented and independently reviewed. S5 installed-wheel checks
pass; a frozen Windows input gate blocks the full source suite. S6 and Claude C1
remain separate and unstarted.** November 4, 2026.

The [README](README.md) owns the funding contract and ordered refusal walks.
The [direct design](direct-oauth-design.md) owns request/stream bounds. Patrick
approved S2–S5 implementation after the earlier documentation-only revision.
No live sign-in, Keychain operation, provider inference or API-credit spend is
included in this software milestone.

## Candidate and review

Implementation base: `ce52b9d3b4a1f1c65c339a05cb8f10b869431a86`.
Signed source candidate: `68bf6111c48a5e38eaa0c2594ced23130479a587`.
The earlier test-only follow-up `9b314a4` added the approved optional extra to
package tests and included inert stream controls in installed qualification.
The final source delta refuses missing validation dependencies before consent
and expired deadlines before helper launch. It also aligns existing shared
HTTP/MCP dependencies and CI constraints with the approved security pins.
[PR #336](https://github.com/Smart-AI-Memory/attune-harness/pull/336)
retains the current review and CI handoff.

Independent review configured as GPT-6 Astra approved S2–S4 source after four
repaired findings: pending mixed authority, malformed stream events, repeated
revocation disposition and pending-refresh inspection. It then approved the
shared atomic-file replacement delta, consent/deadline guards and dependency
alignment. Exact hash comparison covers all 21 changed source files and the
final package/constraint bytes. No runtime model attestation is claimed.
Review reports and exact source hashes are retained locally; the PR records the
reviewer, verdict, findings and source identity. Later source changes require a
delta review.

## Exercised software boundaries

| Boundary | Controls and owner | Limit |
| --- | --- | --- |
| Protected lifecycle | [Profile controls](../../../tests/test_plan_profiles.py) exercise per-profile locking, atomic successor recovery, uncertain refresh, concurrent disconnect, missing storage, unchanged identity/scopes and honest revocation. [OIDC controls](../../../tests/test_plan_oidc.py) validate real signatures and issuer/audience/expiry/nonce against local keys. | Keychain, browser and auth transport use doubles; no real account or native credential store was exercised. |
| One request | [Worker controls](../../../tests/test_plan_worker.py) count zero/one requests, fixed host/path, verified TLS, no retry/redirect, bounded frames/JSON, event/item/text correlation and failed/incomplete/conflicting completion. | Inert HTTPS/SSE does not establish live provider compatibility, model permission or a server token/dollar cap. |
| Real owner authority | [Funding controls](../../../tests/test_plan_funding.py) cover genuine leases/journals, private one-use claims, rotation/disconnect, stale request/runtime, pending mixed authority, replay and distinct concurrent plan profiles. | A v2 receipt is evidence, never deserializable authority or a billing receipt. API-only v1 behavior remains separate. |
| Installed user journey | [CLI walks](../../../tests/test_plan_journeys.py) and funding controls exercise source review, roundtable, positional/task review and resume, plan/build, fix/resume and the separate test path. Completed events replay; missing API authority stops selected siblings. | Test responses are synthetic. No local check/prepare/status/evidence/profile inspection grants entitlement or dispatches a provider. |
| Compatibility | Package/CLI controls retain legacy funding behavior and retired-extra refusals, add exact optional dependency pins and preserve the API worker/body bytes. | The plan runtime remains limited to macOS arm64 / CPython 3.12.2 with the pinned optional dependencies. |

Final focused standard-environment preflight: **334 passed**, including
subscription/package/atomic/CLI, plugin-signing and partition controls. One
nonblocking Authlib deprecation warning remains under its exact 1.9.3 pin.

| Final check on source candidate `68bf611` | Actual result |
| --- | --- |
| Focused subscription/integration preflight | 334 passed; no skips or failures. |
| Complete source suite, two supervised partitions | **Failed:** 6,607 passed, one failed, 224 skipped; seven additional subtests passed. The sole failure is `test_new_workflow_has_four_safe_cells_and_current_controller_origins`, which enforces the historical Windows experiment input map. Neither partition was omitted. |
| Noneditable installed-wheel platform qualification | **Passed:** 4,038 passed, 201 skipped; two additional subtests passed. Platform receipt reports `checks_passed`, zero model calls, successful R2 owner journey, memory checks and all ten plugin-probe steps. |
| Correctness lint and documentation link checker | Passed. |

These are macOS arm64 / CPython 3.12.2 software results. The source-suite failure
is unresolved and S5 remains blocked. Native Windows results belong to hosted
CI; no local skip supplies Windows evidence. The subscription route remains
outside Windows support even if general compatibility checks pass.

Built wheel SHA-256:
`0af91234ae210fc3075d998cbbaf21c494898424c337a601133c90720ab69969`.
All **134** Harness/plugin payload files match source candidate `68bf611`.
Both fresh environments use a noneditable wheel and all five CI constraint
files; dependency consistency checks pass. Full source checks also select the
optional native SDK for its inert witnesses. Installed qualification selects
`all,plan-oauth` and preserves its deliberate provider-SDK exclusion.

## Retained failures and corrected setup

Earlier receipts stay failed/interrupted. A copied test fixture referenced the
wrong imported name; the package-extra compatibility expectation also needed the
new explicitly approved extra. The full-suite atomic-write guard found a direct
replacement in the metadata writer; production now uses the shared file owner.
No retired-extra, persistence, deadline or assertion guard was disabled.

The restricted runner denied local process operations. An active environment
inside a directory scanned for untracked coverage inputs triggered its symlink
refusal. Final checks use clean owned checkouts and external environments.

The expanded installed run under a `uv`-created environment failed 13 native-SDK
witnesses because its `pyvenv.cfg` has `version_info`, while this qualified
macOS Framework profile requires the standard `version` and `executable` keys.
The same failure was reproduced on unchanged main. A fresh standard-library
virtual environment satisfies the unchanged witness; all focused preflight
checks pass. The failed environment and evidence were preserved. These checks
are unrelated to Claude subscription feasibility and contain no model calls.

A later source run failed with macOS socket paths under the default long
temporary root and an editable-install import in a nested environment. The
final setup uses a short external temporary root and an installed wheel without
altering either guard. An expanded installed run passed pytest but failed the
intentional post-check excluding provider SDKs; the final installed environment
omits those SDKs. Earlier failures remain failed for their original setup.

Head `9b314a4` CI exposed shared dependency drift: the existing plugin pin policy
also read exact pins introduced by the optional extra, while CI installed older
certifi/cryptography constraints. Candidate `68bf611` pins those already-shared
base dependencies and aligns the three constraints; the plugin resolver and
its security checks remain unchanged.

The two frozen Windows experiment workflows now refuse the changed
`requirements-mcp.lock` hash before their account fixtures or software checks.
Their maps expect `50f956aff914ee8ca2e85e00e3cc35aa56fff07213b659d962d7c9d91be94735`;
the reviewed candidate has
`87071ba2a0d0c033a4059b44ee9b816076c6e8d87407b59b8f0a35f6fd871211`.
The token/Voyage locks in those maps also differ. Retained diagnostic artifacts
confirm that no account fixture ran. These failures are a PR blocker, not
subscription or Windows qualification. Historical manifests, workflows and
receipts are unchanged; a prospective Windows experiment update needs a
separate scoped decision. The source suite independently reproduces that same
pin mismatch. The route, preflight and pre-fixture caller also retain the old
lock pins, so changing only the workflow maps would not repair the entire
journey. The proposed follow-up needs a reviewed successor input/caller set,
unchanged account/permission/cleanup gates and new account-free CI evidence;
it must not relabel historical results or invoke an account fixture.

## Official protocol sources

Public official documentation was rechecked on November 4, 2026. It establishes
the protocol contract, not this account's eligibility.

| Source | Applied fact |
| --- | --- |
| [Sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) | Validate the issued client, identity signature/claims, fresh nonce and actual returned plan scopes. Identity sign-in alone is insufficient. |
| [Accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions) | Retain verified subject with the issued client registration; the same client preserves its workspace binding. Reauthorization still validates the newly issued ID token. Serialize refresh and retain honest revocation outcomes. |
| [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference) | Plan bearer-token inference requires a final successful response. Usage limits may fail after streaming begins. |
| [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) | The plan body uses an input array, `store:false` and `stream:true`; it cannot copy API output-token and schema controls. |
| [Errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery) | Auth, entitlement and stream failures need explicit handling. This implementation keeps a stricter one-attempt contract with no hidden refresh, retry, model change or funding fallback. |

## Separate live and historical boundaries

S6 still needs explicit account/model/effort/usage approval for real consent,
Keychain interoperability, a bounded plan turn and a minimal mixed plan/API run.
Notify Patrick before any API credits are needed. Live account/model permission,
actual quota and billing, native Codex allowance equivalence and model quality
remain unqualified. Software success supplies none of these verdicts.

The [original app-server S1 report](s1-qualification.md) and receipts are unchanged.
Its SHA-256 remains
`4bc4405cc48d9a12152c97a705e816d6006f23e03e17a62a34a9bf5a2fae5801`.
The direct worker does not turn that earlier single-inference stop gate into a
pass. Frozen campaigns, wheels and environments remain records.

[Claude C1](claude-feasibility.md) remains unstarted. The shared funding contract
does not share credentials, auth mechanisms or qualification between providers.
No merge, release, settings change or new experiment is authorized here.
