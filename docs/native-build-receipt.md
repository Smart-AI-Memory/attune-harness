# Native adapter implementation receipt — 2026-09-14

Status: local implementation and deterministic boundary verification complete;
authenticated provider qualification pending. No different-model review ran.

## Implemented

- `native.NativeExchange`: single-use Claude/Codex CLI translators for the existing
  JsonParticipant. Requests carry the complete accepted assignment; correlation is
  computed by the translator. Native session IDs remain separate from task,
  attempt, role and caller-supplied participant identity.
- Claude: successful result metadata and structured_output required. Codex:
  ordered thread/turn events, completed turn and structured agent output required.
  Duplicate keys, malformed JSON, non-JSON constants, absent identity and partial
  results fail. Native metadata may contain extra fields; unknown Codex event
  types fail explicitly. No automatic fallback or harness retry occurs.
- `process.invoke`: POSIX process-group cleanup, explicit deadline and cancellation,
  bounded retained output, raw stdout/stderr diagnostics, invalid UTF-8 rejection.
  Failures after dispatch retain unknown-effect semantics. The byte limit is
  polled and cannot cap instantaneous temporary-file growth between polls.
- `examples/native_probe.py`: one arithmetic call to a selected provider; records
  CLI version, accepted attempt, result, reported identity and raw process output.

Design note preceded source edits: [design-native-increment.md](design-native-increment.md).
Observed local versions: Claude Code 2.1.266 and codex-cli 0.153.4; help retained in
[receipts/claude-help.txt](receipts/claude-help.txt) and
[receipts/codex-exec-help.txt](receipts/codex-exec-help.txt). Version/help commands
are not provider qualification.

## Verification

```sh
/Users/patrickroebuck/.pyenv/versions/3.10.11/bin/python3 -m pytest tests -q --cov=attune_harness --cov-report=term-missing --cov-fail-under=85
python3 -m build --wheel --no-isolation
```

**124 passed; 99.42% statement coverage.** New native module: 100%; process module:
98.53%. The uncovered process line rejects non-POSIX hosts. Tests for these new
modules accompany new code; the existing-code mutation receipt is not applicable.

Actual subprocess probes cover successful and nonzero exits, missing/non-executable
programs, deadline, cancellation before and during launch, cancellation after
completion, output limits on both streams, invalid UTF-8, and a descendant that
must not write its delayed-effect marker after process-group termination.

Both native-format fixture executables run through the complete
NativeExchange → JsonParticipant → independent verifier path. Wrong answers,
zero-exit provider errors, truncated turns, malformed data and process failures
cannot produce verified results. These executables are deterministic peers,
not Claude/Codex model runtimes.

Rebuilt wheel installed with `pip install --no-index --no-deps` in a fresh temporary
venv. From outside the source tree, using `python -I`, ran the existing JSON
consumer and the actual native_probe.py twice with deterministic executables.
Both generated verified receipts containing native fixture identity and raw
stdout. Confirmed attune, anthropic, claude_agent_sdk and openai were not installed.
The temporary install and its fixture receipts were removed after assertions.

Wheel: `dist/attune_harness-0.1.0.dev0-py3-none-any.whl`.
SHA256: `d25c714d6c5bee57e14b5ce42bf04b30f5688ce4c18d72ccfca63b4638fd49ab`.

## Pending live receipt

After installing this wheel, each command performs exactly one harness invocation
with a 60-second deadline. Native runtimes may have their own internal retries.
The probe uses a temporary working directory and the CLI's normal authentication.
It does not select a fallback model or alter credentials. An omitted model means
native default selection; reported model metadata may be absent, especially for
Codex JSONL. Such absence must remain explicit.

```sh
python -I /Users/patrickroebuck/attune-harness/examples/native_probe.py --provider claude --receipt-dir /Users/patrickroebuck/attune-harness/docs/receipts
python -I /Users/patrickroebuck/attune-harness/examples/native_probe.py --provider codex --receipt-dir /Users/patrickroebuck/attune-harness/docs/receipts
```

These authenticated commands have not run. Patrick's saved credential rule
requires explicit approval before using existing sign-ins for the new probe.
No credentials were read, copied, changed or worked around. No model usage or
provider spend was incurred by this implementation turn.

No claim of full portable cancellation, external-effect reconciliation, tool
isolation, reconnect, Attune feature access, Windows support, ACP/MCP/A2A
interoperability or live model quality follows from these results. Host settings
and hooks may influence the native runtime despite its command-level tool policy.
Next evidence is one bounded arithmetic result per actual runtime, then the
remaining feature/lifecycle qualification matrix.

## Live continuation — 2026-09-14

Patrick approved the pending calls. Codex's arithmetic path passed; Claude returned
an insufficient-credit error from its selected auth source. See the
[live probe receipt](live-probe-receipt.md) for raw evidence, host limitations,
usage, and the diagnostic correction. The latest suite is 129 passing tests at
99.43% coverage. The latest wheel hash is recorded there. No further provider
calls followed the two approved invocations.
