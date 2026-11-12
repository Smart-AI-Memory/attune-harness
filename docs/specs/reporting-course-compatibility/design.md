# Reporting course compatibility design

**Status** — Approved by Patrick on November 11, 2026. See the [implementation tasks](tasks.md).

[Approved requirements](requirements.md) · [Command owner walk](README.md)

## First success

Get Started shows two commands in order.

```sh
uv tool install --python 3.12 attune-harness
attune-harness
```

Keep the uv prerequisite, Python 3.12 or later, and the expected
`"status": "verified"` beside the commands. A fresh install selects the
latest compatible release for the selected Python. Place assistant setup
after verification. Introduce Git, pytest, and example files in the practice
setup section on Get Started. Put version-specific changes
in the changelog and link to migration instructions when readers need to act.

## One maintained course

Use `training/reporting/` as the source for the six maintained lessons.
Serve its overview at `/harness/learn/reporting/`. Point the existing
`/harness/learn/` entry and the Help Center's course links to the practice
section on Get Started. From setup, continue to the overview. The previous
`reporting/setup.html` URL links to the same section. Update lesson prose and generator
labels where they currently name 1.7.0 as a requirement. Preserve the
exercises, protected tests and sample output.

Keep `training/1.7.0-preparation/` as a frozen archive. Its local tree
matches the [deployed source at `e1adfd7`](https://github.com/Smart-AI-Memory/attune-harness/tree/e1adfd7c5b7c838e2a35adf5a5773cd537de1bce/training/1.7.0-preparation),
including the dated receipt and the original sample download. Preserve its
public deep links and byte inventory.
The archive index identifies it as historical. The generator projects only
the maintained course and the archive index.

Preserve all six storage keys, section IDs, and note keys or field order.
Both routes use the same production origin. A reader opening the maintained
lesson resumes the same saved progress. Test a saved position without a
fragment and a direct link with a fragment separately.

## Practice setup and compatibility

Offer one default course setup. The reader downloads and extracts a small
practice bundle built from the same reviewed source as the course. The bundle
root contains `practice.py` and `requirements-practice.txt`. Its
`assets/example/` directory contains `report.py`, `pytest.ini`, and the
existing `data/`, `expected/`, and `tests/` files. This gives the reader
the exact lesson fixtures without cloning the repository. Verify a complete
inventory of regular files with safe relative paths, no duplicate paths, and
exact source bytes. Keep the existing sample download for inspecting the
finished report.

Extract into a fresh folder without a `.venv`. From that folder, run the
following setup. Each step runs after the preceding step succeeds.

```sh
COURSE_WORK="$(pwd -P)" &&
uv venv --python 3.12 .venv &&
uv pip install --python .venv/bin/python -r requirements-practice.txt &&
. .venv/bin/activate
```

The list includes base `attune-harness` and the tested pytest dependency.
Start with the existing pytest 9.1.1 pin in that list.
Readers with Harness and pytest in an existing compatible environment can
select that interpreter and set `COURSE_WORK="$(pwd -P)"` from the same
bundle root. Both paths keep that folder and terminal open for lesson 2,
which sets `PRACTICE="$COURSE_WORK/practice"`. Keep the same interpreter
for preparation, the lesson commands, and protected tests. POSIX setup
instructions retain their current platform scope.

Run a bounded compatibility check inside `practice.py` before creating the
requested directory. Check the Python floor, the installed Harness identity,
pytest import in the selected interpreter, and Git availability. Use the
installed CLI's public help to check the exact switches and choices the
course uses. Run the help probes with the selected interpreter, a timeout,
and captured output. Match option tokens and the required `plan` and
`markdown` choices. Record the package version for diagnosis and evidence.

| Command | Course interface |
| --- | --- |
| `init` | `--for plan`, `--goal`, `--project`, `--scope`, `--interpreter`, `--tests`, `--task-dir` |
| `plan` | `--request`, `--project`, `--config`, `--task-dir`, `--accept`, `--checkpoint` |
| `build` | Task directory and `--allow-external` |
| `status` | Task directory and `--format markdown` |

An absent package, dependency, or required option produces a short error that
names the failed check and the next action. The selected destination stays
absent on those refusals. Move the existing generated-command length check
before directory creation. Keep exclusive creation and the existing path
guards. If preparation later fails for an operational reason, name the
failed step and preserve any existing work. The build and approval owners
continue to enforce their own controls.

The preflight establishes interface availability. End-to-end qualification
establishes that the exercise works with a release. A future release with an
incompatible behavior behind a retained option can still fail at that owner
step. Record the observed refusal and update the affected lesson only when
the change requires it.

## Verification

- Initial release evidence uses separate environments installed from the
  exact published 1.7.0 and 1.8.0 wheels. Read-only checks in both installed
  environments already found the listed options. The full course exercises
  remain part of implementation verification.
- For each version, run the published setup commands from a fresh copy of the
  bundle, with a test-only resolver constraint selecting the verified wheel.
  Keep the learner instructions and dependency list unpinned for Harness.
  Run the rendered lesson's command blocks with a fresh practice directory and
  the checkpoint returned by that run. Check preparation without acceptance,
  then draft, accepted scope, local build completion, and saved-task inspection.
  Check both protected probes, seven unchanged protected files, zero model
  calls, and exact HTML bytes for the six-entry, 270-minute report.
- Verify missing dependencies and options, a bad destination, an overlong
  generated command, and an existing project. Compare existing files before
  and after refusals. Check generated output, ZIP contents, internal links,
  and the archived subtree inventory.
- Keep the repeatable check independent of the version label in the lesson.
  Supply each installed interpreter explicitly and record platform, Python,
  Harness, pytest, wheel hash, and results in separate evidence. Reuse the same
  check on later releases and keep the original 1.7.0 receipt.

## Website review and rollback

The site imports Help and training from one reviewed source commit. Update the
[Help importer's version check](https://github.com/Smart-AI-Memory/attune-ai/blob/e52de25e9083fea0181b1e9a23ea95da8fea0e65/website/scripts/harness-help-export.mjs)
for the reviewed Help export. Extend the
[training importer](https://github.com/Smart-AI-Memory/attune-ai/blob/e52de25e9083fea0181b1e9a23ea95da8fea0e65/website/scripts/harness-training-export.mjs)
to use the stable course identity and an explicit set of allowed current and
historical paths. Continue checking exact source identity, file inventory, and
hashes. Compare both import receipts to the reviewed commit and verify all
43 files in the legacy subtree against the prior export. Help publication
metadata remains independent of the course identity. Keep the frozen 1.7.0
routes and retarget the existing temporary Learn redirect to the practice
section on Get Started.

Adapt the [exact-commit website smoke check](https://github.com/Smart-AI-Memory/attune-ai/blob/e52de25e9083fea0181b1e9a23ea95da8fea0e65/website/scripts/harness-preview-smoke.py)
for the version-neutral heading. Verify the homepage link, Get Started,
practice setup and download, course overview, lesson 2, reading view,
historical deep links, and saved progress on the exact website preview. Show Patrick the complete rendered
Get Started page and its working course link for approval before production
publication. If the cutover fails, restore the preceding reviewed Help and
training exports and redirect target together.

## Tradeoffs

| Approach | Decision |
| --- | --- |
| Maintain a course per Harness release | Keep a single maintained course and preserve the existing versioned archive. |
| Infer compatibility from a version number | Check the required public interfaces and verify behavior with published wheels. |
| Run the exercise automatically during preparation | Keep preparation separate from learner acceptance and build authorization. Use the full exercise in maintainer qualification. |
| Download the repository on setup | Export a bounded practice bundle beside the exact course source it accompanies. |
