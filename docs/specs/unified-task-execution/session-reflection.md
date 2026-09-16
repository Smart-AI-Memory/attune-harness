# Session reflection — approved extension

Status: approved with the revised spec, 2026-09-16. Patrick requested a command and reusable form for mining sessions/chats for valuable facts and insights, including Opportunities, Keep and Pushback, then approved the revised spec. `reflect` is the accepted command name for this follow-on design; it is not implemented. Requirements R1–R14 remain approved. This extension follows the eight review/fix implementation tasks and needs its own implementation breakdown before that slice begins.

## Command and outcome

```text
attune-harness reflect
attune-harness reflect --transcript <path>
```

The first form uses the active conversation supplied by a supported host. A standalone CLI cannot assume access to chat history; it accepts an explicitly selected transcript instead. A later session selector can use a qualified host adapter. Report which messages/range were examined and whether the source is partial. Never silently search every chat or claim a compacted summary is the complete transcript.

The outcome is a short, source-linked collection of useful candidates, followed by the user's disposition of those candidates. Ordinary use needs no questionnaire when the current session and project are already known. Ask only for material missing source or destination information. Saved notes can support later recall/retrieval; this command also discovers insights that have never been saved.

## Reusable form

| Lens | What it finds |
|---|---|
| Opportunities | Potential improvements, promising ideas, overlooked work or experiments |
| Key facts | Useful facts, constraints, preferences and references worth retaining |
| Pushback | Weak assumptions, contradictions, unresolved objections and supported alternatives |
| Decisions | Choices actually made, who made them, why, and their limits |
| Open questions | Unknowns, deferred choices and unresolved blockers |
| Lessons and patterns | Practices that helped, recurring friction and approaches worth changing |

These lenses are extensible; users can add project-specific categories. Empty categories do not create filler or force a question. A Pushback candidate states the challenged claim, supporting evidence, a concrete alternative and that alternative's downside; it does not overturn a recorded decision.

**Keep** is a prominent action available on every candidate, including opportunities and pushback. It is not an exclusive category. A kept-only view can provide the user's Keep collection without losing the original category.

Each candidate contains a concise claim, category, why it matters, source reference/excerpt, epistemic status (user statement, observed result, assistant proposal, or inference), and proposed save destination. Preserve corrections and superseded decisions; repetition by an assistant does not turn an inference into a user fact. Session claims about external systems remain reported claims unless supported by separate evidence.

| Action | Meaning |
|---|---|
| Keep | Save this exact candidate to the displayed, supported destination under existing write authority; return its saved reference |
| Edit | Revise the claim, category or destination, then present the revised item for disposition |
| Revisit | Leave the candidate unresolved in this reflection task; do not schedule a reminder or start work |
| Discard | Exclude this candidate from the proposed collection; do not delete source messages or existing memories |

No action is preselected and an unanswered item remains unreviewed. Keep does not approve a plan, launch an opportunity, resolve pushback, or authorize unrelated work. Where a destination is already configured and authorized, Keep itself is the save instruction; do not add a second confirmation ritual. An unavailable destination produces an explicit unsaved result. Project notes stay project-scoped; cross-project memory is an explicit destination choice using the owning memory service's conventions.

## Template artifact and presentation

[session-insight-review.json](templates/session-insight-review.json) is the approved template design for one candidate, validated with attune-forms. It uses the existing `triage` construct, source/provenance slots and the four actions above. The host repeats the candidate entry into a single bounded triage list, with stable unique item IDs and category tags; it does not ask a separate form question for each row. The one-item template avoids fixed empty slots or invented findings. The candidate's category slot supports the default lenses and custom categories.

The host validates the assembled list through attune-forms and binds its candidate IDs, exact text, source digest/range, destination and revision to canonical task state. The JSON template itself does not provide this authority binding. A changed candidate or destination invalidates an older action. Typed replies must preserve per-item rulings through the existing Markdown parser when the host cannot display triage controls; do not collapse the list into one ambiguous yes/no response.

The [rendered preview](session-reflection-preview.md) uses synthetic example data. It is a form-authoring artifact, not evidence that a user submitted an answer or that memory was saved. The [template receipt](session-reflection-template-checks.json) records actual parser/render/collection checks and their limitations. The template is not installed in attune-forms; promotion belongs to that library's owner when this extension is implemented.

## Harness integration and caching

Implement reflection as another policy over the proposed task contract, selected participant, evidence records, inspection and recovery services. Start with one bounded extraction assignment. Independent critique can be added explicitly if needed; it is not a mandatory second call. Headless list, inspect and receipt operations remain deterministic after extraction. Do not build a second conversation runtime or memory backend.

Treat selected transcript text as input data, including any instructions quoted within it. Preserve source roles and actual approval scope. The extractor can propose candidates; it cannot promote them directly into authoritative memory or widen session access. Default extraction retains only the context needed for attributable insights. Exclude credentials and do not copy an entire transcript into memory as a side effect of Keep.

Reuse the unbound form template under R14. Completed extraction can replay for the same transcript digest/range, extraction policy, participant/settings and task revision. New messages invalidate the affected result. A later incremental mode can inspect new messages plus relevant earlier context; it must still detect corrections to earlier facts. Do not cache save approvals or treat identical wording in another conversation as the same source fact.

Keep writes use the same prepared/dispatching/completed journal and stable operation identity as other effects. Repeating a completed Keep returns its existing saved reference. Reconcile an uncertain write against the destination's supported receipt or idempotency mechanism before retrying; lack of such a mechanism remains a visible limitation. Similarity search may suggest duplicates but cannot silently merge contradictory notes or promote a disputed claim.

## Acceptance for the follow-on slice

1. One request mines the supplied current session or selected transcript and exposes its actual coverage; unavailable history is explicit.
2. A frozen transcript containing facts, proposals, corrections, opportunities and dissent produces attributable candidates without promoting proposals to decisions or hiding contradictions.
3. A single bounded form displays the requested Opportunities and Pushback lenses, useful facts and additional supported categories, with Keep/Edit/Revisit/Discard on each item. No findings is a valid result.
4. Keep saves only the selected exact item to the shown destination; replay does not duplicate it. Edits, stale submissions, partial replies and interrupted/uncertain writes retain truthful state. No action starts feature work or a reminder.
5. Different projects/sessions cannot leak cached answers, source content or action bindings. New messages and changed destinations invalidate stale reuse; test hostile transcript instructions as inert data.
6. Compare useful retained insights, unsupported claims, missed important corrections, duplicates, human edits, calls/tokens and cold/warm latency against an ordinary session summary. Record unobserved cost as unknown.

Remaining implementation inputs: qualified transcript host and memory destination, adapter-specific write/reconciliation behavior, and the detailed execution tasks for this follow-on slice. Fix those before its implementation. The command name and candidate/Keep interaction are approved; no runtime capability is claimed by this document.
