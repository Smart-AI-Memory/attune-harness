# Browser form accessibility assessment

Baseline: `bf7829e1d12ddc49f228157c64508f047e9d863a` (2026-10-08).
This assessment covers the Harness-owned intake and intent review companion,
its saved-answer recovery, and the retained development companion. It uses source
inspection and synthetic regression fixtures. A bounded browser check is
recorded below; screen-reader and broader rendered checks remain open. It does not assess every exported
attune-forms document, CLI collector, host panel, or third-party control.

The [WAI forms tutorials](https://www.w3.org/WAI/tutorials/forms/) offer practical
recommendations across conformance levels. The criteria below refer to
[WCAG 2.2](https://www.w3.org/TR/WCAG22/); they identify relevant evaluation
questions, not proven violations or a conformance claim. A claim would need an
explicit version, level, complete page/process scope, supported technologies,
and evidence for every applicable criterion.

## Journeys and existing strengths

The released intake companion opens a registered saved draft, presents remaining
questions, saves some or all answers, and then offers **Continue form** or
**Review your answers**. The latter displays retained answers and blocking
reasons before **Accept this intent** or **Keep draft for reconsideration**.
Acceptance does not execute work. Browser build controls remain unavailable in
1.3.0; the retained development companion's separate command grant is not a
released user journey.

Current unreleased source uses **Approve this work request** and **Keep as
draft**, with a separate consequence for each choice and an explicit statement
that neither starts work. These copy changes preserve the owner actions and
decision boundaries. The baseline and rendered evidence in this assessment
retain their original labels; they do not establish comprehension or
accessibility of the revised copy.

- Every supported question has a visible `<label>` whose `for` matches the input
  `id`. Labels remain while typing; essential instructions do not use placeholders.
- Scope and success criteria already say `Enter one item per line.` in their
  persistent labels. Choices have a blank initial option; no answer is preselected.
- Opening a decision focuses its heading. Native controls and visible focus
  styles are present. The development evidence poll preserves existing nodes,
  focus, selection, and scroll.
- Saved goal, success criteria, answered material questions, and selected choices
  are shown separately from new positional fields. Saved scope remains in the
  authoritative record but is omitted from the partial-intake summary. Newly
  issued `answer_0` never receives an old `answer_0` automatically.
- Submissions are single-use. Network loss, stale decisions, and refresh failures
  retain copyable values and require inspecting saved state and deliberately
  opening the current form. Browser reopening does not call `resume`.
- Untrusted labels, choices, answers, and owner records use `textContent`.
  Read-only access, session tokens, origin checks, checkpoint binding, and
  explicit approval remain independent of these presentation features.

Evidence: [intake script](../src/attune_harness/gui_forms_intake.py),
[development script](../src/attune_harness/gui_forms.py),
[decision owner](../src/attune_harness/gui_decisions.py),
[question projection and answer collection](../src/attune_harness/work_runtime.py),
[client checks](../tests/test_gui_client.py),
[HTTP/owner checks](../tests/test_gui_decisions.py), and
[released GUI boundary](../tests/test_gui_release.py).

## Prioritized gaps

| Priority | Concrete finding at baseline | Guidance and relevant criteria | Bounded next action |
| --- | --- | --- | --- |
| P1 | `planning_questions()` marks all projected questions `required: true`, because they block acceptance. The browser omits this explanation while allowing partial saves. Calling these fields required for each save would misrepresent the owner contract. | [WAI instructions](https://www.w3.org/WAI/tutorials/forms/instructions/) and [validation](https://www.w3.org/WAI/tutorials/forms/validation/); 3.3.2 Labels or Instructions (A), 1.3.1 Info and Relationships (A). | Describe requiredness as **Required before intent acceptance** beside each owner-required field. Explain that an answer can be left blank for a partial save. Do not add native `required` or change collection rules. |
| P1 | Overall partial-save guidance sits inside the form and is not associated with controls. Nearby checkpoint text is also unassociated. Format guidance within labels already has an association. | WAI instructions recommend overall guidance before the form and programmatic association for separate hints; 1.3.1, 3.3.2. | Put the save instructions before the form and reference them from each input using `aria-describedby`. Keep field guidance visible while typing, after a failed submission, and during recovery. |
| P2 | Empty saves produce actionable text in the existing polite status region and make no request. Other server errors appear as raw messages in the page-level status region alongside a separate generic uncertain-action notice. There is no per-field error association, error summary with links, or guided correction for a specific invalid answer. | [WAI notifications](https://www.w3.org/WAI/tutorials/forms/notifications/); 3.3.1 Error Identification (A), 3.3.3 Error Suggestion (AA), 4.1.3 Status Messages (AA). | Verify empty-save feedback and retention now. Design a structured error contract separately: validation refusals must remain distinct from uncertain persistence, and single-use decisions must not be retried automatically. |
| P2 | `bounded_text()` limits each planning answer to 4,096 UTF-8 bytes. The browser does not explain the limit before submission. HTML `maxlength` counts different units, so it would not faithfully enforce this contract. | WAI instructions/validation; 3.3.2 and 3.3.3. | Keep the server boundary. Plan a byte-aware explanation/error presentation rather than inventing a character limit. |
| P2 | Source uses native controls, heading focus, and 3px focus outlines. There is no recorded keyboard/screen-reader walk establishing heading announcements, descriptions, successful-save feedback, or copyable recovery in supported browsers. | [WAI labels](https://www.w3.org/WAI/tutorials/forms/labels/) and notifications; 2.1.1 Keyboard (A), 2.4.3 Focus Order (A), 2.4.7 Focus Visible (AA), 2.4.11 Focus Not Obscured (Minimum) (AA), 4.1.2 Name, Role, Value (A). | Walk opening, typing, choosing, saving, inspecting, and deliberate reopening without a pointer. Record browser/AT versions and announcements; DOM seams alone do not prove them. |
| P2 | Computed CSS color pairs give body/input text 11.86:1 on white, hint text 6.54:1 on white, and enabled button text 7.58:1. The input border is approximately 2.999:1 on white, and the gold outline is 2.91:1 against the page background. These are source color calculations, not rendered coverage of every state. | WCAG 1.4.3 Contrast (Minimum) (AA), 1.4.11 Non-text Contrast (AA); 2.4.13 Focus Appearance is AAA, not an AA requirement. | Measure actual relevant adjacent colors and states before a minimal token adjustment. Preserve the Harness palette and layout; do not claim a contrast pass from rounded values. |
| P2 | Cards wrap and controls use full width, but question labels lack explicit long-token wrapping. Choices put proposal, rationale, counter-case, evidence, and uncertainty into one native option, which can be hard to inspect at narrow widths. The bounded 320px fixture below shows a clipped selected choice; 400% zoom and long unbroken labels remain unverified. | WAI labels; WCAG 1.4.10 Reflow (AA), 1.4.4 Resize Text (AA). | Test long synthetic labels/choices at 320 CSS px and enlarged text. Hold any choice presentation redesign for a journey decision. |
| P2 | Saved answers survive in the authoritative record, but the partial-intake summary omits saved scope; a scope-only save has no visible summary until intent review. Unsaved typing is only retained in the current expired panel and may be lost on tab closure. This is a continuity limit, not evidence of a WCAG failure by itself. | WAI [multi-page forms](https://www.w3.org/WAI/tutorials/forms/multi-page/); 3.3.7 Redundant Entry (A) is relevant when the same process demands information again. Security/essential exceptions require context. | Add saved scope to the partial-intake summary with a focused regression in a later bounded fix; this needs no new storage. Preserve copy-before-close guidance and verify no unnecessary re-entry of saved answers. Autosave/local draft retention requires a decision on storage, privacy, expiration, and cross-tab conflicts. |

## Testable acceptance checklist

The first implementation increment is limited to the two P1 presentation fixes.
Remaining items are evaluation or future acceptance criteria, not promised fixes.

- [ ] For both shipped scripts, each supported textarea/select keeps the owner's
  exact visible label, matching `for`/`id`, and unmodified response field name.
- [ ] Overall save guidance precedes the form. Every input's `aria-describedby`
  resolves to that visible guidance and its own hint, with unique IDs.
- [ ] Owner-required fields say **Required before intent acceptance**; other
  fields do not acquire that claim. No input gains native `required` or
  `aria-required` that would imply each partial save must complete it.
- [ ] Scope/success format instructions remain visible and associated through
  their existing labels. Hints remain after typing; no example becomes a value.
- [ ] Blank/whitespace-only submission makes zero POSTs, reports the existing
  correction, and leaves the form editable. A partial save sends only supplied
  answers, byte-for-byte, without fabricated answers or approval/execution calls.
- [ ] Slow/repeated submission produces one POST. Network/409/refresh failure
  retains original values and guidance, disables expired submission, and never
  replays it. Deliberate reopen uses the current checkpoint and fresh empty fields.
- [ ] Saved goal, success criteria, material answers, and selected choices remain
  visible without remapping them into new positional fields. Read-only access
  makes no write or model call.
- [ ] Existing HTTP authority tests still reject foreign origins, bad tokens,
  stale/consumed decisions, and unavailable execution routes.
- [ ] Keyboard/browser/AT walk records focus order, labels/descriptions, status
  announcements, selection, save recovery, and **Refresh forms** behavior.
- [ ] Rendered checks at 320 CSS px and enlarged text cover long labels, choices,
  hints, retained answers, and approval blockers, with no loss of actionable text.
- [ ] Measure enabled text, control boundaries, and focus indicators against
  their actual adjacent backgrounds; distinguish disabled-control exceptions.
- [ ] Record changed tests, full-suite result, exact installed-wheel identity,
  independent source-review receipt, and automatic CI results for the exact head.
  Windows qualification requires its CI evidence.

## Decisions held

1. Choose a formal accessibility target and supported browser/assistive technology
   matrix if a conformance evaluation is wanted. Recommended next evidence is a
   bounded intake/approval keyboard and screen-reader walk before a wider claim.
2. Choose whether unsaved drafts should survive closing a tab. Recommended current
   scope preserves explicit saves and copyable recovery; persistent drafts need
   storage/privacy and stale-decision rules before implementation.
3. Choose a readable narrow-screen presentation for long choices if rendered
   testing confirms clipping. Keep option identity, owner evidence, and explicit
   selection; do not default a proposal or alter the approval journey.

No decision is needed for the P1 fixes within the authorized scope. Approval,
execution, permissions, provider budgets, merge, release, and deployment remain
under their existing rules. New documentation follows the
[Google UI writing guidance](https://developers.google.com/style/ui-elements):
exact UI control names are bold, and typed/code literals use code formatting.

## Evidence for the bounded guidance increment

The unreleased `forms-persistent-guidance` branch implements the two P1 changes.
The source diff at `14bbcfaa9a7be033ed73e97e6891a319fde87c1b` adds four lines
and removes one in each browser script. No CSS, owner definitions, validation,
response construction, saved-answer logic, or approval/execution controls change.
These hints must not be described as part of the released 1.3.0 artifact.

Independent source review was dispatched to GPT-5.6-Sol under the repository's
different-model rule. The reviewer accepted the source and identified the saved
scope omission and error-location wording in this assessment; both are corrected
here. A test-only follow-up adds an explicit second submit during an unresolved
request. Documentation/test changes do not modify the reviewed source.

A new hidden in-app browser tab used a synthetic local draft and deterministic
participants, with native dispatch poisoned. Its isolated browser inventory
contained only that tab. At 1280 × 720, the heading received focus on opening,
Tab reached the first input, and visible labels and hints remained after typing.
Every description reference resolved and native requiredness remained false.
An empty save displayed **Enter at least one answer to save.** A goal-only save
was accepted while other required-for-acceptance answers stayed blank. Deliberate
reopening showed that saved goal beside new empty inputs, with scope now
occupying `answer_0`; no old value was replayed.

At 320 × 720 CSS pixels, the fixture's input/hint width was 239px and body scroll
width was 305px: the new guidance wrapped without horizontal overflow. A selected
long choice visibly clipped its rationale/counter-case in the collapsed native
select, although the full value remained in the accessibility tree and the owner
record. This supports the held choice-presentation decision; it does not establish
reflow for every question, expanded menu, recovery state, or 400% zoom. The
viewport override was reset. This walk did not run a screen reader or establish
spoken descriptions/status announcements.

The client tests exercise both scripts, true/false/absent required metadata,
unique description IDs, blank and partial submission, literal untrusted text,
409 recovery, and deliberate reopening. Existing regressions cover network loss,
refresh failure, selection/focus preservation, and authority separation. Local
HTTP/release checks passed 98 tests; the first sandboxed run was blocked by
loopback socket permissions, and the permitted host run passed. Full-suite,
installed-wheel, and exact-head CI results are recorded in the pull-request
handoff rather than inferred from these checks.
