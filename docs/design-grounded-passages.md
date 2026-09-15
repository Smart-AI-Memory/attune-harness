# Passage selection revision

The first grounded campaign is frozen and will finish unchanged. Read-only
diagnostics show repeated model-selected document paths in reference fields;
those are correctly rejected. The accepted document cannot corroborate itself.
This is a citation-selection usability failure, not a reason to weaken checks.

Revise the model-facing contract to select host-assigned document and reference
passage IDs. Catalog nonblank, substantive source lines from the accepted document
and retrieved excerpts. Keep the complete input in the prompt. Build JSON-schema
enums from that request's catalogs. The model supplies assessment, verdict,
reasoning and uncertainty, but cannot supply path or quotation text. Resolve IDs
against the same accepted turn, then use the existing strict renderer and all its
source/verdict/transport guards. Exact citations remain host-checked; semantic
interpretation remains unverified. An ID from another request cannot grant access
to that request's sources: IDs resolve only to this turn's catalog.

Retain dev6, its `--grounded` mode and the failed campaign. Add the revised
`--grounded-passages` mode in dev7; reject selecting both modes. Test unknown,
cross-kind and fabricated IDs, unsolicited quote/path fields, per-request enum
isolation, exact Unicode rendering, verdict checks, retained failures, and actual
CLI selection. Reuse existing bounds rather than create another word/character cap.

Rejected: normalize arbitrary model paths into references, accept document
self-citations, or fuzzy-match invented quote text. All hide evidence mistakes.

Run a second separately frozen acceptance smoke check after the first completes:
the nine existing cases plus three fresh clean/critical/ambiguous publication-
authority cases; one two-role workflow per case, at most 24 local generations.
Keep the pinned model and 2,048-token ceiling. The first campaign's early failed
roles limit its observed calls; the combined execution must remain within the
original 63-call envelope. No paid calls or automatic retries. Require all 12
workflows complete, all four critical opportunities detected, zero unsupported
assertions and all four ambiguous cases preserving uncertainty. Grade all delivered
narratives with labels hidden. This second smoke check has no repeatability or
general-superiority claim. Original nine cases are regression evidence; only the
new three are held out from prior model trials. Freeze everything before calls.
