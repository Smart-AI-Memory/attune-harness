# Voyage validation reuse

Approved for execution, September 16, 2026. Owner: attune-harness.
Patrick approved the task ladder; canonical workspace recorded plan approval
and execution start. Task 1 is in progress; no task has yet been accepted.
Spec: `docs/specs/voyage-validation-reuse/`.

Reduce the immediately duplicated full-generation check at retrieval entry.
Keep existing public inputs, generation/receipt formats, validation boundaries,
evidence semantics and paid-stage controls. The disposable planning prototype
shows one fewer check and a roughly half-second warm offline reduction on the
1,050-passage fixture; it is not production implementation.

<tasks>
  <task id="1" name="lock-validation-boundaries-and-baseline">
    <objective>Capture the current integrity, scope and effect boundaries in failure-sensitive tests, and create a reproducible offline baseline fixture before production edits.</objective>
    <files-to-create>
      <file path="experiments/voyage/profile_validation.py">Portable offline measurement adapted from the disposable planning probe: fresh deterministic source/vector fixture, real LanceDB, separate variant processes, disabled live clients, preserved samples and check counts.</file>
    </files-to-create>
    <files-to-modify>
      <file path="tests/test_voyage.py">Add missing behavioral cases for public selection return semantics, source and revision changes, equal-length edits, vector and metadata tampering, repeated calls, and changes during candidate/provider work. Reuse existing coverage where it already proves a requirement.</file>
      <file path="docs/specs/voyage-validation-reuse/design.md">Record the baseline identity, fixture contract, observed boundaries and exact experiment command.</file>
    </files-to-modify>
    <validation>
      <check>Run the new behavioral tests on the untouched implementation; expected valid behavior passes and deliberately altered integrity data is rejected at the required boundary.</check>
      <check>Measure direct and session recomputation and cache replay separately on a 1,050-passage fixture. Nonempty session counts are six and five full-generation checks respectively; source hashes and all samples are saved.</check>
      <check>Any live provider construction fails the probe; all measured calls replay completed fixture stages with zero new provider calls. The fixture uses synthetic vectors and makes no quality claim.</check>
      <check>Run the measurement script in a fresh source snapshot with no historical .pilot data; refuse output overwrites and preserve original experiment files.</check>
    </validation>
    <risks>
      <risk severity="medium">Timing noise or fixture vectors may misrepresent live behavior. Treat operation counts as the stable result and label warm offline timings explicitly.</risk>
      <risk severity="high">Weak tests could miss a removed guard. Identify the specific source/scope/integrity guards each negative case detects before the refactor.</risk>
    </risks>
  </task>
  <task id="2" name="reuse-checked-entry-generation">
    <objective>Extract the selection-validation helper and consume its checked generation directly in retrieval, removing only the immediate duplicate full check.</objective>
    <files-to-modify>
      <file path="src/attune_harness/voyage_index.py">Private helper validates selection and returns checked directory/metadata; public load_selection retains full validation and returns the original selection object.</file>
      <file path="src/attune_harness/voyage_retrieval.py">Use the checked entry result once; retain checks after candidate search, before reranking and in returned-evidence validation.</file>
      <file path="tests/test_voyage.py">Assert direct check-count reduction while preserving public return, evidence, replay, refusal and error behavior.</file>
    </files-to-modify>
    <validation>
      <check>Run the Voyage, code-RAG, integration and recovery regression suites against changed source. Assert evidence IDs, bytes, scores, scope, usage and replay semantics match baseline, apart from nondeterministic receipt fields.</check>
      <check>Metric probes show direct recompute four to three and cached replay three to two full checks; session paths show six to five and five to four. Session setup remains one.</check>
      <check>Source changes introduced during embedding or reranking, row/vector tampering, changed generation metadata and repeat-call edits still fail before the next protected effect or evidence delivery.</check>
      <check>Individually remove relevant scope, freshness and retained-boundary guards only in disposable copies; report detected mutations and failed/selected new tests in the suite receipt.</check>
      <check>Verify an existing generation and accepted task still work without rewriting their metadata, formats, digests or grants. No new dependency or provider call is introduced.</check>
    </validation>
    <risks>
      <risk severity="high">Expanding reuse across callbacks or invocations could make stale state trusted. Keep reuse private to synchronous retrieval entry; add no cache or caller-supplied validation token.</risk>
    </risks>
    <dependencies><dep>1</dep></dependencies>
  </task>
  <task id="3" name="qualify-artifact-and-report-latency">
    <objective>Qualify the built implementation in a separate environment and measure its actual improvement without overstating performance or changing the user's active host.</objective>
    <files-to-create>
      <file path="docs/specs/voyage-validation-reuse/verification.md">Artifact hashes, suite/mutation results, per-path timing/check counts, measurement limits, preservation evidence and final implementation status.</file>
    </files-to-create>
    <files-to-modify>
      <file path="docs/voyage-rag-session-starter.md">Record the verified implementation state and remaining host/coding-outcome opportunities after task acceptance.</file>
    </files-to-modify>
    <validation>
      <check>Build the wheel and install into a new isolated environment. Outside the source tree, verify every package-module hash against the built source and run the applicable retrieval, plugin, MCP and recovery consumers.</check>
      <check>Compare baseline and changed code in separate interpreters with identical dependency versions, fixture bytes and queries, first baseline/changed then changed/baseline. Save every sample and label cold startup, transport, concurrency, provider time and answer generation as unmeasured.</check>
      <check>Accept no integrity/effect regression. Confirm the deterministic full-check reduction and assess timing in both orders; if timings do not establish improvement, record inconclusive performance and investigate before making a speed claim.</check>
      <check>Verify the 468 frozen historical experiment files and preserved environments remain unchanged. New outputs never overwrite earlier evidence, and no paid provider requests occur.</check>
      <check>Record implemented/tested, installed-for-qualification, active-host, committed/pushed, PR and merge status separately. Deployment or publication requires its applicable later authorization.</check>
    </validation>
    <risks>
      <risk severity="medium">Installed tests may accidentally import the working tree or an old wheel. Run from outside the checkout and prove module hashes before interpreting results.</risk>
    </risks>
    <dependencies><dep>2</dep></dependencies>
  </task>
</tasks>

Read the spec decisions and canonical task state on resume. Plan approval is
recorded; task acceptance remains separate and auto-run is currently disabled.

<!-- spec-state: {"schema_version": 1, "completed": [], "current": "1", "auto_run": false, "last_updated": "2026-09-16T06:36:09.900960+00:00"} -->
