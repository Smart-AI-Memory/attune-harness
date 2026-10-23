# Four training walkthroughs for Harness 1.5.1

**Preparation — unpublished.** Practice saving and approving a request,
accepting a sample plan, retrieving local evidence and returning to saved
answers. Use disposable fixtures; intent acceptance does not execute work.

The [installation guide](installation.md) distinguishes local candidate
validation from installation after publication. Earlier
[1.5.0 candidate procedures](tutorials-1.5.0-candidate.md),
[1.4.0 written preparation](tutorials-next-release-candidate.md) and
[1.3.0 walkthroughs](tutorials-1.3.0.md) retain their original artifacts and
observations. Existing older class decks and HTML examples remain historical;
this page does not claim that they were refreshed or requalified for 1.5.1.

## Choose a walkthrough

| If you want to... | Open this walkthrough | You will practice... |
| --- | --- | --- |
| Save and approve a work request | [Navigation: an accepted intent](#navigation-an-accepted-intent) | Review the whole request, approve it and confirm it remains readable after a reload. |
| Preview and accept a sample plan | [Specification workflow: preview and acceptance](#specification-workflow-preview-and-acceptance) | Inspect a plan checkpoint and accept it without starting a build. |
| Research a question with local files | [Four workflows: research a question](#four-workflows-research-a-question) | Retrieve two sources and verify a link without a model call. |
| Continue a saved draft | [Session continuity: saved answers in another session](#session-continuity-saved-answers-in-another-session) | Reopen saved answers after reconnecting; no work resumes automatically. |

## Selected runtime and examples

Use the installed interpreter from a reviewed 1.5.1 candidate wheel. This page is
preparation; 1.5.1 is not published. The local validation described below uses
current-main runtime bytes with only package-version metadata changed to 1.5.1.
It is not the final release artifact.

Set `R` to the absolute checkout matching that wheel's source. Examples come
from the repository, not the wheel. Run in a new practice directory outside
that checkout. Keep each task directory outside its sample project. Activate
the installed candidate environment and select its interpreter:

```sh
PY="$(python -c 'import sys; print(sys.executable)')"
python -c "from importlib.metadata import version; print(version('attune-harness'))"
```

Expect `1.5.1`. Use that environment's `attune-harness` executable throughout.
Version alone is not source identity: retain the wheel hash and compare its
runtime modules with the selected source. These command examples use POSIX
shell syntax; Windows shell adaptation is not newly qualified.

## Navigation: an accepted intent

Deck title: **Start and continue work**.

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
[Trainer setup for the two form walkthroughs](#trainer-setup-for-the-two-form-walkthroughs).

For an explanation of prompt structure, expand **How this becomes a prompt**.
Its XML is illustrative; answer the actual questions in ordinary language.
**Technical details** contains task identity, checkpoint and authoring format
and remains optional.


## Specification workflow: preview and acceptance

<!-- walkthrough:spec-workflow -->
Title: How does a sample plan become accepted?

Prerequisite: the installed candidate described above. P = prepared Git checkout, T = new task outside P, R = candidate source checkout, PY = active Python.

**Before step 1:** Complete [Prepare the planning example](#prepare-the-planning-example), then return to the numbered actions.

| Step | Action |
| --- | --- |
| 1 | Run: `attune-harness init --for plan --goal "Repair addition" --project "$P" --scope calc.py --interpreter "$PY" --tests tests/test_calc.py --task-dir "$T"` |
| 2 | Run: `attune-harness plan --request "$T.work.json" --project "$P" --config "$R/examples/starter/participants.json" --task-dir "$T"`. Copy `checkpoint_digest` into `C`. |
| 3 | Inspect the preview. If its scope is correct, run: `attune-harness plan --task-dir "$T" --accept --checkpoint "$C"` |

Expected: JSON shows status “accepted”. calc.py still contains a - b.

Limit: Acceptance starts no build. The starter reviewer approves without judging.
<!-- /walkthrough -->

### Prepare the planning example

This uses the existing CLI to preview and accept a sample plan. Use a
fresh disposable Git checkout, not a working project. Activate the environment
with the installed candidate described above first. `examples/` comes from a repository checkout, not the
installed package. Set `R` to an absolute checkout path at the pinned candidate
source inputs. Set `P` and `T` to unused absolute paths, with `T` outside `P`. For
example, after setting `R`:

```sh
P="$PWD/training-plan-project"
T="$PWD/training-plan-task"
PY="$(python -c 'import sys; print(sys.executable)')"
mkdir -p "$P/tests"
printf 'def add(a, b):\n    return a - b\n' > "$P/calc.py"
printf 'from calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n' > "$P/tests/test_calc.py"
git init "$P"
git -C "$P" add calc.py tests/test_calc.py
git -C "$P" commit -m "Training fixture"
```

These commands prepare the fixture only. Return to the
[workflow table](#specification-workflow-preview-and-acceptance) and run steps
1–3 once. In step 2, set `C` to the full returned `checkpoint_digest`; it changes
with your task, so use that task's value.

After that single execution, step 1 returns `created` and writes `$T.work.json`
beside the task directory. Step 2 returns `draft` with no missing questions for
this fixture. Step 3 returns `accepted`. Confirm the accepted result with:

```sh
attune-harness status "$T"
```

This process stops before `build`. It exercises request creation and the
checkpoint-bound acceptance decision. It does not prove that a plan is good or
that an independent reviewer judged it. For real participants and build
authority, read [Plan and build](cli-guide.md#plan-and-build).

## Four workflows: research a question

<!-- walkthrough:four-workflows -->
Title: What can you check in a local source?

Prerequisite: The installed candidate includes rag and verify. E = a fresh copy of its local-workflow example directory.

**Before step 1:** Complete [Prepare the research example](#prepare-the-research-example), then return to the numbered actions.

| Step | Action |
| --- | --- |
| 1 | Run: `attune-harness retrieve "quartz retention policy" --corpus "$E/project" --output "$E/retrieval-report.json"` |
| 2 | Read retrieval-report.json, then project/reference.md. Inspect both returned sources. |
| 3 | Run: `attune-harness verify "$E/project/guide.md" --context "$E/context.json" --output "$E/verification-report.json"` |
| 4 | Read verification-report.json. Check `status`, `passed`, `result.coverage` and `result.semantic_ran`. |

Expected: Two matching sources. Verification shows “verified”, passed true and one link claim.

Limit: `result.semantic_ran` is false. This example establishes link validity, not policy correctness.
<!-- /walkthrough -->

### Prepare the research example

Use `R` and the installed environment from [Selected runtime and examples](#selected-runtime-and-examples). Copy the candidate example into
a new directory outside that checkout. Set `E` to the absolute copy path:

```sh
E="$PWD/training-research"
cp -R "$R/examples/local-workflow" "$E"
```

Use a fresh copy so report output paths do not replace prior evidence. The
query matches `guide.md` and `reference.md`; each result carries an excerpt
and a source hash. The verification result has `result.coverage.total: 1` and
`result.coverage.verified: 1`. Its claim kind is `links`, subject `reference.md`, at
line 3 of the guide. `result.semantic_ran: false` rules out a semantic policy verdict.
This offline sample makes no model calls. The tutorial's later concepts also
cover picking an opportunity, scoped repair and resuming saved work. Read
[Local verification and retrieval](local-workflow.md) for dependency and input
limits.

## Session continuity: saved answers in another session

Prerequisite: Prepare another fresh synthetic draft with the installed candidate described above.
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

The candidate observations below include installed-source captures of the
saved/remaining layout, same-page reload and fresh-listener reopening. Earlier
1.4.0 human observations retain their original source identity. Copied-tab,
history, exact Tab order and other native ownership transitions remain separate
and unobserved in this walkthrough. Released 1.3.0 does not include this reload
restoration.

## Trainer setup for the two form walkthroughs

Use a fresh unused absolute directory for each form walkthrough. `PY` is the
absolute installed-environment interpreter selected above. `R` is the exact
candidate source checkout. Prepare the sample with the existing helper:

```sh
FORM='/absolute/unused/training-navigation'
"$PY" "$R/examples/browser-intake/prepare.py" "$FORM"
TASK="$FORM/saved-task"
"$PY" -m attune_harness.gui --task "$TASK" --edit --launch-json
```

Keep the listener running. Open its complete private `launch_url`; do not put
that URL in public evidence. The sample leaves goal and success unanswered and
includes `source.py`, `Training example` and `No implementation or model calls`.
The helper refuses an existing directory. It does not create a real user task,
accept intent or dispatch a model. For Continuity, use another unused absolute
path and prepare a separate task before running its steps:

```sh
FORM='/absolute/unused/training-continuity'
"$PY" "$R/examples/browser-intake/prepare.py" "$FORM"
TASK="$FORM/saved-task"
"$PY" -m attune_harness.gui --task "$TASK" --edit --launch-json
```

The planning fixture and its three CLI actions are retained above for POSIX
shells. Their Windows PowerShell and PowerShell 7 equivalents require actual
installed-release observation before inclusion. Do not paste POSIX variable,
copy or quoting syntax into PowerShell. No new Windows command is claimed here.

## Verification and release boundary

Reviewed October 22, 2026 against runtime source
`0f2711b4c88ee4f231f61d71cd70a0c840be6357` on macOS arm64/Python 3.10.11.
A fresh noneditable local wheel, with only package metadata changed from 1.5.0
to 1.5.1, has SHA-256
`def6ab630dd677a346cc5ed728ee880a38927bf2e3142272071f96b168decc71`.
All 108 installed runtime modules match that source, and the 96 installed
packages pass dependency compatibility checks. This is a documentation
validation artifact, not an accepted final release candidate.

Observed outcomes:

- Navigation saved both literal answers, recorded intent acceptance and retained
  a read-only accepted request after reload. No editable fields remained.
- Planning returned `created`, `draft`, then `accepted`; `calc.py` was unchanged
  and no build was run. The sample reviewer supplies no substantive judgment.
- Retrieval found the two local Markdown sources. Verification returned
  `verified`, `passed: true`, one verified link and `result.semantic_ran: false`.
  This establishes the sample link, not policy correctness.
- Continuity retained the literal goal after same-page reload and a fresh
  listener, left the remaining success answer blank and stayed unaccepted.
  Unsaved typing was discarded after reload.

Browser checks used the in-app browser on the same Mac and the installed wheel.
Both form cases had no execution state. The walkthroughs made no model calls.
Separately, 222 documentation-link, printed-command, assessment-report and
signature checks passed against the installed wheel. Completed-assessment
Markdown and HTML inspections preserved saved-file hashes and kept semantic
acceptance unverified.

These observations do not establish independent user comprehension, complete
accessibility, another browser, native Windows shell or desktop journeys, live
provider quality, full storage durability or arbitrary-descendant recovery.
Native planning/building remain experimental and full Windows parity remains
deferred. Do not generalize hosted Server checks to those claims.

Before publication, reconcile the selected final source, versioned artifacts,
required qualification and current documentation. Recheck affected procedures
if their inputs or behavior change. Published-byte and index-install checks
follow package publication; they do not replace candidate validation. Release,
website deployment and any live participant work retain their own approvals.
