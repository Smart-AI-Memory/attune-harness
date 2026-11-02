# Choose participant funding

This guide describes the participant-funding development candidate. It adds an explicit direct
OpenAI API adapter. It does not change an existing participant's transport or
authentication. See the [approved specification and revision](specs/participant-funding/README.md).

## Select a route

| Configuration | Candidate behavior |
| --- | --- |
| `adapter: "openai"` with explicit API funding | Send one bounded Responses API request after the owner's per-call admission and fresh spending approval |
| Explicit Claude or Codex subscription funding | Refuse: invocation-level funding enforcement is unqualified |
| Explicit Codex API funding | Refuse: effective native authentication policy is unqualified |
| Existing entry with no `funding` field | Preserve legacy inherited authentication; funding is unverified |

The direct API adapter is a separate choice. Harness never converts a Codex entry
to it or retries a subscription refusal using API funding. It preserves the exact
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

## Check, approve and run

Use **`source-review check`** or **`roundtable check`** with a complete
consultation configuration. Checking sends no model request and grants no
execution authority. For the direct API adapter, `matched` means the selected
local credential and fixed API transport are available. Server authentication,
configured-model access, quota and balance remain unknown. Native funding
combinations remain `unsupported`; a nonmatched funding result exits 2.

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

Pass the flag again when a later execution or resume has pending API calls.
Saved approval evidence is historical, not a reusable grant. Completed calls
replay their retained results without spending again. A refusal before dispatch
stays prepared, records `not_started` and needs no uncertain-call reconciliation.
Timeouts or lost results after launch remain uncertain under the existing
recovery rules. Missing usage never triggers an automatic retry.

The flag authorizes calls within the accepted operation budgets. It is not a
dollar-limit engine and does not authorize spending outside the operator's
allocation. Each request uses the official Responses endpoint, disables response
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
retained by this transport. Answer and identity decoding also prevent an echoed
selected credential from reaching a receipt. This does not certify model quality
or the meaning of an arbitrary answer.

The installed offline journey uses inert request witnesses, not provider calls:

```sh
<installed-wheel-python> -I scripts/qualify_participant_funding.py
```

Software checks, hosted platform checks and live provider qualification are
separate evidence. The [task record](specs/participant-funding/tasks.md) states
which are complete. No release or live account/billing qualification follows
from this guide alone.
