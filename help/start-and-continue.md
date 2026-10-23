## Before you begin

Complete [Get started](/harness/help/get-started/) in a fresh working directory.
Keep the selected 1.5.1 validation environment active. `R` is the absolute preparation checkout
at commit `7caa86ab6d476e9599b08ff75a81bc816e60c382`; its example files are not in the wheel.
These examples use a POSIX shell and canonical paths. On macOS, use
`/private/tmp` instead of the `/tmp` symlink. Choose unused practice directories.
Windows desktop and shell journeys remain unqualified.

## Prepare and open the practice form

Run this setup before the browser steps. The helper refuses an existing directory,
creates a synthetic draft and makes no model calls:

```sh
PY="$(python -c 'import sys; print(sys.executable)')"
FORM="$PWD/training-navigation"
"$PY" "$R/examples/browser-intake/prepare.py" "$FORM"
TASK="$FORM/saved-task"
"$PY" -m attune_harness.gui --task "$TASK" --edit --launch-json
```

Keep the listener running. Open its complete private `launch_url` in one tab.
The launch reports `editable: true` and `execution_enabled: false`. Keep the URL
out of public reports. The sample contains `source.py`, `Training example` and
`No implementation or model calls`; its goal and success criterion start empty.
The helper prepares a practice task rather than accepting intent or executing work.

## Save, review and approve the request

Use the practice form opened above. If it already shows **Intent accepted**, go to step 8.

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



**Expected result:** The request is accepted; **View accepted request** preserves the two answers after reload and contains no editable answer fields.

**Limit:** No build or execution is started. For real work, prepare a new draft with your actual scope and checks.

## Verification and sources

For 1.5.1 preparation, compare the procedure with the [reviewed source](https://github.com/Smart-AI-Memory/attune-harness/blob/0f2711b4c88ee4f231f61d71cd70a0c840be6357/docs/cli-guide.md) and [preparation record](/harness/help/preparation.json). The final selected artifact still requires replay; the older observations below retain their original identity.

The [current verification record](/harness/help/verification.json) distinguishes fresh published-1.5.0 observations
from the retained [candidate walkthrough evidence](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/tutorials-1.5.0-candidate.md).
The [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md) supplies the change sequence;
[released CLI guidance](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md) and released UI source
supply the command and label baseline. Historical 1.3.0 observations remain
historical. These synthetic examples do not qualify Windows, all browser
ownership transitions, assistive technology, real participant quality or paid
providers. Approval and execution require separate decisions.
