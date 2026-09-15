# Attune Harness: opportunities 1–5 implementation report

Date: September 15, 2026. Package: `0.1.0.dev11`. Model campaign: frozen dev10.

## Executive summary

The five opportunities now have implemented mechanisms, retained experiments and
explicit decisions. The private [GitHub library](https://github.com/Smart-AI-Memory/attune-harness)
is accessible and its native Windows, macOS and Linux qualification passed all six
OS/Python jobs. The outcome is a stronger development library, not a production
accuracy certification or a PyPI release.

**Latest steering:** Patrick selected Fable instead of Llama for the next worker
candidate. The [Fable 5.1 lead/Astra reviewer profile](fable-review.md) is configured
and checked offline. Live Fable qualification remains pending his Anthropic API
spending hold and first-spend authorization. Llama results below are historical;
they are not a recommendation to keep using it.

Keep Astra/xhigh for the current review team. Apply the measured 1000-token skills
catalog budget. Use deterministic rules for monitoring and escalation proposals.
Sol is promising for constrained repairs with independent checks; neither Sol nor
the tested Llama qualifies as the sole diagnostic or escalation authority.

The small matched review experiment found **no accuracy advantage from two Astra
roles over one**. The mixed team produced a false allegation despite its correct
Astra reviewer. Team membership alone does not resolve conflicting conclusions.

## Pros

### Reliability and GitHub

- Implemented Windows Job Object supervision with a gated bootstrap: the requested
  command starts only after assignment to the job. Native file locks release after
  process death; reparse-point lock targets are rejected.
- [Successful native matrix](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/34930971590)
  at commit `235137d673bb6582dad0c2993bd3bddcc03383bd`: macOS and Ubuntu each passed
  **369 tests per Python version**; Windows passed **355 per version**, including
  all nine Windows-specific cases. Python versions: 3.10 and 3.12. No skipped tests
  or provider calls in those six jobs.
- Full local suite: **850 passed, 9 Windows-only skipped** on macOS. Installed
  review/recovery consumers: **35 passed**, including one independently observed
  fixture effect. Tests exercise adapter fixtures; this is separate from model quality.
- Mutation checks detected **7/7 targeted changes**; **13/47 new focused-context,
  operations and GitHub tests fail under at least one mutation**. This denominator
  does not include the campaign or Windows-specific tests.
- The read-only GitHub importer consumed actual running, failed and successful
  check exports. Final export: all six checks passed; `repair_verified` remained
  false. It rejects stale revisions, incomplete pages and ambiguous identities.

### Measured review results

All three arms received identical host-projected evidence on eight frozen synthetic
cases, with one repetition. Calls used requested `gpt-6-astra` or `gpt-5.6-sol`,
`xhigh`, and a 1000-token skills catalog budget. Both team narratives must pass.

| Arm | Agreed passes | Agreed failures | Inconclusive | Review calls | Input tokens | Output tokens | Median workflow time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct Astra | 8/8 | 0 | 0 | 8 | 158,021 | 3,987 | 16.38 s |
| Astra lead + Astra reviewer | 8/8 | 0 | 0 | 16 | 317,682 | 7,758 | 32.20 s |
| Sol lead + Astra reviewer | 6/8 | 1 | 1 | 16 | 311,580 | 6,224 | 26.27 s |

Times include this campaign's sequential execution; they do not measure a concurrent
team. Reasoning tokens are already included in output totals. Grading and setup
calls are excluded from this table. The whole campaign used **60 native calls**
against its cap of 64 and **six local calls** against its cap of six.

A separate same-prompt Astra pair reduced reported input from **24,852 to 19,759
tokens**, a **20.49% reduction**. Both reviews were acceptable. Elapsed times were
15.83 and 15.73 seconds: one pair does not establish a latency or dollar saving.
The profile changes catalog description space, not user instructions, enabled
capabilities or runtime controls. The checked-in Astra profile now selects it;
older accepted runs require their original registry to resume.

### Narrow repairs and accounting

Sol passed all **three constrained JSON configuration repairs on its first
attempt**, using exact, type-sensitive independent host checks. No Astra repair
escalation was needed. These tasks preserved unrelated settings and corrected
retention, unknown-effect reconciliation and retry limits. They were not code repairs.

The repair ledger includes failed attempts, escalation, verification and human
correction. Missing costs stay unknown. The live synthetic ledger correctly returns
no dollar ranking because model charges, verification cost and human cost were not
recorded. Cost per verified repair is implemented as the decision measure; actual
comparative dollar savings remain unmeasured.

## Cons

- **Mixed-team review failed its promotion screen.** In case `u2`, Sol called Linux
  design intent a contradiction of macOS-only execution evidence. Those statements
  can both be true. Sol's grader and the author agreed that review failed; they
  disagreed on the number of unsupported assertions and the uncertainty flag.
- **One grade remains inconclusive.** For `m1`, Sol's grader treated “source conflict”
  as a false assertion; the author read the surrounding explanation as a supported
  statement that evidence was missing. Raw Sol scoring is 6/8 for the mixed team;
  author scoring is 7/8. The report does not convert the disagreement to a pass.
- Diagnostic exact-match scores were **Sol 5/6; Llama 3.1 8B 2/6**. Sol incorrectly
  called the cause proven after a failing independent check. Llama also overstated
  causal certainty and misclassified an unknown-effect timeout as infrastructure.
  These results support advisory use only. They do not justify automatic dispatch.
- Eight synthetic cases cannot establish production accuracy. A fresh Sol call
  audited the key and separate calls graded anonymous outputs. The implementation
  author graded all 40 anonymous narratives before reading those grades or role
  mapping. This is not an independent human audit; shared model errors, authorship
  and style clues remain limitations.
- The oracle audit questioned a link requirement because its packet omitted the
  rendered Markdown link. The actual evidence contained `[Policy](reference.md)`;
  inspection retained the original key. That audit-packet limitation is preserved.
- The context measurement still leaves roughly 20,000 input tokens for a tiny
  review. Native processes also retained optional connector startup warnings.
  Those connectors were not needed for the supplied-evidence tasks; no authentication
  settings were changed. Model identity is recorded from requested CLI configuration,
  not a provider-signed attestation.
- The [first native Windows run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/34930761748)
  failed on test fixtures: a shared 30 ms startup allowance and an oversized pytest
  parameter ID in the Windows environment. Both were fixed; the real timeout test
  retains its short deadline. Failed artifacts remain available. The earlier
  [dev10 baseline](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/34930444804)
  recorded native Windows execution as unsupported, not passed.
- Job Objects qualify ordinary descendant cleanup on these runners. They are not
  a security sandbox or evidence of remote-effect rollback, power-loss durability,
  network-filesystem locking or every Windows deployment configuration.

## Opportunities

| Requested opportunity | Implemented result and decision | Remaining evidence |
|---|---|---|
| 1. Frozen accuracy benchmark | Eight cases, matched arms, anonymous grading, retained author disagreement. Keep mixed review opt-in. | Larger held-out real documents, repeated runs and independent human grading. |
| 2. Reduce context overhead | Validated optional budget; same-prompt measurement; 1000-token budget applied to Astra profile. | Broader workloads and repeated latency/cost measurements. |
| 3. Qualify cheaper/local workers | Six log cases per model, three Sol repairs, deterministic routing API. Advisory diagnosis only. | Real code/test repairs and separate documentation-update qualification. |
| 4. Cost per verified repair | Strict ledger, quality floor, complete-attempt accounting, unknown-cost handling. | Billed usage plus measured checking and human correction costs. |
| 5. Measured team/platform expansion | Native Windows runtime and six successful OS/Python jobs; failed mixed-team promotion retained. | Broader provider/host cases and a tested mechanism for resolving reviewer disagreement. |

The next useful increment is a held-out repair pilot with independent tests and
recorded human correction. The smallest already-supported monitoring unit is the
read-only GitHub import and deterministic triage suggestion. A durable monitor
still needs authenticated retrieval, atomic event claims and explicit dispatch
integration; this library increment does not create an unattended repair daemon.

### Reproduction and retained evidence

See [qualification instructions](qualification.md), [operations usage](operations.md),
the [frozen campaign](../experiments/opportunities/campaign.py) and the
[aggregate result with input hashes](../experiments/opportunities/results-2026-09-15.json).
The dev10 model environment is preserved independently of the dev11 Windows build.

Local receipts live under `docs/receipts/opportunities/`: `run-01/` contains frozen
inputs, all raw calls, grades, author audit, repair checks and both raw and audited
summaries; `github-windows-final/` contains the native matrix artifacts. Earlier
receipts and wheels remain local and excluded from Git. The aggregate hashes enable
matching this report to those originals; a hash alone is not independent validation.
