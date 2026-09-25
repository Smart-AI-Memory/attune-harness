---
name: cross-review
description: Obtain an independent review of a bounded change using configured host participants.
---

Read repository review rules and the exact diff. Confirm scope, evidence and
what has not been verified. Use a different model or the human reviewer required
by those rules; never describe self-review as independent review.

Where the host provides configured subagents, dispatch a read-only review of an
immutable snapshot with a narrow brief: break the changed boundary, reproduce
findings, report severity and file/line evidence, then a held list. Do not give
the reviewer edit, merge, publication or spending authority. If no authorized
independent participant is available, report that limitation and request one;
do not silently call a paid API or substitute another provider.

For a repository already configured for Harness review, inspect `attune-harness
review --help` and use its accepted request and participant registry. Keep its
scope, provider and budget requirements. The CLI does not confer permission to
spend. Report partial/refused runs honestly. Reproduce findings before fixing,
run affected tests, and retain the reviewer's verdict with the exact reviewed
revision. No Attune AI roundtable imports, ledger or promotion commands are used.
