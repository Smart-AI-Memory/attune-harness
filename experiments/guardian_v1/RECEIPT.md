# Guardian integrated experiment — local receipt

**Disposition: local experiment passed; native Windows/Linux qualification remains open.**

Executed September 14, 2026 (America/New_York; raw timestamps use September 15 UTC). This carries out the disposable next experiment in Patrick's attached architecture brief. It does not promote Guardian into the production package.

## Result

The coordinator accepted a content-hashed source fixture and external expected values, demonstrated four failing assertions, reserved one synthetic work unit, dispatched one fixture worker, and independently verified four passing assertions in its candidate. A separate client process displayed the retained outcome.

| Case group | Observed result |
|---|---|
| Basic repair and healthy input | Broken fixture repaired and verified; healthy fixture required no worker |
| Duplicate notifications | Repeated and related deliveries retained one incident and one effect |
| Concurrent admission | 12 producer processes admitted one incident |
| Concurrent dispatch | 8 tick processes produced one dispatch, one reservation and one effect |
| Crash before dispatch intent | Recovery dispatched the unstarted operation once |
| Crash after intent, no completion evidence | Unresolved through three recovery attempts; no worker replay; reservation retained |
| Crash after worker effect, before acknowledgement | Completion reconciled and candidate verified; one effect |
| Crash after acknowledgement | Verification resumed; one effect |
| Changed input, altered artifacts or completion records | Stale, rejected or unresolved as specified; never verified |
| Worker claimed success for an incorrect candidate | Independent verifier rejected all four failing assertions |
| Exhausted budget | Dispatch blocked with zero used units and no effect |
| Conflicting event identity | Explicit rejection; no extra incident |
| Repeated recovery and inspection | Completed result preserved without another effect |
| Path portability check | Workspace containing spaces and Unicode completed; explicit LF fixture bytes retained |

These are **20 deterministic cases across 18 groups**, using one arithmetic task. They are not 20 independent real repairs, a model-quality sample, or evidence of exactly-once behavior for arbitrary external tools.

## Runs and retained evidence

- [Run 01 summary](receipts/run-01/summary.json): 19/19 passed in 5.901 seconds. Original sources retained and matched against their pre-run hashes.
- [Run 02 summary](receipts/run-02/summary.json): 20/20 passed in 6.114 seconds. Explicit fixture byte writes fixed a Windows newline issue found during review; the added case covers spaces and Unicode in paths. No native Windows result is implied.
- [Run 02 freeze](receipts/run-02/freeze.json), [case outcomes](receipts/run-02/results.json), [raw test output](receipts/run-02/test-output.txt), and the per-case `*-commands.json` files retain source identities, assertions and process outputs.
- [Separate demonstration](receipts/demo-commands.json): deliberately lost acknowledgement, recovery, separate client inspection; four checks passed and one effect remained.
- [Preservation audit](receipts/audit.json): **all 4,890 protected original files unchanged**, including source, tests, wheels, documentation, old experiments and dependency files. Both campaigns' saved source snapshots match their frozen hashes; current experiment code matches Run 02.

The measured environment was **macOS 26.6.2 ARM64, Python 3.10.11, SQLite 3.51.0**. The ledger uses DELETE journaling with FULL synchronization. No package test rerun or rebuild was needed for these isolated additions; the audit confirms the protected package artifacts did not change.

## What this supports

Continue with deterministic admission, atomic dispatch reservations, operation-specific completion evidence and independent verification. Recovery can distinguish an unstarted operation from a completed operation with a valid journal. Persisted intent without reconcilable evidence stays unresolved: the coordinator does not infer that nothing happened.

The worker creates a proposed repair artifact. It does not modify the live fixture, weaken the original expected values or apply a real repository change. Verification is against the accepted fixture identity, not an atomic certification of a moving repository head.

## Remaining qualification

**Native Windows and Linux runs are unrun.** This session has no configured native Windows/Linux runner; the [environment probe](receipts/native-runner-probe.json) also found the local Docker daemon unavailable. The portable bundle makes the same campaign ready to carry to another machine. A Linux container run would still not qualify a Windows host or native service lifecycle.

Service startup/restart, sleep/logout behavior, containment of child processes, authenticated host decisions, MCP/A2A adapters and attachment to the current conversation are not implemented by this experiment. Recovery assumes the prior coordinator has stopped; ownership leases are not part of this fixture. Crash injection covers named process-exit boundaries, not power loss or arbitrary storage failures.

There were **zero provider calls** in this campaign. One synthetic unit is a dispatch allowance, not a measured financial cost. Model choice, documentation patch quality, total cost per verified repair and saved monitoring time still need separate evaluations.

**Next step:** run this unchanged acceptance campaign on native Windows and Linux, then qualify native process cancellation and restart behavior before adding unattended service operation. See the [walkthrough and commands](README.md).
