# Native memory, ladder 9 (plan 4.4): ending the transition, design note

Draft of September 23, 2026, for [the plan's task 4.4](../../plan-1.0.md),
whose substance [D25.5](../release-1.0/addendum-2026-09-23.md) ruled the
same evening: the attune-ai formats the native reader reads are frozen as
read, the `adapter` reader and the import exception go together with the
differential, the fixture stays as the contract, and the condition "once
attune-ai stops writing" is dropped, the constraint running the other way.
This note is short on purpose: the change is one cycle, and what is left to
decide is five small things. Patrick ruled them "all as recommended" before
the note was written; they are recorded as [D28](../release-1.0/addendum-2026-09-23.md).

## What the code says today

Read against `main` at 65c82cc.

**The switch.** `MemoryHost(config, jobs, native, reader='native')`
(`memory_context.py`) builds the native reader by default and, for
`reader == 'adapter'`, imports `attune.memory.harness_adapter.CompatibilityAdapter`,
a module attune-ai never released: the installed attune-ai has no such file,
and only a checkout of its `codex/shared-memory-adoption` branch has. Any
other value is refused with "Memory reader must be 'native' or 'adapter'".
`memory_cli.py` passes `config.get('reader', 'native')`; `memory_reader.py`
sets the `reader` key aside with `redis` and `scratch` before validating the
roots. An `ImportError` on that path is reported as `unavailable` with the
detail "Optional current-memory adapter dependencies are unavailable".

**The guard.** `tests/test_no_attune_runtime_import.py` has `KNOWN` empty
since D19 and one `FALLBACK`, `memory_context.py`, whose attune import must
sit lexically inside an `if` or `elif` comparing `reader` with `'adapter'`;
a runtime test constructs the host with the default and shows nothing from
attune loaded.

**The differential.** Two tests in `tests/test_memory_reader.py`,
`test_differential_against_the_adapter` and its adversarial twin, run only
where `ATTUNE_TEST_ADAPTER_ROOT` names the branch's checkout, POSIX only;
CI never runs them. `tests/test_memory_compatibility.py` characterises the
adapter's side with one probe that imports attune and skips without it, and
several attune-rag probes of the document formats that run in CI.

**The contract.** `tests/fixtures/memory_compatibility.json`, from commit
`3230643` of `wip/local-snapshot-2026-09-19` unchanged, pinned by digest and
shape in `tests/test_memory_fixture_contract.py` on every platform job.

**The golden rows.** Twelve of the seventy-one concern the adapter. Four
`-adapter` rows pin the read verbs' success shapes over an in-process double
of the adapter's four-member contract. Eight plain rows, `memory-capabilities`
through `memory-execute`, pin the host route's `unavailable` shape by
pointing `reader: adapter` at the absent module; the four read verbs also
have `-native` success rows, and the four worker verbs, `create`, `replay`,
`inspect` and `execute`, have no other pin.

**The formats, as read.** The raw tier: `<root>/findings.jsonl`, one object
per line with `id`, `text`, `topics`, `cwd` and `ts`, ranked by token overlap
with a three-day recency half-life, scoped by `cwd`, rows older than thirty
days expired. The document tiers: `**/*.md` under the root, up to 4,096 files
of 8 MiB and 64 MiB a query, frontmatter `owner`, `scope` and
`classification` matching the root, two sidecars, `summaries_by_path.json`
and `.verdicts.jsonl`, whose digest is part of the handle's version. The
Redis keyspace: `attune:memory:node:<id>` hashes, `file:`, `lesson:` and
`rule:` pointers whose `text` is never served, `status:<s>` sets,
`edges:<id>` lists, a `hydrated_at` stamp, the `idx:attune_memory` index and
the `attune_memory` function library with `recall_digest` and
`recall_related`, prefix not configurable. The statuses `available`,
`partial`, `unavailable` and `empty`, and every refusal text, are in
`memory_reader.py`'s docstring and its tests. The writers are all on
attune-ai's side: `attune/memory/file_stash.py` and `atomic_io.py` for the
findings, `personal.py` and `verdict_log.py` for the documents and their
sidecars, and Patrick's own `~/.attune/memory/hydrate.py` with
`functions.lua` for the keyspace.

**The three fates the plan row names.** `attune_bridge.py` was removed after
0.2.0 (#29, D8), so that fate is settled. attune-ai's `pyproject.toml` has no
`harness` extra today; if the shared-memory branch carried one, it goes with
that branch, which the scoping note says need not merge. `attune_redis`
depends on `attune-ai>=3.5.0` and is attune-ai's bundled plugin; Harness
reads the keyspace it fills and needs nothing from it.

**Where the adapter is still named.** The README's memory row, twice; the
CLI guide's `reader` paragraph; the envelope page's prose and its twelve
rows; the docstrings of `memory_reader.py`, `memory_context.py` and the
guard; and the Phase 2 note, which is dated evidence and stays.

## The design, one cycle

1. **The formats, written down.** `docs/specs/native-memory/formats.md`:
   the three formats and the keyspace as the reader reads them, field by
   field, with the bounds, the statuses and the refusal texts, the writers
   named, the fixture named as the executable form, and the reverse
   constraint stated: a change to any of these on attune-ai's side needs a
   Harness reader change first. 4.1's compatibility document points at it
   as the memory entry of its saved-state row.
2. **The reader, native only.** `MemoryHost` accepts `reader == 'native'`
   and nothing else; the `adapter` branch and its import go; the refusal
   reads "Memory reader must be 'native'". The default and every envelope
   stay as they are; `memory capabilities` keeps naming the reader.
3. **The guard, with no exception.** `FALLBACK` and the lexical check that
   served it are deleted; `KNOWN` stays empty and can only shrink; the
   runtime test stays; the docstring says no exception remains.
4. **The golden table, re-pinned.** The four `-adapter` rows go. The eight
   `unavailable` rows go with the fixture that produced them: the four read
   verbs are already pinned by their `-native` rows, which take the plain
   ids; the four worker verbs are pinned over the native reader with the
   injected participant running one offline job, as `test_memory_worker.py`
   does, so the table keeps a success shape for every host verb. Seventy-one
   rows become sixty-three, each a deliberate diff with the envelope page,
   before the content freeze at `rc1`.
5. **The tests.** The two differential tests and `ATTUNE_TEST_ADAPTER_ROOT`
   go; the compatibility file loses the probe that imports attune and keeps
   the attune-rag probes of the document formats; the fixture contract test
   stays as the sole witness of attune-ai's behaviour, and its docstring says
   so.
6. **The documents.** The README's memory row loses its two adapter
   sentences and gains the formats' address; the CLI guide's `reader`
   paragraph says `native` only; the envelope page's prose and rows follow
   the table; the three docstrings; a changelog line; the plan row closes.
7. **attune-ai's side.** The pull request's body carries the reverse
   constraint as a paragraph for Patrick to place in attune-ai beside the
   writers it names, since he owns both sides (D25.5). Nothing else in this
   repository refers to attune-ai's memory code afterwards.

Touches `src/` at two sites and `tests/` at four, so a different-model
review under [the brief](../../review-brief.md) and a findings-log row.
Independent of 3.4 and 4.3; before 4.1's document, which cites it.

## Decisions for Patrick, ruled as recommended (D28)

1. **The refused form.** Recommended: `reader: adapter` is refused now with
   "Memory reader must be 'native'", with a changelog line and no
   deprecation period, because a form that cannot work in any install is not
   deprecated, it is removed. Alternative: accept it for one minor release
   under 4.1's rule, which would deprecate something nobody can run.
2. **The guard's shape.** Recommended: delete the `FALLBACK` machinery.
   Alternative: keep it with an empty set, code with no caller.
3. **The golden rows.** Recommended: twelve rows go, the `-native` rows take
   the plain ids, and the four worker verbs are pinned over an offline job,
   sixty-three rows. Alternative: leave the worker verbs unpinned, which
   would freeze a table with four verbs missing.
4. **The compatibility probes.** Recommended: the attune-importing probe
   goes, the attune-rag probes stay, the fixture contract test is the sole
   witness. Alternative: delete the compatibility file whole, losing the
   document-format probes that run in CI.
5. **attune-ai's side.** Recommended: the reverse constraint travels in the
   pull request's body for Patrick to place in attune-ai; attune-redis's
   dependency and the absent `harness` extra need nothing here. Alternative:
   a pull request against attune-ai from this session, across repositories.

## Evidence 4.4 ends with

`formats.md`; a native-only `MemoryHost` with its refusal and test; the
guard green with no exception; the differential gone and the fixture
contract green; sixty-three golden rows matching the envelope page, the four
worker verbs among them; the README, the CLI guide and the docstrings saying
native only and where the formats are; the changelog line; the plan row
closed; the reverse constraint's text in the pull request for attune-ai.

## Size

One cycle, `src/` and `tests/` and documents, reviewed under the brief. The
table's re-pinning is most of the work; the removal itself is a few dozen
lines.
