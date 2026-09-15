# Passage review — implementation design

Patrick authorized implementing the reliability/accuracy review. This increment addresses priorities 1 and the next bounded local quality comparison in priority 2. Native platform qualification and broader model/team evaluation retain their separate evidence requirements.

## Evidence before code

The read-only replay reproduced all 27 dev6 rejections. Every trial used unsupported absolute reference paths; 22 cited the reviewed document as a reference, eight supplied absent document quotes, and ten had internally inconsistent verdicts. The categories overlap. All 130 targeted software checks passed. Thus the existing rejection guards work, while model-authored citation bookkeeping prevents useful completion. The replay and raw failures remain preserved.

## Design and cases

Add explicit `--grounded-passages`, mutually exclusive with the original `--grounded`; preserve the original mode and its frozen dev6 artifact. Use a small dependency-free module that reuses existing source validation and tool-scope projection. The host divides accepted text into nonempty paragraph blocks without normalizing Unicode or line endings. It assigns distinct document/reference identifiers bound to the accepted evidence revision, exact block offsets and source identity. The model receives the complete block text and can select only IDs enumerated in a per-request JSON schema. It supplies passage relationships, reasoning and uncertainty. Paths, quotes and the aggregate verdict are generated in code. Actual source matching does not certify the relationship judgment.

Cases: valid Unicode/CRLF passages render exact slices; contradiction/uncertainty/consistent relationships derive the expected verdict; blank input, unknown IDs, cross-role IDs, stale IDs, duplicate pairs, empty reasoning, self/ambiguous/escaped references, and model-supplied paths/quotes/verdicts are rejected. Retain failed generations, correlate the original turn, respect output limits, deny duplicate dispatch, and reject resume after the selected mode changes. Prove semantic limits with a wrong relationship on real source passages remaining explicitly unverified.

Alternative rejected: accepting arbitrary absolute paths or normalizing copied quotes would preserve ambiguity and hide the deeper errors. Asking a model to restate an aggregate verdict duplicates a deterministic decision. Changing `--grounded` in place would alter accepted commands and invalidate the original comparison's meaning.

## Validation and local evaluation

Add behavioral cases plus targeted mutations for changed adapter behavior; run the full suite in the qualified test environment. Build dev7 and install offline into a new isolated environment. Exercise actual installed command/recovery flows and verify every installed module against the wheel. Preserve old wheels, environments, raw generations, grading and experiment sources.

Freeze a separate campaign before inference: nine retained cases plus three fresh cases, three repetitions; passage-based Harness on all twelve and the original dev5 single-pass baseline on the three fresh cases. Maximum 81 local generations and 1,200 seconds, no retries or tuning of the frozen campaign. Use the already-qualified local Llama model/tokenizer, existing 2,048-token ceiling and transport boundaries. No paid provider is needed for this bounded comparison. Require all 36 Harness workflows to complete, zero critical misses/unsupported assertions, and explicit uncertainty preserved across 12 ambiguous trials. Failures stay in denominators. Compare matched fresh cases separately; historical regressions are descriptive. Grade rendered narratives against a separate answer key before opening arm mappings, retain judgments and their limitations, and report usability separately from semantic accuracy. A failed quality target remains revise; a working renderer does not justify promoting this mode to the default.
