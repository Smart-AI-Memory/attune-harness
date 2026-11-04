# T1: native funding controls and qualification limits

**Status: T1 discovery complete; strict subscription-route enforcement remains
unqualified. No provider call was made.** November 2, 2026.

Scope: the approved [funding specification](README.md), T1 only. Baseline
`069b9f010cabcefa076ec292b4a287c49a85d219`. This report establishes candidate
controls and concrete refusals before production changes. It does not silently
weaken R3's invocation-level requirement into a login-status check.

## What was inspected

The local macOS arm64 installation reports Codex `0.153.4` and Claude Code
`2.1.293`. Only their `--version` and `--help` commands ran. No native prompt,
login/status/logout, credential helper, account API or model endpoint ran. No
credential/configuration files were opened. Codex's version/help commands
returned 0 with a warning that PATH-alias creation was denied; they are not
claimed to be free of all attempted filesystem effects.

| Artifact | SHA-256 of inspected local bytes |
| --- | --- |
| Codex npm launcher, package version `0.153.4` | `61b0194f3bb6534439c8d26a3ed57d0805f84b884588b761795323eeb92fcf70` |
| Codex arm64 native binary selected by that launcher | `b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3` |
| Claude native binary reporting `2.1.293` | `4e21122a227857da1178aca3299700c1fd7f2b77c93f12e73c2c76db796a105e` |

The Codex source inspection is pinned to official release `rust-v0.153.4`,
commit `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`. Version output plus local hashes
does not establish a reproducible-build match with that release source. Claude's
binary is opaque; its installed help is local evidence, while the living official
docs are design evidence, not a frozen source contract for `2.1.293`.

## Support and refusal matrix

All rows describe the inspected macOS versions. No Windows/Linux or newer-version
qualification follows. No explicitly funded route has been enabled in Harness.

| Requested route | Candidate child inputs | Evidence and enforcement | T1 disposition / refusal |
| --- | --- | --- | --- |
| Codex API, `0.153.4` | A private child `CODEX_API_KEY` resolved from the selected source variable; built-in OpenAI provider and qualified OpenAI endpoint; verified policy allowing API auth | The pinned exec path enables the override, and the auth loader gives it priority when API login is allowed. Stored login status deliberately ignores that override | Source-supported candidate; not runtime qualified. Refuse missing/empty input, unknown effective provider/endpoint/login policy, workload or access-token routes, and unbound versions. A key's presence proves neither server authentication nor credit balance |
| Codex subscription, `0.153.4` | Remove competing API/access-token/workload inputs from a private child; use existing ChatGPT login with verified provider, endpoint and managed policy | A stored ChatGPT login may supply credentials. Status and the later exec process can load different stored auth; no safe invocation-level binding was established | Unqualified. Refuse explicit subscription dispatch until an enforcement mechanism is established. Do not claim that one successful status check closes the check/use gap |
| Claude subscription, `2.1.293` | Candidate: private environment excluding higher-priority API/provider credentials while retaining the existing subscription login | Settings can restore credentials and providers; gateway/profile/helper paths exist. `--bare` explicitly excludes OAuth/keychain. Neither `loggedIn` nor `forceLoginMethod` establishes a universal inference-route lock | Unqualified. Refuse unknown helpers, policy/settings/provider routes or unenforced credential selection. Do not enable bare mode or change shared login to make subscription isolation appear to work |

Under approved D3, these refusals are the honest disposition of the missing
evidence. They do not mean that ordinary subscription use is unavailable. They
mean that R3's stricter funding guarantee has not been demonstrated. Omitted
funding keeps its existing legacy behavior under D1.

## Codex: version-bound findings

1. The [exec auth manager](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/lib.rs#L552-L555)
   enables the API environment override. The
   [auth loader](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/login/src/auth/manager.rs#L1445-L1462)
   prioritizes a nonempty `CODEX_API_KEY` only when allowed-login policy permits it.
2. [Login status](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/cli/src/login.rs#L443-L463)
   disables that override. A stored-subscription report can coexist with an API
   environment for exec. It must not verify the API request's funding route.
3. Before normal execution, [exec enforces login restrictions](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/lib.rs#L473-L478).
   [Restriction mismatches can log out shared storage](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/login/src/auth/manager.rs#L1309-L1340).
   The preceding restriction check loads the exec-only key with its override
   enabled, so an API key plus forced-ChatGPT policy can trigger that logout.
   An API override therefore does not make unknown managed restrictions harmless.
   Do not inject `forced_login_method` as an assumed nonmutating guard.
4. The [built-in OpenAI provider](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/model-provider-info/src/lib.rs#L386-L420)
   uses OpenAI auth without a custom provider token/helper. However,
   [provider and base URL selection remain configurable](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/config/mod.rs#L3713-L3735).
   [Custom provider auth](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/model-provider/src/auth.rs#L185-L219)
   and [explicit bearer credentials](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/model-provider/src/auth.rs#L292-L304)
   require their own interpretation; they are outside the qualified candidate.
5. [Access-token and stored-auth paths](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/login/src/auth/manager.rs#L1493-L1552)
   and [workload identity selection](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/login/src/auth/workload_identity.rs#L123-L159)
   prevent treating all OAuth or non-key logins as the requested subscription.
   Refuse `CODEX_ACCESS_TOKEN`, `OPENAI_FEDERATION_RULE_ID` and
   `OPENAI_IDENTITY_TOKEN_FILE` in an unqualified selection context.

These source findings agree with current official
[authentication](https://learn.chatgpt.com/docs/auth),
[environment-variable](https://learn.chatgpt.com/docs/config-file/environment-variables)
and [non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)
documentation. They do not establish the actual machine's effective policy.

## Claude: documented hazards and installed-help evidence

Current [authentication documentation](https://code.claude.com/docs/en/authentication#authentication-precedence)
describes several sources above stored subscription OAuth: selected cloud
providers, bearer/API credentials, an API helper, an explicit OAuth token and
named profile/federation credentials. A signed-in apps gateway selects another
provider outside that order. Removing one API variable is insufficient.

The [settings reference](https://code.claude.com/docs/en/settings-reference#env)
states that settings `env` values can apply at startup and again when merged
settings change; non-interactive execution also loads project/local values
without a trust dialog. Helpers and managed policy can supply further inputs.
Clearing inherited environment values therefore does not freeze the effective
configuration. `forceLoginMethod` is a documented sign-in restriction, not an
established inference-route guarantee.

Installed `2.1.293` help confirms that bare mode skips OAuth/keychain credentials.
The [programmatic-execution guide](https://code.claude.com/docs/en/headless#start-faster-with-bare-mode)
documents the same limitation. Bare mode cannot qualify subscription access.
Living docs mention behavior introduced after `2.1.293`; do not backport those
claims automatically. The safety of invoking auth status under arbitrary helpers
was not established, so actual auth status was deliberately not run.

## Offline software witnesses

Run from this checkout with Python 3.12 or later:

```sh
python3.12 scripts/qualify_participant_funding_t1.py
```

The [witness script](../../../scripts/qualify_participant_funding_t1.py) executes
only a temporary stdlib Python program through the existing process supervisor.
It never executes a provider CLI, reads auth storage, or sends a model request.
All key-like inputs are synthetic. Six checks passed:

1. The API child receives its selected synthetic key and label.
2. Concurrent subscription/API children receive separate environments.
3. The synthetic parent and caller-provided dictionaries stay unchanged; the
   real parent environment mapping is restored without inspecting its values.
4. Identical stored-login reports can coexist with different exec environments
   in the deliberately inert source-contract counterexample.
5. The actual existing preflight parser reduces both recognized Codex funding
   methods to `True`, demonstrating the information loss R2 must repair.
6. Unrecognized status remains unknown.

Checks 4–6 expose a limitation; they do not implement funding admission or prove
native provider behavior. The version-pinned source establishes the actual Codex
status/exec distinction. Check 2 establishes local process separation, not
subscription-route enforcement. No balance, entitlement, charge or Windows
behavior is qualified by these witnesses.

A peer evidence review caught unnecessary ambient environment copying in the
first witness. No credential values were printed or saved, but that pattern was
removed. The final witness uses a synthetic parent mapping; original local
receipts/source remain beside the superseding v2 receipt. This review also
narrowed the environment claim to the selected key/label actually inspected.

## Next implementation boundary

T2 can add the approved configuration format and preserve legacy inputs.
T3 must retain D3's refusal for unqualified combinations; a validated funding
object must never be silently ignored by dispatch. Safe effective-policy
inspection and invocation-level subscription binding remain prerequisites for
enabling a subscription route. They require further engineering evidence,
not simply purchasing a successful trial.

If proceeding would require changing shared credentials or weakening the accepted
guarantee, report that concrete constraint to Patrick before taking that action.
No such action, API spending, credential mutation or production routing change
was performed by T1.
