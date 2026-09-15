I’m Patrick Roebuck, founder and sole developer of Smart AI Memory. I want to
brainstorm the architecture of **Attune Harness** with you.

Project: `/Users/patrickroebuck/attune-harness`. This is a standalone project;
`attune-ai` is a separate integration/reference project.

Mode: architecture brainstorming and planning. Keep this session read-only;
implementation belongs to the original session. Help me examine the design,
challenge assumptions, and decide the next architectural direction. Do not
assume the latest implementation proposal is already the right answer.

Proposed outcome: a short architecture decision brief covering the system’s
purpose, major responsibilities and boundaries, the important tradeoffs,
unresolved decisions, and the next small experiment that would test the design.
Agree the scope with me as we talk before treating a design as settled.

## Read before forming conclusions

Resolve the following paths against `/Users/patrickroebuck/attune-harness`:

- `CLAUDE.md`
- `docs/design-first-increment.md`
- `docs/harness-phased-plan.md`
- `docs/local-build-receipt.md`
- `docs/review-quality-receipt.md`
- `docs/design-grounded-review.md`
- `docs/design-grounded-passages.md`

Inspect relevant source as needed, especially the execution contract, review
coordinator, participant adapters, recovery, and grounded review modules. Use
actual source and execution receipts to verify claims; a plan or documentation
statement is not implementation evidence.

## Current state and latest evidence

The intended system lets me choose Claude or Codex to lead useful work, involve
other models, and connect them to Attune features through portable contracts and
adapters. The implementation includes a dependency-free core, optional forms,
retrieval and verification integrations, independent review roles, durable
execution/recovery records, and bounded extension/MCP/A2A work. Qualification is
partial: local receipts do not establish broad provider or platform parity.

The original local Phase 6 execution pilot completed, but review quality and my
decision to adopt it as my preferred workflow remain separate questions.

Recent work removed the arbitrary 3,000-character cap and fixed word-count
instruction, made the output-token budget configurable, and added qualified local
token accounting. The 32 KiB narrative and 64 KiB JSON transport limits remain.

The dev5 quality evaluation used six controlled excerpts, three repeats and the
same pinned local model. Single-pass review passed 16/18 trials; the two-role
Harness workflow passed 9/18, missed two critical issues and emitted nine
unsupported assertions. All 54 generations completed normally, using only
20–336 output tokens under a 2,048-token ceiling. Increasing that ceiling would
not address the observed failures.

**The newest implementation is dev6, ahead of some summary documentation.** It
adds an opt-in `--grounded` mode requiring an explicit verdict, reasoning,
uncertainty and exact document/reference quotations. It rejects fabricated
citations and inconsistent or empty structured results. There are 722 passing
tests, 42 new contract tests, 10/10 detected targeted mutations, and 35 passing
installed review/recovery checks. The installed artifact matches 23 source modules.

However, its live usability test failed: **0/27 grounded workflows completed**.
The model repeatedly selected the reviewed document as its reference or supplied
other invalid citations. The guard rejected the first participant’s response,
and the second participant was not run. All 27 failures are retained. Nine
single-pass trials on three fresh cases passed 6/9. The campaign made 36 local
generations, with no paid calls or retries. Zero emitted unsupported assertions
from the failed grounded workflows is not a quality success: they emitted no
accepted reviews.

For that newest evidence, read:

- `docs/receipts/grounded-review/artifact.json`
- `docs/receipts/grounded-review/full-tests.txt`
- `docs/receipts/grounded-review/mutations/summary.json`
- `docs/receipts/grounded-review/run-01/summary.json`
- `docs/receipts/grounded-review/score-output.txt`

**Proposed, not implemented:** have the model select passage IDs assigned by the
harness, then have the harness render the exact source quotations. The design
note exists, but no passage-ID implementation, dev7 artifact or second live
evaluation exists yet. Treat this as a candidate to critique, not a decision to
rubber-stamp. Existing frozen campaigns and environments must remain intact.

## What I want to explore

Start with the overall architecture rather than optimizing only the latest
review failure. Help me reason about:

- The product’s essential job and what belongs in the portable core versus
  workflow policy, model adapters and optional integrations.
- What the harness should enforce deterministically and what remains a model
  judgment or a human decision.
- How evidence, permissions, accepted requirements, uncertainty and execution
  state should travel between participants.
- Whether two independent model reviews justify their added cost and complexity,
  and when a simpler workflow is preferable.
- How to distinguish successful execution, valid citation provenance, correct
  interpretation and a useful result—and how to measure each.
- Whether the passage-ID proposal addresses the right architectural problem,
  and what alternative deserves serious consideration.

Keep responses concise and use plain language. I welcome substantive pushback.
I’m recovering from an operation and using dictation, so ask one focused question
at a time and accept short answers. Begin with a brief account of what the
evidence says, then ask the most important question needed to frame our discussion.
