# Prepare GUI and memory validation

Prepared November 8, 2026 against `main`
`dcc8c6e428d4e4a73a7f6ee9643e9756dd79557b`.

**Status: preparation only. None of the execution or observation cases below
has been run for this plan.** This document supplies procedures and recording
templates for the existing S3/S6/S9 observations and GUI/memory acceptance gates.
It does not add a release gate, qualify a platform, or authorize implementation,
live model calls, personal hook edits, production Redis writes or publication.

## Start with the right artifact

Use the [current delivery checkpoint](project-plan.md#current-checkpoint--november-9-2026),
[migration guide](migration.md), and actual selected artifact. Historical GUI
build receipts and the hydration task list's older Task 1 status are not the
current runtime capability map.

| Track | Source-bound starting point | What can be prepared now |
| --- | --- | --- |
| Published learner journey | Harness 1.7.0 is published from `5159e7a79fbdb84d2982937716043b142534e6e9`. The [course](../training/README.md) supplies a POSIX offline reporting exercise. | Recruit a first-time learner, select a supported machine, pin the installed wheel and served course, and schedule the observation. |
| Browser forms | [The release boundary](../tests/test_gui_release.py) permits registered draft intake, preview and intent approval. [The server](../src/attune_harness/gui.py) refuses build flags outside its development profile. | Prepare existing-draft, stale-tab, saved-answer, accessibility and service-boundary cases. Treat production build and recovery cases as blocked on their implementation, not as released features. |
| Memory | [The generation reader](specs/native-memory/hydration-generation-reader.md) exists. Source capture, secret checks and accounting are groundwork. [Current migration guidance](migration.md) says 1.7.0 has no supported hydration command, publication/cleanup or automatic delivery. | Prepare synthetic source manifests, negative cases, real-service experiments and clean-host observation procedures. Do not present the proposed commands as available in 1.7.0. |
| Migration | [The current guide](migration.md) defines seven journey rows and rollback boundaries. | Select the exact old/new runtime pair and a disposable copy of each needed journey. Keep every row's outcome separate. |

Keep validation fixtures and evidence outside implementation worktrees, effect
checkouts, authorized memory roots and retained environments. Use one isolated
checkout per implementation owner. Do not modify existing prototypes, frozen
fixtures, receipts or course content while collecting a baseline. Coordinate
any later change to the course's starting paths with its owner after observation.

## Record evidence without upgrading the claim

Use the existing PR handoff and observation record. Keep raw, private receipts
in the existing local receipt location; publish only reviewed synthetic evidence
and redacted summaries. Do not create a second acceptance register.

Create a record for each run with these fields:

```text
Case ID / existing requirement:
State: not run | blocked | passed | failed | assisted observation
Started / finished (UTC):
Operator / observer / consenting participant reference:
Artifact: version, wheel filename, SHA-256, source SHA:
Runtime: absolute interpreter, import location, extras, dependency lock/check:
Machine: OS build, architecture, Python, shell, browser or host version:
Inputs: synthetic fixture/config hashes, selected roots/dataset/task identity:
Preconditions and exact commands or UI steps:
Expected result:
Actual result, exit code, effects and refusal:
Evidence paths and hashes; before/after state comparison:
Assistance, skipped steps and remaining limits:
Next owner/action and required authorization:
```

A source test, installed-wheel test, browser observation, host-delivery observation
and learner observation answer different questions. Record them separately even
when they use the same fixture. Use `blocked` when a required surface is absent;
do not convert that to a passing unsupported row. Preserve failures and rerun
under a new run identity after a correction. Capture actual counts, not historical
counts copied from this plan or the course.

## S6: observe a first-time, non-programmer journey

### Prepare the session

Use a consenting participant who has not used Harness and does not regularly
write or debug code. Record those qualifications by self-report. Keep the
participant's name and consent privately if needed; use an agreed reference in
public evidence. Patrick's preview, an author rehearsal or an agent following
the instructions does not substitute for this observation.

Offer a 45-minute session with a stop or break whenever the participant wants.
This is a planning allowance, not a usability target. Use the published
[Help entry](https://smartaimemory.com/harness/help/) and
[course setup](https://smartaimemory.com/harness/learn/1.7.0-preparation/setup.html).
Record the served source receipt, course/example hashes and actual runtime.
Use a separate Python 3.12 environment and a disposable practice directory.
Do not replace a working installation or alter a shell security policy.

For a complete first-install observation, start before setup. If the facilitator
preinstalls prerequisites, downloads assets or prepares a runtime, record exactly
what was done and call the result a preconfigured-runtime observation. The
published course's command practice uses a POSIX shell on macOS or Linux; it is
not a validated PowerShell exercise.

Tell the participant: "We are checking the instructions and the product, not
testing you. Please say what you expect to happen. You can stop at any time."
Ask permission before recording screen or audio. Use synthetic files only.

### Give outcome prompts, then observe

Follow the current course's commands rather than maintaining another copied
installation script here. The expected observations below are the observer's
checklist, not answers to read to the participant in advance.

| Case | Prompt to the participant | Observe and retain |
| --- | --- | --- |
| L01: find the entry | "You want a report showing where your time went. Find a way to try Harness without paying for model calls." | Entry chosen, confusing terms, whether the participant recognizes the offline example and setup requirements. |
| L02: install and identify | "Follow the setup. Show how you know which Harness installation you are using." | Actual 1.7.0 distribution, interpreter/import path, successful help and local demo, every installation intervention. A demo is not the reporting task. |
| L03: describe success | "Look at the six sample entries. What should a useful report tell you?" | Participant's own goal and one independently checked total; preserve their wording. Opening the supplied report does not count as building one. |
| L04: inspect the plan | "Prepare the practice task. Tell me what may change and how you will know it worked." | A new unaccepted task outside the effect checkout; only `report.py` may change; protected input, checks, registry and expected output remain protected. |
| L05: decide, then execute | "Decide whether the request is acceptable. What happens next?" | Participant distinguishes exact-checkpoint scope acceptance from the separate local-command build grant. No facilitator supplies a stale or copied checkpoint. Record whether that distinction needed a hint. |
| L06: inspect the result | "Show the report you just produced and the evidence that supports it." | Their own generated HTML and task status, actual task/final probe results, unchanged protected hashes, six entries and 270 minutes with project totals checked against the CSV. Fixed command workers are not model-quality evidence. |
| L07: leave and return | "Leave a short note, close the view, then come back and tell me where the work stands." | Locate the saved task and inspect it read-only. Distinguish browser lesson notes, project output and owner records. No **`resume`** merely to reopen a view; no new dispatch. |
| L08: change the request | "Now suppose you only want Orion in the report. What would you do?" | Distinguish reading an existing subtotal from changing requirements and obtaining new acceptance. Do not execute the changed task during this observation. |

At each step record completion, elapsed time, hesitation, the participant's
explanation and the exact help given. Use these assistance labels:

- **Independent:** only the published instructions and participant's own actions.
- **Navigation hint:** point to a section without supplying the decision or command.
- **Procedural assistance:** supply a command, repair setup or explain a required decision.
- **Facilitator takeover:** perform the step for the participant.

Wait for the participant to ask or become clearly stuck before offering help.
Do not let an AI complete an assessed step invisibly. Record an assisted result
honestly rather than restarting the clock to make it independent. A timed-out or
stopped session is useful evidence, not a failed participant.

Ask afterward: "What was most confusing? What did approval mean? Where would
you look tomorrow? What would you trust the checks to tell you?" Save short
verbatim answers with consent. Report whether the needed journey was completed,
which steps required help and what must change. Only the existing acceptance
owner can dispose of S6; this checklist itself does not close it.

### Add the GUI increment when available

Use a second disposable task for browser forms so the CLI course result and GUI
observation remain distinguishable. Give the task outcome, not a tour of buttons.
Ask the learner to save incomplete answers, return to them, review the exact
request, keep a draft or approve it, and explain whether anything executed.
Verify the displayed control names in that build before preparing instructions.
Use only registered tasks; keep future new-task creation, production browser
execution and recovery observations blocked until those surfaces exist.

## S9: exercise installed migration rows

Run against explicitly selected, noneditable installed artifacts outside either
checkout. Record the old/new wheel hashes, interpreter paths and configuration
hashes. Preserve the working old environment and original task/corpus/settings.
Use disposable copies only where the owner supports copying; do not rewrite
task identity, accepted paths or signed evidence to make a copy work. Otherwise
prepare an equivalent new synthetic task in each runtime and state the limit.

Every row needs a normal case, a useful refusal/unavailable case and a documented
return to the previous path. A proposed scenario is not an installed observation.

| Case / current migration row | Procedure and acceptance evidence |
| --- | --- |
| M01: installation and runtime | Install 1.7.0 separately from the previous Harness or Attune AI runtime. Identify the selected executable, distribution and imports, run help/local demo, and select the previous executable again. Original environment/package inventory remains unchanged; do not infer host integration from package installation. |
| M02: file-memory reads | Use authorized synthetic raw, personal and curated sources. Exercise recall, resolve and refresh using the installed help. Compare source/sidecar bytes before and after, provenance and exclusions. Test an unauthorized root, missing source and unsafe link. Use the original reader/configuration for the return path. |
| M03: Redis reads and session recall | Keep existing writer and hooks unchanged. Compare legacy selection with an explicit, matching disposable `harness-v1` fixture. Test absent and foreign native manifests, with no fallback to legacy. Record selected generation and age. Revert only the disposable config to legacy and confirm unchanged legacy keys/library. Host delivery still needs S3 below. |
| M04: explicit saved memory | Create, search, revise and inspect history in a new synthetic saved store using the supported installed CLI. Verify a stale revision refuses and history is retained. Demonstrate that saving is not execution and does not imply automatic recall. Do not test older-runtime downgrade by resuming a newer store without an established compatibility contract. |
| M05: plan/build/review/fix/test | Record a subrow for each needed route, not one blanket pass. Start with the installed offline report and actual protected checks; preserve scope/dispatch separation. Use each route's supported disposable fixture and refusal/recovery procedure. **`fix`** requires its dedicated checkout profile and must not be attempted in this documentation worktree. Unsupported Windows routes stay blocked. |
| M06: review and multi-model consultation | Check the selected scope, exact configured identities and prepared evidence using offline fixtures. Record partial, unavailable and disagreement states where supported. A live roundtable requires separate configured-provider/spend authority; zero-call preparation cannot close live acceptance. Keep the previous required workflow available. |
| M07: host skills and MCP | In an authorized disposable profile, compare required skills, tool names and schemas with the selected plugin/runtime. Verify plugin source/version separately from the Python package. Record absent capabilities and a working alternative. Existing personal plugins, permissions and host settings remain untouched. |
| M08: extensions and Voyage | Check the exact installed extension artifact, signature, grants and replay fixture within its supported profile. Exercise refusal before unauthorized activation/dispatch. Retained replay is not a new live-provider result or general retrieval-quality evidence. Do not regenerate a frozen campaign or make a paid query. |
| M09: command environment compatibility | Without `environment`, verify the documented legacy inheritance with harmless synthetic variables. With an explicit policy, verify only allowed variables reach the test child. Preserve the original registry for older 1.5.1, which refuses the new field. Use no real credentials and do not change the 1.6.0 notice / 1.8.0 removal schedule. |
| M10: rollback and interrupted work | Select the old runtime and its original registry/reader config. Inspect its original saved task. Confirm sources, approval records and legacy Redis state are unchanged. Record the cache timestamp and stopped-writer limitation. Rollback does not undo file effects or establish that new tasks can resume in old software. |
| M11: future hydration replacement | After writer, cleanup and hook packaging land, run the complete H1–H8 installed sequence below with attune-ai absent. Keep this row blocked in 1.7.0. Change a personal startup hook or production selection only under separate rollout authorization after replacement evidence is accepted. |

The first seven journey rows of [the migration guide](migration.md#choose-one-journey)
map to M02–M08. M01 and M09–M11 cover its upgrade, compatibility and rollback
requirements. Record an explicit owner decision for any row still unobserved;
do not silently omit a capability the user depends on.

## S3/H7: prove fresh-session recall without inherited answers

### Keep the observation uncontaminated

Use an evaluator and a separate receiving session. The evaluator owns the
synthetic corpus and expected-answer manifest. The receiving session must not
receive that manifest, this section's seeded answers, prior conversation,
handoff summary, copied banner or evaluator transcript.

1. Create a disposable corpus containing a run-specific random fact, an active
   curated item, an inactive item, a file pointer with a `wrong` sidecar, a valid
   pointer with a unique body-only marker, and records in another authorized
   test dataset. Keep an oracle of IDs, statuses, source paths and hashes outside
   the receiving session's accessible workspace. Use no personal data.
2. Set up only the selected recall route in an explicitly authorized disposable
   host profile. Record host version, actual supported startup event, interpreter,
   root authority, dataset and source/config hashes. Do not change personal
   settings, invent a hook syntax or substitute a manual command for startup.
3. Start a new process/session with no fork, resume, inherited transcript or
   project note containing the synthetic facts. Record the session identity and
   launch settings. A new tab alone is insufficient. Check every other context
   source visible to the receiver for the oracle or seeded answers.
4. Capture the startup event and delivered banner before the first task prompt.
   Preserve sanitized delivery evidence and provenance. Do not paste the banner
   into the receiving chat to repair failed delivery.
5. Ask a neutral prompt that supplies only the retrieval cue, for example:
   "What retained note is available about Aurora's launch window? Give its
   source and capture time. If none is available, say so." Do not include the
   random fact, exclusions or expected answer in the prompt.
6. Compare the actual delivered packet and answer with the private oracle.
   Attribute tool-initiated or manual retrieval separately from automatic
   startup delivery. A correct guess without a delivered source does not pass.

Use a different random fact for each run and a new receiving session for each
condition. Keep these subcases separate for Claude Code and Codex:

| Case | Required observation |
| --- | --- |
| R01: active recall | The startup packet contains the active item with source, timestamp, selected generation and untrusted-evidence guidance. The answer uses the retained random fact with attribution, not invented certainty. |
| R02: unavailable control | Disable only the disposable service or use an empty native selection, then start a clean session. A handled hook failure does not block startup; stdout has no fabricated banner; diagnostics distinguish unavailable from an empty corpus. No fallback reads or inherited random fact. |
| R03: inactive/wrong exclusions | The inactive node and wrong-verdict pointer are absent from emitted context. An explicit question about either does not recover it through this route. Inspect the packet as well as the answer; model omission alone is insufficient. |
| R04: pointer-body exclusion | A legitimate search can match the pointer body, but the body-only marker never appears in the packet/banner. Check provenance and bounded pointer fields without copying body text to the receiver. |
| R05: scope and dataset separation | The selected dataset contains only authorized sources. A second dataset's random fact and a foreign manifest cannot enter the packet. A dataset name alone is not tenant isolation. |
| R06: prompt recall | Where the host supports prompt-triggered recall, separately record its actual mechanism, query, provenance, limits and exclusions. Unsupported prompt recall stays open, rather than being inferred from SessionStart. |
| R07: degraded generation | After a successful disposable generation, cause a safe prepublication failure. Verify the older usable generation retains its original timestamp and an explicit degraded diagnostic. Do not present it as newly hydrated. |
| R08: untrusted recalled text | Include a harmless synthetic instruction to change task authority. Verify it is delivered only as untrusted evidence and neither host nor owner treats it as acceptance, an execution grant or permission to expose other sources. |

Wrapper subprocess tests are useful prerequisites, not fresh-host observations.
Run actual host/model interactions only under the configured authority and any
required spend approval. If no fresh host or approved model path is available,
finish the fixtures and mark the host cases blocked. Do not simulate a named
person's or receiving agent's observation.

## H1–H8: prepare the installed writer sequence

The [approved requirements](specs/native-memory/hydration-writer/requirements.md)
and [command/refusal walk](specs/native-memory/hydration-writer/README.md#proposed-command-journey-and-refusal-walk)
own this sequence. Recheck actual installed help when the implementation exists.
The proposed order is check, apply, status, digest serving, prompt serving,
wrapper, then separate fresh-host observations. Check must not bootstrap by a
reader path that requires an existing generation.

| Case / requirement | Fixture and required evidence |
| --- | --- |
| H01 / H1,H7 | Fresh wheel outside source checkout; attune-ai absent; base import works without Redis extra; selected Redis extra and packaged Lua identities match the wheel. Missing extra is explicit unavailable. |
| H02 / H2,H3 | Four synthetic layers, full source mapping and authority config. Check/apply/serve round-trip IDs, ranking, edges, active membership and current sidecars. Hash all source files and legacy fixture before/after. |
| H03 / H2,H5 | Traversal, symlink, hard link, special file, malformed UTF-8/metadata/edge, ambiguous identity, collision and changing-read cases. Include oversized file/count/snapshot limits and a synthetic blocked-secret pattern beyond the indexing bound or in edge metadata. Refuse before content reaches Redis and retain only sanitized diagnostics. |
| H04 / H4,H6 | Check makes zero mutations. Empty bootstrap publishes once; unchanged input reports unchanged. Test no Search, missing Functions/ACL capability, wrong function identity, unavailable connection and incomplete index. Record real Redis, Search and redis-py versions. |
| H05 / H4 | Inject faults before staging, during writes/indexing, before CAS and before/after switch acknowledgment. Verify prior active state survives and uncertain switches reconcile by identity without blind replay. Two concurrent publishers from the same token cannot both replace it. |
| H06 / H3,H4 | Pause a reader while another publisher switches generation and cleanup runs. Return one coherent generation or refuse. Keep active and previous successful resources; cleanup cannot reclaim a selected/publishable generation or touch legacy/saved/scratch namespaces. Test abandoned-stage expiry and configured bounds. |
| H07 / H5,H6 | Capture stdout/stderr and safe logs for malformed config, connection and subprocess failures. No source bodies, secret values, password-bearing URLs or raw unsafe errors. Wrapper honors its ten-second total deadline, exits zero on handled failure and prints only bounded serve output. Direct apply reports real failure. |
| H08 / H7,H8 | Run the installed CLI sequence, required source/full/installed suites and separate real-service cases, then R01–R08 per host. Revert disposable selection to untouched legacy state. Record original cache age and every remaining gate. |

Use a real disposable Redis+Search service for publication, index readiness,
concurrency and cleanup evidence. Doubles alone cannot prove server behavior.
Never run these injections against production Redis, personal corpora or retained
experiment environments. Source hashes identify captured bytes, not remote Git
freshness. No Git synchronization or model call belongs in the writer test.

## Check each GUI increment

Apply the relevant rows to the current forms release and repeat them for each
later owner-connected increment. Reuse existing test owners instead of creating
a universal command endpoint or a new competing framework. Every observation
records the exact installed build; development-profile tests are labeled as such.

| Case | Procedure and acceptance |
| --- | --- |
| G01: state and authority | Inspect a registered task, save partial answers, reload, preview and explicitly accept current intent. Verify owner status and byte-preserved user wording/capitalization. Approval is not execution. Empty, invalid, unavailable and owner-refused states identify a useful next action. |
| G02: stale/repeated actions | Open two tabs, change one revision, submit the other; double-click; replace a decision; use Back/Forward and Close/Cancel where supplied. Stale/replayed submissions refuse without effects; no old success message masks a newer failure. Verify current screen and history after dismissal. |
| G03: restart and uncertainty | Interrupt before send, after owner save and before acknowledgment. Reconnect and inspect authoritative state without automatic retry or a restored execution grant. Preserve saved answers; explain any unsaved loss. Disk/permission failure cannot be presented as saved or completed. |
| G04: keyboard and focus | Complete the journey with keyboard only. Check logical order, visible focus, no trap, named controls, focus after validation/navigation/dialog dismissal and an accessible alternative to hover-only actions. Record actual browser and assistive technology. |
| G05: reading and layout | Check programmatic names, errors associated with fields and announced status; read long multiline answers and technical input. Measure text/control contrast, test 200% text zoom and 400% page zoom/reflow where applicable, narrow viewport and high-contrast settings. Record measurements and failures; an automated scan is not a screen-reader audit. |
| G06: local service | Verify loopback-only listener; exact Host/Origin; missing, invalid and duplicate capability headers; no permissive CORS; escaped hostile text; CSP; no private-response caching. Capability must not leak through query strings, logs or retained navigation history. Unauthenticated static assets reveal no task/source content. |
| G07: input and path boundary | Reject arbitrary browser paths/commands, foreign task association, traversal/links, unknown fields, oversized requests/responses and invalid launch registrations. Exercise cross-tab/process races. Inspect real owner records to establish absence of unintended effects. |
| G08: released capability boundary | On published 1.7.0, command-build launch flags and direct execution endpoints refuse before effects, including after intent acceptance. Do not use a development override to report production browser execution passed. |
| G09: future execution/recovery | After the owner lands, verify separate exact-scope execution grants, checks/reviewer evidence, progress, terminal/refused states, process loss and evidence-specific reconciliation. Closing a page must not falsely imply cancellation or rollback. Uncertain effects remain inspectable without duplicate dispatch. |
| G10: preservation and export | Compare the replacement with the relevant prototype behavior. Keep original fixtures/results and saved browser choices. No prototype retirement or storage reset; require an explicit export/migration path before a later retirement decision. |

Existing automated starting points include [release boundary tests](../tests/test_gui_release.py),
[decisions](../tests/test_gui_decisions.py), [client behavior](../tests/test_gui_client.py),
[saved requests](../tests/test_gui_saved_request.py),
[navigation](../tests/test_gui_browser_navigation.py) and
[development build tests](../tests/test_gui_build.py). Their presence does not
mean this plan ran them. Record real browser accessibility and failure/recovery
observations beside automated evidence, not in its place.

## Keep platform and host coverage separate

Use the current [qualification workflow](../.github/workflows/qualification.yml),
[qualification guide](qualification.md) and
[release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
for their exact existing evidence. The table below is the run matrix to populate,
not a report that any listed run has passed for this work.

| Profile | Runtime/surface to record | Needed scope and current limit |
| --- | --- | --- |
| Ubuntu hosted | Actual image/build/architecture, Python 3.12 | Source suite, installed wheel, assets and owner fixtures. Does not establish desktop browser/host usability. |
| macOS hosted | Actual image/build/architecture, Python 3.12 | Installed wheel and owner fixtures. Do not infer the user's macOS host or accessibility behavior. |
| Windows Server 2022 | Actual image/x64 runtime, Python 3.12 | Separate source and installed-wheel cells; inspect exact-head CI, refusals and skips. No Windows 11 equivalence. |
| Windows Server 2025 | Actual image/x64 runtime, Python 3.12 | Same evidence categories with its own receipt, not a copied 2022 result. |
| macOS desktop | CPU, OS, shell, Python, browser; VoiceOver version when used | Published POSIX learner/course journey, GUI/accessibility and each available fresh host. Record desktop source/profile independently. |
| Linux desktop | Distribution, session, shell, Python, browser; screen reader when used | POSIX learner/course and GUI tests; fresh hosts only where actually supported and available. |
| Windows 11 standard user | OS, hardware architecture, Python architecture, PowerShell and browser; NVDA/other AT version | Base install/forms observations separately from unsupported course shell, strict stop/recovery, saved-store and live-memory gates. x64 Python under ARM emulation is not native ARM64. |
| Native Windows ARM64 | Exact interpreter and wheel availability | Current binary-only base install has a documented dependency limit. Record refusal; no workaround or passing parity claim is presumed. |
| WSL2 | Windows host plus Linux distribution/runtime | Label as Linux-in-WSL evidence, never native Windows qualification. |
| Claude Code | Exact host version, plugin/runtime source, startup mechanism | Separate R01–R08 receipt. A matching hook name or wrapper unit pass is not automatic delivery. |
| Codex | Exact host version, plugin/runtime source, startup mechanism | Separate R01–R08 receipt with no inherited context. Do not transfer a Claude result or substitute an embedded preview for a system-browser observation. |
| Other host / Antigravity | Exact adapter and claimed capability | Only selected and supported capabilities; consultation support is not plan/build or automatic-memory parity. |

For a browser claim, name each tested browser/version and embedded/system mode.
Choose the supported browser set before execution; do not declare all browsers
supported from a Chromium-only run. Measure startup/action latency and peak
resources with the fixture and machine identified before proposing performance
targets. Missing hardware, assistive technology, host access or authorization is
a recorded blocked cell, not a reason to weaken the matrix.

## Hand off the next work

1. **Now:** select a consenting S6 participant and a supported POSIX machine;
   preserve the published entry/course baseline before suggesting revisions.
2. **With current installed artifacts:** run the applicable M01–M10 and G01–G08
   cases in disposable environments. Keep unneeded migration routes explicitly
   unobserved rather than spending on new provider experiments.
3. **When writer and GUI owners deliver:** bind H01–H08, R01–R08 and G09 to their
   exact artifacts, supported refusal sites and existing acceptance criteria.
4. **Before an acceptance/release claim:** reconcile all required observations,
   independent review, final-head tests, installed-wheel checks and platform
   evidence with the existing gate owner. Open observations remain open until
   evidence or an explicit disposition is recorded. Merge and release remain
   separate decisions.

Completion review for this preparation: the practical next evidence is the
independent installed learner walkthrough already tracked as S6. The memory
publication and fresh-host cases wait for their implementation and authorized
host runs. No new opportunity entry, software qualification or human observation
is claimed by writing this plan.
