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

## Initialize a roundtable

Generate a consultation configuration with explicit models:

```sh
attune-harness init --for roundtable --project "$PROJECT" \
  --question "Review the selected source boundary" --seats claude,codex \
  --model claude=YOUR_EXPLICIT_CLAUDE_MODEL_ID \
  --model codex=YOUR_EXPLICIT_CODEX_MODEL_ID --rounds 1 \
  --scope src/example.py --task-dir "$RUN"
```

This writes only `$PROJECT/roundtable.json`, leaving `participants.json` intact.
The selected roster defaults to `claude,codex`; it never switches seats or guesses
a model ID from `--profile`, a login or PATH discovery. A missing model refuses
with the exact `--model SEAT=YOUR_EXPLICIT_MODEL_ID` flag to add. The same checks
as prepare validate the configuration before writing. Local preflight uses only
the version/login checks and grants no provider, upload or spending authority.
Missing binaries/login and unknown model access are advisory in the creation
result: valid configuration creation exits 0 even when a host is unavailable.
Inspect those reports and resolve them before running a consultation.

`--timeout` defaults to 120 seconds per seat; `--rounds` defaults to 1.
The author identity defaults to the first selected seat; `--author codex` selects
another configured identity. A third `antigravity` seat needs its own `--model`
and explicit `--effort antigravity=high` (or low, medium, max).
`--task-dir` names the future run directory, outside the source with an existing
parent; it is not created. Its default is the sibling `<project>-roundtable`.
`--scope` supplies the repeated `--path` values in the next prepare command;
without it, replace `SELECTED_SOURCE_FILE` with your selected regular source file.
Prepare validates those source paths. This initializer creates no run or accepted
contract and never dispatches a model. Existing `roundtable.json` needs `--force`,
which preserves `roundtable.json.bak` and refuses to overwrite an earlier backup.

To reuse identities from `participants.json`, copy these values explicitly into
the initializer or consultation config. The initializer does not import a registry:

| Registry field | Consultation seat field |
| --- | --- |
| `adapter` (`claude` or `codex`) | Same adapter; use it as the selected `--seats` name |
| `model` | `identity.model`, supplied through `--model SEAT=MODEL` |
| Native adapter | `identity.provider` equals the adapter; Antigravity uses `google-antigravity` |
| `timeout` | `timeout`; set `--timeout` or edit each validated seat |
| Codex `reasoning_effort` | Same optional field, when editing the configuration |
| `tools`, `review_mode`, `max_turns`, `max_tool_calls`, `skills_context_tokens` | Documentary-review settings; do not copy into consultation seats |

Registry participant names such as `lead` and `reviewer` can be the keys of a
handwritten consultation's `participants` object. Its provider/model pairs must
be distinct. Deterministic registry seats are not consultation adapters; command
wrappers require the consultation's explicit identity, command and timeout.

## Seat preflight before prepare

Run the check before preparing either consultation:

```sh
attune-harness roundtable check --config "$CONFIG"
attune-harness source-review check --config "$CONFIG"
```

The check validates the same configuration rules as `prepare`, including seat
count, distinct provider/model pairs and rounds. It returns each participant's
`state`, resolved `binary`, `version` when available, and `fix`. No run directory,
contract, provider/model call or authority is created. Only native Claude/Codex
version and local login-status commands are executed; configured command wrappers
are never run. Authentication diagnostics and credentials are not printed.

States are `ready`, `not_signed_in`, `missing_binary` or `unknown`. A recognized
missing login reports `not_signed_in` for that seat only. A signed-in host still
reports `unknown`: a local login report proves neither token freshness nor access
to the configured model. `ready` is reserved for a free probe that proves model
access; current probes supply no such proof. Antigravity and custom wrappers have
no verified local auth/version probe here and stay `unknown` when found on PATH.
No paid test or fallback is used to resolve uncertainty.

Exit 2 means invalid configuration or a detected missing binary/login. Exit 0
means the check found no such failure, and may still include `unknown` seats.
Read every seat and its fix before `prepare`; the check grants no spend authority.

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

Inspect each citation beside its numbered frozen source context, even after the
checkout changes. The support state starts `unchecked`:

```sh
attune-harness source-review evidence "$RUN"
attune-harness source-review assess-citation "$RUN" --checkpoint "$CHECKPOINT_DIGEST" --round 0 --participant reviewer --citation 0 --decision rejected --note "The cited line does not support the claim"
```

To record several decisions made against one evidence view, pass a JSON list
of `{round, participant, citation, decision, note}` objects instead of the
single-decision options:

```sh
attune-harness source-review assess-citation "$RUN" --checkpoint "$CHECKPOINT_DIGEST" --decisions decisions.json
```

The batch is recorded whole or not at all: one invalid entry, a repeated
selector or a total over 128 refuses every entry, and the error names the
zero-based entry. Each saved entry keeps the checkpoint you judged against, and
the run's checkpoint advances once.

Take the checkpoint and selectors from the current evidence view. Round and
citation indexes are zero-based; displayed source lines are one-based. Decisions
are `supported`, `rejected` or `uncertain`, with a required host note. This appends
an advisory host assessment without changing the model answer or journal, makes
no provider calls, and grants no action authority. A stale checkpoint refuses;
there are at most 128 assessments. Use `roundtable` for roundtable owners.
Successful `assess-citation` commands exit zero even when the owner's retained
status is failed or unresolved. The assessment does not clear that status;
inspect it separately. Refused assessments exit 2 without appending a decision.

## Direct Antigravity seat

The development candidate accepts this explicit native consultation seat:

```json
{
  "adapter": "antigravity",
  "identity": {"provider": "google-antigravity", "model": "gemini-3.1-pro-high"},
  "timeout": 210,
  "effort": "high"
}
```

Use it in the existing participant map; native and external authority are both
required. The signed-in `agy` binary must already exist on PATH. No sign-in,
settings or credentials are changed. Terminal output must report the configured
model and session, successful structured answer and matched finish lifecycle.
Raw process evidence and available usage are retained. External tool/subagent
stream events refuse the answer; this post-hoc check does not prove isolation or
undo effects. Native software output remains bounded to 64 KiB. No fallback,
automatic retries or replay of old provider responses occurs in this adapter.
Each invocation sends one NDJSON user event through stdin and ends input at EOF,
following the [documented headless protocol](https://antigravity.google/docs/cli/headless/#stream-prompts-from-stdin).
Frozen source and prior-round context stay out of command-line arguments.

Codex seats may include an optional explicit `reasoning_effort`, such as `high`;
it becomes part of the accepted contract and native invocation. Missing effort
remains the runtime default. This does not establish Sol 6.1 account availability
or authenticated backend effort. See the [bounded design](design-consultation-evidence-google.md).

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
