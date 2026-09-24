---
name: spec
description: Guide a spec through Harness intake, review, receipt-backed execution and resume.
---

Use the user's project, outcome, acceptance criteria and authorized scope. Read its
rules before acting. Use Harness alone; do not import or install Attune AI.

1. Inspect `attune-harness spec intake --project <root>` to derive the intake.
   Ask only for material missing answers. For command-line intake composition,
   pass an answers JSON object on stdin to `spec intake --project <root> --compose`.
2. Open `command_workspace_open` with `adapter_id: spec`, and `intake` containing
   `route: new`, outcome, done_when, area and slug. Resume is refused by this candidate until verified lifecycle gates (M3) land. Show the returned widget if the host can
   render it; otherwise show its Markdown. Never claim a widget was visible
   without observing it. The same action contract applies to either surface.
3. Collect the user's actual choice through `command_workspace_collect_action`.
   Preserve the title, view, workspace_id, revision, action_nonce, contract_hash
   and confirmation returned by the UI. A host without interactive controls may
   build the response from a clearly stated user choice and the exact displayed
   binding. Never infer approval from silence or fabricate a response.
4. On authorized creation, write the scoped spec/plan artifacts. Publish
   `artifacts_created` using actual project-relative paths and parsed task IDs.
   Use the adapter's returned result to determine the next operation.
5. Lifecycle gates are not shipped by this candidate. When the adapter requests
   `spec.lifecycle_gate`, STOP and report that M3 is required. Do not invent PASS
   receipts, bypass the boundary, call the removed Attune AI command, or claim
   approval/execution is complete. Resume is subject to the same boundary.
6. Inspect existing plans with `spec present tasks|task|progress --plan <path>`;
   task view also takes `--task <id>`. A completed Harness testing task with an exact persisted Spec acceptance can be
   rendered with `spec present result --plan <path> --task <id> --test-run <dir>`.
   That verifies the current test receipt and does not perform a model review.

Workspace state is process-local. Restarting the server invalidates old action
bindings; reopen from a saved plan and show the new decision. Use fresh evidence
and the user's original authorization, not retained UI nonces.
