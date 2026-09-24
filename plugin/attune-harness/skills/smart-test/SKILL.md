---
name: smart-test
description: Identify meaningful test gaps and retain Harness test evidence for an authorized change.
---

Read the changed behavior and existing tests before proposing more tests.
Choose checks that could fail for a realistic regression; avoid mirroring the
implementation or padding coverage with mock-only assertions. Write tests only
inside the authorized scope and run the relevant suite.

Use `attune-harness test --help` to prepare the captured-change testing task.
Follow its preview and acceptance contract before executing its declared checks.
Retain the resulting task directory and report passed, failed, no-tests or blocked
as recorded. Do not translate a test pass into model quality or platform evidence.

This skill uses host coding tools and Harness's deterministic test workflow.
It does not provide Attune AI's audit/generation MCP tools or automatic paid test
generation. If those are required, report the missing capability rather than
calling unavailable tools or widening provider access.
