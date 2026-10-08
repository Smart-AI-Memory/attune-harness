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
The installed 1.3.0 companion is limited to draft intake and intent approval.
Build grants, dispatch, resume and broader GUI controls remain deferred to 1.4.0.
These retained prototypes do not qualify the installed release or human acceptance.

## Reproduce the retained browser checks

The public checks use Playwright's Chromium browser and an ephemeral loopback
fixture host. The host implements only the presentation `widgetState` API used
by the three fragments; it stores authored demo state in the browser session.
It does not need generated preview wrappers or private session records.

In a separate test environment, install Playwright and its Chromium browser:

```sh
python -m pip install playwright
python -m playwright install chromium
```

From the repository root, run each check with a new output directory outside the
checkout. Existing output directories are refused so older evidence stays intact.
If `--output` is omitted, a new temporary directory is retained for the results.
Each run prints its output directory. Optimized Python (`-O` or
`PYTHONOPTIMIZE`) is refused because it disables the checks' assertions.

```sh
python prototypes/spec-workflow/verify.py --output ../prototype-checks/spec
python prototypes/spec-workflow/review-use-cases.py --output ../prototype-checks/review
python prototypes/refined-workspace/verify.py --output ../prototype-checks/refined
python prototypes/session-continuity/verify.py --output ../prototype-checks/continuity
```

The scripts exercise validation, revision acceptance, context selection,
opportunity drafts, session reconciliation, reload persistence and responsive
layouts. [The retained spec review](spec-workflow/use-case-review.md) describes
three observed scenario limitations that the review script reproduces.
JSON results and screenshots are run artifacts and stay outside Git. These checks
exercise a fixture host, not the original AI-host wrapper or a production memory
service. They make no model calls and do not grant execution permission.
