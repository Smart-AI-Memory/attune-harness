# Earlier design: read-only task snapshots

This preserves the earlier implementation design and review-first exploration.
The current Task 1 is [return to work](task-1-return-to-work.md), with its
implementation and human acceptance tracked separately.
The code and evidence below are reuse candidates, not completion of that journey.

The earlier chunk adds
`status TASK --format markdown|html`; omitted format and explicit `json` retain
existing output and exit semantics. No live connection or action controls yet.

## Preparation checkpoint

Current base is `11071a1`, refreshed before implementation. Its newly landed
workspace MCP and spec presenter are integration candidates for later chunks.
Reuse the presenter's literal-text escaping; retain task status as authority.
Baseline: 115 existing work-contract and CLI-boundary tests passed on Python 3.10.
The only warning was pytest's cache write being denied in the isolated checkout.

`work_cli.present` already produces stale/unresolved precedence, host checks,
review advice, completion and evidence pointers. `work_runtime.completed_steps`
derives completion from passing protected probes, not participant prose. The view
must consume those meanings unchanged. A single validated record supplies both
project identity and status projection, preventing mismatched snapshots if a
writer replaces the record between reads.

## Scope and design

- Add `task_view.py`: a bounded, explicit view model plus Markdown and HTML
  renderers. Include project/task/revision/checkpoint, capture time, goal/scope/
  criteria, actual completion, current guidance, check and review references,
  missing information and freshness. Full payloads remain in the saved record.
- Extend `task_cli` with optional format selection only for status. Route non-JSON
  feature-work inspection through the new projection. Unsupported profiles and
  malformed records give an explicit diagnostic and nonzero exit; JSON remains
  available for every currently supported profile. Never dispatch or save.
- Add an internal preloaded-record argument to `work_cli.present` so the validated
  record is read once for each human-readable snapshot. Default callers unchanged.
- Escape repository text in both renderers. No dynamic HTML, scripts, forms,
  external resources or active links from source text; apply a restrictive CSP.
  Preserve all fields up to a 512 KiB view-model limit, then refuse explicitly
  with a JSON-status fallback hint rather than silently truncating evidence.
- Do not scan for or load external reports. Explain that separately authored
  artifacts are not recorded execution; the view does not reconcile their state.
- Update the compatibility surface fixture deliberately, guide, compatibility
  note and changelog. Platform selection discovers the new test module through
  the existing marker; no workflow or retained campaign needs an edit.

Likely later API: inspect once into a JSON-serializable projection, render it
through either output. A future connection can deliver that same projection.
Snapshot time means captured now, not live freshness after the page is opened.

Rejected: rendering arbitrary record JSON exposes internal payloads and confuses
claims with checks; inferring progress from task prose manufactures authority;
introducing a server now expands the chunk before the projection is qualified.

## Protected verification and done condition

Before implementing, freeze tests for one real draft and stale record; a scripted
build with paused, failed, unresolved and completed results; byte-identical default
JSON; project/task identity from the same record; inspect without writes/dispatch;
hostile HTML/Markdown/control characters; explicit output bounds; unsupported and
corrupt input; evidence references and honest absence of execution. Deterministic
fixtures establish software behavior, not native model quality.

Run targeted tests and full suite, build a wheel and qualify its installed artifact,
inspect the rendered page at narrow/wide sizes, then obtain independent source
review and read CI's platform results. Done for this chunk means a reviewed PR
with those results and limitations. Merge remains the maintainer's gate. Later
chunks integrate through main under the repository rules. Retain verified results
and remaining limitations in the pull request handoff.

Fixture correction during verification: the existing owner classifies a settled
nonzero protected check as `needs_revision`. The test now covers that state and
uses an invalid worker task identity to exercise `failed`. No production state
semantics were changed to satisfy a test expectation.

Independent review found that missing-decision IDs did not explain their actual
questions or options. Added regression cases for unanswered/unselected and saved
answers/selections before extending the same projection and shared outline with
question text, materiality, options, rationale, counter-case and evidence limits.

## Earlier human workflow refinement: review work

The review-first exploration proposed helping a person review a result: what outcome was delivered,
why it matters, which evidence supports it, which claims remain untested, and the
specific correction or decision needed to move forward. The initial record-first
snapshot has not established that usefulness, despite passing software checks.

Before another production presentation change, use a brief grounded in real task
evidence to review that content hierarchy. Lead with outcome, review disposition,
ready work, unresolved gaps and the next decision. Keep IDs, paths, checkpoint
details and the full scope available as supporting detail. Do not invent a review
request or an approval control when no such decision exists. Opportunity discovery
stays secondary to evaluating the agreed outcome.

The saved draft alone does not describe implementation and review performed in
the assistant session. A combined briefing must preserve the provenance of those
external results and must not convert them into Harness execution or completion.
The current human-authored preview establishes neither an import API nor packaged
support for combined evidence. Resolve that source boundary before claiming the
product can generate the same briefing. Human workflow acceptance remains pending.
