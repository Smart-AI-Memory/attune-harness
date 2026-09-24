# Session observations — September 24, 2026

Patrick supplied this feedback while scoping the remaining work for 0.6.0,
in response to the request for session-start memory observations in D25.7.

His most noticeable experience was missing Attune AI features: memory saving,
automatic work on the opportunities list, cross-review, enhanced prompts, roundtable, and other familiar
workflows he has not individually named yet.

This is an observation about missing capabilities. It does not establish that
the served memories were irrelevant, stale, repeated or incorrect, or that a
week of dogfooding is complete. No claim about those outcomes is inferred.

## Relationship to the current plan

- Phase 3 task 3.3 improves serving existing memory: provenance, filtering
  withdrawn records, and prompt-related recall. It does not restore durable
  memory capture or the other workflows Patrick named.
- Versioned scratch storage is implemented, but does not by itself restore
  Attune AI's durable memory-saving workflow.
- Cross-review is named in the later host-surface plugin work (H5 / M2,
  D30), scheduled during the candidate period rather than for 0.6.0.
- The specific automatic opportunities-list workflow Patrick misses needs
  identification before its implementation or availability can be assessed.

Sources: [Phase 3 design](../phase-3-design.md),
[native-memory scope](scoping.md),
[host-surface design](../release-1.0/host-surface-design.md), and
[D25/D30 rulings](../release-1.0/addendum-2026-09-23.md).

## Scope decision, September 24

Patrick directed: "prioritize them immediately after 0.6.0". Keep the current
0.6.0 scope; prioritize memory saving, automatic opportunities-list work and
cross-review, enhanced prompts and roundtable immediately afterward. This updates the earlier sequencing for
those capabilities without claiming they are already implemented or fully
specified. Identify the exact capture and opportunities workflows in that
follow-on work. The serving-only change does not resolve this feedback.
