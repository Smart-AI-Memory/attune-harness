# Native memory: decisions, September 23, 2026

[The scoping note](scoping.md) is a dated draft and is not edited. This file
records the rulings Patrick made on September 23, after 0.5.0 shipped and
[the Phase 3 design note](../phase-3-design.md) merged (#87). The rulings
made at the same time on the journey, the plugins, Windows and the order are
[D20](../spec-authority/addendum-2026-09-23.md); the numbers continue one
series across both files.

## D21: the Phase 3 decisions on serving and the store

At about 05:55 UTC Patrick pasted the note's ten decisions and answered
"proceed as recommended". The four on memory are recorded here under the
note's numbering.

**Decision 4, the first surface stays the SessionStart hook, and the prompt
hook is the second.** `memory serve` at session start remains the surface
Patrick uses; a `memory serve --for PROMPT` mode for a UserPromptSubmit hook
follows it. An MCP memory tool waits until a consumer other than Claude Code
asks for it; Codex waits for a Codex user.

**Decision 5, what stops being served.** A node whose id is absent from
`status:active`, and a file-tier stem that carries a `wrong` verdict in
`.verdicts.jsonl`. Nothing else is inferred: no age threshold, no scoring
change.

**Decision 6, 3.4 lands before the freeze.** The scratch record gains an
explicit format name and version, a `writer` field, a compare-and-set on
`stash` and a receipt for an uncertain effect, on both backends; legacy
stores stay read in place; the scratch format's version is the first entry
in the 1.0 compatibility list that Phase 4's freeze (4.1) writes.

**Decision 9, ladder 7 stays outside 1.0.** The corrections lifecycle and
review (N8) is out of 1.0 unless the week with `memory serve` shows
corrections coming back, in which case it returns as a proposal, not by
default.

## A correction to the Phase 3 note, same day

Two sentences in the note's "3.3, serving" paragraph were wrong when merged
and are corrected in the same pull request as this file. "Harness never
reads `status:active`" was false: `memory redis status` counts the set's
members. The serve path still applies no filter, which is what decision 5
changes. "Codex is named in the scoping note and nowhere in `src/`" was
false in letter: `.codex` is one of `repair`'s protected directory names, and
a docstring in `command_workspace` names the Attune AI branch the module was
carried from. No Codex serving surface exists, which was the point. Both
claims came from a search report and were written without running the one
`grep` each that would have settled them; the retro that found them records
the lesson.
