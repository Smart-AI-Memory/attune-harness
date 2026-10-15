# Windows journey fixture producers

**Status: approved fixture contract.** [The command walk](README.md#walk-the-command-journeys)
consumes these artifacts. Fixtures run in disposable directories with no user
data or provider access. Write each JSON object as BOM-free UTF-8:

```python
path.write_bytes(json.dumps(value, ensure_ascii=False).encode('utf-8'))
```

Derive absolute paths from the fixture's resolved temporary directory. Do not
pass the uppercase labels in the command table literally. Commands consume
actual paths and observed response values. Preserve user-facing content exactly.

## Repair, build and testing

Reuse `failing_repository` and `starter_table` from
[test_cold_start_journey.py](../../../tests/test_cold_start_journey.py), with the
existing starter participant registry. The first creates a committed failing
addition project; the second supplies exact paths to the interpreter and offline
example registry. Seed the registry before `init` when testing the printed
next-action command; do not accidentally use `init`'s review-only default roles.
Keep `python` on the fixture PATH bound to its venv for the example command.

For the direct test journey, commit a baseline, then make one uncommitted change
inside `calc.py`; `test_scope.select` requires a change against HEAD. The repair
and build journeys can start from committed bad code; their completed replacement
then supplies the changed scope for testing. Keep every task directory outside
the checkout and new on its first command.

`init --for plan` already calls `draft_request` and build `preflight` before
writing. Its generated request has one change task and distinct worker/reviewer
assignments, `change`/`final` protected probes, nonempty intent and sufficient
budgets. Copy its output path and each actual preview checkpoint. Do not put
the generated work request inside the checkout after effects are frozen.

## File-memory reads

Use [config_for](../../../tests/test_memory_reader.py) and the frozen raw and
document format contracts as producers. The concrete host has actor/owner
`fixture`, scope `windows-fixture`, classification `internal`, and explicit
profiles. Its three roots have distinct IDs, canonical paths and tiers `raw`,
`personal`, `curated`.

Write current raw rows with unique IDs, `cwd=windows-fixture`, numeric `ts`
from the runtime clock, text containing Aurora and valid topics. Write matching
UTF-8 Markdown under personal/curated roots; source labels, when present, match
the root. Install `attune-rag==1.2.0` for the document path. Use each root's
actual ID/path to select handles; raw row versions and document sidecar versions
are different contracts. Save full returned packets for refresh.

Serving has a separate synthetic Redis adapter, connection config, active curated
membership and pointer records. A pointer's canonical absolute path and stem
must map to exactly one personal/curated root. Seed verdict sidecars under that
root. Assert its actual banner/skipped output and exit 0. No live server or
changed source authority is implied by the test adapter.

## Saved lifecycle

Use the following objects. Each named result is the parsed JSON from the
immediately preceding successful CLI operation, not a fabricated envelope.

```python
scope = {'kind': 'global'}
config = {'saved': {'root': str(fixture_root / 'Saved intent')}}
save = {
    'request_id': 'memory-save-1', 'kind': 'memory', 'scope': scope,
    'title': 'Acceptance context', 'content': 'Preserve acceptance criteria.',
    'source': {'author': 'caller', 'reference': 'Windows parity fixture'},
}

# After save; keep its original request file for later replay.
memory_id = SAVE_RESULT['record']['id']
revise = {
    'request_id': 'memory-revise-1', 'scope': scope,
    'expected_revision': SAVE_RESULT['record']['revision'],
    'changes': {'content': 'Updated acceptance criteria.'},
}

# After revise. Never take this revision from an old save replay.
forget = {
    'request_id': 'memory-forget-1', 'scope': scope,
    'expected_revision': REVISE_RESULT['record']['revision'],
}

save_task = {
    'request_id': 'task-save-1', 'kind': 'task', 'scope': scope,
    'title': 'Review acceptance', 'content': 'Inspect the Windows evidence.',
    'source': {'author': 'caller', 'reference': 'Windows parity fixture'},
    'next_action': 'Inspect the retained receipt',
    'opportunity_review': {
        'status': 'pending', 'goal': 'Assess the Windows evidence',
        'progress': 'Saved the checkpoint', 'reason': 'Deferred at session close',
        'next_action': 'Inspect the retained receipt', 'evidence': [],
    },
}

# After saving the separate task.
task_id = TASK_SAVE_RESULT['record']['id']
complete = {
    'request_id': 'task-complete-1', 'scope': scope,
    'expected_revision': TASK_SAVE_RESULT['record']['revision'],
}
```

Write `config`, `scope`, `save`, `revise`, `forget`, `save_task`, and `complete`
at the indicated stages. After forget, replaying the original save returns
historical revision 1; current `show --history` must still show withdrawn
revision 3 and three history entries. A linked-task variant uses project scope,
the actual completed owner directory and its canonical task UUID; it is a
separate record from the locally completable task above.

## Native proposal

Reuse the valid explicit envelope/policy in
[test_memory_worker.py](../../../tests/test_memory_worker.py), fixture `packet`,
and the matching host authority/jobs layout in
[test_memory_host_coverage.py](../../../tests/test_memory_host_coverage.py).
Choose a fresh caller-supplied job ID and the fixture's unsampled policy, or
provide and verify its sampled audit response too. Keep routine/stronger logical
profiles distinct. Native configuration keys exactly match those two logical
profile names; both map to existing allowed model/effort pairs and SDK pins.
The single-profile boundary fixture is not a complete host journey producer.

Create returns a run generation with no claimed jobs. Execute claims the chosen
job ID; inspect consumes that same ID. Existing explicit source facts supply the
envelope, so T7 need not wait for the file reader. Host actor/access/scopes still
validate against those facts before dispatch.

T7 must build the new child-only test seam: install real pinned SDKs, launch
through `invoke` and the Job Object, install a synthetic in-memory HTTP responder
plus fail-closed socket guards inside the trusted test wrapper, and call the
installed `helper_main`. Production bootstrap/refusal is a separate witness.
The fixture records actual runtime/argv, positive offline SDK request count and
zero live provider/model requests. It preserves production evidence fields and
never enables a fake provider in the shipped configuration.

The separately recorded live witness uses the production helper/transport,
synthetic source facts and runtime-supplied credentials. It does not use the
offline HTTP responder or dummy key. D4's shared $50 process cap and conservative
pre-dispatch reservations apply to every paid attempt; record actual usage and
keep credentials out of fixtures and receipts.
