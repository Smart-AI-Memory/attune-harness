# Codex subscription support alongside API credits

**Status: App-owned OAuth/Keychain lifecycle approved; S1 qualification authorized.**
Written November 3, 2026 against main
`03e29647a02073089fb33ea8df45b75be65383ba`. This planning pass changes
documentation only. On November 3, 2026, Patrick approved the app-owned
OAuth/Keychain lifecycle and directed the spec update and start of S1, with
Claude feasibility separate and advance notice before any API credits are needed.
Runtime support remains unqualified. No account connection, native authentication
probe or model call has qualified the proposed route.

S1 result: **not qualified for the required single-inference boundary**. The
[qualification report](s1-qualification.md) records the pinned candidate,
model-free witnesses, source findings and the decision needed before S2.

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
excluded credential management. Patrick explicitly approved this extension on
November 3, 2026 (D1 below); it does not reinterpret the earlier scope.

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
| 7. **`roundtable run /outside/run --accept DIGEST --allow-external --allow-native --allow-api-spend --max-operations 1`** | [Run raises](../../../src/attune_harness/consultation.py#L390-L433): stale acceptance, missing authority, terminal/unresolved state, operation mismatch/budget; [admission](../../../src/attune_harness/participant_funding.py#L254-L307): owner/request/lease mismatch. New subscription proof can still refuse. | After real operator authorization, use the unchanged prepared digest, both explicit funding policies, step 1's still-valid profile, available API credential and two pending turns. [Funding-refusal handling](../../../src/attune_harness/consultation.py#L511-L522) leaves step 6 paused without a dispatching event. The [batch limit](../../../src/attune_harness/consultation.py#L445-L453) admits one turn; require its successful completed answer and `status:paused`, leaving the second turn pending. A failed or uncertain turn stops this walk. |
| 8. Inspect with **`roundtable status /outside/run`**, then resume with **`roundtable run /outside/run --accept DIGEST --allow-external --allow-native --allow-api-spend`** | Same acceptance/authority gates; [saved-record raises](../../../src/attune_harness/consultation.py#L118-L144) reject malformed bindings, and [batch owner](../../../src/attune_harness/consultation.py#L425-L481) rejects mismatched/unresolved operations | Step 7 supplies one completed turn and one pending turn. Preserve the contract and original directory. Re-supply all required grants and issue fresh funding admission only for the pending turn; the completed result replays without dispatch. Omit the per-invocation limit so this successful one-round run reaches `completed`. Never resume a terminal run or treat uncertain effects as pending work. |
| 9. **`roundtable evidence /outside/run`**, then **`roundtable status /outside/run`** | Saved-record/evidence validation; [CLI handlers](../../../src/attune_harness/consultation_cli.py#L63-L115) do not grant execution authority | Read saved turn/route/cleanup evidence from the same run. No provider/account/balance request, profile refresh or model call. |
| 10. *New*, when desired: **`funding disconnect --profile-id PROFILE_ID`** | New owner refuses unknown/invalid profile and disables future admission; report unconfirmed remote revocation | Use the same app-owned ID, coordinate active children, clear only its credential record. Later runs explicitly refuse this profile. |

### Source review

Use a separate `/outside/source-seat.json` with the same nonempty question and
explicit author identity, exactly one qualified subscription reviewer and
`rounds:1`. The reviewer must use a model distinct from the author. Prefix every
command in these tables with `attune-harness`; paths and digests are placeholders.

| Step and command | What its owner refuses | How preceding steps produce and preserve valid input |
| --- | --- | --- |
| S1. **`source-review check --config /outside/source-seat.json`** | [Configuration raises](../../../src/attune_harness/consultation.py#L36-L87) reject a two-seat roster, multiple rounds, same author/reviewer model, invalid question/adapter/funding/timeout. New adapter/profile validation remains required. | Derive a separate one-seat file from the proposed configuration; retain only the explicitly selected reviewer and author, with a bounded question and timeout 120. Current code refuses the new adapter; check grants no execution permission. |
| S2. **`source-review prepare --project /project --path sample.py --config /outside/source-seat.json --run-dir /outside/source-run`** | [Prepare raises](../../../src/attune_harness/consultation.py#L91-L111), [snapshot raises](../../../src/attune_harness/consultation_snapshot.py#L20-L153) and [store raises](../../../src/attune_harness/review_store.py#L61-L114) reject noncanonical/unsafe/oversized source or overlapping/reused state. | Reuse the bounded regular source from roundtable step 4 and S1's valid one-seat config, with a fresh external directory and writable parent. Save the returned contract digest `SOURCE_DIGEST`; source/config are frozen in this owner. |
| S3. **`source-review status /outside/source-run`**, then **`source-review run /outside/source-run --accept SOURCE_DIGEST --allow-external --allow-native`** | [Record raises](../../../src/attune_harness/consultation.py#L118-L144) reject copied/malformed bindings; [run raises](../../../src/attune_harness/consultation.py#L390-L433) reject stale acceptance, missing authority, terminal or unresolved state; new subscription admission can refuse. | Inspect S2's original prepared record, then explicitly authorize its one pending review turn using the exact digest and still-valid profile. This subscription-only example has no API seat. A valid completed reply finishes the run; failure or uncertainty stops it. No per-invocation pause limit is needed. |
| S4. **`source-review evidence /outside/source-run`**, then **`source-review status /outside/source-run`** | Same saved-record validation and [operation-match raise](../../../src/attune_harness/consultation_cli.py#L85-L86). | Read S3's retained answer, funding and cleanup evidence from the same owner using the matching command. Inspection neither dispatches nor refreshes. |

### Existing command coverage

The nine named command surfaces are source-review run, roundtable run, review,
resume-review, test, fix, resume, plan and build. They are not nine registry
execution owners: today's **`test`** uses deterministic pytest, with
[no participant registry](../../../src/attune_harness/test_cli.py#L76-L120), and
[its continuation](../../../src/attune_harness/task_policies.py#L97-L99) branches
before assessment dispatch. Keep it free of funding admission and model calls.

The following ordered walks extend existing contracts. They do not authorize
execution or make the proposed adapter valid today. Reuse the qualified profile
from roundtable steps 1–2; authoritative config/profile/response/state files stay
outside captured source. The plan starter's byte-identical local registry copy
is created before its effects freeze. Each registry schema differs from the
consultation schema: use
its explicit role/tool/budget fields rather than copying `seats.json`. All
subscription validation, admission and native classification below remain new
S4 work. Existing per-command flags remain the authority surface; there is no
universal **`--allow-native`** flag. API authority is fresh per executing invocation.

### Evidence review and review continuation

Use the legacy positional-request path deliberately; **`resume-review`** continues
that schema, whereas the newer **`review --goal ...`** task path continues with
**`resume`**. The parser refuses mixing the two forms
([mode raises](../../../src/attune_harness/task_cli.py#L98-L104)). Commands below
are current parser shapes; accepting `codex-app-server` remains new S4 work.

| Step and command | What its owner refuses | How preceding steps produce and preserve valid input |
| --- | --- | --- |
| R1. Write `/outside/evidence/participants.json`, `/outside/evidence/context.json` and a bounded Markdown corpus; then **`review-form --config /outside/evidence/participants.json`** | [Registry raises](../../../src/attune_harness/review_contract.py#L54-L123): schema/roster/adapter, exact keys, supported unique tools, model/funding and turn/tool/timeout bounds; [feature raises](../../../src/attune_harness/features.py#L23-L38) refuse missing/unqualified libraries. | Finalize a `schema_version:1` registry with two named participants, using the proposed plan seat and API seat's explicit distinct models/funding. Both have `tools:["retrieve","verify"]`, `max_turns:3`, `max_tool_calls:2`, `review_mode:"evidence"`, `timeout:120`; no extensions or paid retrieval. The new adapter must extend registry validation; today it is refused. Use a supported environment with attune-forms 0.17.0, attune-verify 0.6.0 and attune-rag 1.2.0. Create regular UTF-8 `/outside/evidence/project/guide.md` and `reference.md`, and context `{"schema_version":1,"project_root":"project"}`. Keep request/config at most 131,072 bytes, guide/context at most 65,536 bytes and the unchanged local corpus below 1,000 Markdown files/16 MiB. The form command returns the exact registry-bound `submission` template without dispatch. |
| R2. Save only the returned `submission` object as `/outside/evidence/request.json`, fill its seven answers and explicitly accept it | [Acceptance raises](../../../src/attune_harness/review_contract.py#L155-L174): exact schema/answer keys, `accepted:true`, current form revision, nonempty bounded answers and distinct selected participants/models; [preparation raises](../../../src/attune_harness/review.py#L17-L50) and [corpus raises](../../../src/attune_harness/recovery.py#L45-L56) reject missing/out-of-corpus/oversized inputs. | Preserve R1's `schema_version` and `form_revision`; set `objective` and `query` to concrete nonempty text, `document:"project/guide.md"`, `context:"context.json"`, `corpus:"project"`, and `lead`/`reviewer` to the distinct R1 identities. Put the accepted request beside the context and corpus so relative paths resolve correctly. The guide lies inside both corpus and declared project root, satisfying [verification raises](../../../src/attune_harness/verification.py#L23-L39). Keep registry, request and all source bytes unchanged through R5. |
| R3. **`review /outside/evidence/request.json --config /outside/evidence/participants.json --run-dir /outside/evidence/run --allow-external --allow-api-spend --max-operations 1`** | [Review gates](../../../src/attune_harness/review.py#L54-L84) reject missing external authority, invalid API-authority type and unqualified funding; [pause-limit raise](../../../src/attune_harness/recovery.py#L147-L150) rejects an invalid limit; [store raises](../../../src/attune_harness/review_store.py#L61-L114) reject unsafe/reused location or unavailable writer lease. | Use R2's accepted request and exact R1 registry, after real authorization for both routes. `/outside/evidence/run` must not exist; its parent must exist and be writable. S4 must admit the newly qualified plan adapter; current [strict funding refusal](../../../src/attune_harness/participant_funding.py#L53-L72) remains until then. The first [assessment operation](../../../src/attune_harness/task_runtime.py#L261-L266) is local preflight verification: completing that single operation triggers the [saved pause](../../../src/attune_harness/recovery.py#L170-L182), leaving retrieval and both participant assignments pending. Require `status:paused` with that completed preflight; a failure/uncertain dispatch is a different case and must stop this walk. |
| R4. **`inspect-review /outside/evidence/run`** | [Record raises](../../../src/attune_harness/review_store.py#L158-L177) reject malformed schema/checkpoint/status; inspection reports running state as uncertain. | Inspect the original R3 directory and copy its current `checkpoint_digest`; confirm paused state and only a completed preflight. No registry/request/corpus edits and no record copying. Inspection grants no execution permission. |
| R5. **`resume-review /outside/evidence/run --request /outside/evidence/request.json --config /outside/evidence/participants.json --checkpoint CHECKPOINT --allow-external --allow-api-spend`** | [Recovery raises](../../../src/attune_harness/recovery.py#L276-L290) reject unsupported profile/state, stale checkpoint and copied ownership; [resume raises](../../../src/attune_harness/recovery.py#L365-L392) reject inactive state or changed accepted request/registry/source; [unresolved gate](../../../src/attune_harness/recovery.py#L511-L521) rejects uncertain effects. Shared [assessment raises](../../../src/attune_harness/task_runtime.py#L226-L234) and [dispatch raises](../../../src/attune_harness/task_runtime.py#L386-L415) preserve fresh inputs, correlated requests and owned funding admission. | R4 supplies the exact checkpoint, R1–R2 preserve the binding and R3 supplies a completed operation with no unresolved dispatch. Re-supply external/API authority and resolve fresh plan/API admission for each pending model turn; do not replay an old capability. The runtime reuses completed preflight, performs retrieval and validates each participant's bounded/correlated actions and final response. Future model/tool/schema failure remains a real stop, not something setup can guarantee away. Inspect the same directory again to read the outcome; `completed` alone does not mean the document was verified. |

### Task-oriented evidence review and continuation

**`review --goal`** reaches the registry-backed `execute_task` /
`execute_assessment` owners; **`test`** reaches the separate pytest-change owner and
does not dispatch registry participants. Use installed review dependencies,
regular bounded `/review-project/docs/guide.md`, a trusted
`/review-project/context.json` whose `project_root` is `docs`, and a small
keyword corpus `/review-project/docs`. Keep `/outside/intake.json`,
`/outside/response.json`, `/outside/review-seats.json` and the fresh task directory
outside that corpus. The explicit registry selects `alpha` and `beta` with the same evidence-role
fields and bounds as R1, distinct identities/models, no retrieval extension and
the proposed funding/profile contracts. New adapter validation/admission remains S4 work; this source walk is
not a currently executable subscription route or live-call authorization.

| Step and command | What its owner refuses | How earlier steps produce and preserve the required input |
| --- | --- | --- |
| M1. **`review --goal "Check the guide against evidence" --project /review-project --config /outside/review-seats.json --plan independent-review --document docs/guide.md --context context.json --corpus docs --query "retention policy" --criteria "Preserve uncertainty" --assessor alpha --reviewer beta --task-dir /outside/modern-review --intake-only < /dev/null > /outside/intake.json`** | [Mode refusals](../../../src/attune_harness/task_cli.py#L80-L104): mixed legacy/new intake, conflicting flags; [answer refusals](../../../src/attune_harness/task_contract.py#L46-L58): incomplete/unknown or duplicate identities; [evidence refusals](../../../src/attune_harness/task_contract.py#L102-L156): paths escaping the project, corpus/state overlap, non-Markdown document, invalid context/project binding; [feature loader](../../../src/attune_harness/features.py#L23-L38) refuses missing/incompatible dependencies. | Prepare the named regular document/context and existing bounded corpus first; the context's root contains the document. Explicit `alpha`/`beta` match the registry; every required answer is supplied. Closed stdin makes this the headless path, with no implicit interactive acceptance. It returns a draft (exit 1) and [a `submission`](../../../src/attune_harness/task_cli.py#L25-L41) containing exact task ID, revision, form revision, checkpoint, answers and false permissions. No participant call occurs. |
| M2. Prepare `/outside/response.json` from **only** M1's `submission`; retain its ID/revision/form/checkpoint/answers and explicitly set `accepted: true`, `permissions: {"external": true, "provider": false}`. | [Acceptance raises](../../../src/attune_harness/task_contract.py#L403-L443) refuse another profile, replayed approval, missing/extra fields, false acceptance, stale/foreign response, incomplete answers, invalid permission booleans or changed inputs. | The operator reviews the exact complete M1 scope and supplies real external-execution authority. Preserve all generated binding fields rather than constructing their values. Keyword retrieval needs no provider grant. This is preparation of the genuine bound response, not an edit to the saved record or a source of fresh API permission. |
| M3. **`review --task-response /outside/response.json --task-dir /outside/modern-review --pause-after 2 --allow-api-spend`** | [Response-mode refusals](../../../src/attune_harness/task_cli.py#L90-L97) reject intake overrides, `--config`, `--accept`, `--allow-external` and `--allow-provider`; [acceptance raises](../../../src/attune_harness/task_contract.py#L403-L443) still apply. [Execution raises](../../../src/attune_harness/task_policies.py#L108-L126) reject stale checkpoint, draft/cancelled state, stale evidence, missing saved external/fresh API authority or insufficient budget; [shared owner](../../../src/attune_harness/task_runtime.py#L226-L234) refuses changing inputs. | M2 provides the intact current response with saved external authority; supply fresh API permission only when separately authorized. The CLI [accepts then invokes `execute_task`](../../../src/attune_harness/task_cli.py#L112-L163), which binds the accepted request/roles and calls `execute_assessment`. Default 100 operations covers its five-operation independent assessment. `--pause-after 2` completes [local preflight and initial keyword retrieval](../../../src/attune_harness/task_runtime.py#L261-L280), leaving both model assignments and final verification pending. This intentionally produces a paused active owner, not a completed review. |
| M4. **`status /outside/modern-review`** | [Record validation](../../../src/attune_harness/task_contract.py#L215-L276) and [execution validation](../../../src/attune_harness/task_policies.py#L150-L180) refuse foreign ownership, invalid acceptance, changed role bindings, malformed execution or budget overflow. | Read M3's same retained task and its current `checkpoint_digest` as `MC`. Require the expected completed preflight/retrieval prefix and no unresolved dispatch; retain registry/source/context byte identity. Inspection performs no model call. |
| M5. **`resume /outside/modern-review --checkpoint MC --allow-api-spend`** | [Nonfeature resume](../../../src/attune_harness/task_cli.py#L254-L262) refuses `--allow-external` or `--allow-native`; saved intake permissions apply. [Task gates](../../../src/attune_harness/task_policies.py#L108-L146), [freshness raises](../../../src/attune_harness/task_contract.py#L298-L311), and [continuation refusal](../../../src/attune_harness/recovery.py#L511-L521) reject stale checkpoint/config/source or uncertain dispatch. Per-turn funding/reply/schema/answer-budget gates remain mandatory. | M4's current checkpoint names the paused accepted owner produced by M3. Saved external permission is unchanged; fresh API authority and new subscription admission must be supplied/rechecked for pending model turns. Completed local operations replay their retained results rather than execute again. Only valid bounded final replies from both assigned models, unchanged source and completed final verification permit completion; read final status afterward. |

### Planning, acceptance and build

This is a proposed-adapter source walk, not an authorization to execute it. Use a
small, dedicated local Git clone `/build-project` on macOS with an existing
`sample.py`, distinct protected `tests/test_sample.py`, and a qualified absolute
Python interpreter `/qualified/python` with pytest. `/outside/work` must not
exist, and neither it nor the request, authoritative registry, profiles, or
credentials may be inside the effect checkout. `/outside/work-seats.json` is an
explicitly authored
registry with `schema_version:1` and a `participants` map containing distinct
`lead` and `reviewer` models, `tools:[]`, `max_turns:3`, `max_tool_calls:2`,
`timeout:120`, no `review_mode`, and qualified explicit adapters/funding. New
`codex-app-server` registry support/classification remains an S4 contract, not
current behavior; current registry validation refuses that adapter. Do not use an
`init` review profile as a build participant configuration.

| Step and command | What its owner refuses | How earlier steps produce and preserve the required input |
| --- | --- | --- |
| P1. Before freezing, copy the explicit registry into the dedicated clone: **`cp /outside/work-seats.json /build-project/participants.json`** | [Registry loader](../../../src/attune_harness/task_contract.py#L30-L34) and [registry validator](../../../src/attune_harness/review_contract.py#L52-L125) reject invalid/unsupported fields, adapters, assignments and budgets. [Planning](../../../src/attune_harness/work_runtime.py#L854-L889) and [build](../../../src/attune_harness/work_build.py#L740-L760) reject missing roles, tools/review policies and missing authority. | Prepare and validate the explicit external registry first; use a fresh clone without a preexisting `participants.json`. The local byte-identical copy exists before the snapshot. The external original is the later `--config`; leave both unchanged. No profile credential belongs in either file. |
| P2. **`init --for plan --goal "Repair sample behavior" --project /build-project --scope sample.py --interpreter /qualified/python --tests tests/test_sample.py --task-dir /outside/work`** | [Starter raises](../../../src/attune_harness/init_cli.py#L327-L367): missing goal/scope/interpreter/tests, existing task/request, oversized request; [freeze raises](../../../src/attune_harness/work_effects.py#L243-L259): overlapping state and checkout or linked/non-Git checkout; [manifest](../../../src/attune_harness/work_effects.py#L72-L142): missing/overlapping/protected paths and [build preflight](../../../src/attune_harness/work_build.py#L95-L128): task/probe/role/budget mismatch. | P1 supplies the two named participants before freeze. Existing regular `sample.py` and test file have distinct roles and no missing parent; the test and interpreter are frozen as protected `change` and `final` probes. `init` creates a nonempty goal, acceptance criterion, planner/worker/reviewer assignments, one `change` task, default budgets, and frozen effects, then writes `/outside/work.work.json` **after** the freeze, outside the checkout ([construction](../../../src/attune_harness/init_cli.py#L275-L313), [write order](../../../src/attune_harness/init_cli.py#L348-L371)). No model call or scope acceptance occurs. |
| P3. **`plan --request /outside/work.work.json --project /build-project --config /outside/work-seats.json --task-dir /outside/work`** | [CLI raises](../../../src/attune_harness/work_cli.py#L546-L622): missing project/config, old checkpoint, unsupported request fields; [capture raises](../../../src/attune_harness/work_contract.py#L340-L365): noncanonical/missing project, overlapping state, nonregular or symlink evidence; [effects-binding raises](../../../src/attune_harness/work_effects.py#L348-L371): out-of-scope or mismatching preimages. | P2's generated request uses only supported fields and binds the unchanged source/probes. The explicit external config matches the local copy P2 used. A fresh external task directory is created; inspect its `draft`, missing questions and exact checkpoint `C0`. Do not edit the effect checkout, registry, probes or interpreter after the freeze. |
| P4. **`plan --task-dir /outside/work --run --checkpoint C0 --allow-external --allow-native --allow-api-spend`** | [Planning raises](../../../src/attune_harness/work_runtime.py#L792-L889): nondraft/stale checkpoint, changed evidence, changed resumed authority, missing planner, duplicate planner/critic, insufficient budget, unsupported required control, missing external/native/API authority, or tools/review policy. [Funding admission](../../../src/attune_harness/participant_funding.py#L254-L294) separately rejects stale owner/lease/request/funding. | P3 produces the current unaccepted draft with a complete nonempty intent and configured planner; P2's starter uses no critic, unresolved questions or required planning controls. The explicit no-tool registry satisfies role policy. Only separately authorized dispatch supplies these grants; API funding also needs the explicit credential, and the new subscription route must pass fresh admission. A valid bounded planner reply must complete the planning journal; inspect the returned checkpoint `C1`. Refusal or uncertainty ends this path; it is not a valid staged proposal. |
| P5. **`plan --task-dir /outside/work --stage --checkpoint C1`** | [Staging raises](../../../src/attune_harness/work_runtime.py#L945-L982): stale checkpoint, incomplete proposal, stale evidence; proposal/task validation and [revision gates](../../../src/attune_harness/work_contract.py#L775-L847) also apply. | Use P4's completed, validated proposal only if it preserves this bounded example's `change` task ID, `sample.py` output, protected-probe mapping, acceptance coverage and empty unresolved choices. Staging retains a new **unaccepted** revision outside the checkout; inspect its exact current checkpoint `C2`. If the proposal changes the frozen task/probe shape or scope, stop and revise/freeze a compatible request through the supported workflow rather than passing that contradiction to build. |
| P6. **`plan --task-dir /outside/work --accept --checkpoint C2`** | [CLI acceptance raises](../../../src/attune_harness/work_cli.py#L475-L505): stale checkpoint, blocked Spec execution gate or no grant; [complete draft](../../../src/attune_harness/work_accept.py#L394-L399), [acceptance binding](../../../src/attune_harness/work_contract.py#L548-L598) and [fresh draft](../../../src/attune_harness/work_contract.py#L730-L743) refuse incomplete/material intent, missing planner, unsupported controls, stale/foreign receipt, changed evidence or replay. | P5 supplies a fresh complete draft with the original nonempty goal, explicit acceptance and compatible effects; the real operator reviews that exact scope and the owning Spec collector records its decision. Only a successful accepted record supplies build authority. Copy the resulting current checkpoint `A`; P6 grants no paid/native dispatch. |
| P7. **`build /outside/work --checkpoint A --allow-external --allow-native --allow-api-spend --max-operations 1`** | [Effect owner raises](../../../src/attune_harness/work_runtime.py#L306-L319): wrong checkpoint/status, missing effects, changed registry; [build preflight](../../../src/attune_harness/work_build.py#L95-L128): incompatible tasks/outputs/probes/roles/budgets; [build raises](../../../src/attune_harness/work_build.py#L725-L817): unsupported policy/platform, missing authority, changed resumed authority, stale source or unresolved dispatch. | P6's accepted current checkpoint and P2's unchanged manifest/protected probes/config satisfy ownership and preflight. The one-task starter needs five durable operations (worker reply, one file write, task probe, final probe, final review); its default budget is 100 ([defaults](../../../src/attune_harness/task_contract.py#L18)). P5 must preserve that exact shape. Fresh real dispatch grants and both funding checks remain required. `--max-operations 1` stops after the successful worker reply, leaving the file effect and checks pending, so a later authorized **`resume`** has actual remaining work. No unresolved operation is treated as replayable. |
| P8. **`status /outside/work`** | [Saved feature-work validation](../../../src/attune_harness/work_contract.py#L601-L697) rejects copied/foreign ownership, malformed status/bindings and inconsistent journals; [build freshness](../../../src/attune_harness/work_build.py#L293-L312) rejects changed config/interpreter. | Read the same retained owner and its paused build journal from P7; no model call or credential refresh. Use its current checkpoint and existing recovery rules before any continuation. |
| P9. **`resume /outside/work --checkpoint BUILD_CHECKPOINT --allow-external --allow-native --allow-api-spend`**, then **`status /outside/work`** | [Feature-work routing](../../../src/attune_harness/task_cli.py#L249-L255) selects the work owner; [accepted-owner raises](../../../src/attune_harness/work_runtime.py#L306-L319), [build gates](../../../src/attune_harness/work_build.py#L725-L817) and [cursor raises](../../../src/attune_harness/recovery.py#L191-L211) reject stale bindings, changed grants, inputs or unresolved dispatch. | P8 supplies the paused build checkpoint. Preserve its accepted manifest and registry, and re-supply the same external/native grants plus fresh API authority. The completed worker reply replays without a call; remaining file effects and immutable probes execute through their host owners, and the pending reviewer needs fresh funding admission. Require the final probes and artifact-bound review to pass; failure stops the build. |

The successful P4/P5 proposal is a conditional source path, not an assumption that
an arbitrary model response preserves task IDs. If the goal is to exercise build
without a model planning proposal, P2/P3's complete one-task starter may instead
be accepted directly at P6 using P3's current checkpoint; do not claim that this
alternative executed **`plan --run`**.

### Deterministic test and continuation

Prepare an exclusively owned Git repository `/test-project` with a real working-tree change to `src/example.py`, a pytest test under `tests`, and an external executable `/venv/bin/python` containing pytest and project dependencies. Keep task state, preview output and incidental test outputs outside captured inputs or in existing ignored paths. Existing source/test/config/interpreter identity must stay unchanged from preview through continuation. No participant config or funding flags apply.

| Step and command | What its owner refuses | How the preceding input satisfies it |
| --- | --- | --- |
| T1. **`test --project /test-project --scope src/example.py --interpreter /venv/bin/python --task-dir /outside/test-task`** | [Intake raises](../../../src/attune_harness/test_change.py#L54-L95): missing scope, unsafe storage, unsupported platform, invalid interpreter/limits/options and changing snapshot; [capture/selection raises](../../../src/attune_harness/test_scope.py#L67-L114), [changed-scope raise](../../../src/attune_harness/test_scope.py#L157-L163) | The prepared repository is its real Git root, with bounded regular non-symlink inputs and an actual changed file. The interpreter is executable, defaults fit the limits and the new task directory is external. This command freezes the request/selection/interpreter identity and returns a draft with `checkpoint_digest`; it executes no tests or model calls. |
| T2. **`test --task-dir /outside/test-task --checkpoint TEST_PREVIEW_CHECKPOINT --accept --pause-after 1`** | [CLI raise](../../../src/attune_harness/test_cli.py#L79-L102): saved acceptance cannot override inputs; [acceptance/freshness raises](../../../src/attune_harness/test_change.py#L247-L275); [execution raises](../../../src/attune_harness/test_change.py#L300-L307) | After the operator accepts T1's actual selected/excluded coverage, copy its exact draft checkpoint and pass no input overrides. Unchanged inputs satisfy freshness. It runs the single accepted pytest operation, saves its completed event, then the [operation-limit raise](../../../src/attune_harness/recovery.py#L170-L181) deliberately pauses before final projection. This is a saved complete pytest event, not a pending model turn. |
| T3. **`status /outside/test-task`**, then **`resume /outside/test-task --checkpoint TEST_PAUSED_CHECKPOINT`** | [Test execution raises](../../../src/attune_harness/test_change.py#L300-L307): stale checkpoint or draft; [cursor raises](../../../src/attune_harness/recovery.py#L191-L211): changed operation or unresolved dispatch | Read T2's current paused checkpoint and verify its pytest event completed. Preserve its inputs and interpreter. **`resume`** reaches the test owner through `execute_task`; the cursor reuses the saved completed event, validates artifacts and finishes without rerunning pytest. An incomplete/uncertain event fails this walk and must be inspected, not automatically retried. |
| T4. **`status /outside/test-task`** | [Saved test profile/binding validation](../../../src/attune_harness/test_change.py#L141-L243) and [freshness raises](../../../src/attune_harness/test_change.py#L247-L262) | The same saved identity, acceptance and evidence remain bound. Inspect the actual outcome: `completed` alone does not establish passed tests, and all-skipped/collection-only is not passing evidence. |

### Repair and repair continuation

Prepare a small dedicated clone `/repair-project/checkout` with a local `.git` directory, existing UTF-8 `src/math.py`, and a protected `tests/probe.py` that fails with a positive exit code for the known bug. Create `/outside/probe.json` with exactly `argv:["/venv/bin/python","tests/probe.py"]`, `cwd:"."`, `timeout:30`, `max_output_bytes:65536`, `environment:{"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1"}` and `oracle_paths:["tests/probe.py"]`. Prepare `/outside/participants.json` with explicitly selected action-transport worker `alpha` and required reviewer `beta`, distinct configured models and explicit adapters/funding. Use `schema_version:1` with a `participants` map; each participant has `tools:[]`, `max_turns:3`, `max_tool_calls:2`, `timeout:120` and no `review_mode`. Keep task/config/probe JSON/response files outside the checkout before snapshotting; the task directory is outside the project. All checkout entries, including `.git`, must satisfy the bounded regular-file/snapshot profile. Do not edit the clone, registry, executable or oracle after capture.

| Step and command | What its owner refuses | How the preceding input satisfies it |
| --- | --- | --- |
| F1. **`fix --goal "Repair addition" --project /repair-project --checkout /repair-project/checkout --scope src/math.py --probe /outside/probe.json --config /outside/participants.json --worker alpha --reviewer beta --review required --criteria "The frozen probe passes without changing its oracle" --task-dir /outside/fix-task --intake-only`** | [CLI mode refusals](../../../src/attune_harness/task_cli.py#L331-L345); [repair intake raises](../../../src/attune_harness/task_contract.py#L515-L555); [probe raises](../../../src/attune_harness/repair.py#L121-L165); [freeze raises](../../../src/attune_harness/repair.py#L168-L218); [review-policy/transport/model raises](../../../src/attune_harness/task_contract.py#L490-L509) | The prepared project contains the dedicated clone; listed replacement and oracle files exist, are disjoint, canonical and bounded; the executable is outside the clone; the frozen minimal environment and probe limits are valid. The real nonempty goal/criteria and distinct selected identities satisfy answer checks. This command creates a fresh draft and freezes scope, file preimages, probe, registry and generated `submission`; no worker or probe is dispatched. |
| F2. Save F1's returned `submission` as **`/outside/fix-response.json`** after the operator reviews that exact scope; set `accepted:true` and the authorized `permissions.external:true` (retain `permissions.provider:false`) | [Acceptance raises](../../../src/attune_harness/task_contract.py#L403-L442): wrong profile/state, absent acceptance, foreign/stale task/revision/form/checkpoint, incomplete answers, invalid permissions or changed inputs | Preserve the generated task ID, revision, form revision, checkpoint and complete answers. Only the operator's actual scope/external authorization permits setting those two fields. Creating the response outside the frozen clone preserves the scope snapshot. `--allow-api-spend` is separate invocation authority and is not stored in this response. |
| F3. **`fix --task-dir /outside/fix-task --task-response /outside/fix-response.json --allow-api-spend --pause-after 2`** | [Response-mode refusal](../../../src/attune_harness/task_cli.py#L331-L336): no input/permission overrides; [accepted task/checkpoint/binding gates](../../../src/attune_harness/task_policies.py#L100-L123); [repair budget/baseline raises](../../../src/attune_harness/task_policies.py#L318-L371); [external-authority raise](../../../src/attune_harness/review.py#L54-L57), per-turn funding admission | F2 is bound to F1; use only task/response and runtime flags. Default accepted budget 100 exceeds `2 + assignments + allowed files` (5 here). The saved external permission remains true and API spending is fresh for this invocation. First, the immutable baseline probe must fail normally with positive exit; then the authorized worker turn may complete. The operation limit saves these two completed events and pauses before any replacement. A passing/unknown baseline or refused/unresolved turn ends this path. Current subscription configuration is refused; the proposed adapter must add qualified fresh admission before that turn. |
| F4. **`status /outside/fix-task`**, then **`resume /outside/fix-task --checkpoint FIX_PAUSED_CHECKPOINT --allow-api-spend`** | [Non-feature resume flag refusal](../../../src/attune_harness/task_cli.py#L254-L262): do not add `--allow-external`/`--allow-native`; [task freshness raises](../../../src/attune_harness/task_contract.py#L298-L306); [unresolved-continuation raise](../../../src/attune_harness/recovery.py#L511-L521); [proposal/probe/review raises](../../../src/attune_harness/task_policies.py#L367-L393) | Read F3's actual paused checkpoint and verify both baseline and worker events completed, with no unresolved dispatch. Preserve the original clone/registry/oracle. Saved external permission applies; re-supply API authority for the pending reviewer only. The cursor reuses baseline/worker evidence, validates and applies only the bound existing-file replacement, requires the unchanged final probe to pass, and requires the configured reviewer to approve the exact artifact/probe with no findings. New subscription admission is fresh only for pending model work, never a replay of prior capabilities. |
| F5. **`status /outside/fix-task`** | [Execution identity/assignment/budget raises](../../../src/attune_harness/task_policies.py#L150-L180); [expected snapshot/freshness](../../../src/attune_harness/task_contract.py#L298-L306) | The same accepted request and saved event-derived after-state remain intact. Read failed-before/passed-after and exact review evidence. A completed task is verification within its immutable probe scope, not general correctness or model qualification. |


S4 must cover every model-dispatching owner above and retain the dispatch-free
test path. Preserve each caller's role, tool, budget and recovery checks. The
walks show conditional successful responses; malformed responses, failed checks,
changed inputs and uncertain effects remain real stops. Rewalk the tables when
implementation adds or moves refusals.

## Acceptance and qualification gates

| ID | Required evidence |
| --- | --- |
| A1: explicit route | Exact adapter/funding/profile/model selection; isolated child; effective provider/thread config evidence; polluted parent/native cache/helper/proxy/managed settings cannot redirect it. Unsupported configuration refuses before task content. |
| A2: no silent fallback | Auth expiry/revocation, entitlement or quota refusal, unavailable Keychain/binary and unsupported version all stop the selected route. No API attempt, shared-login mutation or model substitution follows. |
| A3: authority and ownership | Every entrypoint, fresh resume grants, forged/stale/swapped/replayed admissions, profile replacement, invalid lease/request and failed receipt persistence are tested. Missing API authority prevents sibling inference. |
| A4: isolation and concurrency | Parallel API/subscription seats and two plan profiles cannot exchange secrets, environment or identity. Refresh races are serialized, parent/shared native state remains unchanged, disconnect prevents new dispatch. |
| A5: bounded lifecycle | Fake duplex server covers malformed/oversized frames, partial writes, stderr floods, wrong RPC/thread/turn/model, unexpected tools, hangs, cancellation, child descendants and cleanup failures. Post-write uncertainty never becomes automatic retry. |
| A6: compatibility | Existing omitted funding, native explicit refusal, API adapter, receipt versions and all command contracts retain their behavior. Same model over different transports fails independence checks. |
| A7: user journey | Installed-wheel local walkthrough of both shared callers and all nine named command surfaces, including the dispatch-free test path; refusal walk updated to implementation raises. No provider call is hidden in prepare/check/status/evidence/inspect. |
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

Patrick approved D1 and directed S1 to start on November 3, 2026. S1 retains
the bounded initial profile in D2. Claude remains a separate feasibility track;
no live/account/model qualification or API spend is authorized by this approval.
S2–S6 remain unstarted and depend on the S1 result and their stated gates.

| ID | Recommended decision | Tradeoff and alternative |
| --- | --- | --- |
| D1 | Approved: app-owned plan OAuth/Keychain lifecycle; app-server remains conditional on S1 | Adds authentication responsibility beyond the previous scope. Shared-login status alone cannot substitute. The route must satisfy intended ChatGPT plan usage; native CLI quota equivalence is unproved. |
| D2 | Applied to authorized S1: local macOS arm64, one pinned runtime/profile, model replies only and both shared callers | More platforms, native tools and broader account/model coverage need later qualification. S1 did not clear the execution bound; see its report before expanding scope. |
| D3 | Confirmed: keep Claude feasibility separate; notify Patrick before any API credits are needed | Claude uncertainty does not imply support or delay a qualified Codex path. Live account/model experiments retain separate scope and authority. |

Approval record: D1 is approved; D2 defines the authorized S1 qualification
scope; D3's separation and advance-notice boundary are confirmed. Approval does
not resolve the technical assumptions or qualify an account/model combination.

Review [evidence and unresolved assumptions](evidence.md) alongside these
decisions. The complete contract is this README; the companion files provide
task detail, evidence and the separate Claude check.
