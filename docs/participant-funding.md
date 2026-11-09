# Choose participant funding

Published Harness 1.7.0 includes separate **`openai`** API and
**`openai-plan`** subscription adapters and preserves an existing participant's
transport and authentication.
Software checks use offline witnesses. Real provider accounts, model access,
quota and billing remain unqualified. See the
[approved funding specification](specs/participant-funding/README.md) and
[subscription software evidence](specs/codex-subscription/evidence.md).

## Select a route

| Configuration | Behavior |
| --- | --- |
| `adapter: "openai"` with explicit API funding | Send one bounded Responses API request after the owner's per-call admission and fresh spending approval |
| `adapter: "openai-plan"` with subscription funding and an app-owned profile | Use one admitted HTTPS/SSE request on macOS arm64 / CPython 3.12.2 with the explicit `plan-oauth` extra; live account/model qualification remains open |
| Explicit subscription funding on native `claude` or `codex` adapters | Refuse: invocation-level funding enforcement is unqualified |
| Explicit API funding on the native `codex` adapter | Refuse: effective native authentication policy is unqualified |
| Existing entry with no `funding` field | Preserve legacy inherited authentication; funding is unverified |

Both direct adapters are separate choices. Harness never converts a native Codex
entry to either route or retries a subscription refusal using API funding. It preserves the exact
configured model; an incompatible or differently reported model refuses. A new
transport alone does not establish reviewer independence.

## Configure the API adapter

In a registry, preserve the required tool and turn budgets. Replace the model
placeholder with your explicitly selected API model:

```json
{
  "adapter": "openai",
  "model": "<your-api-model>",
  "timeout": 60,
  "tools": [],
  "max_turns": 1,
  "max_tool_calls": 0,
  "funding": {"mode": "api", "credential_env": "OPENAI_API_KEY"}
}
```

For consultation, use the existing identity format:

```json
{
  "adapter": "openai",
  "identity": {"provider": "openai", "model": "<your-api-model>"},
  "timeout": 60,
  "funding": {"mode": "api", "credential_env": "OPENAI_API_KEY"}
}
```

These are participant fragments, not complete configuration files. The OpenAI
adapter requires explicit API funding. `credential_env` names the existing
dispatching host's environment variable; it never contains the key itself.
Harness does not create a key, change login state, copy auth caches or modify
your shell. A policy change requires the existing revision and acceptance path.

## Configure the separate plan adapter

The **`openai-plan`** adapter uses app-owned ChatGPT plan OAuth credentials,
stored separately in macOS Keychain. It launches no Codex process and does not
read native CLI credential caches. Its current runtime gate admits only macOS
arm64 / CPython 3.12.2; general Python 3.12 support does not widen that profile.
Offline checks do not establish real consent, Keychain interoperability,
account eligibility or native Codex allowance equivalence.

Create a separate environment with CPython 3.12.2. Install the published
[Harness 1.7.0 package](https://pypi.org/project/attune-harness/1.7.0/) with the
`plan-oauth` extra.

```sh
python -m pip install 'attune-harness[plan-oauth]==1.7.0'
```

For a local install, verify the wheel's source and SHA-256 against the
[1.7.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0).
Replace the example path with the verified wheel path.

```sh
python -m pip install '/absolute/path/attune_harness-1.7.0-py3-none-any.whl[plan-oauth]'
```

The `plan-oauth` extra is separate from `all`. Select `all,plan-oauth` when
you need both. Account consent and provider execution each require separate
authorization.

The profile commands have distinct effects. Use connection or disconnection only
after explicitly choosing that account operation:

| Command | Effect |
| --- | --- |
| **`funding connect --name <label>`** | Open explicit consent, validate the returned identity and plan scopes, and save an app-owned grant in Keychain before returning an opaque `profile_id`. No task is executed. |
| **`funding inspect --profile-id <id>`** | Read local nonsecret metadata. Do not refresh, contact a provider or open Keychain. An `available` result describes local metadata, not live entitlement. |
| **`funding disconnect --profile-id <id>`** | Disable new admission, coordinate active sessions and attempt remote revocation before clearing this profile's credentials. Inspect any unconfirmed revocation result; native CLI login is separate. |

The command prefix is `attune-harness`. For consultation, replace both
placeholders before using this participant fragment.

```json
{
  "adapter": "openai-plan",
  "identity": {"provider": "openai", "model": "<your-plan-model>"},
  "timeout": 120,
  "funding": {"mode": "subscription", "profile_id": "<your-profile-id>"}
}
```

Use only the opaque ID returned by your own profile connection. A registry uses
the same funding object with its existing `model`, `tools`, `max_turns` and
`max_tool_calls` fields instead of consultation's `identity` object. Keep the
workflow's role and tool requirements. Different transports for the same model
do not create independent review seats.

The Harness 1.7.0 configuration supersedes the earlier proposal to reject
`openai-plan` and `profile_id` in the
[approved design](specs/codex-subscription/README.md#proposed-user-configuration).
The original design and its historical observations remain preserved.

Here, subscription identifies the plan OAuth funding route. It does not promise
free usage, distinguish included allowance from purchased plan-side credits or
report a remaining balance. Real account/model eligibility, quota, billing and
model quality require separate live qualification.

## Check, approve and run

Use **`source-review check`** or **`roundtable check`** with a complete
consultation configuration. Checking sends no model request and grants no
execution authority. For the direct API adapter, `matched` means the selected
local credential and fixed API transport are available. Server authentication,
configured-model access, quota and balance remain unknown. Plan checks inspect
local profile metadata and report funding state `unknown`; they do not establish
live entitlement or refresh a grant. Native funding combinations remain
`unsupported`; a nonmatched funding result exits 2.

Prepare and accept the exact contract through the existing workflow. To execute
the direct API participant, add `--allow-api-spend` alongside the existing
external and effects permissions. For example:

```sh
attune-harness source-review run <run-directory> \
  --accept <contract-digest> --allow-external --allow-api-spend
```

The fresh flag is available on **`review`**, **`resume-review`**, **`test`**,
**`fix`**, **`resume`**, **`plan`**, **`build`**, **`source-review run`** and
**`roundtable run`**. It does not remove another gate or cause a model call in
host-only work. The direct API adapter requires external and API-spending
authority; native participants retain their separate native gate.

Plan turns need their own fresh profile/runtime/request admission and the
workflow's external execution authority. They do not use API-key billing or
silently fall back to the API adapter. A mixed plan/API operation must have
authority for every pending route before dispatch; pending API turns require
fresh `--allow-api-spend` even when the next selected turn uses a plan profile.
Completed turns replay retained results without a new model call.

Pass the flag again when a later execution or resume has pending API calls.
Saved approval evidence is historical, not a reusable grant. Completed calls
replay their retained results without spending again. A refusal before dispatch
stays prepared, records `not_started` and needs no uncertain-call reconciliation.
Timeouts or lost results after launch remain uncertain under the existing
recovery rules. Missing usage never triggers an automatic retry.

Recovered API reply files are refused before reading or saving their contents:
the original credential-redaction context is not retained after an uncertain
attempt. Keep that uncertain record or cancel it explicitly. Any new work needs
new acceptance and spending authority. Legacy recovered-reply behavior is unchanged.

The API-spending flag authorizes calls within the accepted operation budgets. It is not a
dollar-limit engine and does not authorize spending outside the operator's
allocation. Each direct API request uses the official Responses endpoint, disables response
storage and tools, bounds output to 4,096 tokens, and has no automatic retry,
redirect, proxy or configurable gateway. Native-only settings such as
`skills_context_tokens` and Codex reasoning controls do not apply to this adapter.

## Inspect retained evidence

Existing JSON and supported readable status/evidence views show the requested
route, observed route, admission basis, attempt and dispatch outcome. The owner
persists admission before starting the supervised request. A failed admission
write starts no request. New evidence binds the accepted configuration,
participant and specific attempt.

Reported input and output counts remain provider metadata. Cached input is a
subset of input and is not added again. Missing, partial or contradictory usage
is unknown. Billed cost and remaining balance are always unknown in this
increment. API access does not prove whether prepaid credits or other account
billing funded a charge; subscription login does not prove which allowance paid.

Credential values, their hashes, raw process output and raw HTTP errors are not
retained by the direct API transport. Answer and identity decoding also prevent an echoed
selected credential from reaching a receipt. This does not certify model quality
or the meaning of an arbitrary answer.

The installed offline journey uses inert request witnesses, not provider calls:

```sh
<installed-wheel-python> -I scripts/qualify_participant_funding.py
```

Software checks, hosted platform checks and live provider qualification are
separate evidence. The [task record](specs/participant-funding/tasks.md) states
which funding steps are complete; the
[subscription record](specs/codex-subscription/evidence.md) supplies its separate
software evidence and live gaps.
