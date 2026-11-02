# Decide how to enable a qualified funding route

**Status: API-first revision approved by Patrick on November 2, 2026.**
Patrick selected “Approve API-first revision” and then chose to reuse the existing
API key. The [specification](README.md), this revision and D1–D3 govern the work.

## Why T3 needs a decision

The existing one-shot native adapters have no qualified invocation-level binding
for any of the three explicit funding policies. D3 requires them to refuse.
This is an enforcement limitation; a paid successful request would not resolve it.

For pinned Codex `0.153.4`, CLI overrides are followed by higher-priority
[managed configuration layers](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/config/src/loader/mod.rs#L440-L496).
An effective forced-ChatGPT policy combined with an API override can
[log out shared authentication storage](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/login/src/auth/manager.rs#L1282-L1340).
CLI flags alone do not establish the effective policy required for safe admission.
The [T1 matrix](t1-support-matrix.md) also retains the subscription-route limits.

The native app-server offers
[effective-configuration reads](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server/README.md#L301-L307),
but adopting it would require a bidirectional transport beyond the current
`process.invoke` input/output boundary. It is not a qualified replacement: its
[auth manager disables the exec-only API override](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server/src/lib.rs#L758-L761).

## Recommended revision: add an explicit OpenAI API adapter

Add a separate `openai` adapter for direct OpenAI Platform requests. The
[official API authentication contract](https://developers.openai.com/api/reference/overview#authentication)
supports explicit bearer credentials loaded by the host. This removes the native
CLI's shared-login and managed-configuration selection from that transport.
This is a proposed design direction, not qualified implementation or billing
evidence.

If approved, revise T3–T5 within these limits:

| Area | Proposed revision |
| --- | --- |
| Configuration | Add an explicitly selected `openai` adapter with API funding and the named credential variable in both configuration owners. Keep all existing policies and their current native refusals. Do not silently change a Codex entry's transport |
| Model and role | Keep the user's exact configured model and role. Refuse incompatible capabilities; do not substitute a model or claim equivalence with a Codex CLI runtime |
| Independence | Check OpenAI/Codex identity comparisons deliberately so a transport change alone cannot create a distinct reviewer |
| Request | Use the official OpenAI Responses endpoint with the selected API credential and bounded task content. No native login, auth-cache copying, credential migration, automatic fallback or implicit ambient-client defaults |
| Authority | Retain every existing acceptance/effects/external gate and add the approved fresh `--allow-api-spend` authority at execution and resume |
| Evidence | Reuse the existing owner and journal; persist admission before sending, redact before saving, retain uncertain effects, and distinguish reported usage from unknown billed cost/balance |
| Qualification | Exercise both shared caller paths with offline request witnesses, run the full suite and installed-wheel checks, and obtain the required source review. Report platform and live-provider evidence separately |
| Subscription support | Keep explicitly selected Claude/Codex subscription routes unsupported until invocation enforcement is qualified. Omitted funding retains the approved legacy behavior |

This revision changes the original exclusion of a direct model API client.
It does not promise that subscription enforcement is complete or that every
configured Codex model is available through the API. No live model call is
required to build or verify the software boundary. Any later live qualification
must remain within Patrick's separately authorized scope and spending allocation.

## Alternative: retain the native-only scope

Complete only the refusal/reporting and compatibility groundwork under D3.
All explicit routes remain unsupported. Mark positive invocation, concurrency
and completed/uncertain funded-call acceptance as open; do not call the original
integration complete. API spending remains unnecessary.

## Current continuation evidence

The candidate now returns R2's structured unsupported funding report from
**`source-review check`** and **`roundtable check`**, exits 2, keeps model
availability unknown and makes no auth/version probe for explicitly funded
seats. The focused funding, preflight, compatibility-surface and golden-envelope
run passed 167 tests. This does not qualify a live funding route. Full source,
wheel and platform results from T2 predate this inspection change; this
continuation has not rerun them or obtained a new independent source review.

## Implementation boundary

Use a supervised stdlib Python child for the direct HTTPS request, reusing the
existing process supervisor. Its private environment contains only selected OS
startup variables and the selected API credential. The worker fixes the official
Responses endpoint, disables proxies and redirects, uses no SDK ambient defaults,
and makes one bounded request with no retry. The body requests the existing outer
text schema, has no tools, disables response storage and bounds output tokens.
It does not add a configurable endpoint or replace a native transport silently.

The owner prepares each journal event, resolves a private admission, persists its
names-only evidence, then marks dispatching and permits the exchange. Refusal
stays prepared, launches nothing and consumes no completed-call slot. Replay of a
completed event needs no fresh admission; pending/resumed calls require fresh
authority. Receipts bind configuration, participant, turn and attempt number.
Model replies cannot construct admission or control metadata. Host evidence steps
use no model admission. A failed admission write cannot activate the exchange.

Admission requires the real owner's active writer lease and a validated saved
contract. Shared pure request builders bind the complete model request, including
task constraints, before dispatch. At the single-use claim, the adapter reads the
saved owner again and requires the same pending, dispatching event and matched
funding evidence. Public capability fields, arbitrary stores and later request
binding cannot create spending authority. This is a library boundary, not a
sandbox against Python code that can replace private internals.

Process output is bounded and stripped from saved direct-API process diagnostics;
only validated answer, response identity, normalized usage and allowlisted failure
evidence survive. Credential echoes are redacted before parsing or error creation.
Malformed replies remain invalid even when usage is present. Existing owner
schemas validate optional funding evidence on reload, including prior attempts.
Full-suite and installed-wheel checks follow focused failure and replay tests.
