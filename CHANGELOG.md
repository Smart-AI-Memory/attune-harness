# Changelog

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
