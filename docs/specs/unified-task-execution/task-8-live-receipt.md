# Task 8 native qualification receipt

September 16, 2026. **The original 60-trial comparison finished; it exposed a repair-review contract defect. The corrected artifact passed all eight targeted native repair cases. The subsequent [assistant grading](task-8-assistant-grading.md) records 48/60 original and 8/8 corrected completed-correct outcomes; the original quality ruling is revise, and Task 8 remains unaccepted.** No assistant-generated labels are represented as human grades.

## Original comparison

Patrick authorized Task 8 and use of added credit, then explicitly selected the existing Claude subscription. The original API attempt returned HTTP 400 `Credit balance is too low` before inference, reporting zero tokens and $0. This describes the configured key’s response at that time, not Patrick’s overall Anthropic funding. He subsequently clarified that Claude is funded. The failed attempt remains preserved; no further API diagnostic or credential replacement ran.

Removing `ANTHROPIC_API_KEY` only from the subprocess environment exposed the existing claude.ai Max login through normal keychain access. Persistent configuration and credentials were not changed. Codex used explicitly authorized ChatGPT credits. The initial stated estimate was $6–15 for API-billed Claude plus 100–400 Codex credits; the selected subscription route instead consumes Claude quota. No new Claude API reservation remains allocated.

The subscription protocol, `a4f1db837afe6df041c6ca1af43989a7125c01f14caceaaf6e3a1250719a6a68`, retained the original cases, models, settings, order, runner, artifact and cache rules, adding an explicit billing amendment and reference to the failed API attempt. Candidate wheel SHA-256: `48e9af5c9877f2f1e8f1ebb39724203787a8fe9b740dfd0fcd5fd4e6ce5f6a15`.

| Slice / arm | Trials | Runtime completed | Probe passed | Native calls | Median seconds |
|---|---:|---:|---:|---:|---:|
| Assessment: legacy | 12 | 12 | Not a repair | 24 | 29.47 |
| Assessment: solo | 12 | 12 | Not a repair | 12 | 16.04 |
| Assessment: independent review | 12 | 12 | Not a repair | 24 | 29.29 |
| Repair: direct | 8 | 8 | 8 | 8 | 14.67 |
| Repair: solo | 8 | 8 | 8 | 8 | 14.01 |
| Repair: required review | 8 | 0 | 8 | 16 | 32.12 |

All **60 trials and 92 calls** completed their planned execution: 52 runs completed, eight failed acceptance. No trial was dropped, retried automatically or replaced. Interrupted cases resumed within the same assignment count. These are runtime/probe observations, not completed-correct semantic grades or a population performance estimate.

Every required-review failure had the same shape: the immutable probe passed, the independent reviewer returned `approve`, and explanatory positive findings remained nonempty. The validator requires empty findings for approval, but the prompt did not explain that findings must be blocking issues only. The original required-review path therefore needs revision; passing code probes did not justify overriding its review obligation.

## Observed usage and limits

| Requested model | Calls | Reported input | Cached input/read | Cache creation | Output |
|---|---:|---:|---:|---:|---:|
| Claude Fable 5.1 | 30 | 60 | 83,992 | 421,366 | 22,238 |
| GPT-6 Astra | 46 | 924,333 | 308,480 | Not reported | 21,119 |
| GPT-5.6 Sol | 16 | 305,216 | 130,048 | Not reported | 6,630 |

Codex input includes its cached-input subset; Claude reports cache reads/creation separately. Claude reports $9.560818 in model-use metadata, which is **not a verified subscription charge**. Codex billed cost and human correction time remain unknown. Applying current standard credit rates to observed Codex token categories estimates approximately 210.21 credits for this comparison; that is not an account billing reconciliation. Account-wide credit changes also include this coordinating conversation and cannot be attributed entirely to the experiment.

Rates checked before dispatch: [Claude Fable](https://platform.claude.com/docs/en/models/fable-5-1/overview), [Codex](https://learn.chatgpt.com/docs/pricing). Host template caches were cleared per trial, and response reuse was limited to the same resumed assignment. Provider cache states varied and are disclosed above; no controlled warm-cache economic ranking is claimed. Fable’s returned model IDs matched the request. Codex reports its session and requested CLI model/settings, but these receipts do not authenticate the backend model identity independently.

## Correction and separate follow-up

The [correction note](task-8-review-contract-note.md) preceded the code change. The prompt now defines findings as blocking defects/material uncertainty, explicitly requires `approve` with `findings: []` when there is no blocker, and excludes positive summaries/nonblocking scope caveats. It does not relax the validator, digest binding, file/probe protections or review requirement.

**178 existing software tests passed** across intake, assessment, repair, effects, recovery and compatibility. A fresh `.venv-task-reviewcontract310` passed dependency checks and the 22-process independent installed qualification; all 41 modules matched source and wheel. New wheel: `dist/task-execution-review-contract/attune_harness-0.1.0.dev13-py3-none-any.whl`, SHA-256 `15863d6be372f06c94fe009fd87aa299512352354e0b53be52e54c6262e6633c`. The original installed environment and artifact remain intact.

The announced follow-up freezes only the eight required-review repair cases, in original relative order, with unchanged sources/models/settings. It permits at most 16 calls, four Claude and twelve Codex, under the same authorized billing routes. Protocol SHA-256: `e94cdbae0115842fe53b715767144059a907365a05f6a8c2d26150c4cc80ed5a`. This is targeted correction evidence, not a new full 60-trial comparison. Follow-up outcome: **8/8 completed, 16/16 calls, eight failed-before/passed-after probes and eight digest-bound approvals with empty findings.** Both lead/reviewer families and interrupted repairs passed. The original eight failures remain unchanged. Observed Codex tokens imply approximately 26.10 standard credits for the follow-up, or 236.31 across both native runs; billing reconciliation remains unavailable. Follow-up median elapsed time was 29.39 seconds; this is not a controlled speed comparison.

## Evidence and acceptance boundary

Local receipts under `docs/receipts/unified-task-execution/`:

- Original rejected API attempt: `task8-frozen-protocol-qualified/ledger.json`, its retained `runs/`, and `task8-live-admission-note.json`.
- Full native comparison: `task8-subscription-live/{protocol,freeze,ledger,mechanical-summary}.json`, all `runs/*/{native-*.json,result.json}`, and `task8-subscription-execution.log`.
- Correction: `task8-correction-suite.xml`, build/install logs, `task8-correction-installed/summary.json`, and `task8-review-contract-live/`.
- Human review: `task8-subscription-live/blind-packet.json`, `grades-template.json` and `blind-redaction-receipt.json`. Withhold mapping and pre-redaction files from graders. [Grading guide](task-8-grading-guide.md).

Assessment has demonstrated native execution on the recorded profiles; supplementary assistant grading now finds four assessments with unsupported allegations. Independent human grading selected by the frozen protocol remains pending. Repair has demonstrated actual effects/probes and revealed the original review-contract failure; judge the corrected follow-up separately. Unknown billing/human time remains unknown. No full-spec acceptance or economic superiority claim follows from runtime completion.
