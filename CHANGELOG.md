# Changelog

## Unreleased

- Changed: an input over its size limit is refused with a fuller message. It
  now gives the file's actual size beside the limit and says the file was
  refused whole, because Harness never shortens an input to fit. The error is a
  new `InputTooLarge`, a `ValueError`, so existing handlers keep working. For an
  imported plan, the message adds what to do: split it into smaller plan files.
  That check now runs before Attune AI is loaded, so it is reported either way.
  The 65,536-byte limit for plans is unchanged.
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
