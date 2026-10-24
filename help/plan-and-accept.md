## Before you begin

Complete [Get started](/harness/help/get-started/) in a fresh working directory.
Keep the published 1.5.1 environment active. `R` is the absolute release checkout
at commit `ebb5b03b8a4398325df7ddabd28c08186451452e`, as set in Get started; its example files are not in the wheel.
These examples use a POSIX shell and canonical paths. On macOS, use
`/private/tmp` instead of the `/tmp` symlink. Choose unused practice directories.
Windows desktop and shell journeys remain unqualified.

## Prepare the sample checkout

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

## Preview and accept the plan

### 1. Create the request

```sh
attune-harness init --for plan --goal "Repair addition" --project "$P" --scope calc.py --interpreter "$PY" --tests tests/test_calc.py --task-dir "$T"
```

Expected: `created`; the request is written as `$T.work.json` beside the task directory.

### 2. Preview that request

```sh
attune-harness plan --request "$T.work.json" --project "$P" --config "$R/examples/starter/participants.json" --task-dir "$T"
```

Expected: `draft` with no missing questions. Inspect its goal, allowed file,
effects and acceptance criteria. Set `C` to its full `checkpoint_digest`, for
example `C='the-full-returned-digest'`; replace that literal with this preview's value.

### 3. If that exact scope is correct, accept its current checkpoint

```sh
attune-harness plan --task-dir "$T" --accept --checkpoint "$C"
attune-harness status "$T"
```

**Expected result:** Status is `accepted`. `calc.py` still contains `a - b` and
there is no build run. Acceptance records the reviewed scope only.

**Limit:** This example stops before **`build`**. The starter reviewer approves
without substantive judgment. A real build needs appropriate participants,
frozen effects, protected checks and separately authorized execution. See
[Plan and build](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/docs/cli-guide.md#plan-and-build).

## Verification and sources

Published 1.5.1 uses release commit `ebb5b03b8a4398325df7ddabd28c08186451452e`. Read its [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/docs/cli-guide.md) and [release record](/harness/help/release-1.5.1.json) for source, artifact and check identities. The [historical preparation record](/harness/help/preparation.json) retains its original candidate boundary. The older observations below are 1.5.0 evidence; they are not new 1.5.1 walkthrough results.

The [historical 1.5.0 verification record](/harness/help/verification.json) distinguishes fresh published-1.5.0 observations
from the retained [candidate walkthrough evidence](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/tutorials-1.5.0-candidate.md).
The [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md) supplies the change sequence;
[released CLI guidance](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md) and released UI source
supply the command and label baseline. Historical 1.3.0 observations remain
historical. These synthetic examples do not qualify Windows, all browser
ownership transitions, assistive technology, real participant quality or paid
providers. Approval and execution require separate decisions.
