# Task-first command navigation

Date: 2026-09-16. Direction adopted by Patrick in this conversation; implementation
authorized by “go and show me the current navigation structure,” then confirmed
with “sounds good.” This is a bounded help/onboarding change.

Patrick subsequently refined the interaction model: some commands are primarily
used by the AI, while the human controls work through spec writing and quality
gates. This supersedes the onboarding instruction to learn four commands. Human
navigation centers on intent, scope, acceptance criteria, evidence and decisions;
the command catalog is the execution interface. People can also direct or
intervene in work through the task verbs.

Patrick further clarified that specs are the principal authoring form for complex
features and constructs, while Harness should choose a clear one-shot prompt when
sufficient or an XML-enhanced prompt when structure improves it. These are
alternative authoring forms, not a mandatory progression. Verbs remain available
with each form; existing scope, authorization and applicable quality gates still
govern execution. Automatic authoring-form selection is an intended capability;
the inspected task CLI currently provides goal-based review/fix intake. This
navigation change documents that direction without claiming a new selector.

**Interface coherence, clarified by Patrick on 2026-09-17:** Harness should be
readily expandable, including through plugins, while retaining a clean interface
that is easy to learn. The communication grammar was designed to support this
coherence. New capabilities should fit the shared interaction language instead
of making each plugin, team or workflow teach a separate set of conventions.
Preserve useful capabilities while improving how they are connected and exposed.

Use the rich context of a session to reflect, retain reasoning and improve the
collaboration. A useful pause can deepen understanding without producing a code
change. Insights may refine an existing spec, interface or test; they do not
automatically justify another feature, command or service. This is a design
direction, not a claim that plugin or grammar integration is already qualified.

## Interaction preferences — approved 2026-09-18

The approved design offers two selectable input defaults through the existing
communication grammar:

- **Quick replies:** short replies such as `approve`, `redo`, or `auto` act on
  the current clear recommendation or approved scope.
- **Click controls:** forms present clearly labeled choices with minimal required
  typing. Keep a concise, durable text fallback available if a form disappears.

Natural-language replies remain available with either preference, including
corrections and partial answers. Users can switch input methods as convenient;
the selected default must not disable another method. Both methods can be fast,
so distinguish them by input preference rather than speed.

Explanation length is independent of input preference. A detailed explanation
must still permit a one-click or one-word decision; a brief explanation must
still accept a longer natural-language reply. A short reply with a clear referent
does not require another confirmation. Material ambiguity needs a focused
clarification through the same grammar.

All input methods retain the same decision meaning, revision binding, scope,
budget and acceptance controls. `auto` continues only already-approved work.
Use the existing grammar and decision mechanisms; do not introduce separate
approval systems for each input method.

Status: approved design, not evidence that selectable defaults are implemented
or qualified. Before claiming support, check equivalent decisions through short
replies, clicks and natural language at both explanation lengths, including a
missing form and rejection of a stale decision. This clarification does not
change the current plan/build qualification or authorize additional paid calls.

## Navigation implementation and verification

Default help groups **Task execution** (review/fix), **Task controls**
(status/resume), and **AI tools and integration** (a pointer to the complete
catalog). `--help-all` lists task commands, operational tools and a separate
compatibility section. This is a presentation of the division of responsibility;
it does not add a spec-authoring command or change existing gate authority.
Old names remain callable with their existing arguments, results and exit codes;
simple aliases are appropriate only when those contracts match. No runtime route
is renamed or replaced in this increment. Plan/build/ship/reflect remain absent
from executable help until implemented.

Cases: default help must not enumerate legacy names; full help must expose all
24 current commands; every existing command's own help must remain accessible;
legacy review arguments and completion/acceptance exit semantics must survive;
help must not dispatch a participant or require optional provider dependencies.
The no-argument library demonstration remains unchanged.

Disposable scratch probe before source edits: an argparse subparser action with
`help=SUPPRESS` omitted legacy names from default help while retaining parsing of
an old command and its distinct argument. Its existing subaction metadata still
contained both command descriptions. All three assertions passed. A compact
explicit root usage is needed because suppressing that action also removes its
placeholder from automatically generated usage.

Implementation: derive catalog descriptions from registered parser entries;
render grouped text with the standard raw-description formatter. A help action
selects the complete catalog and exits. Preserve the parser's dispatch and choices.
Update the existing compatibility discovery check to follow `--help-all`, while
retaining the command-help and behavioral regression checks.

Rejected: deleting parser entries to hide them breaks old scripts. Calling every
old command a simple alias hides differences in arguments and behavior. Adding a
new setup command hierarchy expands this change beyond the adopted navigation.
Tradeoff: specialists need an extra discovery step; default help explicitly points
to the full catalog, and command-specific help remains direct.

## Local verification

- Targeted compatibility, intake, assessment, recovery and repair checks: **149
  passed** using `.venv-token-accounting/bin/python -m pytest` on the five owning
  test modules. The compatibility module passed again (**28/28**) after the final
  help-description edits.
- The updated discovery check detects removal of navigation configuration:
  **1/1** failed under a disposable in-process mutation; source was not mutated.
- `PYTHONPATH=src python3 -S -B -m attune_harness --help` passed without site
  packages. Default help exposes four primary commands; full help lists all 24.
  Existing command-specific help and legacy runtime behavior pass their checks.
- `git diff --check` passed. These are source-checkout checks; frozen installed
  environments were not upgraded. No provider calls or remote publication ran.
