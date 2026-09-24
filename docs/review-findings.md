# Review findings log

What each different-model review under [the brief](review-brief.md) found
that the author's own tests, mutation runs and differentials had not. One row
per review, with the findings sorted into a short list of classes. The classes
are the brief's raw material: when a class keeps recurring, the brief gets a
step for it, and when one stops, the step can go. Add a row when you record a
`## Review` in a pull request; `scripts/review_prep.sh <branch>` makes the
archive and the diff the reviewer works from and scaffolds the mutation table.

## Classes

| Class | The defect | First seen |
|---|---|---|
| **layer** | A check made at a layer that trusts its caller, so a test of the outer layer passes while the inner guard is absent | #59: the nonce was compared by the bridge, never by the host; a host trusting the client's nonce passed all 24 tests |
| **platform** | Windows, NTFS or APFS behaving differently from the POSIX the tests ran on; see [the Windows traps](windows-traps.md) | #61: a JSONL line torn by the C runtime's seek-then-write append |
| **round-trip** | A value one verb hands out that another verb of the same module does not accept | #66: `search` returned `node:n2`, `node` wanted `n2`; three layers answered `no_results` for memories that exist |
| **bound** | A declared limit measured on something other than what is written or read | #67: the value bound measured compact JSON while the record was written with `indent=2`; a value at 52 percent of the limit vanished |
| **wait** | A wait with no deadline, or one bounded on one platform only | #61: `flock` blocked without a deadline on POSIX, inside the host's asyncio lock |
| **mapping** | An exception that escapes the status mapping and reaches the user as a traceback | #66: an out-of-range port raised `ValueError` past the CLI's `unavailable` |
| **fallback** | A degradation that is missing, or one that degrades the wrong way | #61: a file system that cannot grant the lock dropped every event; #67: `forget` said `True` for an expired file |
| **input** | An input class the seam accepts and mishandles: incomplete, aliased, too long, a symlink | #67: a record with no `value`, a valid key past the file-name limit, a symlinked scratch directory |
| **claim** | A docstring, README, changelog or pull-request body that states something the code does not do | #64: the README's retired constraint; #66: "pointers never bodies" was false for the curated layer |
| **test** | A test that passes with a plausible bug present, asserts almost nothing, or pins the wrong thing | #66: three mutations survived and the live test asserted almost nothing; #64: a test fabricated the old hint |
| **install** | Package metadata or a locked install that resolves to something other than what was intended | #64: `mcp==2.2.0` in the base breaks a co-installed attune-ai; tiktoken's `regex` was unconstrained in CI |
| **carry** | A carried module that differs from its original where the design note declared no seam; found only by reading the two side by side | #80: gate patterns transcribed rather than copied drifted in both directions; a guard run after the frontmatter check that the original runs before |
| **race** | A read, a check and an act on shared state with no lock between them, so another writer's change in the gap is undone or lost | #116, second review: `keys()` read a record as expired and unlinked the path, deleting a compare-and-set that had replaced it in between; 35 in 34,555 over 20 seconds |

## Log

B/S/N is blockers, should-fixes, nits, as the reviewer graded them. The last
column is the finding the author would not have caught alone, or "carry
exact" when the review confirmed a carried module changed nothing.

| PR | Change | Verdict | B/S/N | Classes | What the author had missed |
|---|---|---|---|---|---|
| #29 | Remove the two Attune AI bridge modules | approve | 0/0/n | | Recorded in the pull request |
| #31 | Say what happened when an input is over its limit | approve | 0/0/n | | Recorded in the pull request |
| #33 | Carry path validation, Windows check reworked | request changes | 0/2/0 | platform | The Windows bypass the brief's preface names |
| #34 | Carry the `<task>` parser and the plan reader | request changes | 1/0/0 | input | The recursion on deep input the brief's preface names |
| #42 | Carry the plan state reader and writer | request changes | 2/0/0 | input | The pattern that could delete a plan body |
| #43 | Read legacy plans through Harness's own reader | approve | 0/2/0 | claim | A second read of the file that changed task text |
| #54 | Carry the command workspace host, events and eviction | request changes | 1/4/0 | | Recorded in the pull request |
| #55 | Carry the four spec intake names | approve | 0/1/0 | | Recorded in the pull request |
| #58 | Carry the Spec adapter | approve | 0/0/3 | test | Nothing pinned `PLAN_LIMIT` on the resume path's own read; carry exact otherwise |
| #59 | Switch the bridge to Harness's host and adapter | request changes | 0/4/5 | layer, test, input, claim | The nonce checked only by the bridge; simultaneity never exercised; a hard-linked events file let the host append into `record.json` |
| #61 | Append events under a cross-process lock | request changes | 0/3/5 | platform, wait, fallback, mapping | A Windows-only refusal missing from the set; POSIX `flock` with no deadline; `ENOLCK` dropping every event |
| #64 | The base install carries the journeys | request changes | 1/7/5 | install, claim, test | `mcp` 2.2.0 in the base against attune-ai's 1.29.1 (decided, D15 amended); five documents stating the retired constraint |
| #66 | Read the Redis memory a hydration keeps warm | request changes | 1/7/8 | round-trip, mapping, claim, test | Search ids that `node` would not take, and a test that enshrined it; a `prefix` setting the Lua functions ignored |
| #67 | Working memory behind one interface | request changes | 2/5/6 | bound, platform, input, fallback, test | A bound on the wrong bytes; case-folded file names; `CON` as a key; no reclaim of expired files |
| #71 | `memory serve`, the digest as text for a hook | request changes | 2/4/6 | fallback, claim, input, bound, mapping | A pipe whose reader has gone turned exit 0 into exit 120 at the interpreter's exit flush; a `None` stream; ANSI and NUL reaching the banner; an O(n²) trim that could outlast a hook timeout |
| #72 | The lease waits a bounded time | request changes | 0/3/5 | fallback, claim, input, test | A lock the file system cannot grant waited the whole bound and was called busy; two documents still said the refusal was immediate; `nan` as the bound looped forever; dropping the poll's sleep survived every test |
| #80 | The native memory reader | request changes | 3/9/8 | bound, carry, input, mapping, fallback, test | A bare-key rule quadratic in a long key-shaped run; nine strings the adapter's gate blocks that the transcribed patterns let through, and eleven it passes that they blocked; a raw row with no `topics` key refused; eleven controls whose mutants survived |
| #81 | Provenance and staleness on document items | approve with should-fixes | 0/5/6 | claim, bound, test | A docstring naming a `None` contract the code did not have; the verdict log re-read per hit; three volatility rows, the tombstone-before-verified order and the quote stripping unpinned |
| #82 | The native reader as the default | request changes | 0/3/7 | test, claim | A lexical guard that allowed the fallback import anywhere in the file and a runtime test that never invoked a verb; two acceptance criteria narrowed without a ruling; a release-gate label that survived skipping the read |
| #93 | One qualification run per release branch; the Node 24 pins; the approval script | fix first | 3/1/2 | input, fallback, layer | The release-branch skip keyed on the branch name alone, which a fork controls; the approval script exited 0 on a reply with no environment; the required check's pass branch never consulted the classifier, the shape #82 had shown |
| #94 | The MCP receipt deadline named; a miss reports its wait | fix first | 2/0/3 | test, claim | The second observe passed no task, so a miss after cancellation reported the call as still pending; the comment credited this test's Windows timings to its sibling |
| #95 | The Windows append emulated, so the lock's removal fails everywhere | merge | 0/1/2 | claim, test | The docstring said the children were released together; the overlap was host timing, measured at 98 percent; a real barrier now |
| #98 | The task reader parses each top-level block on its own | fix first | 2/2/1 | input, test, claim | Found by fuzzing 4,000 plans: a block closed `</task >` vanished, and a self-closing task beside a comment mis-split and dropped a task; the orphan warning lost; three mutations survived, one test did not fail under its own mutation |
| #99 | One retrying replace for the plan-state and Voyage writers | fix first | 1/5/1 | test, platform | A guard a space or a pathlib spelling escaped; the retry never asserted on POSIX; a refusing stub that finished with `Path.rename`, which fails only on the Windows job, reproduced by emulation; an import alias that evaded the guard |
| #100 | The memory CLI binds structlog once, to a stream resolved at write time | fix first | 0/4/2 | fallback, test, claim | A `None` stderr and a gone pipe, the two degradations the old binding had survived by accident, the second turning exit 0 into 120 at the interpreter's flush; a stub that kept O-67's condition unmet; structlog left configured after a test |
| #106 | The acceptance host and the plan import move to `work_accept` | fix first | 1/1/8 | test, claim | The two re-pointed CLI paths had no test, so a broken import left the suite green; five of six guard mutations survived, on main too; a differential with no mutation sensitivity of its own; counts that did not reproduce |
| #107 | `spec_bridge` is `spec_legacy`; the gate tests take the host's name | merge | 0/0/3 | claim | Three citations in the live design note to files the rename removed; a retargeted `.py` link the link checker never sees |
| #108 | The R2 journey as a test, a gate section and a document | fix first | 0/4/5 | claim, platform, test, fallback | Three receipt fields the gate asserted on were literals that could not be false; a Windows refusal from any module naming the platform would have passed as the sanctioned one; a journey failure would have been filed as a memory failure; a whole file skipped when a base dependency was absent |
| #110 | `plan --accept` walks the execution stages | merge | 0/2/5 | claim, test | The walked accept was indistinguishable from the human's in the evidence file; the design note still called `gate_running` dormant; the one new user-visible string had no source and no test |
| #115 | `plan --import-plan --allow-outside-project`: another project's spec state, with a receipt (spec authority Task 5, 3.2) | fix first | 0/4/4 | bound, fallback, claim, test | A receipt refused after the record was saved reported the landed conversion as `failed`, and the 1 MiB receipts bound was two to eight conversions away because each line repeated the plan's prose; whether a reimport wrote a receipt depended on the file existing; `spec_state: null` for a plan whose comment the reader ignored; three guards surviving mutation |
| #116 | The scratch record as a versioned format with a writer, compare-and-set and an uncertain receipt (native memory Task 5, 3.4) | fix first | 0/3/6 | claim, input, fallback | The uncertain receipt's rule, "a record at version N means it did", held for one writer only; `version` was documented as exact while a plain stash overwrites a compare-and-set; the published reader contract was not met, an `expires_at` ending in `Z` read as expired and `keys()` deleted the record, a naive stamp raised past `except ValueError` |
| #116, second review | The same, at the fixed head `6c4d624` (Claude Opus 5.5) | request changes, merged before the fix | 0/1/3 | race, claim, input | `keys()` deleted a record a compare-and-set landed after it read the expired one, so the compare-and-set reported `ok` for a write that was gone (reproduced, two processes); `forget` takes no lock, so file and Redis differ on a compare-and-set racing it; the new stamp grammar accepted a trailing newline and non-ASCII digits. Merged at the reviewed head; fixed in #125 |
| #118 | Plugin bundles signed, revocable and declaring their capabilities; the Windows probe (4.3, first cycle; D29.1) | fix first | 0/4/11 | bound, test, claim, platform | An `artifact.sig` inside its 16 KiB bound that cost gpg 27 s per check (a compressed message over 6.9 GB of zeros); five guards without a test and 13 of 46 mutations surviving; gpg reading the user's options while the docs said they play no part; a signed bundle failing on a CRLF checkout, the first time a digest crosses machines; `shutil.which` preferring the working directory on Windows |
| #118, second review | The same, at the fixed head `6025ca3` (Claude Opus 5.5) | request changes, merged with the should-fix open | 0/1/3 | bound, claim, test, input | The first review's fix validated only the first armour block while gpg read the whole file, so a good signature followed by a compressed message (773 bytes) still cost gpg 0.69 s against 0.03 s; the legacy `review` path does not recheck the registry mid-run, narrower than the spec's T9 row; the probe fails rather than skips without the `redis` extra; the walk splits lines where gpg does not. A first draft's claim that revocation never reaches an accepted run was wrong, corrected before posting after the cross-review below |
| #118, cross-review | The same (Claude Sonnet 5, dispatched by the reviewer above) | approve | 0/1/2 | input, test, claim | An `END` line before the `BEGIN` made a good signature refuse (fail-closed); the import count cannot see a second certificate inside one signer's block; the receipt names one signer when two signed. It also showed the task, MCP and resume paths reread the registry, which corrected the review above |
| #123 | D30, the host surface's seven decisions; the deprecation milestone's rows (docs only) | approve | 0/0/3 | claim | A heading "After 1.0.0" over rows the next sentence placed in the candidate period; "same columns as the phases" for a table with different ones; four to five October cycles missing from the plan's count |
| #124 | The compatibility list, the verb surface as data, the README example as a test (4.1, first cycle) | request changes | 0/1/4 | test, claim | The surface recorded positionals by name only, so an optional positional made required, the case the freeze note says must fail, passed; the API snapshot's schema-version line was a literal the test wrote itself; the page said exit codes were pinned row by row where two verbs have no row, and that the guard fails only on non-additive changes |
| #124, the fixes | `182603a`, the fixes to the review above (Claude Sonnet 5 reviewing Claude Opus 5.5) | approve | 0/1/2 | input, claim | An arity the table could not render (argparse's `REMAINDER`, a count) fell to a branch that printed misleading text instead of failing; the page's "`...` takes one or more" was untrue for `[name ...]` |
| #125 | `keys()` no longer deletes a record a compare-and-set landed (the fix for #116's second review) | approve | 0/1/2 | test | The race test passed with the unlink moved outside the lock, a real check-then-act gap; no test pinned a planted `.scratch.lock` on the `keys()` path. Codex's GitHub review of the same pull request found nothing |

## What the log says so far

Nineteen reviews. Every `src/` change since the command workspace host (#54)
had a request-changes verdict except the one pure carry (#58) and the
provenance port (#81), so a review that finds nothing is the exception, not
the norm.

Twenty-nine by the evening of September 23. The overnight run and Task 4
added ten: five fix-first verdicts and five merge, and every merge verdict
still carried something fixed before the merge. The classes recur: claim in
nine of the ten, test in eight, fallback and platform in three each, input in
two, layer in one. Three of the ten reviewed no `src/` at all, tests, scripts
and workflow assertions (#94, #95, #108), and found the same classes as the
rest; #108's three receipt fields that the gate asserted on but that could
not be false are the plainest claim finding in the log, an assertion with
nothing to fail. The one platform finding no macOS run could show, #99's
stub finishing with `Path.rename`, was reproduced by emulating the Windows
refusal, the shape the brief now asks for.

September 24 added eight rows: second reviews of #116 and #118 at their
fixed heads, a cross-review of #118 by a third model, and first reviews of
#123, #124, #124's own fixes and #125. Two lessons. A second review of a head
that already carried a first review's fixes still found a should-fix both
times, and both were in the first review's own fix: #118's packet walk
checked a decoding gpg does not use, and #116's cleanup raced the
compare-and-set the pull request added. And a merge that runs ahead of a
posted review lands its finding on `main`: #116 merged at the reviewed head
with the race open, and #125 fixed it the same morning. The cross-review
earned its place the other way, by correcting the reviewer: a should-fix that
revocation never reaches an accepted run was wrong, and reading the three
call paths it named showed so before the review was posted. The new class,
race, is the first finding in the log that needed two processes to show.

By class, over the eleven reviews with a full record (#58 to #82):

| Class | Findings | Where the author's tests were blind |
|---|---|---|
| test | 22 | The author's mutation runs missed the mutations the reviewer chose, a test's `match` was too wide to fail, or a proof only constructed what it claimed to exercise |
| claim | 21 | Prose is not executed; the reviewer read every sentence against the code, design-note criteria included |
| input | 9 | The seam's own inputs, one past the ones the design note listed |
| carry | 9 | A carried module read against its original, line by line: patterns, order of checks, defaults, the `None` contract |
| bound | 6 | A limit measured on the wrong bytes, a loop quadratic in what the server returns, a sidecar re-read per hit |
| mapping | 6 | An error path nobody triggered |
| fallback | 6 | A degradation nobody made happen: a gone pipe, a `None` stream, a lock no file system grants, a dangling symlink |
| platform | 4 | macOS ran the suite; the defect needed NTFS, the C runtime or a Windows runner (a fifth, the console script path, was found by the job itself) |
| install | 2 | Metadata resolved in a fresh environment, not the developer's |
| layer, round-trip, wait | 1 each | Each one a blocker or a should-fix, none caught by a test |

Two steps of the brief came out of this table: the author runs the brief
first (after the six carried steps in a row where a review found something
the author had called verified), and the Windows traps page, after five
platform findings in one day that no macOS test could show. Phase 2 added
a third lesson without a step yet: a carried module's patterns are copied
from the original's source, never transcribed from a description of it; the
one transcription (#80) drifted in both directions and a differential that
compared results could not see it, only a reading of the two side by side.
