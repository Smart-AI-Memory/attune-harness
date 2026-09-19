# Decisions — September 16, 2026

**D1 — Project and mode confirmed.** Patrick selected “Voyage RAG in
attune-harness: assess the validation bottleneck and plan the next increment.”
The older attune-rag release is outside this session.

**D2 — Spec planning selected.** After asking about the advantage of `/spec`,
Patrick selected “Use /spec for the plan.” Carry the established contract forward;
there is no need for another project/outcome intake.

**D3 — Bounded approach proposed, not yet approved.** Recommend reusing the
immediately checked generation at retrieval entry. The disposable experiment
removes one duplicate check with no format or session-lifetime change. The
production task ladder has not been approved or started.

**D4 — Evidence limits.** The timing uses synthetic vectors and real local
LanceDB; it establishes implementation feasibility, not search quality or live
end-to-end latency. The two measured source snapshots run in separate processes.
Task 3 must repeat in reverse order and qualify an installed wheel.

**D5 — Preserved state.** PR #1 is remotely verified merged at
7eabe5821aaf484276909e13f116a4ffe2bdaed4. The current branch retains the previous
local starter commit ce61c18. The preserved code-rag installation differs from
current source in attune_bridge, documentation, voyage_provider and
voyage_retrieval. The historical generation rejects the current checkout as
stale. No frozen environment or experiment was upgraded/reindexed.

**D6 — Host scope.** The active tool catalog has no code-evidence query/read tool.
Codex MCP-server configuration text has no Harness bridge reference; the Harness
project trust entry is not an integration. This is not a probe of every host.

**D7 — Execution and publication.** No paid campaign, credential operation,
desktop switch, release, push or merge is part of this planning authorization.
Plan review and execution decisions remain pending. No task is marked complete
from the disposable prototype or existing-suite results.

**D8 — Broader latency question assessed.** Patrick asked about additional Voyage
features and caching. The design now compares verified-snapshot reuse, exact
cross-session caches, smaller Voyage vectors and lite reranking. A physical-file
hash cost probe is promising but does not establish equivalent tamper detection.
These are follow-on proposals; the production scope and approval state are unchanged.

**D9 — Ready for review.** The installed Attune reader parsed all three XML tasks
and their dependencies; saved progress round-tripped with no completed/current
task and auto-run false. The tasks-boundary symbol-reality and falsifiability
gates both passed without waivers (receipts 6b9d21ef1819 and a491fad3d0e0).
The CLI could not append to its default home-directory ledger under the sandbox;
the same gate runner completed with its supported local ledger argument.
Canonical workspace spec-0b31da2ab17d43d5aa158e89e249cda1 is at review, revision 3.
The exact returned review surface and action binding are preserved locally in
`docs/receipts/validation-bottleneck-20260916/workspace-review.json`.
The probe wording about declared files refers to parsed file declarations;
Task 1's measurement script and Task 3's verification report are future files.
All 468 frozen experiment files remained unchanged. The plan and starter update
are local and uncommitted; production execution remains unapproved.

**D10 — Reranker API retained and comparison made concrete.** Patrick said “we
should take advantage of using the reranker api too,” selecting rerank-2.5-lite
in the design. Source inspection confirms that nonempty uncached retrieval already
uses Voyage's API with rerank-2.5. The design now makes that integration explicit
and proposes a controlled lite comparison on identical candidates, with model-bound
cache/usage receipts and quality/latency checks. The three production tasks still
preserve the current reranker. No alternative-model promotion or paid campaign
is implied by this planning steer.

**D11 — Reranker preparation authorized and completed.** Patrick's subsequent
“go” referred to the lite comparison; his FAQ note confirms lite as the preferred
latency candidate. A separate experiment now compares both models on the exact
100 historical candidate pools, alternating request order. This is explicitly
retrospective; fresh validation remains required for promotion. The evaluator,
offline behavioral tests and immutable packet are prepared; expected spend is
$0.09–$0.11 for 200 reranker calls, with a $1 local stop budget and zero embedding
calls. The upload and first estimated-spend approval remain outstanding under
Patrick's saved first-spend rule. See
[the concrete run packet and validation](../../reranker-comparison-preparation.md).
This preparation does not approve or complete any production task in this ladder.

**D12 — Live comparison approved.** Patrick explicitly approved the prepared
200-call comparison with a $1 local stop budget. The run uses packet
`f53546222f045be518f75ae21f69c153b28c694a73982de44d3c238c61cecbb1`
and the existing local Voyage credential setup. The approval covers this paired
reranker study and its stated uploads; it does not authorize a default-model
switch or execute the production validation-reuse ladder. Its authorization and
durable per-call receipts are under `.pilot/rerank-comparison-2026-09-16/`.

**D13 — Paired comparison completed; no default promotion.** All 200 calls
completed for $0.09212483 at frozen list rates, below the approved $1 stop budget.
Lite cost 60% less and saved a paired median 19.0 ms; evidence completeness was
74/80 versus 75/80 at top five and 76/80 for both at top ten. Two losses and one
gain mean lite failed the predefined no-top-five-loss check. The frozen scores
are retained alongside inspected evidence qualifications. Keep the current model
default and prioritize validation reuse for the larger measured local bottleneck.
See [results and receipts](../../reranker-comparison-results.md). All 468 historical
files are preserved; no production spec task was executed or accepted.

**D14 — Validation-reuse ladder approved.** Patrick said, “I want to approve the
voyage validation reuse -- task ladder in the spec.” His decision was transcribed
through the canonical collector: `approve_plan` at revision 4, then
`start_execution` at revision 5. Execution symbol-reality and falsifiability gates
both passed without waivers (b7e107598c9d and 1c1d281dbb90). Task 1 started at
revision 7. Saved SpecState is completed=[], current=1, auto_run=false. Approval
and gate receipts are preserved under the existing validation-bottleneck receipts
directory. No task is accepted from plan approval alone.

**D15 — Task 1 checks ready; review route pending.** Added the portable offline
probe and 35 cases to the Voyage suite: 79/79 tests pass. A fresh source snapshot
at ce61c18ac396c91e5441ac34f218e41c942df593 reproduces full-check counts 4/3 direct,
6/5 session and 1 for setup on six queries/1,050 passages, with zero live calls.
All 36 production modules and 468 historical files remain unchanged. A disposable
row-integrity mutation makes 8/35 new tests fail. The installed spec task gate
uses paid review workflows, while the approved ladder specifies offline work.
An asynchronous choice asks Patrick to use offline checks and auto-run the
remaining tasks, or prepare a separate paid-review budget. No paid review was
called, skipped gate was reported as passed, or task acceptance fabricated.
