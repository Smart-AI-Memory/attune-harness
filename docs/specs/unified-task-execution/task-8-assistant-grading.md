# Task 8 assistant outcome grading

Patrick requested proceeding to outcome grading after declining a repeat run. This pass grades retained outputs using the current assistant; it launches no provider calls. It is a supplementary assistant evaluation, not the human grading selected by the frozen protocol. The grader has prior knowledge of the study and the discovered repair failure, so anonymized packet IDs do not make this an independent blinded study. Original protocols, responses and the human template remain unchanged.

Apply the existing rubric before writing labels: successful execution plus substantive source/probe correctness for completed_correct; a missed material contradiction or unresolved seeded code defect for critical_miss; distinct unsupported defect allegations for unsupported_findings. A truthful limitation or positive explanatory finding is not itself an unsupported defect. A repaired file rejected by the review contract fails completed_correct even if its probe passes; that execution failure alone is not a missed code defect. Human correction seconds remain null.

All 36 assessment records were read against their document/reference, including both narratives where present. All 24 original and eight corrected repair patches were read against their source/oracle and review responses. Original labels and rationales were saved before opening the original blind-key mapping in this grading pass. This procedural ordering does not remove the grader's prior knowledge.

## Outcome

**Original comparison: revise.** The unchanged auditor reports **48/60 completed-correct, zero critical misses, six unsupported defect allegations**, and failed quality floors for both assessment and repair. The separate corrected repair follow-up grades **8/8 completed-correct**, with zero critical misses or unsupported allegations. It does not replace the original eight failed executions.

| Original slice / arm | Claude-lead correct | Codex-lead correct | Unsupported allegations | Matched quality floor |
|---|---:|---:|---:|---|
| Assessment / legacy baseline | 6/6 | 5/6 | 2 | Baseline |
| Assessment / solo | 4/6 | 6/6 | 3 | Fails on two Claude-lead cases |
| Assessment / independent review | 6/6 | 5/6 | 1 | Meets this set's baseline |
| Repair / direct baseline | 4/4 | 4/4 | 0 | Baseline |
| Repair / solo | 4/4 | 4/4 | 0 | Meets this set's baseline |
| Repair / required review, original | 0/4 | 0/4 | 0 | Fails on all eight cases |
| Repair / required review, corrected follow-up | 4/4 | 4/4 | 0 | Targeted pass; separate artifact, no fresh baseline |

Assessment totals are 32/36 completed-correct; original repair totals are 16/24. Every material seeded assessment contradiction was identified, and every original repair corrected its seeded defect. Eight original repairs nevertheless failed their required review contract: approval contained positive explanatory findings, which the unchanged strict validator correctly rejected. Those positive findings are not false defect allegations.

## Semantic deductions

| Original blind ID | Unblinded trial | Unsupported allegations | Reason |
|---|---|---:|---|
| `e2cba0aee27c8839f52f` | critical-retention / Claude-lead / solo | 1 | Correctly finds the retention contradiction, then labels missing date/version/source as a separate defect without an established metadata requirement. |
| `716a7c94815d3717e6b7` | qualified-exception / Claude-lead / solo | 2 | Labels compatible legal-hold and deletion wording as two concrete defects. |
| `40a3bc44dd0731cd4561` | qualified-exception / Codex-lead / legacy | 2 | One narrative correctly retains compatibility; the other alleges the same two concrete defects. Both are returned to the user. |
| `1e62da5db5461f1f6dc4` | qualified-exception / Codex-lead / independent review | 1 | One narrative calls the legal-hold exemption a concrete overbroad defect despite its compatibility with the reference. |

Exemption from the ordinary 14-day retention rule does not assert indefinite retention after a hold is released. In this fixture, ordinary logs “last 14 days” reasonably supports the guide's deletion paraphrase; the source does not establish an alternative archive requirement. Asking to include “until release” or clarify deletion is reasonable. Presenting those differences as established defects is the deduction. A correct companion narrative does not erase an unsupported allegation left in the delivered assessment.

These are assistant judgments, with a real boundary between a defect and a precision suggestion. For example, `913fb58eaaccc697f599` explicitly treats the same gaps as compatible/uncertain, so it receives no deduction. Records `c5f09b11d4c7661a1357` and `8d996215667dc215c9ab` use loose conflict wording but explicitly preserve unknown geographic placement and say Europe is not proven false; they pass. Source/link checks still do not certify semantic accuracy.

Sensitivity: forgiving only the extra metadata allegation raises the original total to 49/60, but the Claude-lead qualified-exception regression still fails the assessment floor. Treating all six disputed allegations as acceptable suggestions raises it to 52/60 and passes the assessment floor; the original repair floor still fails. These alternatives are not substituted for the recorded grades. The frozen six-case assessment set is too small, and this evaluation too dependent on the implementing assistant, for a general model-quality ranking.

Two original empty-default patches (`3a8d9f2a0353dcff88b8`, `56dcc94a1e1ced8d7709`) use truthiness. They satisfy the frozen empty/nonempty-string oracle and preserve None, but also change behavior for other falsey inputs such as 0 and False. The frozen contract does not specify those inputs; these grades qualify only the stated repair scope, not a general-purpose replacement.

## Evidence and checks

Tracked grading artifacts contain every original/follow-up ID, including failures, and every per-record rationale:

- [Original 60 grades](assistant-grading/original-grades.json), [rationales](assistant-grading/original-rationales.json), [unchanged auditor result](assistant-grading/original-audit.json).
- [Corrected eight grades](assistant-grading/follow-up-grades.json), [rationales and result hashes](assistant-grading/follow-up-rationales.json), [targeted evidence check](assistant-grading/follow-up-audit.json).
- [Grader provenance and file hashes](assistant-grading/provenance.json).

The original auditor ran successfully with the original installed environment and returned `revise` as the quality decision, not an integrity error:

```sh
.venv-task-repair-final310/bin/python -I experiments/task_execution/campaign.py audit docs/receipts/unified-task-execution/task8-subscription-live --grades docs/specs/unified-task-execution/assistant-grading/original-grades.json
```

The original protocol, runner, wheel, installed module identity, complete ID set, anonymous mapping and retained result hashes passed the auditor's checks. Separately, all **941 original, 212 follow-up and 11 rejected-API-attempt retained files** still match their existing manifests, including the untouched human template. The corrected installed environment verified its own protocol identity. The follow-up check verified all eight retained result hashes, immutable oracle hashes, final replacement bytes and artifact/probe-bound approvals. The full comparison auditor is not used for that packet because it contains no direct/solo baselines; its matched comparison logic was not weakened.

No runtime edits, provider invocations or reruns occurred during grading. Billed dollars and human correction seconds remain null. Existing token/latency receipts remain descriptive; they establish no cost ranking or improvement under matched provider-cache conditions.

## Slice decisions

**Assessment:** retain the accepted software qualification; do not promote every native assessment plan as meeting the quality floor. The tested independent-review arm matches its legacy baseline on this set, while Claude-lead solo regresses on two cases. A future evaluation should distinguish optional precision suggestions from evidence-supported defects on fresh material, rather than tuning and retesting against these now-known cases.

**Repair:** retain the accepted software qualification and the bounded 8/8 corrected required-review result. The original 60-case record remains a failed comparison; the new artifact has targeted requalification, not a fresh full comparison or universal repair guarantee.

**Task 8 remains current and unaccepted.** This requested outcome-grading pass is complete. Human-only grading was selected by the frozen campaign protocol, not imposed by the approved spec itself; this supplemental assistant pass does not silently amend that protocol or impersonate its human grader. Independent human grades, measured human effort and verified billing remain unavailable. Final acceptance must address the recorded quality regression and qualification limits; missing cost measurements block economic claims rather than becoming invented zeroes.
