# Separate Claude subscription feasibility check

**Status: Proposed check, not executed. No Claude support is qualified or
authorized by this document.** November 3, 2026.

## Question and baseline

Can an unmodified, user-authenticated Claude Code invocation enforce explicit
subscription funding, remain isolated from API credentials and shared state, and
fit Harness's existing admission/recovery contracts?

The existing [funding owner](../../../src/attune_harness/participant_funding.py#L39-L72)
refuses explicit Claude subscription funding. The prior
[T1 matrix](../participant-funding/t1-support-matrix.md) found that hiding one
environment key or observing cached login state was insufficient invocation
proof. Its versions and observations remain historical evidence.

Claude Code documents multiple credential sources and precedence rules, including
environment, settings and gateway sources. A headless invocation can choose a
different source from the expected stored login.
[Authentication reference](https://code.claude.com/docs/en/authentication)

Anthropic's conditions for running Claude Code in products require an unmodified
binary, preserve built-in authentication methods and require each end user to
authenticate and bear their own usage. Feasibility must account for those
conditions without claiming either blanket permission or a blanket prohibition
on native programmatic use.
[Legal and compliance reference](https://code.claude.com/docs/en/legal-and-compliance)

## Scope and method

C1 is a separate report, not an implementation task. First inspect current
official documentation, published source where available, versioned help/schema
and inert fake-process witnesses. Do not run real login, auth status, refresh,
account requests, **`claude -p`**, model calls or subscription trials during the
documentation/software portion. Model-free status commands can still invoke
credential helpers or refresh credentials and need their own authority.

| Area | Evidence required | Stop condition |
| --- | --- | --- |
| Provider-supported use | Cite current terms/docs for the proposed local unmodified invocation and user-owned sign-in | Unsupported use, credential intermediation, conflicting conditions or missing clarification |
| Credential precedence | Inventory API/bearer/OAuth variables, settings, helpers, keychain/profile behavior, gateways, managed policy and cloud providers for the exact version | Any unexcluded source can redirect the intended route, or excluding it would violate provider conditions |
| Subscription mechanism | Identify a supported invocation-scoped control and evidence that binds actual dispatch, rather than a cached account label | No enforceable selector/proof; `--bare` or another isolation mode also removes required subscription access |
| Shared-state isolation | Show that child environment/config and concurrency leave native login/settings unchanged | Requires logout/login switching, cache copying, shared config edits or exporting Claude OAuth tokens into Harness |
| Process and recovery | Show task-free preflight, bounded execution, output/identity validation, cancellation, descendant cleanup and honest uncertain-effect handling | Hidden model calls, unsafe retries, unbounded tool/effect paths or unverifiable dispatch |
| Eligibility | Identify plan, organization and headless-use conditions and what later account verification would require | Current account eligibility is unknown or organization policy forbids the intended route; no assumption from an old successful trial |

Do not reuse the Codex plan-profile implementation for Claude credentials. Do not
offer third-party Claude sign-in, collect/copy Claude tokens or alter the binary
to force a funding path. If clarification from Anthropic is needed, prepare the
question for Patrick; this task does not authorize contacting anyone.

## Required report

Record the exact version/platform, dated official sources, inspected mechanisms,
inert witness outcomes and remaining unknowns. Use one verdict:

- **Candidate mechanism established:** provider-supported route and invocation
  controls are evidenced; live account qualification and a separate implementation
  spec are still needed.
- **Native use possible; strict funding unenforced:** the binary can be invoked,
  but this check cannot establish the explicit subscription guarantee.
- **Unsupported or blocked:** name the concrete provider, configuration or
  organization restriction and the smallest decision that could change it.
- **Unknown:** name missing primary evidence without treating it as support.

A negative/unknown verdict completes C1 and leaves explicit Claude subscription
refused. It does not delay Codex tasks. If a viable mechanism exists, write a
separate implementation proposal before changing any Claude path. Any later
account/model test needs explicit scope and usage authority; no API fallback is
part of that test.
