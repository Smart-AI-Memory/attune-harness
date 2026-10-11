# Attune Harness 1.4.0 candidate release notes

**Prepared, unpublished.** Patrick selected the now-merged #233 consultation
changes for this release alongside the approved saved-answer presentation and
companion documentation. The current preparation base is signed #258 merge
`0c252b935c3cbc01e1386aa41e0f7dcc1c7de5b7`. Its actual-main qualification is
owned separately. The #234 golden follow-up, PR #260, has Patrick's update,
verification and merge authorization; its final baseline disposition is pending.
The selected final baseline and combined shipping SHA,
archive hashes and publication date remain unset.

The forms presentation was reviewed at
`3d317e71324b609d5e9f603bf88b447e9007345e` and visually accepted by Patrick.
The first goal-based tutorial is aligned to the same controls. Exact combined
source, installed artifact and native-platform qualification remain required;
component reviews and earlier passes do not qualify this later combination.
The [readiness record](release-readiness-1.4.0.md) identifies remaining work.
Version selection and local preparation grant no publication authority.

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
  accepted requests show their answers read-only. The selected local refinement
  places bold **Saved goal:** and **Done when:** labels inline with their saved
  values and uses **Still needed** to introduce the remaining instructions.
  The saved-answer presentation preserves stored wording, case, spacing and
  line breaks. Scope and success-criterion input still uses one item per
  nonblank line, with each item trimmed before saving.
  Saved-request inspection and
  supporting technical details retain the owner record and checkpoint checks.
- **Concurrent consultation and partial recovery:** First-round seats dispatch
  concurrently after operation-budget admission; round two remains sequential
  and requires a complete first round. Partial rounds retain successful siblings.
  Explicit checkpoint-bound `reconcile --retry-refused` reopens only an eligible
  failed turn, retains prior attempts and captures fresh origin where required.
  There is one operator retry per turn, with no automatic retries; usage may
  repeat. Unknown effects without eligible saved refusal evidence, stale
  ownership and unsupported refusal evidence block recovery.
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

Approval-copy
[PR #256](https://github.com/Smart-AI-Memory/attune-harness/pull/256) is merged
in the preparation base. Its author head was reviewed at
`e4d09e95941e77b10263d4b7184915ff1c50f475`. Merged #257 also includes
the reload series reviewed at
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

Patrick's C09-runtime walkthrough observed saving, accepted-request inspection,
accepted-state reload and unfinished reload with editable remaining input. That
runtime matches all 104 modules of merged #257. The separate exact-source
presentation preview was visually accepted; it does not qualify an installed
revised wheel. Exact Tab order, accessibility-tree and screen-reader behavior,
independent approval comprehension, copied-tab behavior and native lock scheduling
remain unobserved. Earlier launcher failures and their uncertain cause are
retained. Existing practices and unsaved input remain intact.

## Compatibility and limits

The v1 contract remains in effect and the deprecation list is empty. Existing
valid defaults and JSON envelopes remain unchanged; the CLI surface deliberately
adds options. An incomplete single `assess-citation` call still exits 2, but now
returns a JSON refusal naming missing options instead of argparse usage text.

Browser saving is not approval, and approval does not start work. Browser build
grants, dispatch, resume and broader GUI controls remain future work. The
corrected refusal messages describe the forms-only browser companion without
promising browser execution in 1.4.0. The forms
server retains registration, loopback, session/origin, stale-checkpoint and
single-use-response boundaries. A private launcher link is listener access data,
not a permanent task link.

Harness checks declared criteria and retains receipts. It can expose defects and
unsupported claims; it cannot guarantee hallucination-free or universally
accurate AI output. Inspect the check, its evidence and its limits before relying
on the result. Offline consultation tests do not qualify live model quality or
model identity. Experimental native-memory and Windows effects boundaries remain
as documented in the [qualification guide](qualification.md).

The selected release includes the merged #233 concurrency and selective-retry
behavior. #259 strengthens consultation acceptance coverage; its separately
reviewed #260 follow-up remains pending integration. Neither changes browser
execution authority. Existing 1.3.0 tutorials, decks and Help captures
retain their source labels; candidate GUI instructions and derivatives still
need their owners' source-consistent readiness records.

See the [CLI guide](cli-guide.md), [consultation guide](model-consultation.md)
and [coverage measurement limits](coverage-measurement.md). The final candidate
needs its own full-suite, noneditable installed-wheel, native-platform,
documentation and derivative evidence before publication is requested.
