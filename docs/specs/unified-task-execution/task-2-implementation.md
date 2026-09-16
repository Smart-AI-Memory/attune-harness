# Task 2 implementation note

Prepared September 16, 2026, after baseline commit `e546cc6`. This is implementation preparation; Task 1 acceptance and its review-route decision are still pending. No production changes accompany this note.

Execution update: Patrick subsequently selected offline Task 1 acceptance. The canonical collector accepted Task 1 and started Task 2. This note preceded the production diff; [the implementation receipt](task-2-receipt.md) records what was built and checked.

Deliver one versioned intake envelope, one durable task identity, and an accepted record using the existing `RunStore`. Keep the dependency-free public core and the legacy two-role form unchanged. Goal intake and the legacy positional request must be explicitly exclusive. Task 2 ends at accepted intake; it must not claim to have assessed a document before Task 3 provides execution.

Cases to prove: solo and independent-review forms; valid headless and interactive answers; missing, declined, stale, duplicate and unknown controls; changed registry, source bytes, scope or budgets; copied records and invalid revisions; immutable assignment identities; task-state/source overlap; current-task answer reuse without inherited approval; explicit allowlisted profile defaults; cache hit, bypass, clear, eviction and corruption. Failure cases dispatch nothing. Acceptance and effect/provider permission must remain separate fields bound to the revision.

Actual disposable probe: `.venv-voyage312/bin/python` constructed and validated a solo form through attune-forms 0.17.0 while the legacy form retained its reviewer field. A versioned draft task record round-tripped through `RunStore.save`/`read_record` with a valid checkpoint. No provider calls occurred. Raw probe: `/var/folders/5t/bzsz5qd17pd7h_wwwd5qjbnw0000gn/T/harness-task2-disposable-nmsf5g1v/probe.json`. These observations support reuse of the form library and storage primitive; they do not establish a complete task contract or runtime.

Use bounded process-local immutable template entries, keyed by schema/policy/forms version, project, source selection and registry dependencies. Bind task IDs, revisions, answers and acceptance separately on every presentation. Record cache outcomes without answer contents. The Task 1 warm schema-build median was 0.171 ms versus 227.052 ms for the guarded fresh process, so a persistent on-disk rendering cache is not justified by the current evidence. Measure cold/warm/bypassed behavior without claiming a benefit in advance.

Keep task storage outside the selected keyword corpus; a corpus containing the proposed state root must fail with an actionable alternative run-root selection. Voyage intake must respect its explicit generation and scope through the existing public validation path. Do not modify Voyage validation ownership in this task. Preserve hashes of accepted inputs and selected participant settings; material changes require a new revision and invalidate dependent bindings.

Rejected alternatives: weakening the legacy two-participant form to support solo (breaks accepted old requests); creating a second JSON persistence implementation (duplicates locking and failure behavior); saving bound form responses in the cache (reuses action authority); a persistent rendering cache before measured benefit (adds storage and invalidation cost without evidence).

Validation will combine focused contract/intake failure cases, the 28 baseline compatibility cases and existing review/recovery suites. Import the public core in the preserved dependency-free environment. Guard-removal probes must demonstrate that identity, stale-input and source-state exclusion checks can fail. Record tests and limits separately from any paid model-review score.
