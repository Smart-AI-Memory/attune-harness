# Graphical journey prototypes

These are retained design demonstrations, separate from the production GUI.
They preserve the existing journeys while production integration proceeds.

- `navigation/harness-workspace.html`: workspace navigation and host choice.
- `spec-workflow/spec-studio.html`: scope, optional research, questions,
  alternatives, review and revision acceptance simulation.
- `refined-workspace/attune-workspace.html`: opportunity selection, fix triage,
  author inspection and state-dependent forms.
- `session-continuity/continuity.html`: two-session context recovery.
- `live-mining/index.html`: live-result review and the authored getting-started
  tutorial; requires its local server. The HTML tutorial is not model evidence.

The first four are editable presentation sources. Generated `preview.html` host wrappers remain in the private local archive rather than being distributed as application code.
They are demonstrations, not production authority or memory stores. Their browser
state may be local to the page or presentation host; do not delete it during a
migration without an export path.

Private source excerpts, model receipts, screenshots containing live results and
session notes are intentionally not published. A verified local preservation
archive contains those original artifacts. The live-mining server requires a
user-supplied `context.txt` beside it. Clicking its live-run action invokes the
configured Codex CLI and consumes usage; publishing this source authorizes no run.
The production companion is `python -m attune_harness.gui --task ABSOLUTE_TASK`.
It currently provides read-only owner snapshots, with no dispatch endpoint.
