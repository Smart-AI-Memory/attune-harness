# Harness training

[Set up the reporting course](../help/get-started.md#set-up-the-practice-folder), then open
[Harness in practice](reporting/index.html). Six lessons follow one reporting
project from a useful goal through a checked result, saved work, review, a local
handoff and a proposed improvement.

[Choose how to start](reporting/development-paths.html) compares goal-driven
and spec-driven development with examples and review points.

Get Started provides a practice ZIP and installs
Harness and pytest in a separate environment. The command practice runs offline
after setup and uses fixed local participants. See the
[compatibility results](reporting/assets/compatibility.json) for the tested
versions and the [historical archive](archive/README.md) for earlier courses.

## Preview the course

Build the [combined Help and course preview](../help/README.md#build-and-preview)
so the setup and lessons share the same origin. Each lesson provides navigation,
**Copy** controls, optional knowledge checks, presenter notes, printing and
saved browser progress. Open **Read full lesson** to read the static HTML.

## Maintain one source

Edit each lesson's `lesson.json`, then run:

```sh
python3.12 training/build_course.py
python3.12 training/build_course.py --check
```

The generator creates the course pages, presenter notes and practice ZIP.
Shared styles and interactions live in `reporting/assets/styles.css` and
`reporting/assets/app.js`. Preserve existing storage keys and section IDs when
editing a lesson so readers can recover saved progress and notes.

The [content map](../docs/content-map.json) identifies authored sources,
generated outputs and website routes.

## Check the practice

Follow the [course setup](../help/get-started.md#set-up-the-practice-folder), then run the lesson 2 commands
from the extracted practice folder. The helper prepares an unfinished project,
fixed local command participants, two protected test files and an unaccepted
request. Review, accept and build the request in lesson 2.

The [compatibility results](reporting/assets/compatibility.json) describe the
versions and environments exercised. The original
[November 5 check summary](1.7.0-preparation/assets/current-checks.json) records
the earlier source-built 1.7.0 exercise.

To repeat the same course check, download a published wheel and find its SHA-256
on the PyPI release's download page. Install the [Help build dependencies](../help/README.md#build-and-preview)
in the verifier's Python environment. Run the verifier from the repository root
with the wheel, its expected digest, and an unused output directory.

```sh
python3.12 scripts/check_reporting_course.py \
  --wheel "$WHEEL" --sha256 "$WHEEL_SHA256" --output "$NEW_EVIDENCE_DIR"
```
