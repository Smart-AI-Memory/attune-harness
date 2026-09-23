# Changelog

## Unreleased

Changes since 0.5.0, each `src/` change with its different-model review
recorded in its pull request. The first three lines landed together after
the overnight run of September 23, 2026, so that three sibling pull requests
did not conflict on this section.

- Fixed: the task reader parses each top-level `<task>` block on its own, so
  prose between two tasks (a bare `&`, a `<`) no longer drops the whole plan
  to the regex path where entities stop being decoded; a block the parser
  rejects falls back alone and is reported as dropped if neither path can
  read it; orphaned content between blocks is still reported; a plan whose
  task tags do not balance, or that carries a comment or CDATA section in
  the task region, keeps the whole-plan path as before. The regex path also
  accepts `</task >` (O-58, #98).
- Fixed: the plan-state writer and the Voyage index writer replace their
  target through `features.replace_file`, which retries for a bounded time
  on Windows while a reader holds the file, as the run store already did; a
  reader holding a plan open no longer fails `save_state` there. A guard
  test pins every spelling of a replace under `src/` to `features.py` and
  the effects host's `dir_fd` replace in `repair.py` (O-59, #99).
- Changed: the `memory` command binds structlog to stderr once per process,
  through a writer that resolves the current stream on every line and drops
  a diagnostic on a missing or closed stream instead of failing the command;
  `main` owns the binding and `execute` no longer rebinds it (O-67, #100).

- Added: `plan --import-plan PATH --allow-outside-project` accepts a plan
  file outside the project when it is named explicitly (spec authority Task
  5, plan task 3.2; D4, D20.3): the plan is read once through `spec_state`
  (schema versions 1 and 2; any other refused with the next action) and
  `spec_legacy`, converted exactly as the implicit import is, and the
  conversion leaves one receipt line in `import-receipts.jsonl` beside
  `record.json`, the path as given (normalised) and resolved, the file's
  SHA-256, the state comment read or whether one was present and ignored,
  what was mapped, what was not (the reader's disclosures by count, kind and
  digest; the record keeps them in full), and the time, the line's room
  checked before the record is saved; a `--reimport` of such a task, one
  whose bound plan lies outside the project, appends a second line. A plan
  the flag names inside the project is refused. The original is only read.
  The implicit import and its refusals are unchanged. Fixtures under
  `tests/fixtures/plans/`, one plan from attune-ai's own `.claude/plans` and
  the seven Harness plans of the Task 2 differential, each with its origin
  recorded; the journey with its envelope, receipt and refusals is
  `docs/journeys/r4-legacy-spec-state.md`.
- Added: the `all` extra, `pip install 'attune-harness[all]'`, installs the
  two qualified extras, `redis` and `voyage`, in one word; it is
  self-referential so the pins stay where they are. `memory-native` stays
  explicit because it is experimental and POSIX-only. The base install is
  unchanged.
- Added: the R2 clean-environment journey, plan, accept, build, review and
  status with `attune` absent and no model called, runs three ways (spec
  authority Task 4, step c; D23.1): as `tests/test_r2_journey.py` in the
  platform selection, so the Windows jobs run it too and fail rather than
  skip on an outcome the test does not name; as the `journey` section of
  `scripts/check_installed.py`, in every mode, the whole journey where
  attune-forms is installed and the install-hint refusals from the
  `--no-deps` wheel, with the adapters and model calls read from the
  evidence; and in the release gate, whose build job now also installs the
  wheel with its base dependencies from the index under the lock files and
  asserts on both reports. The platform receipt carries the section's
  outcome as `r2_journey`, on Windows the build's refusal in the platform's
  own words if it refuses. The sequence and its envelopes are in
  `docs/journeys/r2-clean-environment.md`.

- Changed: the work-acceptance host and the plan import moved from
  `spec_bridge` to `work_accept`; `WorkSpecBridge` is `WorkAcceptance`. Every
  refusal text, the readiness check and the import receipts are unchanged,
  and the legacy plan reader that remained is now `spec_legacy` (spec
  authority Task 4, step a and step b's rename; D20.1, D23). The gate tests
  are `tests/test_work_accept_gate.py` and the reader's
  `tests/test_spec_legacy.py`.
- Changed: `plan --accept` and `plan --decision` walk the workspace's
  execution stages instead of opening at the task gate: `approval`, then
  `start_execution`, then the execution boundary's lifecycle gate with
  Harness's readiness checks as its receipts (the planner assignment and the
  required controls), then the task and its result, which is the gate the
  human decides at, as before. A draft whose required control no runner
  supports now stops at the blocked gate: `plan --decision` retains that gate
  as the decision, and `plan --accept` refuses with the receipt's words, the
  same words the bind refused with. The refusal for missing intent is
  unchanged and still precedes the walk; every accept and decision envelope
  keeps its keys. `chair_required` is wired and has no Harness source yet
  (spec authority Task 4, step b, second half; D23.2, D24).
- Changed: the envelope table's recorded gaps are closed, additively. The
  feature-work envelopes, `plan`, `build`, `status`, `resume` and
  `reconcile-task` on work and their refusals, and every result
  `memory scratch` returns, carry `schema_version: 1`; `triage-check`,
  `repair-economics` and `github-checks` carry `status: completed` on
  success and `schema_version: 1` on their refusals, which the table now
  pins as two refusal rows. `code-config` keeps no `status`: its envelope is
  the retrieval config that `index plan --config` reads back, and a test now
  runs that round trip. Fifteen golden rows change or are added; nothing is
  renamed or removed (the first freeze cycle, 4.1; D27.2, with `code-config`
  the one exception it did not foresee).
- Removed: the five empty extras, `tokens`, `verify`, `rag`, `review` and
  `mcp`, kept since 0.4.0 so that an existing `pip install
  'attune-harness[review]'` went on working. The README promised their
  removal at 1.0 and D27.6 put it in the first freeze cycle. An install that
  still names one gets pip's warning that the extra does not exist and the
  base install, which carries everything they installed; drop the bracket.

## 0.5.0

Memory is native. `attune-harness memory recall`, `resolve` and `refresh`
read explicit `raw`, `personal` and `curated` roots with Harness's own
reader by default, nothing from attune-ai on the path: the standard library
for the raw tier and attune-rag's keyword retriever, already in the base
install, for the document tiers (native memory Phase 2, D19). The reader
reproduces the adapter's contract, its refusal texts, the strict content
gate carried verbatim from the sanitizer's patterns, and the provenance and
staleness metadata on document items; a differential against attune-ai's
adapter, run where its checkout exists, agrees on statuses, result order,
texts, versions and every item's metadata. `"reader": "adapter"` keeps that
adapter selectable as the rollback until the transition ends. The import
guard's known list is empty; the release gate reads a raw root from the
`--no-deps` wheel and asserts on the receipt; the golden envelope table pins
the native shapes. The reader is POSIX-only until the Phase 4 decision; on
Windows it reports the refusal. Interfaces may still change before 1.0; the
README's qualification table says what is and is not covered.

- Changed: the native reader is the default, Phase 2 step 2.4 (D19).
  `memory capabilities|recall|resolve|refresh` read the roots with Harness's
  own code unless the memory config says `"reader": "adapter"`, which keeps
  attune-ai's adapter selectable as the rollback until Task 9. The import
  guard's known list is empty; the adapter import is allowed only inside
  that branch, and a test constructs the default host and shows nothing from
  attune loads. The installed checks read a raw root through the reader in
  every mode, the `--no-deps` release gate included, and record the POSIX
  refusal on Windows; the golden table pins the native success envelopes.
- Added: the native reader's document items carry the adapter's provenance
  and staleness metadata, Phase 2 step 2.3 (D19): `provenance` (tier,
  source, author class, the instruction-shape flags and the
  `<recalled_memory>` envelope) and `unverified_days`, `staleness` and
  `status` from the file's age, its `verified:` date and the `.verdicts.jsonl`
  sidecar, computed as the curated audit computes them. `memory_controls`
  carries the patterns, the digest, the verdict loader, the age basis, the
  tiers and the labels from attune-ai's source. The differential against
  the adapter now compares item metadata and adds an adversarial corpus;
  both agree completely. The adapter's telemetry write is not reproduced.
- Added: the native memory reader, Phase 2 step 2.2 (D19). With `"reader":
  "native"` in the memory config, `memory capabilities|recall|resolve|refresh`
  read the `raw`, `personal` and `curated` roots with nothing from attune-ai:
  the standard library, plus attune-rag's keyword retriever, already in the
  base install, for the document tiers. The reader reproduces the adapter's
  contract as the Phase 2 design note records it: the config validation and
  its words, the binding, the descriptor walk (POSIX-only, as the adapter),
  the 8 MiB, 4,096-file, 64 MiB and 30-day bounds, the raw tier's ranking
  and exact `cwd` scope, the document tiers' ranking over a snapshot that
  keeps mtimes, the frontmatter authority check, the strict content gate
  carried into `memory_controls.py` (the sanitizer's blocking secret and
  personal-data patterns, verbatim; a match refuses in the adapter's words),
  the four statuses and the refusal texts the differential covers. The provenance fields and staleness
  annotations follow in 2.3 with the differential harness; the default stays
  `adapter` until 2.4. A differential test against the adapter runs where
  `ATTUNE_TEST_ADAPTER_ROOT` names the checkout.
- Native memory Phase 2, step 2.1 (D19): the compatibility fixture
  `tests/fixtures/memory_compatibility.json` is on `main`, byte identical to
  the accepted one and pinned by digest and shape on every platform; the
  success envelopes of `memory capabilities|recall|resolve|refresh` are in
  the golden table over an in-process double of the adapter's four-member
  contract; the Phase 2 design note carries the measured dependency (40
  attune-ai modules, 455,609 bytes, on the read path) and the fixture's
  coverage gaps for 2.2.
- Docs: findings-log rows for the `memory serve` and lease reviews and the
  tally over eight full records; the 1.0 plan links the envelope table now
  that it is on `main`; the release runbook records what automating 0.4.0's
  steps taught, including the empty-index flake on a platform job and the
  `dist/` prefix in `SHA256SUMS`.

## 0.4.0

The install is batteries-included and memory is served. `pip install
attune-harness` carries the review, test, acceptance and MCP journeys (D15);
`pip install 'attune-harness[redis]'` adds `memory redis`, read-only reads of
the Redis Stack keyspace a hydration keeps warm, the Redis backend for
`memory scratch` working memory, and `memory serve`, the recall digest as
plain text for a session-start hook that fails open (native memory Task 4,
D16 to D18). The run store's lease waits a bounded two seconds before it
reports busy. Every CLI verb's envelope is pinned by a golden table ahead of
the 1.0 freeze, the review loop is recorded as data with a Windows traps page,
and `docs/plan-1.0.md` lays out the four phases to 1.0.0. Interfaces may
still change before 1.0; the README's qualification table says what is and
is not covered. attune-ai cannot share an environment with this release
(`mcp` 2.2.0 against its 1.29.1); use `pipx` or a separate venv.

- Docs: `docs/plan-1.0.md`, the four phases between 0.4.0 and 1.0.0, twenty
  tasks with their acceptance receipts, the decisions each needs, and
  measured cycle estimates; nothing in it is authorized by itself.
- Pinned: the envelope of every CLI verb, ahead of the 1.0 freeze.
  `tests/test_golden_envelopes.py` runs each verb, and each subcommand of
  `extension`, `index`, `memory redis` and `memory scratch`, in-process on the
  cheapest deterministic fixture that yields an envelope and compares the
  sorted top-level keys, `schema_version`, `status` and exit code to a
  checked-in table; renaming or dropping a key now fails exactly the case
  whose id names the verb. Where a success envelope is reachable offline it
  is the one pinned; `build` before acceptance, `index build|update|inspect`
  and `retrieval-task` without a generation or `--allow-provider`, and the
  memory host route without attune-ai pin their refusal or `unavailable`
  envelope instead, and `mcp-serve` is not pinned because its stdout is the
  MCP protocol stream. `docs/envelopes.md` carries the same table as the
  compatibility surface the 1.0 changelog will point at, and a test keeps the
  two in step. The pass also recorded, without changing them, that the
  feature-work (`plan`, `build`, their `status`) and `memory scratch`
  envelopes carry no `schema_version`.
- Changed: the run store's writer lease waits a bounded time, two seconds
  like the record replace and the event writer's lock, before it reports
  `Run is busy; another owner holds the writer lock`. Two callers touching
  one run in the same moment no longer turn a millisecond overlap into a
  refusal a human has to act on; a holder that keeps the lock past the
  bound is refused in the same words, and nothing runs unlocked. Only a lock
  another owner holds is retried; a file system that cannot grant one is
  reported at once, as `Run lock cannot be taken here`, where it used to be
  called busy. Tests that hold a lease and expect the refusal now see it
  after the bound; the bound is `review_store.LEASE_RETRY_SECONDS`, read
  when the lease is taken.
- Added: `attune-harness memory serve [--limit N] [--chars N]`, the recall
  digest as compact plain text for a session-start hook: a header with the
  count, the hydration stamp and the host, one line per curated node, and a
  footer saying the memory is untrusted evidence and how to read one node or
  search. Node lines are dropped from the end to fit `--chars` and the header
  then says how many are shown. It fails open: with no digest, for any reason
  from a missing `redis` section to an unreachable server, it prints one
  `skipped` line on stderr, nothing on stdout, and exits 0; a console that
  cannot encode a character gets a replacement, never a traceback. The
  installed checks confirm the fail-open path on every platform.
- Tooling and docs for the review loop: `scripts/review_prep.sh <branch>`
  makes the read-only archive a different-model review works from, the diff
  against the base and a mutation-table scaffold; `docs/review-findings.md`
  logs what each of the fourteen reviews so far found that the author had
  missed, sorted into eleven classes; `docs/windows-traps.md` records the
  five Windows differences that cost a finding or a failed job in September
  2026, with the fix for each, and the review brief points at both.
- Qualified: the memory verbs from an installed wheel, the third and last
  step of native memory Task 4 (D18). Every platform job installs the
  `redis` extra with a new `requirements-redis.lock` and, with no server,
  confirms that `memory redis status` and a Redis-backed scratch report
  unreachable, that the file scratch store round-trips, and that nothing is
  written to it when Redis is refused; the release gate's offline check does
  the same with the extra absent, where the report names the extra. The CLI
  guide gains a Memory section documenting the config's `redis` and
  `scratch` sections, the verbs, and the statuses.
- Added: `attune-harness memory scratch capabilities|stash|retrieve|forget|keys`,
  working memory behind one small backend interface, the second step of
  native memory Task 4 (D18). Values are JSON up to 64 KiB under keys of up to
  128 characters, with an optional time to live. Two backends, chosen once at
  startup from the memory config's `scratch` section: a stdlib file store in
  the base, one file per key under a directory the config names, which
  declares neither sharing nor signals; and, with the `redis` extra, a Redis
  store under `attune:harness:scratch:<namespace>:`, outside the keyspace a
  hydration rebuilds, which declares sharing across processes and machines.
  A configured Redis that cannot be reached makes scratch `unavailable` and
  is never replaced by the file store; no `scratch` section means `disabled`.
- Added: `attune-harness memory redis status|digest|related|node|search`,
  behind a new `redis` extra (`redis` 5.3.1), the first step of native memory
  Task 4 (D16, D18). It reads the Redis Stack keyspace a hydration keeps warm,
  `attune:memory:*` with the `idx:attune_memory` index and the `recall_digest`
  and `recall_related` functions, and issues no write. Every answer is an
  evidence packet with an authority binding (host, index, hydration stamp)
  and the untrusted-evidence guidance; the `text` body of a file, lesson or
  rule pointer is never served, a curated node's own record is what its reads
  return. Every id `search` hands back is one `node` accepts, bare for a
  curated node and family-qualified for a pointer; `related` follows the
  hydration's function and refuses a lesson or rule id rather than answering
  that it does not exist. The backend is chosen at startup from the memory config's
  `redis` section (a URL or the variable that holds it, an optional password
  variable); a configured Redis that is unreachable, or without the index or
  the `attune_memory` function library, is `unavailable` with the reason,
  nothing is diverted to a file, and no `redis` section means `disabled`.
- Changed: `pip install attune-harness` now installs what the review, test,
  acceptance and MCP journeys need: `attune-forms`, `attune-verify`,
  `attune-rag`, `mcp` and `tiktoken`, pinned exactly, where before each was an
  extra a user had to know to ask for (D15). `voyage` and `memory-native` stay
  extras because they make paid calls. The old extra names `verify`, `rag`,
  `review`, `mcp` and `tokens` still install as empty extras until 1.0, so an
  existing command line keeps working. Every dependency still loads on first
  use through the same gate, so a wheel installed without its dependencies
  reports each missing piece instead of failing; the report for a piece of the
  base now gives the reinstall command rather than naming an extra. One
  consequence, decided with eyes open (D15, amended): Harness pins the MCP
  SDK's 2.x line and attune-ai its 1.x line, so the two cannot share one
  environment, and `pip install attune-harness` over attune-ai replaces its
  SDK and exits 0. The README leads with an isolated install (`pipx`, `uv
  tool`), and `mcp-serve` prints a notice on stderr when it starts beside an
  attune-ai whose MCP requirement this install does not meet.

## 0.3.0

Spec support is Harness's own, alpha. The plan reader, the state reader and
writer, the path validator, the command workspace host and the Spec adapter
are carried from Attune AI and adapted, and `plan --accept` runs with the
`review` extra and no Attune AI installed. The two modules that plugged
Harness into Attune AI's plugin registry and MCP server are removed;
`attune-harness mcp-serve` serves repository evidence over MCP. Interfaces
may still change before 1.0; the README's qualification table says what is
and is not covered.

- Changed: `plan --accept` no longer needs Attune AI. The bridge hosts the
  decision with Harness's own `command_workspace` and `spec_workspace`, the
  fourth and last step of Task 3 of the spec authority, so the runtime import
  check's known list is down to `memory_context.py`. What acceptance needs is
  the `review` extra, which supplies the forms package that renders the
  decision; without it the command reports the install hint. Two events, a
  render and an accept, are now written beside the task's `decision.json` in
  `workspace-events.jsonl`; they never carry the action nonce, and a sink
  that fails never blocks the decision. The task gate is exercised in CI with
  Attune AI blocked: two processes against one task directory end with one
  acceptance, and every wired action is refused without its nonce, on a
  drifted view, when replayed, and without confirmation where the view
  requires it. The connected journey's Spec control runs in CI for the first
  time for the same reason.
- Added: `attune_harness.spec_workspace`, the Spec adapter that gives each
  stage, action and event of a spec its meaning: `SpecWorkspaceAdapter`,
  `SpecWorkspaceState` and the receipt types, carried from Attune AI as the
  third step of Task 3 of the spec authority. Every import is now Harness's
  own, including the test-evidence check by relative import, which ends the
  one place the two products imported each other. The forms package loads on
  first use, so importing the module needs nothing installed. One behaviour
  differs: a resume refuses a plan whose state comment Harness's reader could
  not use, where the original's parser read it and a later check failed;
  without the refusal the plan would restart from zero. Comments the reader
  refuses itself, such as one without a `schema_version`, are refused with
  the reader's own words, as before. Nothing in Harness calls it yet; the
  bridge switches to it in the next step.
- Added: `attune_harness.command_workspace`, the host that turns an adapter's
  state into one rendered, one-shot decision: `CommandWorkspaceHost`, the
  adapter protocol, the projection, transition, record and render types, and
  `jsonl_event_writer`. Carried from Attune AI as the first step of Task 3 of
  the spec authority. Three things differ. Its two events, a render and an
  accept, go to a sink the caller names instead of Attune AI's telemetry file,
  and never carry the action nonce. A workspace that reaches a terminal state
  is evicted, with its id remembered so a replay is still refused, so a
  long-lived host no longer grows without bound. The forms package loads on
  first use at the pinned version, so importing the module needs nothing
  installed. Nothing in Harness calls it yet.
- Added: `attune_harness.spec_intake`, the four names the Spec workspace
  takes from Attune AI's spec intake: `OTHER`, `existing_spec_slugs`,
  `area_candidates` and `compose_spec_contract`, carried as the second step
  of Task 3 of the spec authority. The intake form, its provider
  registration and the line that wrote into a global registry at import
  time stay behind. `area_candidates` now looks at every package under
  `src/`, not only `src/attune/`. Nothing in Harness calls it yet.
- Changed: importing a legacy plan no longer needs Attune AI. `spec_bridge`
  parses the plan's task blocks with Harness's own `spec_tasks` reader, so the
  read path is exercised in CI, where Attune AI is not installed. Output is
  identical on every existing plan; on malformed input the new reader is
  stricter and decodes entities, where the old one was regex-only. The file is
  read once, and a task block that is not well-formed XML is refused with what
  to do, where before the parser's own error escaped. Accepting a plan still
  needs Attune AI's Spec runtime until Task 3.
- Added: `attune_harness.spec_state`, the reader and writer for the execution
  state a plan file carries in its trailing `<!-- spec-state: ... -->` comment:
  `SpecState`, `load_state`, `save_state`, `clear_state` and
  `find_resumable_plans`, carried from Attune AI as the third step of making
  spec support part of Harness. Three things differ from the original. A
  `schema_version` other than 1 or 2 is refused with what to do next, where
  the original loaded any version. The plans directory is an argument with no
  default. And the comment must be the single trailing one, which is what the
  Spec bridge already requires, so the writer never produces a file the reader
  refuses; the writer also refuses a result over the 65,536-byte plan limit
  rather than writing one the reader would refuse. Plans found by
  `find_resumable_plans` come back in file name order. Nothing in Harness
  calls it yet.
- Added: `attune_harness.spec_tasks`, the reader for the `<task>` blocks a plan
  file is written in: `DecomposedTask`, `parse_tasks` and `read_spec`, carried
  from Attune AI as the second step of making spec support part of Harness. It
  uses the standard library XML parser and adds no dependency: only the
  `<task>` region of a file is parsed, never the file, so an entity declaration
  can never reach the parser, and the hostile cases in its tests show nothing
  expands. Output is identical to Attune AI's reader for every existing plan.
  Nothing in Harness calls it yet.
- Added: `attune_harness.paths.validate_file_path`, carried from Attune AI's
  path validation as the first step of making spec support part of Harness. It
  resolves a path and refuses one that leaves an allowed directory or lands in
  a system directory. On Windows it compares whole path components from the
  drive's root, where the original matched substrings and so refused legitimate
  paths such as `C:\repo\etc\plans\x.md`. Nothing in Harness calls it yet.
- Changed: an input over its size limit is refused with a fuller message. It
  now gives the file's actual size beside the limit and says the file was
  refused whole, because Harness never shortens an input to fit. The error is
  still a `ValueError`, so the `error.type` in the CLI's JSON output is
  unchanged. For an imported plan, the message adds what to do: split it into
  smaller plan files and import each one as its own task. That check now runs
  before Attune AI is loaded, so it is reported either way. The 65,536-byte
  limit for plans is unchanged.
- Removed: `attune_harness.attune_bridge` and `attune_harness.memory_bridge`, the
  two modules that plugged Harness into Attune AI's plugin registry and MCP
  server. Harness is replacing Attune AI and no longer plugs into it; two other
  modules still import it and are being reworked. Nothing else in the package
  used the removed modules. For repository evidence over MCP, use
  `attune-harness mcp-serve`, which serves the same retrieval session. The
  `memory` command is unchanged; memory had no other MCP surface, and one served
  by Harness itself is not written yet.

## 0.2.0

Adds an experimental Windows effects backend, alpha. `fix` and the work runtime
now run on Windows instead of refusing. This is new code passing its own native
tests, not a qualified platform: read the limits before using it on a checkout
you care about.

- Added: a Windows file-effects backend (`windows-existing-utf8-v1` and
  `windows-feature-effects-v1` profiles). It is used only on a Windows host; off
  Windows the module is inert and reports the feature as unavailable. It works
  through retained handles and requires a fixed local NTFS drive-letter volume,
  so network, removable and non-NTFS volumes are refused. Reparse points, files
  with more than one hard link, alternate data streams and path aliases are
  refused before writing. Files are limited to 64 KiB and the checkout to 1,000
  entries and 16 MiB.
- Added: explicit probe environments on Windows. `process.invoke()` passed an
  `environment` only on POSIX and raised `NotImplementedError` on Windows. It
  now reaches the supervised child, and keys that collide ignoring case are
  rejected.
- Tested: the backend's native tests pass in CI on windows-2025 with Python 3.10
  and 3.12 and on windows-2022 with Python 3.12. They cover replacing existing
  files, observing a lost acknowledgement, retrying only when the original bytes
  remain, creating a directory and a file, and an accepted `fix` running a
  failing then passing probe.
- Not qualified: deletion and renames as effects, files with their own ACL or
  nonstandard attributes, process-crash recovery, concurrent writers, power-loss
  durability, and any run against a real project. The
  [design note](docs/design-windows-effect-backend.md) lists the rest. POSIX
  behavior, profiles and saved records are unchanged.
- Fixed: the README's link to the September 18 native comparison results
  returned 404, on PyPI and on GitHub. The document and the receipts it cites
  are now in the repository.
- Changed: a clean checkout can run the test suite. The receipt fixtures the
  tests read are now tracked; tests that need Llama-derived files, which are not
  redistributed, skip with a reason.

## 0.1.0

First PyPI release, alpha. The 0.1.0rc1 runtime plus one fix, with the final
version, a README written for the PyPI page, and per-command usage moved to
docs/cli-guide.md. Qualified on Ubuntu, macOS and Windows with Python 3.10 and
3.12. What is and is not qualified is listed in the README.

- Fixed: on Windows, saving a run record failed with `PersistenceError` whenever
  another process (`status`, an indexer, antivirus) briefly had `record.json`
  open, which stopped all further dispatch in the session. The save now retries
  the replace for up to two seconds before failing closed as before. A record
  held open for longer than that still fails the run.

## 0.1.0rc1

Provisional TestPyPI publishing rehearsal using the qualified release-gap
runtime snapshot. This checks package distribution, clean installation and CLI
behavior. Windows feature-effect support and final native release journeys
remain under qualification; this is not the production release.
