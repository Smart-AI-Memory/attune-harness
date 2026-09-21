# Spec authority — owned by Harness, built from reviewed Attune AI code

Status: **direction approved by Patrick, September 19, 2026** (“everything you
say sounds good in your recommendation go”). No task is started or accepted, and
no code exists for the spec authority yet. Target: second release candidate.

## D1 — User-set objective

Patrick stated the retirement plan: “My plan is to deprecate attune-ai as soon as I
can release a stable version of attune-harness. Hopefully, sometime during
October-November after a period as release candidate.”

He set the constraint on what comes across: “I want to make sure we DO NOT bring
over old, and far less than useful code, in the new attune-harness.”

He then set the rule for code that is solid: “Use solid code from attune-ai. We
spent months working on it, so it has earned the right of a review and possibly
included in the second release candidate. If only as an example to cut your
workload.”

An earlier draft of this note read his “create not use” as excluding all Attune
AI source. That reading was wrong and is withdrawn. Harness creates the
*authority*; Attune AI code is eligible to build it.

## D2 — This reverses a standing boundary, deliberately

The current design makes Attune AI's Spec workspace the approval authority. The
[capability map](../connected-journey-qualification/capability-map.md) assigns
“Spec human decisions” to the “existing AI Spec workspace/collector,” and the
[plan-build design](../plan-build/design.md) says a Harness adapter “must not
create a second competing approval authority.”

That was the right rule while both products were meant to coexist. It is the
wrong rule for a product that replaces the other. **After this decision, Harness
owns spec approval outright.** The rule against a second authority still holds:
Harness becomes the only one, and the runtime bridge to Attune AI is retired.

This does not revive plan-build's rejected alternative. That rejection was about
porting the old spec pipeline *as the build engine*. It stands.

## D3 — Evidence for why this is on the release path

On a clean Linux checkout of `wip/local-snapshot-2026-09-19` (September 19), the
plan/build CLI fails with “Spec acceptance requires the qualified optional Attune
AI Spec runtime.” The failing tests in `test_work_cli`, `test_work_controls`,
`test_work_decisions` and `test_spec_handoff` trace to `spec_bridge.py`, which
imports `attune.spec.workspace`, `attune.elicitation.command_workspace` and
`attune.pipeline.spec_reader`.

Specs are Harness's principal authoring form for complex work. A replacement that
needs the replaced product installed to approve its specs is not yet a
replacement.

## Review, then adopt, adapt, reference or drop

Every Attune AI module in the spec path gets one recorded verdict:

| Verdict | Meaning | Where it ends up |
|---|---|---|
| **Adopt** | Solid as written; its tests pass against Harness contracts | Moved into `attune_harness`, with its tests, as Harness-owned code |
| **Adapt** | The core is sound; its seams assume Attune AI internals | Reworked at the seams, core logic and tests kept |
| **Reference** | The behavior is right; the structure does not fit the task engine | Harness implementation written against it; its tests become characterization cases |
| **Drop** | Superseded, or less than useful | Not carried; the verdict records why |

Adopted and adapted code stops being Attune AI code. It lives in the Harness
namespace, runs under Harness CI, and carries no runtime `import attune`. A CI
check enforces that last point for the whole package (`attune_forms`,
`attune_rag` and `attune_verify` remain allowed).

A module earns **adopt** when it has its own tests, a versioned or otherwise
stable data shape, no hidden dependence on Attune AI globals or registries, and a
boundary that maps onto an accepted task record. Missing any one moves it down a
row, not out.

### First candidates

| Module | Why it is a candidate |
|---|---|
| `spec/state.py` | Versioned on-disk state (`schema_version`), atomic writes, back-compatible reads. Harness's own `.claude/plans/` use this format today, so adopting it may satisfy R4 outright |
| `spec/workspace.py` | Separates lifecycle receipts from human actions and refuses to reinterpret spec-owned state, which is the property D2 needs |
| `pipeline/spec_reader.py` | Parses the `<task>` elements the XML plans are written in |
| Salvaged September edits to `spec/state.py` and `spec/workspace.py` | Uncommitted work from `codex/shared-memory-adoption`, preserved in `~/attune-salvage`; likely the newest thinking on this boundary and not yet reviewed |
| `elicitation/command_workspace.py` | Hosts the decision surface today; likely **adapt** or **reference**, since Harness has its own navigation and error envelope |

## Acceptance (draft)

- **R1 — Single authority.** Create, review, approve and reject decisions for a
  spec are recorded in Harness's task store and nowhere else. A stale or replayed
  decision is refused.
- **R2 — No Attune AI runtime.** Plan/build completes an approved-spec journey in
  a clean environment with Attune AI absent. The import check passes in CI.
- **R3 — Human gates preserved.** Every quality gate that requires a human
  decision today still requires one after the change.
- **R4 — Attune AI spec state is readable.** Every plan in `.claude/plans/` that
  a Harness spec cites remains readable, and Harness reads schema-version-1 spec
  state from any Attune AI project (D4). Unknown versions are refused with a
  plain next action, never guessed at.
- **R5 — Every verdict recorded and independently reviewed.** Each module has an
  adopt, adapt, reference or drop verdict with its reason. Each adopt or adapt
  verdict is reviewed by a team whose reviewing agents use different models from
  the authoring agent (D5), and adopted tests pass under Harness.
- **R6 — Understandable to a domain expert.** A person without a programming
  background can approve, reject and inspect a spec using the task-first
  navigation, with every blocking state carrying a plain next action.

## Task ladder (draft)

| Task | Outcome | Evidence |
|---|---|---|
| 1 | Review the spec path from `spec_bridge.py` inward, including the salvaged edits | Verdict table for R5 with independent team reviews; failure modes noted |
| 2 | Bring adopted modules and their tests into Harness | Tests green under Harness CI; no `import attune` |
| 3 | Specify and implement approval and gate decisions on the task engine | R1 and R3 tests; stale and replayed decisions refused |
| 4 | Switch plan/build to the native authority and retire the bridge | R2 clean-environment journey |
| 5 | Read Harness's own plans and other projects' Attune AI spec state | R4 receipt for every cited plan, plus fixtures from at least one external project |
| 6 | Qualify the installed journey with a non-programmer walkthrough | R6 observed, not inferred |

## Strongest counter-case

Adopting code saves time only if it fits. Modules shaped around Attune AI's
registries, plugin loader or MCP host can cost more to disentangle than to
rewrite, and code that passed review in its old home can hide assumptions that
only fail in the new one.

The response is the verdict ladder. A module that needs deep surgery drops to
**reference**: its tests and behavior still cut the workload, without importing
its structure. Adoption is earned per module, not granted by the project's
history.

## D4 — Legacy spec state: read it, from any project

Asked whether Harness should read spec state from other people's Attune AI
projects or only its own plans, Patrick answered: “yes but it's been worked on
recently and represents my current development ‘level/state’ I am willing to
invest in it after having made the judgement it will let us get to a better
development ‘level/state’ faster in the long run.”

Harness therefore reads Attune AI spec state generally, not only its own plans.
This is also the migration path for Attune AI users at deprecation. R4 is widened
to match.

## D5 — Independent review by model-diverse teams

Asked whether each adopt verdict needs an independent review before Task 2,
Patrick answered: “yes, but I took that to a new level with teams of agents that
used different models based on the agent not just the workflow.”

Each adopt or adapt verdict is reviewed by an agent team in which model choice
follows the agent's role. The reviewing agents must not share a model with the
agent that proposed the verdict. The verdict records the team, the roles and the
models used.

## D6 — Timing: what may wait until after the first stable release

Patrick asked for candidates and expects few or none to qualify. The list below
is the assistant's recommendation, not a decision. The test applied: does an
Attune AI user lose something they depend on, or does a new user hit it on day
one? If either, it cannot wait.

**Cannot wait.** Full-suite CI, a clean-clone install that passes its tests, no
runtime `import attune`, this spec authority (Tasks 1–5), the legacy reader in
D4, and an honest README status. These are what make the release stable and the
deprecation possible.

**Patrick's rulings on the candidates** (September 19). “Defer” never meant
discard: every item below keeps its existing work in the repository.

| Candidate | Ruling | Consequence for this plan |
|---|---|---|
| Plan/build Task 8 across providers and roles | “I did a lot of work on that and don't want it replaced, rather I want to build on ‘build’” | Task 8 continues on the existing build work. Stable names each profile that has qualified by then; the rest ship labeled experimental, not removed |
| Voyage validation reuse | “I did LOTS of work on this … got excellent results using luna and python. I don't want to loose any work here either” | Retained in full. The spec itself is a narrow validation-count optimization; the retrieval-quality results are separate work already in the repository |
| `elicitation/command_workspace.py` | “keep” | Moves from reference to an **adopt/adapt** candidate. Harness must still end with one decision surface, so its review decides whether it becomes the renderer behind task-first navigation |
| Writing Attune AI spec state back | Left to the assistant's judgment | **Read and convert; never write back.** Originals stay untouched and each conversion leaves a receipt. Writing the old format would keep a second authority alive, against D2 |
| Windows build effects | Question asked; see the Windows note below | Open |
| Remote A2A authentication | Deferred by Patrick after discussion | Waits until after the first stable release. The qualified local A2A profile ships as it is, still labeled local-only |
| Executable plugins | “need it” | Required for stable. Gets its own spec with a threat model, and sandboxing or signing, before implementation; it is not a small addition to this one |

**Windows note.** Marking build effects POSIX-only states the gap; it does not
close it. The effects layer relies on `dir_fd`-relative opens, `O_NOFOLLOW` and
directory `fsync`, which Python does not provide on Windows. A native Windows
implementation needs handle-based equivalents (reparse-point checks instead of
`O_NOFOLLOW`, write-through replacement, explicit flushes) and its own safety
review. Until then, running Harness inside WSL2 gives Windows users the POSIX
profile unchanged.

**Should not wait, though it is tempting:** Task 6, the non-programmer
walkthrough. The release candidate period is the natural place to run it, and the
audience it tests is the one Harness is for.

## D7 — Voyage stays a Harness extra, behind the plugin boundary

Voyage retrieval ships as `attune-harness[voyage]`, not as a separate package.
Patrick agreed after reviewing the alternative (`attune-harness-voyage`) and its
release-coupling cost.

Two conditions come with it:

- **Qualified pins stay exact; incidental pins become ranges.** `voyageai` and
  `lancedb` stay pinned exactly, because `require_feature` refuses any other
  installed version at runtime and recovery records those versions in each run
  profile. Loosening them in `pyproject.toml` alone would trade a resolver
  conflict for a runtime refusal. `pyarrow` and `jsonschema` are not checked at
  runtime and are shared with much of the data stack, so they now declare
  compatible ranges. The exact versions remain in `requirements-voyage.lock`,
  which CI already uses as constraints.
- **Voyage loads through the extension interface.** The executable-plugin spec
  should use Voyage as its first real consumer, so the boundary is proven by
  Harness's most substantial integration rather than only by the example
  plugin. If Voyage ever needs its own release cadence, that boundary makes a
  later split into `attune-harness-voyage` straightforward.
