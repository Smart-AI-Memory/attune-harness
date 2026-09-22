# Mixed-queue memory sorter results

Date: 2026-09-16. Status: completed disposable experiment; **revise the response
contract before promotion**. No production memory changes or plan/build execution.

Follow-up: the authorized [citation-contract comparison](memory-citations-results-2026-09-16.md)
is complete. On eight fresh paired cases, repaired Luna replies passed 8/8 on
the first attempt versus 2/8 under the old contract, avoiding six citation repair
calls. These later observations do not replace or regrade this frozen trial.

**Result:** Luna chose the intended operation and disposition and preserved the
required memory meaning on all **11 tasks it received**, under unblinded lead
grading. However, only **1/11** replies passed the host contract on the first
attempt. Ten escalations repaired a citation field rather than reasoning. The
current Luna-first implementation therefore did not demonstrate efficiency.
Keep Luna as the sorter candidate; correct the interface before adding routing
complexity or adopting the current implementation.

## What was tested

The [design](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_sorter/DESIGN.md),
[cases and rubrics](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/experiments/memory_sorter/cases.json), schemas, controller,
schedule and host profile were frozen before dispatch. Patrick authorized this
experiment after discussing Luna as the first-pass sorter and routine worker.

The queue contained 12 synthetic items: new capture, conditional correction,
cross-project nonduplicates, consolidation with an exception, exact forgetting,
node-kind classification, missing evidence, an unmade owner choice, decision
chronology, a complete policy calculation, an untrusted instruction transcript,
and ambiguous-prefix forgetting explicitly assigned to Astra by the host.
Eleven items went to Luna/high; that last assignment went directly to Astra/xhigh.
The assignment tests host policy enforcement, not whether ambiguity needs Astra.

Three cases also received direct Astra comparisons. Three actual queue outputs
received scheduled Astra audits. Four additional audit controls were hand-authored:
three wrong proposals and one correct missing-evidence result. Those labels and
all private expected answers stayed out of participant prompts. They are separate
from naturally produced worker replies.

Source review used existing Attune capture, promotion, forgetting and classification
seams without reading live memory content. Ambiguous-prefix forgetting is grounded
in `session_stash.forget_by_prefix`, which deliberately avoids ambiguous deletion.
The logical note/preference/lesson/decision kinds here do not qualify installed
adapter taxonomies or security sensitivity classification. Consolidation is a
proposed operation; this trial does not establish an existing consolidation API.

The [prototype](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/experiments/memory_sorter/sorter.py) constructs candidates
only. The host owns versions, granted IDs/scopes/kinds and current-state checks.
It rechecks task, record, evidence and grants, including after audits. No live
memory writes, real forgetting, index changes or decision-form integration occurred.

## Sorting and memory meaning

| Observation | Result |
|---|---:|
| Luna initial operation matches the frozen oracle | 11/11 |
| Luna initial disposition matches the frozen oracle | 11/11 |
| Luna initial core memory meaning passes source grading | 11/11 |
| Luna initial response passes host checks | 1/11 |
| Citation-contract escalations to Astra | 10 |
| Model-requested reasoning escalations | 0 |
| Incorrect requests for an owner decision observed | 0 |
| Final queue results pass after corrections | 12/12 |

Luna preserved conditions and exceptions, retained different project rules,
preserved both source references when consolidating duplicates, proposed only the
requested removal, and changed note kind without inventing a universal lesson.
It distinguished an accepted Thursday decision from a later unaccepted Friday
proposal, ignored the untrusted instruction transcript, requested the existing
missing attachment, and left the Quay/Cove choice to the owner.

Its calculation correctly yielded North 11 and South 8, retaining the independent
combined cap of 15 and owner approval for schema changes. The corrected budget,
effective date and expired temporary cap were applied correctly. Astra reached
the same supported values. No stronger-model reasoning rescue was observed.

One initial Luna classification reply had an empty explanation. Its proposed
kind change was correct; absence of an explanation is recorded separately from
an unsupported explanation. These judgments cover a small, deliberately selected
supplied-evidence set, not natural workload frequencies or an error-rate estimate.

## The contract caused avoidable extra work

All eleven Luna replies satisfied the emitted JSON schema. Nine had correct
fact-level source references but an empty top-level `evidence_ids` list. One
missing-evidence reply put the requested attachment filename in that list instead
of citing the supplied note that mentioned it. Only the owner-choice reply
satisfied the host's top-level reference convention on the first attempt.

The host requires nonempty, unique references to supplied source IDs. **The
schema did not enforce those constraints**, and the prompt did not expressly
state that the separate top-level list must be nonempty. The lead introduced
this mismatch in the expanded interface. Its rejection behavior is demonstrated;
the experiment does not isolate why Luna selected those values or establish a
general model deficit. The earlier v2 successes do not qualify this expanded
contract.

Astra supplied acceptable citation metadata while preserving the correct memory
meaning. These were policy-compliant contract escalations, not needed reasoning
escalations. The original failures remain in the ledger. The
[post-observation diagnosis](../receipts/memory-sorter-2026-09-16/contract-diagnostic.json)
does not patch, accept or regrade those replies.

The next correction should align the model-facing schema and instructions with
the actual source-reference rules, clearly separate a missing attachment from
available supporting sources, and assess whether the host can derive redundant
metadata from already supplied references. Do not silently guess citations,
weaken source checks or claim a live repair without a new frozen comparison.

## Audit detection

| Injected proposal | Audit result | Controller action |
|---|---|---|
| Drops the audit-equivalence condition while claiming preservation | Unsupported; identifies the dropped qualifier | Quarantined |
| Says no change despite an accepted replacement | Unsupported; identifies the false no-op | Quarantined |
| Asks the owner to allocate a pool even though the rules are complete | Unsupported; computes the supported limits and identifies false abstention | Quarantined |
| Correctly requests the absent finalized-decision attachment | Supported | Remains awaiting evidence |

The three actual sampled outputs were also supported, consistent with lead
grading. All three were **Astra outputs after contract repair**. No naturally
occurring semantic error was available to test detection, and these observations
do not establish the audit's detection probability or sampling rate. The three
injected detections were explicit diagnoses, not merely uncertain verdicts.
There were no false alarms among the three sampled outputs and one valid control.

## Calls, tokens and timing

| Segment | Calls | Input tokens | Output tokens | Native process seconds |
|---|---:|---:|---:|---:|
| Queue workers, including ten escalations and the host assignment | 22 | 124,588 | 6,035 | 342.36 |
| Three sampled queue audits | 3 | 19,216 | 908 | 54.71 |
| Three direct Astra comparisons | 3 | 20,173 | 1,352 | 69.28 |
| Four injected-control audits | 4 | 24,984 | 1,235 | 72.00 |
| **Whole campaign** | **32** | **188,961** | **9,530** | **538.36** |

The queue itself used **25 calls and 397.07 seconds including its audits**.
Across the three matched tasks, Luna-first workers plus corrections used six
calls and **101.22 seconds**, versus three direct Astra calls and **69.28 seconds**.
Including the scheduled calculation audit brings that Luna-first subset to seven
calls and **124.20 seconds**. Every matched final outcome was correct. Auditing
was not balanced between those arms; keep that overhead explicit.

Profiles were Luna/high and Astra/xhigh through Codex CLI 0.153.4 and the existing
ChatGPT subscription: 11 Luna and 21 Astra calls. The trial stayed within its
33-call and 1,800-second limits. No native boundary failure or automatic transport
retry occurred. All calls produced one agent message and the same three known
host warnings. No direct API charges, Voyage/Anthropic calls or credential changes
were made.

Reported cached input was 4,608 tokens and reasoning output was 5,774 tokens;
these are usage subfields, not additions to total input/output. Cache differences,
single observations and model/effort differences prevent an isolated timing
claim. Process durations exclude design, code review, offline checks and lead
grading; they do not measure first useful finding, first visible form, human
response time, full project effort or subscription dollar savings.

## Verification and remaining boundary

**114 offline tests passed**: 56 new checks and 58 inherited checks. Read-only
review identified a host gap before freezing: removing the last fact bypassed
scope/kind validation because only remaining facts were checked. The prototype
now checks removed targets too; both negative cases pass centrally. Other checks
cover current-state drift, restricted changes, one-hop escalation, no escalation
for evidence/decisions, audit quarantine and native stop/cap/deadline behavior.
The [verification receipt](../receipts/memory-sorter-2026-09-16/offline-verification.json)
records the command and pre-freeze corrections.

All 13 current frozen source hashes matched after the run. The three preceding
campaigns' frozen sources, protocols, ledgers and all 49 native receipts matched
their saved hashes. Grading is explicit, source-based and **unblinded by the lead**;
the source/design reviewer did not independently grade live outputs.

Continue with Luna as a candidate for bounded sorting and routine work. The
immediate defect to address in this prototype is the citation contract, not
observed inability to perform these eleven tasks. Correct it before qualifying
economics or adding another router. Installed taxonomy mapping, actual storage
concurrency and deletion, security classification, retrieval/context refresh,
natural confident-error detection, representative workload frequencies and
active-lead delegation remain unqualified. Production remains unchanged.

Evidence: [protocol](../receipts/memory-sorter-2026-09-16/protocol.json),
[ledger](../receipts/memory-sorter-2026-09-16/ledger.json),
[lead grades](../receipts/memory-sorter-2026-09-16/grades.json),
[aggregation](../receipts/memory-sorter-2026-09-16/analysis.json),
[analysis script](../receipts/memory-sorter-2026-09-16/analyze.py).
Raw receipts remain local under the existing ignore policy.
