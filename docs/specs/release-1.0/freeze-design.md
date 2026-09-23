# The interface freeze (4.1): design note

Draft of September 23, 2026, the evening [D25](addendum-2026-09-23.md) ruled
what the freeze covers and when, for [the plan's task 4.1](../../plan-1.0.md).
Like the design notes before it, it puts what was read from the code first,
then the design, then the decisions that are Patrick's. Nothing here is
authorized until he rules; the rulings go in the release addendum, numbered
on from D26.

## What D25.2 already settled

Frozen means three things at once: a written list, a test that fails on a
non-additive change to anything on it, and a deprecation rule for the change
that is allowed anyway. Additive changes stay free after 1.0.0: a new verb, a
new optional key, a new optional configuration field. A rename, a removal or
a change of meaning ships only with the old form still working for one minor
release, a `deprecations` entry in the envelope, and a changelog line. The
list has six surfaces: the CLI verbs with their subcommands, required
arguments and exit codes; the envelopes' top-level keys, `schema_version`,
the meaning of every `status` value and the exit codes, never the values;
the configuration and saved state, the memory config, the task and run
records, plan state schema 1 and 2, the scratch record from 3.4, the
extension manifest and the accepted registry; the refusal texts, already
contracts under D20.1; the Python API, `run`, `Task`, `Output`, `Check` and
`Receipt`, their signatures and `run`'s documented behaviour; and the
protocols, MCP tool names and schemas per profile version and the A2A local
profile. Outside it: envelope values, stderr text, module names, the
experimental features' contracts, the receipt layouts under `docs/`, and
attune-ai's keyspace as read. Two moments: the content freezes at `1.0.0rc1`,
a change to anything on the list after that restarts the candidate as `rc2`,
and the promise takes effect at 1.0.0. So 4.1 lands last before the
candidate, after 3.4's record and 4.3's manifest fields, in three cycles; the
third is the saved-state fixture.

This note turns each of the six rows into a guard that exists in the
repository, names what has to change first, and puts the choices to Patrick.

## What the code says today

Read against `main` at 2136d59, the evening of September 23.

**The verbs.** `--help-all` lists twenty-eight top-level verbs: `build`,
`cancel-review`, `cancel-task`, `code-config`, `extension`, `fix`,
`github-checks`, `index`, `inspect-review`, `mcp-inspect`, `mcp-serve`,
`memory`, `plan`, `reconcile-review`, `reconcile-task`, `repair-economics`,
`resume`, `resume-review`, `retrieval-task`, `retrieve`, `review`,
`review-form`, `status`, `test`, `transfer-review`, `transfer-task`,
`triage-check` and `verify`; `extension` carries seven actions, `index` four
and `memory` thirteen. The parsers are registered across `cli.py`,
`work_cli.py`, `review_cli.py` and `memory_cli.py`. What pins them today is
`tests/test_task_compatibility.py`: the seven journey verbs in `--help`, the
eighteen compatibility names present in `--help-all`, and model-free `--help`
for each; nothing pins the full list, an argument or an exit code.

**The envelopes.** Seventy-one rows in `tests/test_golden_envelopes.py` and
[the envelope table](../../envelopes.md), pinned by top-level keys,
`schema_version`, `status` and exit code, values never;
`test_documented_table_matches` fails when the page and the test disagree.
The table records eight gaps: no `schema_version` on `plan`, `build`, the
feature-work `status` and `memory scratch`; no `status` on `code-config`,
`triage-check`, `repair-economics` and `github-checks`. Two verbs print no
envelope, `mcp-serve` and the help. Seven rows run on POSIX only.

**The saved state.** Every record on disk carries a version, and every reader
already refuses what it does not know. The task record: `schema_version` 1
and a `task_profile` naming its contract, `assessment-intake-v1`,
`feature-work-v1` or `pytest-change-v1`; `read_task` binds `record_path` to
the directory it reads from (`task_contract.py:226`), and the feature-work
reader requires `project_root` to exist as an absolute directory. The run
record: `review_contract` accepts `schema_version` 1. The plan state
comment: `spec_state.CURRENT_SCHEMA_VERSION` is 2 and the reader refuses any
other with a text that names the file and the version; `spec_legacy` reads 1
and 2. The worker proposal inside a build: schema 3, with schema 2 still
accepted at one site (`work_build.py:259`), the one place the repository
already practises the rule D25.2 states. The effects manifest carries a
profile name, `posix-feature-effects-v1` or `windows-feature-effects-v1`, and
a `before` snapshot the host re-verifies. The scratch record: `schema_version`
1 today; 3.4 adds the format name, its version and a `writer` field (D21.6),
and the scratch format's version opens the compatibility list. The extension
manifest: `schema_version` 1, data only; 4.3 adds `grants`, `declares` and
the `run` binding as version 1's vocabulary (D22.3). The accepted registry:
`participants.json` at `schema_version` 1, copied into the record at
acceptance. The memory config: `roots`, `redis`, `scratch` and `reader`
sections, validated by their readers. The memory context packet:
`schema_version` 1. One fixture of this kind exists,
`tests/fixtures/memory_compatibility.json`, for the memory formats; none for
the task, run, plan or extension records.

**The refusal texts.** Contracts since D20.1, pinned where they arise: the
gate tests, the golden refusal rows, the differential Task 4 ran before the
switch. Nothing changes here; the list names where they are pinned.

**The Python API.** `attune_harness/__init__.py`, 118 lines: `Task`,
`Output`, `Check`, `Receipt`, `run`, and two more public names the README's
example relies on, `Status` (the three terminal values, `verified`,
`rejected`, `failed`) and the `Participant` protocol. `Task.schema_version`
must be 1. `run` executes once and never retries; the docstring says so and
the README says so. Nothing tests the README's example as written, and
nothing pins a signature.

**The protocols.** `mcp_server.py` speaks `MCP_PROTOCOL = '2026-07-28'` and
`MCP_LEGACY_PROTOCOL = '2025-11-25'`; the tools it lists come from the
registry's selection with one input schema, `RETRIEVE_SCHEMA`, and one
output schema; `mcp-inspect` returns the profile in its envelope. `a2a.py`
implements the local task and artifact profile of
[the A2A workflow](../../a2a-workflow.md). Neither has a golden fixture of
its tool names or schemas.

**The extras.** Nine in `pyproject.toml`: `tokens`, `verify`, `rag`,
`review` and `mcp` empty since 0.4.0, which the README promises are removed
at 1.0; `redis`, `voyage`, `all` and the experimental `memory-native`.
`tests/test_extras.py` pins them.

**Deprecation.** No mechanism exists under `src/`: no `deprecations` key,
no register, no helper. The word appears only in dated documents.

## The design

### 4.1.1 The list is one document with a machine twin

`docs/compatibility.md` states the six surfaces, one section each, with the
guard named beside every entry, in the shape D25.2's table already has. Two
of the six have a machine form the document cannot be trusted to keep on its
own. The verbs get `tests/fixtures/compatibility/surface.json`: for each
verb and subcommand, its required arguments and the exit codes its
documentation names, produced from the parsers by
`scripts/compatibility_surface.py` and compared to the committed file by a
test, so adding a required argument or dropping a verb fails a named case;
`test_documented_surface_matches` keeps the document and the file honest, the
way the envelope page is kept honest today. The envelopes keep their table.
The other four surfaces are pinned by the tests this note adds below, and
the document points at each.

### 4.1.2 The eight gaps close first, additively

`schema_version: 1` on the four envelopes without it, `status` on the four
without it, each a new key, so additive under D25.2 and safe to land now; but
each changes a golden row and the table, so each is a deliberate diff with a
changelog line, in the first cycle, well before `rc1`. What the four report
verbs say in `status` is decision 2: they compute and never fail short of an
exception, so `completed` is the honest value, with the mapping to `failed`
they already share through the CLI.

### 4.1.3 The deprecation rule as a small mechanism

A rule nobody can run is prose. The minimum that makes it run: a register,
`docs/deprecations.json`, empty at 1.0.0, whose entries carry `surface`,
`form`, `since`, `removal` and `replacement`; a helper in `features.py` that
appends an entry to an envelope's optional top-level `deprecations` list
when a deprecated form is used, and never otherwise, so the golden rows on
current forms do not change; and `tests/test_deprecations.py`, which checks
the register's shape, that every entry's `removal` is one minor release after
`since`, that the current version has not passed a `removal` whose form still
exists, and, through one synthetic alias in the test, that the helper writes
the entry and the changelog convention is stated. Decision 3 asks whether
this ships at 1.0.0 with an empty register, as recommended, or waits for the
first deprecation in 1.x.

### 4.1.4 The saved-state fixture, the third cycle

`tests/fixtures/compat-1.0/` holds records the candidate itself wrote: a
feature-work directory as a draft and another as accepted with its plan and
`decision.json`; a paused assessment run; a test-change record; a plan file
with a schema 2 state comment; a scratch store on the file backend in 3.4's
format; an extension state directory with a version 1 manifest; a memory
roots layout with a raw, a personal and a curated root and the config that
names them; an effects manifest with its snapshot. A README in the directory
says which release wrote each and how.

The crux is relocation. The readers bind absolute paths on purpose:
`record_path` to the directory, `project_root` and the config path to real
files, the plan's path inside its project. A fixture copied to a temporary
directory would be refused by the very checks the freeze protects. So the
test relocates through one function, `relocate(fixture, target)`, that
rewrites exactly the path-bound fields the README lists and nothing else,
and the test asserts that a record relocated and a record left in place give
the same envelope keys. Then it runs the readers: `status` on each record,
`resume` where a paused record allows it, `inspect-review`, `plan
--decision` on the draft, `extension inspect`, `memory scratch retrieve`,
`memory recall` over the roots, and asserts each envelope's keys and
`status` against the golden rows and each refusal's words where a refusal is
the right answer. The fixture is captured at `rc1`, from the candidate's own
wheel, and refreshed only when a format changes under the deprecation rule,
in which case the old fixture stays beside the new: both must read.
Decision 5 asks whether relocation by rewriting is acceptable, as
recommended, or whether the readers should accept relative paths, which
would be a contract change before the freeze.

### 4.1.5 The Python API, tested as the README shows it

`tests/test_public_api.py` extracts the fenced Python example from the
README and runs it as written, then its two variants the README describes,
the worker that returns `"5"` and the check that raises, asserting
`verified`, `rejected` and `failed`; it pins that `run` calls the participant
once with a counting worker; and it snapshots the signatures of the seven
public names with `inspect.signature` against a committed text, so a
parameter added, removed or renamed is a deliberate diff. Decision 4 asks
whether `Status` and `Participant` are on the list with the five the README
names; the example uses both.

### 4.1.6 The protocols, pinned per version

`tests/fixtures/compatibility/mcp-2026-07-28.json` and its 2025-11-25
sibling hold the tool names and the digests of the input and output schemas
the server lists under each protocol version, captured through
`mcp-inspect` and the server's own listing; a test fails when the listing
under a version changes. The A2A local profile gets the same for its agent
card and the task states the profile uses. D25.2's rule, changed only with
the protocol version, then means: a new version adds a new fixture and leaves
the old one in place.

### 4.1.7 The empty extras go in the first cycle

Removing `tokens`, `verify`, `rag`, `review` and `mcp` is the change the
README promised for 1.0, and it is the one change on the list that a user's
script would meet at install time, so it belongs at the start of the
candidate period, not at 1.0.0: `rc1` ships without them, and the two weeks
of dogfooding are where a `pip install 'attune-harness[review]'` still in
someone's script would show. `test_extras.py` and the README's install
paragraph change with it. Decision 6.

### 4.1.8 The two moments, in the runbook and the tests

The content freeze at `rc1` needs no new machinery: the guards above fail on
any change to the list, in every run. What `rc2` needs is a rule, and it goes
in the release runbook's candidate section: a pull request during the
candidate period that changes a golden row, `surface.json`, a signature
snapshot, a protocol fixture or the fixture's readers restarts the candidate
at the next `rc` number, with the changelog line saying why. Decision 7 asks
whether a classifier label for pull requests touching those files is worth a
cycle; the recommendation is no, the tests already refuse silently-changed
surfaces and the runbook rule covers the deliberate ones.

## Order and dependencies

The gaps, the extras, the verb surface, the API test and the document's
first draft touch nothing 3.4 or 4.3 change, so they are the first cycle and
can start now. The deprecation mechanism and the protocol fixtures are the
second. The document's saved-state section and the fixture wait for 3.4's
scratch format and 4.3's manifest fields, so the third cycle is the last
thing before `rc1`, as D25.2 orders. Each cycle carries a different-model
review under [the brief](../../review-brief.md) where it touches `src/`, and
a findings-log row.

## Decisions for Patrick

1. **Where the list lives.** Recommended: `docs/compatibility.md` for people,
   `tests/fixtures/compatibility/surface.json` for the verbs, kept in step by
   a documented-matches test as the envelope page is. Alternative: the
   document alone, which the review findings log says drifts.
2. **The eight gaps' values.** Recommended: `schema_version: 1` on the four
   feature-work and scratch envelopes; `status: completed` on the four
   report verbs, with `failed` on exception as the CLI already maps.
   Alternative: leave the gaps and freeze the table as it is, which pins an
   inconsistency for the life of 1.x.
3. **The deprecation mechanism at 1.0.0.** Recommended: the register, the
   helper and the test ship at 1.0.0 with the register empty, so the first
   deprecation in 1.x has a path that already runs. Alternative: the rule in
   prose now, the mechanism with the first deprecation.
4. **The Python API's names.** Recommended: seven, the five the README opens
   with plus `Status` and `Participant`, which its example uses;
   `Task.schema_version` fixed at 1 is part of the contract. Alternative:
   the five only.
5. **Relocating the fixture.** Recommended: one `relocate` function that
   rewrites the listed path-bound fields, and a test that a relocated record
   reads as an in-place one does. Alternative: readers that accept relative
   paths, a contract change this note advises against before the freeze.
6. **The empty extras.** Recommended: removed in the first cycle, so `rc1`
   lacks them and the candidate period surfaces any script that still names
   one. Alternative: removed at 1.0.0, as the README's wording could be read.
7. **The `rc2` rule.** Recommended: the runbook's candidate section and the
   tests, no new CI. Alternative: a classifier label on pull requests that
   touch the frozen files.

## Evidence 4.1 ends with

`docs/compatibility.md` and `surface.json` with their test; the envelope
table with no `-` in it and seventy-one or more rows; `test_public_api.py`
green on the README's example; `docs/deprecations.json` empty with its test;
the two MCP fixtures and the A2A one; `tests/fixtures/compat-1.0/` with its
README, `relocate` and its test; the five empty extras gone from
`pyproject.toml`, `test_extras.py` and the README; the runbook's candidate
section naming the `rc2` rule; a changelog line per change; and a row in the
findings log for each reviewed cycle.

## Size

Three cycles, as D25.2 counted: the first can start now and touches `src/`
only in the eight gap closures and the deprecation helper; the second is
tests and fixtures; the third is captured from the candidate. The list
document is drafted in the first and finished in the third, after 3.4 and
4.3 have said what their formats are.
