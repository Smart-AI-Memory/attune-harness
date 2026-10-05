# GUI client regression verification

Run from a source checkout:

```sh
python -m pytest tests/test_gui_client.py -q
```

This command requires Node.js on PATH and fails if it is absent. It does not
skip. The normal full pytest suite includes the same check. No npm dependency,
live model, paid API, GUI server, or retained installation is required.

The Python test imports the shipped `attune_harness.gui_forms.FORM_SCRIPT` and
passes it to `gui_forms.cjs`. The Node runner executes it with deterministic DOM,
fetch and timer seams. Checks assert recoverable answers after 409/network loss
and failed post-submit refresh, disabled expired submissions with no replay,
deliberate reopening without mapping an old `answer_0` into the remaining
question, stable changed/unchanged polling with preserved focus, selection and
scroll, rejected delayed responses after a panel switch, terminal polling stop,
and the offline intake/accept/separate build grant/evidence/resume sequence.

The lightweight DOM records element identity and text selection; it does not
implement browser layout, CSS, accessibility, CSP, or host process behavior.
Actual browser visual verification and existing HTTP/backend authority tests
remain separate evidence. These checks do not qualify any live model or platform.
