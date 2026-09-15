# Local extension increment — design before implementation

2026-09-14. Mode: execute the agreed Harness plan, bounded Phase 4 increment.
Outcome: an explicitly selected portable bundle contributes a skill and real
retrieval tool to the existing review loop. Done when installed CLI receipts
cover lifecycle, content/version changes, paused work, both injected native
leads and an independent command participant, with no provider calls.

## Existing seams and disposable experiment

Baseline: 319 tests passed. Read-only Attune source at local/cached-origin SHA
`fe08f282fb0ad9cbb7eedf75af2597336576578e` retains public `BasePlugin`
metadata/initialize/CLI hooks. `PluginRegistry` removed installed-entry-point
discovery in 16.0.0; it directly discovers two built-ins. The disposable
`/tmp/harness-extension-seam-probe.py` instantiated two public BasePlugin
subclasses in installed attune-ai 16.4.0: registration silently replaced the
first under a duplicate name; no deactivate hook or remove API exists.
Redis's `register_mcp_tools` writes `server.tools` and private
`server._plugin_handlers`. We will not make the portable core depend on those
private tables. Skill files are host packaging/content: no public general
SKILL.md loader was found in `src/attune`; meta-workflow CLI writes host files.
This is a bounded inventory, not proof that no other integration exists.

## Chosen boundary and cases

A strict JSON bundle manifest declares contract version 1, id, version, one
skill file and namespaced retrieval bindings. Bundle identity hashes the exact
manifest and skill bytes; file paths must stay inside the bundle. Discovery
reads only explicitly selected manifests, never imports plugin code. A thin
example BasePlugin bridge adapts public metadata/activation hooks separately from the
portable package. Existing attune-rag remains the implementation owner.

Use the existing atomic RunStore and process lease for extension state, with
strict operation/type validation. Install starts disabled. Enable checks the
artifact and pinned dependency. Disable/removal preserve state, bundle files
and user data; removal is a tombstone, not a package uninstaller. Changes use
an expected state digest to reject stale writes. Invocation holds the extension
lease until the real read-only retrieval finishes; concurrent lifecycle
mutation returns busy and must be explicitly retried. No promise to kill an
active call. A crashed owner releases the OS lease; its review remains subject
to existing unresolved-operation handling.

The accepted review registry optionally binds extension id, state directory,
and artifact digest. Namespaced tool grants and skill content become participant
context; they grant no new authority. Check enabled/current artifacts before
new participant turns and inside each tool invocation. Cached completed events
can be inspected; resume requires the exact accepted artifact and currently
enabled registration. Upgrades require explicit replacement while disabled,
start disabled, and invalidate old accepted forms/requests. Existing registries
and recovery profiles retain their wire shape; extension-enabled records carry
a separate contract marker so older engines reject them.

Cases: malformed/future manifests; duplicate/reserved names; symlinks/traversal;
missing dependency/artifact; stale mutation; disabled/removed registrations;
upgrade including same-version changed bytes; unauthorized tool/path arguments;
active invocation vs disable; interrupted/paused review; removal after a call;
real retrieved/no-results distinction; native injected and independent command
feature calls; source-only vs installed package behavior. Qualification is an
observation bound to artifact, engine, corpus and call, never inferred from a
registry listing. E2's full comparison remains a separate experiment.

## Rejected alternatives / outstanding work

- Reuse PluginRegistry for lifecycle: its replacement semantics and missing
  disable/remove operations cannot enforce this contract without changing the
  owning product. Keep the portable state boundary small and explicit.
- Load arbitrary Python entry points: unnecessary authority and dependency
  surface for the first contribution. This profile permits data-only bundles
  mapped to an existing known retrieval operation; custom code is unsupported.
- Copy host skill loaders or install global plugins: violates ownership and
  obscures the artifact used. Explicit bundle selection is reproducible.
- Silently stop active calls on disable: cannot establish whether an effect
  happened. Finish the leased read-only call or report busy/unresolved.

MCP/A2A are outstanding. The inspected installed MCP SDK is 1.29.1, advertising
2025-11-25. Its legacy initialize/initialized lifecycle must be qualified against
that supported revision, not described as newest; newer revisions exist.
See the [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
and [2026-07-28 changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx).
A2A requires an independent peer and actual task/artifact/cancellation receipts,
not just a schema match; consult its [specification](https://a2a-protocol.org/latest/specification/).
No credentials or live-model spending are part of this increment.

Implementation refinement: no caller of `get_cli_commands` was found in the
inspected Attune source. The explicit bridge therefore characterizes public
metadata/initialize/activation and an explicit scoped search method; it makes
no claim of automatic CLI registration or host MCP interoperability.

## Process cleanup defect found during qualification (before its fix)

Full-suite runs intermittently raised `PermissionError` from `os.killpg` while
output-limit fixtures exited rapidly, both within and outside the execution
sandbox. This is not treated as a sandbox-only limitation. A disposable 100-child
probe reproduced six denials; immediate `poll()` returned None and immediate
re-signalling was still denied. A second disposable 100-child probe waited at
most 100 ms to reap the parent before rechecking its group. Twelve initial denials
all ended with return code 0 and `ProcessLookupError` (group gone); no retry failed.
Raw evidence: `receipts/extensions-cleanup-probe.json`.

Fix only this cleanup boundary: after initial permission denial, allow up to
100 ms for the owned parent to exit, then try group cleanup once more. An alive
parent after the grace period preserves the original permission error. A second
permission denial also propagates, so inaccessible descendants never become a
success claim. Keep existing output-limit/cancellation status. Cases: quick exit,
alive denied process, second denial, and descendants after parent exit. Reject
unbounded waiting, swallowing EPERM, and assuming a reaped parent has no children.
