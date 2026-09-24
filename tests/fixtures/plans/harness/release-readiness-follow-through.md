# Release readiness follow-through

Patrick authorized recommendations 1–3 on 2026-09-17: map a release-critical
journey, repair the shared spec completion summary, and qualify a fresh install.
Artifact tier: three ordered XML tasks. This is bounded follow-through on the
opportunity log, not approval to implement the scoping-only plan/build spec.

Harness stays in the existing dirty checkout; AI edits stay in the isolated
`/Users/patrickroebuck/attune-ai-memory-adoption` worktree. Preserve prior work.
Use synthetic fixtures and public package resolution in disposable environments.
No live memories, provider campaigns, credential changes, release, or activation.
Run offline functional checks and the required different-model review; do not
substitute a claimed provider-backed pipeline run. Record serious unresolved
findings without silently changing requirements.

<tasks>
  <task id="1" name="map-release-critical-journey">
    <objective>Trace a representative goal through spec, execution, quality decisions and recovery. Distinguish executable Harness paths, Attune host support and unimplemented connections while preserving useful features.</objective>
    <context><existing-code path="src/attune_harness/cli.py">Current verbs and actual dispatch.</existing-code><existing-code path="docs/specs/plan-build/tasks.md">Scoping-only work; not executable authorization.</existing-code><existing-code path="/Users/patrickroebuck/attune-ai-memory-adoption/src/attune/spec/workspace.py">Actual spec stage, approval and evidence handling.</existing-code></context>
    <files-to-create><file path="docs/release-journey-map.md">Evidence-backed path map, qualified seams, concrete gaps and release implications.</file></files-to-create>
    <validation><check>Every working-path claim names its implementation and a current central probe or explicitly historical receipt.</check><check>Run a representative existing offline lifecycle and recovery journey; identify absent plan/build wiring without claiming to have implemented it.</check><check>Different-model evidence-chain advice is verified centrally.</check></validation>
    <risks><risk severity="medium">Passing components can disguise a missing end-to-end journey; no aggregate readiness claim.</risk></risks>
  </task>
  <task id="2" name="repair-spec-completion-evidence">
    <objective>Display actual completed task evidence and dispositions in the shared spec completion summary, including truthful behavior after resume, while keeping historical planning probes clearly identified.</objective>
    <context><existing-code path="docs/receipts/shared-memory-adoption-task5/acceptance.json">O-08: terminal completion repeats old planning-only probes.</existing-code></context>
    <files-to-modify><file path="/Users/patrickroebuck/attune-ai-memory-adoption/src/attune/spec/workspace.py">Retain accepted result evidence and render an accurate terminal summary.</file><file path="/Users/patrickroebuck/attune-ai-memory-adoption/src/attune/spec/state.py">Only if needed for truthful retained evidence across existing save/resume behavior; keep old plans compatible.</file><file path="/Users/patrickroebuck/attune-ai-memory-adoption/tests/unit/spec/test_workspace.py">Failing-before/passing-after lifecycle, retry/risk and resumed-summary checks.</file><file path="/Users/patrickroebuck/attune-ai-memory-adoption/tests/unit/spec/test_state.py">Real state round trip if the persisted representation changes.</file></files-to-modify>
    <files-to-create><file path="docs/design-spec-completion-receipts.md">Pre-edit cases, reproduced behavior, selected design and rejected alternatives.</file></files-to-create>
    <validation><check>Regression fails against original behavior and passes with repair; planning, task execution and final display are distinguishable.</check><check>Retain acknowledged high-risk dispositions and do not present a retry's rejected result as accepted.</check><check>Existing plan resume remains compatible; absent historical evidence is disclosed rather than invented.</check><check>Changed-code coverage at least 85%, relevant source and repository gates, protection-removal receipt and independent review.</check></validation>
    <risks><risk severity="medium">A display repair can erase prior evidence or mislabel acknowledged risk; test those sequences explicitly.</risk></risks>
    <dependencies><dep>1</dep></dependencies>
  </task>
  <task id="3" name="qualify-fresh-installation">
    <objective>Resolve dependencies and exercise the intended primary macOS/Python installation from fresh disposable environments outside both source trees, without borrowing an existing site-packages directory.</objective>
    <files-to-create><file path="docs/receipts/release-readiness-follow-through/fresh-install/">Reproducible installer, actual pip output/report, module/dependency identities, consumer and rollback results.</file></files-to-create>
    <files-to-modify><file path="docs/release-journey-map.md">Actual fresh-install outcome and remaining platform/profile limits.</file><file path="docs/opportunity-log.md">Disposition O-04/O-08/O-07 by evidence; retain unrelated opportunities.</file></files-to-modify>
    <validation><check>Install local candidate wheels with dependencies resolved from the public package index into fresh venvs; no source path, editable hook, or reused dependency directory.</check><check>Verify loaded hashes, generated CLI hosts, actual MCP profile, memory retention, disabled-route rollback and repaired spec summary through installed code.</check><check>Record resolver or supported-profile failure honestly; preserve exact dependency constraints unless a scoped repair is separately justified.</check><check>No provider or live memory effects during runtime qualification; publish exact host/platform limits.</check></validation>
    <risks><risk severity="medium">A successful installation is narrower than runtime compatibility; execute consumers and preserve failed resolutions.</risk></risks>
    <dependencies><dep>2</dep></dependencies>
  </task>
</tasks>

<!-- spec-state: {"schema_version": 2, "completed": ["1", "2", "3"], "task_receipts": [{"task_id": "1", "severity": "low", "score": 100, "probes": ["Qualified Harness profile: 149 passed; Python3.12.13, attune-verify0.6.0.", "Spec baseline60 passed; AI preflight87 passed.", "Actual help succeeds; plan/build help exits2; independent map29 hashes centrally checked with one recorded transcription correction."], "detail": "Release journey mapped in docs/release-journey-map.md. Current review/fix/status/resume connected; plan/build remains scoping-only. Continuous primary review CLI receipt and wider qualification are explicit follow-up gaps. Initial wrong-version run retained; no release readiness claim.", "disposition": "auto"}, {"task_id": "2", "severity": "low", "score": 100, "probes": ["153 Spec/host checks passed;678 quality and gate checks passed;Ruff/Black clean.", "19 new regressions failed original;4/4 protection removals detected.", "Changed-code coverage100%state/97.73%workspace;independent review passed,80 focused checks,14 hashes matched."], "detail": "Accepted task receipts and dispositions now persist and render across resume; retries excluded, acknowledged risk visible, historical planning separate, absent old/runner evidence disclosed. Review concern withdrawn after caller-contract trace and added compatibility regression. Candidate code only; active installed plugin unchanged.", "disposition": "auto"}, {"task_id": "3", "severity": "low", "score": 100, "probes": ["Fresh public dependency resolution:74 packages including2 localcandidatewheels; Verify0.6.0; pipcheck passes.", "Installed:151 memory,24 rollback,80 Spec,146 journey checks;3 source-only tests retained in149-passing source suite.", "13 installed module hashes match; zero outer-runtime socketguard attempts; independent support review passed,14 receipt hashes matched."], "detail": "Fresh Harness[review]+AI[harness] installation verified on macOS26.6.2 arm64/Python3.12.13, without borrowed dependency or source paths. Optional removal/restoration preserves legacy routes. Other platform/MCP/native profiles remain unqualified; active install and release unchanged. See docs/fresh-installation-results.md.", "disposition": "auto"}], "current": null, "auto_run": true, "last_updated": "2026-09-17T14:15:07.087495+00:00"} -->
