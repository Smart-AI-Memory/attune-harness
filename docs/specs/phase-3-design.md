# Phase 3: design note

Written September 23, 2026, the night 0.5.0 shipped, for
[Phase 3 of the plan to 1.0.0](../plan-1.0.md): the journey native, and
memory served. Release: 0.6.0. Like the Task 4 and Phase 2 notes, it puts what
was read from the code first, then the design, then the decisions that are
Patrick's; nothing here is authorized until he rules. The rulings go in a dated
decisions file beside the spec they belong to, the spec authority's addendum
for 3.1, 3.2 and 3.5 and the native-memory decisions for 3.3 and 3.4.

Phase 3 spans two ladders and adds one spec. Its five pieces, in the plan's
words: 3.1 spec authority Task 4, switch `plan` and `build` to the native
authority and retire the bridge; 3.2 spec authority Task 5, read other
projects' Attune AI spec state; 3.3 memory ladder Task 6, the serving path;
3.4 memory ladder Task 5, the versioned store and writer protocol; 3.5 the
executable plugins spec. Exit: the connected journey qualification runs end to
end with attune-ai absent, the legacy reader has receipts from another
project, Patrick's sessions receive memory from Harness alone, and the plugin
spec is approved.

## What the code says today

**3.1, the bridge.** `spec_bridge.py` is 439 lines and, since Task 3 (D14),
imports nothing from Attune AI: its docstring says the host and the adapter
are Harness's own. It exports five names. Two are the legacy reader,
`plan_content` and `legacy_plan`, which strip the trailing state comment and
read the `<task>` blocks with source and content digests; three are the
switch, `import_plan` and `reimport_plan` behind `plan --import-plan` and
`--reimport`, and `WorkSpecBridge`, which `work_cli` uses for `--accept` and
the decision preview. `work_cli.py` and `work_contract.py` import the bridge;
`work_runtime.py`, `work_build.py` and `work_decisions.py` do not. The
spec-creation stages carried inside `spec_workspace.py`, eleven of them,
"stay unwired until Task 4 switches plan and build" (D14, decision 4); the
bridge constructs its state already at `executing`. What the R2 journey
needs today is not attune-ai but the `review` extra, `attune_forms`, which
renders the decision and is in the base install since D15. The README already
claims `plan --accept` runs without Attune AI, and CI blocks `attune` for the
gate tests. No document spells the R2 journey out as a command sequence.

**3.2, the legacy reader.** `spec_state.py` reads schema versions 1 and 2 and
refuses any other; `spec_tasks.py` parses the XML tasks; `legacy_plan` reads a
plan into the shape the bridge consumes and records what it could not map.
`import_plan` refuses a plan outside the project or behind a symlink, which
is exactly what a fixture from another project is. The seven plans the Task 2
differential ran against are Harness's own, on the wip branch; no fixture
from another project exists, and nothing writes a conversion receipt.

**3.3, serving.** `memory serve` prints the Redis digest as text, bounded,
failing open, with a fixed footer; it uses none of the provenance envelope
that `memory_controls.wrap_recalled` produces for the recall path, and it
applies no filter of its own: the digest is what `FCALL_RO recall_digest`
returns, and Harness never reads `status:active`. The file tiers' tombstones
(`.verdicts.jsonl`, a `wrong` verdict) live in `memory_controls.staleness`
and never reach the Redis path. The only surface is the Claude Code
SessionStart hook; the MCP server serves retrieval only, with a read-only
annotation and a finite call budget, and no memory tool; Codex is named in
the scoping note and nowhere in `src/`. Patrick's own session has run the
hook since September 22; his observations are the input this section waits
on.

**3.4, the store.** The file scratch store already writes a versioned record,
`schema_version` 1 with `key`, `value`, `stored_at` and `expires_at`, compact
and canonical, through a temporary file and `features.replace_file`, with
expiry checked on read and no sweeper. The shared-memory adoption design's
four open questions (a serialization every writer can honour without
converting the corpus; identity and replay per R5; a root-bound exact-record
API; which tier qualifies first) were handed to this task by the scoping
note, which names the file scratch store the first tenant because losing
scratch data is harmless.

**3.5, plugins.** The extension system is data-only by construction: a
manifest, a `SKILL.md`, one to four tool declarations whose only legal binding
is `retrieve`, an artifact digest checked before and after every call, a
leased lifecycle, and a docstring that says "it never imports bundle code".
No threat-model text exists anywhere in the repository; "sandbox" appears
only in disclaimers. D6 rules executable plugins "need it", required for
stable, with their own spec, a threat model, and sandboxing or signing before
implementation; D7 names Voyage as the first real consumer.

**The Windows decision.** The plan asks for it early. `fix` on Windows is
qualified for nothing: it runs on a fixed local NTFS volume and its native
tests pass in CI, with deletion, renames, ACLs, files over 64 KiB, crash
recovery, concurrent writers and durability all unqualified; `test` on
Windows is unqualified; the native memory reader refuses there (D19). The
implementation exists; what is open is qualification.

## The design

### 3.1 Switch `plan` and `build`; reduce the bridge to the reader

`work_cli` constructs the Spec workspace host directly, `command_workspace`
with the `spec_workspace` adapter, for `--accept`, the decision preview and
the spec-creation stages, so the eleven stages become reachable through the
same gate the task gate already uses. `WorkSpecBridge`, `import_plan` and
`reimport_plan` move into `work_cli` or a `spec_switch.py` beside it, keeping
their words; `spec_bridge.py` shrinks to `plan_content` and `legacy_plan`
and is renamed `spec_legacy.py`, the shim the plan allows, with the reader
tests following it. The R2 journey is written down as a test and a document:
`plan` from a spec, `--accept` through the gate, `build`, `review`, in a
fresh `--no-deps` install with `attune` blocked, and the release gate's
installed check runs it. Two to three reviewed pull requests: the switch, the
shrink, and the journey.

### 3.2 Read other projects' spec state, with a receipt

A `plan import` path that accepts a plan file outside the project when it is
named explicitly, reads it through `spec_legacy` and `spec_state` (schema
versions 1 and 2, anything else refused with the next action), converts it
into the task store's shape, and writes a receipt beside the task: source
path, source digest, schema version, what was mapped, what was not, and the
time. The original is never written. Fixtures: at least one plan from an
Attune AI project other than Harness, checked in under `tests/fixtures/`
with its origin recorded, plus the seven Harness plans from the wip branch as
the regression set. One to two pull requests.

### 3.3 Serve memory into a session, and stop serving what was corrected

Keep the SessionStart hook as the first surface, since it is the one Patrick
uses, and give `memory serve` three things it lacks: the provenance framing
(one line, not the whole envelope, since the digest is a banner and not a
recall), a filter that drops a node whose id is absent from `status:active`
or whose file-tier stem carries a `wrong` verdict, and a second mode,
`memory serve --for PROMPT`, for a UserPromptSubmit hook that serves the
nodes related to the prompt rather than the global digest. "Relevant" at
session start stays what `recall_digest` scores; on a prompt it is `search`
over the index with the prompt's terms, bounded as `serve` is. The MCP
server gains no memory tool in this step; Codex waits for a Codex user.
Two to three pull requests, the first after Patrick's week of observations.

### 3.4 A versioned store with a writer protocol, scratch first

`memory_scratch`'s record gains what the adoption design's questions ask: an
explicit `format` name and version at the top of the record, a `writer`
field naming what wrote it, an `expected_version` on `stash` for a
compare-and-set that refuses a lost update instead of overwriting, and a
receipt for an uncertain effect (a replace that may or may not have landed)
rather than a retry or a divert. The Redis backend gets the same protocol
over `SET ... NX`/`WATCH`. Legacy stores stay read in place. The format's
version becomes part of the 1.0 freeze in Phase 4. One to two pull requests,
`src/`.

### 3.5 The executable plugins spec

A spec, not code: a threat model naming what a plugin may read, write and
call; a trust model with signed manifests and a per-plugin capability list
the host enforces; execution in a subprocess with the run store's lease, the
existing output bounds and timeouts, and no network unless the manifest
declares it; Voyage as the first consumer, so the boundary is proven on the
integration that already exists behind the plugin line. Reviewed as `src/`
is, before any implementation; the implementation is Phase 4's 4.3.

## Decisions for Patrick

1. **3.1 keeps the bridge's words.** The refusal texts, the readiness check
   and the import receipts are contracts; the class and module names are
   scaffolding. Recommended: keep every user-visible text, rename freely.
2. **The R2 journey runs in the release gate.** Recommended: yes, from the
   `--no-deps` wheel with `attune` blocked, so the gate proves the journey
   the README claims, as it now proves memory.
3. **3.2's fixture comes from a real project of yours.** Recommended: one
   plan from attune-ai's own `.claude/plans/`, copied with its origin and
   commit recorded, plus the seven Harness plans as regression.
4. **3.3's first surface stays the SessionStart hook, and the prompt hook
   is the second.** Recommended: yes; an MCP memory tool waits until a
   consumer other than Claude Code asks for it.
5. **What stops being served.** Recommended: a node absent from
   `status:active`, and a file-tier stem with a `wrong` verdict; nothing
   else is inferred.
6. **3.4 lands before the freeze.** Recommended: yes, and the scratch
   format's version is the first entry in the 1.0 compatibility list.
7. **3.5 is signing plus a capability list plus a subprocess, not a
   sandbox claim.** Recommended: say what the boundary is and is not; the
   README already says Harness is not a security sandbox, and the spec
   should not make it one by implication.
8. **The Windows decision, made now.** Recommended: Windows stays a
   documented limit at 1.0: `fix` and `test` unqualified there, the memory
   reader refusing, WSL2 named as the route to the POSIX profile. That makes
   Phase 4's 4.2 one cycle. Qualifying instead is four to six, and nothing on
   the ladders needs it before 1.0.
9. **Ladder 7, the corrections lifecycle, stays outside 1.0.** Recommended:
   yes, unless the week with `memory serve` shows corrections coming back.
10. **Order.** Recommended: the 3.1 design detail and 3.5's threat model
    first, in parallel, since neither touches the memory modules; 3.3 once
    the observations are in; 3.2 and 3.4 after 3.1 lands.

## Evidence the phase ends with

- The R2 journey as a test and a document, green in the release gate with
  `attune` blocked; `spec_bridge.py` gone, `spec_legacy.py` in its place
  with the reader tests (3.1).
- A conversion receipt per imported plan and a fixture from another project
  (3.2).
- A session on this machine that receives the digest with the provenance
  line, a prompt hook that serves related nodes, and a demonstration that a
  tombstoned or inactive node is not served (3.3).
- The versioned scratch record with compare-and-set on both backends, and
  the format's version in the compatibility list (3.4).
- The plugins spec approved, with its threat model and trust model (3.5).

## Size

Measured against Phase 2, which took one design note and four reviewed pull
requests in a day: 3.1 three pull requests, 3.2 one or two, 3.3 two or
three, 3.4 one or two, 3.5 one document reviewed as code is. Eight to twelve
cycles, with 3.1 the largest and 3.3's start gated on the observations.
