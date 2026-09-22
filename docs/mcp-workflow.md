# Local MCP retrieval profile

Harness's base install pins MCP Python SDK **2.2.0** (an extra before 0.4.0). The qualified stdio
profiles are **2025-11-25** and **2026-07-28**. The base install carries the review, test and acceptance journeys since 0.4.0.
The separately installed attune-ai SDK pin is unaffected. Install in a separate
environment; `requirements-workflow.lock` and `requirements-mcp.lock` record the
tested dependency closure.

Use an accepted [review request](review-workflow.md). Select a participant whose
grants contain only `retrieve` and/or enabled contributed retrieval tools, with
a positive `max_tool_calls`. Verification grants are unsupported on this profile.

```sh
attune-harness mcp-serve --request request.json --config participants.json --participant alpha --session-dir new-mcp-session
attune-harness mcp-inspect new-mcp-session
```

The first command is launched by an MCP client and reserves stdout for protocol
messages; errors go to stderr. Each launch requires a new session directory.
The client chooses a qualified protocol profile using its normal SDK interface.
The installed reference journey runs these commands verbatim against generated,
accepted inputs:

```sh
python3 scripts/check_mcp_installed.py --python .venv-mcp2-probe/bin/python --legacy-python .venv-mcp-check/bin/python --report docs/receipts/mcp-installed.json
```

Tools appear as `harness.retrieve` or `harness.evidence.search`. Arguments are
exactly `query` (nonempty, at most 4,096 UTF-8 bytes) and `k` (integer 1–20).
Paths and grants come from the accepted review inputs. Each successful result
contains matching text JSON and structured content, source/corpus hashes, and
the contributed artifact identity where applicable. `no_results` is a valid
retrieval outcome. Errors use MCP `isError` and contain no success payload.

Discovery lists startup grants; call-time checks reject disabled, removed or
changed artifacts, changed input/corpus snapshots, extra path arguments, and
exhausted budgets. Dispatched failures consume budget; pre-dispatch rejections
do not. There is no cross-session budget or automatic restart promise. Listing
and activation are declarations, not evidence that a later call will succeed.

The local launcher chooses the participant identity. `clientInfo`, names and
hashes do not authenticate a remote principal. This adapter configures no HTTP,
OAuth, native host registration, model calls or telemetry exporter.

One session holds an exclusive POSIX writer lease. Dispatch is saved before
retrieval; results settle before a started worker yields to cancellation. A
client timeout can suppress its response while the completed receipt remains.
Cancellation does not undo a started read. Input sizes are bounded; filesystem
I/O itself has no hard deadline. A persistence failure stops later dispatch.

Inspection never executes work. A saved running or interrupted session reports
`unresolved` (exit 2); a normally closed session reports `completed` (exit 0).
This status describes session lifecycle, not verified review prose. There is no
MCP session resume or automatic retry after an uncertain dispatch. The broader
review recovery commands operate on their own review records.
