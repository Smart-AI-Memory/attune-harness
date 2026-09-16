# Sol cross-review — September 16, 2026

Advisory only. Four medium-severity findings confirmed by central offline probes; three claims rejected with reasons. The review itself made no implementation changes. All four confirmed findings were subsequently fixed and tested in the same workspace; see the [September 16 fix receipt](sol-review-fix-receipt.md). Original claims, probe results and raw review artifacts below remain historical evidence.

## Target and coverage

Repository: `attune-harness`, branch `codex/voyage-retrieval`, base HEAD `6bece93e8d5ddae3205d394b9b9c90d4408b8ee3`. All tracked modifications and new files were captured into a temporary Git index. The real index, branch HEAD, and all 59 captured source files remained unchanged.

One explicitly selected `gpt-5.6-sol` native subagent reviewed two module-generated briefs: 29 files in the first pass, followed by exactly the 30 omitted paths. Together they cover every captured diff path. All 58 text-file diffs were supplied in full; `.attune/history.db` was represented only by Git’s binary marker, so its contents were not reviewed.

`attune.roundtable.review.run_review` performed target resolution, manifest packing, reply linting, parsing and receipt generation. An injected invoker transported the brief to the requested Sol subagent. The module’s provider-level `host=codex, self_review=true` stamp remains unchanged. Sol’s model selection is verified by its launch; the moderator is Codex / GPT-6. The earlier exact Astra label was an unverified assumption, corrected in [identity.json](receipts/cross-review-sol-20260916/identity.json).

## Confirmed findings

### 1. Medium — src/attune_harness/voyage_retrieval.py:139

**Claim:** With a permitted `max_provider_calls=1` and any nonempty corpus, retrieval dispatches and bills the query embedding before discovering at line 145 that the mandatory rerank exceeds the stage budget; the run can never complete under that accepted configuration, so required calls must be reserved before dispatch.

**Central evidence:** Offline FakeProvider completed exactly one query embedding, then retrieval raised PermissionError before reranking for max_provider_calls=1.

**Disposition:** Real. Fixed: new and prepared query embeddings check rerank capacity before dispatch; completed stages still replay freely at a full budget. See the [fix verification](sol-review-fix-receipt.md).

### 2. Medium — src/attune_harness/attune_bridge.py:68

**Claim:** `activate()` passes only `_failed` to `finish()`, so an exception outside `search()`—including the explicit duplicate-plugin error during registration or a `serve_attune()` crash—closes the session as `completed` when no paid event is pending, producing a false successful lifecycle receipt.

**Central evidence:** RuntimeError raised inside activate(), outside search(), propagated while the saved session status was completed.

**Disposition:** Real. Fixed: exceptions leaving activation, including cancellation and keyboard interrupts outside search, save an unresolved lifecycle and propagate. See the [fix verification](sol-review-fix-receipt.md).

### 3. Medium — experiments/voyage/evaluate.py:145

**Claim:** A provider or validation failure is converted to an `incomplete` report and returned, but the CLI only prints that report and exits zero; automation can therefore accept a failed, partially run campaign as successful.

**Central evidence:** A real subprocess executing the evaluator CLI produced campaign status incomplete and case status failed with exit code 0 after FeatureUnavailable; no provider authorization or paid calls were used.

**Disposition:** Real. Fixed: an incomplete campaign preserves its JSON report and exits 1; frozen and completed campaigns exit 0. See the [fix verification](sol-review-fix-receipt.md).

### 4. Medium — scripts/check_code_rag_host.py:48

**Claim:** Every qualification condition uses `assert`, so `python -O` or `PYTHONOPTIMIZE=1` removes the result, usage, and durable-session checks while the script still emits `status: passed`, allowing a false host qualification receipt.

**Central evidence:** The same intentionally invalid host-boundary fixture raises AssertionError under normal Python but returns receipt status passed under Python -O, despite failed result status and unresolved session evidence. MCP transport/results were injected; no real network call was made.

**Disposition:** Real. Fixed: explicit runtime checks reject invalid result, usage and lifecycle fixtures under normal and optimized Python. See the [fix verification](sol-review-fix-receipt.md).

## Rejected claims

### src/attune_harness/mcp_server.py:165

**Original claim:** The new Voyage tool is advertised as uploading data and incurring costs but still publishes `read_only_hint=True`; an MCP client that auto-approves read-only tools can therefore send the query and selected source passages to Voyage and incur charges without treating the call as side-effecting.

**Reason:** Not accepted as a demonstrated authorization bypass: the explicit allow_provider flag still gates dispatch. A central probe without it raises FeatureUnavailable with zero provider calls. The tool separately sets open_world_hint=True and describes uploads and costs. MCP readOnlyHint describes environmental modification, not a cost/confidentiality guarantee; no concrete client bypass was demonstrated. See https://modelcontextprotocol.io/specification/2025-11-25/schema#toolannotations.

### docs/voyage-100-question-evaluation.md:90

**Original claim:** The report’s raw results, receipt audit, behavior tests, and installed-code audit all link into unstaged `.pilot` artifacts; a committed clone therefore loses the evidence needed to audit the exact 100-question and 200-call qualification claims.

**Reason:** The local raw evidence files all exist and the report scores match summary.json. Project guidance explicitly preserves frozen raw campaigns locally and ignores .pilot in Git. Clone portability is a real limitation, already part of this local evidence policy, not a demonstrated defect in this change. No published reproducibility guarantee is made.

### docs/integrated-rag-architecture.md:56

**Original claim:** The ADR first says the qualified in-process plugin supersedes the separate-stdio recommendation, then mandates stdio and defers the in-process adapter until later qualification; maintainers receive mutually exclusive deployment decisions from the same accepted document.

**Reason:** Lines 39-47 explicitly date the update and say that the qualified in-process adapter supersedes the initial separate-stdio recommendation. The lower paragraph describes that initial recommendation. Historical text could be labeled more clearly, but the current decision is explicit; no contradictory current requirement was established.

The MCP annotation interpretation was checked against the [official MCP ToolAnnotations schema](https://modelcontextprotocol.io/specification/2025-11-25/schema#toolannotations). This is a moderation judgment, not a claim that every client handles annotations correctly.

## Verification and durable records

- 313 targeted source/integration tests passed in `.venv-code-rag`; one existing ModelTier deprecation warning.
- 23 standalone MCP tests passed in `.venv-mcp2-probe`.
- Four accepted findings reproduced centrally using local fixtures. No live Voyage or Anthropic provider calls were made.
- [First two reproductions](receipts/cross-review-sol-20260916/probes.json) and [second two reproductions](receipts/cross-review-sol-20260916/probes-second.json) retain observed outputs; companion Python scripts allow rerunning the probes.
- [Ledger](specs/cross-review/receipts.md) was written by the module’s ledger CLI. Dispositions may be edited to real, noise, or rejected with claim/reason; findings do not gate anything.
- [Raw result 1](receipts/cross-review-sol-20260916/result-1.json), [raw result 2](receipts/cross-review-sol-20260916/result-2.json), [test commands](receipts/cross-review-sol-20260916/tests.json), and [final snapshot verification](receipts/cross-review-sol-20260916/final-verification.json) are retained locally.
- Initial board access was sandbox-blocked. The original replies were then posted successfully to the local board without re-running the review; [board receipts](receipts/cross-review-sol-20260916/board-posts.json) preserve that distinction.

- `result-1.json`: `review-codex-voyage-retrieval-20260916-0317` (posted).
- `result-2.json`: `review-codex-voyage-retrieval-20260916-0322` (posted).

## Verbatim coverage manifests

### Pass 1

```text
Files under review (29): src/attune_harness/voyage_sources.py, src/attune_harness/voyage_provider.py, src/attune_harness/voyage_index.py, src/attune_harness/voyage_retrieval.py, src/attune_harness/documentation.py, src/attune_harness/mcp_server.py, src/attune_harness/review.py, src/attune_harness/attune_bridge.py, src/attune_harness/cli.py, src/attune_harness/recovery.py, src/attune_harness/voyage_cli.py, src/attune_harness/review_cli.py, src/attune_harness/retrieval_task.py, src/attune_harness/grounded_review.py, src/attune_harness/passage_review.py, src/attune_harness/review_contract.py, src/attune_harness/extensions.py, tests/test_voyage.py, tests/test_code_rag.py, tests/test_voyage_integration.py, tests/test_documentation.py, tests/test_voyage_evaluation.py, .github/workflows/qualification.yml, pyproject.toml, docs/rag-options-research-2026-09-15.md, docs/voyage-retrieval-implementation-plan.md, docs/voyage-next-increment-2026-09-15.md, experiments/voyage/heldout.json, .attune/history.db
OMITTED over the 250000-char budget (30): docs/voyage-100-question-evaluation.md, docs/voyage-answer-accuracy-preparation.md, docs/voyage-answer-accuracy-calibration-2026-09-15.md, docs/design-voyage-answer-accuracy.md, docs/voyage-full-code-evaluation.md, docs/voyage-latency-assessment-2026-09-15.md, docs/voyage-retrieval-receipt.md, experiments/voyage/evaluate.py, docs/voyage-retrieval.md, docs/integrated-rag-architecture.md, docs/voyage-rag-session-starter.md, docs/code-first-rag-receipt.md, docs/code-first-rag.md, docs/design-voyage-retrieval.md, docs/communication-grammar-review.md, docs/voyage-accuracy-receipt.md, scripts/check_code_rag_host.py, experiments/voyage/README.md, docs/harness-api-budget.md, scripts/voyage_smoke.py, docs/design-voyage-full-code-evaluation.md, docs/design-code-first-rag.md, docs/documentation-workflow.md, scripts/qualify_voyage_mutations.py, docs/design-documentation.md, docs/design-voyage-100-question-evaluation.md, requirements-voyage.lock, experiments/voyage/tuning.json, README.md, scripts/qualify_platform.py
This is a PARTIAL review — omitted files were not seen.
```

### Pass 2

```text
Files under review (30): docs/voyage-100-question-evaluation.md, docs/voyage-answer-accuracy-preparation.md, docs/voyage-answer-accuracy-calibration-2026-09-15.md, docs/design-voyage-answer-accuracy.md, docs/voyage-full-code-evaluation.md, docs/voyage-latency-assessment-2026-09-15.md, docs/voyage-retrieval-receipt.md, experiments/voyage/evaluate.py, docs/voyage-retrieval.md, docs/integrated-rag-architecture.md, docs/voyage-rag-session-starter.md, docs/code-first-rag-receipt.md, docs/code-first-rag.md, docs/design-voyage-retrieval.md, docs/communication-grammar-review.md, docs/voyage-accuracy-receipt.md, scripts/check_code_rag_host.py, experiments/voyage/README.md, docs/harness-api-budget.md, scripts/voyage_smoke.py, docs/design-voyage-full-code-evaluation.md, docs/design-code-first-rag.md, docs/documentation-workflow.md, scripts/qualify_voyage_mutations.py, docs/design-documentation.md, docs/design-voyage-100-question-evaluation.md, requirements-voyage.lock, experiments/voyage/tuning.json, README.md, scripts/qualify_platform.py
```
