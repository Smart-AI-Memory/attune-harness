# Design — one work lifecycle behind plan and build

Status: **Tasks 1–7 accepted; Task 8 connected comparison stopped at contract/test handoffs; corrective qualification pending**.
No plan/build production implementation is represented as complete. The selected
fixture, exact module boundaries and runtime probe results are in [first-journey.md](first-journey.md).

## Experience

Proposed examples, not currently registered commands:

```text
attune-harness plan --goal "Add export support to this project"
attune-harness build <work>
attune-harness status <work>
attune-harness resume <work>
```

Plan uses the current request and authorized repository evidence to establish
intent. It asks only for unknowns that alter the result. It proposes a suitable
authoring form with a brief reason. Simple work can remain a clear prompt;
structured tasks can use XML where the consumer or contract requires it; complex
work produces the requirements, decisions and tasks of a spec. Existing workflow
and authorization requirements govern execution for every form.

Human-visible planning presents the desired result, unresolved assumptions,
meaningful alternatives and how the result will be checked. The user can refine
these through conversation or the communication grammar. Supported direct verbs
remain available throughout. A change during active execution takes effect at a
safe operation boundary and creates a revised contract, preserving prior evidence.

Build consumes an accepted executable contract and validates it against the current
repository. Its result includes the actual diff, acceptance evidence, unresolved
findings and any required next action or human decision. It cannot turn a passing model
opinion into a passing implementation.

## Shared representation and ownership

Extend Harness's versioned task envelope with planning and build policies. Keep
one authoritative work record, operation journal and revision history. The authoring
artifact is retained with its content digest; its normalized executable contract,
approval and effects are bound in the task record. Editing an artifact requires
an explicit revision/import step before changed content can govern execution.

Use existing RunStore/RecoveryCursor and shared dispatch/failure handling. Add only
the policy-specific validation and projections needed by the chosen journey.
Reuse attune-forms for grammar rather than adding another form renderer. Legacy
Markdown/XML import is an explicit optional bridge to the existing reader; record
unsupported information instead of silently dropping it. An empty or malformed
task extraction is a visible failure, never a completed build.

Keep the existing spec workspace's distinction between lifecycle receipts and
human actions. Prefer its public adapter/renderer boundaries where the semantics
fit; a Harness adapter must not create a second competing approval authority.
Exact module boundaries and migration strategy belong in the implementation plan
after the first journey is selected.

## Collaboration with purpose

The lead establishes the task and integrates evidence. A bounded exploration
assignment can produce alternative approaches; a critic tests assumptions and
tradeoffs; a worker proposes the scoped implementation; an independent reviewer
assesses the frozen artifact and check evidence. Roles refer to configured
participants rather than hardcoded provider names.

Support explicit solo and multiple-model plans. Extra assignments have a stated
purpose and budget; additional models are not mandatory for already-clear work.
Independent exploration receives the same accepted problem without the lead's
preferred conclusion. Artifact review receives the artifact and checks without
worker self-praise. Keep disagreements and their dispositions visible. One
participant's output cannot supply another participant's independent judgment.

The native adapter currently maps a small set of review roles and has a special
evidence mode. Add explicit operation profiles for planning/building rather than
passing unsupported role strings or assuming review-mode prompts will work.
Model settings and capability availability are checked for the actual assignment.

## Layers of safety and quality

Human intervention is one control among several. Select controls according to the
accepted work and supported host capabilities, retaining existing authorization
rules and quality gates. Do not add a manual confirmation simply because a model
is involved.

| Control | Responsibility and limit |
|---|---|
| Specs, prompts, skills and structured context | Communicate intent, constraints and discipline to the model; instructions alone do not enforce an effect boundary |
| Runtime permissions and effect validation | Constrain the actual operations and protect accepted scope, task state and acceptance inputs independently of model assurances |
| Hooks and lifecycle checks | Run supported checks at defined execution boundaries; distinguish advisory feedback from checks whose failure blocks dependent work |
| Automated tests and independent review | Produce evidence about the artifact; record coverage, failures and uncertainty without treating model agreement as proof |
| Human steering and judgment | Set or correct intent, resolve material choices, intervene through verbs and make the decisions required by the accepted workflow |

Use existing Harness controls and host hook facilities where available. Each
execution profile records which required controls actually ran and their results.
A missing, failed or unsupported required hook/check blocks the dependent operation
with a visible reason; an advisory result remains visibly advisory. Do not claim
hook support across hosts without qualifying each supported profile. This design
does not require a separate general-purpose hook framework.

Account for learned model behavior when designing guidance, grammar and feedback.
The [control audit](control-audit.md) separates current enforcement from assumed
coverage and sets out comparisons for improving weak mechanisms. Evaluate native
tool conventions, prompt structure and examples against response meaning and
reliability on each supported profile; do not assume a shared prompt works equally
well across models. Shared authority semantics remain invariant across adapters.
This work does not require model retraining or claim to identify hidden training
causes from behavior alone.

## Building and checking effects

The first feature profile must support new files as well as modifications. Freeze
the accepted scope, baseline identity, permitted effect kinds and acceptance
inputs before worker execution. A build proposal cannot edit the criteria or the
trusted check used to accept itself. Generated tests may contribute evidence, but
their own success alone cannot establish the feature's acceptance.

The current repair profile scans a tiny dedicated checkout and excludes file
creation. Do not silently reuse those limitations as the definition of general
feature building. Choose and qualify the build checkout/manifest profile against
the selected real journey. Required directory creation, path containment,
symlinks, collisions and interrupted writes need explicit cases. Separate profile
limits from claims of support for arbitrary repositories or platforms.

Reuse host-applied proposals and durable effect records where possible. Retain
before/after identities and completed-operation keys. A crash with an uncertain
effect stops dependent work until observed state can reconcile the operation.
No transaction claim is made for multi-file changes. Process supervision remains
distinct from a security sandbox.

Check each task's artifact and the integrated feature. A passing task does not
prove its dependencies or the final feature work. Preserve rejected evidence and
bind review/check results to final bytes. Human acceptance and configured auto-run
decisions follow the existing discipline, including failure and scope-change stops.

## Cases and evidence before implementation

Must work: a complete clear request; focused clarification of a vague goal;
structured handoff; spec selection for a consequential unresolved design choice;
multiple configured roles; human correction of a plan; feature creation and edit;
interrupted execution; inspection and continuation of the same accepted work.

Must fail visibly: unparseable task artifacts; unsupported assignment profile;
unknown material scope; unapproved changed contract; stale action; omitted check;
scope escape; protected-check edits; file collisions; uncertain effect replay;
unresolved task dependency; an incorrect feature whose self-authored tests pass;
a model claiming compliance while proposing a prohibited effect; dependent work
continuing after a required hook/check fails or cannot run. Valid authorized work
must also pass these controls without unnecessary manual confirmation.

Actual pre-code evidence includes the [source assessment](baseline.md) and
[control audit](control-audit.md), including pure hook probes and 31 selected
existing baseline tests. The [first-journey preparation](first-journey.md) now probes shared-envelope
evolution, adapter roles, parser preservation and scratch create-file recovery.
Those pre-code receipts do not establish implementation. Task 2 subsequently
qualified the structured authoring contract, and Task 3 adds bounded draft
planning through the existing transport and journal. See their result reports;
build effects, the live Spec bridge and native outcomes still need later evidence.

Rejected alternative: port the old spec pipeline as the build engine. Its source
delegates implementation to the host and chiefly runs gates; importing it alone
would not implement a standalone build journey. Rejected alternative: separate
plan and build engines, which would duplicate accepted scope and recovery state.

Strongest counter-case: combining authoring, collaboration and feature effects
creates a substantial increment. One complete first journey should bound the
implementation and provide evidence before generalizing it.
