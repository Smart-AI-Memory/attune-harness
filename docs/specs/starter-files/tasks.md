# Starter files: tasks

**Status: draft, September 29, 2026. Waiting on Q1–Q6 and spec approval.**
Requirements are in [design.md](design.md), and questions Q1–Q6 are in the
[README](README.md). Nothing here is authorized until the spec is approved.

## Order

T1 comes first, as in the first-run journey, so every later done condition is
a CI result. T2 is the smallest change that finishes a verb. T3 depends on T4
to finish a build in CI, so the two can be one PR if that reviews more easily.
T5 is independent. T6 closes out.

- [ ] **T1: the two journeys, red first (R5).**
  Scope: `plan-starter` and `fix-starter` blocks in `docs/cli-guide.md`,
  their cases in `tests/test_cold_start_journey.py` as strict xfails naming
  T2–T4, and the required-tag set.
  Done when: both run in the six installed-wheel jobs and fail as expected.
  Size: one PR, no `src/` change.

- [ ] **T2: `init --for fix` (R1).**
  Scope: `init_cli.py`, `tests/test_init_cli.py`, the surface fixture, the
  `init` rows in `docs/envelopes.md`, and the changelog.
  Done when: `fix-starter` passes and `init` without `--for` is unchanged.
  Size: one PR, `src/`, different-model review.

- [ ] **T3: `init --for plan` (R2).**
  Scope: `init_cli.py` calling `work_effects.freeze`, the staleness
  `next_action`, and tests.
  Done when: the written request passes the owners' validators and previews
  in `plan`, and `plan-starter` passes once T4 lands.
  Size: one PR, `src/`, different-model review.

- [ ] **T4: the example command worker (R3).**
  Scope: `examples/starter/`, used by `plan-starter`.
  Done when: `plan-starter` passes on all six jobs.
  Size: small, no `src/` change.

- [ ] **T5: symlink refusals and the guide's paths (R4).**
  Scope: `task_contract.safe_storage`, `repair.root_handle`, the resolved-root
  check in `work_contract`, their tests, and `docs/cli-guide.md`.
  Done when: each refusal names the resolved path, and the guide has no
  `/tmp` task directory and no 1,000-entry limit.
  Size: small, `src/`, different-model review.

- [ ] **T6: close out and prepare 1.2.0 (Q6).**
  Scope: the spec's status lines, the opportunity log entries for O-70 and
  O-76, and the release notes.
  Done when: the spec is marked complete and a 1.2.0 prepare PR is open.
  Publishing stays Patrick's.
  Size: docs only.

## Estimate

Six PRs, three of which touch `src/`. That is about two sessions, with T3 the
largest because of the freeze and its tests.
