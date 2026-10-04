# Attune Harness 1.3.0 release notes

**Prepared candidate, not published.** Merge and publication remain held for the
October 6–11 window and Patrick's release decision. The installation command and
version-pinned README links become usable after publication.

`1.3.0` lets `plan` and `fix` start from a command. Until now, both verbs
needed a file nobody wrote for you: `plan --request` needed a work request
with a frozen effects manifest, and `fix` needed a trusted probe. `init --for`
writes each one, checked by the verb that reads it (O-70). Use an isolated
environment:

```sh
pipx install 'attune-harness[all]==1.3.0'
```

The v1 compatibility contract holds. Envelope keys only grow: `init` adds
`files`. Existing defaults and exit codes are unchanged, and
`docs/deprecations.json` stays empty. One argparse effect is new: `init --f`,
`--fo` and `--t` are now ambiguous abbreviations. Spell `--force`, `--tests`
or `--task-dir`.

## What is new

- **`init --for fix`** writes `probe.json`, the trusted probe `fix` reads. It
  runs the named tests with pytest. Before writing, `init` runs the same freeze
  `fix` runs, as a dry run, so anything `fix` would refuse is refused first, in
  the same words. It runs nothing. Its `next_action` is the `fix` preview.
- **`init --for plan`** writes a work request `plan --request` accepts as
  written: the goal, the scope, the named tests as acceptance, one task,
  distinct worker and reviewer, and an effects manifest frozen over the
  checkout. It goes beside the task directory, as `<task-dir>.work.json`,
  outside the checkout the manifest freezes. Writing it accepts nothing: the
  preview and `--accept` stay separate steps. A refused `init` removes what it
  wrote.
- **Example participants** in `examples/starter/participants.json` finish both
  journeys with no model call. They are example code, not a profile: `lead`
  applies one declared replacement and `reviewer` approves without judging.
  They need `python` on PATH.
- **The Claude Code plugin comes from a release tag.** The marketplace stays
  pinned to `v1.2.0` during preparation. Runbook step 9 moves it to `v1.3.0`
  and its verified commit only after that tag exists. This candidate does not
  advertise an unpublished plugin through the marketplace.
- **`build` says when its participants cannot build.** Every profile `init`
  writes is for review, so `build` refuses a plan made with one. The refusal
  now names those participants, comes before any dispatch flag is asked for,
  and says to plan again with participants that can propose files;
  `init --for plan` says so up front (O-77). The starter journeys run from a
  checkout of this repository with a virtual environment activated, because
  `examples/` is not in the package.
- **Symlink refusals name the path to use.** On macOS, `/tmp` and `/var` are
  symlinks, so a task directory under them is refused. The refusal now says
  which link and what to use instead (O-76).

## Additional changes included from main

- **Shared source review and roundtable:** bounded preparation, explicit dispatch,
  inspection and abandonment over immutable selected source bytes. Retained
  evidence distinguishes requested and reported model identities and preserves
  unresolved outcomes. These tools do not authorize their own model calls.
- **Consultation evidence and Antigravity:** inspect frozen cited lines and retain
  checkpoint-bound citation judgments. Explicit Antigravity seats record model,
  effort and correlated process evidence; Codex seats can specify reasoning
  effort. This does not establish tool isolation or native plan/build parity.
- **Read-only graphical companion:** `python -m attune_harness.gui --task PATH`
  displays existing task-owner snapshots over a loopback capability boundary.
  It has no write or execution endpoint. GUI M1 is complete; M2 is underway;
  M3/M4 and production GUI qualification remain open.
- **Reliability:** malformed native-memory content entries now retain structured
  refusal evidence. Starter failures clean up their own partial writes, forced
  probe backups count toward the entry bound, and Claude refusal classification
  distinguishes completed refusals from uncertain supervision failures.
- **Packaging and diagnostics:** Codex onboarding no longer assumes unbundled
  helper scripts; qualification retains timing and slow-stack evidence. Windows
  supplemental coverage has temporary measurement headroom, not broader platform
  qualification. The Windows-traps guide and compact Shepherd reference are added.

See [model consultation](model-consultation.md), [the GUI specification](specs/graphical-companion/README.md),
[Windows guidance](windows-traps.md) and [Shepherd](journeys/shepherd.md).

## The two journeys

The CLI guide's `plan` and `fix` sections open with blocks that CI runs as
printed on the installed wheel. The `fix` block runs on POSIX only, as `fix`
is qualified.

```sh
attune-harness init --for fix --project /path/to/repo --scope calc.py \
  --interpreter /path/to/venv/bin/python --tests tests/test_calc.py
```

See [Plan and build](cli-guide.md#plan-and-build) and
[Scoped repair](cli-guide.md#scoped-repair).

## Known limits

- `--test-root .` is still refused (O-76).
- Windows native-memory, `fix` and `test` limits remain as documented; isolated
  backend checks do not broaden the supported command surface.
- Native-memory SDK/live model quality is not established by offline tests.
- Fresh-session memory observations (S3), a qualifying non-programmer walkthrough
  (S6), and installed migration observations (S9) remain open.
- The Claude marketplace explicitly lists Harness, `cross-review` and `smart-test`.
  The bundled `roundtable` skill is included in Codex packaging but is not selected
  by that marketplace entry. A tag-pointer update alone does not add it.
- Research and general opportunity mining are not production GUI capabilities;
  retained prototypes are not installed-product qualification.

## Evidence

This preparation integrates main through `85bc4da` (#223). The PR handoff records
fresh candidate checks. Earlier library results do not qualify the versioned
release artifact by themselves. The publish run and 1.3.0 PyPI hashes do not yet
exist; they must be recorded during release under the [runbook](release-runbook.md).
The [project plan](project-plan.md#where-each-gates-evidence-is) retains the 1.2.0
baseline and explicitly open observation gaps.
