# The standing brief for a different-model review

Every change under `src/` is reviewed by a model other than its author before
it merges (AGENTS.md). This is the brief the reviewing agent is given, so each
pull request adds only what is specific to it. Written after Task 2 of the
spec authority, where four such reviews found five defects the authors' own
mutation tests and differentials had missed: a Windows bypass, a recursion on
deep input, a pattern that could delete a plan body, a second read that
changed task text.

## Before the review

The author runs this brief against their own change first. Six carried steps
in a row had a review find something the author had called verified; the
class-level checks below are cheap and most of those findings were in them.

## The reviewer's position

Read-only. Never edit a file. Work from `git archive <branch>` extracted into
the scratchpad, never from the working tree, which another session or the
author may switch under you. `scripts/review_prep.sh <branch>` makes that
archive, writes the diff against the base beside it and scaffolds the
mutation table. Write probe scripts only outside the repository. Report
findings; the author reproduces each before fixing.

## What to do, in order

1. **Read the original side by side** when the module is carried from
   elsewhere. Everything that is not a declared seam must behave as it did;
   name any silent change (a warning text, a `None`-versus-raise contract, an
   order of results, a translation of newlines).
2. **Try to break the seam the change claims to fix.** The pull request's
   design note names it. Construct the inputs it must refuse and the ones it
   must accept, and the ones in between: empty, duplicated, misplaced,
   unterminated, escaped, at and one over the declared limit, CRLF, a BOM,
   a Windows path.
3. **Measure adversarial input within the declared limit.** Any pattern with
   an unbounded quantifier gets a spam input at the limit and a stopwatch.
   Numbers, not adjectives.
4. **Check the contracts the tests do not.** Which branch is unreachable;
   which test could pass with a plausible bug present; what depends on the
   environment (cwd, platform, root, an installed extra).
5. **Python 3.10 and Windows.** No newer syntax or stdlib; nothing that only
   POSIX provides without a guard. Check the change against each entry of
   [the Windows traps](windows-traps.md): append, case folding, device
   names, replace under an open handle, console script paths.
6. **No `import attune`**, and no dependency on Attune AI, anywhere in the
   new files.

## The report

A verdict line: approve, or request changes. Then findings ordered by
severity, blocker, should-fix, nit, each with what, where (`file:line`), how
it was reproduced or "by reading", and what to change. Then a held list: what
was checked and found fine, so the author knows what not to re-verify.

The author records the review in the pull request under `## Review`: who
reviewed, the verdict, each finding and what changed, the held list in short.
Then one row in [the findings log](review-findings.md), with each finding
sorted into its class; the classes there are what this brief's steps are
rewritten from.
