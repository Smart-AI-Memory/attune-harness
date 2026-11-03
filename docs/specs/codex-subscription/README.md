# Codex subscription support alongside API credits

**Status: Draft for Patrick's review. Not approved for implementation.**
Written November 3, 2026 against main
`03e29647a02073089fb33ea8df45b75be65383ba`. This planning pass changes
documentation only. No account connection, native authentication probe or model
call has qualified the proposed route.

## Outcome and recommendation

Allow a participant to explicitly use a ChatGPT plan through Codex while another
participant explicitly uses the existing OpenAI API adapter. Preserve the
accepted task, funding, spending, independence and recovery boundaries.

Recommend a new **`codex-app-server`** adapter supplied with a user-consented
Sign in with ChatGPT plan OAuth grant. OpenAI documents this integration for
local/open-source applications. It gives this design a separate credential and
provider route to enforce, rather than inferring funding from shared Codex login
state. The documentation establishes a candidate, not a qualified Harness
implementation. [Official app-server integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server)

This is an explicit scope extension: Harness would own a small sign-in/profile
lifecycle. The [approved funding spec](../participant-funding/README.md#approved-decisions)
excluded credential management. Approval of this draft must resolve D1 below;
it must not silently reinterpret that exclusion.

The separate [Claude feasibility check](claude-feasibility.md) ends with an
evidence-backed verdict. Claude implementation does not enter this scope, and a
negative or unknown Claude verdict does not block Codex implementation.

## Baseline and scope

The [API-first revision](../participant-funding/t3-decision.md) delivered the
explicit **`openai`** adapter. Explicit funding on native **`codex`** and
**`claude`** remains refused; omitted funding keeps inherited, unverified legacy
behavior. These are separate cases in
[the current funding owner](../../../src/attune_harness/participant_funding.py#L16-L72).

| Include in the next implementation | Keep outside this implementation |
| --- | --- |
| Local macOS arm64, one pinned Codex binary/protocol and a qualified configuration profile | Other operating systems/architectures, unattended upgrades, hosted or commercial deployment qualification |
| Explicit subscription adapter plus existing direct API adapter in the same accepted workflow | Automatic routing, quota-based switching, API fallback, balance polling or a billing ledger |
| App-owned plan OAuth profiles in macOS Keychain, explicit connect/inspect/disconnect | Reading or copying native auth caches, changing shared logins, importing pasted tokens, plaintext credential fallback |
| Model replies through both shared participant caller paths and their executing/resume owners | Native Codex tools, shell, MCP servers, apps, subagents, arbitrary user config or a second agent workspace |
| Existing Harness-owned retrieval, verification and proposal/application gates | Giving Codex direct filesystem or tool authority through this transport |
| A separate Claude feasibility report | A Claude adapter, Claude OAuth intermediary or a Claude API integration |

The initial release qualifies software behavior and an exact execution route.
It does not qualify model quality, every account/model entitlement, or every
platform. S1 must confirm that the proposed local distribution meets current
provider conditions before implementation proceeds.

## Funding and authority contract

1. Keep funding separate from model, role and adapter identity. Never change a
   participant's funding mode, model or effort because a request fails.
2. Require the new adapter to carry exactly
   `{"mode":"subscription","profile_id":"<opaque-local-id>"}`. No omitted
   policy, API key, credential path or custom endpoint is accepted on it.
3. Keep **`openai`** with explicit API funding and a named environment credential.
   Require fresh **`--allow-api-spend`** or its host argument for each execution
   and resume that can call that adapter. This flag remains an authorization
   gate, not a dollar ceiling.
4. A saved subscription choice authorizes neither sign-in nor task execution.
   Connecting a profile authorizes neither a model call nor API spending. Retain
   acceptance and external/native authority where the existing owner exposes
   them; extend consultation's native-seat classification to this new adapter.
5. Check all participants' static funding and authority requirements before any
   sibling model dispatch. Resolve and admit every member of the selected batch
   before sending task content to any member. A missing API grant must not
   consume subscription quota through a partially dispatched batch.
6. Refuse unknown, revoked, unavailable, unqualified or mismatched profiles/routes,
   and expired grants that cannot be refreshed within authorized execution
   limits. Return an actionable refusal; do not offer an automatic
   API retry. A deliberate funding change needs a new configuration, contract
   and acceptance.
7. Preserve approved D1–D3: legacy omission remains unverified, API authority is
   fresh, and unsupported routes fail closed. Existing native explicit funding
   stays unsupported; this spec adds a distinct transport.

Here, `subscription` means the plan-authorized OAuth route, as distinct from
API-key billing. It does not distinguish included plan allowance from purchased
plan-side credits, promise free usage or report a remaining balance. Account
eligibility and the selected model must be verified separately.

## Proposed user configuration

The following is a **design example, not a runnable current configuration**.
Current validators reject the new adapter and `profile_id`. Replace every
placeholder with an explicitly selected, qualified value after implementation.
Do not use aliases such as `default` or silently select a model.

```json
{
  "schema_version": 1,
  "question": "Review the selected code for correctness risks.",
  "author": {"provider": "codex", "model": "AUTHOR_MODEL"},
  "participants": {
    "subscription": {
      "adapter": "codex-app-server",
      "identity": {"provider": "codex", "model": "SUBSCRIPTION_MODEL"},
      "timeout": 120,
      "funding": {"mode": "subscription", "profile_id": "PROFILE_ID"}
    },
    "api": {
      "adapter": "openai",
      "identity": {"provider": "openai", "model": "DIFFERENT_API_MODEL"},
      "timeout": 120,
      "funding": {"mode": "api", "credential_env": "OPENAI_API_KEY"}
    }
  },
  "rounds": 1
}
```

Map `codex-app-server` explicitly to consultation identity provider `codex`.
Normalize all three OpenAI transports to the same provider/model comparison.
The same model on subscription and API routes is not independent. Preserve
source-review's distinction from its author and roundtable's distinct seats.
Extend the existing
[identity checks](../../../src/attune_harness/consultation.py#L27-L87) and
[model normalization](../../../src/attune_harness/participant_funding.py#L75-L87).

Registry participants use the same funding object with their existing `model`,
`tools`, `max_turns`, `max_tool_calls` and timeout fields. Do not transplant the
consultation `identity` shape into a registry. Keep review, planning and build
role/tool contracts in
[registry validation](../../../src/attune_harness/review_contract.py#L54-L124) and
[ReviewExchange](../../../src/attune_harness/review_participants.py#L169-L255).
Optional reasoning effort must be explicit and supported by the pinned profile;
unsupported values refuse rather than downgrade.

## Profile lifecycle

Propose three CLI commands, implemented only after approval:

| Proposed command | Required new owner contract |
| --- | --- |
| **`funding connect --name <label>`** | Explicit interactive user consent; bounded loopback OAuth flow; validate identity, granted plan scopes and account/workspace registration; save to Keychain before returning a new opaque `profile_id`. Refuse unavailable storage, invalid callbacks, missing scopes or unsupported eligibility. Never execute a task. |
| **`funding inspect --profile-id <id>`** | Read local nonsecret metadata only. Report missing/expired/unqualified state honestly. Never refresh, open a browser, launch Codex, read native caches or contact a provider. |
| **`funding disconnect --profile-id <id>`** | Block new dispatch and coordinate active sessions; revoke the app-owned grant through the supported endpoint, then clear only this profile's credentials. If remote revocation is unconfirmed, report that explicitly while leaving local dispatch disabled. Never sign out the native CLI. |

These commands have no current `raise` implementation: the current
[parser](../../../src/attune_harness/cli.py#L79-L87) rejects `funding`.
S2 must add the refusal contracts above, structured output and secret-safe
errors. Do not document them as available before that gate passes.

Use the official public-client authorization-code/PKCE flow and a maintained,
pinned OAuth/OIDC validation library. Validate state, nonce, issuer, signature,
audience, expiry, callback and actual token-response scopes. A successful identity
sign-in alone is insufficient plan permission. Follow the documented issued
client registration and resource binding.
[Official sign-in flow](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)

Store tokens, issued client ID, granted scopes and expiry atomically in Keychain;
never fall back to plaintext. Serialize rotating refresh per profile across
processes. Keep private metadata outside checkouts and run directories. Bind an
immutable profile ID to the verified identity/registration. Refresh may preserve
that ID; switching account/workspace requires a new profile and new accepted
configuration. Keep a random stable host identifier and consistent app identity
for the official registration flow. Track credential generation locally;
disconnect, refresh or profile changes invalidate unused admissions. Execution
may refresh a valid grant within its bounded deadline, but never opens an
interactive sign-in flow to repair missing consent.
[Official profile and session lifecycle](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)

Never copy `~/.codex/auth.json`, export refresh tokens to children, use email as
a profile identifier, or expose credentials, auth codes, PKCE material or raw
account identifiers in logs, command arguments, config, receipts or errors.
Opaque local IDs may appear in accepted config and receipts. This boundary
protects normal configuration and dispatch paths; it does not claim to defend
against arbitrary code running as the same operating-system user.

## Runtime and admission

### Qualified runtime profile

S1 must pin the Codex binary/version/hash, upstream source revision, generated
protocol schema, model/effort support, OS/architecture and effective configuration.
The historical funding T1 binary is not automatically qualified for this route.
Unknown versions or changed profiles refuse until separately qualified.
Resolve the executable by the qualified absolute path and verify its identity
again before launch; a different `PATH` entry cannot select another binary.

Create a fresh supervised app-server process and thread for each pending model
turn. Use a private per-invocation `CODEX_HOME` and empty working directory
outside the checkout; never copy user config, plugins or login state. Leave
`HOME` intact. Supply an allowlisted startup environment plus only the admitted
plan access token under an adapter-owned variable. Exclude API keys, proxy and
provider overrides, credential helpers, refresh tokens and unrelated host data.

Fix the official SIWC Responses provider/endpoint, token environment reference,
HTTP/SSE transport, `store:false`, `stream:true` and
`requires_openai_auth=false` configuration. Inspect the
effective configuration and managed requirements, including thread-resolved
configuration, rather than trusting launch flags. An `account/read` result from
Codex's separate login machinery is not funding proof. Protocol operations must
be allowlisted; no login/logout/config-write RPC is part of task execution.
[App-server protocol](https://learn.chatgpt.com/docs/app-server)

Disable native tools, shell, apps, MCP, subagents, automatic compaction/model
follow-ups and inference retries for the qualified profile. S1 must establish
how the pinned implementation enforces this, including startup behavior. If it
cannot prove model-free initialization and one host-authorized logical inference
per turn with bounded transport attempts, stop with an unsupported result.
Reject unexpected tool/approval requests without executing them.

Existing Harness tool proposals remain data: the host can validate and execute
an accepted `retrieve` or `verify` action under existing owners. A model-reply-only
transport does not remove those host contracts or give the app-server native
tool authority.

### Dispatch sequence

1. Under the real run lease, validate accepted config, complete reconstructed
   request, pending operation, role, budgets and current external/native/API
   grants for the whole selected batch. Resolve each profile locally.
2. Refresh a valid plan grant if necessary only within authorized execution;
   serialize refresh and revalidate the unchanged identity/registration. Launch
   the isolated child and inspect only model-free initialization/configuration
   metadata. No task text, model inference or shared-login mutation is allowed
   before admission. Treat these startup effects explicitly in recovery.
3. Persist a names-only admission binding the owner/lease, accepted configuration,
   reconstructed request digest, participant/attempt, profile identity, exact
   model/effort, runtime qualification and private session/thread. A failed save
   prevents task-bearing RPCs. Use a new in-memory, one-use capability tied to
   that live owner; never deserialize an admission from a receipt.
4. Recheck the saved pending-to-dispatching boundary and live profile/session,
   then claim once immediately before `turn/start` sends task content. Reject
   forged, swapped, stale, cross-owner or replayed capabilities. Reuse the
   [existing admission pattern](../../../src/attune_harness/participant_funding.py#L153-L174)
   and [persist-before-issue boundary](../../../src/attune_harness/participant_funding.py#L254-L307),
   extended with subscription-specific bindings.
5. Validate RPC IDs, thread/turn IDs, framing, model identity and the expected
   reply schema. Only the matching successful terminal turn can complete the
   operation. Failed/interrupted/incomplete responses are not successes.
6. Stop the child and descendants and retain cleanup evidence on every path.
   Host history reconstructs subsequent authorized turns; no invisible native
   thread reuse or automatic replay after an unknown outcome.

The existing
[process invocation](../../../src/attune_harness/process.py#L60-L93) is one-shot.
S3 must add a bounded duplex supervisor, retaining its timeout, output and
descendant-cleanup disciplines without changing existing `invoke` behavior.
Apply one monotonic deadline across startup, inference and cleanup, a combined
1,048,576-byte stdout/stderr cap, bounded individual RPC frames and timeout
`1..300` seconds. Check cancellation before dispatch and throughout supervision.
Retain consultation's separate 65,536-byte answer budget and each registry
owner's existing reply limits; the larger transport capture cap does not raise
the accepted answer budget.

The SIWC preview does not support `max_output_tokens`; do not silently reuse or
weaken the direct API request contract. This adapter promises bounded host time,
bytes and authorized attempts, not a server token or dollar ceiling. If the
pinned runtime cannot enforce this profile, it remains unsupported.
[Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)

### Recovery and evidence

Before any task-bearing write, a proved refusal is `not_started`. Once such a
write begins, timeout, cancellation, auth failure, lost replies or process death
may leave model effects uncertain. Preserve the existing unresolved-operation
gate; never relabel uncertainty as a free retry. Stop descendants and require the
owner's supported evidence-based recovery and fresh authority before continuation.
If that owner cannot reconcile the unknown effect, retain the blocked handoff or
explicit abandonment; do not invent a successful recovery. The current
[consultation retry owner](../../../src/attune_harness/consultation_recovery.py#L86-L113)
refuses unknown effects and does not accept a generic subscription error as
proof of a safe retry. Do not
automatically reconnect, resume a native thread, switch profiles or switch to API.

Add a versioned subscription admission/receipt variant, without extending an
exact v1 object with unknown fields. Keep old receipt readers and legacy output
compatible. Retain requested/observed route, match/refusal, allowlisted basis,
opaque profile ID, runtime qualification ID, owner/request binding, dispatch and
cleanup outcome. Credential values and raw provider diagnostics are excluded.

Report validated final token usage when available; missing or contradictory
usage is `unknown`. Do not sum cumulative notifications or count cached tokens
twice. Billed dollars and remaining subscription/API balances stay `unknown`
unless independently evidenced; software receipts are not billing records.

## Command journey and refusal walk

This is a **source/design walk, not an executed subscription journey**. Existing
owner references are pinned by the baseline above. Rows labeled *new* are
required implementation contracts with no current `raise`. The new configuration
must remain refused until those contracts and S1 qualification exist.

Use a canonical project path with one explicit, regular UTF-8 source file, at
most 32 files and 131,072 total captured bytes. Keep config and run state outside
the source checkout. Use two distinct explicitly configured models and a
nonempty question. Do not place credentials in either file.

| Step and command | What its owner refuses | How the preceding input satisfies it |
| --- | --- | --- |
| 1. *New*: **`funding connect --name work-plan`** | New profile owner: invalid/missing consent, callback/identity/scope errors, unavailable protected storage, identity overwrite | User explicitly completes the validated flow; only a successfully stored plan grant yields `profile_id`. Failure ends setup without a task call. |
| 2. *New*: **`funding inspect --profile-id PROFILE_ID`** | New owner: unknown ID; report expired/unqualified state without refresh | Use step 1's opaque ID. Metadata is advisory, not a cached execution grant. |
| 3. **`roundtable check --config /outside/seats.json`** | [Configuration raises](../../../src/attune_harness/consultation.py#L36-L87): strict fields, schema, roster, names, provider/model independence, rounds and timeout; [check](../../../src/attune_harness/consultation_cli.py#L67-L78) reports unavailable routes. New adapter/profile validation must be added. | Use the full example with real distinct models, qualified profile, `rounds:1` and timeout 120. Check stays local/advisory with zero model calls; it cannot promise future entitlement. |
| 4. **`roundtable prepare --project /project --path sample.py --config /outside/seats.json --run-dir /outside/run`** | [Prepare raises](../../../src/attune_harness/consultation.py#L91-L111): operation and run location; [snapshot raises](../../../src/attune_harness/consultation_snapshot.py#L20-L153): canonical root, explicit eligible paths, file/count/byte bounds; [store](../../../src/attune_harness/review_store.py#L61-L73) refuses an unsafe/reused run location | Supply a canonical existing project, selected bounded regular file and fresh external run directory with an existing writable parent. Preparation freezes config/source and returns the exact `contract_digest`; it does not connect or refresh. |
| 5. **`roundtable status /outside/run`** | [Saved-record validation](../../../src/attune_harness/consultation.py#L118-L160) refuses malformed/stale bindings | Inspect step 4's saved contract, snapshot, budgets and digest. This command never dispatches or refreshes a profile. |
| 6. Negative check: **`roundtable run /outside/run --accept DIGEST --allow-external --allow-native`** | [Per-turn funding refusal](../../../src/attune_harness/participant_funding.py#L254-L294) rejects the API seat without fresh API authority; new adapter classification must preserve this before any sibling inference | Use the exact digest but omit API permission deliberately. Expect a funding refusal, a saved paused/prepared boundary and zero task-bearing model dispatches across both seats. |
| 7. **`roundtable run /outside/run --accept DIGEST --allow-external --allow-native --allow-api-spend --max-operations 2`** | [Run raises](../../../src/attune_harness/consultation.py#L390-L433): stale acceptance, missing authority, terminal/unresolved state, operation mismatch/budget; [admission](../../../src/attune_harness/participant_funding.py#L254-L307): owner/request/lease mismatch. New subscription proof can still refuse. | After real operator authorization, use the unchanged prepared digest, both explicit funding policies, step 1's still-valid profile, available API credential and two pending operations. [Funding-refusal handling](../../../src/attune_harness/consultation.py#L511-L522) leaves step 6 paused with no dispatching event, so fresh admission can proceed. A different state fails this journey; stop rather than assuming a retry is safe. |
| 8. Resume with the same **`roundtable run`** shape | Same acceptance/authority gates; unresolved dispatch cannot replay automatically; [batch owner](../../../src/attune_harness/consultation.py#L435-L481) enforces pending/admitted boundaries | Read current saved status/checkpoint. Re-supply all required grants, re-resolve funding and issue fresh admissions for pending turns only. Never use a previous capability or count a refusal as a successful turn. |
| 9. **`roundtable evidence /outside/run`**, then **`roundtable status /outside/run`** | Saved-record/evidence validation; [CLI handlers](../../../src/attune_harness/consultation_cli.py#L63-L115) do not grant execution authority | Read saved turn/route/cleanup evidence from the same run. No provider/account/balance request, profile refresh or model call. |
| 10. *New*, when desired: **`funding disconnect --profile-id PROFILE_ID`** | New owner refuses unknown/invalid profile and disables future admission; report unconfirmed remote revocation | Use the same app-owned ID, coordinate active children, clear only its credential record. Later runs explicitly refuse this profile. |

**`source-review`** uses the same check/prepare/run/status/evidence owner, with
exactly one reviewer, one round and a configured model distinct from the author.
Do not copy the two-seat example unchanged: that is refused at
[configuration line 44](../../../src/attune_harness/consultation.py#L44).
Its operation budget is one pending review turn.

### Registry execution coverage

This table extends the existing workflow contracts; it does not invent new
shortcuts around intake, plan acceptance, testing or effects freezes. Each owner
must reconstruct its accepted request before subscription admission, just as it
does for API admission. Existing per-command flags remain the public authority
surface; there is no invented universal **`--allow-native`** flag.

| Existing executing command/host owner | Refusals and upstream inputs that must remain satisfied |
| --- | --- |
| **`review`** / `review`, `execute_review` | [External authority](../../../src/attune_harness/review.py#L54-L96), exact accepted request and valid registry. Existing accepted review preparation supplies them; new funding adds no implied consent. |
| **`resume-review`** / `resume_review` | [Checkpoint/request/registry/source binding](../../../src/attune_harness/recovery.py#L371-L392). Saved accepted record supplies the exact inputs; new invocation supplies fresh authority. |
| **`test`** / `execute_task`, `execute_assessment` | [Accepted active task/checkpoint/budget](../../../src/attune_harness/task_policies.py#L86-L147) and [assessment source/turn/unresolved checks](../../../src/attune_harness/task_runtime.py#L210-L350). Use the accepted task's frozen source and unexhausted operations. |
| **`fix`**, **`resume`** / `execute_repair` | [Repair gates](../../../src/attune_harness/task_policies.py#L318-L402): failing baseline, immutable acceptance probes, budget and review binding; shared assessment refusals also apply. The prior accepted task and retained failed baseline must satisfy them; a new adapter cannot bypass them. |
| **`plan`** / `plan_work` | [Planning gates](../../../src/attune_harness/work_runtime.py#L781-L942): draft/checkpoint, configured planner and dispatch authority. Existing work intake supplies a nonempty accepted goal and registry; profile state stays outside the checkout. |
| **`build`** / `build_work` | [Build gates](../../../src/attune_harness/work_build.py#L712-L932): accepted build profile, native trial authority, effects/recovery and uncertain operations. Existing accepted work/effects freeze supplies them; include the new adapter in the appropriate native classification. |

S4 must exercise all nine executing entrypoints: source-review run, roundtable
run, review, resume-review, test, fix, resume, plan and build. Both shared caller
paths must refuse stale or missing authority before dispatch and preserve their
own role/tool/budget contracts. The tables are the baseline refusal inventory;
implementation must rewalk it if source owners move or add a refusal.

## Acceptance and qualification gates

| ID | Required evidence |
| --- | --- |
| A1: explicit route | Exact adapter/funding/profile/model selection; isolated child; effective provider/thread config evidence; polluted parent/native cache/helper/proxy/managed settings cannot redirect it. Unsupported configuration refuses before task content. |
| A2: no silent fallback | Auth expiry/revocation, entitlement or quota refusal, unavailable Keychain/binary and unsupported version all stop the selected route. No API attempt, shared-login mutation or model substitution follows. |
| A3: authority and ownership | Every entrypoint, fresh resume grants, forged/stale/swapped/replayed admissions, profile replacement, invalid lease/request and failed receipt persistence are tested. Missing API authority prevents sibling inference. |
| A4: isolation and concurrency | Parallel API/subscription seats and two plan profiles cannot exchange secrets, environment or identity. Refresh races are serialized, parent/shared native state remains unchanged, disconnect prevents new dispatch. |
| A5: bounded lifecycle | Fake duplex server covers malformed/oversized frames, partial writes, stderr floods, wrong RPC/thread/turn/model, unexpected tools, hangs, cancellation, child descendants and cleanup failures. Post-write uncertainty never becomes automatic retry. |
| A6: compatibility | Existing omitted funding, native explicit refusal, API adapter, receipt versions and all command contracts retain their behavior. Same model over different transports fails independence checks. |
| A7: user journey | Installed-wheel local walkthrough of both shared callers and all nine owners; refusal walk updated to implementation raises. No provider call is hidden in prepare/check/status/evidence/inspect. |
| A8: truthful qualification | Source/software receipts are separate from an explicitly authorized minimal live plan/API mixed run. Record exact artifact/platform/models, granted route and observed response; missing live evidence keeps that combination unqualified. No claim of billing or model quality follows. |

Use inert fake servers, OAuth/Keychain doubles and environment witnesses first.
Before shipping, run focused tests, the full suite, wheel build and installed-wheel
platform qualification. Windows behavior needs its own CI evidence and remains
outside initial subscription support. Source changes require recorded independent
review. No live connection, model trial or API spend is authorized by this draft;
present a bounded qualification plan and obtain the applicable authority first.

## Implementation order and stopping points

[Tasks S1–S6](tasks.md) move from route qualification to profiles, transport,
owner integration, offline verification and separately gated live qualification.
S1 is a hard feasibility gate: stop before implementing auth/runtime if the
pinned app-server cannot enforce the proposed restrictions. Retain an honest
unsupported verdict and bring the smallest concrete alternative to Patrick.

[C1](claude-feasibility.md) is independent and read-only at first. It may finish
with insufficient evidence. Its report must never activate a Claude route.

## Decisions for Patrick

All choices below are **recommended, not yet approved**. No implementation starts
from this document alone.

| ID | Recommended decision | Tradeoff and alternative |
| --- | --- | --- |
| D1 | Approve the official plan-OAuth approach, explicit `codex-app-server` adapter and app-owned Keychain profile lifecycle, conditional on S1 | Adds authentication responsibility beyond the previous scope. If that is undesirable, keep subscriptions unsupported and investigate a provider-supported native enforcement mechanism; shared-login status alone cannot substitute. This route must satisfy the intended ChatGPT plan usage, not assume identical native CLI quota accounting. |
| D2 | Limit first qualification to local macOS arm64, one pinned runtime/profile, model replies only and both shared callers | Delivers a bounded mixed-funding journey. More platforms, native tools and broader account/model coverage need later qualification. If S1 disproves feasibility, return a decision rather than expand scope. |
| D3 | Keep Claude as feasibility-only and separate live/account/spending approval from software implementation | Allows Codex to progress without treating Claude uncertainty as support. A later live plan or API experiment needs explicit scope and limits; approval of this spec alone grants none. |

Review [evidence and unresolved assumptions](evidence.md) alongside these
decisions. The complete contract is this README; the companion files provide
task detail, evidence and the separate Claude check.
