# Harness host plugin candidate

Shared skills and MCP configuration for Claude Code and Codex. This is an
unpublished development candidate for M1/M2, not part of PyPI 0.6.0.

The MCP process launches `attune-harness mcp-serve --workspace` from the host
project working directory. Put the tested candidate environment's `bin` (or
Windows `Scripts`) on the launching host's PATH. A normal 0.6.0 executable lacks
`--workspace` and will refuse startup. Do not replace a retained evidence venv.
For hosts that do not launch in the project root, configure explicit `--project`
and a fresh `--state-dir` in their local server registration. State directories
are unique per process by default; inspect their `record.json` with
`attune-harness mcp-inspect <directory>`. No provider SDK/model is called.

Both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` point at the
shared skills. Load the local directory using the host's plugin installation
flow. No marketplace is published or user settings changed by these files.
Validate each host in a fresh session; static manifest checks are not a display
acceptance receipt. Confirm the three workspace tools, open Spec intake, observe
the widget or Markdown fallback, submit a bound action and verify a replay is
refused. Keep all cold/warm display trial results when measuring acceptance.

Lifecycle gates remain M3: the server refuses lifecycle events, resume and task execution publication. Spec can create and display drafts but cannot enter execution. Roundtable is M4. Memory saving,
opportunities automation and enhanced prompts are still separate follow-on
work. Cross-review and smart-test are adapted host workflows and do not claim
parity with legacy paid tools. Existing approvals remain required.

The actual Harness test-task receipt producer currently supports POSIX only.
Windows qualification exercises workspace discovery, draft publication, action
bindings and execution refusal, plus the producer's explicit unsupported result.
It does not qualify production of test receipts or accepted-result presentation
from a Windows testing run.

Result presentation requires both a persisted task-content binding and the exact
accepted test-run receipt. Rewriting an accepted task invalidates presentation;
old state without a content binding cannot be upgraded by saving it. An explicitly
authorized `clear_state` reset is required before redoing and reaccepting the task.
The binding detects edits after acceptance persistence; it does not establish
what ran before that save or supply the missing M3 execution authority.
