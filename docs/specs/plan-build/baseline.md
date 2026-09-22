# Plan and build — source assessment

Date: 2026-09-16. Status: scoping evidence; no implementation plan is approved.
Owner: attune-harness. Patrick requested implementation of plan/build through the
next generation of the spec workflow, including goal discovery, multiple
models/LLMs, creative exploration and the established engineering discipline.

## Inspected sources

Harness HEAD: `fc65e74fc7c289f71f3a7d081dfe7c1be1238c33`, with this conversation's
uncommitted navigation changes and unrelated Voyage/reranker work present.
Attune AI reference HEAD: `fe08f282fb0ad9cbb7eedf75af2597336576578e`.
This is a local source assessment, not a remote freshness or installed-provider
qualification claim. Attune AI is a read-only reference for this work.

| Finding | Source | Consequence for the next design |
|---|---|---|
| Goal-based review/fix intake already stores accepted scope, participants and permissions | `src/attune_harness/task_contract.py`, `src/attune_harness/task_cli.py` | Extend shared contracts; do not create separate plan and build identities |
| Assessment and repair share participant dispatch, effect journaling and failure handling | `src/attune_harness/task_runtime.py`, `src/attune_harness/task_policies.py` | Reuse these services for planning assignments and build operations |
| Repair is limited to existing regular UTF-8 files in a bounded dedicated POSIX checkout | `src/attune_harness/repair.py` | Feature creation needs an explicit file-creation effect contract; renaming fix cannot supply build |
| Participant transports support deterministic, explicit command, Claude and Codex adapters | `src/attune_harness/review_participants.py`, `src/attune_harness/native.py` | Separate assignment roles from model/provider choice; preserve requested versus observed identity |
| Native role handling and evidence mode are review-specific | `src/attune_harness/review_participants.py` | Planning/build roles need explicit adapter mapping; do not assume arbitrary role names already work |
| The old spec workspace owns stages, bound actions, lifecycle receipts and saved state projections | `/Users/patrickroebuck/attune-ai/src/attune/spec/workspace.py`, `/Users/patrickroebuck/attune-ai/src/attune/spec/state.py` | Preserve the distinction between an evaluation receipt and a human lifecycle decision |
| The old pipeline runs gates; its class documentation explicitly leaves task implementation to the host assistant | `/Users/patrickroebuck/attune-ai/src/attune/pipeline/orchestrator.py` | A standalone build journey must define who performs edits and how effects are accepted |
| Existing spec documents and XML plans are read through the existing task parser | `/Users/patrickroebuck/attune-ai/src/attune/pipeline/spec_reader.py` | Import/export must preserve supported task information; unparseable input cannot become an empty successful build |

## Discipline to carry forward

The canonical authoring selection rules are the Attune AI
[collaboration contract](/Users/patrickroebuck/attune-ai/content/collaboration/contract.md#artifact-selection)
and [XML eligibility rules](/Users/patrickroebuck/attune-ai/.claude/rules/attune/xml-enhanced-prompts.md).
They select by consequence, ambiguity, dependency and continuity needs, not a file
count cutoff. The new selector must preserve these rules rather than create a
competing definition. Plain prompts, structured task prompts and specs are
alternative authoring forms; a short prompt never supplies missing authority.

The existing Socratic policy asks only when missing information materially changes
the work. Supplied goals, constraints, corrections and accepted answers survive
continued planning. Human verbs remain available alongside spec authoring and
quality gates. Decision, pushback and per-item disposition use the communication
grammar; model proposals remain distinguishable from human choices.

Creativity should produce useful candidate approaches with tradeoffs and evidence.
Multiple models can explore, critique, implement and review bounded assignments.
Neither role count nor model agreement proves correctness. Test the contribution
of additional roles on frozen cases and retain failures; do not claim that existing
review/fix provider qualification transfers to plan/build.

## Open scope decision

The active decision form asks which complete first journey defines done:
feature work in an existing repository (recommended), creating a new project,
or both in the first release. No answer has been recorded at this assessment.
This affects build effects, scaffolding and acceptance cases; the source findings
above apply independently of that choice.

No plan/build source edits, provider calls, delegated agents or gate waivers were
made during this assessment. Existing navigation edits remain a separate completed
slice of this conversation.
