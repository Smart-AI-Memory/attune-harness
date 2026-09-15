# Native CLI boundary increment

Status: disposable implementation, authorized continuation. Scope is explicit
Claude/Codex CLI translation and local process lifecycle; no workflow migration.

Cases: success envelope with independent acceptance; wrong answer; zero exit with
error result; missing executable; incompatible CLI; malformed/truncated/duplicate
JSON; missing terminal event or identity; timeout; cancellation before launch and
during execution; cancellation after completion; stdout/stderr limit; repeated
dispatch; process cleanup. Failed native runs never become verified output.

Evidence before code: local `codex --version` reports 0.153.4 and `claude --version`
reports 2.1.266. Help is retained in receipts/. Both expose structured output;
Codex emits JSONL events, Claude JSON has structured_output. Official headless
documentation was read. A disposable Python process emitted partial output then
slept; timeout/kill retained `partial\n` with exit -9. Partial output cannot prove
completion. No authenticated model calls ran during these probes.

Design: a POSIX subprocess runner uses argument lists and temporary files for
input/output, polls for a deadline/cancel request/output limit and kills its
process group on interruption. The limit is checked while running and after exit;
it bounds retained parsing input, not instantaneous disk writes between polls.
NativeExchange translates exactly one request, retaining raw stdout/stderr and
runtime identity separately. Claude requires successful result metadata plus the
structured text field. Codex requires thread identity, turn start/completion and
a final structured agent message. The trusted translator computes correlation;
the model does not certify identity. Native failures preserve diagnostics and
unknown-effect semantics. Core run/JsonParticipant remain unchanged.

Default commands preserve host permission policies, use ephemeral sessions, and
request no tools for the arithmetic fixture. CLI sandbox/permission settings do
not establish isolation from all host configuration. Live tests must declare the
actual environment. Production tool access and interactive approval are later
qualification work. Authentication remains owned by installed CLIs; no credential
reading, copying or workaround is part of the implementation.

Rejected alternative: use exit status or the last printable line as completion;
both admit truncated/error runs. Rejected alternative: add mandatory provider
SDKs; CLI translation can test the boundary without expanding core dependencies.

Done when real local subprocess fault tests, both deterministic native-format
translations and isolated installed-wheel checks pass. Live provider receipts
are a separate evidence obligation, and will not be fabricated if unavailable.

Sources: [Claude headless](https://code.claude.com/docs/en/headless),
[Claude structured output](https://code.claude.com/docs/en/agent-sdk/structured-outputs),
[Codex noninteractive](https://developers.openai.com/codex/noninteractive/).

## Live diagnostic correction — 2026-09-14

Before this edit, the approved Claude probe returned exit 1 with a structured
`is_error: true` result of `Credit balance is too low`; stderr contained an
auth-source/connector warning. The adapter summary reported only stderr, hiding
the actionable cause. Preserve the provider error from a valid Claude result
in the failure summary alongside stderr. Cases: valid structured error retained,
malformed/non-error stdout ignored, original raw receipt unchanged. Rejected
alternative: print all stdout in every exception; that mixes ordinary output
with errors. Verify against the saved response and deterministic tests; no
additional provider call is needed.
