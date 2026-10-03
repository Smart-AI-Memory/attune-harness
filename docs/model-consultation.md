# Source review and roundtable from either coding host

These additive CLI routes are a development candidate. Install this branch's
wheel to use them; the published 1.2.0 runtime and pinned Claude marketplace
release do not expose them. The shared development plugin contains both skills;
`scripts/package_codex_plugin.py` packages the same skill bytes for Codex.
No host settings or credentials need changing to exercise the CLI.

Use the same configuration and commands from Claude Code or Codex. Select an
explicit reviewer different from the author. Here is a source-review
configuration; replace the model identifiers with the exact configured models
you have authorized:

```json
{
  "schema_version": 1,
  "question": "Review the selected source boundary and cite reproducible defects",
  "author": {"provider": "codex", "model": "gpt-6.1-sol"},
  "participants": {
    "reviewer": {
      "adapter": "claude",
      "identity": {"provider": "claude", "model": "YOUR_EXPLICIT_CLAUDE_MODEL_ID"},
      "timeout": 120
    }
  },
  "rounds": 1
}
```

```sh
attune-harness source-review prepare --project "$PROJECT" --path src/example.py --config "$CONFIG" --run-dir "$RUN"
attune-harness source-review status "$RUN"
attune-harness source-review run "$RUN" --accept "$CONTRACT_DIGEST" --allow-external --allow-native
```

`RUN` must be a new directory outside the source checkout, with an existing
parent. Read the prepared contract before taking its `contract_digest` as
`CONTRACT_DIGEST`. Provider flags require your upload/spend authorization. They
do not create a dollar cap. Source files are retained as hashed UTF-8 bytes,
at most 32 files and 128 KiB total; subsequent checkout edits do not change them.

Capture opens source directories and files through retained no-follow handles.
Windows capture uses the existing fixed local NTFS eligibility profile: canonical
names, no reparse points, no alternate streams and single-link regular files.
UNC/network volumes and other Windows filesystems refuse this profile. Windows
native behavior requires its actual CI jobs; macOS checks cannot qualify it.

For roundtable, configure two or three seats with distinct provider/model pairs,
and `rounds` of 1 or 2, then use `roundtable` in place of `source-review` in the
commands above. First-round seats receive no other answers or chair lean.
Second-round seats receive only the completed preceding round. The host retains
every verdict and disagreement; the chair decides what action to take.

Each turn has a configured timeout of 1–300 seconds and 64 KiB process output
limit. There are at most six calls, no automatic retries and no paid synthesis.
`run --max-operations 1` pauses after one new saved turn. Continue with the same
contract; completed turns replay without a call. Status exposes the saved
`events` journal even if interruption happened before the answer projection.

An uncertain dispatch refuses continuation. Inspect the owner before abandoning
with `source-review abandon "$RUN" --checkpoint "$CHECKPOINT_DIGEST"` (or the
roundtable equivalent). Abandonment retains the journal and unknown effects;
it never establishes that charges or detached activity stopped. Ctrl-C stops
the supervised process and leaves an unresolved checkpoint. Library callers
can pass a cancellation `Event` to the shared `run` API. A supervised cancellation
is retained as cancelled with unknown effects; abandonment preserves the previous
status. Read `status` explicitly: exit zero also covers prepared, paused and
cancelled states.

## Identity and evidence limits

The author and selected provider/model pair are host declarations. Claude's
reported `modelUsage` and session identity are retained; a reported different
model refuses the turn. Codex currently reports a thread but no actual model.
Missing metadata remains unknown, and no identity is authenticated by Harness.
Aliases cannot establish actual model independence. Provider errors and raw
bounded process diagnostics remain evidence, never authorization.

Answers use `verdict`, `summary`, and `evidence`; each citation contains a frozen
`path`, one-based LF/CRLF content `line`, and `detail`. Harness checks citation location, not
whether the reasoning or claimed defect is true. Reproduce findings before
editing. Model verdicts never authorize a merge or publication.

## Other agent seam

An explicit `command` adapter supplies `identity`, `timeout`, and `command`
(argument list, no shell). It receives the existing v1 `Attempt` JSON on stdin
and returns `{version: 1, request_digest: SHA256(stdin), text: STRING}`. `text`
contains the answer JSON above. External authority is required; native authority
is unnecessary. Its provider/model identity is declared and unverified. No third
LLM, live host invocation or model quality is qualified by offline wrapper tests.

The [design](design-model-consultation.md) explains the retained authority and
replay boundaries. Documentary `review` and repair remain separate routes.

## Observed development journeys

On October 1, Codex chaired a source review using native `claude-opus-5-5`.
Claude reported that model, found a cancellation defect, and approved the
corrected three-file scope in a separate delta review. A Claude Code chair
using a per-session candidate plugin then invoked the installed shared CLI
for a one-round Opus/Codex roundtable: both seats completed, retained citations
and returned `recommend`. The explicit roster was `claude-opus-5-5` and
`gpt-6-astra`. Codex reported a thread and token usage but no actual model;
its configured identity remains unverified.

An earlier explicit `gpt-6.1-sol` Codex CLI roster failed because that account
rejected the model identifier. The failed run remains terminal and retained;
it was not retried or silently substituted. Desktop model names are not proof
of CLI access. The new roster had its own prepare/accept contract. Per-seat
reasoning effort is not part of this configuration contract; a `High` execution
claim needs separate transport evidence.

These observations qualify the bounded host journey for the selected source
scope, not model quality, fresh desktop plugin discovery, three live seats,
Google/Antigravity transport, or published-release availability. Three-seat
configuration and command exchange are supported in software; a third live
provider needs its own explicitly configured model, upload authority and evidence.
