# First local build receipt

- Scope: deterministic execution-contract experiment, not the completed harness.
- Design note preceded source edits; see design-first-increment.md.
- Python 3.10.11 behavioral run: 17 passed, 98.75% statement coverage. Command: `/Users/patrickroebuck/.pyenv/versions/3.10.11/bin/python3 -m pytest tests -q --cov=attune_harness --cov-report=term-missing --cov-fail-under=85` from this package root.
- Wheel built with `python3 -m build --wheel --no-isolation` using the local Python 3.12 build environment. Initial build failed because that interpreter lacked the explicitly required wheel distribution; switched to setuptools>=77, which provides the build command. No download needed.
- Installed wheel using `pip install --no-index --no-deps` into a clean temporary venv. Ran from /private/tmp with `python -I -m attune_harness`; JSON receipt reported verified arithmetic result.
- Independent installed-wheel negative check returned rejected for answer 5. Import discovery confirmed attune, anthropic, claude_agent_sdk, and openai were absent.
- No native model calls, protocol interoperability, persistence, tool isolation, or migration was tested. No remote repository, release, or publication created.
- Roadmap copy links to the current attune-ai planning worktree; those references must be migrated before that worktree is removed.

Next: review the small contract, expand Phase 0 capability/state cases, and design the native-adapter experiment. Retain the experimental designation until lifecycle and adapter guarantees have real receipts.

## Continuation receipt — 2026-09-14 UTC

- Reproduced the original 17-test result at 98.75% statement coverage before
  source edits. Rebuilt and installed the original wheel in a fresh temporary
  venv; positive and negative checks passed outside the source tree.
- Added the disposable adapter boundary described in
  [design-adapter-increment.md](design-adapter-increment.md): immutable assignment,
  full-request correlation, strict bounded JSON decoding, single-use dispatch,
  and identity retained alongside independent verification receipts.
- Suite: **56 passed, 99.35% statement coverage**, including 39 new adapter
  cases; adapter module has 100% statement coverage. Same Python 3.10.11 command
  as the original receipt. Existing source and tests were unchanged; new tests
  accompany new code, so the existing-code mutation receipt is not applicable.
- Rebuilt wheel with `python3 -m build --wheel --no-isolation`. Installed using
  `pip install --no-index --no-deps` in a fresh temporary venv and ran from its
  temporary directory with `-I`. The actual `examples/json_exchange.py` consumer
  passed (verified result and refused second dispatch); original demo passed;
  independent wrong-answer adapter check returned rejected. Import discovery
  confirmed attune, anthropic, claude_agent_sdk and openai absent.
- Wheel: `dist/attune_harness-0.1.0.dev0-py3-none-any.whl`;
  SHA256 `3bd4982870a851da37c8bd0ce19366b8c5ab704073ca097b5b10573699e03041`.
- [portable-contract.md](portable-contract.md) records observed source seams,
  profile qualifications, state cases and C8–C15/C19 probe mappings.
  [native-adapter-experiment.md](native-adapter-experiment.md) records the next
  live comparison. Neither Phase 0 nor Phase 1 is claimed complete.
- This directory still has no Git repository. No commits, remote publication,
  credentials changes, model calls or modifications to attune-ai occurred.
  No different-model review ran. Source inventory uses the locally verified
  attune-ai HEAD; remote freshness remains unverified.

Next: finish host/handoff caller inventory, then qualify native translators with
recorded versions and raw boundary receipts. The JSON format is experimental,
not a standard protocol. Roles/digests do not authorize or authenticate; failed
dispatch does not prove absence of external effects. Cancellation, persistent
deduplication, capability registry and recovery remain unsupported.

## Native implementation continuation — 2026-09-14

The next bounded increment is implemented and verified locally. See
[native-build-receipt.md](native-build-receipt.md): 124 tests pass at 99.42%
statement coverage; both native translators and actual POSIX process failure
probes pass; isolated installed-wheel fixture consumers pass. Authenticated
Claude/Codex model calls remain pending. This supersedes the earlier test count
and wheel hash, without turning fixture evidence into live qualification.

## First live boundary receipt — 2026-09-14

The approved Codex arithmetic probe passed independent verification; Claude's
probe failed with insufficient credit. Raw results and the resulting diagnostic
fix are in [live-probe-receipt.md](live-probe-receipt.md). Current suite:
129 passed, 99.43% coverage; saved-output replay passes on the updated installed
wheel. Awaiting Claude funding confirmation before another provider call.

## Local feature milestone — 2026-09-14

Completed the four requested steps: pinned dependency snapshots, optional strict
verification with CLI, installed workflow checks, then local keyword retrieval.
[Full receipt](feature-workflow-receipt.md): 170 passing tests, 98.51% statement
coverage, 26 installed CLI cases across four configurations, reproducible
pinned dependency wheels and retained example reports. No provider calls ran;
Claude remains on hold. The final wheel hash and runnable commands are linked
from that receipt.

## Local coordinated-review milestone — 2026-09-14

Implemented the authorized local Phase 2 journey: real attune-forms intake,
scoped retrieval/verification for two configurable participants, independent
document verification and durable inspectable records. [Full receipt](review-workflow-receipt.md):
252 passing tests, 98.67% statement coverage, 3/3 new CLI tests fail with their
dispatch branch removed, and 40 installed CLI cases across five dependency
profiles. Both native leads pass injected-transport journeys; the independent
command peer passes the installed real-feature journey. Zero provider calls.
The full live multi-model Phase 2 matrix and broader roadmap obligations remain
open; Claude qualification remains on hold. The final wheel hash and runnable
example are linked from the receipt.

## Local recovery milestone — 2026-09-14

Implemented the authorized local Phase 3 increment: checkpointed resume,
constrained reconciliation, cancellation and two-way local lead assignment.
[Full receipt](recovery-workflow-receipt.md): 319 tests passed, 97.50% statement
coverage, 5/5 targeted mutation tests failed with guards removed, and 63 installed
CLI cases passed. A real local command's uncertain reply was recovered without
repeating its effect. The 24-case deterministic transfer matrix preserved accepted
constraints and evidence. No provider calls ran. Full live qualification, E1 and
cross-machine/general effect recovery remain outstanding.

## Local extension milestone — 2026-09-14

Implemented the bounded local Phase 4 extension contract: explicit data-only
skill/tool bundles, artifact-bound lifecycle controls, scoped review dispatch and
an explicit public Attune BasePlugin bridge. [Full receipt](extension-workflow-receipt.md):
366 tests passed, 97.26% statement coverage, 10/11 targeted mutation tests fail
with guards removed (the live-denial negative pin passes), and 90 installed CLI
cases passed. Qualification uncovered and fixed a bounded process-cleanup race.
Zero provider calls. MCP/A2A interoperability, executable/host plugin support and
E2 remain open; this is not full Phase 4 completion.

## Local MCP/A2A milestone — 2026-09-14

Harness's optional MCP adapter now pins SDK 2.2.0. Independent stdio clients pass
2025-11-25 and 2026-07-28; a legacy SDK 1.29.1 client also passes against the new
server. The separate attune-ai environment retains its 1.29.1 pin. A2A 1.0 now
has a local JSONRPC adapter with task/artifact correlation, an independent HTTP
peer, explicit refresh/cancellation and unresolved acknowledgement handling.
[Final receipt](a2a-workflow-receipt.md): **427 tests**, **94.50% coverage**,
**110 installed cases**, and **2/2 new MCP CLI mutation tests fail** with guards
removed. The final wheel rebuild is byte-identical. Zero provider calls; public
dependency downloads used isolated environments. E2, broader host/remote identity
qualification and earlier live-model obligations remain open.

## E2 local experiment — 2026-09-14

[E2 receipt](e2-capability-evidence-receipt.md): all **24 cells** were evaluated and
independently audited. Disposition **revise**: a version/scope-bound success cache
made two false verified-availability claims after injected runtime failure.
Working cases passed, upgraded evidence was invalidated, fresh qualification
passed and there were no unnecessary rejections. The candidate was not promoted
to production; existing call-time checks and call-bound evidence remain intact.
**445 tests passed**, including 18 evaluator tests, at **94.50% production statement
coverage**. The prior wheel and production sources remain byte-identical. Zero
provider calls, downloads or credential changes. Broader Phase 4 and earlier
live-model obligations remain open.

## Phase 5 local evaluation — 2026-09-14

[Phase 5 receipt](phase5-evaluation-receipt.md): E1's local precursor passed and
audited all **48 cells**. Both conditions preserve accepted constraints; Harness
completes 24 continuations with zero duplicate request effects and eight explicit
lost-reply reconciliations. E1 remains inconclusive on broader recovery value.
E3 has **144 prepared trial envelopes** and a validated synthetic scorer; real
collaboration trials and C16 remain unrun/inconclusive. E2 retains its **revise**
disposition. **479 tests passed**, including **34 new evaluator checks**, at
**94.50% production statement coverage**. All 19 production Python files match
the prior qualified wheel. Zero provider calls, downloads or credential changes.
Phase 5, broader Phase 4 qualification and earlier live obligations remain open.

## E2 proposal fixed — 2026-09-14

[Revision receipt](e2-revision-receipt.md): the call-bound replacement passes
the new **24-cell comparison** and **two post-success runtime-failure checks**.
It makes no current-availability claim from history, delivers working/upgraded
invocation results and performs no consumer dispatch when current guards deny
access. Disposition: **adopt the narrowed local contract**; the original cache
and its **revise** result remain unchanged. **523 tests passed**, including
**44 new policy checks**, at **94.50% production statement coverage**.
Production source and the qualified wheel are unchanged. Zero provider calls,
downloads, credential operations or sibling edits. E1/E3/C16 live comparisons
and wider host qualification remain outstanding.


## Phase 5 real research and Phase 6 local pilot — 2026-09-14

[Phase 5 research](e3-local-research-receipt.md) completed 144 real trials and
480 local model calls. E3/C16 are **revise**: equal correctness but one extra
critical miss versus the best fixed baseline. E1 remains inconclusive beyond the
local precursor; E2's narrowed local contract remains adopted. Broader native,
paid-cost and human-repair claims are unqualified.

[Phase 6 pilot](phase6-pilot-receipt.md) completed the clean install, real document
review, pause/resume, extension lifecycle and package rollback on dev3. **582 tests,
93.34% statement coverage, 110 installed cases, 28 pilot commands and 10 rollback
commands pass; 2/2 eligible diagnostic tests fail with their handler removed.**
An initial live grammar failure was retained and corrected; the final wheel's
rebuild is byte-identical. The pilot preserves 9 verified, 0 refuted and 25 unknown
claims. A model narrative's unsupported assertions are explicitly identified.
Zero paid API calls or credential operations; original artifacts/data are retained.
The supported local pilot is complete. Patrick's preferred-path decision and
broader platform/native-provider qualification remain outstanding.

## Configurable output budget — 2026-09-14

[Dev4 receipt](output-budget-receipt.md): removed the 3,000-character cap and
fixed word-count instruction; added per-workflow `--max-output-tokens`, retaining
the 512-token default and 32 KiB narrative / 64 KiB JSON transport limits.
**615 tests pass (33 new), 94.09% statement coverage, 110 installed checks, and
28 real pilot commands.** Targeted mutations detect 9/9 introduced regressions;
28/33 new cases fail under at least one relevant mutation. Long ASCII/Unicode
boundaries are proven by fixtures. Live 2,048-token configuration succeeds but
the model chooses a short answer; an 8-token truncated answer is retained as
failed without retry. Four local generations and zero paid API calls. The wheel
rebuild is byte-identical and all prior wheels/research artifacts are preserved.

## Model-aware token accounting — 2026-09-14

[Dev5 receipt](token-accounting-receipt.md): optional local token counting uses
the qualified Llama vocabulary/template and preserves explicit output reserves.
The full-document pilot completes at **2,048 output tokens**, with **4,386 input
tokens** matching the server and no evidence removed. Byte estimation remains a
labeled option; missing/changed selected tokenizers and count drift fail visibly.
The 32 KiB narrative / 64 KiB JSON limits remain unchanged. **654 tests (39 new),
94.36% coverage, 110 installed regression checks, three installed tokenizer checks,
and 28 pilot commands pass.** Targeted mutations detect 11/11 regressions;
31/39 new cases fail under at least one mutation. Four local generations and
zero paid API calls; no model download or credential changes. Dev0..dev4 wheels
are preserved and dev5 rebuilds byte-identically.

## Documentation-review quality acceptance — 2026-09-14

The [frozen quality comparison](review-quality-receipt.md) is **revise**. All
36 workflow trials / 54 local generations completed, but Harness passed 9/18
quality trials versus single-pass 16/18. Harness missed two of six critical
opportunities, produced nine unsupported assertions, and preserved uncertainty
in four of six ambiguous trials. Single-pass also failed the zero-miss/zero-false-
assertion target. No output/context budget was exhausted. **680 tests passed**,
including 26 evaluation-only checks; the production dev5 wheel and 22 modules
remain unchanged. All inputs, judgments, raw responses and failures are retained;
no paid API calls or retries. Next proposed work is source-grounded review output
and substantive verdict validation before another bounded comparison.

## Grounded review and passage review — 2026-09-14

The [dev6 closing receipt](grounded-review-receipt.md) records **722 software tests**
and the preserved live failure: **0/27 Harness workflows completed** because of
invalid reference citations. That quality result remains **revise**.

The authorized [dev7 increment](passage-review-receipt.md) adds explicit
`--grounded-passages`, host-issued IDs, exact host-rendered source text and an
overall verdict derived from individual assessments. **758 tests pass**, including
36 new cases; **10/10 targeted mutations are detected**, with **29/36 new tests**
failing under at least one relevant mutation. The isolated offline installation
passes **35 review/recovery checks and three dependency-free core CLI checks**.
All 24 installed production modules match source; the wheel rebuilds identically.

The frozen local evaluation finished **45 trials / 76 generations in 697.32 s**.
Harness completed **30/36**, passed **2/36** quality trials, missed **3/12** critical
opportunities and made **73 unsupported assertions**. The matched fresh subset is
**0/9 Harness versus 5/9 single-pass**; historical regressions are reported
separately. Six duplicate-pair rejections and false passage interpretations remain
open. **Disposition: revise; opt-in only.** No paid API calls, retries or default
changes. The [final preservation audit](receipts/passage-review/final-audit.json)
checks all 5,173 prior artifacts plus frozen sources, inputs and installed identities.
Native Windows/Linux, broader provider comparisons and total cost per verified
repair remain unqualified.

## Astra worker selection — 2026-09-15

The [dev8 receipt](astra-review-receipt.md) records Patrick's requested switch:
workspace lead and reviewer now select **gpt-6-astra / xhigh** through native Codex.
The adapter binds the reasoning setting to explicit CLI arguments, acceptance and
recovery; new review commands default to `./participants.json`. The fresh
`.venv-astra-review` environment has 24 installed modules matching source and a
byte-identical wheel rebuild. **780 tests, 35 installed review/recovery checks,
two installed profile checks and 7/7 targeted mutations pass; 13/22 new tests
detect at least one mutation.** Historical artifacts and old profiles are retained.

Automatic approval review blocked the prepared external smoke test pending explicit
approval of its synthetic document/reference payload to the signed-in Codex/Astra
service. **No Astra invocation ran; semantic accuracy remains unmeasured.** The
worker configuration is changed, while the live smoke test and matched quality
comparison remain outstanding. See the receipt for exact payload links and command.

## Astra native evidence repair and live test — 2026-09-15

Patrick's explicit build/test instruction resolved the prior approval block. The
first dev8 test used three Astra/xhigh calls and failed because the model shortened
the copied final response digest; its otherwise correct prose was rejected. That
failed run is retained. The [dev9 repair](native-evidence-review-receipt.md) adds
explicit evidence mode: the host schedules retrieve/verify and owns correlation;
each native role writes one review without copying the protocol envelope.

**798 tests, 35 installed review/recovery checks and 7/7 targeted mutations pass;
11/18 new tests detect at least one mutation.** A fresh offline dev9 environment,
`.venv-astra-evidence`, has 24 modules matching source and an identical wheel rebuild.
The revised live run completed both roles in **two Astra/xhigh invocations / 33.58 s**
on the same approved source bytes, for five calls total including the failed run.
Both narratives identify the critical conflict, preserve uncertainty and limit the
verifier's scope. No unsupported assertion was found in this one manually inspected
scenario; it is not a general accuracy score. The matched benchmark, independent
grading, human correction costs and cost per verified repair remain open.
