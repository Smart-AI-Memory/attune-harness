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

## What the log says so far

Fourteen reviews. Every `src/` change since the command workspace host (#54)
had a request-changes verdict except the one pure carry (#58), so a review
that finds nothing is the exception, not the norm.

By class, over the six reviews with a full record (#58 to #67):

| Class | Findings | Where the author's tests were blind |
|---|---|---|
| test | 13 | The author's mutation runs missed the mutations the reviewer chose, or a test's `match` was too wide to fail |
| claim | 12 | Prose is not executed; the reviewer read every sentence against the code |
| input | 6 | The seam's own inputs, one past the ones the design note listed |
| platform | 4 | macOS ran the suite; the defect needed NTFS, the C runtime or a Windows runner (a fifth, the console script path, was found by the job itself) |
| mapping | 4 | An error path nobody triggered |
| fallback | 2 | A degradation nobody made happen |
| install | 2 | Metadata resolved in a fresh environment, not the developer's |
| layer, round-trip, bound, wait | 1 each | Each one a blocker or a should-fix, none caught by a test |

Two steps of the brief came out of this table: the author runs the brief
first (after the six carried steps in a row where a review found something
the author had called verified), and the Windows traps page, after five
platform findings in one day that no macOS test could show.
