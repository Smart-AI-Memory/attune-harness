# Design note before implementation

The case study found useful specialist capabilities with incomplete handoffs.
The first slice connects selection, execution and receipts; it does not merge
the engines or repair every legacy route.

Use a versioned testing policy under the existing task envelope. RunStore owns
atomic checkpoints and the writer lease; TaskExecutionStore projects execution
into the task; RecoveryCursor records the pre-dispatch boundary and exact result.
Existing status/resume/cancel dispatch on the testing profile. Review and repair
records retain their formats and semantics. Unknown test effects cannot use the
read-only retry reconciliation path.

Expose the human verb `test` with explicit scope, interpreter and task directory;
default invocation produces a bound intake preview, and `--accept` authorizes the
displayed deterministic plan. A saved preview can be accepted by checkpoint.
The task directory is outside the repository so evidence cannot enter its own
snapshot. The established forms workspace renders preview and result; its output
is a projection, while the task JSON is authoritative.

Capture HEAD and the Git index/working-tree file inventory (tracked plus untracked
nonignored regular files), hashes and deletions, with bounded counts/bytes.
Copy the captured bytes into the task's execution directory, verify each against
the accepted manifest, and check freshness before and after dispatch. Never stash,
reset or overwrite the user's checkout. A changed source/test/config snapshot
invalidates reuse. The coarse whole-input snapshot intentionally favors freshness
over avoiding invalidation from unrelated later edits.

Selection computes import relationships and filename hints without assuming that
static Python analysis proves completeness. Automatic mode therefore shows the
broader named test directory fallback. Operator-supplied targets are a deliberate
narrowing with missing coverage disclosed. No model or provider is required.

Reuse Harness process.invoke, already qualified for bounded supervision and group
cleanup. It retains complete output up to its accepted byte limit and reports
overflow. Save the streams as immutable task artifacts before declaring execution
complete. This avoids Attune AI's separate 10,240-character truncation without
changing its generic VerificationMixin callers or replacing attune-verify.

A small Python worker uses the selected interpreter's pytest and a pytest plugin
to capture collected tests, phase counts, collection errors, skips, return code,
pytest version, and loaded repository module origins. The worker emits a bounded
JSON artifact, which the host checks together with the actual process result.
It cannot grant acceptance. Require executed call phases for a pass and reject
collection-only, missing/inconsistent worker evidence, stale files and incomplete
output. Use repository source paths before installed packages; record the remaining
environment limits rather than claiming hermeticity.

After a durable execution event, pause/resume uses its artifacts and hashes.
A crash during dispatch is unresolved; it requires inspection/cancellation and a
new explicitly accepted attempt. A completed timeout/interruption receipt is not
retried automatically. Status never dispatches. These are existing recovery
principles applied to test effects, not a new gate system.

Rejected alternatives: using the maintenance placeholders as an executor;
changing generic verifier success semantics globally; trusting console text alone;
creating a model router for routine test execution; using basename matching as a
complete impact analysis; silently repeating an interrupted test process.
