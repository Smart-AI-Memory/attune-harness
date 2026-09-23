# Release 1.0.0: the requirements, and what waits

Draft of September 23, 2026, the evening Task 4's steps (a), (b)'s rename
and (c) merged (#106, #107, #108), for [the plan's Phase 4](../../plan-1.0.md)
and the release it ends in. It answers the one question the plan leaves
open: of everything the repository has promised, in the README, in the spec
authority's rulings and in the older planning documents, which promises are
requirements of 1.0.0, and which are aspirations that belong to a later
milestone. Like the design notes before it, it puts what was read from the
code first, then the requirements, then the decisions that are Patrick's.
Nothing here is authorized until he rules; the rulings go in a dated addendum
beside this file, numbered on from D24. Ruled the same evening:
[D25](addendum-2026-09-23.md), the ten decisions, with the freeze's list and
October as the month; the deprecation's distance from 1.0.0 is raised there
and not yet ruled.

## Two readings of 1.0.0

The README says what 1.0.0 means: interfaces, configuration formats and CLI
commands may change before 1.0, and what is and is not qualified is listed,
not implied. So 1.0.0 is the release after which those three things change
only through a deprecation, with the qualification table still honest. That
reading is realistic. The plan's remaining tasks deliver it, and the count
below is its cost.

D1 gives a second reading. Patrick's stated plan is to deprecate attune-ai as
soon as he can release a stable Harness, "sometime during October-November
after a period as release candidate". The README also says, today, that
attune-ai "is still where cross-session memory, the Claude Code plugin and
the multi-agent workflows live" and that "Harness does not replace those
today". Memory has since gone native (Phase 2, 0.5.0). The Claude Code plugin
and the multi-agent workflows have no task in the plan, no design note and no
fixture. Under the second reading, 1.0.0 waits for two things nobody has
written down, and its size is unknown.

The first decision below recommends separating the two: 1.0.0 is the stable
core the README describes, and the deprecation of attune-ai is a later
milestone with its own parity list, whose first two rows are the plugin and
the workflows. Everything that follows is written under that split, and the
decision says what changes if Patrick rules the other way.

## What the code and the plan say today

Read against `origin/main` at `03a8e1d` (#108), the evening of September 23.

**The plan.** Twenty tasks: nine done, three in progress, eight not started.
What remains, with the plan's own cycle estimates; a cycle is one design note
or one reviewed pull request with its suite, review and platform runs.

| Task | State on September 23 | Cycles left |
|---|---|---|
| 1.4 dogfood `memory serve` | The hook has run since September 22; the observations are not written down anywhere under `docs/` | 0 |
| 3.1 the journey native | Three of four pull requests merged; step (b)'s stages under D24 mapping 3 are in flight on `feat/task4-b2-stages` | 1 |
| 3.2 other projects' spec state | Not started; no fixture from another project exists, nothing writes a conversion receipt | 1 to 2 |
| 3.3 the serving path | Not started; gated on 1.4's observations (D20.10); `memory serve` has no `--for` mode and applies no `status:active` filter | 2 to 3 |
| 3.4 the versioned store | Not started; the scratch record is `schema_version` 1 with no `format`, `writer` or `expected_version` | 1 to 2 |
| 4.1 the interface freeze | Not started; the golden table (#73) is the precursor; the five empty extras are still declared; the saved-state fixture (D25.2) is the third cycle | 3 |
| 4.2 Windows | Ruled (D20.8); the README's table already states the limit; the written decision and the qualification table are the cycle | 1 |
| 4.3 executable plugins, implementation | Not started; the spec is approved (D22), four cycles by its own count | 4 |
| 4.4 end the memory transition | Not started; `memory_context.py` still imports the adapter inside `reader == 'adapter'`, the one allowed exception | 1 |
| 4.6 the non-programmer walkthrough | Not started; nobody named | 1 |
| 4.7 the release | Not started; `main` is `0.6.0.dev0` | 1 |

Sixteen to nineteen cycles, before the loose ends in S8 and the release
candidate period. Done and not in the table: Phase 1 entire, Phase 2 entire,
3.5 (the plugins spec, D22) and 4.5 (the hygiene row: all nine pull requests
merged on September 23, #89 to #100 without #96, #97 and #98).

**The public surface.** Twenty-eight top-level verbs in `cli.py`, `memory`
carrying thirteen operations and `extension` seven actions. Seventy-one
envelope rows pinned by `tests/test_golden_envelopes.py` and
[the envelope table](../../envelopes.md): 55 success, 6 refusal, 9
unavailable, 1 disabled, and the gaps the table itself records: no
`schema_version` on `plan`, `build`, `status` for work and `memory scratch`;
no `status` on `code-config`, `triage-check`, `repair-economics` and
`github-checks`. Nine extras in `pyproject.toml`: `tokens`, `verify`, `rag`,
`review` and `mcp` empty, which the README promises are removed at 1.0;
`redis`, `voyage`, `all` and the experimental `memory-native`. A Python API
the README opens with, `run`, `Task`, `Output`, `Check` and `Receipt`, that
no document names as frozen or not. Two protocol surfaces with local
receipts, MCP (the 2025-11-25 and 2026-07-28 profiles) and A2A 1.0. An
extension manifest at `schema_version` 1, data-only, to which 4.3 adds
`grants`, `declares` and the `run` binding as version 1's vocabulary (D22.3).
Every refusal text is a contract by D20.1.

**attune-ai on the path.** `tests/test_no_attune_runtime_import.py` has an
empty `KNOWN` set and one `FALLBACK`, `memory_context.py`, whose import of
`CompatibilityAdapter` is allowed only inside the `reader == 'adapter'`
branch. The adapter was never released by attune-ai; the differential that
proves the native reader's parity runs only where its checkout exists. The
formats the native reader reads are attune-ai's: `findings.jsonl`, the
personal and curated Markdown with sidecars, and the Redis keyspace that
Patrick's own hydration writes.

**What the README labels.** Status "0.5.0, alpha" and the classifier
`Development Status :: 3 - Alpha`; native planning and building
experimental; `fix` on Windows experimental and `test` there unqualified;
"this is not a security sandbox"; remote authentication, arbitrary
executable plugins and automatic host installation unqualified; the native
memory reader POSIX-only; `memory-native` experimental and never exercised
in CI; `ship` and `reflect` "planned routes and do not exist yet".

**CI and the release path.** The platform matrix builds and installs the
wheel on macOS, Ubuntu and Windows with Python 3.10 and 3.12; one Ubuntu job
runs the full suite; the release gate installs the wheel with its base
dependencies and without them, and runs the journey on the first and its
refusal proof on the second (#108). Two
things outside the repository stand in the way of a release candidate: the
`testpypi` environment's allowed branch names a branch that no longer exists
([runbook](../../release-runbook.md)), and the publish workflow's action
pins moved three major versions in #93 with no `publish=false` rehearsal
since.

**Promises in the older planning documents that the plan does not carry.**
[The readiness direction](../../harness-release-readiness-direction.md)
asks for an inventory mapping every intended capability to its value,
callers, roles, decisions, outputs and recovery, and rules that no feature
is subtracted. [The journey map](../../release-journey-map.md) lists `ship`
and `reflect` among the human verbs. [The phased plan](../../harness-phased-plan.md)
records agents, teams and the round table as product features to connect,
migration milestones, and a held-out comparison of the collaboration
hypotheses. [The October plan](../../october-release-plan.md) budgets eight
phases in working tokens for an October 1 review. The plan to 1.0.0 counts
cycles instead and names four exclusions; these promises are in neither
list. Each is placed below, so that its absence from 1.0.0 is a ruling and
not an omission.

## Requirements of 1.0.0

Each requirement names its acceptance evidence, the plan tasks that deliver
it, the cycles, and where it stands. Evidence means what the plan means by
done when: a receipt, a test, a table row, a document. They are numbered S1
to S8, S for stable, so that they do not collide with the R-numbers of the
spec authority and the plugins spec, which this note cites.

**S1, the surface is frozen and written down.** Delivered by 4.1 and 3.4.
Evidence: the envelope table complete, with `schema_version` on the four
envelopes that lack it and `status` on the four that lack it; every
configuration format listed with its version, the memory config (`roots`,
`redis`, `scratch`, `reader`), task and run records, plan state (schema
versions 1 and 2), and the scratch record with its `format`, version and
`writer` (D21.6); the twenty-eight verbs listed; the five empty extras
removed; and a deprecation path written down, what a change to any of these
after 1.0.0 requires before it ships. The Python API's place in the
contract is decision 2. Four to five cycles, the saved-state fixture
counted (D25.2); not started.

**S2, nothing from attune-ai on any path, and its formats read natively.**
Delivered by the rest of 3.1, by 3.2 and by 4.4. Evidence: the R2 journey
green in the release gate (done, #108); step (b)'s stages wired under D24
(in flight); a conversion receipt per imported plan and a fixture from
attune-ai's own `.claude/plans/` (D20.3); `KNOWN` and `FALLBACK` both empty,
which is decision 5. Three to four cycles.

**S3, memory is served, and corrected memory stops being served.**
Delivered by 3.3. Evidence per D21.4 and D21.5: the SessionStart digest with
its provenance line, a node absent from `status:active` or carrying a
`wrong` verdict not served, and the `--for PROMPT` mode for a prompt hook.
Two to three cycles, the first gated on Patrick's observations from the
week of `memory serve`, which are decision 7.

**S4, executable plugins implemented and qualified.** Delivered by 4.3, as
D6 ruled ("need it") and D22 approved. Evidence: the plugins spec's R1 to
R7 with receipts on macOS, Ubuntu and Windows, and the README's protocols
row changed last. Four cycles, and the critical path: the first thing in CI
that depends on `gpg` on three runners, and a child environment the Windows
jobs have not met. Whether it stays on the 1.0.0 path, and its order against
the freeze, is decision 4.

**S5, the qualification table is honest and Windows is a written limit.**
Delivered by 4.2. Evidence: the README rows for `fix`, `test` and the memory
reader on Windows say documented limit with WSL2 as the route (D20.8), the
qualification guide says the same, and nothing in the table's qualified
column lacks a receipt. One cycle.

**S6, a person who does not program can run the installed journey.**
Delivered by 4.6, the spec authority's Task 6 and its R6: observed, not
inferred, during the release candidate period, from the PyPI artifact. Who
walks through is decision 8. One cycle.

**S7, the release mechanics prove the artifact.** Delivered by 4.7 and by
two steps outside the repository. Evidence: the `testpypi` environment
repointed by Patrick; a `publish=false` rehearsal green on the new pins
before any release candidate; `1.0.0rc1` on TestPyPI through the runbook's
`testpypi` target; a release candidate period with the exit condition of
decision 3; then 1.0.0 with the runbook's receipts, and `main` reopened at
`1.1.0.dev0`. One cycle plus two dispatches.

**S8, the loose ends the documents already promise.** One hygiene pull
request: `scripts/check_code_rag_host.py` and its test removed, which
[the qualification guide](../../qualification.md) calls separate work; the
three check scripts that lost their caller when `qualify_pilot.py` was
deleted, folded into `check_installed.py` or removed; O-51's TestPyPI
receipt no longer naming a deleted script; O-53 closed by 3.1. One cycle.

Seventeen to twenty cycles in all, then the release candidate period.

## What waits, and why

Each row is a promise the repository makes somewhere, placed after 1.0.0
with the reason. Under the readiness direction's rule, nothing here is
removed: each stays in the repository with its evidence, and is listed so
that leaving it out of 1.0.0 is a ruling and not an omission.

| Promise | Where it is made | Why it waits | Where it goes |
|---|---|---|---|
| The Claude Code plugin, in Harness | The README's "Harness and attune-ai" section names it as attune-ai's | No design, no task, no fixture; a parity list is the first deliverable | The deprecation milestone (decision 1) |
| Agents, teams and the round table, connected and reliable | The readiness direction and the phased plan | Same: the multi-agent workflows live in attune-ai and nothing in the plan carries them | The deprecation milestone (decision 1) |
| `ship` and `reflect` | The README's roadmap row; the journey map | A new verb after the freeze is additive and breaks nothing; the row's wording is the only change 1.0.0 needs | 1.x, additive (decision 6) |
| `fix` and `test` qualified on Windows; the memory reader on Windows | The README's table; D11 | Ruled a documented limit at 1.0 (D20.8) | After 1.0.0 |
| The corrections lifecycle (ladder 7) | The scoping note | Ruled outside 1.0 unless the dogfooding week brings it back (D21.9) | After 1.0.0, as a proposal |
| Remote A2A authentication | D6 | Deferred by Patrick; the local profile ships labeled local-only | After 1.0.0 |
| Native planning and building across providers and roles (plan/build Task 8) | D6 | Ships labeled experimental; two repetitions per role establish no rate | After 1.0.0, under its label (decision 9) |
| The `memory-native` extra activated for live memories | The README | Experimental, POSIX-only, never exercised in CI | After 1.0.0, under its label (decision 9) |
| The capability inventory | The readiness direction | O-04 tracks it; the plan's phases replaced the method with tasks and receipts; the maps are rewritten once, after 3.1 | The October 1 review |
| Specialist testing backends, the D, E and F groups, the eight token-budgeted phases | The October plan and the log | Opportunity work, not contract work; the log's October 1 review owns it | The October 1 review |
| Migration milestones and the held-out collaboration comparison | The phased plan | Superseded in part by the plan to 1.0.0; the comparison needs paid trials nobody has authorized | The October 1 review |
| An enforced review and a merge queue | The collaboration plan | Planned, not in force, and not the repository's to set up | After 1.0.0 |

## The path

Ordered by dependency; what shares a line may overlap.

1. Now: 3.1 step (b)'s stages (in flight); 3.2 and 3.4, which touch neither
   the plugins nor the serving path; 4.3's first cycle, signing, revocation
   and the capability fields, since the spec is approved; the `publish=false`
   rehearsal, a dispatch of Patrick's.
2. 3.3 once the observations are written down (decision 7).
3. 4.3's remaining cycles: the `run` binding and the bootstrap, Voyage
   behind the boundary, the Windows traps.
4. 4.1 the freeze, after 3.4's record and after 4.3's manifest fields, so
   that what is frozen is what ships (decision 4).
5. 4.4, 4.2 and R8, one cycle each, in any order.
6. `1.0.0rc1`: the version, the README's status line at release candidate,
   TestPyPI through the runbook. The release candidate period: 4.6 observed,
   the hook and the plugin dogfooded from the candidate, the findings-log
   rows for the period's pull requests, and the exit condition of decision 3.
7. 1.0.0.

The critical path is 4.3, four cycles with platform risk, and 3.3, gated on
an input only Patrick has. Both can start now: 4.3's signing cycle, and the
observations.

**A calendar, stated as an assumption.** Phase 2 took four reviewed pull
requests in a day and the overnight run of September 23 built ten; with
Patrick merging, three to four cycles a day is the measured pace. Sixteen to
twenty cycles are five to seven working days of building. Spread over the
sessions he can give it, 1.0.0 in October fits D1's window; decision 3
rules the month and nothing finer, and the sessions a week are still his to
name.

## Decisions for Patrick

1. **Separate 1.0.0 from the deprecation of attune-ai.** Recommended: yes.
   1.0.0 is the stable core the README describes; the deprecation is a
   later milestone with its own note and parity list, whose first rows are
   the Claude Code plugin and the multi-agent workflows, and whose ticks
   already include memory (Phase 2) and the spec authority (Tasks 1 to 5).
   If no: a Phase 5 for the plugin and the workflows goes before 4.7,
   unsized until it has a design note, and the calendar above is void.
2. **What the freeze covers.** Recommended: the README's three, the CLI
   verbs, the envelopes and the configuration formats, plus the Python API
   the README opens with (`run`, `Task`, `Output`, `Check`, `Receipt`) as
   named public; the MCP tool schemas and the A2A profile pinned by their
   protocol version and changed only with it; the extension manifest as a
   versioned schema whose version 1 is the data-only form plus 4.3's fields.
   Alternative: the three only, which leaves the Python API free to change
   and the README's first example unprotected.
3. **Dates, the release candidate period and its exit.** Recommended:
   `1.0.0rc1` when S1, S2, S4, S5, S7 and S8 have their evidence and S3 has
   at least the SessionStart filter; the period ends when 4.6 has been
   observed, two weeks of dogfooding from the candidate have produced no
   change to a frozen surface, and the findings-log rows are in; 1.0.0 in
   the month D1 names, October, with no finer date written anywhere.
   Patrick names the sessions a week he will give it, which turns the
   assumption into a plan.
4. **4.3 stays on the 1.0.0 path and precedes the freeze.** Recommended:
   yes, as D6 ruled. 4.1 follows 4.3's manifest and `run` binding cycles, so
   the frozen manifest is the one that ships; if 4.3 slips, 1.0.0 slips with
   it rather than freezing a manifest that 4.3 must then extend under a
   deprecation. Alternative: 4.3 lands in 1.1 as an additive change, which
   reverses D6's "need it" and would need Patrick to say so.
5. **What ending the memory transition means at 1.0.0.** Recommended: 1.0.0
   declares the attune-ai formats the native reader reads frozen as read,
   `findings.jsonl`, the document tiers with sidecars and the hydrated
   keyspace; the `adapter` reader and the `FALLBACK` exception are removed
   and the differential retires with them, the fixture staying as the
   contract. The plan's condition "once attune-ai stops writing" is dropped:
   Patrick's own hydration keeps writing the keyspace, and the native reader
   reads it. attune-redis's dependency on attune-ai and the `harness` extra
   are attune-ai's side of the line and are settled there.
6. **`ship` and `reflect`.** Recommended: they stay in the README's roadmap
   row as planned routes, reworded at 1.0.0 to say a new verb is additive and
   needs no deprecation. They are not requirements of 1.0.0.
7. **The `memory serve` observations.** The one input 3.3 waits on, and the
   one this note could not find written down. Recommended: Patrick's
   observations since September 22, in his words, as a dated note under
   `docs/specs/native-memory/`, before 3.3's first pull request.
8. **Who walks through, and when.** Recommended: one person who does not
   program, during the release candidate period, installing `1.0.0rc1` from
   PyPI and running the R2 journey while observed, with the receipt in
   `docs/journeys/`. Patrick names the person.
9. **What ships labeled experimental at 1.0.0, and the labels themselves.**
   Recommended: `memory-native`, native planning and building, and `fix` on
   Windows stay in the wheel under their labels; their envelopes stay pinned,
   but the deprecation promise of S1 does not cover them, and the README
   says which. The status line reads release candidate at `rc1` and stable
   at 1.0.0; the classifier moves to `4 - Beta` at `rc1` and
   `5 - Production/Stable` at 1.0.0.
10. **The older planning documents.** Recommended: the readiness direction,
    the October plan, the journey map and the phased plan are marked in the
    documentation index as superseded by the plan to 1.0.0 and this note,
    kept as dated evidence; the October 1 review reads them for opportunities,
    not for requirements.

## Size

Seventeen to twenty cycles and two dispatches before the release candidate,
then a period whose length decision 3 sets. Measured against Phase 2 (one
design note, four reviewed pull requests in a day) and the spec authority's
Task 4 (one note, three pull requests merged in a day, the fourth in flight),
and counted from the plan's own estimates
for each remaining task; 4.3's four are the spec's count. Each cycle carries a
different-model review under [the brief](../../review-brief.md) where it
touches `src/`, and lands in [the findings log](../../review-findings.md).
