# Select and verify participant funding

**Status: specification approved by Patrick on November 2, 2026. Execution starts
with T1; live provider calls require the separately authorized spending scope.**
November 2, 2026. Source baseline: `069b9f010cabcefa076ec292b4a287c49a85d219`
(local `origin/main`, Harness 1.6.0). This specification is the complete review
document. [Implementation tasks](tasks.md) divide the work after approval.

[T1 support matrix](t1-support-matrix.md) records the inspected versions, offline
witnesses and remaining invocation-enforcement limits. Ordinary subscription
access and a strictly enforced funding route are separate claims.

## Outcome and limits

A user can explicitly choose Claude subscription access, Codex subscription
access, or Codex API funding for each native participant. Before a model call,
Harness checks the selected route, refuses a mismatch or an unverifiable route,
and records what it checked. Funding is separate from model, provider and role.

This increment adds funding selection, local preflight checks, visible receipts,
and an explicit API-spending gate. It extends the existing native CLI adapters.
It adds no direct model API client, automatic fallback, routing optimizer,
balance polling, monthly budget tracker, credential manager or hosted service.
It does not select new models, change roles, or change accepted work or effects.
Claude API funding is outside this increment; existing legacy behavior stays
subject to its existing authority and compatibility rules.

API funding means OpenAI Platform usage. It does not promise that a particular
request will consume prepaid credits rather than other account billing. Likewise,
subscription login does not prove whether included allowance or purchased
subscription-side credits paid for a request. This spec verifies the execution
route, not the account's final charge or remaining balance.

## Current evidence

| Finding at the baseline | Primary source | Consequence |
| --- | --- | --- |
| Registry and consultation configurations have separate strict validators | [Registry validator](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/review_contract.py#L54), [consultation validator](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L34) | Both must accept and validate the same optional funding policy |
| Local preflight recognizes login but reduces ChatGPT/API-key results to a boolean | [Preflight](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation_preflight.py#L29) | Preserve model availability as unknown; add a separate funding result |
| Native execution invokes `claude -p` or `codex exec` without a selected funding policy | [Native exchange](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/native.py#L159) | Bind a child environment and funding checks to each invocation |
| Native dispatch reaches the adapter through two shared paths | [Review exchange](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/review_participants.py#L173), [consultation dispatch](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L199) | Cover both paths, including assessment, repair, planning, build and resume consumers |
| The process owner already accepts a per-child environment | [Process invocation](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/process.py#L51) | Reuse it; do not change the parent environment or persistent login |
| Consultation results already retain identity, process and provider-usage slots | [Dispatch result](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L222) | Extend retained results rather than create a second run ledger |
| Native decoders retain model/session identity but do not expose normalized usage | [Native decoders](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/native.py#L90) | Capture available usage separately without weakening answer validation |
| A historical live trial used Claude subscription access after removing an API key from its child environment | [Task 8 receipt](../unified-task-execution/task-8-live-receipt.md) | Subscription use has historical evidence; current account access still needs checking |

Provider documentation was checked November 2, 2026:

- Codex supports ChatGPT subscription login and API-key usage; those methods can
  apply different workspace and data-handling policies. [OpenAI authentication](https://learn.chatgpt.com/docs/auth)
- `CODEX_API_KEY` supplies a key to non-interactive execution. A child-only
  override is the candidate API route; it needs version-specific qualification.
  [Codex environment variables](https://learn.chatgpt.com/docs/config-file/environment-variables),
  [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- Claude Code gives an environment API key precedence over subscription login.
  [Claude authentication guidance](https://support.claude.com/en/articles/12304248-manage-api-key-environment-variables-in-claude-code)
- Claude Code integrations must preserve the published binary and users'
  authentication choices, with users funding their own access under the stated
  conditions. Harness selects a route for its child process; it does not modify
  the binary, resell usage or alter the user's other sessions.
  [Claude Code integration conditions](https://code.claude.com/docs/en/legal-and-compliance)

Documentation supports the design direction. It does not qualify a particular
installed CLI, account, platform, balance or billed amount.

## R1: select funding independently

Add one optional `funding` object to native participant entries in both existing
configuration formats. Keep their versions and existing required fields.

| Adapter | Funding object | Meaning |
| --- | --- | --- |
| `claude` | `{"mode":"subscription"}` | Use native Claude account subscription authentication |
| `codex` | `{"mode":"subscription"}` | Use native ChatGPT account authentication |
| `codex` | `{"mode":"api","credential_env":"OPENAI_API_KEY"}` | Read the named environment variable at dispatch; pass its value only to the Codex child as `CODEX_API_KEY` |

`credential_env` is required for API mode. Accept only a portable environment
variable name, never a literal credential, file path or shell expression. Resolve
its value only in the host process; reject missing, empty or invalid values.
Handle Windows names without case ambiguity. Do not persist values or their
hashes. Refuse unknown modes, extra fields, Claude API mode, and funding objects
on deterministic, command or Antigravity participants.

Funding does not contribute to reviewer independence: two entries using the same
provider/model remain the same model identity even if funded differently.
The full funding object participates in existing configuration/request/contract
digests. A change of mode or credential-variable name requires the owner's
existing revision and acceptance path. It cannot edit an accepted run in place.

Configuration examples below are accepted by the T2 candidate's validators;
explicitly funded execution remains refused pending T3 qualification. Preserve
all other fields in the user's existing participant entries:

```json
{
  "claude-subscription": {"funding": {"mode": "subscription"}},
  "codex-subscription": {"funding": {"mode": "subscription"}},
  "codex-api": {
    "funding": {"mode": "api", "credential_env": "OPENAI_API_KEY"}
  }
}
```

These are participant fragments, not a complete registry. They do not choose a
model, create credentials or authorize calls. Initial delivery documents manual
configuration of this optional field; changing **`init`** defaults or adding a
funding wizard is outside this increment.

## R2: inspect the route without a model call

For explicitly funded participants, add a `funding` report to the existing
**`source-review check`** and **`roundtable check`** participant results:

| Field | Values and meaning |
| --- | --- |
| `requested` | `subscription` or `api` |
| `observed` | `subscription`, `api`, or `unknown` |
| `state` | `matched`, `mismatch`, `not_signed_in`, `missing_credential`, `unsupported`, or `unknown` |
| `basis` | Allowlisted evidence label such as `cli_subscription_status` or `scoped_api_override`; no raw diagnostics |
| `cli_version` | Recognized version, otherwise `null` |

`matched` means local evidence supports the selected execution route. It does
not authenticate an API key against a server, prove model entitlement, available
quota or an account balance. Keep those facts explicitly unknown. API mode's
scoped-key check is not represented as a successful server login. If the CLI's
status command ignores an exec-only override, do not use its stored-login report
as proof of the API invocation's route.

Preflight uses only bounded, documented version/status operations. It never
runs a prompt, executes a configured wrapper, logs in/out, creates a run, refreshes
authority or calls an account-billing endpoint. Unsupported versions, malformed
status, unknown authentication helpers, custom gateways, alternate cloud
backends or conflicting managed policy yield `unsupported` or `unknown` until a
supported interpretation is qualified. Report a useful, credential-free remedy.

For explicit funding, **`check`** exits 2 if any route is not `matched`. Its
existing envelope status remains `checked`; a successful route does not change
the existing overall model-availability state to `ready`. A previous successful
check is advisory and never authorizes a later dispatch.

## R3: verify and bind every native dispatch

Before each native model invocation, including resumed and reviewer turns:

1. Validate the accepted configuration and existing call/effects authority.
2. Snapshot the relevant environment into a private per-invocation object.
3. Derive the selected child environment, inspect it and verify the route.
4. Persist the funding admission evidence under the existing run owner.
5. Invoke the native CLI with that same child environment and configuration.
6. Retain the result or interruption evidence before considering another call.

Subscription mode excludes API-funding overrides from the child environment;
it does not clear them from the user's shell. API mode uses only the explicitly
named source variable and the supported child-only override. Neither mode may
silently fall back to another funding source. Only the qualified authentication
paths are allowed: detect and refuse ambiguous helpers, backend overrides and
settings that could select a different route. Keep managed policy and project
rules authoritative.

Qualification must establish how each supported CLI enforces the route during
the invocation, not merely how it reports a login a moment earlier. A status
check alone cannot eliminate a change between check and use. If the supported
CLI cannot enforce the selected route without changing shared credentials,
refuse that configuration and report the limitation. Do not work around it by
copying auth caches, rewriting `CODEX_HOME`, logging the user out, or changing
credential-store settings. In particular, do not assume `forced_login_method`
is harmless: the documented mismatch behavior includes logging out.

Concurrent subscription and API participants get independent child environments.
Neither can change another participant's selection or an interactive session's
login. The guarantee concerns funding selection; ordinary provider-managed token
refresh is not a promise that authentication storage stays byte-identical.

The shared native boundary rejects an explicitly funded invocation lacking the
owner's admission evidence. All native consumers use that boundary; no direct
library path may bypass it. Host-scheduled evidence steps with no model call do
not consume a native admission or claim provider usage.

## R4: require explicit API-spending authority

Add an optional `--allow-api-spend` flag, default false, on each CLI operation
that can execute or resume an explicitly API-funded participant: **`review`**,
**`resume-review`**, **`test`**, **`fix`**, **`resume`**, **`plan`**, **`build`**,
**`source-review run`** and **`roundtable run`**. Add an equivalent explicit
host/library argument. Inspection, preparation and reconciliation never grant
this authority. Existing external/native/effects gates remain required.

The flag approves only API-funded native calls already bounded by the current
accepted request, selected participants and remaining operation budget. It is
not stored as a reusable blanket approval. A later process or resume requires
it again. Calls outside the agreed monetary allocation still require a separate
operator decision; this increment does not implement a dollar-limit engine.

A configuration entry, detected key, monthly allocation, or subscription limit
does not itself authorize API spending. Stop on missing authorization before
model dispatch. Subscription exhaustion or refusal must never trigger an API
retry. The user can select API funding in a revised/new request, review it, and
explicitly authorize that execution. Preserve the earlier run and its uncertain
effects; the new request does not reconcile them automatically.

## R5: show funding and usage evidence

Extend existing per-turn identity/result evidence with optional versioned
`funding` and `usage` objects. Use `profile: "participant-funding-v1"` for funding
evidence and `profile: "native-usage-v1"` for normalized usage. Bind them to the
participant, accepted configuration digest and existing operation/attempt ID.

Funding evidence records requested mode, observed route, admission state/basis,
CLI version and the API-authorization boolean. It records dispatch outcome as
`not_started`, `started`, `completed`, or `unknown` from host process evidence.
Do not call an admission failure a completed provider refusal. The owner records
a pre-dispatch refusal with no provider call, without manufacturing a provider
result or consuming a paid-call slot. It still preserves the refusal for review.

Usage records nonnegative reported input, output and cached-input/read/creation
categories when available. Retain each provider's category meanings; do not add
cached subsets to input totals or invent cross-provider comparability. Missing
fields are `null`, not zero. Invalid, contradictory or partial usage remains
unknown with an allowlisted reason and cannot validate an invalid model reply.

Keep provider-reported cost metadata distinct from verified billed charges.
Use `provider_reported_cost_usd` only when its meaning is established by the
qualified decoder; `billed_cost_usd` and `remaining_balance` remain `null` in this
increment. Do not convert subscription token usage to a claimed dollar charge.
Show the selected route, verification basis, available usage and unknown costs in
the existing JSON and supported readable result/status views. Add no dashboard.

Persist admission evidence before launch. Persistence failure stops dispatch.
Timeout, cancellation or an undelivered result after launch preserves uncertain
usage/effects and existing reconciliation requirements. No automatic retry follows
from missing usage. Preserve every previous attempt rather than replacing it.

Receipt fields and new errors use allowlisted summaries. No key value, auth
token, account email, raw auth-status output, credential fingerprint or complete
environment is stored, printed or sent to the model. New funded execution must
also prevent native process/error serialization from retaining credential values
echoed by a CLI. Redaction applies before persistence, including failure paths;
it must not turn missing evidence into proof of no spending.

## R6: preserve compatibility and acceptance boundaries

Omitting `funding` retains the existing execution behavior and saved-record
interpretation. Do not infer subscription funding, rewrite existing registries,
or retrofit old receipts with verified claims. The explicit-funding guarantee
applies only to selected participants carrying the new policy. Documentation
labels omission as legacy inherited authentication with unverified funding.
Unrelated deterministic, command and Antigravity behavior stays unchanged.

New policy and receipt fields are additive and optional. Existing JSON fixtures
without them remain valid and keep their default bytes/meanings. Update surface
and envelope fixtures deliberately for the new optional flag/fields and refusal
cases, with a changelog entry; follow [compatibility policy](../../compatibility.md).
If implementation discovers a required breaking change, stop for a separate
compatibility decision instead of silently widening this spec.

No live model call, credential operation, merge, release or publication is
authorized by this draft or its approval alone. Live qualification needs its own
bounded call estimate and explicit spending/subscription authorization.

## Walk the command journey before approval

This is a source-level walk, not a claimed live execution. Names in angle
brackets are supplied by the user/test fixture. Funding fields and
`--allow-api-spend` are proposed additions, unavailable at the baseline.
The installed offline journey must run real CLI commands with inert native CLI
witnesses, fresh disposable sources, and run state outside the source checkout.
The approved live journey substitutes separately authorized actual CLIs.

| Step and command | Owner's existing refusal and source | How the input satisfies it; proposed funding check |
| --- | --- | --- |
| 1. Write a complete consultation config outside the source checkout | `configuration`: strict fields/version, explicit model/provider, one source reviewer distinct from author, timeout 1–300 and one round; [raises at lines 37–78](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L34). Registry workflows separately use [validate_registry](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/review_contract.py#L54) | Use schema version 1, nonempty question, an explicit author identity, one different reviewer and `rounds: 1`. Preserve required fields and add exactly one valid R1 funding object. An inert test model is not a selected production model |
| 2. `attune-harness source-review check --config <config>` | [CLI check](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation_cli.py#L71) calls the validator before [bounded probes](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation_preflight.py#L54); missing binary/login returns 2 | Install the witness/qualified CLI on PATH. Supply the selected route's local evidence. R2 returns a separate funding result; missing/ambiguous/mismatched evidence exits 2 without creating a run |
| 3. `attune-harness source-review prepare --project <root> --path sample.py --config <config> --run-dir <new-run>` | [prepare raises at 84/89](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L82); [capture raises at 131–152](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation_snapshot.py#L128); [RunStore refuses symlinks/metadata and exclusively creates the run directory](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/review_store.py#L65) | Use canonical, existing root/ancestors, one regular UTF-8 file below the byte bound, and a new run-directory leaf under an existing parent outside the checkout. No unresolved `/tmp` alias on macOS. The config already passes step 2; prepare freezes it but does not authorize spending |
| 4. Review the returned `contract_digest`, funding selection and `budget.max_calls`; `attune-harness source-review status <new-run>` | [load/validate_record raises at 113–128](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L107); [read_record checks checkpoint](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/review_store.py#L152) | Read the original record at its owning path. Do not modify or copy it. Expect one accepted possible call. New funding evidence does not alter contract/record identity rules; status dispatches nothing |
| 5. `attune-harness source-review run <new-run> --accept <contract_digest> --allow-external --allow-native` | [run raises at 303/306/308](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L296); [unresolved-turn guard](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L341) prevents replay | Use the exact digest from step 3 and a prepared nonterminal record. Subscription route must match immediately before launch. API route deliberately refuses this command until `--allow-api-spend` is also supplied. Existing gates are necessary but insufficient for explicit API funding |
| 6. API only: repeat step 5 with proposed `--allow-api-spend` after operator authorization | Same existing owner plus R3/R4 admission | A pre-dispatch funding refusal leaves no dispatched call to reconcile. Recheck the same unchanged accepted API config and current child override; persist admission then run at most the remaining accepted calls. This flag never substitutes for a wrong digest or missing native/external authority |
| 7. `attune-harness source-review status <new-run>`; `attune-harness source-review evidence <new-run>` | [answer validates verdict/citations at 154–165](https://github.com/Smart-AI-Memory/attune-harness/blob/069b9f010cabcefa076ec292b4a287c49a85d219/src/attune_harness/consultation.py#L150); retained record/snapshot validation remains authoritative | The witness/live reply uses a permitted verdict and only the frozen path/line range. Inspect requested/observed route and usage, including unknown charge/balance. Completed records cannot dispatch again |

Roundtable uses the same walk with two or three distinct model identities and at
most two rounds; a second funding entry is not a distinct-model identity.
For registry workflows, retain the existing owner-specific acceptance, stale
registry, effects and recovery guards. Implementation must extend installed
journeys through both shared native paths; the consultation walk alone does not
qualify planning, repair, build or their resume paths.

## Acceptance and verification

| Criterion | Evidence required before claiming implementation complete |
| --- | --- |
| A1: each supported funding combination validates in both formats | Positive/negative validator tests; unsupported adapters, extra keys, literal secrets and duplicate Windows environment names refuse |
| A2: preflight and dispatch agree on the selected child route | Inert CLI witnesses assert environment/argv, status parsing and zero model calls during checks; stale preflight, missing/unknown/conflicting auth and unsupported versions refuse |
| A3: API spending requires deliberate authority | Each executing/resuming entry point refuses explicit API mode without its new flag/argument, then obeys existing acceptance and remaining-call limits when authorized |
| A4: concurrent modes stay independent | Simultaneous API/subscription witness runs leave parent environment and persistent login selection unchanged; swapping the source variable cannot affect another admitted invocation |
| A5: receipts survive failures without leaking secrets | Admission persistence failure launches nothing; crashes/timeouts preserve uncertainty; sentinel secrets echoed in stdout/stderr/status/errors never reach saved evidence or readable views |
| A6: usage and compatibility claims remain precise | Absent/partial usage stays unknown; cache subsets are not double-counted; provider cost is not billed charge; old records/default fixtures still read unchanged |
| A7: the delivered wheel exercises both native paths | Focused tests, full suite, built noneditable wheel, installed platform qualifier and installed CLI witness journeys. Read Windows CI results; local POSIX checks do not qualify Windows |
| A8: live route support is stated separately | Each claimed CLI/version/platform route has a retained, separately authorized result. Unqualified combinations are listed as unsupported; no economic superiority or balance claim follows |

Required adversarial cases include funding changes after acceptance, unrelated
ambient keys, a key present while subscription mode is selected, CLI helpers that
reintroduce a key, a status command that reports cached subscription login while
exec uses an API override, missing API approval, model substitution, partial
output after cancellation, and a second process attempting to resume the same
owner. Tests must expose bypasses, not just mirror field validation.

## Approved decisions

Patrick approved D1–D3 and subsequently approved the full specification on
November 2, 2026, directing execution to start with T1. Paid calls remain
subject to their separately authorized scope and allocation.

| ID | Decision | Approved choice and tradeoff |
| --- | --- | --- |
| D1 | Existing configurations | Keep omission compatible and label it unverified legacy behavior. Require the guarantee only when `funding` is explicit. Requiring every existing config to choose now is a separate breaking migration |
| D2 | API-spending authority | Add `--allow-api-spend`/host argument, default false, alongside the existing acceptance gates. Require it again on resume. This is an explicit gate, not an enforceable dollar ceiling |
| D3 | Unsupported authentication routes | Refuse a version/configuration when the CLI cannot safely enforce the selected route. Qualify supported child-only paths before promising concurrency; never change shared logins to make a route work |

The scope already excludes automatic fallback, new model selection, monthly
accounting and credential management. No further provider or model choice is
needed to review this draft. Personal allocations stay outside public repository
documents and do not change D2. T1 establishes the supported combinations before
implementation promises a funding route.
