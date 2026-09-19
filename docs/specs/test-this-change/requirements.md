# Test this change

Approved implementation boundary: Patrick's 2026-09-17 instruction to execute
the four-item first slice in the testing case study. Existing approvals stand;
no release, plugin activation, paid campaign or generation/repair is implied.

Outcome: a person or agent can capture a Git working-tree change, inspect the
chosen tests, execute them and inspect/resume a durable result through Harness.
Existing test, audit, generation and repair features remain available.

Requirements:

- Bind repository root, HEAD, explicit relative change scope, source/test/config
  content, selection rationale and interpreter identity before execution.
- Discover associations by module imports and matching test names; describe
  uncertainty. Automatic selection conservatively uses the named tests directory
  when hints cannot prove a complete narrower set. Explicit test targets are
  supported and disclose broader checks excluded by that choice.
- Preserve unrelated dirty work. Execute an exact disposable copy of captured
  regular files, with explicit cwd/interpreter/timeout/output bound. Tests are
  trusted project code, not sandboxed against arbitrary external effects.
- Record actual pytest collection and execution counts independently of exit
  status. Collection-only and all-skipped runs must not become passed execution.
- Persist bounded complete stdout/stderr artifacts and their digests. Output-limit
  failures explicitly report incomplete evidence, never a passing result.
- Results distinguish passed within scope, failed, no tests, interrupted and
  blocked environment/evidence. Status displays freshness and missing checks.
- Reuse the existing task store, writer lease and recovery cursor. Completed
  operations are not repeated. Unknown dispatched effects are not blindly retried.
- Render with the existing forms grammar and durable Markdown. Recommend only a
  relevant next action; no automatic changes to assertions, source or test files.

First qualified profile: local POSIX Git repository, regular files, Python/pytest.
Repository copying omits Git metadata, ignored files and environment directories;
tests needing those inputs must disclose that gap or fail visibly. The interpreter
environment remains explicit; this is not a hermetic dependency environment.

Done when behavioral tests cover normal/failing/empty/collection-only/all-skipped
execution, import/collection errors, indirect consumers, duplicate basenames,
configuration changes, dirty-file preservation, stale evidence, large output,
interruption, persistence failure and completed/uncertain resume; a real Spec
repair runs through the new CLI; installed outside-tree execution and existing
task/process compatibility checks pass. Independent review and protection-removal
checks support the final receipt.
