# Attune Harness 1.4.0 release notes

These notes describe the bounded 1.4.0 package, its compatibility and limits.
Use the [1.4.0 written forms walkthrough](tutorials-next-release-candidate.md#save-and-approve-a-clear-work-request)
to practice saving and approving a work request. The
[preparation readiness record](release-readiness-1.4.0.md) retains dated source,
software-check and human-observation evidence; its historical preparation pins
do not identify a later installed artifact.

Install 1.4.0 in its own environment:

```sh
pipx install 'attune-harness[all]==1.4.0'
```

Python 3.10 or later is required. Base dependencies and optional extras retain
their existing pins; `all` still excludes experimental native memory.
Installing the package grants no model, upload or spending authority.

## Changes in 1.4.0

- **Saved forms:** The browser opens the current form directly when one draft
  is registered. Reopened intake shows saved answers above remaining questions;
  accepted requests show their answers read-only. The refined presentation
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

The release also adds full-coverage timing and slow-test diagnostics using
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
behavior. #259 and its merged, reviewed #260 follow-up strengthen consultation
acceptance coverage. Neither changes browser
execution authority. The written 1.4.0 walkthrough is the approved interim
guide. Existing 1.3.0 tutorials, decks and Help captures remain historical with
their source labels; replacement decks and separate Help deployment are deferred.
Independent fresh-session memory, nonprogrammer walkthrough and migration
observations remain open (S3/S6/S9). Full M2/M3/M4 acceptance is outside this
release's claim.

See the [CLI guide](cli-guide.md), [consultation guide](model-consultation.md)
and [coverage measurement limits](coverage-measurement.md). Inspect the exact
source and archive identities in release evidence when matching an installation
to its checks. Software qualification does not establish the deferred human,
derivative or model-quality claims.

## Historical preparation record (October 12 snapshot)

The following text retains the earlier preparation state. It is superseded by
the dated [readiness record](release-readiness-1.4.0.md), rather than describing
the current installation path. The
[original candidate notes](https://github.com/Smart-AI-Memory/attune-harness/blob/09f79820831ea7cdc3df83a8b2f772fd57ee25c7/docs/release-notes-1.4.0.md)
retain the complete earlier page.

**Prepared, unpublished.** Patrick selected the now-merged #233 consultation
changes for this release alongside the approved saved-answer presentation and
companion documentation. The fixed preparation base is signed #260 merge
`e459faeb9909c9d2cbbb7337dc18e460d5d49e1f`, which includes #258 and the
reviewed #234 golden follow-up. Actual-main qualification and the remaining
macOS supplemental coverage result are owned separately. The combined shipping SHA,
archive hashes and publication date remain unset.

The forms presentation was reviewed at
`3d317e71324b609d5e9f603bf88b447e9007345e` and visually accepted by Patrick.
The first goal-based tutorial is aligned to the same controls. Exact combined
source, installed artifact and native-platform qualification remain required;
component reviews and earlier passes do not qualify this later combination.
The [readiness record](release-readiness-1.4.0.md) identifies remaining work.
Version selection and local preparation grant no publication authority.
