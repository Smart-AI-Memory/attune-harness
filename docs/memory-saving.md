# Save memories and task intent

`attune-harness memory saved` explicitly saves a memory or task for another
session. Files are authoritative; Redis is an optional rebuildable index. Saving
a task records intent and a next action. It does not start work or claim execution
ownership.

## Configure and save

Use a dedicated absolute store directory in your configuration:

```json
{"saved":{"root":"/absolute/path/to/saved-memory"}}
```

Create a request file, for example `save.json`:

```json
{
  "request_id": "save-example-1",
  "kind": "task",
  "scope": {"kind": "project", "project": "/absolute/path/to/project"},
  "title": "Document installation",
  "content": "Explain installation from an installed wheel.",
  "source": {"author": "Patrick", "reference": "planning session"},
  "next_action": "Draft the installation steps"
}
```

Run `attune-harness memory --config config.json saved save --request save.json`.
The result includes the stable record ID, revision and `index_status`. A memory
uses `"kind":"memory"` and omits `next_action`. Scope is always explicit: use
`{"kind":"global"}` for global records. Project paths are canonicalized;
project and global results are never implicitly combined.

## Find, inspect and change

Put the exact scope object in `scope.json`. With the same `memory --config
config.json saved` prefix, use:

| Command | Effect |
| --- | --- |
| `list --scope scope.json` | List visible records in that scope |
| `search "installation" --scope scope.json` | Search authoritative saved text |
| `show RECORD_ID --scope scope.json` | Inspect a visible record |
| `show RECORD_ID --scope scope.json --history` | Include history, even after withdrawal |
| `revise RECORD_ID --request revise.json` | Apply an optimistic revision |
| `forget RECORD_ID --request change.json` | Withdraw from ordinary recall; retain history |
| `complete RECORD_ID --request change.json` | Complete an unlinked task |
| `reindex --scope scope.json` | Reconcile that scope's optional Redis index |

A revise request contains `scope`, a new `request_id`, `expected_revision`, and
`changes`, for example `{"next_action":"Review the draft"}`. Forget and complete
use the same envelope without `changes`. Status is changed only by its explicit
operation. Revision conflicts refuse a stale update.

Reuse a request ID only to retry the identical operation. Retained replay evidence
returns its original result, even if a later revision exists; a changed operation
with the same ID is refused. Records, revision history and retry identities commit
in one atomic file replacement under a bounded writer lock. An `uncertain` outcome
means the replacement may have committed: inspect the record or retry the same
request, rather than inventing a new request ID.

## Reference Harness execution

A project task may include
`"execution":{"directory":"/absolute/path/to/harness-task","task_id":"TASK_ID"}`.
Inspection reads existing Harness execution state and checks its identity and
project. Missing, corrupt or mismatched execution is reported as unavailable.
This read never dispatches work, creates execution state or interprets missing
evidence as completion. Linked tasks cannot be locally completed: Harness owns
execution status. Global tasks cannot link execution because they have no project
binding.

## Optional Redis index

Add `"redis":{"url_env":"SAVED_REDIS_URL","namespace":"personal"}` inside
`saved`, and provide the connection URL through that environment variable. The
adapter loads Redis lazily and uses a dedicated `attune:harness:saved:v1:` keyspace
with hashed scope and record identities. Connection and read waits are bounded; URL query options are refused because
they can override those bounds.

`index_status` is `disabled`, `indexed`, or `pending`. An unavailable dependency,
missing connection setting or index failure leaves an already committed save
readable and reports pending work. Reindex retries current records and withdrawn
record removals. Reads use files, so stale Redis entries cannot resurrect a
withdrawn record. This feature has injected adapter tests; no live Redis service
qualification is claimed.

## Storage limits and supported profile

The initial storage profile is local POSIX filesystems with advisory locks and
atomic replacement. Windows refuses before creating the store; this is not a
Windows storage qualification. Native Windows support remains an open release
requirement, including concurrent writes, crash/retry recovery and safe path
handling. WSL has not been qualified as an alternative. A store is private to its configured root. Do not
manually edit its versioned state or lock files. Unsafe symlink/hardlink targets,
malformed state and unsupported versions are refused.

Limits are UTF-8 bytes: title 1 KiB, content 64 KiB, each source field 2 KiB,
next action 8 KiB, request 128 KiB, total state 8 MiB. Lock acquisition waits at
most two seconds. History and retry evidence count toward the state limit;
withdrawal retains them and is not erasure. No automatic extraction, scheduling,
background hooks or migration of existing memories is performed.
