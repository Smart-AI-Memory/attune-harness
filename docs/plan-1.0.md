# The four phases between 0.4.0 and 1.0.0

Written September 22, 2026, the evening native memory Task 4 closed. This is
a plan, not a decision record: every phase names the decisions that are
Patrick's, and nothing here is authorized until he says so, one design note
at a time, as Tasks 3 and 4 were. The sources are the README's own promise,
the spec authority's rulings on what may wait (D6 in
[its README](specs/spec-authority/README.md)), the native-memory
[candidate ladder](specs/native-memory/scoping.md), the
[decisions of September 22](specs/native-memory/decisions-2026-09-22.md) and
the [opportunity log](opportunity-log.md). Which of the repository's promises
are requirements of 1.0.0 and which wait for a later milestone is
[the release 1.0.0 note](specs/release-1.0/README.md), written September 23
with the count of what remains.

**What 1.0.0 means.** The README says it in one sentence: interfaces,
configuration formats and CLI commands may change before 1.0, and what is and
is not qualified is listed, not implied. So 1.0.0 is the release after which
those three things stop changing without a deprecation, with the
qualification table still honest. D6 adds what cannot wait for it: full-suite
CI, a clean-clone install that passes its tests, no runtime `import attune`,
the spec authority through Task 5, the legacy spec reader, executable plugins
with their own threat model, and an honest README status. Task 6 of the spec
authority, the non-programmer walkthrough, should not wait either.

**Historical baseline (September 22–23).** 0.3.0 is on PyPI with its tag and Release. `main` is
at `0.4.0.dev0` and carries the batteries-included install (D15, amended),
the `redis` extra, `memory redis` and `memory scratch` (Task 4.1 to 4.3,
D16 to D18), and the review loop as data. All three landed the same evening, and 0.4.0 shipped from `9b15502`; Phase 1 below is
the record of what that took. Phase 2 landed on September 23 as #79 to #82,
four reviewed pull requests in a day, and its exit holds: the known-import
list is empty, the release gate reads memory, and the README's memory row
says native. The last `import attune` under `src/` is `memory_context.py`.
Phase 3 began on September 23: 3.5 is approved (D22), 3.1 has three of its
four pull requests merged (#106, #107, #108) and the release gate runs the R2
journey; 4.5's nine pull requests all merged the same day. 3.1 completed
the same evening with #110, step (b)'s stages under D24.

## Release-gate status — September 27, 2026

Updated through `main` at `da2206dab02fe2a3812ddf7465aa0ed02d5c0ad9`
([PR146](https://github.com/Smart-AI-Memory/attune-harness/pull/146)); its tree
was compared with the reviewed head. Original status baseline: September 26. The
requirements and exceptions remain those of [S1–S9](specs/release-1.0/README.md)
and [D25–D30](specs/release-1.0/addendum-2026-09-23.md). This table updates
execution status; the historical phase tables below preserve the original plan.
Existing stable-release gates have priority. Nice-to-have features stay in the
opportunity backlog unless needed to satisfy an existing requirement.

Implemented means code is merged. Evidenced means a named check or observation
supports a bounded claim. Accepted means the requirement's full evidence and
human decisions hold. Neither merged code nor a passing suite alone closes a gate.

| Gate | Implemented / evidenced at this revision | Remaining action and acceptance evidence | Owner / decision |
| --- | --- | --- | --- |
| S1 / 4.1, 3.4 — compatibility | First CLI/API/envelope guards (#124), versioned scratch (#116), saved memory/task records (#147), and deprecation/protocol guards plus saved-format inventory (#151). See [compatibility list](compatibility.md) and its named tests. | After plugin fields settle, capture the candidate saved-state fixture and freeze at rc1. | Implementation and independent review; Patrick approves release. |
| S2 / 4.4 — independent memory | Native readers, legacy import (#115), R2 installed journey, and D28 transition removal (#149) are merged. Adapter/differential removed; native fixture retained; old reader explicitly refused. PR149: full suite 3,123 passed, installed wheel 1,513 passed, all 19 CI checks green. | The Harness implementation and tests close 4.4; retain the [frozen-format contract](specs/native-memory/formats.md). | Patrick carries the reverse writer constraint to attune-ai; this summary does not claim that separate-repository action happened. |
| S3 / 3.3 — useful recall | Serving filters/prompt recall (#128) and explicit saved capture (#147) have software checks. [September 24 observations](specs/native-memory/observations-2026-09-24.md) identify user gaps. | Observe fresh-session serving, provenance and corrected/inactive exclusion. Explicit saved records are not yet wired into that serving path; do not claim automatic recall from save/index tests. | Real-session evidence with Patrick; no invented observations. |
| S4 / 4.3 — executable plugins | Signing, revocation, capability fields and early probes (#118); signed run binding, bootstrap/import closure and result framing (#150), with all 19 checks passed at its merged head. [Approved plugin contract](specs/executable-plugins/README.md). | Voyage dependency metadata, signed-provider wiring, host-owned journal differential, and final R1–R6 receipts on declared platforms; qualification wording changes last (R7). | Implementation/review; live paid differential needs separate authorization. D29 Windows decision remains Patrick's on October 10 if needed. |
| S5 / 4.2 — honest limits | Windows memory limits and experimental labels remain documented. | Reconcile [qualification](qualification.md) and README against final receipts. Native saved storage on Windows is not a new gate inferred from #147; executable-plugin platform evidence is separate. | Existing D20.8/D25/D29 decisions govern. |
| S6 / 4.6 — usability | No current candidate walkthrough accepted by this status update. | A named non-programmer completes the installed journey during the candidate period; retain observed receipt under `docs/journeys/`. | Patrick names participant; observer records outcomes. |
| S7 / 4.7 — artifact and candidate | Latest observed GitHub release is [v0.6.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v0.6.0), not rc1. The [September 24 build-only rehearsal](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/35967800177) passed; publication jobs were skipped and the workflow is byte-identical at this baseline. | TestPyPI now permits `main` with required reviewer retained (Patrick changed it; API verified September 27 UTC). Prepare and qualify the exact candidate commit, then obtain publication approval through the [runbook](release-runbook.md); two weeks without frozen-surface changes and the observed acceptance evidence still follow. | Patrick owns settings, dispatch/publication approval and release. |
| S8 — promised loose ends | Most 4.5 hygiene merged September 23; that closed row is not reopened. | Disposition the separately promised obsolete code-RAG caller and check final public claims against retained evidence. | Bounded implementation/review; inspect before removal. |
| S9 / 4.8 — migration | M1/M2 workspace and host plugin candidates (#140/#141) are distinct from full lifecycle support. | [Pre-release migration guide](migration-from-attune-ai.md) prepared; verify each row during candidate: carried/not carried/workaround, separate environments, and honest successor milestones. No premature deprecation notice. | Documentation; notice timing remains Patrick's under D26/D30. |

**Execution order:** executable plugins → final compatibility fixture/freeze →
rc1 → observed candidate period → stable. D28 and the deprecation/protocol
guards are merged; the final fixture still waits for plugin fields to settle. New format changes before rc1
must be incorporated into that fixture; after rc1 they restart the candidate.
October remains the target month, with no promised day.

The next useful implementation chunk is Voyage behind the signed-plugin boundary. Release-gate status and evidence remain here,
linked from O-04 in the [opportunity log](opportunity-log.md), rather than in a
second tracker. Recovery PR146 is merged with a bounded operator-observation path; its original
failed native-build evidence remains retained and is not rewritten as success.

## Retrieval scope for stable v1

Patrick confirmed this scope on September 27, 2026: finish and qualify Voyage;
additional RAG providers, an OpenAI SDK retrieval option and automatic fallback
are outside this release. A failed Voyage request must produce an explicit error,
not an empty successful search or an unnoticed switch of retrieval backend.
Unknown paid effects retain their journal and are never retried automatically.

Keep the existing local keyword route and offline memory document reads.
`attune-rag` remains a compatibility dependency until its retrieval and memory
selection features have tested replacements; no removal or formal deprecation
is part of this release decision. Local keyword search is an explicit user
choice, with different matching behavior from Voyage. See the
[Voyage failure and offline guidance](voyage-retrieval.md#failure-and-offline-behavior).
This narrows delivery scope; it does not claim that the outstanding plugin or
Voyage differential gates have passed.

## How to read the tables

*Done when* is the acceptance receipt, in the ladder's own words where it has
them. *Decision* names what only Patrick can settle before the work starts;
each phase opens with a design note that puts those decisions first. *Cycles*
is measured, not guessed: Task 4 took one design note and three reviewed
pull requests in one day; Task 3 took four steps over two. A cycle here is one
design note or one reviewed pull request with its suite, review and platform
runs.

## Phase 1 — Close 0.4.0

Goal: the install change, the Redis memory and the review tooling reach
users, and the serving path is used before it is designed. Release: 0.4.0.

| # | Task | Done when | Decision | Cycles |
|---|---|---|---|---|
| 1.1 | Merge #71, #72, #73 | Each merged on green with its review recorded; `main`'s tree matches each squash | Patrick merges, or says "shepherd" | 0 |
| 1.2 | Findings-log rows for #71 and #72 | Two rows in [the findings log](review-findings.md) with their classes; the tally updated | none | 1 |
| 1.3 | Release 0.4.0 | The [runbook](release-runbook.md)'s nine steps with receipts: release branch, both qualification runs green, `publish-pypi.yml` dispatched at the release SHA, the `pypi` environment approved, hashes verified, tag signed, GitHub Release with assets, `main` reopened at `0.5.0.dev0` | Patrick approves the environment and the tag | 1 |
| 1.4 | Dogfood `memory serve` | Patrick's own SessionStart hook runs `attune-harness memory --config … serve` from the isolated install for a week; what he notices is written down as the first input to Task 6 | Patrick switches his hook | 0 |

Exit: 0.4.0 on PyPI, `pip install attune-harness` gives the review, test,
acceptance and MCP journeys, `pip install 'attune-harness[redis]'` gives the
memory reads and the Redis scratch, and a session on this machine starts with
the digest served by Harness.

## Phase 2 — Memory native

Goal: Harness reads memory with attune-ai absent, and the adapter becomes the
fallback rather than the path. Release: 0.5.0. This is the native-memory
ladder's Tasks 1, 2, 3 and 8, in order, each consuming the previous result.

| # | Task | Done when | Decision | Cycles |
|---|---|---|---|---|
| 2.1 | Map the dependency (ladder 1) | A table of every attune-ai call `memory_context.py` makes, per tier, which the narrow reader needs, and which fixture in `tests/fixtures/memory_compatibility.json` covers each; gaps named | Which tiers the native reader must serve at 1.0 and which may stay adapter-only | 1 |
| 2.2 | Native readers (ladder 2) | Stdlib readers for the three file tiers; the compatibility fixtures pass in an installed environment with attune-ai absent; results match the adapter path where both are available | Whether a mismatch with the adapter is a defect in Harness or in the adapter, ruled per tier | 2 to 3 |
| 2.3 | Port the controls (ladder 3) | The sanitizer and the provenance checks in Harness under differential tests: same inputs through both implementations, same outcomes; the N5 duplication guard holds | The differential regime: how long both implementations run side by side | 1 to 2 |
| 2.4 | Switch the default (ladder 8) | `attune-harness memory` uses the native reader; the adapter is selectable as a fallback; installed qualification with attune-ai absent; rollback to the adapter without data conversion | The name and form of the fallback switch, and whether the release gate's `core` mode requires the native path | 1 |

Exit: `tests/test_no_attune_runtime_import.py`'s known list is empty, the
release gate's `core` mode reads memory, and the README's memory row says
"native" instead of "read-only integration plan accepted".

## Phase 3 — The journey native, and memory served

Goal: plan, build, review and memory all run with nothing from Attune AI
installed, other projects' spec state is still readable, and a fresh session
receives memory without a command. Release: 0.6.0. Four pieces from two
ladders, plus the spec that D6 says a stable release needs. Design note:
[phase-3-design.md](specs/phase-3-design.md); rulings on September 23, all as
recommended: [D20](specs/spec-authority/addendum-2026-09-23.md) and
[D21](specs/native-memory/decisions-2026-09-23.md).

| # | Task | Done when | Decision | Cycles |
|---|---|---|---|---|
| 3.1 | Spec authority Task 4: switch `plan` and `build` to the native authority and retire the bridge | The R2 clean-environment journey: plan, accept, build, review in a fresh install with attune-ai absent; `spec_bridge.py` gone or reduced to the legacy reader's shim | What of the bridge's behaviour is a contract to keep and what was scaffolding. Ruled (D20.1, D20.2): the user-visible words are the contract, the names are not; the R2 journey runs in the release gate; the six Task 4 decisions ruled September 23 (D23): the journey runs in the install a user gets, the `--no-deps` check kept beside it. Done September 23: four pull requests, #106, #107, #108 and #110, the stage mapping ruled as D24; the row is closed | 2 to 3 |
| 3.2 | Spec authority Task 5: read other projects' Attune AI spec state | An R4 receipt for every cited plan, fixtures from at least one other project; read and convert, never write back (D4), originals untouched, a receipt per conversion | Which projects' fixtures are the evidence. Ruled (D20.3): one plan from attune-ai's own `.claude/plans/`, origin recorded, plus the seven Harness plans | 1 to 2 |
| 3.3 | Serving path (ladder 6, N7) | A fresh Claude Code or Codex session receives relevant memory without an explicit command; the model's disclosure of a memory's influence is preserved as a requirement; corrected or forgotten memories stop being served. Starts from the week of 1.4 | Hook or plugin; what "relevant" means at session start; the disclosure form. Ruled (D21.4, D21.5): the SessionStart hook first and a prompt hook second, no MCP memory tool yet; a node absent from `status:active` or with a `wrong` verdict stops being served | 2 to 3 |
| 3.4 | Versioned store and writer protocol (ladder 5) | Versioned serialization designed natively; the file scratch store is the first tenant; legacy stores stay read-in-place, no conversion without a separate proposal | Whether this lands before the format freeze (this plan says yes: the freeze cannot pin a format that is about to change). Ruled (D21.6): yes; the scratch format's version opens the compatibility list | 1 to 2 |
| 3.5 | Executable plugins: the spec | A spec with a threat model and a sandboxing or signing design, reviewed before any implementation (D6: "need it", required for stable) | The trust model: who may sign, what a plugin may touch. Ruled (D20.7): signing, a capability list and a subprocess, stated as such and not as a sandbox. Approved September 23 (D22), all six decisions as recommended | 1 to 2 |

Exit: the connected journey qualification runs end to end with attune-ai
absent; the legacy reader has receipts from another project; Patrick's
sessions receive memory from Harness alone; the plugin spec is approved
(done: D22, September 23).

Ladder 7, the corrections lifecycle and review (N8), stays outside 1.0 by
ruling (D21.9, September 23) unless the week of dogfooding shows corrections
coming back; D6 does not list it among what cannot wait.

## Priority immediately after 0.6.0

Patrick's September 24 direction prioritizes memory saving, automatic work on
the opportunities list, cross-review, enhanced prompts, and roundtable immediately after 0.6.0. This changes
the sequencing of those capabilities from the later host-surface work;
it does not add them to 0.6.0 or approve an unspecified implementation.
See the [observations and scope decision](specs/native-memory/observations-2026-09-24.md).

## Phase 4 — The 1.0.0 candidate

Goal: stop changing the three things the README names, close the loose ends
the earlier phases created, and prove the release on the audience it is for.
Release: 1.0.0rc1 to TestPyPI through the runbook's `testpypi` target, then
1.0.0.

| # | Task | Done when | Decision | Cycles |
|---|---|---|---|---|
| 4.1 | Interface freeze | [The envelope table](envelopes.md) becomes the compatibility contract, with the gaps #73 recorded settled: `schema_version` on the `plan`, `build`, `status` and `memory scratch` envelopes, `status` on `code-config`, `triage-check`, `repair-economics` and `github-checks`; the config formats (memory config with `redis` and `scratch`, task records, plan state) and the CLI verbs written down with a deprecation path; the empty extra names removed as the changelog promised | Which shapes change before the freeze and which are frozen as they are. Ruled (D25.2): the list, the deprecation rule and the two moments; the saved-state fixture is the third cycle. The design note's seven decisions ruled as recommended (D27, September 23); the first cycle can start, and is the chair session's by exception (D29) | 3 |
| 4.2 | Windows | Either `fix` and `test` qualified on Windows for the cases the README names (deletion and renames, ACLs, files over 64 KiB, crash recovery, concurrent writers) or a written decision that Windows is a documented limit at 1.0 with WSL2 as the route to the POSIX profile (D6's Windows note) | Made on September 23 (D20.8): Windows is a documented limit at 1.0, `fix` and `test` unqualified there, the memory reader refusing, WSL2 the route; the work is the written decision and the qualification table | 1 |
| 4.3 | Executable plugins: implementation | The spec from 3.5 implemented and qualified; the README's protocols row no longer lists arbitrary executable plugins as unqualified | none new if 3.5 settled the trust model. Ruled (D29): the Windows unknowns, `gpg` and the child bootstrap on the three runners, are probed inside the first cycle; October 10 is the fallback's decision date | 2 to 4 |
| 4.4 | End the memory transition (ladder 9, N5) — implemented | [Frozen formats](specs/native-memory/formats.md), native-only reader, no import exception or differential, unchanged format fixture, and 70 golden envelopes (the original 63 plus seven later cases); reverse writer constraint travels with the PR | D25.5 and D28 implemented; attune-ai writers may continue but format changes require a compatible Harness reader first. attune_bridge removal, absent harness extra and attune-redis dependency require no further change here | 1 |
| 4.5 | Hygiene from the opportunity log | Built in the overnight run of September 23, one pull request each: `configure_process` idempotent and the CLI tests unstubbed (O-67, #100); one qualification run per release branch (O-64, #93); the review-gate habit in AGENTS.md (O-63, #90, merged); `qualify_pilot.py` deleted (O-68, #92, merged); the append lock's necessity asserted on every platform (O-65, #95); `docs/handoffs/` in `.gitignore` (O-43, #89, merged); one atomic writer with the Windows retry (O-59, #99); the index completeness check (O-60, #91, merged); the MCP test's deadline named (O-42, #94). All nine merged on September 23; the row is closed, and new hygiene candidates go to the log's October 1 review | none | 1 to 2 |
| 4.6 | The non-programmer walkthrough (spec authority Task 6) | R6 observed, not inferred: a person who does not program installs from PyPI, runs the installed journey and is watched doing it, during the release-candidate period | Who walks through | 1 |
| 4.7 | 1.0.0 | The README status line reads stable; the qualification table lists what is and is not covered; the runbook's steps with receipts; the tag; the Release | Patrick approves the environment and signs the tag | 1 |
| 4.8 | The migration page (D26) | During the candidate period, before 4.7: a page listing, per journey, what Harness carries at 1.0.0, what it does not (the plugin's skills and hooks, the hydrate writer, the multi-agent workflows, attune-ai's MCP tools) and what a user does about each; linked from the README's "Harness and attune-ai" section, rewritten at 1.0.0 | Ruled (D26): the deprecation is a notice, not parity | 1 |

Exit: 1.0.0 on PyPI, and a change to any envelope, config format or verb
after it is a deliberate diff with a deprecation, because a test fails
otherwise.

## What stays outside 1.0

By ruling, not by omission: remote A2A authentication (deferred by Patrick,
the local profile ships labeled local-only); the Voyage validation reuse spec
(retained in full, runs on its own track); native memory proposals (the
`memory-native` extra stays experimental and POSIX-only); the corrections
lifecycle (ladder 7), by D21.9, unless the dogfooding week brings it back;
the Claude Code plugin's skills and the hydrate writer, whose Harness
successors are the deprecation milestone's first rows (D26), designed on
September 23 ([the host-surface note](specs/release-1.0/host-surface-design.md),
D30), the deprecation itself being a notice that follows 1.0.0 once `/spec`
runs on Harness end to end.

## After 1.0.0 — The deprecation milestone

The rows D26 and D30 name, run during the candidate period beside 4.3 and
after the freeze's first two cycles, none on the path to `rc1`. Same
columns as the phases; each cycle that touches `src/` is reviewed under the
brief.

| Task | Deliverable | Receipt | Decisions | Cycles |
|---|---|---|---|---|
| M1 | The workspace surface | `mcp-serve --workspace` exposing attune-ai's three command workspace tool names over the carried host, the events file as evidence, the record's golden rows, and an end-to-end test through the real forms artifact with a mutation set | Ruled (D30.1, D30.3, D30.7) | 1 |
| M2 | The intake, the presenters, the plugin | `spec intake` and `spec present` ported and read against their originals; `plugin/` with `.claude-plugin/plugin.json`, a `.mcp.json` launching the server with `uvx`, the `/spec` skill rewritten only where it names a source, cross-review and the release skills copied | Ruled (D30.2, D30.4): `test` receipts are the task evidence | 1 |
| M3 | The gates | `gates check tasks\|execution --spec --changed`: `symbol-reality`, `falsifiability`, `format-lint`, the ledger, the G5 exits; receipts the Spec adapter consumes unchanged | Ruled (D30.5) | 1 |
| M4 | Roundtable | The roundtable adapter registered on the same host, its own review | Ruled (D30.1): the second row | 1 |
| M5 | The notice | `/spec` run end to end on Harness in Patrick's own sessions with the measured display receipt under `docs/journeys/`; the plugin on the marketplace; attune-ai's last release warning and pointing here, attune-ai's own work; the migration page (4.8) linked from both | Ruled (D26, D30.6): when M1 to M3 hold, not before | 0 to 1 |

## Order, and what can overlap

The phases are sequential where a task consumes the previous result: 2.2
needs 2.1, 2.4 needs 2.3, 3.3 starts from 1.4's week, 4.3 needs 3.5, 4.4
needs 2.4 and 3.3. Two things may run beside the memory work in Phase 2
without waiting: the spec authority's Task 4 design note, and the executable
plugins spec, because both are design first and neither touches the memory
modules. The Windows decision (4.2) was made on September 23, at the start
of Phase 3 (D20.8): 4.2 is one cycle.

Counted: 21 tasks with 4.8, between 27 and 36 cycles at today's pace now that
D20.8 fixes 4.2 at one. On September 23, ten are done, two in progress and
nine not started; [the release 1.0.0 note](specs/release-1.0/README.md)
counts eighteen to twenty-one cycles left with the migration page; its
rulings are [D25 and D26](specs/release-1.0/addendum-2026-09-23.md). Each cycle carries a different-model review under
[the brief](review-brief.md) and lands in [the findings log](review-findings.md).
