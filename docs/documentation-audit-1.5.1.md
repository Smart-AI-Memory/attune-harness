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
| Current technical references | Installation, supported journeys, CLI, operations, consultation, plugins, memory, local/review/recovery/extension/pilot/passage workflows, MCP/A2A, retrieval and documentation generation were inspected for setup and version boundaries. | #300 contains the reviewed refresh. The consultation introduction still recommends 1.4.0; #301's owner has accepted a correction to link current installation while retaining feature-introduction history. |
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

## Release and delivery gaps

After the initial audit snapshot, the release owner verified #303 merged as
main `e78576eda9b99369472f3f58f768230a4a2656c9`, with the merged tree matching
its tested reader prerequisite. Separate #304 timeout diagnostics remain open.
#299 and #300 retain
failed old-head Windows observations; #301's green head still needs their
integration through main and a fresh final artifact. The GUI timeout's cause
remains unknown. Diagnostics and later passing schedules do not establish a
runtime latency repair.

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
   Accessibility, mobile presentation and independent user acceptance remain
   unverified unless recorded by their owners.

See the draft PR description for checks on this archive/audit change. Historical
test counts and the earlier owners' receipts remain bound to their original
sources and artifacts.
