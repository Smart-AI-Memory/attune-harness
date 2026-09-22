# Voyage validation reuse — task ladder

Status: approved for execution. **Task 1 implementation/checks ready; 0/3 tasks accepted.**
The XML authority is `.claude/plans/voyage-validation-reuse.md`.

Patrick selected Voyage RAG assessment in attune-harness, then explicitly selected
the `/spec` planning workflow. He subsequently approved this task ladder.
Canonical workspace revision 4 records plan approval; revision 5 starts execution.
Both execution-boundary gates passed before Task 1 began.

| Task | Deliverable | Acceptance receipt | Depends on |
|---|---|---|---|
| 1 | Lock integrity/effect behavior and add reproducible offline timing | Behavioral suite, baseline source/check counts, portable fixture | None |
| 2 | Reuse the immediately checked generation | Same evidence and failures; one fewer full check; targeted mutations | 1 |
| 3 | Qualify the built artifact and record measurements | Installed suite, module hashes, separate timing runs in both orders | 2 |

## Acceptance summary

- Behavioral tests cover source/revision/selection changes, database and metadata
  tampering, scope, paid-stage recovery, grants and lifecycle failure.
- Metric probes show nonempty session recompute checks fall from six to five and
  cached replay checks from five to four, while all other boundaries remain.
- The suite receipt reports guard-removal detection counts. Any retained-boundary
  regression fails acceptance even when timing improves.
- Installed-artifact probes run outside the source tree, compare module hashes,
  preserve old environments, and use zero live provider calls.
- Timing receipts contain individual samples, cache states, source identity and
  forward/reverse run order; cold startup, live-provider, concurrency and coding
  outcomes remain unmeasured unless separately tested.

Read `requirements.md`, `design.md` and `decisions.md` before execution.
The reusable measurement script is `experiments/voyage/profile_validation.py`.
Task 1 passed 79 Voyage tests and the fresh 1,050-passage baseline; removing the
row-integrity guard in a disposable copy made 8/35 new tests fail. See the design
for measured counts, raw receipts and the acceptance status. The standard paid
review workflow has not run; the offline-review/auto-run choice is pending.

## Resume

Read the decisions and approval status before using the XML. Plan approval is
recorded; task acceptance remains separate. Preserve the workspace's actual
review decision through the canonical action collector.

If main has changed, compare the target code and repeat the decisive probes.
The historical 100-question index is stale against the current checkout and must
remain frozen. Use fresh fixtures and a separate qualification environment.
