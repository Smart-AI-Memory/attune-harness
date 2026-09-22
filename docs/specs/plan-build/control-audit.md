# Control audit — plan and build

Status: **scoping evidence and proposed design, not executable**. Dated
2026-09-16. This is a bounded audit of the mechanisms relevant to plan/build,
not a complete security audit or qualification of every model and host.

## Purpose and baseline

Patrick's direction is to account for models' training when designing grammar
and safety/quality constructs, then reimplement controls for effectiveness and
reliability. The agreed approach is to inspect and measure the existing controls,
preserve those that work and replace weak mechanisms. A wholesale rewrite is not
the starting assumption.

Training matters here as learned response behavior: which instructions, tool
interfaces, examples and feedback a model follows reliably. The audit treats
these as hypotheses to test on each supported model/host profile. It does not
infer a model's training data or a causal training explanation from an output.
Fine-tuning is not required for this work.

Local Harness HEAD: `fc65e74fc7c289f71f3a7d081dfe7c1be1238c33`.
Attune AI reference HEAD: `fe08f282fb0ad9cbb7eedf75af2597336576578e`.
Forms reference HEAD: `976bf91a1b33f2d7a4072beb68fd941861e3f15d`.
Harness retains the unrelated and navigation changes listed in [baseline.md](baseline.md).
Sibling projects are read-only references; their source does not establish what
is installed or active in a user's host.

## Inspected mechanisms and disposition

| Mechanism and source | Observed responsibility or limit | Proposed treatment |
|---|---|---|
| Grammar definitions and host rendering: `attune-forms/src/attune_forms/host_question.py` | Profile limits, admissibility and answer bindings are explicit; the consumer owns decoding, deadlines and receipts | Preserve shared grammar semantics; qualify each real host round trip and model's choice of construct separately |
| Host formatting: `attune-ai/src/attune/elicitation/ask_payload.py` | A helper adds host-specific recommendation labels and form metadata; these conventions are separate from shared form semantics | Adapt at the host boundary; verify that confirm decisions retain their own semantics instead of applying recommendation conventions universally |
| Host response timing: `attune-ai/src/attune/elicitation/host_question_adapter.py` | The declared deadline is advisory at this layer; the transport implementation must enforce it | Name and test the enforcing owner; a declared timeout alone is not an enforced timeout |
| Hook dispatch: `attune-ai/src/attune/hooks/scripts/security_guard.py`, `_sdk_gate.py` | Tool-name matching and session mode affect coverage; the guard explicitly allows missing/unrecognized tools, and its entrypoint permits parse errors | Do not transplant as a universal boundary; qualify event translation, actual invocation and error policy for each supported host |
| Task authority: `src/attune_harness/task_contract.py` | Explicit permissions, current evidence, task/form/checkpoint revisions and acceptance are validated; unchanged accepted answers do not need new approval | Preserve this behavior; extend it to plan/build revisions and applicable control configuration |
| Dispatch and effects: `src/attune_harness/task_runtime.py`, `repair.py` | Host code checks allowed tools, budgets and effects; repair protects scope, acceptance inputs and uncertain writes within its bounded POSIX profile | Reuse the enforcement and recovery design while qualifying the new create-file/build profile |
| Native participants: `src/attune_harness/native.py` | Prompt instructions accompany provider-specific CLI settings; the wrapper explicitly disclaims tool isolation and authenticated model identity | Record configured versus observed controls; qualify actual host behavior before claiming isolation or equal coverage |
| Lifecycle gates: `attune-ai/src/attune/gates/lifecycle/runner.py` | Gate receipts and exit codes report outcomes; the runner itself does not advance the phase | Preserve separate evaluation and transition authority; a caller must enforce required outcomes |

## Actual local observations

Pure calls to the existing `security_guard.main` produced:

| Input | Result |
|---|---|
| Missing tool name (`{}`) | Allowed |
| `Write`, `file_path=/etc/audit-sentinel` | Blocked |
| Unrecognized `apply_patch`, same synthetic `file_path` | Allowed |
| `Write`, `file_path=/Users/patrickroebuck/attune-harness/audit-sentinel` | Allowed |

These calls evaluated dictionaries only. No target file was written and no host
tool was dispatched. The unrecognized-name case demonstrates the function's
coverage boundary; it is not a real-host bypass test or a reproduction using an
actual `apply_patch` payload. The inspected hook source SHA-256 was
`4d6afc7b979b42ab4638461e6333d2b25bb9044a4d1423834d64c9946aed18b4`.

Seven selected existing test functions expanded to **31 passing cases** in
0.78 seconds using `.venv-token-accounting/bin/python -m pytest -q`:

- `tests/test_task_contract.py::test_invalid_response_leaves_draft_unchanged`
- `tests/test_task_contract.py::test_unchanged_answers_reuse_acceptance_without_reapproval`
- `tests/test_task_contract.py::test_changes_after_presentation_require_revision`
- `tests/test_task_repair_effects.py::test_real_failure_write_success_and_no_duplicate_write`
- `tests/test_task_repair_effects.py::test_invalid_patch_paths_never_write`
- `tests/test_task_repair_effects.py::test_changed_protected_state_and_stale_preimage_stop`
- `tests/test_task_repair_effects.py::test_partial_write_and_lost_ack_reconcile_without_second_write`

These establish a current local baseline for selected authority, effect and
recovery checks. They do not test model understanding, live host hooks, new-file
creation or the future plan/build commands. No production code, provider calls
or sibling project files were changed for this audit.

## Proposed implementation boundaries

1. **Define each control's contract.** Record its purpose, applicable operation,
   authoritative owner, host coverage, inputs, failure behavior and evidence.
   Keep advisory guidance, a blocking decision and unavailable enforcement
   distinguishable. Required controls must be checked before the dependent
   dispatch or effect, including after resume or a material revision.
2. **Adapt guidance to measured model behavior.** Compare concise instructions,
   examples and available native tool interfaces while preserving the same
   grammar and authority semantics. Model-specific wording belongs in a bounded
   adapter; the model cannot select a weaker permission policy. A corrective
   retry must have a budget and cannot repeat an uncertain effect.
3. **Enforce constraints outside model judgment.** Validate proposed actions and
   resulting artifacts through the shared runtime. Host hooks may provide early
   feedback or a required check where qualified; critical enforcement must not
   depend on the model remembering to invoke it. Reuse existing mechanisms before
   adding new machinery. Reimplement a weak mechanism with equivalent intended
   policy and evidence of improvement, preserving its old baseline and failures.

## Qualification design to freeze before trials

Use matched cases and unchanged acceptance criteria for the old and candidate
mechanisms. Change one relevant factor at a time where possible, then test the
combined path. Identify model/version, host/version, configuration, prompt/control
revision and actual observed execution for every case. Repeat runs to expose
variability; freeze sample size and acceptance floors before promotion.

| Property | Cases and measurements |
|---|---|
| Response meaning | Correct construct, preserved intent, substantive answer, genuine counter-case, no invented decision or approval; schema validity alone is insufficient |
| Model and context sensitivity | Same goal across supported models and interfaces; long context, conflicting evidence instructions and corrections; record failures without attributing a training cause prematurely |
| Human answer fidelity | Real supported surfaces preserve terse replies, cancellation, partial answers, explicit approvals and revision binding; defaults and silence do not create decisions |
| Enforcement | Missing/unrecognized event, unavailable/failed/timed-out required hook, unauthorized action, protected-input edit, stale decision and uncertain replay; observe actual effects, not only rejection text |
| Legitimate work | Valid operations complete, unchanged grants remain usable, advisory issues do not become unrequested approval gates; measure unnecessary blocks and user interventions |
| Reliability and cost | Repeatability, escaped failures, outcome correctness, corrective attempts, latency, calls/tokens and known spend, with retained raw failures and no aggregate score hiding a critical miss |

Deterministic checks establish contracts and enforcement; live model/host trials
establish behavior in the qualified profiles. Existing authorization requirements
for native/provider trials still apply. No maximum-effectiveness or universal
reliability claim is made from the source audit and 31 baseline cases.

## Latency: time to first useful finding or decision

Patrick suspects inspection and disposition mechanisms contribute to latency.
He located the observed delay **before findings or a decision form appear**.
The primary measurement is therefore request-to-first-useful-finding or
request-to-actionable-decision, with the full completion time reported separately.
A progress acknowledgement does not count as a useful finding. Human response
time and processing after submission are separate intervals.

Existing raw receipts establish two different local costs:

| Measured path | Observation | Limit |
|---|---|---|
| Small task-intake fixture, 30 samples per mode | Presentation medians: 2.081 ms cold, 1.842 ms warm, 2.120 ms bypassed | Python form construction/validation; excludes host transport, visible paint and model turns |
| Saved-provider retrieval through a shared session, 20 warm queries | 3.220 s mean total; 3.160 s in six generation checks | Local installed retrieval with copied completed provider stages; excludes live provider calls and answer generation |
| Same session path with final results cached | 2.660 s mean total; 2.644 s in five generation checks | Immediate warm replay, not a production optimization comparison |

Verified against the raw [intake summary](../../receipts/unified-task-execution/task2-intake-timing-final/summary.json)
and [retrieval timing](../../receipts/voyage-next-increment-2026-09-15/latency.json).
These are historical measurements of their recorded source/installed profiles,
not a new timing of this conversation or proof of its root cause.

The subsequent [research synthesis](../../research/control-and-latency-2026-09-16.md)
builds on these receipts and four primary sources. Its synthetic Forms 0.17.0
probe confirms that `workspace_latency` cannot distinguish zero from 30 seconds
of pre-render delay when render/acceptance events are otherwise identical. This
is the API's documented measurement scope, not a measured production delay.
Reuse existing Forms timing primitives while instrumenting the missing interval.

Current source also supplies two hypotheses to trace. Assessment assignments run
serially in `task_runtime.execute_assessment`; their contribution to the visible
delay depends on selected roles and the caller's presentation timing. The shared
command workspace constructs both HTML and Markdown, and validates an action's
current projection before creating/rendering its successor. Those costs and any
assistant/tool round trips need measurement; their presence alone is not a defect.

Instrument one correlated request through initial inspection, source/index
validation, hook execution, model scheduling/generation, result assembly, form
construction, transport and visible presentation. Count repeated checks and
assistant/tool turns. Preserve parent/child timing relationships so nested work
is not added twice. Distinguish work required before a useful result from work
required before execution or final acceptance.

Evaluate reuse only when evidence identity and the relevant mutation boundary
permit it. Evaluate concurrent independent checks or earlier presentation of
qualified partial findings without weakening the checks required for decisions.
Showing an unfinished finding must not expose approval of incomplete evidence.
Compare candidates in separate baseline/candidate processes with unchanged
correctness and stale-state tests. The existing Voyage validation-reuse work
remains separately scoped; this audit neither changes it nor claims its proposed
optimization is already implemented.

## Compatibility adapter reliability repair

Patrick authorized noting and fixing the `ask_payload.py` defects and exploring
`form_to_host_question`. Direct Forms 0.17.0 probes confirmed that the replacement
preserves neutral confirmations, consequences and answer bindings, but is not a
drop-in replacement for the old batching, fallback and return contract. The
personal format hook also rejects a neutral ordinary select, so a migration must
reconcile host policy without disguising it as a confirmation.

An isolated Attune AI fix is prepared on `codex/fix-ask-payload-reliability` at
`/private/tmp/attune-ask-payload-reliability-20260916`. It preserves confirmation
neutrality and context, removes injected multi-select recommendations, retains
rationale/notes, and isolates confirmation exemptions. Central verification:
319 passed, 3 expected xfails, 95.95% adapter coverage; restoring the baseline
adapter makes 7/18 focused cases fail with zero errors. Independent review found
no actionable defects. The branch's `docs/handoffs/codex-fix-ask-payload-reliability.md`
records the probes and limitations. The fix is uncommitted and not installed or
merged; broader migration and observed-latency attribution remain separate work.
