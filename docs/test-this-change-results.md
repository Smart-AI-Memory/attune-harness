# Test this change — first slice complete

2026-09-17. The approved capture → selection → execution → durable result journey
is implemented as `attune-harness test`, with existing `status`, `resume` and
`cancel-task` controls. The verifier does not need replacing: `attune-verify 0.6.0`
continues checking supported document claims. The new pytest policy reuses Harness
process supervision and task/recovery storage. Attune AI's generic verifier and
specialist testing routes are unchanged.

## Behavior

- Explicit scope means working-tree changes against Git HEAD, including untracked
  files and staged deletions. Snapshot capture binds source, tests, configuration,
  interpreter and observer identity. Tests execute copied inputs; unrelated dirty
  work is preserved. Clean-only scopes and unsafe storage paths are rejected.
- Import and filename hints are disclosed. Automatic selection uses a visible
  broader fallback to the named tests directory. Explicit narrower targets show
  excluded checks. Full inventories remain in the saved task; console lists are
  bounded and link that record.
- The actual pytest runtime validates effective default discovery settings before
  collection. Its precedence rules handle INI/TOML configuration. Custom patterns
  are blocked rather than silently omitted; custom collectors remain unqualified.
- Actual collection/call outcomes, current inputs and intact output artifacts are
  required for passed-within-scope. Collection-only, all-skipped, empty, failed,
  interrupted and blocked results remain distinct. The existing forms grammar
  renders the evidence and offers a specific follow-up only when warranted.
- Completed attempts replay evidence without another subprocess. A crash during
  unknown-effect dispatch cannot use read-only retry; cancellation preserves the
  uncertainty. New attempts require new accepted inputs.

See the [CLI usage](../README.md#test-this-change) and the real
[durable grammar rendering](receipts/test-this-change-implementation/installed-spec-receipt.md).

## Validation

| Evidence | Result |
|---|---|
| Final source testing/process/task/recovery compatibility | **307 passed** |
| Outside-tree installed wheel, same bounded suite | **304 passed, 3 source-only deselected**; all three pass in source |
| Testing-policy behavioral cases | **38 passed**; real subprocesses and disposable Git repositories |
| Actual Spec completion repair through installed preview → accept → status → resume | **80 passed**, one dispatch, saved record unchanged on status/resume |
| Installed production origins | **11/11** selected module hashes match current source |
| Protection removal in disposable copies | **4/4 removals detected; 6/7 targeted tests failed**, one unaffected interrupt control passed |
| Host-policy coverage | **88.25%** over four new host modules, secondary Python 3.10 run |
| Formatting/lint | New modules/tests pass Black and Ruff; tracked diff passes whitespace check |

[Exact commands and exits](receipts/test-this-change-implementation/qualification-commands.json),
[source output](receipts/test-this-change-implementation/source-suite.stdout.txt),
[installed output](receipts/test-this-change-implementation/installed-suite.stdout.txt),
[real Spec receipt](receipts/test-this-change-implementation/installed-spec-journey.json),
[mutation runs](receipts/test-this-change-implementation/mutations.json), and
[coverage](receipts/test-this-change-implementation/coverage.txt) retain the evidence.
The subprocess observer has behavioral coverage; the percentage above does not
claim subprocess line coverage.

The installed trial uses a new target-installed wheel outside both source trees,
with the previously qualified integrated Python 3.12 dependencies and Verify
0.6.0. This is not a new dependency resolution or active installation update.
Wheel SHA-256: `28086a1aa95f2e2647621bdc1d45fb548c6a260a596bea1dd4e29bd0111ee3f3`.
The supplementary coverage environment is existing Python 3.10 with forms0.17.0;
its Verify0.6.1 is not invoked by those testing-only cases and does not qualify
that version for document-verification routes.

## Review and learning

The [independent review](receipts/test-this-change-implementation/implementation-independent-review.json)
found clean-scope provenance and symlink-parent storage defects. Both are repaired
and exercised centrally. Two preliminary findings about test directories and
cancelled unknown effects were fixed during review. The
[lead closure](receipts/test-this-change-implementation/review-closure.json) preserves
that distinction; it is not a new independent approval of the final diff.

Two installed trials exposed an over-strict duplicate configuration parser.
Removing it and asking pytest to validate its own effective settings reduced code
and made the boundary more reliable. Their failed outputs remain in the attempt
archives. This is the useful lesson: reuse the owning engine's interpretation,
then validate the result against the accepted Harness contract.

One actual CLI case measured preview **6.72s**,
accepted execution **9.32s**, status
**1.02s**, and resume
**1.72s**. Internal intake was
5.67s and execution 6.07s.
These are command wall times from one case, not native-form visibility timings or
a representative latency benchmark. O-11 records a bounded profiling opportunity.

## Support boundary and completion

This qualifies local macOS/POSIX regular-file Git working-tree changes, pytest
with default Python file discovery, and explicit interpreter/plugins. Other
platforms, committed revision ranges, custom collectors, ignored/Git metadata
inputs, hermetic dependency capture and arbitrary external test effects remain
outside this profile. Copied execution is not a security sandbox. The output
budget is explicit; overflow cannot pass. Coarse snapshot invalidation includes
unrelated later file changes.

Existing specialist generation/repair/maintenance handoffs remain separate O-10
work. No provider-backed pipeline, live model campaign, release or plugin
activation was performed. The lifecycle gates that ran are retained in
[lifecycle.jsonl](receipts/test-this-change-implementation/lifecycle.jsonl); the
symbol gate checked zero cited tokens and is not implementation proof.
All three approved implementation units are recorded through the existing Spec
state API. Completion scores in those executor receipts mean checklist completion,
not model confidence or a provider-generated quality score.
