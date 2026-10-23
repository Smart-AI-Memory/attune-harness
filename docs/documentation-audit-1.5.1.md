# Harness 1.5.1 documentation surface audit

Audited on October 23, 2026. **1.5.1 is preparation, not a verified published
release.** A fresh PyPI JSON response reported latest version `1.5.0` and no
`1.5.1` release. The [published package reference](https://pypi.org/project/attune-harness/1.5.0/)
remains the installation baseline. This dated audit does not change release
status or authorize publication.

## Current guidance and ownership

The audit inspected main `c8acd9a1e8efef7cc42773eef417ab56582d1c38`, the separate
documentation candidate `3a8bf4ed6c4d7ccac92a9b9b9c86b64ec7768dad` (#300), canonical
Help `46b2ee4768401e744d65f90baa6309f7638ece5c` (#299), and release preparation
`ac634573591981c70d895d784f3bd093ee006750` (#301). Unmerged changes were inspected
as separate candidates. They were not consolidated into this branch.

| Surface | Current treatment | Owner and remaining work |
| --- | --- | --- |
| Root README and PyPI description; package/plugin versions and changelog | Published 1.5.0 remains distinct from planned 1.5.1. PyPI renders the release artifact's README, not the current repository README. | #301 reconciles after #299 and #300 reach main; rebuild and compare the final artifact. Publication and later PyPI rendering remain separate. |
| Installation, workflow selector and four walkthroughs | #300 supplies isolated-runtime setup and `tutorials-1.5.1.md`, explicitly unpublished. Candidate validation uses a selected local wheel; old observations retain their identities. | #300 is settled with the release owner. Final combined-source and artifact replay remain open. |
| Canonical Help landing, eleven topics, goals, examples and captures | #299 owns `help/`, its manifest, `scripts/build_help.py` and renderer checks. Get started uses a 1.5.1 candidate wheel, with a published 1.5.0 fallback. | Consume the canonical export; do not maintain another React copy or hand-edit generated HTML. Final source and publication metadata still require reconciliation. |
| CLI entry points | `cli_help.py` gives task routes and `COMMAND --help`; it contains no old-version website destination. The CLI guide and host skills describe commands and scope rather than an invented `docs` command. | Keep commands tied to the selected installed runtime. This audit does not add a CLI route or change runtime behavior. |
| Agent/plugin documentation | `.agents/skills/attune-harness/`, its browser/workflow references, and `plugin/attune-harness/skills/` retain runtime discovery, inspection versus execution, and authorization boundaries. | Versioned installation and marketplace pins are release-owner work; an older released pin is not evidence of drift by itself. |
| Current technical references | Installation, supported journeys, CLI, operations, consultation, plugins, memory, local/review/recovery/extension/pilot/passage workflows, MCP/A2A, retrieval and documentation generation were inspected for setup and version boundaries. | #300 contains the reviewed refresh. #301 commit `93f161b8` corrects consultation setup to current installation while retaining its feature-introduction and October 12 history. Final integration remains separate. |
| Qualification and compatibility | Software qualification, coverage, Windows reliability, compatibility and envelope contracts retain their scoped claims. | Passing Server CI does not establish Windows 11 desktop/shell, all storage/recovery, live providers or human acceptance. No old table is promoted to new qualification. |
| Project, opportunity and readiness summaries | #300 updates the documentation index, project checkpoint, opportunity register and release summaries. | Keep release blockers and observed outcomes tied to their exact heads. The audit adds its archive section at the end of the index to avoid #300's current-walkthrough insertion. |
| Historical guides, release records and results | The [archive catalog](archive/README.md) labels eighteen versioned records as historical and links originals. Dated results/designs and specifications retain their dates and status. | Original files, headings, commands, source hashes and citations remain unchanged. A historical candidate's “unpublished” wording describes that candidate, even after a different artifact was released. |
| Training derivatives | Versioned Markdown procedures, five HTML prototypes and two prototype notes, website historical projections and original 1.5.0 screenshots remain historical. | No 1.5.1 deck or refreshed standalone HTML training set was found in the tracked Harness tree. Separately retained editable decks have not been exhaustively located or qualified. |

## File inventory and review limits

[The file inventory](documentation-audit-1.5.1.json) enumerates all 350 tracked
Markdown files and HTML prototypes in the #300 candidate: 305 Markdown files
under `docs/`, plus integration/project material and five HTML prototypes and two prototype notes.
Each row records its path, heading, category, version literals and SHA-256.
Additional snapshots inventory 31 canonical Help/renderer inputs, 24 website
export files, five historical training inputs and #2575's eight entry-point files.

| Category | Files | Meaning |
| --- | ---: | --- |
| Current references | 39 | Current user, operator and project guidance; review does not mean every historical measurement was rerun. |
| 1.5.1 preparation | 3 | Walkthroughs, draft release notes and readiness. |
| Versioned archive | 18 | Earlier tutorials, first repair, migration and release/readiness records. |
| Dated evidence or design | 171 | Original results, receipts, research, proposals and design notes. |
| Specification or decision record | 76 | Each retains its own approval and delivery status; specification text alone does not prove delivery. |
| Agent integration | 9 | Skills and workflow references. |
| Historical prototype material | 7 | Five original HTML prototypes and two Markdown notes, not newly qualified release tutorials. |
| Project support | 27 | Project instructions, example/experiment notes and other support material. |

This is an exhaustive file classification for the named tree and a targeted
content/entry-point audit. It is not a claim that every sentence, external link,
source symbol, old receipt or live service in the corpus was independently
requalified. Version literals are search evidence, not an instruction to replace
them. The archive keeps original paths so links and artifact pins survive.

## Website and generated exports

Website source main `6695106f8a185e310b7b8f9d463395cb0752c22a` was inspected beside
publisher #2574 (`dcaa5f05f54dc9470783a15613730b85fa4f350b`) and entry points #2575
(`4bf232f88ee2248b1b89ad8c3f218fdc3a94d224`). Fresh public HTML confirmed the old
Docs quick start still serves 1.4.0; a search-engine rendering instead returned
older 1.3.0 content, so it was not used as the current-state authority.

| Surface | Finding and treatment |
| --- | --- |
| Main Navigation | `/docs#harness-docs` still led to the page containing the old runnable quick start. The separate website correction points directly to `/harness/help/`. |
| Docs default and `#quickstart` | #2575 retained the full historical 1.4.0 setup in the active section. Its owner is replacing that section with a current notice, canonical guide and explicit archive link. The top Quick Start action targets `/harness/help/get-started/`. Keep `#harness-docs` and `#quickstart` working. |
| Historical 1.4.0 quick start | The separate archive route `/harness/archive/1-4-0/#quickstart` preserves the original 4,538-byte JSX section byte-for-byte. It adds a historical wrapper and a link to the canonical current guide. Section SHA-256: `3d9eb727c5e5f7e37e25e07366102261dfe1a4e5ff2df0b2c088380c8a670ba0`. |
| Pricing/open source | Main still recommends installing `attune-harness[all]==1.4.0`. The separate correction removes that stale command, uses #2575's canonical release adapter, links current setup and keeps the package link on the published baseline until publication. |
| How it works | The Help action still points to `/docs#harness-docs`; the separate correction points to canonical Help. Historical demo assets remain unchanged. |
| Homepage, FAQ, footer and sitemap | #2575 owns the existing refresh and publication-aware metadata adapter. Its standalone build needs #2574's generated JSON. Neither owner nor this audit claims a final integrated production deployment. |
| Canonical publisher | #2574 owns `website/public/harness-help-static/**`, export/import scripts, Help rewrites and cutover tests. Re-import reviewed merged canonical source; verify exact exported file sets/hashes and the actual HTTP routes. |
| Earlier generated training | `website/content/harness-help/tutorials-1.3.0.source.md`, `walkthroughs.generated.json`, `walkthrough-provenance.json` and `next-release.json`, plus their historical projector, remain original evidence. They are not current 1.5.1 source. |
| Framework docs and companion projects | Earlier Attune AI references and generated `framework-docs` are separate-project material. Do not silently rename them to Harness 1.5.1. General accuracy of that separate corpus was not requalified here. |

## Committed website corrections and delivery order

The Docs owner committed the current Quick Start and compatibility-anchor
correction as `948ba152259b4e5810f506f498f907dd5cc3f4d5` in website #2575.
The separate [archive prerequisite #2580](https://github.com/Smart-AI-Memory/attune-ai/pull/2580)
at `59ddfa95f2c8a93f667843d32b9fa8bfb44cd5cb` preserves the old block unchanged
and builds against website main independently. [Entry points #2579](https://github.com/Smart-AI-Memory/attune-ai/pull/2579)
at `d21e1c6ea9b7b9123569e686c65c96f1aa2a89d5` now contains only Navigation,
pricing, how-it-works and its handoff; an ordinary follow-up commit removed the
archive addition from its net diff while preserving the original commit.

The archive, #2574 publisher and later Author-reference prerequisite #2581 can
integrate independently; all must precede #2575, followed by #2579. This avoids
active Docs links depending on destinations supplied only by a later PR. All remain drafts. A passing
disposable combination does not establish a standalone branch, production
deployment or package publication. Exact local verification and current
unverified checks belong to each PR description.

## Migration correction and remaining source-index links

The original active website links reached an explicitly historical 1.0.0 guide.
The [current migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/93f161b8e65bf86b4a7670e899ff96ff260644f1/docs/migration.md)
is now committed in #301 at signed `93f161b8e65bf86b4a7670e899ff96ff260644f1`.
It distinguishes 1.5.1 preparation from published 1.5.0 and states current
Windows limits. All 21 relative targets and anchors resolve. The historical
1.0.0 guide and consultation historical tail remain byte-identical.

Canonical #299 `fd42e9cb` updates the common documentation ref; publisher #2574
`f2e35afd97ec48976000ec85a4afa162a01cb3c6` imports that source. Only
`preparation.documentation_commit` changes from the previous preparation
metadata; behavioral, validation, tutorial and historical-observation identities
remain unchanged. #2575 `edd14d471cff759e505695c5e1c83685d67dd717` changes both
Docs migration paths to `docs/migration.md` through the existing adapter.
Both actual browser clicks independently reached that exact committed guide.
This closes the website's current-to-historical mismatch in the committed
dependency combination; it does not qualify final main or production.

Two current-reference dispositions remain pending final #301 reconciliation
after #300 and #305 reach main:

- `docs/project-plan.md` S9 still links the historical file as its current
  migration guide; switch that link to `migration.md` while retaining unfinished
  acceptance and evidence gates.
- The old `docs/README.md` index row needs an explicit historical 1.0.0 label.
  Preserve its original target and the underlying record.

The release owner accepted both corrections and is avoiding competing writes
to #300's project-plan lane and #305's index end-context. Their through-main
dependency remains open under the current no-merge instruction. The frozen
inventory JSON records its original snapshots and is unchanged.

## Author reference placement

The #2575 owner removed the large Attune Author section from the Harness Docs
flow in signed `0eb99800a607386260dc8171516ef9372547b654`, a separate follow-up
to the migration commit. A concise reference beside the earlier Attune AI
references preserves the visible `/docs#attune-author` anchor and links the
dedicated page. Separate main-based [prerequisite #2581](https://github.com/Smart-AI-Memory/attune-ai/pull/2581)
at `eb102ccf37e85b7b73977cea7c2991bb537594c6` supplies `/attune-author/` and
retains `#attune-author`. Its 1,940-byte section exactly matches website main
`6695106f8` and Docs `948ba152`, SHA-256
`ef3183373161ea0453f17da04dc67f0e18b2e42cb2feae92188798e58b9d9990`.
The destination identifies the earlier project reference and links back to
Docs. Its standalone build, HTTP and bounded mobile/keyboard checks pass.

The final disposable five-input combination uses publisher `f2e35afd`, Docs
`0eb99800`, archive `bb7841b0`, Navigation `86489edb` and Author `eb102ccf`.
78 website tests, TypeScript/125-page production build, lint and the
12-page/24-file export check pass. All 33 HTTP checks pass, including 23 exact
publisher responses, current migration links, concise reference, Author page,
archive, sitemap exclusions and unknown-topic/import-metadata 404s. Actual
Docs anchor to Author to Docs, current Quick Start, migration and Navigation to
Help to Get started journeys pass. Verified 320/390-pixel checks show no
page-wide overflow; Enter links, root skip-link order and visible focus pass.
The Docs owner independently inspected all 16 overlaid Git blobs, the result
files and desktop journey. This new receipt is separate from the prior
migration-only combination and does not establish final main or production.

## Bounded mobile and keyboard checks

On the exact four-input local website combination above, the Navigation and
archive journey was checked at 390 and 320 CSS pixels. Neither Docs nor the
archive overflowed the page; wide historical code stayed inside its own
horizontal scroller. The labelled mobile menu opened and closed with Enter,
exposed its expanded state and reached canonical Help by keyboard. Focus had a
visible three-pixel outline. The archive's skip link moved the next tab stop
into its main content, the PowerShell disclosure expanded by keyboard, and
local fragment targets existed. Both pages had one main region and one primary
heading. These are bounded presentation and keyboard observations, not full
accessibility conformance, screen-reader testing or independent user acceptance.

## Attune AI deprecation direction

Patrick subsequently directed deprecation of Attune AI and a move to Harness
1.5.1 instead of routine Attune AI dependency or feature maintenance. The
separate [README notice #2582](https://github.com/Smart-AI-Memory/attune-ai/pull/2582)
and #2575 website notices remain their owner's lane. #2579 commit
`39273d3a1660eb1646b9f8b105fd1936534d9775` adds notices on Pricing and How it
works using the existing release adapter; Navigation already targets canonical
Help. #2581 commit `1a876991265ad69135a8f3ba6a73f7f31695d90d` labels the retained
Attune AI installation command historical in the Author wrapper and links the
current Harness Quick Start. It adds no adapter dependency to that independent
prerequisite. The original Author and 1.4.0 archive blocks remain byte-identical.

Deprecation does not establish feature parity or migrate saved work. Preserve
existing environments and published artifacts; the standalone attune-help
reader is a separate project. The fresh package-index check still reports
published 1.5.0 with no 1.5.1 artifact. Current setup must continue to distinguish
candidate validation from a published installation.

The [reviewed current migration correction](https://github.com/Smart-AI-Memory/attune-harness/blob/0dc82db327af9eae41f7bf812480cc76d2cd7fc7/docs/migration.md)
is signed and committed in #301 at `0dc82db327af9eae41f7bf812480cc76d2cd7fc7`.
It records deprecation while preserving the unpublished target, environment,
saved-data and parity limits. All 21 relative links and their target bytes are
unchanged from the earlier verified guide; the historical 1.0.0 record remains
byte-identical. Canonical #299 `d98b31d06b3a3fadbbf2066b874a69df9f325139`
and publisher #2574 `0d6ea8bc758e6a799f8b54f09e3db9c64b97f729` now supply the
reviewed common documentation pin and normal reimport. Five payloads change;
nineteen retain their exact bytes. Only `documentation_commit` changes in
preparation metadata. This closes the current website-to-old-source mismatch
in the committed combination; final main and production remain separate gates.
Preserve behavioral, validation, tutorial,
historical observation and frozen audit-inventory identities. No package
metadata, archival setting, runtime, dependency, workflow or credential change
is included in this documentation phase.

The separate deprecation-notice combination uses publisher `f2e35afd`, Docs
`fe82c8b3`, archive `bb7841b0`, entry points `39273d3a` and Author `1a876991`.
All 16 overlaid blobs match their commits. Its 78 website tests, lint, export
check and TypeScript/125-page production build pass. Fifteen HTTP checks verify
the notices, current guide targets, preparation-only install gate, published
fallback, legacy anchors and 404 behavior. Actual browser checks reach Get
started and open the FAQ deprecation answer with Enter and visible focus.
The six changed notice surfaces have no page-wide overflow at verified 320/390
CSS pixels. These narrow checks do not extend the earlier accessibility or
independent-user acceptance claims. The build-directory cleanup and initial
probe corrections are retained in local evidence; no product change cleared
them. This receipt remains bound to the earlier publisher and does not qualify
the later source-ref/export update.

The final reference-delta receipt instead uses publisher `0d6ea8bc` with the
same four other inputs. All 16 overlaid blobs match; fresh 78 website tests,
changed-input lint, export checks, TypeScript/125-page build and fifteen HTTP
checks pass. Both actual Docs migration actions reach `0dc82db3` and display
deprecation, publication and data-preservation limits. Docs Quick Start and
Navigation to Help retain the current preparation/published distinction. No
unreleased 1.5.1 index-install command is exposed in preparation HTML. Earlier
mobile/keyboard observations remain at their original notice inputs; this
reference-only delta does not requalify broader accessibility or user acceptance.

## Release and delivery gaps

After the initial audit snapshot, the release owner verified #303 merged as
main `e78576eda9b99369472f3f58f768230a4a2656c9`, with the merged tree matching
its tested reader prerequisite. The later #304 diagnostic-reader correction
`a2aa2ff252298073ee343a8052297d4ec82efc0c` is now API-verified merged as
`e9c4262ed549ea39b2b9e0f1ca0c1046e0ec7cb1`. Its diagnostic readiness does not
establish a cause or runtime repair for the separate Windows failures.
#299 and #300 retain failed old-head Windows observations and now have normal
owner updates through current main; fresh qualification and final #301 source
integration/artifact checks remain separate. The release owner also retains a
new saved-store contention failure before installed qualification, separate
from the earlier Python build-future timeout and main's Node-child timeout.
Their underlying causes remain unproven. Diagnostic revisions and passing
schedules do not establish a runtime latency repair or release readiness.

The website PRs remain drafts. #2574 needs reviewed merged canonical source;
#2575 needs that publisher's JSON through main. A separate website automation
job reported HTTP 401; credentials/settings remain the repository owner's lane.
This task changes neither credentials nor production state.

Before declaring the documentation release complete:

1. Integrate owner changes through main and reconcile all exact source and
   documentation identities. Keep each draft's dependencies visible.
2. Run documentation and export checks on the integrated head and exercise
   Navigation, Docs quick start, FAQ, footer, pricing, goals and archive links
   through the built website.
3. Select and qualify the final 1.5.1 artifact. After separately authorized
   publication, verify its bytes and clean package-index installation before
   changing canonical publication status or released-install claims.
4. Rebuild/import Help from reviewed merged source, obtain separate website
   approval and verify production routes after deployment.
5. Locate separately retained decks/HTML distributions and either mark them
   explicitly historical at their distribution points or qualify replacements.
   The bounded mobile/keyboard observations above do not qualify those
   distributions. Full accessibility and independent user acceptance remain
   unverified.

See the draft PR description for checks on this archive/audit change. Historical
test counts and the earlier owners' receipts remain bound to their original
sources and artifacts.
