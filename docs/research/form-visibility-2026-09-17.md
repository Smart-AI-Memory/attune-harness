# Native question visibility investigation — 2026-09-17

## Question and method

Patrick reports that questions sometimes disappear while he is reading, and that
hovering appears to act like a click. Inspect the installed Codex app's native
async-question path separately from Attune's HTML widget. Reproduce the relevant
handlers and state transitions in an isolated process using synthetic questions.
Do not modify the installed app or submit a real answer.

The installed app is `/Applications/ChatGPT.app`, bundle identifier
`com.openai.codex`, version `26.908.70816`, build `9275`. Its application archive
contains the native question UI. The reviewed path is the one generating
`request_user_input_async` question IDs and `send_user_message_question_reply`
responses, matching this conversation's earlier forms.

Cases: pointer enter versus explicit click; highlight versus answer selection;
automatic opening and its deadline; deadline expiry after hover; interaction
or draft changes cancelling the old deadline; completed-turn rendering.
Use the actual extracted handler functions where feasible, with stubbed React
element construction and state atoms. Report static checks separately from
executed handlers. A deliberate click is the positive control for option
selection. Removal of the interaction guard must make the deadline check fail.

This establishes local code behavior, not a visible-host reproduction of Patrick's
specific incident. No screen capture, private conversation database, provider
call or remote telemetry is required. Keep hover, timeout and turn-completion
explanations distinct. A persistent Markdown decision remains available while
native behavior is unresolved.

Rejected approaches: treating a form tool's success as proof of visibility;
attributing host-native behavior to Attune's widget without tracing the route;
patching a signed third-party app; treating pointer proximity as proof of a click.

## Results

The [probe](../../experiments/form_visibility/probe_native_question.cjs) executed
six checks using actual extracted handler functions and synthetic state. All six
passed. Three additional code-wiring checks passed; these are static checks, not
browser interaction tests. Source fingerprints and exact results are in the
[receipt](form-visibility-2026-09-17.json).

1. Pointer entry changes the hovered option and its visual highlight. It does
   not call the option-selection callback, and the answer remains unchecked.
2. Explicit click calls option selection; this is the positive control.
3. Automatically opened questions receive a 30-second deadline.
4. Hover does not clear that deadline. Invoking its matching timeout handler
   closes the panel without recording an answer.
5. The user-interaction handler clears the deadline; an already scheduled
   callback with the old deadline then cannot close the panel.
6. Editing a draft also clears the deadline.

Static inspection additionally shows that the actual component schedules the
timeout dismissal, calls the interaction handler on pointer-down capture, and
returns no question panel once the turn leaves `inProgress`. The display path
and the answer-submission path are separate. The first suggested answer is not
treated as a submitted answer simply because the panel closes.

One protection-removal control omits the interaction callback before invoking
the old timeout: the panel closes, whereas it remains open when the callback
clears the deadline. This demonstrates the guard's effect in the extracted state
model; it is not a mutation of the installed app.

## Interpretation and response

Patrick's observation is plausible: hover changes visual emphasis and does not
protect a form from the concurrent timer. Turn completion is another independent
way for the panel to disappear. The probe establishes these mechanisms but does
not establish which event caused his specific incident or reproduce a native
pointer event stream. No production bug is claimed fixed.

Provide a persistent Markdown decision record alongside consequential native
forms. Keep unresolved decisions pending after disappearance and do not infer an
answer from timeout, minimization, hover or an assistant turn ending. Where a
native form is essential, qualify its visibility and lifetime separately from
payload validity. Do not patch the signed app or claim Attune's form renderer can
override this host lifecycle.

## Reflection checkpoint

**What changed our understanding:** the new mouse-over detail motivated inspection
of the actual native host. The first layer inspected, Attune's widget, is not the
renderer of the earlier async questions. Native source and handler behavior show
a deadline and turn-lifetime boundary that renderer microbenchmarks cannot cover.

**Method adjustment:** identify the active display route first, distinguish visual
highlight from selected/submitted state, and measure visibility/lifetime as well
as construction cost. Preserve the unresolved incident attribution. A later
visible-host trial should vary idle reading, hover, deliberate focus and turn
completion independently, without sending a real approval.
