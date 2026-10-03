# Inspectable citation decisions and direct Google consultation

This follow-up depends on the shared consultation source reviewed in #208.
It is developed separately so that PR's approved source remains unchanged.
The pre-code scope and acceptance were retained in the private audit-followup
handoff before implementation. No merge or release is implied.

## Bounded design

`evidence` reads saved answers beside numbered frozen LF/CRLF source context,
not the current checkout. A citation starts unchecked. `assess-citation` appends
the host's supported/rejected/uncertain judgment, note, selected citation,
snapshot digest and prior checkpoint. Original model answers and journal remain
intact. A judgment is advisory; it cannot authorize dispatch, edits or merging.
At most 128 judgments may be retained. Host judgment is declared, not authenticated.

Antigravity is an explicit consultation adapter with provider
`google-antigravity`, exact model and required effort. It uses existing process
supervision, an empty temporary working directory, disabled slash expansion and
single-use execution. The decoder requires a matching model, request-review
permission mode, matching conversation, one terminal SUCCESS and strict answer.
Only the built-in finish control and its matched ACTIVE/DONE lifecycle are
accepted. External tool or subagent events refuse the answer with unknown effects.
Raw bounded process evidence and available terminal usage stay in the record.

These are post-hoc stream checks, not a tool-isolation boundary. Global runtime
configuration can influence behavior; permitted actions may already have happened
before rejection. No CLI bypass, credential/config edit, automatic retry, model
fallback or cached-response substitution is introduced. The software output limit
remains 64 KiB, not the earlier task-local bridge's larger raw limit.

Codex seats optionally freeze `reasoning_effort` in their accepted configuration.
Antigravity freezes its required `effort`. Other hosts do not gain a High claim.
Explicit flags establish requested effort, not backend attestation.

## Refusal journey

| Command in order | Owner refuses | How preceding input satisfies it |
| --- | --- | --- |
| `source-review prepare` / `roundtable prepare` | `consultation.configuration` raises on unknown adapter, native-provider mismatch, invalid/missing effort or bounds; `prepare` refuses run state inside the source tree | Explicit provider/model/effort config; fresh run outside selected source root |
| `run --accept DIGEST --allow-external --allow-native` | `consultation.run` raises on stale acceptance, absent authority, terminal owner or unresolved journal | Digest comes from prepared contract; chair already owns concrete upload/spend authority |
| Native Antigravity completion | `antigravity.decode` raises on wrong session/model/mode, external steps, unmatched finish, failed/malformed terminal output | Successful headless CLI stream must supply the exact frozen model and complete lifecycle; a failure is retained, not repaired by inference retry |
| `evidence RUN` | `consultation.load` raises on changed owner, checkpoint, contract or malformed retained decisions | Original owned run, unchanged journal and frozen source snapshot; no provider call |
| `assess-citation RUN --checkpoint DIGEST ...` | `assess_citation` raises on stale checkpoint; `consultation_evidence.assessment` raises on unknown citation, invalid decision/note or 128-entry bound; writer lease refuses concurrent owner | Current evidence view supplies checkpoint and selectors; explicit host note/decision; no answer or call-history edits |
| Inspect again | Same load checks; original frozen source remains authoritative | New saved checkpoint and append-only assessments; original answers unchanged |
| Attempt terminal run again | `run` raises `Terminal consultation cannot dispatch again` | No earlier step grants a repeat: test must show zero new process calls |

Selectors use zero-based round and citation indexes. The source display uses
one-based editor lines. In-range false claims remain unchecked until explicitly
assessed; a model's approve/recommend verdict never changes that state.

## Evidence gates

Real fixture subprocess tests cover Google completion/single-use/authority/replay;
malformed streams cover model/session/lifecycle/tool/subagent refusals. The CLI
inspection test accepts a structurally valid false claim, changes the checkout,
shows the original line, rejects a stale judgment, saves rejection without changing
answers/journal, and refuses terminal continuation. Source and wrapper changes
require different-model review, then full-suite/installed-wheel and CI evidence.

A fresh authorized live contract selects only the three previously approved
consultation source files and configured providers, within the existing $10 task
cap. Known prior Anthropic spend is $1.231298; Google/Codex quota dollar values
are unavailable. No larger upload or new provider is authorized. Old failed
records, raw responses, wheels and environments remain untouched.

Protocol references: [Google headless output](https://antigravity.google/docs/cli/headless/),
[permissions](https://antigravity.google/docs/permissions?tab=cli),
[finish control](https://www.antigravity.google/docs/sdk/tools/).
Live direct transport, installed desktop discovery and model-quality claims need
their own observed evidence; offline tests do not supply them.
