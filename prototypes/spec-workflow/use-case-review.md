# Spec studio — second iteration use-case review

Retained design observations from September 24, 2026. The reproduction script
now uses the public fragment and a local presentation-state fixture host.

## Verdict

The prototype demonstrates a complete, local interaction sequence for one saved-work navigator specification. It supports evaluating navigation, decision clarity, and the distinction between evidence, acceptance and execution. It does not yet demonstrate a general-purpose spec authoring product or an operational agent harness.

This review inspected the actual implementation and ran three Chromium journeys. The prototype itself was left unchanged. `review-use-cases.py` reproduces the observations and writes a fresh `use-case-review-evidence.json` bound to the prototype SHA-256. Prior successful checks do not cover arbitrary goals or production integration.

## Supported use cases

“Demonstrated” means working within the simulation; it never means connected to Harness.

| User need | Support | Actual behavior and limit |
|---|---|---|
| Understand how an idea becomes a spec | Demonstrated | Seven stages with forward/back navigation and visible boundaries |
| Define goal, included/excluded scope and done conditions | Demonstrated | Editable fields and required-field validation; no semantic consistency validation |
| Skip external research for familiar work | Demonstrated | Skip advances to material questions |
| Inspect relevant context before searching outside | Demonstrated with fixtures | Shows current-conversation direction, sample project memory and an excluded fictional conflict |
| Select context to carry into the spec | Demonstrated | Selected implications and provenance appear in spec and handoff |
| Inspect external findings and include selected implications | Demonstrated with fixtures | Two static sources; no live search, arbitrary source input, source-date capture or research synthesis |
| Answer material questions | Demonstrated for scenario | Two fixed questions; immediate execution option is blocked with explanation |
| Compare approaches and retain a tradeoff | Demonstrated for scenario | Shared companion versus host panels, with rationale/counter-case |
| Pause and reopen one draft | Demonstrated locally | Save & close plus fixture-host reload restoration; best-effort presentation persistence, not durable project storage |
| Revise a drafted or accepted spec | Demonstrated | Content changes increment revision and clear simulated review/acceptance |
| Resolve a reviewer finding | Partial | Can apply one fixed empty-state finding; cannot dispute, defer, explain an alternative resolution or request another reviewer |
| Inspect differences between revisions | Partial | Only immediately previous snapshot, not complete differences from accepted baseline |
| Accept an exact revision | Demonstrated locally | Current sample review required; no real checkpoint-bound grant |
| Distinguish acceptance from permission to build | Demonstrated | Separate status rows; permission remains not granted |
| Produce a portable build handoff | Partial | Selectable text with intent, requirements, choices and sources; predefined tasks and no actual dispatch |
| Understand memory retention at completion | Partial | Prepares a fixed candidate; no editing, approval, persistence or retrieval of that candidate |
| Switch Claude/Codex/Antigravity presentation | Demonstrated label choice | Changes handoff text only; no host connection or integration qualification |
| Inspect checks versus research evidence | Demonstrated distinction | Implementation requirements remain Not run; no live test or receipt drill-down |
| Create multiple goals or manage projects | Unsupported | One sample task; no new-task collection, project selector or task search |
| Import an existing spec or recover partial legacy work | Unsupported | No import, parsing, migration or reconciliation journey |
| Execute Fix or Build and review results | Unsupported | Build ends at a handoff; no Fix journey |
| Recover from unavailable research/memory services or concurrent edits | Unsupported | No failure/retry or conflict resolution flow |

## Findings from alternate journeys

### 1. Arbitrary-goal editing can imply support the template does not provide

Browser reproduction: changed the goal to “Create a searchable recipe collection,” skipped research, answered the fixed questions and created the spec. The new goal appears, but tasks still say “Build the navigator.” Source inspection also shows a fixed title, findings and implementation sequence.

This is acceptable only as an explicitly bounded scenario demonstration. Next iteration should either keep a clearly named scenario with bounded editing or add distinct scenario fixtures that update questions, tasks, findings and handoff coherently. A text field alone does not demonstrate general-purpose generation.

### 2. Research changes have inconsistent freshness messaging

Browser reproduction: accepted revision 2, changed the research question and left the field. The status says review is required again, but acceptance remains on revision 2. Research questions are excluded from revision increments and omitted from the handoff.

Decide the semantics explicitly: an exploratory query can remain outside the accepted spec, but it must not claim to invalidate review; a query that changes accepted assumptions or findings should mark dependent content stale. Show which finding answers which question, its source and freshness, and which requirements depend on it.

### 3. Review cannot show all changes since acceptance

Browser reproduction: after acceptance, edited goal and then scope. Review shows only the scope difference. `snapshot()` retains a single predecessor and omits questions, selected context and selected findings; `log()` keeps only 16 events.

Before evaluating real approval decisions, retain an accepted baseline and compare all substantive fields against it. Show changed requirements, choices, evidence and scope together. Recent-activity truncation must not masquerade as durable decision history.

## Recommended next iteration

1. **Prove one alternative journey.** Add a second scenario such as a narrowly scoped bug fix, with its own questions, optional research, requirements, review finding and handoff. Done when switching scenario cannot leave navigator-specific content behind. This tests whether the navigation generalizes before introducing live generation.
2. **Make evidence traceable.** Connect question → context/source → finding → decision → requirement. Include unavailable/old/conflicting context and one unresolved research question. Done when a user can explain why a requirement exists and what remains uncertain.
3. **Make review a real choice.** Offer apply, revise another way, and disagree with a recorded reason; show all changes since the last accepted revision. Done when acceptance cannot hide an unresolved blocking issue and disagreement does not require accepting the canned fix.
4. **Complete the memory learning loop.** Let the user edit a proposed memory, choose project versus broader scope, inspect the source decision and preview its next-session retrieval. Keep the simulation clearly labeled. Done when the user can distinguish task history, retrieved memory and a new memory proposal.
5. **Demonstrate interruption and recovery.** Add research unavailable, no relevant memory, stale source, saved draft and competing-revision states. Done when every blocked state offers a clear next action and preserves the user's work.

The smallest useful next unit is correcting research freshness messaging and adding an accepted-baseline comparison. The highest-value design expansion is a second coherent scenario plus the context-to-requirement evidence chain. Neither requires real model calls to evaluate the UX.

## Limits of this review

No live internet research, memory service calls, paid model execution, production authority testing, screen-reader audit or human usability study was performed. The prior responsive checks covered 320, 736 and 1024 pixel widths; this review did not repeat those unchanged layout checks. Findings describe this prototype, not missing capabilities in the underlying Harness engine.
