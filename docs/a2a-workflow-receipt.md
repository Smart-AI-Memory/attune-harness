# A2A local interoperability and final protocol receipt

2026-09-14. Bounded Phase 4 MCP/A2A increment complete; full Phase 4 remains open.
[Design before implementation](design-a2a-increment.md), [runnable workflow](a2a-workflow.md),
[combined machine-readable summary](receipts/protocols-summary.json).

- **427 tests passed**, 1,666/1,763 statements covered (**94.50%**). This includes
  38 new A2A cases. [Full suite](receipts/protocols-suite.txt),
  [coverage](receipts/protocols-coverage.json), [A2A cases](receipts/a2a-suite-increment.txt).
  Server subprocess execution is not included in the coverage denominator's hits.
- **110 installed cases passed**: 90 feature/review/recovery/extension regression
  cases, ten MCP CLI/cross-version cases and ten A2A journeys. The independent
  MCP client also exercises two complete protocol profiles. The summary lists
  each retained result file; [A2A wire and peer state](receipts/a2a-installed.json)
  and [MCP wire data](receipts/mcp-installed.json) retain actual requests/results.
- **2/2 new tests on existing MCP CLI branches fail with their guards removed**
  in disposable source copies. A2A and MCP module tests accompany new modules
  and are outside that mutation denominator. [Mutation receipt](receipts/mcp-mutations.json).
- **Zero provider calls**. Public SDK dependency downloads occurred in isolated
  environments; no account credentials, native host configuration, sibling
  checkout, remote repository or published package was changed.

The installed A2A consumer used a core-only environment with no attune-ai, provider,
MCP or Attune feature packages. A separate stdlib HTTP process, importing no
Harness code, computes an arithmetic result and maintains server-generated task
and context identity. The original core independently verifies the artifact:
an intentionally wrong answer is rejected even when the peer reports completed.

Pinned agent-card identity, selected version/interface, local operation grants
and HTTP 401/403 refusals have checks. This is local identity correlation and
access-error handling, not production authentication. Malformed/oversized/
truncated JSON, duplicates, nonfinite numbers, wrong RPC/task/request identity,
unknown states, redirects and unsupported artifacts cannot produce completion.
No artifact URL is fetched.

The peer demonstrably creates one task before losing its submission response;
Harness saves uncertainty and never resubmits. After an acknowledged task's poll
disconnect, explicit GetTask retrieves the completed artifact with one total
submission. Cancellation, acknowledgement loss during cancellation, refresh and
the completion race retain truthful peer state. A lost cancellation response
does not permit another CancelTask. Dispatched operations and results use the
existing POSIX lease/atomic persistence; a write failure stops further dispatch.
Inspection makes no calls and does not rewrite records.

## Packaged artifact

Wheel: `dist/attune_harness-0.1.0.dev0-py3-none-any.whl`  
SHA-256: `c07d974a0eb4da5d9a90111d9148654a3967e251367bf6ac072dc7703799b27c`

Built twice with Python 3.10.11, build 1.5.0, local setuptools/wheel and
`SOURCE_DATE_EPOCH=1789344000`; both wheel bytes match. Installed with
`pip --no-index --no-deps --force-reinstall` into eight local environments:
core, verify, rag, all-feature, review, workflow, MCP 2.2.0 and the explicit
Attune bridge. All installed checks run outside the source tree with `-I`.
[Artifact and lock hashes](receipts/protocols-artifacts.json),
[47 matched dependency pins](receipts/protocols-dependencies.json).
`pip check` reports no broken requirements in the isolated MCP environment.

Harness's optional MCP extra pins **2.2.0**. Qualified stdio profiles:
**2025-11-25** and **2026-07-28**, including a 1.29.1 legacy SDK client against
the new server. [MCP receipt](mcp-workflow-receipt.md). The v1 server/source/lock
baseline remains retained. The base environment still has attune-ai 16.4.0 and
MCP 1.29.1. The explicit [BasePlugin bridge regression](receipts/protocols-attune-bridge.json)
also passed real retrieval and disabled-call refusal on the final wheel.

Reproduction (from this checkout):

```sh
.venv-mcp2-probe/bin/python -m pytest -q --cov=attune_harness --cov-report=json:docs/receipts/protocols-coverage.json --cov-report=term
.venv-mcp2-probe/bin/python scripts/check_mcp_mutations.py
python3 scripts/check_mcp_installed.py --python .venv-mcp2-probe/bin/python --legacy-python .venv-mcp-check/bin/python --report docs/receipts/mcp-installed.json
python3 scripts/check_a2a_installed.py --python .venv-core-check/bin/python --report docs/receipts/a2a-installed.json
```

The A2A/full-suite runs require permission to bind local loopback sockets. The
default sandbox refused the initial scratch bind; automatic escalation review
approved the local-only probe and tests. No test was skipped to get the result.

## Remaining acceptance work

This qualifies macOS/Python 3.10.11, local POSIX storage, MCP stdio and the bounded
A2A 1.0 JSONRPC profile. A2A review-roster integration, process-restart resumption,
remote TLS/authentication, tenant/streaming/push support, general artifacts and
hard aggregate transport deadlines remain unsupported. Model usability/quality,
Windows and cross-machine behavior have no new qualification from these fixtures.

Phase 4 still needs the E2 declaration-versus-evidence comparison and broader host
and authenticated integration receipts. Earlier live-model/E1 obligations remain
open. Phases 5 (collaboration value) and 6 (pilot/migration) have not been completed.
No different-model review ran in this increment; none is implied by the tests.
