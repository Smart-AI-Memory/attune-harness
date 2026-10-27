# Evaluate human and AI performance in a Harness workflow

**Status: proposed protocol; no study runs or participants collected.**
Patrick approved the priority: higher token use is acceptable when it improves
human or AI performance. Collection details, implementation gaps and any model
budget still require approval. This is a new prospective evaluation, not a
rescore of the retained Forms pilots.

## Question and decision order

Does a Forms-assisted Harness workflow help people and AI complete the right
work more reliably or with less human effort than a conversational workflow?

Evaluate in this order:

1. Preserve safety and explicit authority. Never exchange a privacy violation,
   unauthorized effect or stale acceptance for speed, correctness elsewhere or
   token savings.
2. Measure correct authorized completion and human and AI performance.
3. Compare token use, elapsed waiting time and other resource costs for those
   outcomes. A higher token count does not by itself make a condition worse.

Do not collapse these dimensions into an invented weighted score. Report both
the benefit and its cost, including cases where one participant benefits while
the other does worse.

## Measures and evidence

The evaluation unit is one assigned person–task attempt, including its retries,
corrections and any abandonment. Model calls are not independent participants.

| Priority | Measure | Operational definition and source |
| --- | --- | --- |
| Primary joint outcome | Correct authorized completion | Before the declared time limit, the final artifact passes every required independent criterion, matches the latest accepted intent and has no observed authority/safety breach. Evidence: protected checks, owner revisions, effect receipts and observer record. A model's completion statement is insufficient. |
| Primary human outcome | Active human effort | Minutes spent reading, deciding, entering, correcting and inspecting, from timestamped observation with consent. Record system waiting separately, including overlapping active work; do not infer effort from tokens, clicks or chat length. |
| Human guardrails and diagnostics | Understanding, mistakes and recovery | Before execution, ask the person to state effective scope and whether work is authorized to start. Score against a frozen rubric. Record materially wrong decisions, omitted requirements, corrective interventions, repeated questions, abandonment and a brief post-task effort rating. Record comprehension prompts identically in both arms. |
| Primary AI outcome | First-pass artifact correctness | Fraction of assigned attempts whose first produced artifact passes every frozen task criterion before repair. Attempts producing no artifact do not pass. Score filter preservation, page scope, excluded private data and valid CSV independently as diagnostics. Record unsupported assumptions, superseded choices used, failed checks and repair attempts, including failures the human catches. |
| Secondary costs | Tokens, calls and waiting | Record input, output and cached tokens separately where exposed; include failed calls and retries. Separate interaction, planner, worker, reviewer and research-evaluator usage. Record latency and total elapsed time. Missing usage is unavailable, never zero. |

Report denominators and task-level results for every assigned attempt. Report
completion and active effort together: early abandonment can look fast, while
reporting time only for successes hides difficult failures. Show successful-task
time as a conditional diagnostic, alongside all-attempt effort, failure and
time-limit outcomes. Do not replace missing durations with the time limit.
Dollar estimates are optional and require recorded dated prices and billing
rules; tokens are not dollars. Cost per successful task includes costs of failed
attempts and is undefined when no task succeeds.

## Fair comparison

Use two conditions in the same named host and installed Harness candidate:

- **Chat:** natural conversation. The assistant may infer supplied facts, ask
  only material missing questions, accept corrections and summarize scope.
  Do not force one question per turn or weaken chat to favor forms.
- **Forms-assisted:** the same task and assistant policy, with the real supported
  Forms presentation for unresolved decisions and review. Preserve open-text
  answers and corrections; unsupported controls use a recorded fallback.

Both conditions use the same authoritative Harness owners, validation, explicit
acceptance, execution permissions and protected checks. If a mandatory shared
approval control is required by the owner, use it in both conditions and label
the claim as an intake comparison, not an entirely form-free workflow.
Do not give chat the form's UI-specific response schema just to simplify scoring.
Do not withhold task facts or semantic constraints from either arm. Log the
actual messages so differences in assistance can be inspected.

Hold model/version, role assignments, tools, system instructions, sampling
settings when configurable, time and retry budgets, starting repository state
and task difficulty constant. Record unavailable settings rather than claiming
control. Start a fresh model context and disposable checkout for each attempt;
do not carry solutions between arms. Record context/cache policy.

Use equivalent task variants and randomize/counterbalance both condition order
and variant assignment within participants. Give equal practice and instructions.
Do not ask a person to solve the identical task twice and attribute learning to
the UI. Record experience and accessibility needs; retain keyboard-only cases.
Participants cannot be blinded to the UI, but artifact assessors should receive
condition-neutral IDs and only the evidence needed for scoring.

The previous [72-unit simulated pilot](https://github.com/Smart-AI-Memory/attune-forms/blob/4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7/docs/specs/outcome-experiment/outcome-pilot-v0.2-results.md)
used deterministic replies and a shared structured action envelope. It did not
measure human benefit. Reuse its lessons, not its success ceiling as evidence
that the new human conditions are equivalent.

## Concrete task: filtered CSV export

Use a small disposable application checkout containing synthetic reports,
pagination, active filters and private-note fields. No production data or remote
effects. Implementing this fixture and instrumentation is separate work.

Give the person this request:

> Add CSV export to reports. Keep the active filters and exclude private notes.

Keep the initial page/all-records decision unresolved. Give the person a task
card directing an initial choice of all matching records, followed by a change
to current page before approval. This is a standardized correction challenge,
not an estimate of how frequently real users change their minds. Do not dictate
their answer wording or let an agent impersonate the human.

1. **Prepare.** Freeze a fresh application snapshot, synthetic data, authorized
   output paths and protected verification. Prepare an unaccepted Harness work
   request with the known constraints and one missing material decision. Keep
   task storage, configuration and observation files outside the effects checkout.
2. **Clarify and correct.** Collect the person's choice through the assigned
   condition, then their correction. Record displayed text, actual reply, saved
   revision and elapsed/active time. Verify that current page replaces all
   matching records in effective intent and affected tasks/checks, while history
   retains the old choice. Count re-asked settled facts and moderator assistance.
3. **Review and accept.** Ask the same short comprehension questions in both
   conditions. Let the person inspect scope and make an explicit decision using
   the required trusted collector. A saved answer or clicked review disclosure
   is not approval. Intent acceptance does not grant model dispatch or effects.
4. **Execute.** Only after separate collection/budget authorization, run the real
   configured planner if needed, worker and reviewer through Harness. Bind any
   staged plan to its current checkpoint and obtain required acceptance before
   build. Preserve the accepted task's effect manifest and protected oracles.
   Use identical permitted repair policy in both conditions; no silent rescue.
5. **Check the artifact.** Run protected checks for exact row IDs from the
   corrected current page, active filters and order; no off-page/unmatched rows;
   no private-note columns or values; correct headers and CSV round-trip for
   commas, quotes, newlines and Unicode; and empty-result behavior. Freeze
   expected outputs for each variant before collection. Check allowed effects
   separately. A worker-written test is not the independent oracle.
6. **Inspect completion.** Have the person use current `status` evidence to
   explain what completed, what was checked and what remains uncertain. Score
   comprehension against retained evidence. The proposed one-action results
   summary is not assumed to exist; testing it requires its own qualified build.

Also include a fully specified variant where no clarification is needed and a
simple one-question variant without the correction challenge. Analyze them
separately: a form should not receive credit for adding unnecessary interaction.
Handoff, cancellation and stale-response refusal are separate qualification
cases after the same-host comparison, not confounded into its primary result.

### Command outline, not a runnable fixture

Use one explicit candidate environment. Check its installed `--help` and package
versions first. These commands follow the [CLI guide](../../cli-guide.md#plan-and-build)
and [owner refusal walk](README.md#proposed-workflow-owner-refusals-and-input-flow).
Paths and checkpoints below are placeholders. `work.json` must be constructed
with the real schema, frozen effects and protected verification described in
[dependent build](../plan-build/dependent-build.md) and `scripts/check_installed.py`;
the CLI does not generate that manifest. A default review registry is not a
proposal-capable build registry.

```sh
attune-harness plan --request /study/run/work.json \
  --project /study/run/app --config /study/run/participants.json \
  --task-dir /study/run/task

# Forms condition only: the same environment's Python; no build commands.
python -m attune_harness.gui --task /study/run/task --edit --launch-json

# After answers/corrections and the required actual human acceptance decision:
attune-harness plan --task-dir /study/run/task \
  --accept --checkpoint CURRENT_CHECKPOINT

# Only with separately authorized external calls and accepted build scope:
attune-harness build /study/run/task --allow-external --max-operations 4
attune-harness status /study/run/task --format markdown
```

The GUI listener stays in a separate retained process. Open only its validated
private loopback launch URL; never include its capability token in study exports.
Do not repeat CLI acceptance if the GUI already accepted the current revision.
Native participants additionally require explicitly authorized `--allow-native`.
The illustrated four-operation boundary can pause a build; it does not establish
completion. Inspect the record before any separately permitted continuation.
Missing decisions, incompatible registries, unsupported corrections or uncertain
effects stop the attempt at that boundary; never edit records to bypass it.

## Pilot, analysis and decision rules

First qualify the installed software seam with deterministic fixtures, then run
an authorized exploratory pilot with actual people. A single Patrick walkthrough
is useful for finding confusion, not a population-level superiority claim.
Use the pilot to assess feasibility, measurement reliability and variance, not
to select favorable endpoints after seeing results. A subsequent confirmatory
study needs its own frozen protocol and sample-size rationale.

Before the first human/model attempt, record the protocol revision and approval,
participant population/count, task variants/repeats, randomization seed,
configured roles/models, settings, budget, time limits, allowed assistance and
stopping rules. Predeclare exclusions, fallback classification, missing-data
handling, primary endpoints, meaningful improvement thresholds, non-inferiority
margins and analysis method. These numeric choices remain open; this document
does not pretend they have been ratified. Keep assigned-condition analysis
primary even if forms fall back to chat; report actual-surface analysis separately.

Report paired differences and uncertainty, accounting for repeated tasks within
people and variants. Do not treat 42 calls or 72 simulated units as 42 or 72
independent human participants. Report technical failures and abandonment in the
assigned attempts; distinguish them from unobserved human measures. Exclude only
under the frozen rules, with counts and reasons. Never replace a failed attempt
silently. Retain disagreement between assessors and its adjudication.

A comparative benefit requires a predeclared meaningful improvement in human
effort, AI first-pass correctness or correct authorized completion, with the
other primary outcomes and comprehension/error guardrails within predeclared
non-inferiority limits. Designate the claim-driving endpoint before collection.
If a confirmatory study permits multiple primary endpoints to support the claim,
freeze its multiple-testing procedure. Better AI first-pass performance can
justify extra tokens even if final completion is unchanged; it cannot erase
worse human outcomes outside the agreed margins. Mixed results remain tradeoffs,
and inconclusive evidence remains inconclusive—not equivalence.

An observed critical privacy/authority failure triggers a pause and investigation
under the frozen stopping policy; a condition cannot win by averaging it away.
Zero observed failures does not prove safety. Extra tokens are acceptable when
performance meets the declared rule and the separately approved cost ceiling.
Cheaper tokens without performance benefit support only a cost finding.

## Evidence and prerequisites

Store a new append-only campaign outside retained experiments. Keep protocol and
approval, source/package/host versions, registry and fixture hashes, allocation,
de-identified task events, observed human times, transcripts, revision/checkpoint
receipts, protected-check output, final artifacts, usage and scoring records.
Bind files with a SHA-256 manifest. Corrections append a new attributed record;
hashes establish byte integrity, not truth or legal admissibility. Restrict raw
human recordings and launcher secrets; publish only separately authorized,
redacted evidence with documented omissions.

Collection remains blocked until these prerequisites are complete:

- A qualified installed candidate and observed chat/forms paths through the same
  owner, including correction and acceptance; no claim that T2–T4 already shipped.
- A disposable CSV fixture, frozen oracles and instrumentation that observes
  human effort without substituting synthetic answers.
- Approved participants, consent/retention arrangements, primary margins,
  allocation/sample plan, stopping rules, configured model roles and budget.
- A recorded precollection ruling binding those items to this protocol revision.

## Completion review of this planning update

The goal is better human–AI work, not fewer tokens in isolation. The user and
next-step lenses sharpened existing J4: shared validation can make a simulated
comparison look equal while leaving comprehension and correction cost unmeasured.
J4, R7 and T5 now point to prospective direct observation and artifact checks.
No duplicate opportunity-log entry is needed. The first user-visible test is
whether the corrected page choice survives review and the actual exported file.
Fixture implementation, installed qualification and human outcomes remain open.
This planning review is complete; it grants no execution or publication authority.
