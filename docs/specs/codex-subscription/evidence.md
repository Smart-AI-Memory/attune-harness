# Evidence and unresolved assumptions

**Status: Direct OAuth design revision authorized; documentation/source evidence
only. No direct-worker implementation or live qualification.** November 3, 2026.

The [README](README.md) contains the active funding/authority contract and
corrected command walks; the [direct design](direct-oauth-design.md) specifies
the new transport. The [original app-server S1 report](s1-qualification.md) stays
unchanged and unqualified for its single-inference gate. A different mechanism
does not turn historical evidence into a pass.

## Verified repository basis

Source baseline: `03e29647a02073089fb33ea8df45b75be65383ba`. The S1 follow-up
was integrated on main `65b90234792c61db8e539567930443aee91ceff0`; the relevant
funding/consultation/registry/process sources were unchanged. This design pass
began at `9ebad0988de5e4e99142473381af6793e2227781`.

| Observed source | Implication |
| --- | --- |
| [Funding validation/refusal](../../../src/attune_harness/participant_funding.py#L16-L72) accepts only existing adapter/policy fields and refuses native explicit routes | `openai-plan` and `profile_id` remain proposed. They must not fall through to native or API-key auth. |
| [Model identity](../../../src/attune_harness/participant_funding.py#L75-L87) and [consultation configuration](../../../src/attune_harness/consultation.py#L36-L87) | Add explicit plan-to-OpenAI identity mapping; the same model across transports cannot create independence. |
| [One-use claim](../../../src/attune_harness/participant_funding.py#L153-L174) and [real-owner admission](../../../src/attune_harness/participant_funding.py#L254-L307) | Preserve reconstructed request, live owner/lease, persistence and private capability checks; extend with plan profile/generation and wire-profile binding. |
| [Batch admission](../../../src/attune_harness/consultation.py#L435-L481) and [single-use participant attempt](../../../src/attune_harness/adapters.py#L84-L104) | Preserve admission before sibling inference and no implicit re-dispatch of the same attempt. |
| [Registry schema](../../../src/attune_harness/review_contract.py#L54-L124) and [exchange roles](../../../src/attune_harness/review_participants.py#L169-L255) | Extend the direct adapter explicitly, retaining host review/planning/build tool and role contracts. |
| [One-shot process supervision](../../../src/attune_harness/process.py#L60-L93) | A supervised single-request worker fits this interface; the duplex app-server primitive is no longer proposed. |
| [Current API wire body](../../../src/attune_harness/openai_exchange.py#L71-L87) and [worker](../../../src/attune_harness/openai_worker.py#L1-L43) | API-key requests use a different body/response transport. Reuse compatible helpers only; preserve API semantics and use a separate plan wire profile. |
| [Native build authority](../../../src/attune_harness/work_build.py#L754-L761) | The new HTTP adapter is not a native CLI seat. Preserve grants for actual native seats and all other existing owner gates. |

## Official sources, checked for this revision

These sources describe a candidate protocol, not this account's entitlement or
an implemented/qualified Harness worker. Recheck changing preview conditions
during implementation and before live qualification.

| Source | Relevant fact |
| --- | --- |
| [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference) | Documents direct plan bearer-token Responses requests, streaming completion and explicit account-specific model discovery. Terminal completion is required; usage-limit failure may arrive after streaming starts. |
| [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) | Requires input array, `store:false` and `stream:true`; excludes `max_output_tokens` and several normal Responses controls. A plan body cannot copy the API-key body unchanged. |
| [Sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) | The approved profile owner validates identity and actual granted plan permission; successful identity sign-in alone is insufficient. |
| [Profiles and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions) | Approved storage/refresh/revocation obligations remain part of the profile owner. This revision does not move refresh/ID tokens into workers. |
| [Local/open-source token sharing](https://developers.openai.com/siwc/token-sharing-open-source) | Applicability and eligible plan access require verification; hosted/commercial qualification remains outside initial scope. |
| [Errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery) | Authentication, consent, entitlement and stream errors require explicit handling. This worker's stricter one-attempt contract never silently refreshes/retries or changes funding. |

Claude sources and provider conditions stay in the [separate feasibility
document](claude-feasibility.md). C1 remains unstarted.

## Assumptions still requiring evidence

1. **Direct-worker enforcement:** the implemented/pinned worker must prove one
   POST, verified fixed TLS host/path and no retries, redirects, tools, probes
   or SDK/ambient defaults. A proposed architecture is not a software receipt.
2. **Bounded streaming:** time, wire/answer bytes, frame/JSON limits, matching
   completion/model/text and cancellation/cleanup must be exercised with inert
   fixtures. They do not create a server output-token/dollar ceiling.
3. **Account/model eligibility:** the chosen account's grant and explicit model/
   effort must work for the intended plan route. Native Codex allowance
   equivalence remains unproved; no catalog or login label establishes it.
4. **Credential lifecycle:** OAuth/OIDC validation, Keychain custody, atomic
   rotating refresh, concurrency and revocation must satisfy the already
   approved contract. Approval has resolved the scope decision, not proved the
   implementation.
5. **Usage:** normalize validated final counts without summing cumulative events;
   unavailable/contradictory data, dollars and balances remain unknown.
6. **Claude:** only its separate future check can establish a candidate mechanism.
   This OpenAI design supplies no Claude credential or route qualification.

S2–S5 own software evidence for 1, 2, 4 and software aspects of 5. S6 needs
separate explicit account/model/usage authority for 3 and live route evidence.
C1 owns 6. Patrick's no-code instruction keeps all implementation unstarted.

## Alternatives and supersession

| Mechanism | Current disposition |
| --- | --- |
| Direct plan OAuth Responses transport | Authorized design revision; explicit `openai-plan` adapter proposed. Software and live evidence remain missing. |
| Codex app-server with a plan grant | Original S1 stopped at its single-inference gate. No new binary, duplex worker or relaxed request bound is proposed. Preserve its report and receipts. |
| Shared native login/status with stripped API variable | Remains unqualified for explicit funding; inherited legacy use is not a guarantee. |
| Copied native OAuth cache or pasted tokens | Rejected; approved app-owned consent and Keychain profiles remain required. |
| One authentication mechanism for OpenAI and Claude | Rejected. Share the funding/admission contract; keep mechanisms, credentials and qualification separate. |
| Automatic API fallback or changing models after refusal | Rejected. New funding/configuration needs deliberate acceptance and applicable authority. |

## Evidence boundary

This revision read source and official documentation and changed Markdown only.
It did not run a provider worker, native login/status/account command, OAuth flow,
Keychain operation or inference request. No API credit was needed or spent.
It does not rerun or supersede the original S1 receipts. Passing document checks
does not qualify the direct route, a platform, an account or model quality.
