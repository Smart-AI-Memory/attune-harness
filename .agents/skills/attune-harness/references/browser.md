# Open and resume browser forms

Use the existing loopback companion for saved tasks. This route opens a form; it
does not execute a Harness workflow. Keep the same explicit runtime selected by
the main skill, and read its GUI help before constructing the launch command:

```sh
python -m attune_harness.gui --help
python -m attune_harness.gui --task /absolute/path/to/task --launch-json
```

Here, python means that runtime's interpreter, not an unrelated global Python.
Task directories must already exist at canonical absolute paths; register at
most 20 distinct tasks by repeating --task. Resolve relative paths first. Add
--edit only when the user's intent covers answering intake or recording explicit
intent decisions. Never add --allow-build-commands as part of opening a form.

If the user starts with an idea and has no saved draft, prepare it through the
existing plan/work owner using the actual project, supplied scope and configured
participants; follow the plan/build workflow reference. Leave missing material
intent unanswered rather than inventing it. Preparation creates a draft, not
acceptance or dispatch. The source checkout's
docs/specs/saved-request-journey/README.md contains the owner walk and a synthetic
training example; do not treat the sample as the user's real task.

## Open in the host

Run the server as a retained process. Structured mode emits one JSON startup
line and suppresses automatic external-browser opening. The process stays alive
until stopped; its eventual exit status is not a startup readiness signal.

The record has type attune-harness.browser-launch, version 1, origin, launch_url,
editable, task_count and execution_enabled. Require the recognized type/version,
execution_enabled false for this route, a loopback HTTP origin, and launch_url
matching that origin with a nonempty fragment. Treat it as private launcher
data. Pass the exact launch_url to an available browser-opening tool; never
execute it as shell code, invent a different port, strip the fragment, or put it
in a committed artifact, public page, log or upload.

If the callable Codex open_in_codex tool is available and its schema supports a
browser target, open the emitted URL using the host's default placement.
Use the actual tool schema; do not request custom pane positioning. A queued
result means queued, not rendered. Do not
repeat queued requests. If a browser tool is unavailable, let the user open the
private launcher link manually; report that fallback clearly. Never work around
a native app inspection or permission block.

Use the host's **Enter split view** control to show chat and the form side by side.
Use the host's default layout. Observe the actual result; a URL-opening request
does not prove rendering or placement. Codex's existing Files control remains
on demand at its host-defined position. Structured launch output does not alter
host geometry or provide custom pane docking.
The requested workspace order is Codex navigation, primary chat, enhanced forms
view, then Files at the far right. Verify placement in the host before claiming
that arrangement is supported; the companion cannot move Codex's own panels.
The [official browser guide](https://learn.chatgpt.com/docs/browser) documents
Enter split view and Cmd+Shift+B (Ctrl+Shift+B on Windows/Linux). It does not
document an arbitrary pane-swapping or docking API.

If an older runtime lacks --launch-json, use its documented --no-open option
and the printed private launcher link. Do not upgrade a retained runtime merely
to open a form. Host rendering and available form types depend on the runtime:
older blob snapshot views may need a regular browser, while the forms-only
companion can render directly in the built-in browser.

## Reopen saved work

While the same listener is running, reopen its same private launch URL. Refresh
saved state and deliberately open the current form. Saved answers are read from
the task's authoritative record. Do not silently replay the previous submission.
In a candidate with saved-request inspection, View saved request / View accepted
request opens a read-only summary of that owner revision. A stale-input warning
means its acceptance is historical; inspect before continuing. This addition is
not a claim about a published runtime that lacks saved-request inspection.
Unsaved typing is not guaranteed to survive tab closure; copy it before closing.

After the listener stops, its old launcher is invalid. Start a new listener for
the same registered task directories and use its new private link. Saved answers
remain in the task record; old form checkpoints may be stale. Inspect current
guidance rather than retrying a lost submission.

Do not call attune-harness resume to reopen the page: that command may dispatch
participants or effects. Form opening, saving answers, accepting intent and
executing work remain distinct actions. Keep the preview running until the user
is done, unless they ask to stop it.
