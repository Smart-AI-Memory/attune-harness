# Codex subscription implementation tasks

**Status: Draft, not executable until Patrick approves the specification and
its decisions. No implementation has started.** November 3, 2026.

The [README](README.md) owns scope, requirements, refusal walk and acceptance
criteria. These tasks do not grant account access, model selection, spending,
workflow dispatch, publication or merge authority. Use ordinary reviewed PRs;
do not carry the prior named PR's merge delegation forward.

## S1 — Qualify the proposed mechanism

Dependencies: spec approval, including D1 and D2. No live account/model call.

Inspect official documentation and the exact candidate Codex binary's source,
help and generated protocol schema using bounded model-free witnesses. Record
version, executable path/hash, upstream source SHA, schema hash, OS/architecture
and the configuration needed for the SIWC provider. Verify private `CODEX_HOME`,
configuration/managed-policy precedence, thread overrides, environment handling,
entitlement reporting limits, startup behavior and lifecycle APIs.

Prove that initialization is model-free, task content is withheld until admission,
native tools/apps/MCP/subagents and automatic compaction/model follow-ups are
disabled, and inference/transport attempts have a finite enforced bound. Verify
whether the intended local use and plan accounting meet the documented conditions.
Do not infer native CLI quota equivalence from an OAuth token or model catalog.

Done when: a source-cited runtime profile and inert witness receipts support every
restriction in the README, or an explicit unsupported/unknown verdict identifies
the first failed requirement. Negative evidence is a finished S1 handoff. It is
not permission to relax requirements, choose another provider or start a paid
trial. Return any required scope change to Patrick before S2 or S3.

## S2 — Add the app-owned profile lifecycle

Dependencies: successful S1, approved D1. Own the proposed **`funding connect`**,
**`funding inspect`** and **`funding disconnect`** contracts.

Implement public-client OAuth/OIDC with a maintained pinned validation library,
loopback callback validation and protected Keychain storage. Make account/client
registration immutable per profile. Serialize refresh and atomically replace
rotating credentials. Separate private metadata from secrets; reject pasted keys,
tokens, unsafe storage and account replacement. Disconnect invalidates admissions
and prevents new dispatch even if remote revoke cannot be confirmed.

Done when: OAuth/Keychain doubles cover cancellation, replayed callbacks, invalid
state/nonce/issuer/audience/signature/expiry, missing granted scopes, identity
switch, refresh races/crashes, missing Keychain and partial revocation. Inspection
is network-free. All errors and outputs pass secret-redaction checks. No real
login or native credential access is required to complete these software tests.

## S3 — Add the bounded app-server transport

Dependencies: successful S1; S2 profile interface available. Preserve the existing
one-shot process API and native/direct API adapters.

Implement a supervised duplex session using the pinned schema. Use private
per-turn config/cwd and a startup environment allowlist. Permit only qualified
initialization, config inspection, thread creation, one admitted turn and
termination operations. Enforce deadlines, framing/output bounds, request and
response identity, unexpected request refusal and descendant cleanup.

Done when: fake-server tests exercise every A5 failure and verify zero task text
before final admission, no native tool execution, no automatic reconnect/replay,
no child access to API/refresh credentials and no mutation of shared native state.
Any impossible profile restriction returns to S1 as unsupported, not a workaround.

## S4 — Integrate funding and both shared callers

Dependencies: S2 and S3. Extend strict configuration and model identity mapping;
do not rewrite existing saved configs or v1 receipts.

Add the mandatory subscription policy and opaque profile reference. Bind and
persist route evidence under the real owner/lease before issuing a one-use
capability; claim at the actual dispatch boundary. Cover consultation and
registry callers, planning/build role contracts, the README's model-dispatching
entrypoints and each resume path. Keep the separate deterministic **`test`**
path free of model dispatch and funding admission. Preserve whole-batch admission
before inference. Extend each native
classification explicitly; do not invent flags absent from that command.

Done when: A1–A4 and A6 pass, including polluted environment/config, disconnected
or replaced profile, failure to persist, stale/forged/cross-owner/replayed
capability, same-model independence, missing API grant with a subscription
sibling, cancellation, resumed uncertainty and concurrent refresh. API-only
behavior and inherited native behavior remain compatible. Read back the new
receipts; no credential values or raw account identity may appear.

## S5 — Verify the installed software and user journey

Dependencies: S4. This is software qualification, not a live funding verdict.

Run focused tests and the full suite. Build/install the wheel in a fresh
environment, then run the platform qualifier against it. Walk the README's
journey and all registry owners against inert fixtures; replace proposed owner
contracts with implementation `raise` citations. Include a clean no-API-grant
mixed-seat refusal and an uncertain-dispatch recovery case. Keep the public
support table conditional until live route evidence exists.

Done when: reproducible artifact-bound receipts pass A1–A7, no hidden provider
call occurs in local inspection/preparation, and independent review covers the
current source changes. Retain failures honestly; do not edit old evidence to
match new code. Windows/other-platform checks cannot establish subscription
support outside the approved initial profile.

## S6 — Separately authorize and qualify a minimal live route

Dependencies: S5, explicit approval for the account connection, selected models,
scope and limits of live qualification. No such approval is granted here.

Present the exact candidate wheel/runtime/profile and a bounded plan: one small
subscription turn, one deliberately mixed API/subscription journey and relevant
failure evidence already obtained offline. State expected API spend, call/attempt
bounds, subscription quota use and what happens on uncertain output. Request
only the still-missing authority; reuse an already authorized credential choice
when it remains applicable. Never expose a secret in the plan.

Done when: the approved live sample supports A8 or a refusal/blocker is retained.
Compare parent/shared login state before/after without reading or copying secrets.
Record observed route, response and usage limits; do not invent charges, remaining
balances or model-quality conclusions. Read back evidence and complete the normal
review/merge handoff. Release and merge remain separately gated.

## C1 — Claude feasibility, independent of S1–S6

Follow [the separate check](claude-feasibility.md). Start with docs/source/help
and inert witnesses only after authorization to execute that check. It may run
independently of Codex tasks. Its verdict never enables Claude dispatch or
inherits Codex OAuth custody. A supported implementation requires its own spec.

## Completion discipline

At meaningful handoffs, re-anchor on usable explicit mixed funding, inspect the
actual evidence, update the relevant refusal walk and retain any unsupported
result. Completion review is part of done, not authority to implement additional
opportunities. Finish each task with a current-head reviewable result and the
smallest concrete decision if a gate cannot be met.
