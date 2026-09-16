# Task 4 software receipt

Primary status/resume read the accepted task record; callers can provide an optional checkpoint. Advanced reconcile-task, transfer-task and cancel-task share record-level controls with legacy recovery. All legacy argument/exit contracts remain. Shared continuation preserves Voyage paid-stage replay and never silently repeats uncertain calls.

Observed: 354 focused tests passed, including 19 new recovery cases. They pause at every solo/team operation boundary and check retained event identities, no duplicate calls, lost acknowledgement, explicit correlated recovery, bounded read-only retry, foreign replies, transfer timing/identity/context, terminal cancellation, copy/stale/source/busy ownership checks and primary CLI controls. Raw receipt: docs/receipts/unified-task-execution/task4-final.xml.

Three original Task 1 v2 checkpoints were loaded from their original paths. Completed replay returned unchanged; paused execution completed through the new runtime with a capture-only persistence adapter; unknown external effects refused resume. Original record bytes, accepted digests and completed operation keys were unchanged. Raw receipt: task4-frozen-replay.json. The initial probe used a wrong baseline directory and installed interpreter imports; it failed, then the verified probe explicitly selected the frozen v2 directory and checkout source.

Broader Task 3 A2A retry remained unqualified on this host: 33 fixture startup timeouts, 5 passing cases after sandbox escalation (task3-local-peers.xml). This is not a green A2A qualification. The original full suite's seven historical artifact-identity errors remain visible; no preserved environment/campaign was rewritten. Current task/legacy focused qualification is green. No live provider was invoked.
