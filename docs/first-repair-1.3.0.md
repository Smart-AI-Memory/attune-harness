# Make your first checked repair with Harness 1.3.0

Correct a small addition bug, inspect the unchanged check, and continue after a
pause. This example uses two deterministic command participants. It makes no
model calls and needs no API key. The worker proposes a known replacement; the
example reviewer approves without judging. The passing test establishes only
the result it checks.

Use macOS or Linux, Python 3.12, Git and a shell such as bash or zsh. The repair
uses existing regular files in a disposable Git project. Windows repair and
linked Git worktrees are outside this example's qualified profile.

## 1. Install the named release in a fresh directory

Choose an unused directory outside your working projects:

```sh
mkdir harness-first-repair
cd harness-first-repair
FIRST_REPAIR_ROOT=$(pwd -P)
export FIRST_REPAIR_ROOT
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install 'attune-harness==1.3.0' 'pytest==9.1.1'
python -c "from importlib.metadata import version; print('Harness', version('attune-harness')); print('pytest', version('pytest'))"
```

Expect Harness `1.3.0` and pytest `9.1.1`. Keep this environment active. The
probe needs pytest in its selected interpreter; installing Harness alone does
not install pytest. Use `pwd -P` so the task path does not traverse a symlink,
such as `/tmp` on macOS.

Get the example participants from the released repository checkout:

```sh
git clone --branch v1.3.0 --depth 1 https://github.com/Smart-AI-Memory/attune-harness.git release-source
git -C release-source rev-parse HEAD
export FIRST_REPAIR_RELEASE="$FIRST_REPAIR_ROOT/release-source"
export FIRST_REPAIR_PROJECT="$FIRST_REPAIR_ROOT/project"
export FIRST_REPAIR_TASK="$FIRST_REPAIR_ROOT/repair-task"
export FIRST_REPAIR_PYTHON="$FIRST_REPAIR_ROOT/.venv/bin/python"
```

The commit must be `0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0`. Stop if it
differs. `examples/` comes from that checkout, not the installed wheel. New
main-branch features can share the same version string; this guide describes
the released source above, not an unspecified main build.

## 2. Prepare the disposable project

Save the following as `prepare.py` in `harness-first-repair`. It refuses to
replace an existing project and makes no Git commit:

<!-- journey: first-repair-prepare -->
```python
import os
from pathlib import Path
import subprocess

project = Path(os.environ['FIRST_REPAIR_PROJECT'])
project.mkdir()
(project / 'tests').mkdir()
(project / 'calc.py').write_text('def add(a, b):\n    return a - b\n', encoding='utf-8')
(project / 'tests/test_calc.py').write_text(
    'from calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n', encoding='utf-8')
subprocess.run(['git', 'init', '-q', str(project)], check=True)
```

Run `python prepare.py` from the active environment.

`calc.py` subtracts, so the test fails. Only `calc.py` may be replaced. The test
file is the protected oracle: changing it would invalidate this repair. The
environment, released examples and saved task are outside the project.

## 3. Initialize and preview the repair

<!-- journey: first-repair-preview -->
```sh
attune-harness init --for fix --project "$FIRST_REPAIR_PROJECT" --scope calc.py \
  --interpreter "$FIRST_REPAIR_PYTHON" --tests tests/test_calc.py
attune-harness fix --goal "Repair addition" --project "$FIRST_REPAIR_PROJECT" \
  --checkout "$FIRST_REPAIR_PROJECT" --scope calc.py \
  --probe "$FIRST_REPAIR_PROJECT/probe.json" \
  --config "$FIRST_REPAIR_RELEASE/examples/starter/participants.json" \
  --worker lead --reviewer reviewer --review required \
  --criteria "The frozen probe passes without changing its oracle" \
  --task-dir "$FIRST_REPAIR_TASK" --intake-only < /dev/null > "$FIRST_REPAIR_ROOT/preview.json"
```

`init` returns `created` and writes the probe; it does not run it. The second
command returns exit code **1** for a draft and saves its JSON in `preview.json`.
The source is unchanged and the saved task already exists.
The explicit closed stdin keeps this preview noninteractive so the saved output
is one JSON value rather than prompts mixed with results.

Open `preview.json`. Check the goal, `calc.py` scope, protected
`tests/test_calc.py`, probe interpreter and the `lead`/`reviewer` commands. Read
`release-source/examples/starter/worker.py`: these are offline examples, not
model agents. The worker proposes the replacement, Harness applies it within
the accepted scope, and the unchanged probe checks it. The example reviewer's
approval is not independent judgment.

## 4. Accept the current response and pause

If the preview is correct and you authorize those local participant/probe
commands, save the following as `accept-response.py` in `harness-first-repair`.
It creates a separate response file using the current task/form/checkpoint
bindings; it does not edit the saved task. External command permission is
explicit. Provider permission stays false for this offline example.

<!-- journey: first-repair-response -->
```python
import json
import os
from pathlib import Path

root = Path(os.environ['FIRST_REPAIR_ROOT'])
preview = json.loads((root / 'preview.json').read_text(encoding='utf-8'))
response = preview['submission']
response['accepted'] = True
response['permissions'] = {'external': True, 'provider': False}
with (root / 'accepted-response.json').open('x', encoding='utf-8') as output:
    json.dump(response, output, indent=2)
```

Run `python accept-response.py` in the active environment only after that
acceptance decision.

Submit that response to the existing draft:

<!-- journey: first-repair-continue -->
```sh
attune-harness fix --task-dir "$FIRST_REPAIR_TASK" \
  --task-response "$FIRST_REPAIR_ROOT/accepted-response.json" --pause-after 1
attune-harness status "$FIRST_REPAIR_TASK"
```

Expect exit code **1** and `paused` from the first command, then exit code **0**
and `paused` from inspection. The initial probe has failed; the replacement has
not run. Do not repeat the creation command with `--accept`: it would try to
create the already existing task. Do not add intake/config overrides to a
bound response or fabricate a checkpoint from another run.

## 5. Resume and inspect the checked result

<!-- journey: first-repair-result -->
```sh
attune-harness resume "$FIRST_REPAIR_TASK"
attune-harness status "$FIRST_REPAIR_TASK"
attune-harness resume "$FIRST_REPAIR_TASK"
```

Each command returns exit code **0** and `completed`. Repair resumes with the
saved permissions; do not add feature-work flags such as `--allow-external`.
Open `project/calc.py`: it now returns `a + b`. Read
`repair-task/record.json` without editing it. Under `execution`, compare
`before_probe` and `after_probe`: the same probe fails before and passes after.
The test oracle is unchanged. The integration result is
`verified_within_probe_scope`, with semantic verification false.

The last command replays the completed result. It retains the same event IDs
and attempt counts; it does not repeat completed work. `status` inspects saved
evidence without authorizing more work. Keep the task directory so you can
return to that evidence later.

## If a step stops

| Result | Next action |
| --- | --- |
| Wrong release commit/version, missing interpreter or pytest | Stop before acceptance. Check the active environment and selected probe interpreter against step 1. |
| Existing project, response file or task directory | Inspect what is there; choose a fresh example directory for a new run. Continue an existing draft only with its current bound response. |
| Stale response or changed inputs | Run `status` and inspect the saved evidence. Do not edit the record, copy a foreign digest or repeat approval on an accepted task. |
| Unknown effects or unresolved operation | Inspect the [recovery workflow](recovery-workflow.md) and reconcile with evidence. Do not retry blindly or start a replacement task to bypass uncertainty. |

This result demonstrates bounded proposal, application, checking, approval and
recovery. For a useful repair on your own project, choose a comparable failing
check and an appropriate dedicated checkout, then configure and assess real
participants through [Scoped repair](cli-guide.md#scoped-repair). Installing a
provider or accepting intent does not grant paid execution. Browser form
reopening is intake/inspection; it does not execute this CLI repair.
