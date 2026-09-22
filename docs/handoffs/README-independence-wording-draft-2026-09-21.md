# Draft: README independence wording, corrected

Drafted 2026-09-21 against `README.md` at tag `v0.1.0` (the text shown on the PyPI
page). On disk only. Nothing here is applied, committed or authorized.

**Where it can land.** Not on `v0.1.0` (the tag must not move) and not on the PyPI
page for 0.1.0 (frozen). It belongs on `main`, which became the trunk for 0.2.0 when
PR 5 merged as `3b3b5ff` on 2026-09-21, and reaches PyPI with that release. Evidence for each change is in the opportunity
log entry of 2026-09-21 ("the published 0.1.0 README overstates the harness's
independence"), commit `b67a67c` on `wip/local-snapshot-2026-09-19`.

**No blanks remain.** For change 3 Patrick chose the plainer origin sentence on
2026-09-21. He named the memory system as an example of code brought over from
attune-ai; the full list was not established, and it was not inferred from the
source.

Four changes (the fourth now touches three table rows). Each shows the published text, the replacement, and why.

---

## Change 1: the install paragraph (published lines 26 to 27)

Published:

> The core has no dependencies and needs Python 3.10 or later. No provider SDK, no
> API key, and no attune-ai installation.

Replacement:

> The core install has no dependencies and needs Python 3.10 or later. That install
> pulls in no provider SDK and no attune-ai, and needs no API key. Provider SDKs and
> the Attune libraries arrive only through the extras below. The native Claude and
> Codex participants run the `claude` and `codex` command-line tools, which you
> install and sign in to yourself. Two features currently call attune-ai directly;
> these limits are listed under
> [what is not qualified](#what-is-qualified-and-what-is-not).

Why: the published sentence is true of `pip install attune-harness` and reads as a
claim about the whole harness. Scoping it to "the core install" keeps the claim that
a clean environment demonstrates (zero packages pulled, verified 2026-09-21) and
points at the exceptions instead of leaving the reader to find them.

## Change 2: the "Harness and attune-ai" paragraph (published lines 125 to 129)

Published:

> Harness is the successor I am building to
> [attune-ai](https://pypi.org/project/attune-ai/). It starts from a constraint
> attune-ai never had: the core must run with no provider SDK and nothing else from
> the Attune family installed. The Attune libraries come in as extras, where you can
> see exactly what each one adds.

Replacement:

> Harness is the successor I am building to
> [attune-ai](https://pypi.org/project/attune-ai/). It starts from a constraint
> attune-ai never had: the core must install and run with no provider SDK and nothing
> else from the Attune family present. `attune-forms`, `attune-verify` and
> `attune-rag` come in as pinned extras, where you can see exactly what each one
> adds. Provider SDKs come in the same way: `anthropic` behind `memory-native` and
> `voyageai` behind `voyage`. Harness uses no OpenAI SDK. It reaches Anthropic and
> OpenAI models for native planning, building and review by running their
> command-line tools, `claude` and `codex`, as supervised subprocesses; those tools
> and their sign-ins are yours to install, and Harness pins neither.
>
> That separation is not finished. Two features still call attune-ai at runtime, and
> no extra declares it: memory context loads attune-ai's memory adapter, and
> `plan --accept` runs through attune-ai's Spec workspace. With attune-ai absent,
> both are unavailable. Removing those calls is planned work, not a shipped fact.

Why: "come in as extras, where you can see exactly what each one adds" is true of
the three libraries and false of attune-ai, which `pyproject.toml` names nowhere
while `memory_context.py` and `spec_bridge.py` import it. Corrected 2026-09-21: on `main`
at `3b3b5ff`, `spec_bridge.py` imports three attune-ai modules
(`attune.pipeline.spec_reader`, `attune.elicitation.command_workspace`,
`attune.spec.workspace`), not two; the first search missed indented imports. Four
modules import attune-ai at ten sites in all, counting the two plugin bridges. Naming the two SDKs closes
the gap between "no provider SDK" and what `memory_native.py` and
`voyage_provider.py` do. The last sentence is deliberately modest: the cut is
direction N1 of the native memory scoping note, which is a scoping draft, and the
Spec tie is covered by no spec at all.

On provider tooling (added 2026-09-21 after Patrick said the harness uses SDK code
from both OpenAI and Anthropic). Checked at `v0.1.0`, and on `main` and `wip`:
the Anthropic half is right, `memory_native.py` imports the `anthropic` SDK. The
OpenAI half is not an SDK: the string `openai` appears nowhere under `src/` or in
`pyproject.toml` on any of the three lines. What is true, and was missing from the
first version of this draft, is that `native.py` reaches both providers through
their CLIs: `claude -p --output-format json --json-schema ...` and
`codex exec --json --output-schema ...`, run through the harness's own process
supervisor, with the executable name defaulting to the provider name. That is a
real dependency on Anthropic's and OpenAI's tooling which "No provider SDK" hides,
so the replacement names it. If Patrick means something else, such as source adapted
from either SDK, no trace of it was found and he would need to point at it; nothing
here asserts it. "Harness pins neither" should be checked: no CLI version pin was
found in `native.py`, but the qualification receipts may record the versions used.

**Correction, 2026-09-21: "needs attune-ai installed" is too generous for memory.**
`attune.memory.harness_adapter` exists in no released attune-ai. In `~/attune-ai` it
is only on branch `codex/shared-memory-adoption` (`c170febaf`); it is not on attune-ai
`main`, no tag contains it, and the branch has no PR, so attune-ai 16.4.0 on PyPI
almost certainly lacks it (inferred; the wheel was not inspected). Installing attune-ai
does not make harness memory work. The memory sentences in changes 2 and 4 below must
not land as written. Until the adapter is brought into Harness, the honest wording is:
"Memory context is unavailable in this release: it depends on an adapter that has not
been released. The command reports `unavailable` and exits 2." The failure is safe:
`memory_cli.py` catches the `ImportError` and returns that report. See
`session-starter-cut-attune-ai-dependency-2026-09-21.md`.

Wording to check before it lands: "both are unavailable". For memory this rests on
the scoping note's 2026-09-19 observation that `memory capabilities` reports
`unavailable` and exits 2; it was not re-run on 2026-09-21. For `plan --accept` it
rests on the published qualified table. If an installed-environment check shows
either one fails differently (a traceback instead of an unavailable report, say),
the sentence must say what actually happens.

## Change 3: a sentence on where the code came from (new; same section, after change 2)

Decided by Patrick, 2026-09-21: use the plainer form.

> Parts of Harness, the memory system among them, began as attune-ai code that I
> brought over and modified.

Why: no file at `v0.1.0` says this (README, `docs/`, `src/`, `LICENSE`,
`CHANGELOG.md` searched; there is no `NOTICE`). "Nothing else from the Attune
family" sits badly beside code that started there. This is an accuracy point, not a
licensing one: both projects are Patrick's and both are Apache-2.0. The plainer form
names the one area Patrick confirmed and does not claim a complete list.

Open decision: whether a `NOTICE` file or a short provenance page under `docs/` is
wanted as well. Not drafted.

## Change 4: three rows of the qualified table

The `Plan acceptance` row already concedes the Spec tie. Tighten it so the package is
named, and make the `Memory` row state the tie it currently omits.

Published `Plan acceptance`, "Not qualified" cell:

> `plan --accept` needs the optional Attune AI Spec runtime in the same environment

Replacement:

> `plan --accept` needs attune-ai installed in the same environment: it runs through
> attune-ai's Spec workspace. No extra installs it

Published `Memory`, "Not qualified" cell (unchanged text elided):

> The memory modules and the `memory-native` extra ship in the wheel but are
> experimental and not activated for live memories. ...

Replacement, one sentence added at the front:

> Memory context needs attune-ai installed in the same environment; no extra installs
> it, and without it memory reports unavailable. The memory modules and the
> `memory-native` extra ship in the wheel but are experimental and not activated for
> live memories. ...

Published `Models`, "Qualified" cell:

> CI calls no model provider. Native Claude and Codex adapters have recorded
> comparisons

Replacement, one sentence added at the end:

> CI calls no model provider. Native Claude and Codex adapters have recorded
> comparisons. They run the `claude` and `codex` command-line tools, which Harness
> neither installs nor pins

Why: this table is where the README promises the limits are "listed, not implied".
The memory tie is currently implied by nothing, and the native adapters' reliance on
two provider CLIs is stated nowhere in the README.

---

## Not changed, deliberately

- The install table ("Install only what you use"). Its rows are accurate, including
  the `memory-native` row, which already names `anthropic`, `ANTHROPIC_API_KEY` and
  paid calls.
- `attune_bridge.py` and `memory_bridge.py`. They import `attune.plugins.base`
  because they are plugins meant to be loaded by attune-ai. Nothing in Harness
  imports them and they are not entry points. A plugin importing its host is
  expected, so the README need not list them as a dependency of Harness. One sentence
  in the docs saying they exist and when to import them would be enough; not drafted.
- The closing paragraph ("attune-ai is still where cross-session memory ... live").
  Still accurate.

## Checks before this lands

1. Done: Patrick chose the plainer origin sentence (change 3).
2. An installed-environment check with attune-ai absent records what memory context
   and `plan --accept` actually do, and changes 2 and 4 are made to match.
3. The README's pinned links still point at a tag that exists for the version being
   released (they are pinned to `v0.1.0` today).
4. A README change on a release branch starts a qualification run; re-qualify and
   dry-run before any publish, as with 0.1.0.
