# Review using host-owned source passages

The local reviewer can select source passages while Harness supplies their exact citations and calculates the overall verdict. This removes model-authored file paths, copied quotations and a duplicated overall-verdict field from the output contract.

**Experimental:** the dev7 local campaign completed 30/36 Harness reviews, but only 2/36 passed the full quality criteria. Incorrect passage interpretations and duplicate selections remain unresolved; see the [measured result](passage-review-receipt.md).

## Select the mode

Use the dev7 installation: this workspace's isolated interpreter is `/Users/patrickroebuck/attune-harness/.venv-passage-review/bin/python`, and its coordinator command is `/Users/patrickroebuck/attune-harness/.venv-passage-review/bin/attune-harness`. The older preserved environments do not provide this new flag.

For a **new accepted review**, set that interpreter as the first entry in each local `attune_harness.ollama_review` participant's command array and add `--grounded-passages`. If the array contains `--grounded`, replace that flag. The two modes are mutually exclusive. Use a fresh receipt directory for the new review; keep the chosen model identity, seed, tokenizer and output-budget arguments.

The evaluation configuration uses `--max-output-tokens 2048`; the unchanged default is 512. Only the configuration recorded in the quality receipt has live evaluation evidence.

Use the existing [local review workflow](pilot-workflow.md) to obtain the accepted request and run it. Changing the selected mode changes the accepted participant configuration, so obtain a new accepted review instead of resuming an old checkpoint with different commands.

The `--grounded` command retains its original dev6 quotation-based behavior. Omitting both flags retains the original narrative mode. Passage review is explicit and opt-in; the quality receipt determines what the evaluated model actually demonstrated.

## What the host checks

- Document and reference passages occupy separate identifier lists. The reviewed document cannot corroborate itself.
- Identifiers bind exact paragraph slices to their accepted evidence revision, source identity and offsets. Changed evidence invalidates old selections.
- The model selects only identifiers supplied in the request's schema, classifies their relationship and supplies reasoning and uncertainty.
- Harness rejects unknown or cross-role IDs, duplicate pairs, empty assessments and model-supplied citation or verdict fields. It renders the original text without Unicode or line-ending normalization.
- The overall verdict is `issues_found` when any relationship is a contradiction, otherwise `uncertain` when any is uncertain, otherwise `no_supported_defect`.

The generation record retains the complete citation catalog, accepted turn, actual prompt/schema, raw output and rendered result. Existing 32 KiB narrative/64 KiB JSON transport limits, context reserves, duplicate-dispatch protection and conservative recovery remain in force.

## What still needs judgment

Selecting a real passage does not establish a correct interpretation. A model can label two compatible passages contradictory or overlook a critical instruction. Every rendered review therefore remains an **unverified proposal**. The contract does not certify full-document coverage or approve a repair.

Read the [implementation design and evaluation criteria](design-passage-review.md) and the [passage-review receipt](passage-review-receipt.md) for measured completion, accuracy and limits. Windows/native service qualification is a separate workstream.
