---
name: attune-release-check
description: Review release readiness against the repository runbook without publishing.
---

Read the target repository's rules, release runbook and current Git state.
Check the intended version, changelog, artifact build, relevant/full tests,
installed-package behavior, required CI jobs and independent review evidence.
Read actual CI results for platforms unavailable locally. Verify the exact SHA
and distinguish source tests from installed-wheel and live-host evidence.

Report ready or blocked with concrete supporting results and any unverified
requirements. Preserve existing receipts. Do not publish, merge, tag, dispatch
workflows, delete artifacts or change repository settings as part of this check.
The user can separately authorize a concrete release after reviewing the result.
