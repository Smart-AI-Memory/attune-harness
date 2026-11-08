# Private hydration preparation increment

This increment composes the source primitives merged in #318 with a pure
four-layer projection. It does not expose **`hydrate`**, construct a Redis client,
or publish a generation. The [approved writer plan](tasks.md) still requires
supervised command execution, Redis staging and recovery, installed host delivery,
and migration acceptance.

## Scope and provenance

The implementation ports the projection and input-binding files from retained
commit `4494dac` and the private preparation owner from `11fdd89` onto current
`main`. It does not carry their historical branch's dependency, workflow, context
capture or process-supervision changes. Historical reviews apply to their recorded
checkpoints, not automatically to this port.

| Owner | Responsibility |
| --- | --- |
| `memory_reader.source_labels` | Keep the existing effective authority parser. Optional private observations retain decoded occurrences that duplicate keys or YAML merges would otherwise overwrite. Reader callers that do not request observations retain their existing path. |
| `memory_hydration_projection` | Inspect all captured files and sidecars before projecting curated nodes, file pointers, lesson bullets and recursive rules. Validate IDs, links and collisions; return logical records and resources without Redis effects. |
| `memory_hydration_inputs` | Bind root authority, explicit endpoint selection, raw bytes, inventories, absences, file versions and packaged Python policy. Exclude credential values and their hashes from public configuration commitments; keep exact in-process comparisons private. |
| `memory_hydration.PreparedHydration` | Accept a preparation only after guarded capture exits successfully. Return a body-free summary, materialize the existing self-counted generation manifest, and compare a complete fresh capture without replacing the original observation. |

## Projection decisions

- Preserve the reference writer's literal metadata mapping separately from the
  effective authority parser. Curated scalar duplicates keep the first literal
  value; file metadata duplicates keep the last. Safe decoded values and ignored
  records still pass complete secret inspection.
- Keep curated IDs and family-qualified pointer IDs compatible with the existing
  reader's key mapper. Refuse duplicate IDs rather than collapsing sources with
  the same stem. Refuse file pointers that match more than one authorized root.
- Preserve curated type/status memberships and explicit edges. Explicit neighbors
  must be selected curated or file records. Resolve file wikilinks within the same
  corpus first, then require a unique selected cross-corpus target. Count missing
  links and forward references rather than inventing neighbors.
- Exclude `MEMORY.md` from file indexes after inspecting its complete source.
  Index pointer text at no more than 32,768 characters and report each truncated
  record by layer. Keep source bytes unchanged and preserve full source paths.
- Preserve the existing YAML parser and its dependency-free subset. Observe
  overwritten occurrences without creating a second authority grammar. Inspect
  decoded keys, binary values, aliases and constructor-produced values; refuse
  cyclic metadata rather than expanding it indefinitely.

These are projection and preparation decisions, not live search-ranking,
publication or host-delivery qualification.

## Required caller responsibilities

`PreparedHydration` is private cooperative code, not a public check result or an
approval token. Its caller must own hard process interruption, a shared operation
deadline, fresh reads of the configuration files, bounded context capture and all
Redis capability checks. `verify_fresh` compares the newly supplied inputs and a
complete guarded source observation. It does not hold source descriptors across
a later Redis switch or implement that switch.

Publication must still reserve bounded writer-owned staging, verify function and
index readiness, perform one conditional manifest switch, reconcile lost
acknowledgments and reclaim only proven unreferenced resources. No unchanged-input
shortcut or retry is authorized by successful private preparation alone.

Production Redis, legacy namespaces and functions, personal hooks, source files,
saved memory and scratch operations remain untouched. No model calls, Git
synchronization, new dependencies, release or deployment are part of this change.

## Verification boundary

Synthetic tests cover all four layer mappings, complete decoded inspection,
indexing bounds, identity collisions, link ambiguity, exact payload accounting,
source/config/context changes, capture-exit failure and detached materialization.
The pull request records current focused, full-suite and noneditable-wheel results
and the independent review of this port.

Real disposable Redis+Search staging, concurrent publication, crash recovery,
retention races, hard supervision and automatic Claude Code/Codex delivery remain
unimplemented or unverified here. macOS tests do not establish Windows or desktop
host acceptance. No broader writer-completion claim follows from this increment.
