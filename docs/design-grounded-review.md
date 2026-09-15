# Grounded local review increment

Patrick authorized requiring source-backed findings and a substantive verdict,
then testing the revised workflow. Done means a packaged strict review mode,
behavioral/negative tests and a frozen local evaluation with failures retained.
Keep the 2,048-token evaluation ceiling, 32 KiB narrative/64 KiB JSON boundaries,
existing recovery controls, independent roles and zero paid calls.

Pre-code read-only probe: the retained dev5 q006 invents a conflict on a clean
policy; q035 falsely says the reference promotes unknown claims; q033 only
announces findings. All were accepted as nonempty free text. The saved
`receipts/grounded-review/pre-code-probe.json` records these failures without
new model calls. The prior verifier probe established that link verification
cannot certify policy prose.

Add an explicit `--grounded` local-adapter mode, recorded in the accepted command
configuration and generation receipt. It is mandatory in the revised pilot;
preserve the original default mode for reproducible existing workflows. The
outer participant wire protocol stays unchanged. Strict output has an enum
verdict (`issues_found`, `no_supported_defect`, `uncertain`), reasoning, an
uncertainty account, and at least one assessed passage pair. Each pair contains
an exact document quote, retrieved reference path and exact reference quote,
an enum assessment (`contradiction`, `consistent`, `uncertain`), and reasoning.
Findings are the contradiction assessments, rendered from validated objects.
No model-supplied claim IDs or tool-verification labels are accepted. Tool scope
is labeled separately in the prompt and final presentation. Verdict and
assessment relations must agree. Require meaningful text rather than a bare
introduction, without imposing a new character cap or word-count target.

The host checks citations against the accepted document and retrieved excerpts,
never follows a model path or fetches a source. Reject unknown/ambiguous paths,
invented/blank quotes, unsupported keys, malformed shapes, duplicate assessments,
empty reasoning and inconsistent verdicts. At least one cited assessment is
required even for no-defect/uncertain verdicts. Reject pure headings or unfinished
introductions ending in a colon. This is a limited structural guard, not a
semantic quality proof: true quotes can still support a false interpretation.
Retain rejected raw generations and errors without automatic retry or fallback.

Rejected: merely raising token budgets (all prior generations stopped below
the ceiling); accepting a free-text verdict plus optional citations (lets empty
or unsupported reviews through); treating source matching as verification of
truth; rewriting historical receipts to use the new contract.

Testing: exact Unicode/source matching, source escape/ambiguity, false provenance,
verdict consistency, old failure shapes, long valid outputs and transport limits,
failed-generation retention and config-change rejection. Package as dev6 in a
new isolated environment; keep dev5 installed for prior receipts. Run the full
suite, targeted mutation checks, installed workflow/recovery checks, and a new
frozen campaign: six retained regression cases plus three fresh recovery-policy
cases (clean, critical and explicitly uncertain), three repeats, two Harness
roles. Compare the regression subset descriptively with the frozen dev5 results;
run dev5 single-pass only on the fresh cases. At most 63 local generations,
1,200 seconds, no retries or tuning after observing outputs. Fresh cases are
held out from model/prompt tuning, not from their author. Freeze case/oracle,
code, package hashes and criteria before generation; grade the rendered reviews
with labels hidden, keeping failed/unrun workflows in denominators. Require all
27 revised trials complete, zero critical misses, zero unsupported assertions,
and uncertainty preserved across all nine ambiguous trials. A failed quality
target remains revise/inconclusive rather than silently changing the rubric.
