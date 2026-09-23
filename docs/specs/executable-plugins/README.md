# Executable plugins: the spec

Draft of September 23, 2026, for [the plan's 3.5](../../plan-1.0.md).
D6 ruled executable plugins "need it", required for stable, with their own
spec, a threat model, and sandboxing or signing before implementation. D7
made Voyage the first real consumer. D20.7 ruled the shape: signing plus a
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
  the call and again after it returns; a mismatch refuses ("Extension bundle
  changed; disable and explicitly replace it").
- **A leased lifecycle.** `install` (disabled), `enable`, `disable`,
  `replace` (disabled only, same identity), `remove` (a tombstone), each
  under the run store's writer lock with a `state_digest` checkpoint;
  `invoke_tool` holds the lease across the whole call, so a concurrent
  `disable` reports busy.
- **Grants through the accepted registry.** One to eight registrations,
  each a `state_dir` and an `artifact_digest`; a participant may be granted
  only `retrieve`, `verify` or a catalogued `<extension>.<tool>`, with
  `max_tool_calls` in 0..8 and no budget reset.
- **A bounded subprocess primitive.** `process.invoke`: no shell, an
  explicit environment that replaces the inherited one, a positive finite
  timeout, an output cap, a process group on POSIX and a Job Object on
  Windows, descendants killed on teardown, and the docstring "Not a security
  sandbox." Three callers already scrub the environment to an allow-list:
  `test` passes six keys, `fix`'s probe requires a frozen minimal
  environment, and the native memory helper passes five keys and refuses
  ambient provider overrides.
- **Protocol hygiene.** The MCP server declares every tool read-only,
  non-destructive and non-idempotent, sets `open_world_hint` only when the
  registry has a Voyage retrieval section, validates arguments against a
  fixed schema and results against an output schema, records every call
  with an effect class before dispatch, and tells the model that source and
  skill content is untrusted data.
- **What does not exist.** No signature, key or trust root anywhere in
  `src/`; no per-actor capability list; no threat-model text. The README's
  isolation row says "This is not a security sandbox", its receipts row says
  receipts "are local values, not signed attestations", and its protocols
  row lists "arbitrary executable plugins" among what is unqualified.

## Terms

A **bundle** is a directory with a manifest, a skill, and now code. A
**plugin** is a bundle whose manifest declares an entry to execute. The
**host** is Harness, in the process that holds the run store's lease. The
**principal** is the launcher-selected participant, as the MCP server has
it. A **capability** is one named thing the host will do for the plugin. A
**grant** is the subset of a plugin's declared capabilities the accepted
registry allows. A **signer** is a key the accepted registry lists.

## Threat model

**Assets.** The dedicated checkout the user trusts; the task and run
records, which are the authority for decisions and acceptance; receipts;
secrets in the environment (`VOYAGE_API_KEY`, `ANTHROPIC_API_KEY`, anything
the shell carries); the network, because a call can cost money or leak
data; the protocol streams, JSON on stdout and MCP stdio, which a stray
print corrupts; and the user's machine beyond the checkout.

**Threats considered, and what the design does about each.**

| # | Threat | Response |
|---|---|---|
| T1 | The code that runs is not the code that was reviewed: a bundle replaced or edited on disk, before or during a call | The artifact digest already covers the manifest and the skill and is checked before and after every call; it now covers the code archive too, and a signature over that digest by a listed signer is required to enable and to run |
| T2 | A plugin reads or writes outside what it was given: the checkout, another task's directory, the home directory | The host passes paths, never discovers them for the plugin; the working directory is plugin-private; writes outside it are not prevented (same user, no sandbox) but are declared, recorded, and detectable where the host already checks digests (task and run records, the checkout snapshot) |
| T3 | Secrets or data leave over the network without the user knowing | Secrets reach the child only by name, from the grant; a plugin with no `secrets` grant has none; network use is declared per host name, recorded in the receipt and attested by the signer, not blocked |
| T4 | Runs forever, floods output, or leaves children behind | `process.invoke`'s timeout, output cap, process group or Job Object, and descendant teardown, as for every other subprocess |
| T5 | Forges evidence: writes the run record, the task record, the event file, or a receipt | Those paths are never passed; the host holds the writer lease for the call's duration; the result is a file the host validates against the tool's output schema and digests; a record whose checkpoint digest changed under a plugin is refused by the existing store checks. Detected, not prevented |
| T6 | Corrupts a protocol stream | The plugin's stdout and stderr are captured diagnostics, never a protocol; the result is a file; the host's stdout stays the host's |
| T7 | Plugin-produced text is taken as instructions by a model | Every string a plugin returns is untrusted data, wrapped the way retrieved content and `SKILL.md` text already are, never a directive |
| T8 | Over-grant: a manifest asks for more than the user meant to give, or a grant drifts from a manifest | The effective set is the grant, never the declaration; a grant that names a capability the manifest does not declare is refused at registry validation; the manifest's `declares` and the registry's `grants` are both in the receipt |
| T9 | Replay and staleness: a call against a bundle whose signature or grant has since been withdrawn | The signer list and the grant are read from the accepted registry inside the lease, before and after the call, as the artifact digest is now |
| T10 | A hostile or compromised same-user process | Out of scope, as it is for the rest of Harness: cooperating-process guarantees, not a sandbox against a local process rewriting files |

**What this model does not defend.** Kernel or OS isolation; a malicious
host; a plugin's own code doing what any process of that user can do,
including reaching the network or the file system beyond what it was
given. The boundary is what the host hands over (credentials, paths,
arguments, time, output, the lease) and what the signer vouched for. The
README's row stays as written: this is not a security sandbox.

## Trust model

**Signing.** A bundle carries a detached signature over its artifact digest,
made with a key the accepted registry lists under `signers`. The scheme is
the one the repository already uses for its tags: GPG, verified through
`gpg --verify` in a bounded subprocess, so no cryptography library enters the
base install. The maintainer's key is the first trust root; a second signer
is a registry edit, which is itself an accepted, checkpointed artifact. A
signature means one thing: this exact bundle, code and manifest and skill,
was reviewed by the signer under the brief. It does not mean the bundle is
safe in general, and the receipt words it that way.

**Capabilities.** The manifest gains two fields whose names carry the
difference between what the host enforces and what it only records:

- `grants`, host-enforced: `secrets` (a list of environment variable
  names the host will pass, and nothing else from the environment),
  `paths` (which of the task's inputs the host will pass as arguments, read
  only), `scratch` (a plugin-private writable directory the host creates
  and removes), `time` (a timeout, at most 300 seconds, as for command
  participants), `output` (a result cap, at most 1 MiB, and 64 KiB of
  diagnostics).
- `declares`, recorded and attested: `network` (host names the plugin will
  contact), `writes` (paths outside `scratch` it intends to write, expected
  empty), `subprocess` (whether it spawns children; it runs in a process
  group either way).

The registry's grant for a plugin is a subset of its `grants`; the effective
set is the grant; `declares` cannot be granted, only acknowledged, and an
acknowledgement is what puts `open_world_hint` on the tool.

**Principal.** Launcher-selected, as today; MCP client identity is not
authentication.

## Execution model

- **One binding for code, beside `retrieve`:** `run`. A `run` tool has an
  input schema and an output schema in the manifest, both bounded the way
  `RETRIEVE_SCHEMA` and `OUTPUT_SCHEMA` are, and the host validates both
  sides.
- **The child.** `process.invoke` with the host's own interpreter,
  `-I -B`, `PYTHONPATH` set to the bundle alone, the plugin's `entry`
  module as `-m` target; an environment that is the allow-list the test
  runner uses plus the granted secrets, nothing inherited; the working
  directory is the scratch directory; the request is a file, the result is
  a file, stdout and stderr are diagnostics. Python only in this version;
  another language is a later binding, not a manifest flag.
- **Under the lease, checked twice.** The signature, the artifact digest
  and the grant are checked inside the lease before the child starts and
  again after it exits; a change in between discards the result and records
  the call as `unresolved`, which is what the MCP server does for an
  interrupted read.
- **Receipts.** Every call records the plugin's id, version and artifact
  digest, the signer, the effective grant, the acknowledged declarations,
  the environment keys passed, the argument digest, exit status, duration,
  the result digest and its effect class (`read_only`, `scratch_write`,
  `paid_provider`); the receipt says, in words, that declarations were
  recorded and not enforced.
- **Bounds.** Manifests and skills 16 KiB as now; a code archive at most 4
  MiB; one to four tools; timeouts and output as above; `k` and the other
  argument bounds unchanged.

## Voyage, the first consumer (D7)

Voyage is the integration that already makes paid network calls behind an
explicit flag, so it is the one to prove the boundary on. As a plugin its
manifest grants `secrets: [VOYAGE_API_KEY]`, `scratch` for the index
generation, `time` and `output`, and declares `network: [api.voyageai.com]`;
its `run` tools are the embed, rerank and index operations
`voyage_provider` and `voyage_index` expose today. `--allow-provider`
becomes the grant's acknowledgement of the network declaration. The paid
stage journal and `PaidStageUnresolved` keep their meaning, and the
differential that 4.3 owes is that a Voyage journey through the plugin
produces the same receipts, stage by stage, as the in-process path did. The
`voyage` extra stays the install unit; D7's package boundary is unchanged.

## Requirements

- **R1, signed or not run.** An unsigned bundle, a bundle signed by a key
  the registry does not list, and a bundle whose code changed after signing
  are refused at `enable` and at every call, before and after, with the
  refusal text naming which. Tested with a scratch key on all three
  platforms.
- **R2, only what was granted.** The child sees exactly the environment
  keys, paths and scratch directory of the effective grant; a canary
  variable set in the host's environment is absent in the child; the receipt
  lists what was passed. Tested by a plugin that prints its environment.
- **R3, bounded.** Timeout, output cap, process group teardown and orphan
  cleanup hold for a plugin as `tests/test_process.py` proves them for
  every other subprocess, on all three platforms.
- **R4, evidence is the host's.** A plugin that writes to the task record,
  the run record or the event file through a path it guessed is detected by
  the existing digest checks and the call is recorded `unresolved`; the
  record's authority is unchanged. Tested with a plugin that tries.
- **R5, output is data.** A plugin's result text never reaches a model as
  an instruction; it is wrapped as untrusted data on every path, and a test
  asserts the wrapper is present on the recall and the review paths.
- **R6, Voyage unchanged in meaning.** The Voyage journey through the plugin
  yields the same journal and the same unresolved behaviour as before, in
  a differential run once with a live key and recorded, and offline with the
  recorded stages in CI.
- **R7, the README changes last.** The protocols row stops listing
  arbitrary executable plugins as unqualified only when R1 to R6 have
  receipts on macOS, Ubuntu and Windows; that is 4.3's done-when.

## Decisions for Patrick

1. **Signing scheme.** Recommended: GPG through `gpg --verify` in a bounded
   subprocess, with the maintainer's key as the first trust root; no new
   dependency, and the same tooling the release already verifies tags with.
   Alternative: an ed25519 library, which adds a dependency to the base
   install for one feature.
2. **`grants` and `declares` as two manifest fields.** Recommended: yes, so
   the enforced and the recorded are visible in the manifest itself and in
   every receipt, and the spec cannot be read as promising more than the
   host does.
3. **The vocabulary of version 1.** Recommended: the five grants and the
   three declarations above; anything else is a manifest schema version 2.
4. **Python only, through the host's interpreter with `-I -B`.**
   Recommended: yes; another language is a new binding with its own review.
5. **Voyage first, in 4.3's first pull request.** Recommended: yes; the
   example plugin follows, since a boundary proven only on an example proves
   less.
6. **Approval.** Recommended: this document is reviewed under the brief by
   a different model tonight, the findings are dispositioned in its pull
   request, and Patrick's approval is a ruling in the next spec-authority
   addendum; 4.3 waits for it.

## Size

4.3 at two to four cycles, as the plan says, if the decisions above hold:
one for signing and the capability fields with their tests, one for the
`run` binding and the child, one for Voyage behind the boundary with its
differential, and one to spare for the platform traps the child's
environment will meet on Windows.
