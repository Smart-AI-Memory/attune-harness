# S1 — Codex app-server qualification result

**Status: S1 complete with a stop-gate result. Subscription support remains
unqualified. S2–S6 have not started.** November 3, 2026, America/New_York.

## Verdict

The app-owned OAuth/Keychain lifecycle is approved. The existing Codex app-server
candidate does not yet meet this spec's required execution boundary: one
host-authorized logical inference per turn, with native model follow-ups disabled.
The reviewed source permits another sampling request after a tool response,
including a rejected/unsupported tool call. No configuration or app-server RPC
that enforces the required single-inference cap was established in this pass.

This is a **not-qualified** result for the inspected candidate and contract,
not a claim that all Codex versions or every possible integration are incapable
of enforcing a bound. A public documentation example for token routing does
not establish that bound. The first failed requirement stops qualification
before auth/runtime implementation, as S1 requires.

No live sign-in, native auth/status/account RPC, model endpoint, subscription
trial, API credit or credential-store access was used. Claude C1 remains
separate and unstarted. No Harness source, test or workflow file changed.

## Pinned candidate and evidence

| Item | Observed value |
| --- | --- |
| Platform | Darwin, arm64 |
| Installed package and version output | `@openai/codex` / `codex-cli 0.153.4` |
| Candidate binary | Platform package entrypoint `vendor/aarch64-apple-darwin/bin/codex`; resolved by absolute path, without the JavaScript launcher |
| Binary size and SHA-256 | 220,584,000 bytes; `b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3` |
| Upstream release tag | `rust-v0.153.4`, annotated tag object `042fb41b7c813ac7999105e886b2b7aa715b5081` |
| Release source commit | `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` |
| Downloaded source archive SHA-256 | `bbbf66ffa30846f1e9bc3ae8a87a5aa0bb768efee8dbb94759dc9eb64bb4aa3a` |
| Generated protocol evidence | Stable and experimental JSON schema export: 720 retained files in total |
| Schema manifest SHA-256 | `973b840528d25234826ca0154f1f64b7992e2822d6ed3eeb2b56e16e7f1cb9a6` |
| Latest-release comparison | `rust-v0.166.0`, published October 29, 2026; source commit `6ff1e1ca3b30fc8b914720681fcf5fe62e95f856` |

The source mapping follows the published release tag and installed version;
this pass did not reproduce the binary build or verify a build attestation.
The latest-release check inspected selected source files only: no 0.166.0
binary was installed, executed or qualified, and the installed runtime was
not upgraded.

Local ignored evidence is retained under
`docs/receipts/codex-subscription-s1-2026-11-03/`. It contains the original
source archive, source manifest, model-free witness scripts/results, generated
schemas and the limited latest-source comparison. Those files are private
local evidence, not prerequisites a public reader is assumed to possess.

## Model-free witnesses

The candidate ran in a fresh private directory with an explicit child
environment containing only `PATH`, unchanged `HOME`, private `CODEX_HOME`,
private `TMPDIR` and `LANG`. A macOS process profile denied all networking,
reads from the native Codex home and Keychain directory, and writes under the
user home. No app-server session or thread was started.

| Witness | Result | Claim supported |
| --- | --- | --- |
| Initial attempt under the host's normal process restrictions | `sandbox_apply: Operation not permitted`, exit 71 | No candidate process ran; this failed receipt is preserved |
| Same restricted witness with host permission to apply its process profile | Version command exit 0; `codex-cli 0.153.4` | Observed binary version |
| **`app-server --help`** | Exit 0 | This installed binary exposes the expected command family |
| **`app-server generate-json-schema`** | Exit 0 | A stable protocol schema was exported by the pinned binary |
| **`app-server generate-json-schema --experimental`** | Exit 0 | Experimental fields were also inventoried; this does not approve their use |

The four successful commands had empty stderr. Schema export follows the
[CLI's direct generation branch](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/cli/src/main.rs#L1354-L1371),
which does not start a model session. These checks qualify only version/help
and schema export under the witness restrictions; they do not qualify startup,
token routing, tool isolation or account/model eligibility.

## Source findings

| Requirement | Primary evidence | Finding |
| --- | --- | --- |
| A separate plan-token provider is a supported candidate mechanism | [Official integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server); [provider fields](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/model-provider-info/src/lib.rs#L102-L148) | The fixed endpoint, token environment reference and separate provider configuration can be described. Effective startup/thread configuration and actual route remain unqualified. |
| Zero configured retries bounds the whole turn | [Provider retry controls](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/model-provider-info/src/lib.rs#L359-L370); [turn loop](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/session/turn.rs#L380-L434) | Not established. Request/stream retry controls are distinct from the agent's next sampling request. |
| Unexpected or disabled tool calls cannot trigger another inference | [Tool-result handling](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/stream_events_utils.rs#L293-L329); [unknown-tool response](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/tools/registry.rs#L516-L536); [loop continuation](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/session/turn.rs#L511-L572) | The source marks tool output for follow-up and returns unsupported tool errors to the model. A host interrupt after notification cannot establish an atomic pre-request cap. |
| A time limit or read-only workspace proves one inference | Same loop; exported thread/turn schema | Neither supplies the required request-count guarantee. They constrain different effects. |
| A newer public release clearly removes the concern | [0.166.0 follow-up marking](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/stream_events_utils.rs#L369); [0.166.0 turn loop](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/session/turn.rs#L585-L627); [turn protocol](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server-protocol/src/protocol/v2/turn.rs#L173) | The limited comparison still contains autonomous follow-up. It did not establish the missing control and is not a full 0.166.0 qualification. |

The [upstream inert test](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/tests/suite/search_tool.rs#L248-L326)
also describes a rejected tool call appearing in a later model request. It
supports the source interpretation; that Rust test was read, not run here.
No fake-model turn was executed against the native runtime.

The generated `ThreadStartParams` and `TurnStartParams` expose configuration,
environment and output-schema controls, but no explicit per-turn inference-count
limit. This is an inventory observation, not proof that every indirect mechanism
has been exhausted. A replacement must provide positive enforcement evidence;
absence of a discovered control cannot be converted to a passed gate.

## Unfinished qualification at the stopping point

Managed/configuration precedence, thread-resolved provider enforcement,
model-free runtime startup, full native tool suppression, cancellation/descendant
cleanup, refreshed-token identity binding and actual plan/model eligibility
remain unqualified. These were not bypassed or inferred from help/schema output.
No chosen model/effort tuple is qualified. S1 stops at the first enforcement gap
rather than consuming quota to see whether a friendly response happens to work.

Latest-source snapshots retained through the connector have one additional
trailing newline from the local text-copy operation. The separate copy-validation
receipt verifies their upstream Git blob hashes after removing that one byte;
the original saved copies and manifests remain unchanged. Public citations use
the immutable upstream commit, not the normalized local copy.

## Next decision before S2

Keep the approved funding contract, app-owned OAuth/Keychain custody, no automatic
API fallback and separate Claude qualification. The unresolved decision concerns
the inference transport and its enforceable limits.

**Recommended:** authorize a narrow design/source revision that evaluates the
official direct plan-OAuth Responses route. It would reuse the approved profile
lifecycle and owner/admission contracts, and require one host-controlled HTTP
request with no native tool executor, automatic retry or implicit fallback.
It must still verify the intended plan/model eligibility and must not claim
native Codex quota equivalence. This changes the proposed transport; it is not
an authorization to implement a new client or run a live request.

Alternative: retain app-server as a requirement and wait for, or identify, a
provider-supported atomic inference-budget control. Qualify that exact version
before continuing. No such control was established here.

Do not relax the one-inference/native-tool boundary silently to make S1 pass.
No API credits are needed for either next design/source investigation. Any later
live connection or credit use must be presented to Patrick first.
