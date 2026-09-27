# Voyage plugin journal: interrupted dispatch

This is the first host-side slice of the approved [executable-plugin
specification](specs/executable-plugins/README.md), requirement R6. It does not
wire Voyage to executable plugins or qualify a live provider.

The host keeps the paid-stage ledger and writes `dispatching` before invoking a
provider. A child stopped during a paid operation must leave that durable state
intact. The next attempt refuses it as unresolved, without another dispatch.
The provider adapter will signal a stopped subprocess using `PaidStageInterrupted`;
`StageJournal` translates that signal to a fixed, safe `PaidStageUnresolved`
diagnostic without replacing the stage record. Neither raw child output nor
exception text enters the billing record.

Cases to prove: embed and rerank interrupted after dispatch; refusal on a fresh
journal with either value of `allow_provider`; no second provider call; retained
call budget; completed replay without permission; and ordinary SDK exceptions or
invalid results still recorded as `unresolved`. A real bounded subprocess timeout
must exercise the interruption path. A deliberately abrupt host exit provides the
comparison: its existing durable state is also `dispatching`.

Before implementation, an isolated probe against main `aa0f765` injected a
`TimeoutError` from the provider and read back `unresolved`. Thus existing caught
exceptions do not meet the spec's exact interrupted-child state, even though they
already prevent retry. The new signal distinguishes a stopped child from an SDK
error. Broadly leaving every provider exception as `dispatching` was rejected:
that would change existing diagnostic meaning for errors and invalid responses.

The signed plugin adapter, accepted signer/grant binding, compiled dependency
closure, full index/retrieval differential and authorized live comparison remain
later slices. A declaration of network access alone never authorizes a paid call.
