# Coordinated evidence review

This local Phase 2 increment reviews an existing Markdown document with a selected
lead and an independent reviewer. It uses real attune-forms 0.17.0, attune-rag 1.2.0
and attune-verify 0.6.0. A completed review preserves both narratives and all native
verification findings. It does not certify arbitrary prose or dispose of disagreements.

## Run the installed example

From the Harness directory, using the prepared environment:

```sh
.venv-review-check/bin/attune-harness review-form --config examples/review/participants.json
.venv-review-check/bin/attune-harness review examples/review/request.json --config examples/review/participants.json --run-dir /tmp/attune-example-review
.venv-review-check/bin/attune-harness inspect-review /tmp/attune-example-review
```

Choose a new run directory for each execution. Existing directories are rejected,
including earlier failed runs. The sample request is explicitly accepted fixture
data and selects two deterministic participants. Each invokes retrieval and
verification, then returns a clearly labeled demonstration narrative. The sample
retention policy is fixture content, not a real policy recommendation.

To rebuild/install locally from the pinned source commits:

```sh
python3 scripts/build_local_dependencies.py
python3 -m build --wheel --no-isolation
python3 -m venv .venv-review
.venv-review/bin/python -m pip install --find-links dist/dependencies -c requirements-workflow.lock 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl[review]'
```

The dependency builder uses existing local Git objects and checks recorded wheel
hashes; see dependency-lock.json for exact build tools/commits. The installation
command may fetch ordinary packages if absent locally. No provider is invoked by
installation. The implementation receipt used offline cached packages throughout.

## Intake and participant configuration

`review-form` emits a JSON envelope containing the form definition, a keyboard
Markdown rendering, a revision and an unaccepted submission template. Fill its
seven answers, set `accepted` to true after accepting the request, and save the
submission object as request.json. Paths are relative to that request file.
The reviewed document must be inside the selected Markdown corpus and the trusted
verification context's project root. A changed registry invalidates old forms;
missing answers, unknown participant choices and the same identity in both roles
are rejected. Form acceptance supplies request data, not credentials or authority
outside this local workflow.

The registry has integer schema_version 1 and a participants mapping. Every entry
declares adapter, tools, max_turns (1–10) and max_tool_calls (0–8). Supported tools
are retrieve and verify; grants may be empty. The example config is executable as
provided. Additional profiles are:

| Adapter | Additional required configuration | Execution |
|---|---|---|
| deterministic | None | Built-in demonstration, no model judgment |
| claude / codex | model, timeout (1–300 seconds) | Existing native CLI translator; fresh invocation per turn |
| command | command (argument list), timeout | Separate process, JSON stdin and JSON stdout, no shell expansion |

Native/command selections require `--allow-external`; review the trusted registry,
model settings, commands and budgets before enabling them. They can use the host's
credentials and incur costs. There is no provider fallback. Budgets bound turns,
tool calls, output and individual process time; they are not dollar-cost limits.
The native/command process runner is POSIX-only. Configured commands are trusted
code, not isolated plugins. Native host settings can affect behavior.

An additional provider can implement the command protocol. The independent
`examples/review/json_participant.py` demonstrates it without importing Harness or
calling a model; set command to an absolute Python path plus that script's absolute
path. Arbitrary configured identity/model labels are not authenticated identities.
Live qualification of both native leads and an additional model remains pending.

## Turn and tool contract

The wire request contains schema_version 1, request_digest and turn. The turn binds
run/task, attempt, turn ID, accepted revision, participant and role; it includes
the reviewed document, initial retrieval, granted tool names, remaining budgets,
protocol instructions and only that participant's own tool history. The reviewer
does not see the lead's narrative. Native profiles encode the same response JSON
inside the native translator's outer text string.

```json
{"schema_version":1,"request_digest":"COPY_FROM_REQUEST","action":{"kind":"tool","name":"retrieve","arguments":{"query":"retention policy","k":3}}}
```

`verify` takes an empty arguments object. A final action has only kind="final" and
nonempty text. Responses must echo the current request digest and contain exactly
the documented fields; duplicate keys, stale turns, unsupported versions and
non-finite JSON are rejected. The digest is correlation, not authentication.

Tool calls cannot specify filesystem paths or grant more tools. Retrieval uses the
accepted corpus, and verification uses the accepted document/context. Results are
the existing operation envelopes with native library evidence. Document/context
changes, changed retrieved source bytes or a changed corpus version observed by
another retrieval fail the run. Other mutable verification targets retain the
underlying library's per-call evidence boundary; this is not a filesystem snapshot.
Trusted verification manifests may execute declared interpreter/help commands.

Bounds: input JSON 128 KiB; reviewed document/context 64 KiB each; each turn request
512 KiB; response 64 KiB; final narrative 32 KiB; run record 8 MiB. Existing corpus
limits remain 1000 Markdown files, 16 MiB total, 4 MiB each, and k in 1–20.
There are no automatic retries, background jobs or provider cancellation guarantees.
New runs support explicit local recovery and task-assignment transfer through the
[recovery commands](recovery-workflow.md), with one writer and conservative handling
of unknown effects. Cross-machine transfer remains unimplemented.

## Results and saved state

The CLI prints JSON and saves record.json in an exclusively created run directory.
Pending operations are saved before dispatch; results after it. Writes use a
temporary file, fsync, atomic replacement and directory fsync on POSIX. These are
local records, not signed attestations. Keep the run directory with the referenced
files; the record retains document/source references and hashes, source excerpts,
tool results and narratives, not a portable copy of the whole project.

| Outcome | CLI exit | Meaning |
|---|---|---|
| ready | 0 | Intake form rendered |
| completed + verified + retrieved | 0 | Journey finished; supported document claims passed and initial sources were found |
| completed + refuted/unknown/no_results | 1 | Journey finished with an explicit negative or incomplete evidence result |
| failed / unavailable / unresolved | 2 | Invalid request, missing capability, failed work or uncertain completion |

Participant narrative correctness is never inferred from exit 0. Both narratives
remain visible for comparing disagreements; attune-verify owns structured findings.
An interruption propagates to the caller after recording unresolved state when
possible. A persistence failure stops further dispatch. Inspection of a stored
running record reports unresolved and preserves the original file: the owner may
still be running or may have died. Inspect the owner/effects before a new attempt.
`inspect-review` works with core-only installation and never invokes a participant.
For new recovery-profile records, use the returned checkpoint_digest with the
explicit recovery commands. Phase 2 records remain inspect-only.
