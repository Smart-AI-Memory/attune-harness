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

## Plugins: signing, revocation and the capability fields

A bundle whose manifest carries `grants` or `declares` is a plugin (the
[executable plugins spec](specs/executable-plugins/README.md), approved as
[D22](specs/spec-authority/addendum-2026-09-23.md); plan task 4.3, first of
four cycles). No plugin code runs yet: the `run` binding is a later cycle,
and a plugin's tools are still `retrieve` bindings. What this cycle adds is
the trust boundary those tools already run behind: a signature the accepted
registry can check, a revocation list, and the two fields whose names carry
the difference between what the host enforces and what it only records. A
data-only bundle, one with neither field, is unchanged: it needs no
signature and no registry to enable, and its receipts are what they were.

### The manifest's two fields

`grants` names what the host will do for the plugin. Each is a host action,
so each is enforced. Version 1 knows five: `secrets` (up to eight
environment variable names the host will pass, and nothing else from the
environment), `paths` (up to eight lowercase names of the task's inputs the
host will name in the request), `scratch` (`true` for a plugin-private
writable directory), `time` (a timeout, an integer of at most 300 seconds)
and `output` (an object with `result`, at most 1048576 bytes, and
`diagnostics`, at most 65536 bytes). `declares` names what the child could
violate, so each is recorded and attested, not enforced. Version 1 knows
six: `imports` (distributions installed in the host's environment the bundle
will import, an extra in brackets), `network` (lowercase host names),
`reads` and `writes` (paths outside what it was given, expected empty),
`subprocess` (`true` or `false`) and `vendored` (the distributions the
bundle carries itself). Any other name in either field is refused as
manifest schema version 2 material, in those words. Both fields are manifest
bytes, so they are bound into the artifact digest like everything else.

```json
{
  "schema_version": 1,
  "id": "evidence",
  "version": "0.1.0",
  "skill": "SKILL.md",
  "tools": {"search": "retrieve"},
  "grants": {"secrets": ["VOYAGE_API_KEY"], "scratch": true, "time": 120,
             "output": {"result": 65536, "diagnostics": 8192}},
  "declares": {"imports": ["voyageai"], "network": ["api.voyageai.com"],
               "reads": [], "writes": [], "subprocess": false, "vendored": []}
}
```

### What is signed, and with what

The signed bytes are the artifact digest's 64 lowercase hexadecimal
characters, ASCII, with no newline: exactly the `artifact_digest` that
`extension discover` prints. The signature is a detached OpenPGP signature
over those bytes, armoured or binary, in the file `artifact.sig` beside the
manifest, at most 16 KiB and never a symlink. The signature file is not part
of the digest, so signing does not change what is signed. A signature means
one thing: this exact bundle, manifest and skill, was reviewed by the signer
under [the brief](review-brief.md). It does not mean the bundle is safe in
general, and every receipt words it that way.

A maintainer signs with an ordinary `gpg` key. The example below uses a
scratch key in a temporary home so that it touches no real keyring; the
maintainer's own key is the first entry of a real registry's `signers`:

```sh
export GNUPGHOME=$(mktemp -d) && chmod 700 "$GNUPGHOME"
gpg --batch --passphrase '' --pinentry-mode loopback \
    --quick-generate-key 'Scratch <scratch@example.invalid>' default default never
DIGEST=$(attune-harness extension discover bundle/extension.json \
         | python3 -c 'import json, sys; print(json.load(sys.stdin)["bundle"]["artifact_digest"])')
printf '%s' "$DIGEST" | gpg --armor --detach-sign > bundle/artifact.sig
gpg --armor --export > signer.asc                                   # the public key block
gpg --with-colons --fingerprint | awk -F: '/^fpr/ {print $10; exit}'  # its fingerprint
```

`printf '%s'` matters: a trailing newline is a different set of bytes, and a
signature over it is refused as a changed artifact.

### What the registry carries

Two keys of the `extensions` section are not registrations: `signers`, a
list of one to eight entries, each a key's 40-character uppercase
fingerprint and its ASCII-armoured public key block, and `revoked`, a list
of up to 64 artifact digests that never run again whatever their signature
says. Both are validated without opening any bundle, and no extension can be
registered under either name. A registration may carry `grant`, the subset
of the manifest's `grants` this registry allows: the effective set is the
grant, never the declaration, a registration without one grants nothing,
and `declares` cannot be granted, only acknowledged, which registering the
bundle does.

```json
"extensions": {
  "signers": [{"fingerprint": "<40 uppercase hexadecimal characters>",
               "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...\n-----END PGP PUBLIC KEY BLOCK-----\n"}],
  "revoked": [],
  "evidence": {
    "state_dir": "extension-state",
    "artifact_digest": "<digest returned by extension install>",
    "grant": {"secrets": ["VOYAGE_API_KEY"], "time": 60}
  }
}
```

The registry is also the key distribution: an accepted, checkpointed
artifact whose every change is a receipt. A key rotates by a registry edit
that lists the old and the new key together for an overlap and then drops
the old one; the receipts of those edits are the audit trail. A signed
bundle that turns out to be wrong goes on `revoked` by its digest.

### Where the checks run

A plugin enables only against the accepted registry: `extension enable`
takes `--registry`, refuses a plugin without it, and refuses a registry that
does not register this state directory with this artifact digest. Inside
the lease, at `enable` and before and after every call, where the host
already re-reads the manifest to compare the artifact digest with the
checkpoint it holds in memory, it also checks that the digest is not on
`revoked`, that `artifact.sig` verifies over that digest by a listed key,
and that the grant is a subset of the manifest's `grants`; a change in
between, a signature withdrawn during a call included, discards the result.
The revocation list applies to any registered bundle, data-only or not.
Verification is `gpg --verify` in a bounded subprocess with `--status-fd`,
in a private home directory created with mode 0700 for the call and removed
after it, holding a keyring built from the registry's key blocks and nothing
else; the user's own keyring, options and agent play no part, and
`GNUPGHOME` is not passed. The verdict is read from the status lines alone,
a `GOODSIG` and a `VALIDSIG` whose primary-key fingerprint is listed and no
expiry, revocation, bad, error or no-data line, never from the exit status,
which gpg sets to 0 for a signature by an expired or a revoked key. The
same function will run before the `run` binding's child starts.

### The receipts

The enable receipt, and the `extension` block of every contributed call,
gain `plugin`: `signer`, the fingerprint that vouched; `grant`, the
effective grant; `declares`, the acknowledged declarations exactly as the
manifest states them; `signature_scope`, which says that the signature means
this exact bundle was reviewed by the signer under the brief and not that it
is safe in general; and `declarations_scope`, which says the declarations
were recorded and not enforced. Disabling drops `plugin` from the state,
since it ends the grant. The envelope is pinned as `extension-enable-plugin`
in [the envelope table](envelopes.md).

### What each refusal means

Each is unavailable (exit 2 from the command line), worded as what happened
and what to do next. The existing refusals come first and are unchanged: an
artifact that differs from the accepted binding or from the state is refused
in the words above before any signature is checked.

- *Plugin bundles enable only against the accepted registry; pass --registry ...*: a plugin was enabled without `--registry`.
- *Plugin ID is not registered in that registry ...* and *Registry registers plugin ID under a different state directory ...*: the registry passed does not bind this state directory.
- *Plugin bundle carries no signature ...*: no `artifact.sig` beside the manifest.
- *Plugin artifact.sig is not a detached signature ...*: gpg found no OpenPGP data in the file (`NODATA`).
- *Plugin artifact changed after it was signed ...*: the signature does not verify over the current digest (`BADSIG`); the manifest or the skill changed after signing, or other bytes were signed.
- *Plugin signature was made by a key the registry does not list ...*: the signature verified, but the key's primary fingerprint is not under `signers`.
- *Plugin signature names a key with no public key in the registry ...*: the signing key's block is not under `signers` (`NO_PUBKEY`).
- *Plugin signature was made by a key that has expired ...* and *... that has been revoked ...*: `EXPKEYSIG` and `REVKEYSIG`, which gpg reports with exit status 0; this is why the exit status is never the verdict.
- *Plugin signature has expired ...* and *Plugin signature could not be checked by gpg ...*: `EXPSIG`, and an `ERRSIG` that is not a missing key.
- *Plugin artifact is on the registry revocation list and never runs again ...*: the digest is under `revoked`.
- *gpg is absent from PATH ...*: no verifier on this machine; install GnuPG. The platform jobs run the plugin tests, so a runner without gpg fails them by name rather than skipping.
- *Plugin signature verifier failed to run (...)* and *... reported no verdict ...*: the subprocess did not run, or ran and produced no `GOODSIG` with a `VALIDSIG`; a silent exit 0 is a refusal.
- *Plugin signature verifier could not import a registry key block ...*: a `public_key` entry gpg cannot read.
- *Grant names NAME, a capability the plugin manifest does not declare ...* and *Grant of NAME exceeds what the plugin manifest declares ...*: the registration's grant is not a subset of `grants`.

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
