# Attune Harness 1.4.0 candidate release notes

**Combined locally, unpublished.** Exact-source software, installed-wheel and
platform evidence is recorded in the release handoff. Human form assessment and
publication remain pending. Version selection does
not authorize publication. These notes describe the combined preparation based on main
`209a822a2d49ba66fd3e6ab3f918d4e5a118a699`; the
[readiness record](release-readiness-1.4.0.md) identifies the component heads and remaining readiness decisions.

Use [released 1.3.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.3.0)
for a published installation. After 1.4.0 publication, install it separately:

```sh
pipx install 'attune-harness[all]==1.4.0'
```

Python 3.10 or later is required. Base dependencies and optional extras retain
their existing pins; `all` still excludes experimental native memory.
Installing the package grants no model, upload or spending authority.

## Changes already in the preparation base

- **Saved forms:** The browser opens the current form directly when one draft
  is registered. Reopened intake shows saved answers above remaining questions;
  accepted requests show their answers read-only. Saved-request inspection and
  supporting technical details retain the owner record and checkpoint checks.
- **Readable consultation evidence:** `source-review` and `roundtable`
  `prepare`, `status` and `evidence` accept `--format markdown`. These views show
  retained identities, verdicts and numbered frozen citations. JSON remains the
  default; a readable view does not authenticate a model or establish support.
- **Roundtable setup and seat checks:** `init --for roundtable` writes a
  configuration using explicit model IDs. Both consultation verbs provide
  `check` for local binary/login checks and model-access uncertainty. These
  operations prepare or inspect configuration; they do not dispatch a model.
- **Batch citation assessments:** `assess-citation --decisions FILE` records a
  group of host judgments against one evidence view, with one checkpoint
  advance. All decisions are saved or all refuse. The judgments remain advisory.
- **Recovery and qualification:** Shared recovery-cursor code and interruption
  fixtures strengthen existing recovery boundaries. Windows installed-wheel
  qualification uses fresh environments. Windows qualification budgets and
  supplemental measurement headroom are documented separately from behavior.
- **Instructions and entered text:** Revised guidance names controls directly.
  Prose uses the reading font; technical values use monospace. Entered wording
  and capitalization are preserved.

The preparation also adds full-coverage timing and slow-test diagnostics using
the existing Python watchdog. The test selection, source denominator, coverage
admission checks and process budgets remain unchanged. This diagnostic correction
does not establish a performance fix for the earlier macOS timeout.

## Combined approval wording and reload restoration

The local candidate includes approval-copy
[PR #256](https://github.com/Smart-AI-Memory/attune-harness/pull/256), reviewed at
`e4d09e95941e77b10263d4b7184915ff1c50f475`, and the reload series reviewed at
`af59b5b9d9278dcdb802584178ebbf978657282f`. Their original source and review
receipts remain preserved; neither component receipt qualifies their combination.

Click **Approve this work request** to record approval of the reviewed request,
or **Keep as draft** to leave it unapproved. Each choice explains its consequence;
neither starts work. A same-page reload restores the existing current form only
when its listener, draft, checkpoint, collector and browser ownership remain
current. Automatic restoration requires usable session storage, navigation timing
and an exclusive Web Lock. Saved answers remain visible and remaining fields stay
blank; unsaved typing is not restored. Stale or uncertain recovery requires
deliberate reopening and never replays a submitted response.

The revised wording, reopening behavior, keyboard use and human comprehension
must be assessed on this combined candidate. Synthetic client tests do not
qualify native browser lock scheduling, copied-tab or history behavior. Software
checks alone do not establish that a new user understands approval or can complete
the form. The live installed practice remains separate from this local candidate.

## Compatibility and limits

The v1 contract remains in effect and the deprecation list is empty. Existing
valid defaults and JSON envelopes remain unchanged; the CLI surface deliberately
adds options. An incomplete single `assess-citation` call still exits 2, but now
returns a JSON refusal naming missing options instead of argparse usage text.

Browser saving is not approval, and approval does not start work. Browser build
grants, dispatch, resume and broader GUI controls remain future work. The forms
server retains registration, loopback, session/origin, stale-checkpoint and
single-use-response boundaries. A private launcher link is listener access data,
not a permanent task link.

Harness checks declared criteria and retains receipts. It can expose defects and
unsupported claims; it cannot guarantee hallucination-free or universally
accurate AI output. Inspect the check, its evidence and its limits before relying
on the result. Offline consultation tests do not qualify live model quality or
model identity. Experimental native-memory and Windows effects boundaries remain
as documented in the [qualification guide](qualification.md).

See the [CLI guide](cli-guide.md), [consultation guide](model-consultation.md)
and [coverage measurement limits](coverage-measurement.md). The final candidate
needs its own full-suite, noneditable installed-wheel, native-platform,
documentation and derivative evidence before publication is requested.
