---
name: roundtable
description: Consult two or three explicitly named model seats through the shared bounded Harness CLI.
---

Read the repository's authority and budget rules. Reuse the user's question,
scope and configured participants; do not invent provider access or substitute
models. Keep the chair's lean out of the first-round participant brief.

Inspect `attune-harness roundtable --help`. Prepare with `roundtable prepare
--project ROOT --path FILE --config CONFIG --run-dir RUN`; repeat `--path` for
each selected file. Configuration names the author, two or three distinct
provider/model identities, timeout per call, and one or two rounds. The first
round is independent; the second sees only the completed preceding round.

Inspect the retained contract and budget. Only with the user's upload, provider
and spend authority run `roundtable run RUN --accept DIGEST --allow-external
--allow-native`. Command wrappers need external authority but no native flag.
Both coding hosts use the same run directory and CLI, never parallel authority.

Use `roundtable status RUN` to inspect without calls. A paused run continues
with its accepted contract; completed turns replay. An uncertain dispatch stays
unresolved. Stop continuation with `roundtable abandon RUN --checkpoint DIGEST`
only after checking the owner; retained unknown effects stay unknown. In-flight
interrupt stops the supervised process and preserves uncertainty; it does not
prove external activity stopped.

Report each seat's verdict, evidence, requested and runtime-reported identity,
and disagreements. Missing model metadata remains unknown. The chair makes the
decision; votes and summaries never authorize edits, spending or merging. No
automatic fallback, retries, extra rounds or paid synthesis.
