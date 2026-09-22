# Session starter: attune-harness, after 2026-09-19

Paste this into a new session, or point the agent at it. It says where everything
stands and what to read. It authorizes nothing.

## Read first

1. `docs/handoffs/first-pypi-release-2026-09-19.md` — the release, step by step,
   including where the TestPyPI rehearsal stopped and the first command to run.
2. `docs/specs/native-memory/scoping.md` — direction N1 to N8 and a nine-task ladder
   for making memory native to Harness.
3. `docs/specs/shared-memory-adoption/verification.md` — what the accepted memory
   adoption actually delivers, and its limits.

## State in one screen

| Thread | State |
|---|---|
| First PyPI release | Release commit `afa415f03d43e2321545dd106072d10b1b41eac0`, version `0.1.0rc1`, licensed (Apache-2.0), qualified on Ubuntu, macOS, Windows x Python 3.10 and 3.12, gated dry run passed. **TestPyPI rehearsal complete:** `0.1.0rc1` published to TestPyPI by run 35476747591 (evening of 2026-09-19). Nothing published to production PyPI. Next is the production path in the release handoff |
| Publishing route | `publish-pypi.yml` only. Production accepts final versions, TestPyPI accepts `rcN`. The `testpypi` environment allows only `codex/testpypi-rc-20260918` and needs Patrick's approval. No `pypi` environment exists yet. Never `gh run rerun --failed` on this workflow; dispatch fresh (see the release handoff) |
| Shared-memory adoption | Accepted, five tasks, revision 23. Task 5 installed qualification reproduced first-hand on 2026-09-19 (151 and 24 passed). Delivered scope is read-only; done-criterion in `requirements.md` amended to say so |
| attune-ai side of adoption | Committed and pushed on `codex/shared-memory-adoption` in the `attune-ai-memory-adoption` worktree. Now a transitional bridge, not a merge goal |
| Native memory | Scoping note only. No spec, no tasks started |
| Receipts | `docs/receipts/` is gitignored. Snapshot tarball from 2026-09-19 is in iCloud, SHA-256 `9c0bfb206d137017c72a95db55c9dafc6015752549845e747f3027ab2696b591` |
| attune-ai security alerts | soupsieve bumped to 2.9 via #2532; zero open alerts on 2026-09-19 |

## Branches that matter

- `wip/local-snapshot-2026-09-19` — working snapshot. Holds today's spec edits, the
  scoping note, `0.1.0.dev14` (not a release version), license and metadata.
- `codex/testpypi-rc-20260918` — the only branch allowed to deploy to `testpypi`.
- `release/0.1.0rc1-packaging` — RC line plus license, manifest and metadata.
- `main` — behind the working line; carries the inert workflow registration stub.
  Its `.gitignore` lacks some snapshot-branch entries, so avoid `git add -A` there.

## Decisions that are Patrick's

- Approving the TestPyPI upload, and later the production upload.
- Whether `0.1.0` final is right while the README says "not production-ready".
- Whether to open the native-memory spec, and whether a manual review of existing
  correction memories comes first.

## Open follow-ups

- README: relative links and workspace-specific passages will read badly on PyPI.
  A replacement is drafted at `docs/handoffs/README-draft-0.1.0.md`, with the old
  usage sections moved to `docs/cli-guide.md` (uncommitted on the wip branch).
- Opportunity log: test-named product modules entry needs an O-number.
- Native memory open questions: pattern audit-log usage, recurrence signals,
  owner-authored rules versus forged instructions, retirement signal for attune-ai.

## Working notes for the next agent

- Patrick's shell is zsh. In pasted blocks write `"${VAR}:..."` with braces.
- `gh` and `git` pagers trap short output. `GH_PAGER=cat` is set per command in the
  blocks used today; `core.pager` is now `less -FRX` globally.
- Check for an existing process before adding one. On 2026-09-19 an ungated publish
  workflow was added without noticing the gated one on main; it was removed the same
  day (PR #4).
- Always dry-run the release workflow on a new SHA before a real run.
