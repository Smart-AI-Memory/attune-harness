# Reporting course compatibility

## Phase 1 requirements

**Status** — Approved by Patrick on November 11, 2026. See the [design draft](design.md).

### Problem and outcome

Get Started is moving to a single base install that selects the current
compatible Harness release. The six-lesson course still installs and requires
exactly 1.7.0. With the published 1.8.0 interpreter, the practice helper refuses
before creating a project. A test currently expects that refusal.

Learners can follow the same course with 1.8.0 or another compatible Harness
release. A new package version alone does not require rewritten lessons.
Changes to a command or behavior the course relies on trigger a review of the
affected steps. The changelog records deprecations, and an upgrade that
requires reader action links to migration instructions.

### Scope

- The reporting course setup, practice helper, generated lessons, and Help
  links that describe the current practice path.
- Offline compatibility checks and evidence for the runtimes used to qualify
  the course.
- Preserve the six lessons, practice inputs, protected tests, sample report,
  saved browser progress, public deep links, and original versioned records.
- Scope stops at course and Help behavior. Harness runtime commands, effect
  protections, provider settings, and production deployment retain their
  existing ownership.

### User stories

1. A new learner can start from the normal Harness installation and reach the
   first reporting exercise with a compatible interpreter.
2. A learner with a working Harness environment can use it for practice when
   it satisfies the requirements, or prepare a separate practice environment.
3. A maintainer can run the same course checks on a new release. Passing
   compatibility checks require no lesson edits.

### Coverage areas

| Area | Requirement |
| --- | --- |
| Runtime compatibility | Allow the selected installed runtime when it supports the course's required interfaces. Establish evidence initially on published 1.7.0 and 1.8.0. Keep future claims tied to verified behavior. |
| First run | Show one default path. State Python, Git, and pytest prerequisites at the relevant step. Guide a reader with a missing requirement to the specific fix. |
| Course contract | Preserve preparation, draft review, exact-checkpoint acceptance, separately authorized local build, saved-task inspection, and report generation. Use the selected interpreter throughout. |
| Offline and authority | Command practice runs offline after dependencies and fixtures are available. The practice helper prepares an unaccepted request, and fixed local participants make zero model calls. |
| Refusals | Missing or incompatible runtime capabilities give an actionable result before creating a practice project. Existing practice state is preserved on failure or repeat invocation. |
| Evidence | Record the tested Python and Harness versions separately from the lesson copy. Preserve the original 1.7.0 receipts and their artifact identity. |
| Updates and rollback | Course copy changes when an actual interface change affects the learner journey. Preserve a versioned route or archive when readers need the original steps, and deliver the updated export only after source review. |

### Acceptance

- Run the published 1.7.0 and 1.8.0 runtimes separately through the published
  setup and reporting journey on a qualified environment. Both complete the
  same deterministic exercise, pass the two protected test files, preserve
  protected inputs, and produce the expected six-entry, 270-minute HTML report.
- A compatible version can qualify without changing lesson prose or resetting
  saved course progress. The tests prove the exercised capabilities and report
  the runtime they used.
- An absent dependency, a runtime missing a required capability, and an
  existing practice destination each have a focused negative check.
- The public Help and course links, renderer, copy controls, and archived
  receipts remain valid. Production validation follows the website import.

See the [command owner walk](README.md) for the current journey and refusal
conditions. The compatibility mechanism and supported verification matrix
belong to the design phase.
