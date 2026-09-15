# Local extension workflow

The supported profile is a data-only bundle mapping namespaced tools to Harness's
existing attune-rag retrieval adapter. A bundle supplies one portable `SKILL.md`;
its text enters only participants' granted tool contracts. No bundle code is
imported. There is no plugin marketplace, automatic host installation or general
Python plugin execution in this profile.

## Reproduce the installed example

From the Harness checkout, use the review environment prepared by the
[local workflow](local-workflow.md). Its pinned feature dependencies remain unchanged:

```sh
SOURCE_DATE_EPOCH=1789344000 python3 -m build --no-isolation --wheel
SOURCE_DATE_EPOCH=1789344000 python3 -m build --no-isolation --wheel --outdir dist/dependencies examples/extensions/plugin
.venv-review-check/bin/python -m pip install --no-index --no-deps --force-reinstall dist/attune_harness-0.1.0.dev0-py3-none-any.whl dist/dependencies/attune_harness_evidence_example-0.1.0-py3-none-any.whl
.venv-review-check/bin/python -I examples/extensions/run_review.py --work-dir /tmp/my-new-extension-review
```

The last command requires a **new** output directory. It explicitly registers
the installed example bundle, enables retrieval, creates an accepted deterministic
fixture request through attune-forms and runs two participants. It writes the
request, registry, state, full review record and summary. No provider calls occur.
These commands install only the two newly built wheels; they require the
previously prepared review dependencies. No index/network access is used.

The retained [example summary](../examples/extensions/qualified-example/summary.json)
and [run record](../examples/extensions/qualified-example/run/record.json) were
produced by this installed script. Inspection of completed historical evidence
works even after an extension is disabled; it makes no claim of current availability.

## Bundle and registration contracts

The separately packaged example contains:

```json
{
  "schema_version": 1,
  "id": "evidence",
  "version": "0.1.0",
  "skill": "SKILL.md",
  "tools": {"search": "retrieve"}
}
```

Discovery accepts an explicit manifest path, never scans/imports entry points.
The manifest is bounded to 16 KiB, the skill to 16 KiB, declarations to four tools,
and a registry to eight extensions. IDs/local tool names are lowercase identifiers
of at most 24 characters. Duplicate JSON keys, reserved IDs, unsupported fields,
future versions, skill traversal and symlink files fail. Artifact identity binds
exact UTF-8 manifest and skill bytes, including whitespace. Bundle version labels
alone cannot preserve evidence after a content change.

A participant registry may add:

```json
"extensions": {
  "evidence": {
    "state_dir": "extension-state",
    "artifact_digest": "<digest returned by extension install>"
  }
}
```

State paths resolve relative to the registry. The registered ID must match the
manifest ID. Grant `evidence.search` in selected participants' `tools`; undeclared
or ungranted names fail before invocation. Generate a fresh `review-form` after
changing bindings. The call accepts **only** `query` and integer `k` (1–20).
The accepted corpus belongs to the coordinator, and existing tool/turn budgets
apply. This contribution uses the same real retrieval adapter through deterministic,
Claude/Codex injected-transport, or independent command participants. These are
local integration receipts, not live model qualification.

## Lifecycle commands

```sh
attune-harness extension discover path/to/extension.json
attune-harness extension install path/to/extension.json --state-dir new-state
attune-harness extension inspect --state-dir new-state
attune-harness extension enable --state-dir new-state --checkpoint STATE_DIGEST
attune-harness extension disable --state-dir new-state --checkpoint STATE_DIGEST
attune-harness extension replace --state-dir new-state --checkpoint STATE_DIGEST --manifest path/to/updated/extension.json
attune-harness extension remove --state-dir new-state --checkpoint STATE_DIGEST
```

Use the latest `state_digest` from inspection or the previous successful mutation;
`STATE_DIGEST` is a placeholder. Each mutation increments the revision. Lifecycle
success returns exit 0 even for disabled/removed states; failed/unavailable returns 2.

Install creates a disabled registration. Enable checks the artifact and exact
attune-rag dependency version. Replace requires a disabled registration, keeps its
ID, changes its artifact binding and leaves it disabled. Old accepted review
requests cannot resume against a different artifact; accept a new request.
A byte-identical replacement preserves artifact identity, but still changes the
lifecycle state revision. Removal leaves a tombstone and preserves bundle files
and user data. Package uninstallation is separate and is never performed here.
Missing/broken bundles remain inspectable and can still be disabled or removed.

Each contributed call holds a process lease until retrieval returns. A simultaneous
disable, replace or removal reports **busy**, with no successful state change;
retry explicitly after the call settles. The OS releases leases on process death.
Review recovery still governs interrupted calls. A disabled registration prevents
new contributed tool invocations. Paused runs require re-enabling the exact
accepted artifact; new participant turns and final completion also check lifecycle
state. Cancellation does not undo an earlier call.

Lifecycle state uses the existing atomic store, POSIX locks and local trust model.
These are cooperating-process guarantees, not authentication or a sandbox against
a local process rewriting files. An interrupted in-flight review may remain
unresolved; no automatic retry or exactly-once guarantee is added. Read-only
artifact checks detect observed changes, not every transient external filesystem
mutation. Copied state/run directories are not a cross-machine transfer protocol.

## Evidence and Attune integration limits

A successful tool result retains native retrieval status, sources and corpus
version, plus extension ID, tool name, bundle version, artifact digest and dependency
pin. The evidence describes that invocation. A listing or successful activation
never claims verified availability. `no_results` stays distinct from retrieved
sources; retrieved evidence does not verify arbitrary participant prose.

Extension-enabled recovery records add integer `extensions: 1` to the existing
engine profile. Older engines reject that profile; previous unextended records
retain their existing profile and remain resumable in this engine.

The [explicit BasePlugin bridge](../examples/extensions/attune_bridge.py) subclasses
the public Attune interface and forwards scoped search to the same tool boundary.
Its installed receipt characterizes metadata, initialization, activation, retrieval
and disabled refusal against attune-ai 16.4.0. It does not auto-register with Attune,
write private MCP handler tables, or install host skills. The portable plugin
wheel contains only the manifest/skill package data and no mandatory dependencies.
MCP protocol qualification, A2A peer exchange, executable extension code, Windows
lifecycle and E2's full comparison remain outstanding.
