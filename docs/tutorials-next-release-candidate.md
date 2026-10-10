# Training walkthroughs for the Harness 1.4.0 candidate

**Unpublished, source-reviewed candidate guidance.** These procedures target
runtime source `df3e242c98a0fecb4c7ac4f6cb143ae30752ab00` and the corrected
noneditable 1.4.0 wheel SHA-256
`c09c3ccc3cd4f280994204f95d35a64b997eaab6e8eaab993c0e7e4dbd064f45`.
The local documentation base is `364ac1011053f5181e297552159c14fed9b6a4a5`.
The [candidate readiness record](release-readiness-1.4.0.md) identifies the
selected components and remaining checks. The publication date and final
shipping SHA remain unset.

The numbered GUI procedures below match the selected source. They have not yet
been walked or captured on this corrected candidate. Earlier #243 captures
remain tied to their original build; they do not verify the changed wording,
#242 guidance, direct opening or reload restoration. Human comprehension and
new derivative rendering remain pending.

The [released 1.3.0 walkthroughs](tutorials-1.3.0.md) and their PowerPoint/HTML
files retain their original instructions, source labels and evidence. This
candidate page does not replace them. Control names are bold; literal answers
and commands use code font. Browser execution remains future work; the selected
1.4.0 candidate provides forms without browser build or execution resume.

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

## Navigation: how can I inspect the approved request?

Prerequisite: Use the pinned candidate interpreter and prepare a fresh synthetic
draft as described below. It starts with an unanswered goal and success
criterion. `TASK` is the returned canonical task directory. Keep the listener
running and use its exact private `launch_url`.

| Step | Action |
| --- | --- |
| 1 | Open the private `launch_url`. The single eligible draft opens its current form directly. If the form is not displayed, inspect the saved state, then click **Continue form** to reopen deliberately. In “**What should this work accomplish?**”, enter `Group saved work by the decision it needs`. |
| 2 | Click **Save answers**, leaving the success question empty. Wait for the “Answers saved” confirmation. |
| 3 | Expand **View saved request**. Check the saved goal, allowed file `source.py`, context `Training example` and constraint `No implementation or model calls`. |
| 4 | In “**What observable result establishes success? Enter one item per line.**”, enter `Each saved task shows its next decision`. Click **Save answers** and wait for the saved confirmation. |
| 5 | Review the answers in the current preview. If it is not displayed, click **Review your answers**. Check the goal, success criterion, allowed files, context and constraints. |
| 6 | If the reviewed request is correct, click **Approve this work request**. Otherwise, click **Keep as draft** to leave it unapproved. After approval, reload the page and inspect **View accepted request**. |

Expected after approval: **Saved work** shows “Intent accepted”.
**View accepted request** displays the approved answers read-only, including the
literal goal and success criterion above. Inspecting this record opens no new
approval form and starts no implementation or model call. This endpoint is
source-defined; a current-candidate browser observation is still pending.

For an explanation of prompt structure, expand **How this becomes a prompt**.
Its XML is illustrative; answer the actual questions in ordinary language.
**Technical details** contains task identity, checkpoint and authoring format
and remains optional.

## Session continuity: what survives reload and reopening?

Prerequisite: Prepare another fresh synthetic draft with the pinned candidate.
Use one browser page and keep its listener running through step 4. This procedure
ends while the request remains a draft.

| Step | Action |
| --- | --- |
| 1 | Open the new private `launch_url`. If the current form is not displayed, inspect saved state, then click **Continue form**. |
| 2 | In “**What should this work accomplish?**”, enter `Group saved work by the decision it needs`. |
| 3 | Click **Save answers**. Leave the success question empty and wait for the “Answers saved” confirmation and the remaining question. |
| 4 | Reload this same page. When its listener, task checkpoint, collector and browser view ownership remain current, the saved goal and blank remaining success question reappear without clicking **Continue form**. |
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
remain separate from client tests. The corrected-candidate walkthrough and human
result are pending. Released 1.3.0 does not include this reload restoration.

## What if the saved inputs changed?

The candidate shows “Accepted intent — inputs changed” and a warning with the
historical **View accepted request** record. Inspect its earlier answers; that
acceptance does not establish authority over changed inputs. This walkthrough
ends at inspection. No automatic retry, new recovery control or browser execution
is described. User understanding of the warning and next permitted action still
needs a source-attributed observation.

## Prepare and reopen the synthetic sample

Use the existing noneditable candidate interpreter throughout. Set `CANDIDATE`
to an absolute checkout containing the pinned candidate fixture and choose an
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

The corrected sample wheel has metadata version 1.4.0. A version string alone
does not identify its source; retain the full source and wheel SHA-256 above.
The fixture grants no implementation, provider or spending authority.

## Review all four training topics before publication

| Topic | Candidate disposition | Remaining derivative or observation work |
| --- | --- | --- |
| Navigation | Selected-source instructions now use direct opening, current approval wording and read-only accepted inspection. | Walk on the pinned corrected wheel, retain matching captures and render changed PowerPoint/HTML copies. Human comprehension remains pending. |
| Session continuity | Selected-source instructions now separate same-page restoration, deliberate reopening and listener restart. | Observe saved goal plus blank remaining field, ownership refusal and fresh launcher behavior; capture and render matching derivatives. |
| [Specification workflow](tutorials-1.3.0.md#specification-workflow-preview-and-acceptance) | Existing three literal CLI actions were replayed on the corrected 1.4.0 wheel. The plan was accepted; `calc.py` stayed unchanged and no build state was created. Keep the historical tutorial bytes. | The CLI procedure is unchanged but reviewed for this candidate. Candidate presentation framing and any historical GUI images require separate disposition. |
| [Four workflows research](tutorials-1.3.0.md#four-workflows-research-a-question) | Existing retrieve/verify pair was replayed on the corrected wheel: two retained source hashes, one verified link and `semantic_ran: false`. Keep the historical tutorial bytes and sample-policy limits. | The CLI procedure is unchanged but reviewed for this candidate. Review any approval controls and GUI images in the broader deck separately. |

These five command results belong to the release owner's retained corrected-wheel
replay receipt; they are not new runs in this documentation pass. They do not
establish policy truth, semantic model output, graphical behavior or presentation
rendering. The historical released local-workflow guide's dev0/old-extra/future-forms
wording remains historical; use current versioned setup guidance.

For retained consultation evidence, the candidate adds opt-in
`--format markdown` to `source-review` and `roundtable` `prepare`, `status` and
`evidence`; JSON remains the default. Follow the existing
[consultation guide](model-consultation.md#readable-consultation-views) for the
exact commands, local seat `check`, roundtable initialization and batch citation
assessments. These inspection/setup features do not grant dispatch or spending
authority. The separately prepared #233 concurrent-round/selective-retry feature
is not included in this selected candidate.

Keep canonical instructions, PowerPoint/HTML copies and the Help projection on
matching reviewed source pins. Record changed versus reviewed unchanged topics,
examples, observed results, link checks and retained versus superseded guidance
through the existing release checklist. Version selection does not make these
local files published or close the remaining software and human observations.

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
