# Approved live probes — 2026-09-14

Patrick explicitly approved one Claude and one Codex arithmetic probe using the
existing sign-ins. Invocations were sequential, with no harness retry or fallback.
Ran the installed wheel from outside the source tree via `.venv-probes/bin/python
-I examples/native_probe.py`, using absolute paths in the actual commands. Each
native invocation had a 60-second deadline and an isolated temporary working
directory. The CLIs retained their existing host configuration and auth selection.

Input wheel SHA256:
`d25c714d6c5bee57e14b5ce42bf04b30f5688ce4c18d72ccfca63b4638fd49ab`.

| Provider | Outcome | Retained evidence |
|---|---|---|
| Claude Code 2.1.266 | Exit 1; native structured result reports `is_error: true`, HTTP 400, `Credit balance is too low`. Zero input/output tokens, zero reported cost. No model output qualified. | [Raw Claude receipt](receipts/claude-364ec5d6-9baf-405a-9203-095640291933.json) |
| Codex CLI 0.153.4 | Exit 0; ordered thread/turn events, final `{"text":"4"}`, completed turn, independent exact arithmetic check accepted. | [Raw Codex receipt](receipts/codex-a31ae0cf-10c9-4c33-b28a-243035d4f377.json) |

Claude's stderr says an API key or another auth source takes precedence over the
claude.ai login. The exact account was not inspected. No auth source was changed,
no credential was read/copied and no credit purchase was made. Patrick indicated
he can add funds; completion of the top-up and a Claude retry remain pending.

Codex reported session `01a09f32-8ad1-75f0-8769-8ae1239c9cc0`; its JSONL did not
report a model ID or dollar cost. Usage: 25,555 input tokens, 15 output tokens,
zero cached input tokens. Host skills/configuration were loaded: the stream
contains a shortened-skill-description warning, and stderr includes existing
MCP startup/auth and local state warnings. No tool invocation appears in the
retained event stream. The result qualifies this arithmetic/structured-output
path, not a minimal-context runtime, clean host integration, feature access,
provider cancellation, recovery or model identity.

## Diagnostic fix discovered by the Claude probe

The original raw receipt is preserved. Its aggregate error string included only
stderr's connector warning, hiding the actionable structured credit error in
stdout. The native adapter now includes a valid Claude structured error's result
in the failure summary. Malformed or non-error stdout is not promoted to a cause.

- Suite: **129 passed, 99.43% statement coverage** using the documented Python
  3.10.11 pytest/coverage command.
- Mutation in a disposable source copy: **2/5 new tests fail** with structured-cause
  preservation removed; three negative controls pass. [Output](receipts/diagnostic-mutation.txt).
- Rebuilt and reinstalled wheel without dependencies. Replayed both saved native
  process outputs through the installed adapter using an injected runner:
  Claude remains failed with its credit error visible; Codex remains verified.
  Replay made no native runtime or provider calls.
- Updated wheel SHA256:
  `644d945aa3ad8771c9bd59ba1e26dfda3fb51cde6b11540da3ccbb72c819a102`.

The two live calls establish evidence for the earlier wheel. The diagnostic
change is covered by deterministic tests and installed-wheel replay only; it was
not used to obtain another live receipt. No different-model review ran.
