# What better controls can save in an AI workflow

Draft for Patrick's review · September 18, 2026 · Not published

In Attune Harness, controls limit what an AI can change and check its results.
Recent work on those controls led to a practical improvement: a local prototype
kept a useful code repair while preventing an unrelated change elsewhere in the
file. Additional tests caught a separate logic error. A local replay—applying
saved model responses again—let us check these improvements without requesting
new responses. I consider that an opportunity realized.

The work began with model choice. I wanted to know whether the Luna model could
handle more routine repairs and whether a small Python program could identify
work that needed Sol, the more expensive model in this comparison.

In a small, controlled comparison, sixteen attempts per model used **1.74 estimated
credits for Luna** and **33.63 for Sol**—approximately **95% lower estimated cost
for the repair calls with Luna in that sample**. Luna passed sixteen original
attempts; Sol passed fifteen.
Sol's median response was about two seconds faster. The comparison covered eight
small cases constructed for the experiment, repeated twice. These estimates
express model usage in credits, not dollar charges. They exclude the session
reviewing the work and do not establish customer savings or time to a completed
journey.

The Python filter showed no quality advantage: the cases it assigned to Sol also
had passing Luna replies. Its selected results failed the requirement that every
attempt pass. Luna warranted further testing; the filter did not qualify for
production use. [Comparison and results](../plan-build-routing-eligibility-results.md).

Larger repairs exposed another opportunity: reduce how much code a model can
replace. A function is a named block of code that performs a task. Asking for a
complete file to fix one function gives unrelated changes room to enter the
response. One reply fixed the requested function but broke a renderer—the code
that formats output—elsewhere in the file.

The local prototype limited the replacement to the function body: the instructions
inside the function selected for repair. The code applying the change selected
the file and function, checked that the file had not changed since preparation,
and inserted the proposed body. It preserved every surrounding byte.

That prevented the renderer change while keeping the useful repair. Twenty
known-correct reference repairs passed; twenty attempts to introduce code outside
the function were rejected. The replay required **zero new model calls**. Every original grade
remained unchanged. [Replay results and verification](../plan-build-function-body-replay-results.md).

Another reply contained a logic error inside the permitted function: it reported
interrupted test runs as “no tests.” Restricting the edit left that error intact.
Behavioral checks added only to the replay caught it. Removing those checks
reproduced the eight passing tests that had missed the problem originally.

The broader model trial had a preparation defect: two cases included the correct
solutions in the model's input. It stopped after twenty-one calls, retaining
twelve original passes and nine failures at about **7.04 worker credits**. The
exposed solutions prevent us from treating it as a valid reliability test. The local replay
demonstrates the edit boundary and checks; it does not repair the trial or measure
the cost and speed of fresh body-only responses. Smaller replies and less repeated
review remain savings opportunities to test. [Broader trial closeout](../plan-build-luna-broader-results.md).

Controls should also help the user understand what happened and what to do next.
These proposed messages illustrate the intended experience; they are not shipped
interface copy:

> **Repair needs revision.** The repair reports interrupted test runs as “no
> tests.” The failing case is saved. Correct the decision order, then run the
> checks again.

> **Paused before applying the repair.** The file changed after this proposal
> was prepared. Harness has not applied the replacement. Refresh the proposal
> against the current file.

> **Optional suggestion.** The required checks passed. A clearer function name
> could help future readers; this suggestion does not block completion.

Each message explains a different consequence. Correct a failed requirement.
Refresh a proposal based on an older file version. Leave optional advice optional.
When a required check
cannot run, identify it, explain which step has paused, and show how to restore it.

Normal use can also expose technical debt: the maintenance burden of unresolved
design problems and shortcuts. Testing gaps, fragile interfaces and repeated
recovery work can add to that burden. A regression check—a test that detects the
return of a known problem—or a fix to shared code can prevent the next task from
repeating a failure. The decision-ordering check closed one testing gap. Having
code manage the source-version check also removes an error-prone copying task
from model replies.

Those improvements need restraint. Body-only editing does not simplify an existing
architecture, and duplicate checks or one-off exceptions add maintenance work.
Fix the demonstrated cause within the accepted scope, retain the regression test,
and record larger cleanup separately. Judge progress by recurring failures,
duplicated mechanisms and recovery effort. This trial did not measure net
maintenance savings.

Prompt enhancement belongs earlier in that same process. I have already seen
several long prompts improve when ambiguities were removed. Prompt enhancement
should also carry forward my established writing style: direct verbs in process
steps, consistent terms and clear sequences. Those choices make instructions
easier to follow while preserving their meaning.

Use the conversation and project evidence to clarify intended behavior, expose
buried requirements and make completion testable. A detailed prompt can become
clearer without becoming shorter. Resolve material uncertainty before it turns
into code, tests and documentation built on the wrong assumption.

Preserve the user's requirements and permissions when enhancing a prompt. Keep
unsupported assumptions visible and ask only questions that matter. Clear
requests should stay quick. I have observed better clarity; the effect on rework
and technical debt still needs measurement. Prompt enhancement addresses the
instructions, controls govern changes, and regression checks help prevent repeated
failures.

The journey I want is straightforward: request a scoped change, inspect the result
and its checks, understand any remaining issue, and continue from verified work.
A short reply, a click, or a natural-language correction should carry the same
decision. Keep explanation length separate: a detailed explanation can still end
with a one-word answer. Keep a text fallback available if a form disappears.
These interaction preferences are an approved design; the full interface still
needs implementation and testing.

I would measure the next improvement by time to the first useful finding,
unnecessary interruptions, repeated calls, and cost to reach an accepted result.
Those measures connect the controls to the user's experience of getting work done.

[More warning, progress and decision examples](../user-guidance-examples.md)
connect this direction to the current code and distinguish existing behavior
from proposed user-facing wording.
