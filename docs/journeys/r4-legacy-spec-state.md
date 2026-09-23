# R4: another project's spec state, with a receipt

*September 23, 2026. Spec authority Task 5, plan task 3.2; the R4 line of
[the spec authority's acceptance](../specs/spec-authority/README.md), its D4,
and decision 3 of [D20](../specs/spec-authority/addendum-2026-09-23.md).*

R4 says: "Every plan in `.claude/plans/` that a Harness spec cites remains
readable, and Harness reads schema-version-1 spec state from any Attune AI
project (D4). Unknown versions are refused with a plain next action, never
guessed at." D4 adds the rule for what is read: read and convert, never write
back; originals untouched; a receipt per conversion. This is that journey as
it runs, command by command: a plan file from another project, named
explicitly, becomes a draft in the task store, and the conversion leaves a
receipt beside the record. No model is called; the import is offline.

The same sequence runs twice in the repository: as
`tests/test_r4_legacy_spec_state.py`, in the platform selection, over the
eight fixture plans below, and here. Every value shown was captured from one
run on September 23, 2026; the test pins the outcomes, the receipt's fields
and the refusal texts, not the digests or the times.

## Run it yourself

```bash
attune-harness plan --task-dir work --project project \
  --config participants.json --request request.json \
  --import-plan ~/attune-ai/.claude/plans/chart-widget-kernel.md \
  --allow-outside-project
cat work/import-receipts.jsonl
```

`--allow-outside-project` lifts exactly one rule, the one that refuses a plan
that is not a regular file inside the project; it is a `store_true` flag in the
style of `--allow-external`, meaningful only beside `--import-plan`, and
refused alone. A plan it names that resolves inside the project is refused
too, with the path to import without the flag, so that whether a task's
conversions leave receipts follows the record, a bound plan outside the
project, and never a file beside it. The request's `intent.scope` must list
the plan's outputs, as the store requires of every import, implicit or
explicit; for this plan that is fifteen distinct paths across the seven tasks.

## The fixtures

Eight plans under `tests/fixtures/plans/`, each byte-identical to a named
commit and each with a sidecar `<name>.origin.json` recording the repository,
branch, commit, path, SHA-256, size, schema version and task ids; the test
fails if a copy drifts from its sidecar. `.gitattributes` marks the directory
`-text`, so a Windows checkout does not rewrite their line endings.

| Fixture | Origin | Schema | Tasks | Conversion |
| --- | --- | --- | --- | --- |
| `attune-ai/chart-widget-kernel.md` | attune-ai, `main` at `b769dc2e8` (the file last changed in `ee4913ff3`, 2026-09-04) | 1 | T1 to T7 | draft, receipt |
| `harness/connected-journey-qualification.md` | attune-harness, `wip/local-snapshot-2026-09-19` at `c8b3235c` | 2 | 1 to 3 | draft, receipt |
| `harness/plan-build.md` | same | 2 | 1 to 8 | draft, receipt |
| `harness/release-readiness-follow-through.md` | same | 2 | 1 to 3 | refused by the store, see below |
| `harness/shared-memory-adoption.md` | same | 1 | 1 to 5 | refused by the store, see below |
| `harness/test-this-change.md` | same | 2 | 1 to 3 | draft, receipt |
| `harness/unified-task-execution.md` | same | 1 | 1 to 8 | draft, receipt |
| `harness/voyage-validation-reuse.md` | same | 1 | 1 to 3 | draft, receipt |

The attune-ai plan is the one D20.3 asked for: tracked in that repository's
history, small (8,036 bytes), read by both readers with a schema-version-1
state comment that marks all seven tasks complete, and free of secrets or
private context; it names only files and design decisions of the attune-ai
codebase. The seven Harness plans are the Task 2 differential's regression
set. Both readers read all eight. Two of the Harness plans, the release
readiness follow-through and the shared memory adoption, name their outputs
as absolute paths into a second checkout
(`/Users/patrickroebuck/attune-ai-memory-adoption/...`), which no intent scope
can cover, so the work store's intent rule refuses them before anything is
written, in its own words, `Expected a canonical relative file path outside
metadata`, on the explicit path and on the implicit one alike. That is a
property of those two plans, not of the reader; the test pins it.

## The sequence

**1. Import the plan by name.** Exit 0, `status: draft`. The envelope has the
same keys as an implicit import's, including `import_disclosures`, the
reader's account of what it could not map; nothing about the envelope changes
with the flag, so the golden table is untouched.

```bash
attune-harness plan --task-dir work --project project \
  --config participants.json --request request.json \
  --import-plan tests/fixtures/plans/attune-ai/chart-widget-kernel.md \
  --allow-outside-project
```

```json
{"status": "draft", "authority": "draft", "phase": "draft", "revision": 1,
 "checkpoint_digest": "3d69cd47…8fd73",
 "summary": "Draft ready for review; work is not yet accepted.",
 "next_action": "Review this work record; use plan --accept with this exact --checkpoint.",
 "import_disclosures": ["Unmapped surrounding content: # Chart-widget kernel\n\n**Outcome:** …"],
 "tasks": [{"id": "T1", "dependencies": [], "outputs": ["src/attune/widgets/chartkit/package.json", "…"],
            "checks": ["dist/kernel.min.js builds and carries version banner", "…"]}, "…"],
 "task_directory": "…/work", "record_path": "…/work/record.json", "blocking": true}
```

The record is a draft with no acceptance: the state comment's `completed`
list, all seven tasks, is read and recorded and grants nothing
(`approval_imported: false`), as the implicit import has always held.

**2. Read the receipt.** One JSON line in `work/import-receipts.jsonl`,
written through the same locked writer as the workspace events, sorted keys,
ASCII, 1,982 bytes for this plan. Shown here indented and shortened.

```json
{"schema_version": 1, "receipt": "legacy-plan-conversion", "conversion": "import",
 "time": "2026-09-23T22:06:35.959894+00:00",
 "source": {"given": "tests/fixtures/plans/attune-ai/chart-widget-kernel.md",
            "resolved": "/…/tests/fixtures/plans/attune-ai/chart-widget-kernel.md",
            "sha256": "afd414bc5d5de98035f54b3b6266ba6450163b19dc430ce3d23eaab049d11d5b",
            "content_sha256": "01ac25d6…7eb4f", "bytes": 8036},
 "state_comment": {"present": true, "schema_version": 1, "ignored": null},
 "spec_state": {"schema_version": 1, "completed": ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
                "current": null, "auto_run": false,
                "last_updated": "2026-08-05T07:57:26.252622+00:00", "task_receipts": 0},
 "mapped": [{"id": "T1", "objective": true, "dependencies": 0, "outputs": 5, "checks": 3},
            {"id": "T2", "objective": true, "dependencies": 1, "outputs": 3, "checks": 1}, "…"],
 "unmapped": {"fields": {"T1": ["name"], "T2": ["name"], "…": "…"},
              "disclosures": {"count": 1, "sha256": "a4ef22ed…64ca0",
                              "kinds": {"surrounding": 1, "nested": 0, "attributes": 0, "elements": 0}}},
 "approval_imported": false,
 "task": {"task_id": "745b3493-…", "revision": 1,
          "record_path": "…/work/record.json", "checkpoint_digest": "fbb03359…e8f71"}}
```

The fields, in the design note's order. `source`: the path as given, in the
command line's normalised spelling (`./a//b.md` is recorded as `a/b.md`), and
as resolved (a symlink named explicitly is followed, and both are recorded),
the SHA-256 of the file's bytes, which the test compares with its own hash of
the file, the digest of the plan without its state comment, which is what the
record binds and the freshness check re-reads, and the size. `state_comment`:
whether the plan has a state comment, the schema version it declares, and,
when the reader ignored the comment with its warning (a `completed` that is
not a list of strings, a `current` that is not a string), why. `spec_state`:
the comment as `spec_state` reads it, or `null`, which `state_comment` tells
apart: no comment, or one ignored. `mapped`: each task in the store's shape,
with the counts of what it carries. `unmapped`: per task, the parsed fields
the store's shape has no place for, the `name` attribute, `risks`, and file
descriptions, all of which stay in the record's `request.legacy.tasks`; and
the reader's disclosures by count, by kind (prose around the blocks, nested
content, task attributes, unknown elements) and by digest, the SHA-256 of the
list the record keeps in full as `request.legacy.unsupported` and the
envelope shows as `import_disclosures`. A receipt that repeated the
disclosures would grow with the plan's prose; by count and digest it stays a
few kilobytes for the fixtures. `task`: the record the receipt is about, by
identity, revision and checkpoint. `time`: UTC, taken after the record is
saved.

**3. Reimport, and read the second line.** After an edit to the plan, a
`--reimport` with the current checkpoint re-reads and re-converts it through
both readers, and because the record binds a plan outside the project, which
only the explicit path does, the reimport appends a receipt: the second line
says `"conversion": "reimport"`, the new digest, the state read again, and
revision 2 with its checkpoint. The first line is byte-for-byte what it was.
The record decides, not the file: a receipts file that was deleted is started
again by the next conversion, and a task imported the implicit way is never
receipted, whatever is planted beside its record.

```bash
attune-harness plan --task-dir work --reimport --checkpoint fbb03359…e8f71
```

Before the record is saved, the conversion checks that the receipts file can
take the line, since a receipt is written after the save (it names the
record's checkpoint) and the writer's bound is 1 MiB per file: a symlinked,
hard-linked or non-regular receipts file, or one the line would push past the
bound, refuses the conversion with nothing changed and the next action, to
move the file aside so the next conversion starts a new one. The check
measures the line with the values the save will supply at their longest, so
a line it passes the writer takes. What can still fail after the save, a
race or the writer's lock, is reported as the command's error, never
swallowed, naming the revision that landed and its checkpoint and the
reimport with that checkpoint that records the receipt; the test stages it
with a writer that refuses, since a race cannot be.

## The refusals

Each refusal but the last is before anything is written: no task directory
exists afterwards, or, on a reimport, the record keeps its revision and its
checkpoint and the receipts file its bytes.

| Case | Exit | `error.detail` |
| --- | --- | --- |
| The same plan without the flag | 2 | `Legacy plan must be a regular file inside the project` |
| A symlink to a plan inside the project, without the flag | 2 | `Legacy plan must be a regular file inside the project` |
| `--allow-outside-project` without `--import-plan` | 2 | `--allow-outside-project requires --import-plan` |
| The flag on a plan that resolves inside the project | 2 | `Legacy plan resolves inside the project: <resolved path>. Import that path without --allow-outside-project.` |
| State comment `"schema_version": 3`, with the flag, on an import or a reimport | 2 | `Unsupported Spec state comment in <path>: schema_version 3 is newer than this Harness reads (1 and 2). Update Harness, or keep working on the plan with the version that wrote it.` |
| No `schema_version` in the comment, with the flag | 2 | `Unsupported Spec state comment in <path>: schema_version none is not one this Harness reads (1 and 2). Remove the spec-state comment to start the plan over, or set "schema_version": 2 if the recorded state is trusted.` |
| `"schema_version": "2"` (a string), with the flag | 2 | as above, with `schema_version "2"` |
| `"schema_version": 3`, inside the project, without the flag | 2 | `Unsupported Spec state comment` |
| The two plans whose outputs are absolute paths | 2 | `Expected a canonical relative file path outside metadata` |
| A reimport whose receipts file is a symlink, or sits in one | 2 | `Conversion receipt cannot be written: <path> is, or sits in, a symlink. Nothing was changed. Remove the link; the next conversion starts a new receipts file.` |
| … has more than one link | 2 | `Conversion receipt cannot be written: <path> has more than one link. Nothing was changed. Remove the other link, or move the file aside; the next conversion starts a new receipts file.` |
| … is not a regular file | 2 | `Conversion receipt cannot be written: <path> is not a regular file. Nothing was changed. Move it aside; the next conversion starts a new receipts file.` |
| … would pass the writer's bound with this line | 2 | `Conversion receipt would not fit: <path> would pass 1048576 bytes. Nothing was changed. Move the receipts file aside to archive it; the next conversion starts a new one.` |
| A receipt refused after the record was saved (a race, the writer's lock) | 2 | `The conversion landed as revision 2 with checkpoint <digest>, but its receipt was not written: <the writer's words>. Inspect import-receipts.jsonl beside the record and remove or move it aside, then reimport with this checkpoint to record the receipt.` |

The explicit path reads the state comment through `spec_state` before the
tasks, on an import and on a reimport alike, so an unknown version gets that
module's refusal with its next action. The implicit path keeps its own words
for the same file (D20.1): the reader's contract text, unchanged. A comment
the reader ignores with a warning (a `completed` that is not a list of
strings, a `current` that is not a string) is not a refusal on either path,
as the carried reader has it; the receipt records it under `state_comment`.

## The original is only read

The test proves it three ways for every fixture: the SHA-256 of the file and
its modification time and size are the same before and after the import, and
every open of the plan during the import, through `Path.open` or the builtin,
is in a read-only mode. The receipt's `sha256` equals the test's own hash of
the bytes.

## On Windows

The test carries the platform marker, so the Windows jobs run it against the
installed wheel. The fixture directory is `-text`, the receipts file is
written through the writer that already handles Windows's append (trap 1 of
[the Windows traps](../windows-traps.md)), the paths in the receipt are
strings as the platform spells them, and the symlink cases skip where the job
has no symlink privilege, the hard-link case where the file system refuses
one; nothing else here is platform-specific. The obstacle tests make the
receipts path a directory, fill the file to sixteen bytes short of the bound,
or replace it by a link; the failure after the save is a writer that refuses,
staged in-process, since a race cannot be.
