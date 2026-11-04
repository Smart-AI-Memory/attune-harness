# Direct plan OAuth transport design

**Status: Design revision authorized November 3, 2026. Documentation only;
implementation and live qualification have not started.**

This design replaces the proposed Codex app-server transport after its
[S1 stop-gate result](s1-qualification.md). Patrick approved the direct OAuth
design revision while retaining Keychain/funding contracts, keeping Claude
feasibility separate, requiring notice before API credits are needed and saying
“No code changes yet.” Original receipts and the original S1 report stay intact.

## Contract and scope

The proposed adapter is **`openai-plan`**, with mandatory funding exactly
`{"mode":"subscription","profile_id":"<opaque-local-id>"}`. Consultation
identity provider is `openai`; registry entries retain their existing explicit
`model` and role/tool budgets. Normalize this adapter, native `codex` and API-key
`openai` to the same provider/model identity for independence checks.

The API-key adapter remains **`openai`** with mandatory API funding and fresh
**`--allow-api-spend`** for each executing/resuming invocation. The new adapter
cannot accept an API-key credential reference, arbitrary token, endpoint or
fallback. Funding is established by the admitted credential/grant and fixed
request route, not by a hostname shared by both transports.

Retain the approved OAuth/Keychain lifecycle: explicit user consent, validated
OIDC identity and granted plan scopes, immutable opaque profile identity,
protected atomic credential storage, serialized rotating refresh and explicit
disconnect/revocation. No plaintext fallback, copied native auth/cache, shared
login mutation or credential material in run state is introduced.

Initial scope remains local macOS arm64, one qualified Python/HTTPS/SSE request
profile, text replies and both shared callers. This adapter launches no native
provider CLI and needs external execution authority. Native authority remains
required for actual native seats and any applicable existing owner gate. Host
retrieval, verification, file proposals and effects retain their original owners.

The goal is subscription access alongside API credits. This mechanism directly
uses a ChatGPT plan grant; native Codex CLI allowance equivalence and account/
model eligibility remain unproved. No model is selected or substituted here.
No balance, billed-dollar or model-quality claim follows from route validation.

## Official request basis

OpenAI documents bearer plan-token inference at the public Responses endpoint,
streamed completion and account-specific model discovery. The initial Harness
flow uses an explicitly configured model and has no model picker or implicit
catalog request. A later catalog feature needs its own explicit contract.
[Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)

The preview requires an input array, `store:false` and `stream:true`, and omits
several normal Responses fields. It does not support `max_output_tokens`.
Therefore this worker has its own request profile; it cannot copy the current
API adapter's wire body unchanged.
[Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)

The grant/identity checks stay with the approved profile owner. OAuth access
tokens are opaque bearer credentials; do not apply API-key syntax rules or infer
funding from a token prefix. Expiry/scopes/identity come from validated stored
grant metadata and supported refresh, not a model request.

## One host-controlled inference request

Use a separate one-shot standard-library worker, isolated with the established
Python `-I -S` process pattern. Select the qualified interpreter/worker by trusted
absolute paths. The [existing process supervisor](../../../src/attune_harness/process.py#L60-L93)
already supports a bounded one-shot process; no duplex RPC supervisor is needed.

The worker has a fixed `HTTPSConnection`-style transport with normal certificate
and hostname verification, no proxy/environment configuration loader, no SDK
retry middleware, no redirect handling and no credential-helper invocation.
The implementation must demonstrate those properties; naming a library alone
does not qualify them. Pin interpreter/stdlib/SSL behavior and worker source in
the installed artifact's qualification record.

| Property | Required value |
| --- | --- |
| Method and endpoint | One `POST https://api.openai.com/v1/responses` at most per admitted pending model turn |
| Credential | Only that turn's admitted plan access token; never an API key or native login |
| Headers | Fixed bearer authorization, JSON content type, SSE accept type; no arbitrary caller-supplied headers or organization/project routing |
| Automatic retries, redirects, reconnects | Zero, including auth/rate-limit/server errors and partial-stream failure |
| Model requests beyond the initial POST | None: no follow-up, repair, provider tool result, compaction, summary request, polling or response-ID continuation |
| Other provider requests during inference | None: no model/account/catalog/usage/balance/status probe |
| Native execution | No Codex/Claude CLI, app-server, tools, shell, MCP, apps or subagents |

The request limit counts client inference attempts. It cannot describe internal
provider compute or impose a server token/dollar ceiling.

### Wire-body allowlist

Require exactly the qualified shape: `model`, `instructions`, `input`,
`store:false`, `stream:true`, plus `reasoning:{"effort":...}` only if explicitly
accepted and qualified for that model/profile. No other body fields are enabled
in the initial profile. Unsupported effort refuses; it is never dropped or
downgraded. If a requested tuple cannot be qualified, it stays unsupported.

```json
{
  "model": "EXPLICIT_ACCEPTED_MODEL",
  "instructions": "Complete only the accepted Harness task. Return a JSON object with one string field named text.",
  "input": [
    {
      "role": "user",
      "content": "COMPLETE_OWNER_RECONSTRUCTED_REQUEST"
    }
  ],
  "store": false,
  "stream": true
}
```

This is a design example, not a live command. The host reconstructs the complete
accepted request, including frozen context and allowed prior history; callers
cannot replace it with a shorter question. No secret is part of the prompt.

Omit provider `tools`, `additional_tools`, `previous_response_id`, conversation,
background and unsupported sampling/budget/metadata fields. The first profile
also omits server structured-output controls: instruct the required text
envelope and validate it locally. A malformed reply fails this attempt; it does
not generate a repair call. Later server-schema support would need separate
model/profile qualification rather than silent request changes.

The [existing API exchange](../../../src/attune_harness/openai_exchange.py#L71-L87)
uses a string input, token cap and JSON-schema response request. Keep its API
behavior intact. Share only proven compatible parsing, redaction, usage and
process helpers; do not share credential-mode acceptance or the wire body by
accident. The [existing API worker](../../../src/attune_harness/openai_worker.py#L1-L43)
also demonstrates bounded one-shot supervision, not subscription qualification.

## Admission, secrets and concurrency

1. Hold the real owner's run lease. Validate the saved acceptance, complete
   reconstructed request, registry/role/budget, pending operation and fresh
   execution authority. Check every selected participant's static funding
   requirements before any sibling inference. API-funded seats still need
   their fresh spending grant when pending. Completed turns replay without a
   new admission, profile refresh or spending requirement.
2. Resolve the accepted opaque profile locally. If an existing consented grant
   needs refresh, refresh before inference within the same bounded execution,
   serialize rotation and revalidate identity/client/scopes. Never connect a
   missing account or prompt for consent during task execution.
3. Build and freeze the exact wire bytes and method/endpoint/profile. Persist
   names-only evidence binding the real owner/lease, accepted config, complete
   request and wire digests, attempt/participant, model/effort, profile identity/
   credential generation and qualified worker profile. Save failure sends no
   inference request and issues no reusable authorization.
4. Issue a private one-use capability and recheck/claim it at the same live
   pending-to-dispatching boundary. Reuse the existing
   [owner/request claim discipline](../../../src/attune_harness/participant_funding.py#L153-L174)
   and [persist-before-issue pattern](../../../src/attune_harness/participant_funding.py#L254-L307).
   Do not deserialize saved receipts into capabilities or accept a fake cursor.
5. Supply the access token only to the admitted child in an adapter-owned
   environment variable. Child stdin contains the bounded request/control
   envelope, not token material. Exclude API keys, native/provider variables,
   proxy/endpoint overrides, refresh/ID tokens and unrelated host environment.
6. Supervise, validate, save the result and release the private capability on
   every path. A future model turn reconstructs owner history and obtains a new
   admission; the current worker cannot continue its own conversation.

Refresh/profile changes invalidate unused capabilities by credential generation.
Profile lifecycle updates must atomically exclude new claims. Already claimed
attempts are active dispatches: disconnect requests cancellation and reports
possible effects, without promising to undo an already-started request. Serialize
refresh consistently with owner leases and profile locks; test concurrent owners
for deadlocks and identity swaps. Never hold a credential lock across user input.

Keep at least the existing secret-redaction strength, including escaped and
nested echoes. Raw HTTP bodies, headers, tokens, callback data, email/account IDs
and raw process diagnostics never become public errors or run receipts. No
streamed delta is shown before final validation/redaction in this first slice.

## SSE and response contract

Consume SSE inside the bounded worker. Validate HTTP status/content type,
UTF-8, frame boundaries, JSON object uniqueness/depth and the qualified event
schema. Correlate all response/item identifiers with the same response. Validate
event order and any sequence fields according to the qualified schema; do not
invent ordering guarantees from delta arrival alone.

Only a single matching `response.completed` with final completed status, no
error/incomplete details, the exact configured model and supported completed
assistant text can produce a result. Accept reasoning items only as permitted
by the profile; never expose private reasoning as the task answer. Validate the
final text envelope. The exchange constructs its returned owner-bound digest
from the frozen request; it does not trust a digest invented by the model.
No alias/canonical-model substitution is implicit.

Read through the terminal event and stream end under the deadline. Missing,
conflicting or repeated terminal responses, unexpected provider tool/function
items, failed/incomplete responses, explicit error events and interrupted streams
fail the attempt. `[DONE]` or a text delta alone is insufficient completion.
Usage-limit errors may arrive after streaming begins; no partial text is a
success. [Completion/error handling](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)

No provider tool request is executed or returned to the model. A Harness action
encoded in the validated assistant text remains a proposal for the existing
host-owned tool/role contract; it can cause another model turn only through
that owner's remaining budget and a new admission.

## Bounds and honest recovery

| Resource | Bound |
| --- | --- |
| Total accepted execution deadline | `1..300` seconds, monotonic; profile resolution/refresh, startup, network and cleanup use remaining time |
| Serialized wire body | 1,048,576 UTF-8 bytes; refuse before network I/O |
| Private worker stdin envelope | 3,000,000 UTF-8 bytes, including JSON escaping/control fields |
| HTTP stream capture | 1,048,576 bytes total |
| Individual SSE frame | 262,144 bytes |
| Combined process stdout/stderr | 1,048,576 bytes |
| JSON nesting | 32 |
| Accepted task answer | Existing caller limit; consultation remains 65,536 bytes |
| Inference HTTP requests per admitted model turn | At most one; zero automatic retries, redirects and reconnects |

Enforce remaining deadlines on reads/writes, including slow/trickling streams;
an idle socket timeout alone is insufficient. Parent cancellation kills/reaps
the worker and descendants. A request cap does not establish a server output-token
or billing cap. **`--allow-api-spend`** remains an authority flag, not a dollar cap.

Only positive pre-write evidence may establish `not_started`. Once inference
request writing begins, conservatively preserve possible external effects on
HTTP/auth/quota errors, transport loss, invalid output, timeout or cancellation.
The trusted worker's phase evidence must be distinguishable from provider data;
an error message or exit code cannot invent a safe retry.

Do not react to 401 by refreshing and resending, or to 429/5xx by retrying. Leave
the run at its real saved failure/uncertainty boundary. Existing owner-supported
recovery and fresh authority are required; where unknown effects cannot be
reconciled, preserve a blocked handoff or explicit abandonment. Never replay a
completed model call to obtain better formatting or usage evidence.

Persist a versioned subscription receipt, preserving strict v1 compatibility.
Keep requested/observed route, allowlisted basis, opaque profile and worker/profile
IDs, owner/config/request binding, start/terminal/cleanup outcomes and validated
final usage. Normalize final counts without adding cumulative deltas twice.
Missing/contradictory counts, billed dollars and remaining balances stay unknown.
An HTTP response or grant check is not a billing receipt. A separately configured
API seat retains its own prior authority; a plan-seat failure never creates an
API fallback request for that seat.

## Required software qualification

Implementation remains unstarted. Before any live qualification, S2–S5 must
produce artifact-bound evidence for the following:

- Profile lifecycle with OAuth/Keychain doubles: scope/identity/callback refusal,
  atomic refresh, concurrent owners, revocation and no plaintext fallback.
- Request-counting inert HTTPS/SSE fixtures: zero POST on rejected admission,
  at most one POST otherwise, no redirect/auth/error retry, no second request
  after unexpected tool output or malformed text, and no hidden catalog probe.
- Fixed host/path, verified TLS, no proxy/default-env influence, token/API-key
  separation, secret redaction and same-model identity across transports.
- Framing/deadline/cancellation tests: partial writes, slow streams, oversize,
  malformed/duplicate JSON, inconsistent IDs/models, missing/failed/conflicting
  completion, worker crash and descendant cleanup. Preserve uncertainty.
- Every model-dispatching owner from the corrected README walks, real
  pause/resume with pending work, fresh grants/admissions and batch refusal;
  the deterministic test/resume path remains dispatch-free.
- Focused/full tests, wheel build, installed-wheel platform qualification and
  recorded independent review of the actual source changes.

Inert transport fixtures must not add a production endpoint/proxy override or
test-token fallback to the public worker/configuration surface.

These future checks qualify software behavior. Account/plan/model permission,
native Codex allowance equivalence and live route evidence remain separate S6
questions. State the proposed live scope and usage before any call or API credit
is needed. No such call or spend is authorized by this design revision. Claude
C1 remains separate and unstarted.
