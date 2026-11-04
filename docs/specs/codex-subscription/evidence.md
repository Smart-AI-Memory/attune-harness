# Evidence and unresolved assumptions

**Status: S1 completed with a stop-gate result. Runtime support remains
unqualified; the separate Claude check is unstarted.** Reviewed November 3, 2026.

See [S1 qualification](s1-qualification.md) for the installed binary/source/schema
pins, four successful model-free commands, retained initial failed witness,
source comparison and the execution-bound decision before S2. The planning
observations below remain distinct from that later evidence.

## Repository baseline

Read against `03e29647a02073089fb33ea8df45b75be65383ba`, after the API-first
funding implementation. Existing claims below describe that source; proposed
contracts are in the [README](README.md).

| Observed source | Consequence for this spec |
| --- | --- |
| [Strict funding validation and refusal](../../../src/attune_harness/participant_funding.py#L16-L72) supports only existing adapter/policy fields; native explicit policies refuse | Add a new adapter/policy explicitly. Neither `profile_id` nor the proposed commands work today. |
| [Model normalization](../../../src/attune_harness/participant_funding.py#L75-L87) and [consultation validation](../../../src/attune_harness/consultation.py#L36-L87) | Extend adapter mapping and normalized OpenAI identity without weakening reviewer independence. |
| [One-use claim](../../../src/attune_harness/participant_funding.py#L153-L174) and [real-owner admission](../../../src/attune_harness/participant_funding.py#L254-L307) | Reuse owner/request/persistence discipline; a saved receipt is not dispatch authority. |
| [Consultation batch admission](../../../src/attune_harness/consultation.py#L435-L481) precedes sibling model calls | Preserve all-member admission and prevent partial mixed-funding inference on a refused member. |
| [Registry schema](../../../src/attune_harness/review_contract.py#L54-L124) and [shared exchange](../../../src/attune_harness/review_participants.py#L169-L255) distinguish planning/build/evidence roles | Integrate the transport without skipping host tool validation or treating native tool access as equivalent. |
| [One-shot process supervisor](../../../src/attune_harness/process.py#L60-L93) | Duplex app-server RPC needs a separate bounded supervisor; the current API is not already suitable. |
| [Existing native exchange](../../../src/attune_harness/native.py#L158-L287) | Keep inherited native behavior and native explicit refusal separate from the new qualified path. |

## Official documentation consulted

These are dated documentation observations, not receipts from the installed
runtime or a live account. Recheck them in S1; preview details and provider
conditions can change. The requirements derived from them are design choices
until implementation proves them.

| Primary source | Relevant observation and limitation |
| --- | --- |
| [OpenAI local/open-source token sharing](https://developers.openai.com/siwc/token-sharing-open-source) | Describes optional plan-authorized access for eligible local/open-source applications. Hosted/commercial use follows a different process. Eligibility is not universal. |
| [OpenAI app-server integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) | Describes a custom Responses provider using an app-supplied plan access token, HTTP/SSE and app-owned refresh. A model catalog is not an entitlement check. This supports investigating a distinct adapter. |
| [OpenAI sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) | Describes public-client PKCE, issued registration, identity validation and returned scope checks. Identity alone does not grant plan use. |
| [OpenAI profiles and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions) | Describes separate registrations, atomic rotating refresh and explicit revocation. Profile handling is meaningful new scope, not an environment-variable toggle. |
| [OpenAI preview limits](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) | Requires the supported streaming/storage profile and excludes some Responses fields, including `max_output_tokens`. The direct API request contract cannot simply be reused. |
| [Codex app-server protocol](https://learn.chatgpt.com/docs/app-server) | Describes bidirectional stdio RPC, generated schemas and configuration/requirements inspection. It does not prove the exact installed version disables all autonomous model/tool behavior. |
| [Claude authentication](https://code.claude.com/docs/en/authentication) | Documents precedence among several credential/provider sources. Removing one environment variable cannot establish invocation funding. |
| [Claude legal and compliance](https://code.claude.com/docs/en/legal-and-compliance) | Defines conditions for unmodified Claude Code and user-owned authentication. C1 must establish applicability without collecting or intermediating subscription credentials. |

## Assumptions that must be resolved before support

1. **Runtime feasibility:** a pinned Codex implementation can enforce task-free
   startup, the fixed plan provider, effective configuration inspection and the
   restricted one-turn profile. No version is qualified by this planning pass.
2. **Bounded inference:** the profile can disable native tools, subagents,
   automatic compaction/follow-ups and retries that would create hidden model
   requests. A timeout alone does not establish this.
3. **Account and model eligibility:** the user's actual returned plan grant and
   selected model are usable for the intended workflow. Neither login metadata
   nor a bundled model catalog proves this or native CLI quota equivalence.
4. **Credential lifecycle:** the proposed OAuth library and Keychain integration
   can satisfy identity binding, atomic refresh, concurrency and revocation. No
   plaintext fallback or native auth-cache reuse is accepted as a substitute.
5. **Usage reporting:** a qualified completed turn exposes enough reliable usage
   to normalize counts. Missing values stay unknown; no dollar/balance claim
   depends on the answer.
6. **Claude:** no current strict subscription selector has been established by
   this pass. C1's separate verdict may remain negative or unknown.

The first two are S1 stop gates. The third needs later explicitly authorized
account/live evidence. S2–S5 verify the fourth and software aspects of the fifth.
C1 owns the sixth. Failure does not authorize silent fallback or broader scope.

## Alternatives considered

| Alternative | Decision in this draft |
| --- | --- |
| Native **`codex`** login/status plus stripping an API environment variable | Rejected as the funding guarantee: shared config, helpers and status/dispatch gaps remain. Preserve it only as legacy unverified behavior. |
| Copy native OAuth cache/token into a private child | Rejected: unsupported credential custody and identity/refresh coupling. Use explicit official app consent instead. |
| Call SIWC Responses directly, bypassing Codex | Not selected: would add another direct client and change the requested Codex integration. Reconsider only through a concrete scope decision if app-server restrictions fail S1. |
| Enable native Codex tools immediately | Deferred: expands filesystem, tool, model-attempt and recovery authority. Host-owned Harness proposals provide the first bounded workflow. |
| Solve Claude and Codex authentication as one abstraction now | Rejected: provider conditions and invocation evidence differ. Share the funding contract, keep mechanisms and qualification separate. |

## Evidence boundary

This spec was checked against source and current official documentation. No
native login/status/account/model request, OAuth connection, Keychain mutation,
new runtime implementation or live quota/billing observation occurred. Existing
API receipts do not qualify this subscription route. Passing document checks or
future software checks cannot replace the missing live route evidence.
