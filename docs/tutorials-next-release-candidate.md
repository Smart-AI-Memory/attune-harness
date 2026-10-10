# Training walkthroughs for the next Harness candidate

Unreleased review draft. These GUI procedures describe the
[saved-request GUI](https://github.com/Smart-AI-Memory/attune-harness/pull/243)
reviewed and qualified at `0e1a285307b3f9593e504ba0139a3f9e8e83992a`, now merged
as signed squash `82cdff9379b62e1858eb44366d0923721ff037e5` with an identical
complete tree. The next release's version, date and combined source commit have
not been selected. The separate form guidance in #242 is absent from this
tested tree and its captures. That guidance has since merged to main as
`9410c4b57df5e0dc6cb1a5fcb38d0fb5a665ce37`; this page does not claim that the
earlier walkthroughs or captures qualify the combined source.

The [released 1.3.0 walkthroughs](tutorials-1.3.0.md) and their PowerPoint/HTML
files retain their original instructions and evidence. This draft stages the
changed GUI procedures for a later canonical and derivative review. Control
names are bold; typed values and commands use code font.

## Approval wording in current unreleased source

The current source uses **Approve this work request** and **Keep as draft** in
**Review your answers**. Click **Approve this work request** only to record
approval of the reviewed request. Click **Keep as draft** to leave it unapproved
for reconsideration. Each choice explains its consequence; neither starts work.
These are presentation labels for the existing single-use intent decisions,
not new execution controls. Human comprehension with this wording has not yet
been checked.

The #243 procedures and retained captures below still use the earlier labels
**Accept this intent** and **Keep draft for reconsideration**. They remain
evidence for that pinned build; they do not verify the changed copy. The
published 1.3.0 tutorial and its derivative files retain their released labels.

## Navigation: how can I inspect what I accepted?

Prerequisite: Use the installed #243 candidate and prepare a fresh synthetic
draft as described below. It starts with an unanswered goal and success
criterion. `TASK` is the returned canonical task directory.

| Step | Action |
| --- | --- |
| 1 | Click **Continue form**. In “**What should this work accomplish?**”, enter `Group saved work by the decision it needs`. |
| 2 | Click **Save answers**, leaving the success question empty. Wait for the “Answers saved” confirmation. |
| 3 | Reopen the same task after a listener restart, using the command below. Expand **View saved request** and check the goal and allowed files. Click **Continue form**. |
| 4 | In “**What observable result establishes success? Enter one item per line.**”, enter `Each saved task shows its next decision`. Click **Save answers** and wait for the saved confirmation. |
| 5 | Click **Review your answers**. Check the goal, success criterion, allowed files, context and constraints. If those answers are correct, click **Accept this intent**. |
| 6 | Reload the page. Expand **View accepted request** and compare the retained answers with the request you accepted. |

Expected: **Saved work** shows “Intent accepted”. **View accepted request**
retains the goal, success criterion, `source.py`, `Training example` and
`No implementation or model calls`. The captured fixture has saved revision 3.
Inspection opens no new approval form and starts no implementation or model call.

For an explanation of prompt structure, expand **How this becomes a prompt**.
Its XML is illustrative; answer the actual questions in ordinary language.
**Technical details** contains the task identity, checkpoint and authoring
format and remains optional.

This is the captured partial-save variation: it uses two saves and a restart.
The retained 1.3.0 Navigation procedure enters both answers before its single
save. Keep the action sequence and its matching captures together.

## Session continuity: what survives reopening the form?

Prerequisite: Prepare another fresh synthetic draft with the same candidate.
This procedure ends while the request is still a draft.

| Step | Action |
| --- | --- |
| 1 | Click **Continue form**. |
| 2 | In “**What should this work accomplish?**”, enter `Group saved work by the decision it needs`. |
| 3 | Click **Save answers**. Leave the success question empty and wait for the “Answers saved” confirmation. |
| 4 | Stop the listener with `Ctrl-C`. Run `python -m attune_harness.gui --task "$TASK" --edit --launch-json` and open the new private `launch_url`. |
| 5 | Expand **View saved request**. Check the retained goal, `source.py`, context and constraint. |
| 6 | Click **Continue form** to answer what remains. |

Expected: **Saved answers** retains the goal above the unanswered success
question. The task remains a draft. The new form session expires the earlier
collector; saved answers remain in the owner record.

The candidate example uses the shared Navigation fixture. The retained 1.3.0
Continuity example uses `Review quartz retention documentation`. Its original
captures remain with that version. The candidate's reopened saved-request image
supports step 5. A separate local walkthrough check also captures the retained
goal beside the fresh unanswered success field at step 6. Both use #243 alone;
repeat that capture on the combined candidate before derivative publication.

Saved answers are the observed result. Unsaved typing is not guaranteed to
survive closing the tab. Copy needed unsaved text before closing it.

## What if the saved inputs changed?

The candidate shows “Accepted intent — inputs changed” and a warning before
the closed **View accepted request** disclosure. Opening it retains the earlier
answers for inspection. That acceptance is historical; it does not establish
authority over the changed inputs.

This walkthrough ends at inspection. The GUI owner's real-task trial still
needs to establish whether the warning and next permitted action are clear to
a user. No new recovery button or automatic retry is described here.

## Prepare and reopen the synthetic sample

Use one installed candidate interpreter throughout. Set `CANDIDATE` to an
absolute checkout of #243 at the pinned commit, and choose an unused absolute
`TRAINING` directory for each procedure. The helper creates the sample project,
deterministic registry and saved draft; the task remains outside the project.

```sh
CANDIDATE="/absolute/path/to/candidate-checkout"
TRAINING="/absolute/unused/training-form"
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
own newly prepared draft.

The installed sample wheel retains metadata version 1.3.0 despite containing
unreleased source. A version string alone does not identify this candidate;
use the source and wheel provenance below. The fixture scopes `source.py`,
retains `Training example` and `No implementation or model calls`, and grants
no implementation or provider dispatch.

## Review all four training topics before the combined release

| Topic | Current disposition | Remaining candidate review |
| --- | --- | --- |
| Navigation | Changed candidate procedure staged above; exact sample literals match the retained canonical source. | Include #242, repeat the actual sequence on the selected combined source and use matching captures. |
| Session continuity | Changed candidate disclosure and shared fixture staged above; retained 1.3.0 example remains separate. | Confirm the draft endpoint and capture the fresh unanswered success field on the combined source. |
| [Specification workflow](tutorials-1.3.0.md#specification-workflow-preview-and-acceptance) | Retained 1.3.0 CLI instructions and receipts; no changed procedure claimed by this draft. | Review/replay the exact fixture on the selected candidate before marking it unchanged-but-reviewed. |
| [Four workflows research](tutorials-1.3.0.md#four-workflows-research-a-question) | Retained 1.3.0 retrieve/verify instructions and receipts; no changed procedure claimed by this draft. | Review/replay the exact fixture and preserve the link-validity/semantic-check limits. |

After the integrated source and version are explicit, refresh canonical
procedures, PowerPoint/HTML derivatives and the Help projection together.
Record tested source/version, examples, visible results, checked links and
retained versus superseded guidance through the existing release checklist.
The historical released local-workflow guide's dev0/old-extra/future-forms
wording remains a recorded discrepancy, not current installation guidance.

## Source and evidence

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
