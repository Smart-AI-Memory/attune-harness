# Task 3 implementation note

Auto-run authorized September 16: Task 2 accepted; remaining offline tasks proceed through their recorded checks. Live trials still require a frozen packet and separate spend authorization.

Move the existing assessment loop into task_runtime, retaining legacy operation keys and its exception/persistence boundary. The legacy review entry point passes its current evidence services to preserve integration seams. New task policy projects accepted identity/assignments into that loop and stores its execution as a versioned child of the authoritative task record; a store adapter saves the whole checkpoint under the existing writer lease. No second journal or loop is introduced.

The new policy supplies host retrieval and verification in each isolated assignment packet and permits only one final participant response. Solo has one assignment; independent review has two. Native evidence mode consumes the same host evidence. Scratch probe of evidence_step with the two completed host results, zero remaining tools and one remaining turn returned None, confirming the next exchange is the single native invocation. The unrelated attune.spec import in that scratch interpreter was unavailable; spec state uses its existing identified interpreter.

Cases: clean/refuted/unknown tool results, contradictory participant prose, invalid/tool output, stale inputs during dispatch, command peer, two identities, denied external calls, persistence failure and exact legacy regression. Integration retains attributed narratives and explicitly leaves semantic acceptance unknown. Durable execution is separate from document status. Accepted operation/output budgets are enforced.

Rejected: copying review into a new orchestration loop, treating successful tool verification as a model verdict, or returning an intake-only success from the primary accepted review command. An explicit --intake-only remains available for preparation and existing intake consumers. Recovery and installed qualification follow as Tasks 4 and 5.
