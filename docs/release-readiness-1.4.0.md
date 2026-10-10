# Attune Harness 1.4.0 preparation readiness

**Not publication-ready.** The selected version is 1.4.0. The publication date
and final shipping SHA remain unset. This record supplies the preparation
inventory required by the [release runbook](release-runbook.md#documentation-readiness).
All results below belong to the stated source and artifact; they do not qualify
a later combination or establish human or model quality.

## Source and ownership

The local runtime candidate is
`df3e242c98a0fecb4c7ac4f6cb143ae30752ab00`, tree
`2ac53a89c02e2cdfc6d55705ee7d0408abd465f1`. Its preparation base is main
`e382c37eae1350f7e164e6c29e5c6fd01121b749`. This documentation reconciliation
is a separate docs-only branch based on that candidate. Its final commit, tree,
patch and checks are recorded in the local handoff. It changes no runtime module
and does not integrate the candidate into main.

- Approval copy: [PR #256](https://github.com/Smart-AI-Memory/attune-harness/pull/256)
  merged into main at `e382c37` on October 10, 2026, at 15:56 UTC. Its author head
  `e4d09e95941e77b10263d4b7184915ff1c50f475` was independently reviewed by GPT-6
  Astra. The owner reports 73 focused cases and all 20 component CI checks passed.
  Human comprehension of the revised copy remains pending.
- Reload restoration: included locally from the series ending at
  `af59b5b9d9278dcdb802584178ebbf978657282f`, independently approved by GPT-6
  Astra. Original focused and guard-mutation receipts remain tied to that head.
  Remote qualification of the combination remains pending.
- Forms-only refusal wording: corrected at `df3e242` and independently reviewed
  by GPT-6 Astra. It no longer promises execution controls in 1.4.0. This is a
  string-only runtime correction; no execution authority or route was added.
- Canonical tutorials and PowerPoint/HTML derivatives remain with their tutorial
  owner. The accepted one-file candidate tutorial patch is integrated locally
  with its exact document and independent same-model GPT-6 review receipt.
  Candidate deck copies and rendering remain held. Help source, projection and
  website readiness remain with the Help owner; active owner files and old
  captures were preserved.

The released v1.3.0 tag, artifacts, receipts and retained environments are
unchanged. The Claude marketplace still points to that released tag. Moving the
catalog needs the verified new tag and separate authority. The standalone Codex
plugin retains its independent 0.1.0 version.

## Candidate software and installed evidence

The prior combined candidate `b882217b7bb11c61d5375ab6b6877459c0a4228f`
passed the local macOS Python 3.10 source suite: 4,355 passed, 57 skipped and
7 passed subtests. Its noneditable macOS Python 3.12 installed qualification
reported 2,490 passed, 13 skipped and 2 passed subtests. These receipts and the
active human preview belong to `b882217`, not to `df3e242` or this docs-only head.

The correction at `df3e242` passed 22 focused GUI cases and the bounded installed
checks. Its wheel SHA-256 is
`c09c3ccc3cd4f280994204f95d35a64b997eaab6e8eaab993c0e7e4dbd064f45`;
its sdist SHA-256 is
`576449a833371a8f92515860c5cdeb34ba932bc89ad11878934d93cd2ec1e73e`.
All 104 runtime module bytes match that committed source, wheel, sdist and
noneditable installation. The installed CLI checks include an offline command
consultation journey. Their receipts do not qualify live model judgment.

During this documentation reconciliation, five literal commands from the
retained [1.3.0 tutorials](tutorials-1.3.0.md) were replayed on that corrected
1.4.0 wheel in fresh disposable directories:

- The sample plan became accepted; `calc.py` still contained `a - b`, and no
  build state or execution run was created.
- Retrieval retained `guide.md` and `reference.md`. Verification passed with
  one verified link claim and `semantic_ran: false`.

All five commands exited 0. No model was called. Initial replay-driver errors
and the correctly refused macOS `/tmp` symlink path are retained in the local
receipt. This is bounded CLI walkthrough evidence, not a replay of graphical
forms, the first-repair journey or the training presentations.

## Earlier component evidence retained

The original preparation base was
`209a822a2d49ba66fd3e6ab3f918d4e5a118a699`, tree
`66348b3edb38c0f76bde10a96b75013fc6b8b1b3`.
Its [Library qualification run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38057079307)
reported 4,317 passed and 65 skipped. Retained ordinary installed-wheel platform
and Windows effects receipts qualify that recorded source only.

That base's [macOS supplemental coverage job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38057079294/job/114227643384)
timed out at 1,200 seconds. Its last complete progress line was 86%, followed by
11 dots; no active-test journal or final JUnit was retained. Its manifest records
an unfinished test exit without input drift. A
[neighboring successful macOS job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38055337661/job/114222520342)
reported 4,321 passed, 62 skipped and 7 passed subtests in 898.26 seconds.
Different revisions and test sets prevent treating that duration as a completion
promise for the failed source.

The October 10 terminal component readback recorded all 20 checks successful for
PR #256's author head, including six ordinary installed-platform checks, three
Windows effects checks and three supplemental measurements. That later macOS
success neither erases the earlier timeout nor establishes its cause. It does
not qualify the local combined candidate.

The preparation adds full-suite phase timing and slow-test Python stacks without
extending limits or relaxing admission checks. Earlier focused preparation
checks passed 62 coverage-diagnostic cases and 186 release, packaging and
compatibility cases. The first diagnostic attempt had 12 failures because
installed metadata was absent; those cases passed after a disposable wheel
installation. A negative control detected the old driver's missing journal.
These historical receipts support diagnostics, not a performance fix or final
candidate measurement.

## Documentation and derivative inventory

Fresh October 10 readback confirms
[PR #249](https://github.com/Smart-AI-Memory/attune-harness/pull/249) merged the
canonical 1.3.0 tutorials at
`e9f3dd1dccc2d0f6435dc55b7dd2c94b6db7d194`. The remote document, candidate's
retained document and Help snapshot have SHA-256
`a31a785ce28a5b035cc202e06959f2832048f235e0724f753fd84f50102a2d97`.
Historical tutorial source `86e83c6` and behavior source `0ecf8e6` stay historical.
They must not be relabeled as 1.4.0 evidence.

The tutorial owner's latest four PowerPoint and four HTML training files match
their retained delivery manifests: Navigation, Specification and Continuity use
version 3 deliveries; Four Workflows uses version 2. The PowerPoint files contain
39 slides in total. These are retained local delivery/Library receipts; no remote
Library refresh, new rendering or native PowerPoint review was performed here.
All files still describe 1.3.0. Earlier version 2 files and receipts also remain
unchanged.

The [candidate tutorial](tutorials-next-release-candidate.md) now has numbered procedures reviewed against source for direct opening, saved answers, current approval
controls, conditional reload and deliberate reopening. Its exact accepted bytes
retain the historical #243 evidence tail and link the earlier numbered procedure
at an immutable source. The five existing corrected-wheel CLI results support
its reviewed unchanged plan/research procedures. They were not rerun. Candidate
GUI captures, human results and presentation rendering remain pending.

Candidate deck copies are blocked by the unavailable supported presentation
runtime. The installed Presentations instructions require the supplied runtime
and forbid substitute installations. The release record retains this capability
limit and the affected slide/image seams. Historical decks are useful labeled
1.3.0 downloads; keeping them does not mark changed 1.4.0 derivatives ready. Any
interim addendum arrangement needs an explicit owner/release disposition under
the runbook before publication readiness can be claimed.

At Help source `87cb091b85bd16e90b4b480f709784ed6f5ef26c`, the four generated
walkthroughs pass their canonical hash and projection drift check. The seven
topics are get-started, start-and-continue, plan-and-accept, research,
save-and-resume, troubleshooting and dependencies. Help's next-release inventory
still has an unset target version and older #242/#243 source and capture pins.
Those captures remain valid for their labeled sources; they do not qualify the
combined 1.4.0 controls or reload behavior.

The existing Help review preview is hosted under its owner's earlier approval.
[Website PR #2552](https://github.com/Smart-AI-Memory/attune-ai/pull/2552) is still
open and draft at `87cb091`; production publication remains held. This release lane did not build, render or deploy the website. A subsequent
Help-owner handoff records a local nine-file correction staged at tree
`9661c9d2f6bb3018a05490576b7f31bcd852de47`, with no new commit. Its patch
SHA-256 is `e025c9d0dfc4b4b3c0568467a113048bc98d5e6997aa44c08f068b427cdb66a2`.
It selects unpublished 1.4.0, corrects the current publication context, stages
approval/reload/forms-only guidance, preserves the 1.3.0 snapshot/projection and
old capture entries, and excludes #233. The owner reports 75 website tests,
126 compiled static pages, four desktop/mobile light/dark cases and nine local
Help routes passed, plus governance, ledger, drift, lint and TypeScript checks.
Different-model GPT-6 Astra advisory review is complete. These results qualify
that local website input only. It is ready for owner review/integration selection,
not deployed Help or final Harness qualification. The existing hosted review
preview still contains source `87cb091`.

The Help owner also records unresolved scanner/helper authentication failures
on the earlier remote head and HTTP 503 on the new public GitHub blob link,
despite successful contents-API byte verification. Human/native-platform and
candidate derivative limits remain. No website code was imported into Harness;
Help integration/hosting/publication remain with their owner.

| Topic or source | Current disposition | Derivative and owner | Remaining evidence | Older guidance |
| --- | --- | --- | --- | --- |
| README, CLI installation, manifests and release records | Prepared for 1.4.0; these two release records reconciled against `df3e242` | Package and release body; release owner | Final source/tree and shipping copy; verify tagged URLs and index installation when publication exists | Released 1.3.0 retained |
| Browser intake, saved answers, approval and reopening | Candidate canonical numbered steps now match reviewed controls and reload; GUI observations pending | Navigation, continuity and GUI portions of four-workflows; tutorial owner; Help start-and-continue, save-and-resume and troubleshooting | Current steps source-reviewed; source-bound captures, human result and revised deck rendering pending | Keep 1.3.0 controls/captures labeled |
| Sample plan and research | Unchanged commands reviewed and replayed on corrected candidate wheel | Spec-workflow and research examples; tutorial and Help owners | Candidate prose now reconciled and reviewed; presentation framing/images/rendering still need disposition; CLI pass alone does not qualify derivatives | Versioned 1.3.0 canonical text retained |
| Consultation setup, seat checks, batch citations and Markdown | Candidate command evidence retained in correction handoff; JSON stays default | Consultation guide and shared skills; respective owners | Confirm candidate topic coverage and resolve the existing packaged cross-review preflight omission with its assigned owner | Core 1.3.0 guidance retained; no concurrent-round promise |
| First checked repair | Static document, journey and example hashes match retained acceptance contract | First-repair tutorial and derived guidance; tutorial owner | Candidate semantic disposition; this pass did not rerun the repair journey | Contract remains pinned to 1.3.0 |
| Help and official website documentation | Old projections retained; owner local 1.4.0 topics/publication context reconciled and tested; hosted preview still old source | Help owner | Owner integration selection and final tutorial pin reconciliation; HTTP link/auth holds, human/derivative evidence and publication disposition remain | Preserve old snapshot and capture pins |
| Coverage and platform limits | Diagnostics retained; no new final-candidate measurement | CI and qualification guide; release owner | Exact candidate native-platform and supplemental evidence | Keep prior successes and timeout receipts |
| Writing and entered text | Approved guide applied to revised release prose | All affected UI/documentation owners | Source-consistent rendered copy and preserved entered answers | Historical captures retain original labels |

Local Markdown target/index checks and static journey parsing are separate from
semantic checks. They do not test HTTP URLs, every fragment anchor or native
rendering. The Help owner's local correction now separates the published equivalent
canonical bytes from their historical local source. That correction is not yet
in the hosted preview or production; frozen snapshot bytes remain unchanged.

## Remaining technical checks and Patrick decisions

Technical work can continue locally: owners can reconcile their candidate topics,
regenerate source-derived Help content when appropriate, update decks with
source-bound captures, check changed links/builds and record reviewed unchanged
content. Keep old versions and receipts. This inventory grants no write authority
over another owner's active files.

The corrected runtime candidate still needs exact-head/tree full-source,
noneditable installed, native-platform and supplemental qualification for the
final selected combination. Existing component and `b882217` results remain
useful evidence at their own boundaries. Push and automatic PR CI are awaiting
the parent's bounded authorization request; no push or dispatch occurred here.
A docs-only change does not require repeating unaffected source tests locally.

The active disposable human preview remains `b882217`, wheel SHA-256
`a41ef78bfc1ddaeabeca1d02227c11300064d0605f8f106a1257ec4058a83f9a`.
It was not upgraded. The intake, approval copy, saved-request view, client reload
script and fixture bytes are unchanged from that preview to the corrected
runtime. Any actual b882217 observations remain evidence for their recorded
source/browser/inputs and can support these unchanged components with the mapping of identical bytes, as the runbook permits. Do not discard them or relabel them as
observations of the corrected refusal/help text in `gui.py`. The available
preview receipt still has pending human fields; this record invents no result.
Keyboard/visibility, comprehension and native reload/ownership limits remain
bounded by the observations actually supplied. Any controlled replacement must
identify its new source and artifact and preserve the existing accepted practice.

Patrick's remaining decisions are the observed form assessment, final feature
scope, and the specific integration and publication actions. Open observations
need explicit disposition: S3 fresh-session recall/exclusion, S6 a named
non-programmer's installed walkthrough, and S9 each migration row on the
installed stable artifact. Broader M2 still needs its real owner-chain and
recovery evidence. The separately prepared #233 concurrent rounds and selective retry feature is not included; its inclusion would require an explicit scope
decision and new combined qualification. #234's production behavior is already
in the base; its separate acceptance-test addition is not silently included.

Named merge authorization, tag creation, workflow dispatch, package publication,
marketplace updates and website production deployment remain separate actions.
Bind the final shipping artifacts and checks to the actual approved SHA/tree
before requesting publication. No release date, final shipping qualification or
publication authority is inferred from this preparation record.
