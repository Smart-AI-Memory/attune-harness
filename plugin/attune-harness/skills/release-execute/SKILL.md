---
name: release-execute
description: Execute a repository release runbook with concrete evidence and explicit publication authority.
---

Read the repository rules and release runbook. Establish the exact repository,
version, source commit and authorized destinations. Prepare release metadata,
tests, packages and a reviewable PR using the repository's required checks.
Record failures, skipped checks and independent review requirements.

Use normal protected PR integration. Never bypass checks or use an admin merge.
Before each merge, tag, release, workflow dispatch or package publication, apply
the user's existing authorization and the repository's approval rules. If new
authorization is needed, present the concrete artifacts, target SHA and result
of required checks before asking. Never infer permission from this skill.

Verify publication against the actual publishing run's artifact hashes and a
fresh isolated install. Preserve retained evidence and report incomplete work.
Do not invoke paid documentation/model workflows, delete remote resources or
alter repository protection as incidental release steps.
