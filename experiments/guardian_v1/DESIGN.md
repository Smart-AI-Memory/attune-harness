# Guardian v1 — disposable end-to-end experiment

Status: experiment authorized by Patrick's `proceed` with the attached Guardian brief. This is not a production increment or an implementation of the unrelated steering-cards spec.

## Question and acceptance

Can one durable coordinator carry a real, bounded fixture check through failure detection, deterministic worker assignment, interrupted acknowledgement, independent result verification and inspection by a separate client process?

Done locally when the frozen cases below pass, raw commands/results are retained, and the original package and campaigns remain unchanged. Native Windows/Linux runs are separate evidence; portable Python source alone does not qualify them.

## Prior evidence

The earlier scratch research passed 43 coordinator checks on macOS, including transaction contention and abrupt-exit recovery; two checks were a clock simulation and local path observation. A naive retry duplicated its fixture effect. Its local routing diagnostic scored 24/36 against rules at 36/36. Those frozen artifacts remain in the thread's guardian-research directory and will not be overwritten. The local source review identifies POSIX-only process and store implementations; this experiment uses its own disposable SQLite store with DELETE journaling and FULL synchronization, keeping the existing package intact.

## Bounded design

- A standard-library script exposes init, observe, tick, recover and inspect commands. A separate process uses inspect as the host-client boundary.
- Init creates a deliberately defective arithmetic source fixture and fixed external expected values. The observer snapshots their exact bytes and admits one incident per input revision. Repeated deliveries retain one incident; conflicting reuse of a delivery identity is rejected.
- A separate process executes the fixture check. Only a structured, demonstrated assertion failure admits the fixed repair recipe. Passing checks need no worker. Missing or invalid evidence cannot become success.
- Before dispatch, SQLite atomically reserves one synthetic work unit and records intent. A fixture worker makes a candidate artifact and a correlated completion journal in its own operation directory. It is ordinary code, not a model or production agent.
- Recovery consults that action-specific journal. An absent journal leaves an uncertain dispatch unresolved. A valid journal permits independent verification without repeating the worker. The coordinator uses the frozen expected values to check the candidate; the worker's own success claim cannot accept it.
- All commands retain source/operation identities and diagnostic evidence. Relevant input changes invalidate pending work. Synthetic budget reservations remain charged across uncertain dispatches. There is no arbitrary command execution interface, provider call, remote GitHub write, scheduler installation or general authentication service.

## Frozen behavioral cases

1. Failing input, one fixture repair, independent passing verification and a separate inspect client.
2. Initially correct input: verified check, zero repair dispatches.
3. Duplicate delivery and distinct deliveries for the same incident: one worker effect.
4. Concurrent incident admission: one incident.
5. Concurrent ticks: at most one repair operation/effect.
6. Crash before dispatch intent: recovery can dispatch the still-unstarted operation once.
7. Crash after intent with no completion journal: unresolved; no automatic worker replay.
8. Crash after worker effect before parent acknowledgement: reconcile and verify; one effect.
9. Crash after acknowledgement before verification: resume verification; one effect.
10. Input changes before dispatch: stale; no repair.
11. Input changes after an effect: stale; preserve evidence and prevent acceptance for the changed input.
12. Wrong operation identity or malformed completion journal: unresolved, never verified.
13. Candidate with a wrong answer despite a claimed successful worker: independent rejection.
14. Tampered candidate or accepted oracle snapshot: no verified result.
15. Exhausted synthetic budget: no worker dispatch.
16. Duplicate observation identifier with a different input revision: explicit conflict.
17. Repeated recovery and inspection preserve the same result without another effect.
18. A workspace path with spaces and Unicode still completes; fixture source bytes use explicit LF line endings.

Save the protocol and source hashes before evaluation. Any fixes after a failed campaign get a separate run directory and freeze; retain the failed run. These are deterministic fixture cases, not independent real-world repair incidents or a model-quality evaluation.

Run 01 passed its original 19 tests. A subsequent portability review identified that default text writes would translate fixture newlines on Windows. Run 02 uses explicit UTF-8 bytes for those fixtures and adds case 18; it also retains complete source snapshots with every campaign. Run 01's original sources were copied only after confirming every byte against its pre-run hashes. This is a reviewed portability correction, not a native Windows qualification.

## Alternatives and limits

Reusing the existing coordinated-review loop would preserve more implementation but also its fixed review roles and POSIX persistence boundary, obscuring this narrow portability question. A production workflow engine such as Temporal remains a serious later alternative; this experiment does not establish equivalent durability. A file-only queue is smaller but makes concurrent admission and budget reservation harder to inspect atomically.

The fixture journal demonstrates one reconcilable effect class. It does not prove exactly-once execution for arbitrary tools, physical power-loss durability, process-tree containment, authenticated human decisions, MCP/A2A interoperability, live GitHub monitoring or current-conversation attachment. The CLI inspect client is explicitly a fixture host boundary. No human quality verdict will be fabricated by the test runner.
