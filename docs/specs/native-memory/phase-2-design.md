# Native memory, Phase 2: design note

Written September 22, 2026, the evening 0.4.0 shipped, for
[Phase 2 of the plan to 1.0.0](../../plan-1.0.md): the native-memory
ladder's Tasks 1, 2, 3 and 8, released as 0.5.0. Like
[the Task 4 note](task-4-design.md), it puts what was read from the code and
the machine first, then the design, then the decisions that are Patrick's;
nothing here is authorized until he rules, and the rulings are recorded in
[the decisions file](decisions-2026-09-22.md) as D19 onward.

## What the dependency actually is, read from the code

The ladder's Task 1 says "record exactly which attune-ai calls the current
adapter makes, per tier, and confirm the fixtures cover each". Most of that
record can be written now, and it is smaller and stranger than the plan
assumed.

**One import.** The only `import attune` under `src/` is
`memory_context.py:21`, `from attune.memory.harness_adapter import
CompatibilityAdapter`, inside `MemoryHost.__init__`. The test
`tests/test_no_attune_runtime_import.py` pins that as the single known entry
and fails if the list grows or goes stale. Harness uses four members of the
adapter object: `query(query, k)` for the whole recall path, `binding` (a
digest of the root config that `refresh` checks), `capabilities()` and
`resolve(handle)`. `refresh` itself is Harness code.

**The adapter was never released.** attune-ai 16.2.1, the version installed
on this machine, has no `attune/memory/harness_adapter.py`. The module
exists only on attune-ai's `codex/shared-memory-adoption` branch, checked
out at `~/attune-ai-memory-adoption` (head `b89f7953f`). So `attune-harness
memory recall` is `unavailable` for every user today, with or without
attune-ai installed, unless their environment was built from that branch;
the opportunity log recorded this on September 21. Phase 2 is therefore not
replacing a working path with a native one. It is making the path work at
all, for the first time, from Harness alone.

**What the adapter reads, per tier.** Only three tiers, and none of them is
the Redis keyspace:

| Tier | Source on disk | How the adapter reads it | attune-ai code on the path |
|---|---|---|---|
| `raw` | `<root>/findings.jsonl`, one JSON object per line: `id`, `text`, `topics`, `cwd`, `ts` | Copies the file into a private temp dir, ranks it through the file stash backend, enforces `cwd == root.scope` exactly, reads the kind from one `type:` topic, expires rows past 30 days on `resolve` | `attune.memory.file_stash.FileStashBackend` (19,614 bytes), `attune.memory.session_stash.recall_entries` and `recent_entries` (28,186 bytes) |
| `personal`, `curated` | `**/*.md` under the root, up to 4,096 files of 8 MiB, 64 MiB per query, plus two sidecars, `summaries_by_path.json` and `.verdicts.jsonl` | Snapshots descriptor-checked bytes with original mtimes into a temp dir and queries `PersonalMemory(...).query(query, k, strict=True)`; the handle version is a digest of the source and the sidecars, so a sidecar change invalidates handles | `attune.memory.personal.PersonalMemory` (22,295 bytes) |

The curated nodes, file pointers, lessons and rules are the four Redis
layers, already native and attune-ai-free since Task 4 (`memory_redis.py`).
Phase 2 does not touch them.

**The controls on the path**, which N2 says the port must keep:

- **Sanitizer.** Every string the adapter surfaces, metadata keys and values
  included, goes through `session_stash.prepare_strict_content`; any change
  means "Source is unsafe or requires redaction; governed exposure refused".
  Underneath is `DataSanitizer(pii_scrub_enabled=True,
  secrets_detection_enabled=True)` from `attune/memory/short_term/security.py`
  (9,897 bytes), and the gate fails closed when it cannot be imported.
- **Provenance.** Stamped inside attune-ai, not called by the adapter:
  `provenance_fields` and `scan_instructions` in `attune/memory/provenance.py`
  (11,356 bytes) add the untrusted-evidence framing and the instruction-shape
  flags. "Flags, never blocks."
- **Path and authority.** `attune.security.path_validation._validate_file_path`
  (3,222 bytes), a POSIX descriptor walk with `O_NOFOLLOW` that refuses
  symlink swaps and hard links and refuses non-POSIX outright, and a check
  that each document's frontmatter `owner`, `scope` and `classification`
  match the root.

Transport: none. The adapter's `apply()` always raises. Total attune-ai code
on the read path, before transitive imports: about 95 KB across six files,
of which the harness adapter itself is 18,999 bytes and imports two Harness
modules back (`memory_contract`, `review_contract`), a cycle the port removes.

**The fixtures are not on `main`.** `tests/test_memory_compatibility.py`
reads `tests/fixtures/memory_compatibility.json`; the file exists on exactly
one commit, `3230643` on `wip/local-snapshot-2026-09-19`, with sections
`raw` (5), `documents` (5), `curated` (2), `digest_node` (7), `working` (2)
and `pattern` (3). The test skips when attune-ai is absent, which is why the
suite is green without it and why 19 of its 24 cases error when the file is
missing but attune-ai is present. N4 makes this file the format contract.
Landing it on `main` is the first concrete step of the phase.

**The success envelopes are unpinned.** The golden table (#73) pins
`memory capabilities|recall|resolve|refresh` only in their
attune-ai-absent `unavailable` shape. Their success shapes,
`memory_context`'s packet with `schema_version`, `operation`, `status`,
`authority`, `items`, `problems` and `guidance`, are what the native reader
must keep, and nothing asserts them yet.

## The design

One new module, `memory_reader.py`, implements the four-member contract the
host already consumes (`binding`, `capabilities()`, `query(query, k)`,
`resolve(handle)`) with the standard library, and `MemoryHost` takes a
reader instead of importing the adapter. The envelopes do not change. Two
smaller modules carry the controls: `memory_controls.py` for the strict
content gate and the provenance fields, and the path walk reuses the
validator Task 2 of the spec authority already carried, with its Windows
check. The adapter remains reachable behind a config switch until Task 9
removes it.

What the reader reproduces is the adapter's observable contract, not its
internals: the fixtures' expected meaning per tier, the bounds (4,096 files,
8 MiB, 64 MiB, 30 days), the exact `cwd` scope on raw rows, the sidecar-bound
handle versions, the frontmatter authority check, the refusal wording, and
the `available | partial | unavailable | empty` statuses. Where the adapter's
ranking is a property of attune-ai's tokenizer rather than of the fixtures,
the differential in 2.3 says whether Harness matched it, and Patrick rules
per tier on any mismatch (decision 3).

What is not carried, by N2: promotion authoring, grounding and polish, the
retrieval-summary generation behind `summaries_by_path.json` (the reader
consumes the sidecar, it does not write it), `curated_audit`,
`recall_digest`'s HTML, and every writer path (ladder Task 5).

### 2.1 Map the dependency, and land the contract

- The table above, completed with transitive imports measured (the
  sanitizer's `attune.security` imports in particular) and each fixture case
  mapped to the adapter calls it exercises; gaps named.
- `tests/fixtures/memory_compatibility.json` brought onto `main` from
  `3230643` unchanged, with a receipt of its origin, and
  `test_memory_compatibility.py` made to run its adapter-free assertions
  (file shapes, frontmatter parsing, byte identity) without attune-ai
  instead of skipping the whole module.
- The four success envelopes added to the golden table as rows the native
  reader must match.

Done when the design note's table has no "unmeasured" cell, the fixture is
tracked, and the golden table pins the success shapes. Docs and tests only;
one pull request.

### 2.2 Native readers

`memory_reader.py`: the raw tier (a JSONL reader with the stash's ranking
semantics, exact `cwd` scope, `type:` topic kind, 30-day expiry on resolve)
and the document tiers (Markdown with frontmatter, the two sidecars,
descriptor-checked reads within the bounds, sidecar-bound versions), behind
the four-member contract. `MemoryHost` constructs it when the memory
config's `reader` is `native`.

Done when the compatibility fixtures pass in an installed environment with
attune-ai absent, and `attune-harness memory capabilities|recall|resolve|refresh`
return their success envelopes there. Touches `src/`: a different-model
review, with the reviewer reading the adapter side by side as the brief's
step 1 says. Two to three pull requests: raw, then documents, then the host
switch if the reviewer asks for the split.

### 2.3 Port the controls, under the N5 guard

`memory_controls.py`: the strict content gate (secrets detection and PII
scrub as the sanitizer applies them, fail closed) and the provenance fields
(untrusted-evidence framing, instruction-shape flags). The differential:
the same inputs through both implementations, same outcomes, run wherever
the adapter checkout exists, gated by an environment variable naming it
(`ATTUNE_TEST_ADAPTER_ROOT`), the way the live Redis test is gated. CI runs
the checked-in outcomes; the differential's receipts are recorded per run.

Done when every fixture string and a corpus of adversarial strings (secrets
in each format the sanitizer knows, PII shapes, instruction-shaped memory)
produce the same refusal or the same redaction through both, and the
receipts say so. Touches `src/`: a different-model review. One to two pull
requests.

### 2.4 Switch the default

The memory config gains `"reader": "native" | "adapter"`, default `native`.
`adapter` keeps the old import, so a user with the unreleased branch can
fall back without touching their data; `memory capabilities` names which
reader answered. The release gate's `core` mode runs `memory recall` against
a fixture root and expects a success envelope.

Done when `tests/test_no_attune_runtime_import.py`'s known list is empty
(the adapter import moves behind the switch and the test learns that one
guarded, documented site), installed qualification with attune-ai absent
reads all three tiers, rollback to the adapter is a config edit, and the
README's memory row says native. One pull request, `src/`, reviewed.

## Decisions for Patrick

1. **Land the fixture from `3230643` unchanged, as the contract N4 names.**
   The alternative is to regenerate it from the adapter checkout, which
   would make the contract whatever the branch does today rather than what
   Task 1 accepted. Recommended: unchanged, with the origin receipted; any
   correction is a separate, visible edit.
2. **What "matches the adapter" means for ranking.** Bit-identical ordering
   would mean porting the stash tokenizer and PersonalMemory's scoring line
   by line. Recommended: identical sets and identical top result on the
   fixtures and on the differential corpus; order below that may differ and
   is reported, not failed. The fixtures already assert sets and byte
   identity, not order, except the raw tier's soft `cwd` ordering, which is
   kept.
3. **A mismatch is ruled per tier, in the design note's receipt.** When the
   differential disagrees, either implementation may be wrong; the adapter
   is an unreleased branch, not a standard. Recommended: Harness fixes its
   side by default, and a case where the adapter is judged wrong is
   recorded with the reason and excluded from the differential by name.
4. **How long two copies of the controls live.** N5 allows the duplication
   only as a bounded transition. Recommended: until Task 9, which the plan
   puts in Phase 4; the differential runs at every release in between and
   its receipt is attached to the release.
5. **The differential is local-only evidence.** The adapter exists only in
   a checkout on this machine, so CI cannot run both sides. Recommended:
   accept that, gate it by `ATTUNE_TEST_ADAPTER_ROOT`, and attach its
   receipt to each of 2.2, 2.3 and 2.4's pull requests, as the live Redis
   receipt was attached in Task 4.
6. **POSIX-only at 0.5.0, as the adapter is.** The adapter refuses non-POSIX
   because its descriptor walk needs `O_NOFOLLOW` and `dir_fd`. Harness has
   the carried path validator with a Windows check, so the reader could
   accept Windows for reads. Recommended: keep the adapter's refusal for
   0.5.0 so parity is what the differential measures, and take Windows with
   the Phase 4 decision, where the qualification cases for it are already
   listed.
7. **The `core` gate requires the native path.** Recommended: yes, from
   2.4 on; a wheel installed with `--no-deps` must read memory, or the
   release does not ship.
8. **The switch's name and default.** Recommended: `reader` in the memory
   config, `native` by default, `adapter` as the only other value, removed
   in Task 9 with a changelog line.

## Evidence the phase ends with

- The dependency table with measured sizes, the fixture tracked with its
  origin, the success envelopes in the golden table (2.1).
- The compatibility suite green in a `--no-deps` install of the wheel, on
  the three platforms' jobs, with the adapter absent (2.2).
- Differential receipts for 2.2, 2.3 and 2.4 from this machine, each naming
  the adapter commit, the corpus and every mismatch with its ruling (2.3).
- `KNOWN` empty; the README's memory row rewritten; installed qualification
  in `core` mode reading all three tiers; a rollback rehearsed and
  receipted (2.4).

## Size

Measured against Task 4, which took one design note and three reviewed pull
requests in a day: 2.1 is one docs-and-tests pull request; 2.2 is two or
three `src/` pull requests, the largest of the phase; 2.3 one or two; 2.4
one. Five to seven cycles, each with its review under the brief and a row in
the findings log. The unknowns that move the estimate are the sanitizer's
transitive imports (measured in 2.1) and how far PersonalMemory's scoring
is from a stdlib rewrite (decision 2 caps the cost).

## 2.1 receipt, September 22, 2026

Measured in the adapter checkout (`~/attune-ai-memory-adoption`, head
`b89f7953f`, its own venv), with Harness's `src` on the path because the
adapter imports two Harness modules:

| What | Modules | Bytes |
|---|---|---|
| Imported when `attune.memory.harness_adapter` loads | 20 | 253,719 |
| Also loaded when the read path's modules import (`file_stash`, `session_stash`, `personal`, `provenance`, `path_validation`, `short_term.security`) | 20 more | 201,890 |
| Total attune-ai code the read path needs | 40 | 455,609 |

The six files named above are 95 KB of that; the rest is the security
package the sanitizer pulls (`secrets_detector` 23,643 bytes, `pii_scrubber`
21,300, `log_methods` 14,735, `audit_logger`, `reports`, `query`, `events`,
`secrets_types`), `curated_audit` (31,909), `verdict_log`, `atomic_io` and
the packages' `__init__` modules. Third-party packages the load pulls in:
`cryptography`, `redis`, `rich` and `structlog`. So the native controls of
2.3 replace about 90 KB of sanitizer and 11 KB of provenance, and the
reader of 2.2 about 70 KB of stash and document code; nothing else on the
list is needed by the four members Harness calls.

The fixture is on `main`: `tests/fixtures/memory_compatibility.json`, byte
identical to commit `3230643` (SHA-256 `37ed7a15…4b3bce`, 3,193 bytes),
pinned by `tests/test_memory_fixture_contract.py` on every platform, with
the sections `raw` (5), `documents` (5), `curated`, `digest_node`, `working`
and `pattern`. The success envelopes of `memory capabilities`, `recall`,
`resolve` and `refresh` are pinned in [the envelope table](../../envelopes.md)
as the four `-adapter` rows, over an in-process double of the four-member
contract.

Coverage of the adapter's calls by the fixture, for 2.2: `raw` covers
`recall_entries` and `recent_entries` over `findings.jsonl` with two `cwd`
values and five kinds; `documents` covers the five personal kinds through
`PersonalMemory.query` and full-source resolution; `curated` covers
frontmatter parsing with links and a review id. Not covered by the fixture,
and to be added as cases in 2.2: the sidecar-bound handle version
(`summaries_by_path.json`, `.verdicts.jsonl`), the 4,096-file, 8 MiB and
64 MiB bounds, the frontmatter `owner`/`scope`/`classification` refusal, the
30-day raw expiry on `resolve`, and the sanitizer refusal on a surfaced
string (the compatibility test has one for the write path only).

## 2.2 rulings under decision 3

Recorded from the differential and the review of #80, September 22, 2026.

- **Adapter wrong, excluded by name:** a raw row whose `topics` list holds a
  non-string element. The adapter's tokenizer raises inside `recall_entries`'
  blanket `except`, so the whole root answers `empty`; the native reader
  tokenizes the string topics and ranks the row. Harness keeps its behaviour.
- **Native fixed to the adapter:** a raw row with no `topics` key is legal;
  an empty or blank string passes the gate (the candidate is `label=value`,
  never blank); the gate runs before the frontmatter check, so a document
  that is both mislabelled and unsafe refuses in the gate's words; an
  unreadable raw `ts` is "expired", never a `TypeError`; a dangling
  `findings.jsonl` symlink is an absent file; a sidecar that appears during a
  query is a change; the binding is re-checked per root during a query.
- **Declared seams kept:** the provenance fields and staleness annotations
  in document metadata (2.3); `resolve` on a malformed handle refuses with a
  `ValueError` where the adapter raises `AttributeError` or `KeyError`; a
  directory locator refuses with the regular-file text where the adapter
  raises `IsADirectoryError`.
- **Gate parity:** the sanitizer's patterns are carried verbatim, and a
  comparison against `prepare_strict_content` itself on 35 strings, the
  reviewer's twenty disagreements included, finds none.
