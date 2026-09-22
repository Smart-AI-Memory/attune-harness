# Disposable Luna stage-contract experiment

Date: 2026-09-16. Status: bounded research, not production implementation.
Patrick selected Luna first, agreed to investigate its Voyage/inspection behavior,
and said to continue researching. This increment compares response contracts
using synthetic memory cases; it does not restart the stopped Voyage campaign.

## Question and existing evidence

Does enforcing the actual stage object improve usable responses over enforcing
only a text envelope? Saved-reply analysis found 10/10 Luna envelopes valid but
only 5/6 inspection payloads with the required actions shape. The same host
warnings accompanied shape-valid and invalid replies. See
[the analysis](../../docs/research/luna-voyage-follow-up-2026-09-16.md).

## Cases and comparison

Four fresh operational cases cover: requesting an unread correction, handling
unavailable evidence, preserving an exception while updating a preference, and
distinguishing a tentative suggestion from an accepted decision. Inspection
returns read actions over explicitly supplied source IDs; answer stages return
a proposed memory disposition, text and supporting source IDs. No action is
executed and no personal memory is changed.

Each case runs once with a text-envelope schema and once with its actual stage
schema: eight native calls maximum, serial, alternating which condition goes
first. The logical task, evidence, expected meaning, model, reasoning setting
and host settings stay fixed within each pair. Only the enforced schema and
the necessary decoding differ. This compares complete response contracts,
including removal of JSON-within-a-string escaping; it cannot isolate native
schema enforcement as the sole cause. Both prompts describe the same logical response
and how to wrap it when the response schema requires a text field.

Use `gpt-5.6-luna`, high effort, through the existing Codex ChatGPT login.
This consumes subscription quota, not a newly authorized direct API budget.
There are no Voyage or Anthropic requests: supplied evidence is synthetic.
Record all calls, failures, warnings, usage and complete-process durations;
eight calls is an operational comparison across four cases, not a statistical
quality qualification. No numerical improvement target or production promotion
is inferred from such a small sample.

## Checks, controls and disposition

Before native dispatch, exercise saved premature prose, valid read actions,
missing evidence, unknown sources, empty actions despite needed evidence,
extra fields, duplicate keys, conflicting messages and valid-shaped wrong
decisions. Shape validation and case-specific meaning checks are separate.
Use the recorded source failure as a regression case, never a fresh scored case.

Freeze schema, cases, runner and protocol hashes before dispatch. Each attempt
is recorded before starting; refuse a second run in the same receipt directory.
Use a fresh temporary work directory containing only schema/instructions and
the prompt on stdin, read-only sandbox, no native tools or provider fallback.
Use the existing experimental disabled-feature profile unchanged between arms;
record its warnings and stop on unexpected tool events, missing usage, ambiguous
responses, provider/transport failure or timeout. A well-formed completed turn
that fails its stage contract is a scored failure, not a retry trigger.
Per-call timeout is 180 seconds; a timeout does not prove zero provider usage.
The native adapter's configured restrictions and observed events are recorded;
this experiment does not establish universal host tool isolation.
Only the three observed warning prefixes are accepted as diagnostic error items;
unknown native error items stop the experiment even if an answer follows.
The eight-call bound counts runner dispatches, not internal HTTP requests made
by the native CLI, which this experiment cannot independently count.

Native output shape, correct task disposition and evidence fidelity are separate
results. The lead reviews all generated memory prose against the frozen rubric;
this is unblinded, source-grounded assistant grading, not independent human grading.
Runtime totals include client startup and are not first-token measurements.

Rejected: silently repairing prose into actions; counting valid empty actions
as successful inspection; adding corrective model calls only to one arm;
changing host settings and schema simultaneously; using these synthetic cases
to claim a Voyage retrieval gain or autonomous memory-management readiness.
