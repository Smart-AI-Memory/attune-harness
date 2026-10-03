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

For shared Harness source review, inspect `attune-harness source-review --help`.
Use `source-review prepare --project ROOT --path FILE --config CONFIG --run-dir
RUN` to freeze explicitly selected files with the named author and different
reviewer model. Inspect the returned contract, scope and call budget, then use
`source-review run RUN --accept DIGEST --allow-external --allow-native` only with
the user's provider/upload/spend authority. Command participants need external
authority but no native flag. `source-review status RUN` is read-only. A pause
resumes with the same run and contract; uncertain dispatch never retries.
`source-review abandon RUN --checkpoint DIGEST` stops continuation and preserves
unknown effects. Never edit a record to get past refusal.

Both Claude Code and Codex use this same CLI and configuration. Preserve requested
and runtime-reported identities separately; absent actual-model metadata stays
unknown. `review` remains documentary evidence review. Reproduce findings before
fixing, run affected tests and retain the exact frozen scope and verdict. CLI
acceptance is host-owned and does not grant merge or publication authority.
