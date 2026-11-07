## Match the practice environment to its evidence

These walkthroughs use a rehearsal wheel built before Harness 1.7.0 was
published. For a new installation, [get started with the published
release](/harness/help/get-started/). The four older practice pages retain their
[isolated 1.5.1 setup](/harness/help/get-started/#prepare-the-151-practice-examples)
and original observations.

This preparation uses the reviewed software checkpoint
`9ecefe8a0fded05b1bb55b2f81d8579725666666` and the wheel from
[build-only rehearsal 41961339343](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/41961339343).
Its wheel SHA-256 is
`57223f23037014a0c134956375aa8088ca586e9816e0c7a1c7b8161c5eb3916a`.
The rehearsal did not publish a package. New documentation changes and later
rebuilt artifacts need their own qualification.

Use a fresh POSIX shell and unused practice directory. Select the absolute path
to that downloaded wheel below. You need Git and Python 3.12 or later; the
recorded local checks use macOS arm64 / CPython 3.12.2. That observation does not
qualify every desktop, shell or browser. On macOS, use canonical paths such as
`/private/tmp`, rather than the `/tmp` symlink.

```sh
WHEEL='/absolute/path/to/attune_harness-1.7.0-py3-none-any.whl'
python3.12 -c "import hashlib, pathlib, sys; assert hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() == '57223f23037014a0c134956375aa8088ca586e9816e0c7a1c7b8161c5eb3916a'" "$WHEEL"
PRACTICE="$PWD/harness-1.7.0-practice"
mkdir "$PRACTICE"
cd "$PRACTICE"
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install "$WHEEL"
git clone --no-checkout https://github.com/Smart-AI-Memory/attune-harness.git release-source
R="$(cd release-source && pwd -P)"
git -C "$R" checkout --detach 9ecefe8a0fded05b1bb55b2f81d8579725666666
python -c "from importlib.metadata import version; assert version('attune-harness') == '1.7.0'; print(version('attune-harness'))"
python -m attune_harness
```

**Expected result:** Version `1.7.0` and a verified deterministic demonstration.
`R` is the matching source checkout, which supplies examples absent from the
wheel. Keep this shell open. Tasks and sample projects belong beside
`release-source`, outside that checkout. Choose each workflow below in its own
unused directory; no workflow here starts implementation or a model call.

## Start and continue work

This synthetic form practices saving and accepting a request. Its constraint
is `No implementation or model calls`. Acceptance records only the reviewed
request; it does not grant execution.

### Prepare and open the practice form

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

### Save, review and approve the request

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
   To leave the request unapproved, choose **Keep as draft** and stop this
   practice with an unapproved draft. Continue to step 8 only after approval.

8. Verify the accepted request.
   Reload the tab and inspect **View accepted request**, which opens expanded.
   If you have collapsed it, expand it again. Both answers should remain visible,
   with no editable answer fields. This completes the practice.



**Expected result:** The request is accepted; **View accepted request** preserves the two answers after reload and contains no editable answer fields.

**Limit:** No build or execution is started. For real work, prepare a new draft with your actual scope and checks.


## Preview and accept a plan

This workflow ends at acceptance. Git must be able to create a local fixture
commit with your configured author identity.

### Prepare the sample checkout

Use a disposable Git checkout with a deliberately incorrect `add` function. The
following setup defines all variables before the planning commands use them:

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

`P` is the sample project; `T` is the unused task directory outside it. Do not
put new files inside `P` after the next step freezes its inputs.

### Preview and accept the plan

#### 1. Create the request

```sh
attune-harness init --for plan --goal "Repair addition" --project "$P" --scope calc.py --interpreter "$PY" --tests tests/test_calc.py --task-dir "$T"
```

Expected: `created`; the request is written as `$T.work.json` beside the task directory.

#### 2. Preview that request

```sh
attune-harness plan --request "$T.work.json" --project "$P" --config "$R/examples/starter/participants.json" --task-dir "$T"
```

Expected: `draft` with no missing questions. Inspect its goal, allowed file,
effects and acceptance criteria. Set `C` to its full `checkpoint_digest`, for
example `C='the-full-returned-digest'`; replace that literal with this preview's value.

#### 3. If that exact scope is correct, accept its current checkpoint

```sh
attune-harness plan --task-dir "$T" --accept --checkpoint "$C"
attune-harness status "$T"
```

**Expected result:** Status is `accepted`. `calc.py` still contains `a - b` and
there is no build run. Acceptance records the reviewed scope only.

**Limit:** This example stops before **`build`**. The starter reviewer approves
without substantive judgment. A real build needs appropriate participants,
frozen effects, protected checks and separately authorized execution. See
[Plan and build](https://github.com/Smart-AI-Memory/attune-harness/blob/9ecefe8a0fded05b1bb55b2f81d8579725666666/docs/cli-guide.md#plan-and-build).


## Research a local question

### Prepare the local corpus

Copy the example from the release checkout before retrieving or writing reports:

```sh
E="$PWD/training-research"
cp -R "$R/examples/local-workflow" "$E"
```

Choose an unused `E` directory outside the release checkout. The base install
includes local retrieval and verification. A fresh copy protects prior reports.

### Retrieve sources and verify a link

#### 1. Retrieve local evidence

```sh
attune-harness retrieve "quartz retention policy" --corpus "$E/project" --output "$E/retrieval-report.json"
```

#### 2. Inspect the sources

Read `retrieval-report.json`, then `project/reference.md`. Inspect both
returned sources, `guide.md` and `reference.md`, including excerpts and hashes.

#### 3. Check the supported link claim

```sh
attune-harness verify "$E/project/guide.md" --context "$E/context.json" --output "$E/verification-report.json"
```

#### 4. Inspect verification

Read `verification-report.json`. Check `status`, `passed`, `result.coverage`
and `result.semantic_ran`.

**Expected result:** Retrieval returns two Markdown sources. Verification returns
`verified`, `passed: true`, `result.coverage.total: 1` and
`result.coverage.verified: 1`. The `links` claim refers to `reference.md` at line
3 of the sample guide.

**Limit:** `result.semantic_ran` is false. This checks link validity; it does not
establish policy correctness. The example is local and makes no model or Voyage
call. Choose and authorize paid retrieval separately when a real task needs it.


## Save and return to a draft

Use a new fixture for this workflow, even if you completed the acceptance
practice above.

### Prepare and open the practice form

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

### Continue a saved draft

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


### Inspect before continuing execution

Saving answers records intake; approving intent records a scope decision.
Neither starts work. Browser forms cannot dispatch builds or resume execution.

1. In another terminal, activate the same environment and set `TASK` to the same absolute saved-task directory.
2. Run `attune-harness status "$TASK" --format markdown` and read its state, evidence and next action.
3. If an execution task is eligible and you have its current authority, follow the stated CLI **`resume`** route with its required checkpoint and grants. This practice draft is still incomplete; do not execute it.

**Expected result:** Inspection describes the saved draft without running work.
**Limit:** Restarting a form listener reopens intake; it is different from execution resume. External/native execution can have effects and consume usage.

For a `feature-work-v1` task, the [pause-and-return procedure](https://github.com/Smart-AI-Memory/attune-harness/blob/9ecefe8a0fded05b1bb55b2f81d8579725666666/docs/cli-guide.md#pause-and-return-to-work) shows how to inspect the current task and write a read-only HTML briefing with a caller-owned continuation note. It does not resume execution or restore an old browser form. Read its task/revision and path requirements before using it.

Explicit [CLI saved memory](https://github.com/Smart-AI-Memory/attune-harness/blob/9ecefe8a0fded05b1bb55b2f81d8579725666666/docs/memory-saving.md) is a separate store from browser form answers.


## Read the results and remaining limits

These are synthetic software walkthroughs with local evidence. Successful link
verification is not semantic policy approval, and a browser automation pass is
not an independent-user comprehension or accessibility observation. Keep actual
runtime, browser, commands, actions and outcomes with each receipt. An
interrupted or unconfirmed action stays uncertain until its saved state can be
inspected; do not submit it again blindly.

The original 1.5.1 and older walkthroughs, goal screenshots and delivered decks
retain their original source/version labels. This draft is proposed written
material for the four training topics, not an approved replacement for those
decks or proof of their visual accuracy. Website import, release-record updates
and deployment remain separate review decisions; the live website has not been
verified by this walkthrough.

Read the [1.7.0 readiness record](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/release-readiness-1.7.0.md)
for the exact-main qualification, retained failed native-memory combination,
Windows payload and incomplete-coverage limits, and publication gates. The
[release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/release-notes-1.7.0.md)
retain legacy command environments through 1.7.0, with removal no earlier than
1.8.0. API/plan funding has offline software evidence; account eligibility,
native Keychain interoperability, quota and billing remain unestablished.
Hydration is groundwork; keep existing writers and host hooks. No step here
authorizes a paid provider call, build, execution resume or publication.
