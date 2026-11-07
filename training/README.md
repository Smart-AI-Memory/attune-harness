# Harness training

Open the [current course](1.7.0-preparation/index.html): **Harness in practice**.
Six lessons follow one reporting project from a useful goal through a checked
result, saved work, review, a local handoff and a proposed improvement.

[Choose how to start](1.7.0-preparation/development-paths.html) compares
goal-driven and spec-driven development, with examples and the review points
both paths share. It is linked from the overview and the first two lessons.

The course uses published **Harness 1.7.0**. Its
[setup page](1.7.0-preparation/setup.html) installs the runtime in a separate
environment. The command practice runs offline after setup and makes no model calls.
Superseded material belongs in the separate [historical archive](archive/README.md).

## Preview the course

If you need the course source, clone the public repository:

```sh
git clone --depth 1 https://github.com/Smart-AI-Memory/attune-harness.git
cd attune-harness
```

From the repository root, start a local preview with uv:

```sh
uv run --no-project --python 3.12 python -m http.server 8768 --bind 127.0.0.1 --directory training
```

Open <http://127.0.0.1:8768/1.7.0-preparation/>. Each lesson has section
navigation, Copy controls with manual fallback, an optional knowledge check,
presenter notes, printing and independent browser progress. **Read full lesson**
provides static HTML for readers and tools that do not execute JavaScript.

## Maintain one source

Edit each lesson's `lesson.json`, then run:

```sh
python3.12 training/build_course.py
python3.12 training/build_course.py --check
```

The generator projects the same content into the interactive shell, full text
and presenter script. Shared appearance and interactions live in
`1.7.0-preparation/assets/styles.css` and `app.js`. Use a new storage key when
creating another lesson; do not rewrite a reader's saved answers.

[The content map](../docs/content-map.json) identifies authored sources,
generated outputs, intended website routes and publication state. The website
should import one reviewed export rather than maintain a second copy of these
lessons. A repository PR or local preview does not publish the course.

## Check the practice

Use the selected installed Harness 1.7.0 interpreter to run
`1.7.0-preparation/practice.py` with a new canonical destination. It prepares
an unfinished reporting project, fixed local command participants, two protected
test files and an unaccepted request. Accept and build separately as explained
in lesson 2. No provider SDK or account is used by the practice participants.

The [November 5 check summary](1.7.0-preparation/assets/current-checks.json)
records 77 reporting cases, both completed Harness probes, unchanged protected
inputs and the resulting sample bytes. It states the runtime and wheel identity.
These are software checks on macOS; browser/platform coverage and observed
learning effectiveness are separate claims.
