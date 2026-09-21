# Spec authority, Task 1: module verdicts

September 21, 2026. Task 1 of [the spec authority note](README.md): review the
Attune AI code in the spec path, and the memory adapter added by D10 of
[the addendum](addendum-2026-09-21.md), and give each module one verdict.

**Status: proposed and independently reviewed, not accepted.** Accepting these
verdicts is Patrick's decision. Nothing here moves any code.

Everything was read from the Attune AI branch `codex/shared-memory-adoption` at
`b89f7953f`, the branch Codex qualified Harness against. It is three commits
ahead of Attune AI's `main` and has never been released. Harness was read at
`0314b66`.

## The result in one paragraph

No module is fit to adopt exactly as written. Seven are **adapt**: the core is
sound and worth carrying, and each has a named seam to rework. Four are
**reference**. The first proposal had three adopts; the design review moved all
three down a row, each for a defect that matters to Harness and not to Attune
AI. Reuse still cuts the work substantially: the seven adapt modules bring 2,619
lines and 269 tests. But the review also shows why the note asked for one before
moving anything.

## The verdicts

The note's four tests for **adopt**: the module has its own tests; its data
shape is versioned or otherwise stable; it has no hidden dependence on Attune AI
globals or registries; and its boundary maps onto an accepted task record.
Missing one moves a module down a row, not out.

| Module | Lines | Its tests | Imports from Attune AI | Proposed | After review |
| --- | ---: | ---: | --- | --- | --- |
| `security/path_validation.py` | 93 | 19 | none | Adopt | **Adapt** |
| `spec/state.py` | 319 | 130 | `spec_reader`, `path_validation` | Adopt | **Adapt** |
| `elicitation/command_workspace.py` | 504 | 22 | none | Adopt | **Adapt** |
| `pipeline/spec_reader.py` | 56 | 10 | `path_validation`, `wizards.decomposer` | Adapt | **Adapt** |
| `spec/workspace.py` | 995 | 51 | `command_workspace`, `spec_intake`, `spec_reader`, `path_validation`, `state` | Adapt | **Adapt** |
| `elicitation/spec_intake.py` | 229 | 11 | `intake_template`, `meta_workflows.models` | Adapt | **Adapt** |
| `memory/harness_adapter.py` | 423 | 26 | `file_stash`, `personal`, `session_stash`, `path_validation` | Adapt | **Adapt** |
| `wizards/decomposer.py` | 604 | 66 | `workflows.compat` | Reference | **Reference** |
| `memory/file_stash.py` | 495 | 53 | `atomic_io` | Reference | **Reference** |
| `memory/personal.py` | 565 | 75 | seven modules | Reference | **Reference** |
| `memory/session_stash.py` | 690 | 61 | seven modules | Reference | **Reference** |
| `attune_bridge.py`, `memory_bridge.py` (Harness) | 245 | | | Drop (D8) | **Drop** |

"Its tests" counts `def test_` in files named `test_<module>*.py`, except the
decomposer, whose 66 tests are in `tests/unit/wizards/test_wizard_decomposer.py`.
The first proposal missed that file and said the decomposer had none.

## Why each verdict

**`path_validation.py`: adapt.** One function, no imports, 19 tests, and every
other candidate calls it. Harness has no single equivalent, only containment
checks written inline in several modules. It moves down because its Windows
branch matches substrings: `unix_markers = ["\\etc\\", "\\sys\\", "\\proc\\",
"\\dev\\"]` (line 70), and `"\\program files"` a few lines earlier. A plan at
`C:\repo\etc\plans\x.md` is refused. Harness must run on Windows, and every spec
read would go through this function. The seam is that check. It is also named
`_validate_file_path`, a private name used across modules; carrying it is the
moment to give it a public one.

**`spec/state.py`: adapt.** The state is a `schema_version` comment inside the
plan file, written through a temporary file and `os.replace`, with the largest
test base of any candidate. All seven plans in Harness's own `.claude/plans/` on
the wip branch carry the format. It moves down on the fourth test and on R4:

- It stores `schema_version` and never branches on it
  (`schema_version=int(data.get("schema_version", 0))`, line 157), so any version
  loads. Harness already refuses unknown versions: `spec_bridge.py:43` accepts
  only 1 and 2 and otherwise raises "Unsupported Spec state comment". Adopting
  `state.py` as written would replace a refusal with a guess, which R4 forbids.
- Its current version is 2 (line 36); R4 speaks of schema version 1. R4 needs
  restating to cover both.
- `find_resumable_plans` defaults to the relative path `".claude/plans"`.
- `task_receipts` is a list of plain dictionaries and does not map onto the
  acceptance record `work_contract.py` validates.
- `save_state` appends or substitutes the comment wherever it finds it, while
  `spec_bridge.py` requires a single trailing state comment. A comment not at the
  end of the file would be written by one and refused by the other.

**`command_workspace.py`: adapt.** Its own body imports nothing from Attune AI,
and its adapter protocol (`create`, `project`, `apply`) never inspects domain
state, which is the separation D2 wants. Patrick ruled "keep". Two things move
it down:

- It calls `attune_forms.form_events.log_workspace_stage`, which appends to
  `telemetry/form_events.jsonl` under `ATTUNE_FORMS_HOME`, else `ATTUNE_HOME`,
  else `~/.attune`: the home directory of the product being deprecated.
- Its locks are `dict[str, asyncio.Lock]` (line 217): in-process and never
  evicted. R1 requires that a stale or replayed decision is refused. Across two
  processes these locks prove nothing, and Harness's task store is a
  cross-process record.

In Attune AI, importing it also runs `attune/elicitation/__init__.py`, which
loads the workflow registry and registers templates as a side effect. That
coupling disappears once the module lives in Harness, but it means the module
has only ever been tested with those side effects present. Whether it becomes
the one decision surface behind task-first navigation belongs to Task 3.

**`spec_reader.py`: adapt.** The reader is 56 lines and sound. Its seam is that
it builds a `TaskDecomposer(workflow=None)` only to reach that class's XML
parser. The work is to lift the `<task>` parser and the `DecomposedTask` shape
out of the decomposer: 189 of its 604 lines, measured.

**`wizards/decomposer.py`: reference.** Most of it decomposes work for Attune
AI's wizards. What it takes from `workflows.compat` is one name, `ModelTier`.
Only its XML parsing is wanted. Its behaviour, including the regex fallback and
the warnings for dropped content, and its 66 tests are the reference for the
lifted parser.

**`spec/workspace.py`: adapt.** The core is what D2 needs:
`SpecWorkspaceState` is documented as state "the host never interprets", and
lifecycle receipts are presented "without reinterpretation". The first proposal
named the 164-line `_view_data` as a seam. It is not: it builds plain
dictionaries for `attune_forms`, which is already Harness's `review` extra. The
real seams are three: `spec_intake`, `read_spec`, and its import of
`attune_harness.spec_handoff`, by which the two products currently import each
other. Carrying it into Harness ends that cycle. The coupling also runs the
other way: `work_contract.py:544-553` already validates a "Spec collector
receipt" with an `adapter_version`, so Harness is shaped around this adapter.
That argues for adapting it, not writing against it. It is still the largest
single piece, with fewer seams than first thought.

**`spec_intake.py`: adapt.** `workspace.py` uses four names from it (`OTHER`,
`area_candidates`, `compose_spec_contract`, `existing_spec_slugs`). Carry the
four, not the module. Two corrections to the first proposal: `intake_template`
is not unreviewed Attune AI code, because `attune/elicitation/__init__.py:61`
aliases it to `attune_forms.intake_template`; and the real problem is line 116,
`TEMPLATES["spec-intake"] = SPEC_TEMPLATE`, a write into a global registry at
import time. It also takes `FormSchema` from `meta_workflows/models.py`, 466
lines that nobody has read.

**`harness_adapter.py`: adapt, and further from adopt than first proposed.** It
is already written against Harness: it imports `attune_harness.memory_contract`
and `review_contract`, its 26 tests run to 560 lines, and it never resolves a
default backend. But line 111 reads `if os.name != "posix": raise
ValueError("Scoped descriptor reads are currently qualified only on POSIX")`,
and line 119 opens directories with `O_DIRECTORY | O_NOFOLLOW` and `dir_fd`.
Memory through this adapter does not exist on Windows. That is the same gap D6's
Windows note describes for build effects, and 0.2.0's `windows_effects.py` is
the precedent for closing it.

**The three memory stores: reference.** The adapter calls `PersonalMemory(...)`,
`recall_entries` and `recent_entries` to rank results over private snapshots.
The first proposal took that to mean Harness needs the stores' ranking and
called the replacement large and uncertain. The design review read the ranking
and found otherwise. The raw tier is about 35 lines in `file_stash.py`: keyword
overlap, plus `0.5 ** (age / halflife)`, plus a boost for the working directory.
No embeddings. The curated tier delegates to `attune_rag` (`personal.py:265`),
which is already a pinned Harness extra. The stores are 1,750 lines with fifteen
further Attune AI imports, including `authoring.polish`, telemetry and the write
paths Harness must never use (D6: read and convert, never write back). Carrying
them whole would break the note's constraint, "DO NOT bring over old, and far
less than useful code". A Harness-owned reader of the three formats, with one
small ranking function and a call into `attune_rag`, is smaller and safer. The
stores' 189 tests are its characterization cases. `atomic_io` is reached only
through the stores, so it drops out.

## What this means for memory in the first stable release

D10 makes memory a goal for the first stable release if its review allows. The
review allows it on POSIX and not on Windows.

- The format reader and ranking are medium-sized work, not large, and can be a
  spec of their own running beside Tasks 2 to 5.
- What decides the release is the platform. Either memory ships in the first
  stable release as POSIX-only and says so, as `fix` did before 0.2.0; or it
  waits for a handle-based reader on Windows with its own safety review.

That is Patrick's call and is not made here.

## Dependencies these verdicts would bring

Harness's core declares no dependencies today.

- **`defusedxml`: an open question, not a requirement.** The decomposer uses it
  and falls back to regex when parsing fails. The first proposal said the
  standard library parser is not a safe substitute. But Harness already parses
  the same plan files with it: `spec_bridge.py:12` imports
  `xml.etree.ElementTree`, and line 58 calls `ET.fromstring(block)`. Either that
  is already a weakness in shipped Harness, or `defusedxml` is unnecessary here.
  Nobody has tested entity expansion against it. Settle this before Task 2, and
  fix `spec_bridge.py` in its own change if it turns out to be the first.
- **`PyYAML`: needed, as an extra.** The adapter imports it lazily and only for
  sources with frontmatter, but it parses the owner, scope and classification
  labels that decide authority. Replacing it with a regular expression would
  weaken a security check. It belongs to a memory extra.
- **`structlog`: avoided.** `file_stash.py` imports it and the adapter constructs
  `FileStashBackend`, so the adapter needs it today. With the stores as
  reference it never arrives.

`attune_forms` is already the `review` extra.

## The salvaged edits are already committed

The note lists "salvaged September edits to `spec/state.py` and
`spec/workspace.py`", preserved in `~/attune-salvage` as uncommitted. The patch
`codex_shared-memory-adoption.patch` applies cleanly in reverse to the branch
tip and does not apply forwards. Every edit in it is already in the branch.
There is nothing separate to review.

## A first estimate

The October plan's 270,000 working tokens assumed Attune AI stays installed, and
said itself that it had no measured baseline. No token figure is given here for
the same reason. Sizes are lines carried or written, with their tests.

| Work | Size | Depends on |
| --- | --- | --- |
| Adapt `path_validation.py`: fix the Windows check, make it public | Small: 93 lines, 19 tests, plus Windows cases | nothing |
| Lift the `<task>` parser; adapt `spec_reader.py` | Medium: 189 plus 56 lines; 10 tests, plus cases from the decomposer's 66 | the `defusedxml` question |
| Adapt `spec/state.py`: refuse unknown versions, take the plans directory as an argument, agree comment placement with `spec_bridge.py` | Medium: 319 lines, 130 tests to port | the two above |
| Adapt `command_workspace.py`: move locking to the task store, decide where form events go | Medium: 504 lines, 22 tests | Task 3's design for R1 |
| Carry four names from `spec_intake.py` without the registry write | Small to medium: `FormSchema`'s module is unread | nothing |
| Adapt `spec/workspace.py` at three seams | Large: 995 lines, 51 tests | all of the above |
| Memory: a reader for three store formats, one ranking function, the adapter | Medium on POSIX: 423 lines and 26 tests for the adapter; 189 tests to characterize the reader | its own spec |
| Memory on Windows | Unsized | a handle-based reader and its safety review |

`workspace.py` is the critical path for the spec authority. Windows is the
critical path for memory.

## README status, as far as it was checked

The note lists "an honest README status" under "cannot wait". These rows of the
README's qualification table were checked on September 21 and are accurate
today: plan acceptance needs the Attune AI Spec runtime; memory ships but is not
activated; `ship` and `reflect` do not exist. The section "Harness and
attune-ai" says Harness "does not replace those today", which stays true until
Patrick announces the deprecation. The rest of the README was not reviewed.

## Review record

D5 requires that each adopt or adapt verdict is reviewed by agents whose models
differ from the proposer's, with the team, roles and models recorded.

| Role | Model | What it did |
| --- | --- | --- |
| Proposer | Claude Fable 5.1 | Read the modules, measured them, wrote the first table |
| Design skeptic | Claude Opus | Told to show each verdict wrong. Read the eleven modules, their package `__init__` files and the four Harness modules they meet. Read-only |
| Fact checker | Claude Sonnet | Checked 18 numbered factual claims against the files. Read-only |

All three are Anthropic models. D5 asks for different models, and these are; it
does not ask for different vendors, and no other vendor's model was configured
for this task.

**Fact checker:** all 18 claims true, including every line count, test count and
import list, the salvage result and the README rows. One measurement was
sharpened: the decomposer's XML span is 189 lines, where the draft said "about
200".

**Design skeptic:** agreed with nine of the eleven verdicts and disagreed with
two. One of the nine came with a Windows caveat serious enough to move it too. Every finding below was checked against the cited
line by the proposer before it changed this document.

| Finding | Effect |
| --- | --- |
| `state.py` loads any `schema_version`; Harness already refuses unknown ones | `state.py`: adopt to adapt |
| `command_workspace.py` logs to `~/.attune` and locks in-process only | `command_workspace.py`: adopt to adapt |
| `path_validation.py` refuses legitimate Windows paths | `path_validation.py`: adopt to adapt |
| `_view_data` is not a seam; `spec_handoff` and the collector receipt are | `workspace.py` seams corrected |
| `intake_template` is `attune_forms`; line 116 writes a global registry | `spec_intake.py` reasoning corrected |
| The adapter refuses to run off POSIX | Memory section rewritten; Windows is the deciding question |
| Ranking is 35 lines plus `attune_rag` | Memory reader resized from large to medium |
| Harness already parses plan XML with the standard library | `defusedxml` changed from requirement to open question |
| `structlog` arrives through `file_stash.py` | Added to dependencies, as avoided |
| The decomposer has 66 tests in a file of another name | Table corrected |

The skeptic did not run any test, did not test entity expansion, and did not
read `attune_rag`. The fact checker did not read `intake_template`,
`meta_workflows.models`, `workflows.compat` or `atomic_io`.

## Not verified

- No Attune AI test was run. Test counts are counts of test functions, not of
  passing tests.
- `meta_workflows/models.py` and the stores' further imports were not read.
- Whether the standard library XML parser is safe for plan files.
- That the carried tests pass under Harness. R5 requires it; it is Task 2's
  evidence, not this table's.
- Behaviour on Windows. Every Windows statement here comes from reading code.
