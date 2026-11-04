# Subscription OAuth implementation tasks

**Status: S2–S5 implementation approved November 4, 2026; software verification
in progress. S6 and Claude C1 remain separate and unstarted.**

The [README](README.md) owns the funding/authority contract and corrected command
walks. The [direct OAuth design](direct-oauth-design.md) owns the revised worker/
request/stream contract. Patrick retained Keychain and funding contracts, kept
Claude separate, required notice before API credits are needed and expressly
said “No code changes yet.” The later S2–S5 approval grants implementation and inert software checks only.
It grants no account/model experiment, API spending, merge, release or manual
workflow authority.

## S1 — Original app-server qualification: completed with a stop gate

The [retained S1 report](s1-qualification.md) records the candidate binary/source/
schema and model-free observations. It did not establish the required single-
inference boundary. Do not rerun, relabel or edit that evidence to qualify the
direct worker.

Patrick subsequently authorized the direct OAuth design revision (D4). That
revision replaces the proposed mechanism, preserves the one-client-request
boundary and leaves direct software/live qualification outstanding. The later D5 approval authorizes S2–S5 software work; it does not authorize a
provider request.

## S2 — Add the approved app-owned profile lifecycle

Dependencies: explicit authorization to implement the revised design. D1's
OAuth/Keychain lifecycle approval is already recorded; do not ask for it again.

Implement the proposed **`funding connect`**, **`funding inspect`** and
**`funding disconnect`** contracts using maintained pinned OAuth/OIDC validation
and protected macOS Keychain storage. Bind immutable identity/client/scopes to
each opaque profile, serialize rotating refresh and atomically replace tokens.
Keep metadata outside checkout/run stores. Refuse pasted credentials, unsafe
storage, missing scopes and account replacement.

Disconnect atomically excludes new claims and invalidates unused capabilities.
Coordinate cancellation of already claimed work and report possible effects;
remote revoke failure must not re-enable local dispatch. Inspection stays local
and never refreshes or contacts a provider.

Done when: OAuth/Keychain doubles prove state/nonce/callback/signature/issuer/
audience/expiry/scope refusals, identity switches, atomic refresh/crash behavior,
concurrent owners/deadlock avoidance, missing storage and partial revocation.
Outputs pass redaction checks. No live sign-in or credential access is required
for the software tests.

## S3 — Add the single-request HTTPS/SSE worker

Dependencies: code authorization and the S2 profile interface. Preserve the
existing API-key adapter, its wire body and existing one-shot process API.

Implement the **`openai-plan`** exchange and isolated standard-library worker.
Freeze the host-reconstructed request before admission; allow only the qualified
plan body, fixed verified HTTPS endpoint, one POST and bounded SSE parsing.
Use private child environment/token handling and the existing supervisor. No
native CLI, duplex RPC, SDK defaults, redirects, retries, tool executor,
catalog/status call, remote conversation continuation or repair inference.

Done when: request-counting inert fixtures prove zero POST before accepted
admission and at most one afterward, including 3xx/401/429/5xx, timeout, partial
write/stream, malformed text and unsolicited provider tool outputs. Verify TLS/
host/path behavior, proxy/environment exclusion, final event/model/ID/text
validation, framing/byte/deadline bounds, cancellation and descendant cleanup.
Missing/failed completion never becomes success or automatic retry. No actual
model call is needed. Record exact worker/interpreter/request qualification.

## S4 — Integrate funding and both shared callers

Dependencies: S2 and S3. Extend strict configuration and normalized model identity.
The new adapter requires the unchanged subscription profile reference; API-key
`openai` remains API-only. Legacy omitted funding and native explicit refusals
remain compatible. No config, accepted request or v1 receipt is silently migrated.

Bind and persist names-only admission under the real owner/lease before issuing
a private one-use capability; recheck and claim against the exact complete
request, model, profile/generation and worker profile. Never deserialize a
receipt into authority. API funding still requires fresh spending permission.

Cover consultation, registry, planning/build role/tool contracts and each
model-dispatching/resume owner in the corrected README walks. This transport
does not become a native CLI seat; preserve actual native-seat and owner-specific
authority. Keep the separate deterministic **`test`** path dispatch-free.
Preserve all-member admission before selected sibling inference.

Done when: A1–A4 and A6 pass for stale/forged/cross-owner/swapped/replayed claims,
profile rotation/replacement/disconnect, failed persistence, polluted API/native/
proxy settings, same-model independence, concurrent profiles and missing API
authority with a plan sibling. Completed work never re-dispatches on resume;
pending work requires fresh grants and admissions. Receipts remain secret-free.

## S5 — Verify installed software and corrected user journeys

Dependencies: S4. This is software qualification, not a live funding verdict.

Run focused tests, the full suite, wheel build and installed-wheel platform
qualification. Walk both shared callers and all nine named command surfaces
with inert fixtures, including the dispatch-free test path. Preserve #333's
ordered input-producing walks: source-review, positional review/resume-review,
task-oriented review/resume, plan/build, test/resume and fix/resume.

Replace proposed-owner contracts with real implementation refusal citations.
Verify a paused run actually has pending work before resume, missing API grant
causes zero sibling inference, inspection is network-free and uncertain effects
remain a real stop. No local check/prepare/status/evidence/inspect operation
implicitly connects, refreshes or probes entitlement.

Done when: artifact-bound A1–A7 evidence passes and recorded independent review
covers current source changes. Retain every failure honestly. Other platforms
and untested Python/request/model profiles stay unsupported. The old app-server
receipts and successful direct software tests cannot supply missing live proof.

## S6 — Separately authorize minimal live route qualification

Dependencies: S5 and explicit authority for the chosen account connection,
models, bounded live scope and usage. No such authority is granted by this
design revision. Notify Patrick before any API credits are needed; do not carry
a historical allowance forward.

Present the candidate wheel/worker/request profile, one small plan turn and a
minimal mixed API/plan journey. State call/attempt limits, expected API spend,
plan quota use, missing billing evidence and the stop on uncertain results.
Reuse an already applicable credential choice rather than requesting a new
API key unnecessarily. The plan grant is distinct from the API-key credential.

Done when: an approved sample supports A8, or an honest refusal/blocker remains.
Record exact model/effort/platform/artifact and observed route/terminal/cleanup/
usage. Verify the intended account's model and plan permission; do not infer
native Codex quota equivalence, charges, balances or model quality. No automatic
fallback follows a limit. Merge and release remain separately gated.

## C1 — Claude feasibility, independent

The [separate Claude check](claude-feasibility.md) remains unstarted. It begins
with docs/source/help and inert witnesses only when its execution is authorized.
Its verdict never enables Claude dispatch or inherits OpenAI OAuth custody.
Negative/unknown Claude findings do not block a qualified direct plan route.
A supported Claude implementation requires a separate proposal and authority.

## Completion discipline

At meaningful handoffs, inspect evidence against usable explicit mixed funding,
update source-bound refusal walks and preserve unsupported results. Completion
review is part of done; it grants no additional implementation, spending or
scope. A concrete gated handoff is preferable to silently weakening the contract.
