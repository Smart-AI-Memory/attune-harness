# Four training walkthroughs for the unpublished Harness 1.5.0 candidate

**PROVISIONAL REVIEW CANDIDATE.** The selected installed local 1.5.0 wheel
has SHA-256
`17823fbd7037ce26e9de6108a8db9680956ee2b7a20224bc490173ccb5e0bd6d`.
Its runtime source is byte-identical to main baseline
`18e9f2894e0c0e6ac0d18dda2c65615648f1dcc7`; the review proposal adds only
documentation changes. Its source commit was null at build time. Build-time
source archive
`b0d9d2ca6e88ae10e3ec63ead65eabe0b3577b2aba9d2e8f0ecde914f459e2cb`
and exact input hashes retain that proposal.

All 107 installed runtime modules and the resolved dependency versions match
the retained wheel859 environment. The new wheel changes the README description
and build-generator metadata; it retains the same package metadata headers,
dependency requirements and wheel tags. A fresh noneditable installation and
`pip check` passed. Final source integration, artifact qualification and content review are
separate requirements.

The four procedure outcomes below were observed on retained wheel
`859120544a5040532f06a19eab02996377afc0f73b05f7d0b19829378249b586`
on macOS arm64/Python 3.12.2. Their original uncommitted source/archive
`f38205a1bdb15c4890d8e7c08d633a5f1353a369c868d0b78900e8d2614a157e`
and later f9/main bindings remain historical evidence. This review reuses those
unchanged procedures and records exact runtime/example/dependency equivalence;
it does not relabel their executions as new observations on a different wheel.
Full Windows parity is deferred and remains unqualified. Publication stays held.

Practice saving and approving a request, accepting a sample plan, checking local
evidence, and continuing saved answers. Browser approval records the reviewed
request. Starting work requires separate authority. Use disposable examples.

The [1.3.0 walkthroughs](tutorials-1.3.0.md) and
[written 1.4.0 interim guide](tutorials-next-release-candidate.md) retain their
original version and evidence. Use this revision only for the explicitly identified review candidate and
its stated evidence limits. Final release reconciliation remains
required before publication.

## Choose a walkthrough

| If you want to... | Open this walkthrough | You will practice... |
| --- | --- | --- |
| Save and approve a work request | [Navigation: an accepted intent](#navigation-an-accepted-intent) | Review the whole request, approve it and confirm it remains readable after a reload. |
| Preview and accept a sample plan | [Specification workflow: preview and acceptance](#specification-workflow-preview-and-acceptance) | Inspect a plan checkpoint and accept it without starting a build. |
| Research a question with local files | [Four workflows: research a question](#four-workflows-research-a-question) | Retrieve two sources and verify a link without a model call. |
| Continue a saved draft | [Session continuity: saved answers in another session](#session-continuity-saved-answers-in-another-session) | Reopen saved answers after reconnecting; no work resumes automatically. |

## Selected runtime and examples

Use the installed interpreter from the selected candidate wheel. Confirm that
its source modules match the frozen source inputs above and use that environment's
`attune-harness` executable throughout. Do not treat the version string alone
as source identity. No published 1.5.0 install command is supplied.

Set `R` to the absolute checkout of the pinned source inputs described above. The examples
come from the repository, not the wheel. Run outside that checkout. Keep
practice task directories outside their sample projects. Activate the selected
candidate environment, then set its interpreter for the examples:

```sh
PY="$(python -c 'import sys; print(sys.executable)')"
```

Use the `attune-harness` executable from that same active environment. The
command setup below uses a POSIX shell. Windows shell adaptation remains
untested here.

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

The retained wheel859 walkthroughs reproduced all four procedures on macOS
arm64/Python 3.12.2. Their 107 installed modules and 1,008 frozen source inputs
matched their recorded original bindings. The selected replacement wheel178
has identical runtime modules, example inputs and dependency versions; its
changed description/build metadata has a separate exact artifact binding. Navigation ended accepted,
retained both literal answers after an actual same-page reload, and exposed a
read-only accepted request. Continuity retained the exact saved goal across
same-page reload and a fresh listener, left success blank, and remained a draft.
Unsaved typing disappeared on reload. Neither created planning or build state.

Planning returned `created`, `draft`, then `accepted`, left `calc.py` unchanged,
and created no build state. Retrieval returned two Markdown sources with matching
hashes. Verification returned `verified`, `passed: true`, one verified link,
and `result.semantic_ran: false`. It does not judge the sample policy's truth.
The synthetic examples made no model calls. The starter reviewer approves
without substantive judgment.

Browser evidence uses isolated headless Chromium 147.0.7727.15. Each successful
walkthrough retained one page through its reloads. The first CLI report-reader
looked at the wrong envelope field after nine successful commands; its original
output remains retained and the documented `result` fields were checked without
repeating those commands. Earlier browser-harness connection/tab attempts also
remain retained separately. They do not establish product failures or completed
same-page checks. The successful continuous-page run supplies those observations.

The retained wheel859 local full source suite and installed qualifier passed separately:
5,057 full-source passes, 237 skips and seven passing subtests; 2,826 installed
selection passes, 193 skips and two passing subtests. The qualifier's additional
R2, Redis-without-server and ten plugin steps passed, with zero model calls.
Those completed suites were not repeated for this documentation review.

These checks establish the listed sample outcomes. They do not establish
independent user comprehension, exact Tab order, assistive-technology support,
400% zoom, real-provider quality or native Windows qualification. Broader saved
memory, process completion and execution-resume examples retain their separate
evidence and authority boundaries. Older 1.4.0 screenshots or observations remain
historical and must be labelled with their original provenance when reused.

Full Windows parity is deferred from the 1.5.0 release claim. The strict
arbitrary-descendant stop requirement remains unchanged and unqualified.
Full storage acceptance, live native-memory acceptance, Windows 11
standard-user desktop journeys, Windows PowerShell and PowerShell 7 journeys
retain their separate open evidence needs. Hosted Server passes do not close
those requirements.

Before publication, bind the final selected source, installed wheel, examples,
dependencies, packaged metadata and these review materials. Recheck affected
inputs and close the candidate review; preserve unchanged earlier evidence.
Final source integration and publication approval remain separate gates.
After Patrick separately approves publication, verify the actual GitHub
tag/release and live PyPI file hashes against the publishing evidence and
confirm the installed published bytes. All assets remain provisional until
their final-source and publication gates.
