# Attune Harness 1.4.0 preparation readiness

**Not publication-ready.** This record is the preparation inventory required by
the existing [release runbook](release-runbook.md#documentation-readiness).
The selected version is 1.4.0; the publication date and final shipping SHA are not established. The local
combined SHA/tree, wheel hashes and check results belong in the release handoff.
Record actual results before replacing pending states with verified results.

## Source and ownership

Preparation starts from main
`209a822a2d49ba66fd3e6ab3f918d4e5a118a699`, tree
`66348b3edb38c0f76bde10a96b75013fc6b8b1b3`. Local preparation combines the exact reviewed GUI source, release
metadata/guidance and coverage diagnostics in a separate checkout. It is not
integration into main, and no owner checkout or live practice was changed.

- Approval copy: draft [PR #256](https://github.com/Smart-AI-Memory/attune-harness/pull/256),
  author head `e4d09e95941e77b10263d4b7184915ff1c50f475`, reviewed independently
  by GPT-6 Astra. Its owner reports 73 focused cases passed; all 20 exact-head CI checks succeeded.
  Included locally; revised-copy human comprehension remains pending.
- Reload restoration: included locally from the exact three-commit series ending at
  `af59b5b9d9278dcdb802584178ebbf978657282f`, independently approved by GPT-6
  Astra. Its owner reports 91 unique focused cases and meaningful guard mutations.
  Reload has no remote CI; combined/native evidence remains separate.
- Canonical tutorials and PowerPoint/HTML derivatives: the tutorial owner retains
  their sources and captures. Candidate reconciliation remains pending.
- Help Center and official website documentation: their owner retains website
  provenance, topic readiness and publication decisions. A prepared route is
  not a live Help URL.

The released v1.3.0 tag, artifacts, receipts and retained environments remain
unchanged. The Claude marketplace still points to that released tag. Moving the
catalog requires the new verified release tag and a separately authorized step.
The standalone Codex plugin's independent 0.1.0 version is preserved.

## Evidence already inspected

Main's [Library qualification run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38057079307)
passed on the preparation base. Its full suite reported 4,317 passed and 65
skipped. Retained ordinary installed-wheel platform receipts and Windows effects
checks were inspected. These qualify their recorded source, not a future combined
1.4.0 candidate, and do not close human or model-quality assessments.

The base's [macOS supplemental coverage job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38057079294/job/114227643384)
timed out at 1,200 seconds. Its last complete progress line was 86%, followed by
11 dots; no active-test journal or final JUnit was retained. The manifest records
an unfinished test exit with no input drift. The
[neighboring successful macOS job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38055337661/job/114222520342)
reported 4,321 passed, 62 skipped and 7 passed subtests in 898.26 seconds
(14 minutes 58 seconds). Different revisions and test sets prevent treating that
duration as a completion promise for the failed source.

At the 15:20 UTC October 10 readback, PR #256 remained open and draft at the
head above. Nineteen checks had succeeded then; the terminal readback subsequently confirms
all 20 succeeded, with Windows coverage completed at 11:20:45 a.m. EDT October 10.
The full suite, six ordinary installed-platform, three Windows effects and three
supplemental measurements succeeded for that component head. This later macOS success is useful
comparison evidence. It neither changes the earlier main receipt nor identifies
the cause of that timeout, and it does not qualify the future combined candidate.

The prepared correction retains full-suite test/phase timing and slow-test Python
stacks without extending limits or relaxing checks. Local focused regressions
include timeouts in setup, call and teardown and refusal to combine unfinished
receipts. This repairs missing diagnostics. The final combined candidate still
needs a successful measurement; the earlier timeout's cause remains unestablished.

Local preparation checks passed 62 unique coverage-diagnostic cases and 186
release admission, plugin packaging and compatibility cases. The first
diagnostic run had 12 environment failures because installed Harness metadata
was absent; those cases passed after installing the wheel in the fresh disposable
environment. A negative control failed against the old full-coverage driver
because the journal was missing. These checks support the preparation changes,
not full-source or native-platform qualification of the final candidate.

## Documentation topic record

All local preparation guidance refers to the source boundary above. Walkthroughs
have not yet been reproduced on the final combined candidate. Link checks and
version consistency checks are recorded in the release handoff; they are distinct
from semantic walkthrough and human review.

| Topic or source | Preparation disposition | Derivative and owner | Expected result and remaining evidence | Older guidance |
| --- | --- | --- | --- | --- |
| README, CLI installation, release notes and shared manifests | Changed for 1.4.0; explicitly unpublished | Package README and GitHub release body; release owner | Matching version and local target paths; tagged links and published install pending | Released 1.3.0 retained |
| Browser intake, saved answers, accepted inspection and reopening | Current CLI guidance includes reviewed copy/reload; combined/human checks pending | Saved-request walkthrough; tutorial owner; Help projection owner | Save/reopen without replay, visible approval result; exact combined-source and human checks pending | Versioned 1.3.0 tutorial/captures retained |
| Consultation setup, seat check, citation batch and Markdown evidence | Changed version boundary in consultation guide | Shared skill references and Help topics; respective owners | No-spend setup/inspection, retained citations and atomic assessment; candidate command checks pending | Core 1.3.0 consultation guidance retained |
| Coverage and installed-platform limits | Diagnostics guidance changed; qualification claims retained at their recorded boundary | CI artifacts and qualification guide; release owner | Active phase retained after timeout; final coverage and native-platform evidence pending | Older measurement receipts unchanged |
| First checked repair and four canonical walkthroughs | Existing released-source guidance retained; no claim of final-candidate review | PowerPoint and HTML tutorials; tutorial owner | Reconcile every procedure, control, example and limit against final source; drift/semantic checks pending | `first-repair-1.3.0.md` and `tutorials-1.3.0.md` remain versioned |
| Help Center and official docs publication | Pending owner readiness record | Prepared website Help Center; website owner | Tested source, affected topics, checked links/build, reviewed unchanged topics and hosting disposition pending | Old-version source labels retained |
| Writing and entered-text policy | Approved guide applied to revised release prose | All affected documentation/UI owners | Direct instructions and preserved entered wording; final rendering checks pending | Historical captures retain original labels |

## Combined candidate qualification and remaining gates

The reviewed copy/reload and local release preparation have been assembled only
in an isolated local candidate. Keep every component receipt tied to its own
head; record combined review, relevant/full suite, wheel/sdist, installed checks,
source identity and local links in the handoff for the exact assembled SHA/tree.
Any later source change requires its own delta review and checks.

Actual Windows and other unavailable native-platform CI remain pending under the
no-push/no-dispatch boundary. Prior component CI does not substitute for it.
Human comprehension, keyboard/visibility and native-browser reload/lock behavior
also remain pending. A controlled human preview must use a new disposable
practice; it must preserve the accepted live practice, listener and browser.
Replacing the live rehearsal requires separately applicable authority.

Canonical tutorial/deck and Help owners still need to reconcile their versioned
examples, controls, expected results, limits and drift/publication records against
the combined source. Retain old captures with their source labels. Review the
remaining 1.3.0/1.4.0-target refusal wording before publication; these messages do
not enable browser execution. Verify tagged targets and index installs when the
release exists, and update preparation-only wording before the shipping freeze.

Integrate through protected main only under applicable named authorization.
Then bind final shipping review/checks and publishing artifacts to that actual
SHA/tree before requesting a concrete publication action. Local preparation
permits no push, merge, workflow dispatch, tag, publication or website deployment.

S3/S6/S9 and broader M2 dispositions remain human/product decisions. Software CI
cannot substitute for them. No publication or final shipping qualification is
claimed by this local preparation record.
