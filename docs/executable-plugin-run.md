# Running a signed Python plugin

The `run` binding is the second executable-plugin implementation cycle. It uses
signing, accepted grants and a bounded subprocess. **It is not a security sandbox.**
Network-declaring run plugins refuse until the host-owned paid-stage journal is
integrated. The README's platform qualification claim is unchanged.

A tool declaration beside an existing `retrieve` declaration can be:

```json
{
  "binding": "run",
  "entry": "main",
  "input_schema": {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
    "additionalProperties": false
  },
  "output_schema": {"type": "object"}
}
```

The manifest adds `code: "plugin.zip"`, a relative ZIP archive containing
`main.py` (or the package named by `entry`). The manifest, skill and archive hashes
form the signed artifact digest. Both the archive and its expanded contents are
limited to 4 MiB. Archive traversal, duplicate members, symlinks and encrypted
members refuse before installation.

Declare capabilities in the existing `grants` and `declares` fields. A run needs
explicit effective `scratch: true`, `time` and `output` grants. The accepted
registry's grant remains a subset of the manifest's grant. `paths` names accepted
host inputs such as `document` or `corpus`; the caller supplies arguments, not
replacement paths. `secrets` names only the environment values explicitly passed.
The host records environment keys and diagnostics digests/lengths, not their
values. Plugin-returned result data may itself contain sensitive content.

At enable, Harness resolves `declares.imports` from installed distribution
metadata, including transitive requirements, environment markers and explicitly
selected extras. No package is downloaded. Missing metadata, unsatisfied versions
or dependency-pin conflicts refuse. The resolved versions, module mappings and
files are checkpointed; changed resolution refuses calls until an explicit
re-enable. `packaging==26.3` is a base dependency for this resolution.

The child runs the host Python with `-I -S -B`, using the standard library, a
private copy of the signed ZIP and the declared distribution closure. A finder
exposes only files belonging to that closure. This guards cooperating code;
malicious code can remove the finder or access the user's machine directly.
Operating-system startup environment additions are removed before plugin entry.

Installed wheel `METADATA` is also snapshotted for the selected distributions,
with a combined 1 MiB UTF-8 limit. The child can discover their versions, metadata
fields and declared requirements through `importlib.metadata`; undeclared or
bundle-local distribution metadata is not discovered. Metadata changes require
re-enabling the plugin, just like import-closure drift. The snapshot does not expose
metadata directories, arbitrary files, entry points or distribution file-location
APIs, and does not add site-packages to the child's search path. Voyage's SDK uses
this version discovery when importing its compiled dependency closure; network
execution still requires the separately planned host-owned journal integration.

The plugin reads the UTF-8 JSON request at `sys.argv[1]` and writes its UTF-8 JSON
result to `sys.argv[2]`. The request contains `arguments`, granted `paths`, and
`scratch`. Standard output/error are bounded diagnostics, never the result or an
MCP protocol stream. The host validates arguments and result using the declared
schemas. Schemas allow bounded local object/array/scalar constraints; references,
regular expressions and remote schemas are not supported.

MCP and review participants invoke the tool by its existing
`<extension>.<tool>` grant. Successful responses wrap the plugin value in
`plugin_result` beside an explicit `untrusted_data` marker and the host receipt.
The receipt binds the bootstrap/configuration/request, effective grants,
declarations, imported versions, environment keys, process status/duration and
result digest. Returned data does not authorize another operation.
Per-call `imports` contains `versions` and `closure_digest`; full file lists and
metadata text stay in accepted extension state and the bootstrap configuration,
so repeated calls do not duplicate large snapshots in the enclosing run record.

Host authority files and extension state are compared against in-memory
checkpoints after execution. Signature/grant/artifact checks run again. A changed
record, invalid result or subprocess failure discards the result and retains an
unresolved receipt. MCP stops subsequent dispatch; review recovery retains an
unknown-effects operation instead of replaying it as a read-only retrieval.
