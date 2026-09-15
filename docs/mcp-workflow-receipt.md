# MCP implementation and SDK upgrade receipt

2026-09-14. Harness's optional adapter is pinned to **MCP Python SDK 2.2.0**.
The separate attune-ai environment remains on SDK 1.29.1. This is a bounded
Phase 4 result; broader phase acceptance remains open.

- Before A2A was added, **389 tests passed**, 1,467/1,546 statements covered (**94.89%**). Coverage does
  not count server subprocess execution. [Suite](receipts/mcp-suite.txt),
  [coverage](receipts/mcp-coverage.json).
- **2/2 new CLI tests fail with dispatch guards removed** in disposable copies.
  New MCP-module tests are outside that denominator. [Mutations](receipts/mcp-mutations.json).
- An installed-wheel, SDK-free stdlib client passes **two protocol profiles**:
  2025-11-25 and 2026-07-28. Ten CLI/cross-version checks support those journeys.
  A separate SDK 1.29.1 client also calls the 2.2.0 server successfully.
  [Raw requests/results](receipts/mcp-installed.json).
- Zero provider/model calls and credential changes. Public PyPI dependency
  downloads occurred in isolated environments. No release, remote write or host
  registration occurred.

Tests exercise real attune-rag retrieval, structured/text equivalence, schemas,
unknown methods/tools, extra path arguments, boolean rejection, missing SDK,
participant grants, finite budgets, changed sources and extension lifecycle.
Client cancellation during a started retrieval leaves its settled durable result.
Normal stdin closure exits successfully; interrupted or pending work remains
unresolved. Filesystem persistence failures stop subsequent writes and calls.

[Design note](design-mcp-increment.md) records the v1 baseline and the measured
v2 API migration. The [retained baseline](receipts/mcp-v1-baseline/suite.txt) has
387 passing tests before migration, plus its source and dependency lock. The v2
server explicitly validates schemas, wraps errors, uses public callback APIs and
disables optional telemetry middleware. Harness pins the SDK and dependency
closure in `requirements-mcp.lock`; core dependencies remain empty.

[Workflow and reproduction commands](mcp-workflow.md). Qualification is local
macOS/Python 3.10.11, stdio and POSIX leases. ClientInfo/card names are not remote
authentication. HTTP/OAuth, native-host integration, other protocol profiles,
MCP resumption, hard filesystem deadlines and model usability evaluations remain
unqualified. A2A and E2 are separate remaining Phase 4 work.

The subsequent [A2A/final protocol receipt](a2a-workflow-receipt.md) supersedes the
packaged test count: **427 tests and 110 installed cases pass**. Both MCP protocol
profiles and the legacy SDK client were rerun against the final wheel, whose hash
and byte-identical rebuild are recorded there. E2 and wider phase acceptance remain open.
