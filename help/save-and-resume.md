## Before you begin

Complete [Get started](/harness/help/get-started/) in a fresh working directory.
Keep its published 1.5.0 environment active. `R` is the absolute release checkout
at commit `7caa86ab6d476e9599b08ff75a81bc816e60c382`; its example files are not in the wheel.
These examples use a POSIX shell and canonical paths. On macOS, use
`/private/tmp` instead of the `/tmp` symlink. Choose unused practice directories.
Windows desktop and shell journeys remain unqualified.

## Prepare and open the practice form

Run this setup before the browser steps. The helper refuses an existing directory,
creates a synthetic draft and makes no model calls:

```sh
PY="$(python -c 'import sys; print(sys.executable)')"
FORM="$PWD/training-continuity"
"$PY" "$R/examples/browser-intake/prepare.py" "$FORM"
TASK="$FORM/saved-task"
"$PY" -m attune_harness.gui --task "$TASK" --edit --launch-json
```

Keep the listener running. Open its complete private `launch_url` in one tab.
The launch reports `editable: true` and `execution_enabled: false`. Keep the URL
out of public reports. The sample contains `source.py`, `Training example` and
`No implementation or model calls`; its goal and success criterion start empty.
The helper prepares a practice task rather than accepting intent or executing work.

## Continue a saved draft

1. Open the new private `launch_url`. If the current form is not displayed, inspect saved state, then click **Continue form**.
2. In “**What should this work accomplish?**”, enter `Group saved work by the decision it needs`.
3. Click **Save answers**. Leave the success question empty and wait for the “Answers saved” confirmation and the remaining question.
4. Reload this same page. When its listener, task checkpoint, collector and browser view ownership remain current, **Saved goal:** and the blank remaining success question reappear without clicking **Continue form**. Check that **Still needed** separates the instructions from the saved answer, then type in the remaining field.
5. Stop the listener with `Ctrl-C`. Run `python -m attune_harness.gui --task "$TASK" --edit --launch-json` with the same `TASK`.
6. Open the new private `launch_url`. Inspect the saved goal and remaining blank success question. If the current form is not displayed, expand **View saved request**, then click **Continue form** to reopen deliberately.

**Expected result:** The saved goal retains its exact wording and the task remains a draft.
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


## Inspect before continuing execution

Saving answers records intake; approving intent records a scope decision.
Neither starts work. Browser forms cannot dispatch builds or resume execution.

1. In another terminal, activate the same environment and set `TASK` to the same absolute saved-task directory.
2. Run `attune-harness status "$TASK" --format markdown` and read its state, evidence and next action.
3. If an execution task is eligible and you have its current authority, follow the stated CLI **`resume`** route with its required checkpoint and grants. This practice draft is still incomplete; do not execute it.

**Expected result:** Inspection describes the saved draft without running work.
**Limit:** Restarting a form listener reopens intake; it is different from execution resume. External/native execution can have effects and consume usage.

Explicit [CLI saved memory](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/memory-saving.md) is a separate store from browser form answers.

## Verification and sources

The [current verification record](/harness/help/verification.json) distinguishes fresh published-1.5.0 observations
from the retained [candidate walkthrough evidence](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/tutorials-1.5.0-candidate.md).
The [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md) supplies the change sequence;
[released CLI guidance](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md) and released UI source
supply the command and label baseline. Historical 1.3.0 observations remain
historical. These synthetic examples do not qualify Windows, all browser
ownership transitions, assistive technology, real participant quality or paid
providers. Approval and execution require separate decisions.
