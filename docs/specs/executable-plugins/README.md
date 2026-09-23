# Executable plugins: the spec

Draft of September 23, 2026, revised the same night after its first
different-model review, for [the plan's 3.5](../../plan-1.0.md). D6 ruled
executable plugins "need it", required for stable, with their own spec, a
threat model, and sandboxing or signing before implementation. D7 made
Voyage the first real consumer. D20.7 ruled the shape: signing plus a
capability list plus a subprocess, stated as such and not as a sandbox claim.
This document is reviewed as `src/` is, by a different model under
[the brief](../../review-brief.md), before Patrick approves it; the
implementation is Phase 4's 4.3. Nothing here authorizes code.

## What exists: the data-only extension system

Everything a plugin will need to fit is already in `src/attune_harness/`:

- **A manifest and a skill, and nothing executed.** `extensions.discover`
  reads one selected manifest: exactly the fields `schema_version` (1),
  `id` (lowercase, at most 24 characters, not `retrieve` or `verify`),
  `version` (`major.minor.patch`), `skill` (a relative `SKILL.md` inside the
  bundle, no symlink, at most 16 KiB) and `tools` (one to four declarations),
  and every declaration's binding must be `retrieve`, else "Extension
  contract 1 only supports the retrieve binding". The module docstring says
  it "never imports bundle code" and, in its last sentence, "State hashes
  are not authentication."
- **An artifact digest checked before and after every call.** SHA-256 over
  the canonical JSON of the manifest's and the skill's SHA-256, bound at
  install, compared on `enable`, in `catalog`, and in `invoke_tool` before
  the call and again after it returns. Two refusals: "Accepted extension
  artifact changed; update the binding and accept a new request" when the
  state disagrees with the registry's accepted binding, and "Extension
  bundle changed; disable and explicitly replace it" when the bundle on disk
  disagrees with the state.
- **A leased lifecycle.** `install` (disabled, no checkpoint yet), then
  `enable`, `disable`, `replace` (disabled only, same identity) and `remove`
  (a tombstone), each of those under the run store's writer lock against a
  `state_digest` checkpoint; `invoke_tool` holds the lease across the whole
  call, so a concurrent `disable` reports busy.
- **Grants through the accepted registry.** One to eight registrations,
  each a `state_dir` and an `artifact_digest`, validated without opening the
  bundle; a participant may be granted only `retrieve`, `verify` or a
  catalogued `<extension>.<tool>`, with `max_tool_calls` in 0..8, and the
  MCP server refuses a call past that budget with no reset.
- **A bounded subprocess primitive.** `process.invoke`: no shell, a
  positive finite timeout, an output cap, a process group on POSIX and a Job
  Object on Windows, descendants killed on teardown, and the docstring "Not
  a security sandbox." When a caller passes an environment it replaces the
  inherited one entirely; with none passed the child inherits everything,
  which is how the model CLIs authenticate. Three callers pass one: `test`
  passes six keys, `fix`'s probe requires a frozen minimal environment (on
  Windows with one `SystemRoot` and no casefold aliases), and the native
  memory helper, POSIX-only, passes five keys and refuses ambient provider
  overrides. That helper is launched with `-I -B -c` and a code string that
  inserts its package on `sys.path`, because `-I` ignores `PYTHONPATH`.
- **Protocol hygiene.** The MCP server declares every tool read-only,
  non-destructive and non-idempotent, sets `open_world_hint` only when the
  registry has a Voyage retrieval section, validates arguments against a
  fixed schema and results against an output schema, records every call
  with an effect class before dispatch, and tells the model that source and
  skill content is untrusted data.
- **What does not exist.** No signature, key or trust root anywhere in
  `src/`; nothing in CI verifies a signature or a tag (the maintainer signs
  release tags and verifies them by hand with `git tag -v` on his machine);
  no per-actor capability list; no threat-model text. The README's isolation
  row says "This is not a security sandbox", its receipts row says receipts
  "are local values, not signed attestations", and its protocols row lists
  "arbitrary executable plugins" among what is unqualified.

## Terms

A **bundle** is a directory with a manifest, a skill, and now code. A
**plugin** is a bundle whose manifest declares an entry to execute. The
**host** is Harness, in the process that holds the run store's lease. The
**principal** is the launcher-selected participant, as the MCP server has
it. A **capability** is one named thing the host will do for the plugin. A
**grant** is the subset of a plugin's declared capabilities the accepted
registry allows. A **signer** is a key the accepted registry lists. The
**checkpoint** of a call is the state the host read into memory before the
child started.

## Threat model

**Assets.** The dedicated checkout the user trusts; the task and run
records, which are the authority for decisions and acceptance; receipts;
secrets in the environment (`VOYAGE_API_KEY`, `ANTHROPIC_API_KEY`, anything
the shell carries); the network, because a call can cost money or leak
data; the protocol streams, JSON on stdout and MCP stdio, which a stray
print corrupts; and the user's machine beyond the checkout.

**Threats considered, and what the design does about each.** Every row
says which of the two things it is: something the host enforces because it
is the host's own action, or something recorded and attested that the child
could violate.

| # | Threat | Response |
|---|---|---|
| T1 | The code that runs is not the code that was reviewed: a bundle replaced or edited on disk, before or during a call | Enforced. The artifact digest already covers the manifest and the skill and is checked before and after every call; it now covers the code archive too, and a signature over that digest by a listed signer is required to enable and to run. The check runs against the checkpoint the host holds in memory, not against a digest read back from disk |
| T2 | A plugin reads or writes outside what it was given | Recorded. The host passes paths and never discovers them for the plugin, and the working directory is plugin-private; but the child is the same user with no sandbox, so a read or a write elsewhere is not prevented. It is declared, recorded, and detectable only where the host already compares digests |
| T3 | Secrets or data leave over the network without the user knowing | Enforced in part: secrets reach the child only by name, from the grant, and the child's `sys.path` is the standard library and the bundle, so a network client the bundle did not vendor is not importable. Recorded for the rest: network use is declared per host name, acknowledged in the grant, attested by the signer, and not blocked; a bundle that vendors a client can reach anything |
| T4 | Runs forever, floods output, or leaves children behind | Enforced. `process.invoke`'s timeout, output cap, process group or Job Object, and descendant teardown, as for every other subprocess |
| T5 | Forges evidence: writes the run record, the task record, the event file, or a receipt | Recorded and detected. Those paths are never passed and the host holds the writer lease for the call's duration. A record's self-digest proves nothing against a writer who recomputes it; what detects a rewrite is the host comparing the record on disk after the call with the checkpoint it read before, which is what `mutate` already requires of its callers. A mismatch discards the result and records the call as `unresolved` |
| T6 | Corrupts a protocol stream | Enforced. The plugin's stdout and stderr are captured diagnostics, never a protocol; the result is a file; the host's stdout stays the host's |
| T7 | Plugin-produced text is taken as instructions by a model | Enforced on the host's paths. Every string a plugin returns is wrapped as untrusted data the way retrieved content and `SKILL.md` text already are, on every path that reaches a model |
| T8 | Over-grant: a manifest asks for more than the user meant to give, or a grant drifts from a manifest | Enforced. The effective set is the grant, never the declaration; a grant that names a capability the manifest does not declare is refused inside the lease, at `enable` and before every call, where the host opens the bundle's manifest; both the declaration and the grant are in the receipt |
| T9 | Replay and staleness: a call against a bundle whose signature, signer or grant has since been withdrawn | Enforced. The signer list, the revocation list and the grant are read from the accepted registry inside the lease, before and after the call, as the artifact digest is now |
| T10 | A hostile or compromised same-user process | Out of scope, as it is for the rest of Harness: cooperating-process guarantees, not a sandbox against a local process rewriting files |

**What this model does not defend.** Kernel or OS isolation; a malicious
host; a plugin's own code doing what any process of that user can do,
including reaching the network with a client it vendored or the file system
beyond what it was given. The boundary is what the host hands over
(credentials, paths, arguments, time, output, the lease, the import path)
and what the signer vouched for. The README's row stays as written: this is
not a security sandbox.

## Trust model

**Signing.** A bundle carries a detached signature over its artifact digest,
made with a key the accepted registry lists under `signers`, each entry the
key's fingerprint and its public key block, so the registry is also the key
distribution: an accepted, checkpointed artifact whose every change is a
receipt. Verification is `gpg --verify` in a bounded subprocess against a
keyring the host builds from those blocks and nothing else, so the user's
own keyring plays no part. The maintainer already signs release tags with
GPG; nothing verifies them in CI today, and this spec adds the first
verification, so the CI runners' `gpg` and a user's are both assumptions
the implementation must prove on all three platforms. An absent `gpg`, a
verifier that fails to run, an expired or revoked key (`EXPKEYSIG`,
`REVKEYSIG`, which `gpg` can report with exit status 0) and "no public key"
are each a refusal, worded as what happened, never a pass. A signature means
one thing: this exact bundle, code and manifest and skill, was reviewed by
the signer under the brief. It does not mean the bundle is safe in general,
and the receipt words it that way.

**Revocation and rotation.** The registry carries `revoked`, a list of
artifact digests that never run again whatever their signature says, for
the case where a signed bundle turns out to be wrong. A key rotates by a
registry edit that lists the old and the new key together for an overlap
and then drops the old one; the receipts of those edits are the audit
trail.

**Capabilities.** The manifest gains two fields whose names carry the
difference between what the host enforces and what it only records:

- `grants`, host-enforced because each is the host's own action: `secrets`
  (a list of environment variable names the host will pass, and nothing
  else from the environment), `paths` (which of the task's inputs the host
  will name in the request), `scratch` (a plugin-private writable directory
  the host creates and removes), `time` (a timeout, at most 300 seconds, as
  for command participants), `output` (a result cap, at most 1 MiB, and 64
  KiB of diagnostics).
- `declares`, recorded and attested: `network` (host names the plugin will
  contact), `reads` and `writes` (paths outside what it was given it intends
  to touch, expected empty; the host cannot make a passed path read-only for
  a same-user child), `subprocess` (whether it spawns children; it runs in a
  process group either way), `vendored` (the third-party packages the bundle
  carries, since nothing else is importable).

The registry's grant for a plugin is a subset of its `grants`; the effective
set is the grant; `declares` cannot be granted, only acknowledged, and an
acknowledged `network` declaration is what puts `open_world_hint` on the
tool. The check that the grant is a subset of the declaration runs where the
manifest is open: inside the lease, at `enable` and before every call. That
is a new disk read at those points, accepted.

**Principal.** Launcher-selected, as today; MCP client identity is not
authentication.

## Execution model

- **One binding for code, beside `retrieve`:** `run`. A `run` tool has an
  input schema and an output schema in the manifest, both bounded the way
  `RETRIEVE_SCHEMA` and `OUTPUT_SCHEMA` are, and the host validates both
  sides.
- **The child.** `process.invoke` with the host's own interpreter and the
  flags `-I -S -B` and a `-c` bootstrap the host writes: it sets `sys.path`
  to the bundle directory plus the standard library entries of the host's
  path and nothing else (no site-packages, no user site, no `PYTHONPATH`,
  which `-I` ignores in any case; `-P` would help but is 3.11 and the floor
  is 3.10), then runs the plugin's `entry` module as `__main__`. The
  bootstrap text is part of the receipt's argument digest. The environment
  is passed, always: the allow-list the repair probe requires (with
  `SystemRoot` on Windows) plus the granted secrets, nothing inherited. The
  working directory is the scratch directory; the request is a file, the
  result is a file, stdout and stderr are diagnostics. Python only in this
  version; another language is a later binding, not a manifest flag.
- **Under the lease, checked against the checkpoint.** The signature, the
  artifact digest, the revocation list and the grant are checked inside the
  lease before the child starts; after it exits, the artifact digest is
  checked again and the records the host guards are compared with the
  checkpoint it holds in memory; a change in between discards the result and
  records the call as `unresolved`, which is what the MCP server does for an
  interrupted read.
- **Receipts.** Every call records the plugin's id, version and artifact
  digest, the signer, the effective grant, the acknowledged declarations,
  the environment keys passed, the argument digest (including the
  bootstrap), exit status, duration, the result digest and its effect class
  (`read_only`, `scratch_write`, `paid_provider`); the receipt says, in
  words, that declarations were recorded and not enforced.
- **Bounds.** Manifests and skills 16 KiB as now; a code archive at most 4
  MiB; one to four tools; timeouts and output as above; `k` and the other
  argument bounds unchanged.

## Voyage, the first consumer (D7)

Voyage is the integration that already makes paid network calls behind an
explicit flag, so it is the one to prove the boundary on. As a plugin its
manifest grants `secrets: [VOYAGE_API_KEY]`, `scratch`, `time` and
`output`, and declares `network: [api.voyageai.com]` and `vendored:
[voyageai, lancedb, pyarrow]`; its `run` tools are the embed, rerank and
index operations `voyage_provider` and `voyage_index` expose today.

Two things stay with the host, because the boundary would otherwise break
them. First, **the paid stage journal is the host's.** Today `StageJournal`
writes `prepared`, then `completed`, per stage under the caller's lease, and
a missing ledger beside stage files is itself `PaidStageUnresolved`; a
scratch directory the host deletes cannot hold a billing ledger, and an
exception does not cross a process boundary. So the host assigns the stage
key, writes `prepared` before the child starts, and writes `completed` or
`unresolved` from the child's result or its absence; a child killed at the
`time` bound mid-call leaves a `prepared` stage the host marks `unresolved`,
which is the case the journal exists for. Second, **`--allow-provider`
stays what it is**, the per-invocation authorization for a new paid stage
(a completed stage replays without it); it is not the acknowledgement of
the network declaration, which lives in the accepted registry as part of
the grant, because a flag is not accepted state. `open_world_hint` derives
from that acknowledgement, which for Voyage is always present.

The differential 4.3 owes is that a Voyage journey through the plugin
produces the same journal, stage by stage, as the in-process path did, and
that a child killed mid-call leaves the same `unresolved` stage the
in-process path leaves for an interrupted call. The `voyage` extra stays the
install unit; D7's package boundary is unchanged.

## Requirements

- **R1, signed or not run.** An unsigned bundle, a bundle signed by a key
  the registry does not list, a bundle whose code changed after signing, a
  bundle on the revocation list, and a bundle whose signature cannot be
  verified because `gpg` is absent, fails, or reports an expired or revoked
  key, are each refused at `enable` and at every call, with a refusal text
  naming which. Tested with a scratch key on all three platforms, including
  the platform with `gpg` removed from the path.
- **R2, only what was granted.** The child sees exactly the environment
  keys, the named paths and the scratch directory of the effective grant,
  and can import only the standard library and the bundle; a canary variable
  set in the host's environment is absent in the child; an `import` of a
  package that is installed in the host's site-packages but not vendored
  fails; the receipt lists what was passed. Tested by a plugin that prints
  its environment and its `sys.path`.
- **R3, bounded.** Timeout, output cap, process group teardown and orphan
  cleanup hold for a plugin as `tests/test_process.py` proves them for
  every other subprocess, on all three platforms.
- **R4, evidence is the host's.** A plugin that rewrites the task record,
  the run record or the event file through a path it guessed, recomputing
  the self-digest, is caught by the host's comparison with its in-memory
  checkpoint; the call is recorded `unresolved` and the result discarded.
  Tested with a plugin that does exactly that.
- **R5, output is data.** Every string a plugin returns is wrapped with the
  untrusted-data marker on both paths that carry plugin output to a model,
  the recall path and the review path; a test drives each path with a
  plugin result that reads as an instruction and asserts the wrapper is
  present around it.
- **R6, Voyage unchanged in meaning.** The Voyage journey through the plugin
  yields the same journal and the same `unresolved` behaviour as before, in
  a differential run once with a live key and recorded, and offline with the
  recorded stages in CI, including the kill case.
- **R7, the README changes last.** The protocols row stops listing
  arbitrary executable plugins as unqualified only when R1 to R6 have
  receipts on macOS, Ubuntu and Windows; that is 4.3's done-when.

## Decisions for Patrick

1. **Signing scheme.** Recommended: GPG through `gpg --verify` in a bounded
   subprocess against a keyring built from the public key blocks the
   accepted registry carries, with the maintainer's key as the first entry;
   no new dependency, and the tool the release already signs with. Its
   costs are named: `gpg` must be present or the plugin refuses, and the
   implementation must prove the verifier on all three runners. Alternative:
   an ed25519 library, which adds a dependency to the base install for one
   feature and has no key infrastructure here either.
2. **`grants` and `declares` as two manifest fields.** Recommended: yes,
   with the rule that a grant is a host action and a declaration is
   anything the child could violate, so the spec cannot be read as
   promising more than the host does.
3. **The vocabulary of version 1.** Recommended: the five grants and the
   five declarations above, plus `revoked` and `signers` in the registry;
   anything else is a manifest schema version 2.
4. **The child's import path.** Recommended: the standard library and the
   bundle only, through the host's interpreter with `-I -S -B` and a
   bootstrap the receipt digests; a bundle vendors what it needs and
   declares it. Alternative: the host's site-packages visible, which makes
   T3's recording claim empty for any bundle that imports a network client.
5. **The paid stage journal stays with the host.** Recommended: yes; it is
   the only way the kill case keeps its meaning, and it is the first thing
   4.3's Voyage pull request builds.
6. **Approval.** Recommended: this revision is re-reviewed under the brief
   by the same different model, the findings are dispositioned in its pull
   request, and Patrick's approval is a ruling in the next spec-authority
   addendum; 4.3 waits for it.

## Size

4.3 at four cycles, the plan's upper bound, if the decisions above hold:
one for signing, revocation and the capability fields with their tests on
three platforms; one for the `run` binding, the bootstrap and the child's
environment; one for Voyage behind the boundary with the host-side journal
and its differential; one for the platform traps the child's environment
and `gpg` will meet on Windows.
