# Training walkthroughs for Harness 1.4.0

These walkthroughs describe the bounded 1.4.0 forms companion. Practice saving
answers, returning to them, approving a work request and inspecting its saved
state. Browser build and execution resume remain future work. The
[preparation readiness record](release-readiness-1.4.0.md) retains dated checks,
observations and their source pins. Match an installed version, source commit
and wheel SHA-256 to its release evidence; a version string alone is insufficient.

Patrick's base-runtime walkthrough recorded accepted-request inspection,
accepted-state reload, unfinished-form reload with the saved goal retained, and
typing in the remaining field. His separate exact-source preview inspection
accepted the inline saved-answer presentation. These bounded observations do not
establish every numbered step below, independent approval comprehension, exact
Tab order, copied-tab behavior or accessibility conformance. Attribute new captures
to their source and version; retain earlier captures with their original source
labels.

The [released 1.3.0 walkthroughs](tutorials-1.3.0.md) and their PowerPoint/HTML
files remain historical with their original instructions, source labels and
evidence. This written 1.4.0 page is the approved interim guide; replacement decks
and separate Help deployment are deferred. Control names are bold; literal
answers and commands use code font.

## Approval: what does each choice do?

In **Review your answers**, click **Approve this work request** only to record
approval of the reviewed goal, success criteria, scope, context, constraints
and choices. Click **Keep as draft** to leave that request unapproved for
reconsideration. Neither choice starts work or authorizes a model call.

The saved state still uses “Intent accepted”. That state describes the recorded
request decision, not an execution grant. The controls are presentation labels
for the existing single-use decisions. Earlier #243 procedures and captures use
**Accept this intent** and **Keep draft for reconsideration**; those labels stay
historical. Human understanding of the new wording remains pending.

## Save and approve a clear work request

Keep your goal and definition of success together so you can check the whole
request before approving it. You’ll practice saving answers, returning to them,
and recording exactly what you approve. You’re done when your approved request
survives a reload and remains readable without editable fields.

### Before you start

Ask the person or agent running Harness for a fresh practice form and its
complete private link. Use one browser tab and keep the local form launcher
running. If you already see **Intent accepted**, go to step 8.

1. Open your practice link.
   You’ll see **Saved work** and the questions. If they’re hidden, click
   **Continue form**.

2. Enter your goal.
   In **What should this work accomplish?**, enter:
   `Check that my saved request survives a reload.`
   Leave the success question empty for now.

3. Click **Save answers**.
   Wait for the saved confirmation. **Saved answers** shows your goal;
   **Still needed** identifies the unanswered success question. Your request
   is saved as a draft.

4. Reload the tab.
   Your saved goal should remain visible. If necessary, click **Continue form**
   to reach the remaining question.

5. Define success and save again.
   In **What observable result establishes success? Enter one item per line.**,
   enter: `After reloading, the saved goal remains unchanged.`
   Click **Save answers**. **Review your answers** should show both answers.
   If the review is hidden, click **Review your answers** on the saved-work card.

6. Check the whole request.
   Confirm your goal and success criterion, the sample file `source.py`, the
   context `Training example`, and the constraint `No implementation or model calls`.
   These are all part of what you’ll approve.

7. Record your decision.
   If everything is correct, click **Approve this work request**. Your answers
   are already saved; this records acceptance of the whole request.
   **Intent accepted** appears. Approval does not start implementation or
   authorize execution.
   To leave the request unapproved, choose **Keep as draft**.

8. Verify the accepted request.
   Reload the tab and inspect **View accepted request**, which opens expanded.
   If you have collapsed it, expand it again. Both answers should remain visible,
   with no editable answer fields. This completes the practice.

### What comes next?

To prepare your own work, ask the person or agent running Harness for a new
draft for that task. Starting the work requires a separate explicit decision.

### Launcher reference and optional details

For local launcher setup, see
[Prepare and reopen the synthetic sample](#prepare-and-reopen-the-synthetic-sample).

For an explanation of prompt structure, expand **How this becomes a prompt**.
Its XML is illustrative; answer the actual questions in ordinary language.
**Technical details** contains task identity, checkpoint and authoring format
and remains optional.

## Session continuity: what survives reload and reopening?

Prerequisite: Prepare another fresh synthetic draft with the selected 1.4.0 installation.
Use one browser page and keep its listener running through step 4. This procedure
ends while the request remains a draft.

| Step | Action |
| --- | --- |
| 1 | Open the new private `launch_url`. If the current form is not displayed, inspect saved state, then click **Continue form**. |
| 2 | In “**What should this work accomplish?**”, enter `Group saved work by the decision it needs`. |
| 3 | Click **Save answers**. Leave the success question empty and wait for the “Answers saved” confirmation and the remaining question. |
| 4 | Reload this same page. When its listener, task checkpoint, collector and browser view ownership remain current, **Saved goal:** and the blank remaining success question reappear without clicking **Continue form**. Check that **Still needed** separates the instructions from the saved answer, then type in the remaining field. |
| 5 | Stop the listener with `Ctrl-C`. Run `python -m attune_harness.gui --task "$TASK" --edit --launch-json` with the same `TASK`. |
| 6 | Open the new private `launch_url`. Inspect the saved goal and remaining blank success question. If the current form is not displayed, expand **View saved request**, then click **Continue form** to reopen deliberately. |

Expected: the saved goal retains its exact wording and the task remains a draft.
Saved answers persist; unsaved typing is not restored. A listener restart opens
a fresh collector rather than restoring the old one. The shared sample retains
`source.py`, `Training example` and `No implementation or model calls`.

Same-page restoration requires usable session storage, reload navigation timing
and an exclusive Web Lock. It inspects the current collector without replacing
it, replaying a response, approving a request or starting work. If another view
owns the form, the checkpoint changed, or a submission was unconfirmed, inspect
saved answers and click the displayed **Continue form** or **Review your answers**
to reopen deliberately. Inspect saved state before repeating any unconfirmed
answer; Harness does not replay that submission for you.

Record the actual browser/version, source, wheel identity and assistance when
walking these steps. Copied-tab, history and native lock scheduling observations
remain separate from client tests. Patrick observed same-view unfinished reload and editable remaining input on the
base runtime. The local presentation preview is separate evidence; installed
revised-layout captures, exact Tab order and other native ownership transitions
remain pending. Released 1.3.0 does not include this reload restoration.

## What if the saved inputs changed?

Harness 1.4.0 shows “Accepted intent — inputs changed” and a warning with the
historical **View accepted request** record. Inspect its earlier answers; that
acceptance does not establish authority over changed inputs. This walkthrough
ends at inspection. No automatic retry, new recovery control or browser execution
is described. User understanding of the warning and next permitted action still
needs a source-attributed observation.

## Prepare and reopen the synthetic sample

Use the selected noneditable 1.4.0 interpreter throughout. Set `CANDIDATE`
to an absolute checkout containing its version-matched fixture and choose an
unused, absolute, resolved `TRAINING` directory for each procedure. Keep task
storage outside the project. On macOS, use a resolved path such as `/private/tmp`
rather than the `/tmp` symlink. The helper creates a synthetic project,
deterministic registry and saved draft without a participant call.

```sh
CANDIDATE="/absolute/path/to/pinned-candidate-checkout"
TRAINING="/absolute/resolved/unused/training-form"
python "$CANDIDATE/examples/browser-intake/prepare.py" "$TRAINING"
```

Copy the returned `task_directory` into `TASK`, then launch the listener:

```sh
TASK="/absolute/canonical/task-directory-returned-by-prepare"
python -m attune_harness.gui --task "$TASK" --edit --launch-json
```

Keep the listener running and open its exact returned private `launch_url`.
For a restart, stop it with `Ctrl-C` and repeat the launch command with the same
`TASK`. Open the new launcher link. Each independent procedure starts from its
own newly prepared draft. A private launcher link is listener access data,
not a permanent task link. Do not replace an existing human-review listener.

Use a noneditable 1.4.0 installation. Before walking the sample, obtain its full
source commit and wheel SHA-256 from the release evidence. Check the [readiness record](release-readiness-1.4.0.md)
for the selected scope and remaining qualification limits.
A version string alone does not identify its source. The earlier C09 runtime
excludes the inline saved-answer refinement and cannot illustrate that layout.
The fixture grants no implementation, provider or spending authority.

## Historical preparation topic review

The table below retains the earlier candidate assessment. The approved October
12 disposition uses this written 1.4.0 guide and defers replacement decks and
separate Help deployment. Independent observations and broader GUI claims remain
open; the historical remaining-work column does not override that disposition.

| Topic | Candidate disposition | Remaining derivative or observation work |
| --- | --- | --- |
| Navigation | Instructions include direct opening, current approval wording, inline **Saved goal:** and **Done when:** labels, **Still needed**, and read-only accepted inspection. Base intake/accepted inspection and the separate revised visual preview have human observations. | Capture the selected layout with source/version attribution; retain applicable base evidence. Independent approval comprehension and exact keyboard checks remain open. New deck rendering or an explicit interim-material disposition is required. |
| Session continuity | Instructions separate same-page restoration, deliberate reopening and listener restart. Base accepted-state and unfinished-form reload have bounded human passes. | Capture the revised saved/remaining split. Keep earlier launcher failures and uncertainty visible; other ownership transitions remain unobserved. New deck rendering or an explicit interim-material disposition is required. |
| [Specification workflow](tutorials-1.3.0.md#specification-workflow-preview-and-acceptance) | Existing three literal CLI actions were replayed on the corrected 1.4.0 wheel. The plan was accepted; `calc.py` stayed unchanged and no build state was created. Keep the historical tutorial bytes. | The CLI procedure is unchanged but reviewed for this candidate. Candidate presentation framing and any historical GUI images require separate disposition. |
| [Four workflows research](tutorials-1.3.0.md#four-workflows-research-a-question) | Existing retrieve/verify pair was replayed on the corrected wheel: two retained source hashes, one verified link and `semantic_ran: false`. Keep the historical tutorial bytes and sample-policy limits. | The CLI procedure is unchanged but reviewed for this candidate. Review any approval controls and GUI images in the broader deck separately. |

These five command results belong to the release owner's retained corrected-wheel
replay receipt; they are not new runs in this documentation pass. They do not
establish policy truth, semantic model output, graphical behavior or presentation
rendering. The historical released local-workflow guide's dev0/old-extra/future-forms
wording remains historical; use current versioned setup guidance.

For retained consultation evidence, 1.4.0 adds opt-in
`--format markdown` to `source-review` and `roundtable` `prepare`, `status` and
`evidence`; JSON remains the default. Follow the existing
[consultation guide](model-consultation.md#readable-consultation-views) for the
exact commands, local seat `check`, roundtable initialization and batch citation
assessments. These inspection/setup features do not grant dispatch or spending
authority. The selected release also includes the merged #233 first-round
concurrency and explicit refused-turn recovery. Follow the same consultation
guide for that separate CLI journey and its partial-result, retry and unknown
effect limits. The browser companion does not dispatch consultation work.

Keep canonical instructions, PowerPoint/HTML copies and the Help projection on
matching reviewed source pins. Record changed versus reviewed unchanged topics,
examples, observed results, link checks and retained versus superseded guidance
through the existing release checklist. Version selection does not make these
local files published or close the remaining software and human observations.


## Historical preparation metadata (October 12 snapshot)

The following text records the earlier preparation state, superseded by the dated
[readiness record](release-readiness-1.4.0.md). The
[original candidate introduction](https://github.com/Smart-AI-Memory/attune-harness/blob/09f79820831ea7cdc3df83a8b2f772fd57ee25c7/docs/tutorials-next-release-candidate.md)
retains its original source and publication boundaries.

**Unpublished candidate guidance.** Patrick selected the merged #233 consultation
changes alongside the approved saved-answer presentation for 1.4.0. Current
preparation base: `e459faeb9909c9d2cbbb7337dc18e460d5d49e1f` (#260),
including the merged #258 consultation changes and #234 golden follow-up.
The owner tracks the remaining macOS supplemental coverage result separately.
Reviewed forms source:
`3d317e71324b609d5e9f603bf88b447e9007345e`. The new local combination has
not replaced the live practices or been published. The
[readiness record](release-readiness-1.4.0.md) separates component observations
from required combined qualification. Publication date, final shipping SHA and
archive hashes remain unset.


## Historical #243 source and evidence

The following records describe the earlier #243 procedures, not the selected
1.4.0 steps above. Their original numbered instructions remain in the
[retained published candidate draft](https://github.com/Smart-AI-Memory/attune-harness/blob/e9f3dd1dccc2d0f6435dc55b7dd2c94b6db7d194/docs/tutorials-next-release-candidate.md).
All original source, wheel and capture hashes remain unchanged.

The GUI owner retained ten actual synthetic captures at installed source
`a51460dfcd15701b36955d74a5e1324adc1a4f80`, unchanged in #243's final head
`0e1a285307b3f9593e504ba0139a3f9e8e83992a`. Documentation-only `af34fe4` and
the main prototype-check update change no browser source or tests. The current
capture manifest SHA-256 is `07065ac63bd783140dd9c7ab751d3848021248acbb1fc4c7783f9fe484b9097f`;
the installed sample wheel SHA-256 is
`b38c302de95cce80e528fe0d60f6b5e63bbbfbf7bd34369ba99598468671942e`.

The retained owner handoff records approved source, 20 successful automatic
checks, completed full-source/installed-platform receipts, zero model calls,
keyboard Enter on disclosures and the bounded 320px layout observation.
Captured accepted revision 3 has no planning/build, and drift inspection
preserves owner bytes. Captures 06/07 show accepted request and optional prompt
details; 09/10 show the warning and retained historical answers. They exclude
#242 hints.

Patrick merged #243 on October 8, 2026 at 7:43 p.m. America/New_York. GitHub
reports a valid signature on the squash. Its complete tree
`9ef266723c972a7c8e61ec9440d81d94eeee29b6` equals the qualified head and CI
synthetic tree. All twelve original receipt hashes and ten capture hashes
remain unchanged. This reconciles the merge with existing evidence; no new
post-merge main qualification or release claim follows from it.

The tutorial owner independently walked both staged GUI procedures against the
installed candidate, checking all 103 installed modules against the pinned
source before and after. Navigation ends accepted at revision 3; Continuity ends
as a draft at revision 2 with a fresh empty success field. Restarted listeners
issue fresh launcher links. Saved-request inspection preserves owner bytes,
no planning/build state appears, and execution remains disabled. The two new
full-page captures were visually reviewed. This is bounded walkthrough evidence,
not a repeat of the owner's full or platform qualification.

Read the pinned [journey specification](https://github.com/Smart-AI-Memory/attune-harness/blob/0e1a285307b3f9593e504ba0139a3f9e8e83992a/docs/specs/saved-request-journey/README.md)
and [sample preparation](https://github.com/Smart-AI-Memory/attune-harness/blob/0e1a285307b3f9593e504ba0139a3f9e8e83992a/examples/browser-intake/prepare.py)
for the owner handoff and fixture. Synthetic software/capture evidence does
not establish real-user benefit, model quality, assistive-technology or 400%
qualification, or general WCAG conformance. The combined release candidate
needs its own exact-source and derivative checks.
