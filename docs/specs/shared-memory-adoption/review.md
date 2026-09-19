# Shared memory adoption — planning receipt

Status: plan ready for chair review; no task started or accepted.

The five XML tasks parse through Attune's actual spec reader. Source inspection
and the existing preflight establish the baseline; no integration test or new
native experiment has been represented as already passing.

A bounded different-model review by gpt-5.6-sol/high used the evidence-chain
receipt class and made no edits, tests or provider calls. Its findings were
resolved before the chair-facing plan:

- Use an exact isolated Attune AI checkout rather than absolute mutation paths
  into the dirty main checkout. Task 1 records and verifies its path/HEAD first.
- Name actual installed product entry points and test CLI/MCP transport through
  durable shared-worker records, not direct adapter construction alone.
- Include keyed working-memory and persisted-pattern data in the preservation
  baseline alongside raw, personal and curated memory.
- Preserve root identity when personal documents share a relative path. Do not
  translate exact record deletion into existing cross-root topic deletion.
- Ground the historical receipt count: central hash verification confirmed 104
  preceding native receipts plus four journey receipts, totaling 108.

The reviewer rechecked those fixes and reported all five closed with no introduced
contradiction. The root independently inspected the cited source behavior and
reran the frozen receipt verification. This review qualifies the plan, not the
unbuilt implementation.

After that review, Patrick clarified that remote-user usage collection is no
longer needed. R8 and D8 distinguish it from local memory feedback and accounting.
Source inspection confirmed separate local writers and a UsageTracker exit-time
upload hook. Tasks 1 and 4 now require a purpose map and a shutdown-inclusive
no-upload check. This clarification has been checked by the lead; it is not
represented as part of the earlier five-finding different-model review.

The task boundary runs the existing `attune.gates.lifecycle.run_boundary` API
with the actual XML create/modify paths. Its ledger is saved under this project's
`docs/receipts/shared-memory-adoption-planning/`. The CLI's default global ledger
was unwritable in this sandbox, so the same runner's supported `ledger_file`
argument supplies the local destination; no gate is waived or replaced.

Mechanical symbol and falsifiability gates pass. The existing chair-review gate
requires acknowledgment because the cross-product plan changes `pyproject.toml`.
The mechanical symbol check covers the task document's cited tokens; the manual
source inventory and parsed XML supply the broader path evidence. Neither check
proves implementation behavior.

Canonical workspace: `spec-461d7dcb00604997b9ac1110d4df773b`.
Creation was within the accepted adoption-planning request. Implementation-plan
approval, lifecycle acknowledgment and execution have not been recorded.
