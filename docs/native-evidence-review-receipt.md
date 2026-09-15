# Astra native evidence review — dev9 receipt

September 15, 2026. **Build, software checks and one real two-role Astra review
passed. General review accuracy remains unqualified.**

Patrick explicitly requested building and testing the new Astra configuration
after the prepared payload and six-call approval question. Five native calls ran
in total: three in the retained failed dev8 run, then two in the successful dev9
run on identical document/reference bytes. No approval is pending for this work.

## What the live test found and what changed

The dev8 lead retrieved the reference and invoked verification successfully. Its
final review correctly identified the policy contradiction and preserved cost
uncertainty, but it shortened the copied request digest with an ellipsis. Harness
correctly rejected that response. The reviewer never ran.

The [dev8 failure](receipts/astra-review/live-01/summary.json), raw native responses,
original profile and installed artifact remain preserved. Its rejected prose is
not retroactively counted as an accepted review.

The [repair design](design-native-evidence-review.md) preceded the dev9 source edits:

- The workspace profile explicitly selects `review_mode: evidence` for both Astra
  roles. The host schedules retrieve, verify and final review within the accepted
  tool/turn budgets. Only the final step invokes the model.
- The model receives the complete document, distinct retrieved reference excerpts
  and scoped verifier findings. Request digests, action protocol and peer narratives
  are excluded from that evidence projection.
- The existing native exchange binds each invocation and reply. Host code creates
  the final action envelope and exact current-turn digest; the model never copies it.
- Incoming digest/history/budget checks, reference provenance, response limits,
  accepted-mode binding and conservative recovery remain enforced. Old native
  configurations without `review_mode` retain their original action protocol.

This was a new accepted run with a changed contract. There was no automatic retry,
silent repair of the bad returned digest, model fallback or credential workaround.

## Live result: one synthetic scenario

| Check | Observed result |
|---|---|
| Worker selection | Both invocations explicitly passed `gpt-6-astra` and `xhigh` |
| Workflow | Completed both lead and reviewer; four host evidence steps |
| Critical defect | Both identified that worker success cannot verify a repair when independent checks fail |
| Uncertainty | Both preserved the unmeasured possible cost benefit and did not label it a defect |
| Tool scope | Both stated that the verified link does not certify policy or model reasoning |
| Unsupported assertions found | Zero in manual inspection of these two narratives |
| Native invocations | 2 in the final run; 5 including the failed run |
| Final-run elapsed time | 33.58 seconds |

This is **one scenario with two role outputs**, not two independent benchmark
cases or a general accuracy percentage. The implementation author inspected the
narratives against the prewritten oracle; grading was unblinded. A matched direct
versus Harness benchmark with unseen cases and independent grading remains open.
The earlier Llama **2/36** result is unchanged and is not a matched comparator.

[Complete narratives](receipts/astra-evidence/live-02/summary.json) ·
[Audited prompts, identities, usage and exact judgment quotes](receipts/astra-evidence/live-02/audit.json) ·
[Frozen inputs](receipts/astra-evidence/live-02/freeze.json) ·
[Durable workflow record](receipts/astra-evidence/live-02/review/record.json)

Native session IDs and explicit dispatch arguments are retained. Codex JSONL did
not provide server-attested model/effort identity; no attestation is inferred from
the selected model or the model's prose.

## Software and installed-artifact checks

- **798 tests passed**, including **18 new cases** for host scheduling, correlation,
  evidence projection, invalid budgets/history, output limits and mode binding.
  [Full suite](receipts/astra-evidence/full-tests.txt)
- **7/7 targeted mutations detected; 11/18 new tests fail under at least one
  relevant mutation.** This is a targeted guard check, not an exhaustive mutation
  score. [Mutation evidence](receipts/astra-evidence/mutations-02/summary.json)
- **35 installed review/recovery checks passed**, including one external fixture
  effect and two local lead-transfer directions. These fixtures made no provider
  calls. [Review](receipts/astra-evidence/installed-review.json) ·
  [Recovery](receipts/astra-evidence/installed-recovery.json)
- All **24 installed modules match source**, the default profile loads in the
  installed CLI, and the dev9 wheel rebuilt byte-identically. The final
  [preservation audit](receipts/astra-evidence/final-audit.json) checks all **5,919**
  previously recorded artifacts, including the failed live run.

Two initial test runs exposed fixture mistakes (a wrong Task field name, then a
tuple/list comparison across JSON persistence). Those logs remain retained. The
corrected checks compare the real `requirements` field and canonical persisted
values. The final suite and mutation checks passed on unchanged production code.

Wheel: [attune_harness-0.1.0.dev9-py3-none-any.whl](../dist/attune_harness-0.1.0.dev9-py3-none-any.whl).
SHA-256: `5abc86f7dcec77946fc7ec2f118419f5d5c38437a397e4306bca79d147336af1`.
Use `.venv-astra-evidence/bin/attune-harness`; the older `.venv-astra-review`
preserves dev8. See the [current usage guide](astra-review.md).

## Cost and remaining limits

The final two calls reported 50,086 input tokens and 994 output tokens. Including
the failed run, the five calls reported 128,324 input tokens and 1,835 output
tokens. Reasoning-token counts are retained separately in the raw usage fields;
they are not added again to these output totals. Dollar cost, human correction
time and cost per verified repair remain unmeasured; this test performed no repair.

The native CLI reported shortened skill descriptions on both final calls. The
captured review prompt contains the complete synthetic input. Substantial native
session context remains a cost concern on this small task; global Codex settings
were not altered. Source matching, a passed smoke test and successful tool checks
do not authorize automatic document acceptance or establish broader semantic quality.
