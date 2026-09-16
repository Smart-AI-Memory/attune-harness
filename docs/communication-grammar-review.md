# Human–AI communication grammar: bounded review

Follow-up: both reproduced defects now have source fixes and regression tests in
the isolated Forms worktree `.pilot/forms-grammar-fixes`, branch
`codex/grammar-validation-fixes`, based on 4191c4e (0.17.0). All 195 focused tests
passed; 12 of 18 new cases failed before the guards were added. The deliberate
nonnumeric-key policy remains unchanged. The installed dependency is unchanged;
integration/release is still pending.

## Scope and identity

The communication grammar belongs to `attune-forms`, primarily
`src/attune_forms/models.py` (construct definitions), `bridge.py` (definition and
response validation), and the host-question, widget, Markdown, and elicitation
schema renderers. This is distinct from inference-server JSON sampling grammar.

The local Forms checkout declares 0.15.0. Harness pins 0.17.0, installed under
`/Users/patrickroebuck/.pyenv/versions/3.10.11/lib/python3.10/site-packages/attune_forms`.
Tests below exercise the checkout because its conftest explicitly pins imports;
direct installed-runtime probes independently confirm the ranking issue in 0.17.0.

## What it implements

Seven basic controls plus eight communication constructs: decision, pushback,
progress, deliberation, triage, confirm, ranking, and assumption review. Their
value is preserving the shape of a human decision across rendering surfaces.
Model endorsements and recommendations are presentation metadata, not evidence
of correctness or human authorization. Confirm forbids preselected approval;
assumption edits require replacement text; required triage collects every ruling.

## Findings

### P2: ranking slot positions are discarded before validation

Installed `bridge.py:1966–1979` and checkout `bridge.py:1891–1904` parse numeric
suffixes, sort them, then validate only the resulting list. For a two-option
ranking, both `{'r.0': 'A', 'r.2': 'B'}` and
`{'r.1': 'A', 'r.3': 'B'}` are accepted as `['A', 'B']` by installed 0.17.0.
The missing-slot case also reproduces against checkout 0.15.0.

Impact: a direct/flat adapter can submit an invalid position or omit a rank,
yet collection produces a fully validated answer. Require the actual numeric
slot set to equal 1..N before folding. Preserve existing duplicate-slot checks.
The current Harness review intake uses text and single-select fields, so this
is not a demonstrated failure in that particular intake.

### P3: date validation accepts noncanonical dates

Installed `_validate_date` (`bridge.py:1788`) uses `strptime` without a canonical
format check. `2026-1-2` is accepted unchanged, despite the YYYY-MM-DD contract.
Consumers expecting a fixed-width date can disagree across surfaces. Reject
noncanonical input or explicitly normalize it before collecting the response.

## Deliberate limitation, not a newly discovered regression

An additional dotted ranking key such as `r.typo` is silently ignored by the
direct collector. The checkout explicitly tests this policy in
`test_ranking_construct.py::test_non_decimal_suffix_still_ignored`; Markdown
handles it at parsing time. Documentation should distinguish that policy from
a blanket promise that every malformed/unknown answer is rejected. Revisiting
the policy requires a contract decision, not merely repairing an untested branch.

## Validation

146 existing tests passed across grammar completeness, confirm, ranking, and
assumption review. Direct runtime probes reproduced the ranking and date findings.
This was not a full renderer/browser/security audit. No paid calls or product
edits were performed.

## Implications for documentation and coordinated models

Use this package as the documentation workflow's real-world case. The first
Harness documentation increment cannot adequately describe it: listing class
names omits enum members, dataclass fields, response shapes, and construct rules.
Those need explicit extraction and behavior-backed documentation examples.

Keep grammar ownership in Forms. Harness should consume its validated forms.
An author can explain each construct from code/tests; an independent reviewer
can challenge the explanation against those sources. Deterministic round-trip
examples should establish that valid answers survive each supported surface and
invalid answers are rejected. Do not present model consensus as proof of better
human communication; that requires separate user-facing evaluation.
