# Harness Help Center

Harness owns the Help Center's Markdown, version manifest, static renderer and
verification. The existing public URL remains
<https://smartaimemory.com/harness/help/> until a separate website cutover.

## Find the source before editing

[The content map](../docs/content-map.json) identifies the authored Help and
training sources, generated outputs, public entry point and proposed website
routes. Help lives in `help/`; the six-lesson HTML course lives in `training/`.
Edit those maintained sources rather than a website copy, temporary preview or
old worktree handoff. `training/build_course.py` derives interactive HTML, static
reading pages and presenter scripts from each lesson's JSON.

Use task names in website navigation: **Get started**, **Learn Harness**,
**Do a task** and **Reference**. Keep **Historical archive** secondary. Archive
superseded guidance, rather than every older document. Preserve existing URLs
and evidence; a supported installation or recovery guide remains current while
it is useful. The proposed training route is not deployed by this source PR.

## Current onboarding and historical evidence

The goals guide is also canonical Harness content. Port its authored HTML, local
worksheet data, styles, controls and historical 1.5.0 captures from the reviewed
website commit without changing saved example wording. The static renderer acts
as its projector: validate markup, IDs, control bindings, 21 goals, six testing
FAQs and assets before exporting. Keep the learning category first and the
compact clickable rows; add a prominent goals link to the landing page.

The build must preserve native disclosure behavior without JavaScript and the
unapproved local worksheet with JavaScript. Hash its script and assets alongside
the Markdown output. Do not add a Next.js or provider runtime to the source build.
The existing website goals route would shadow the cutover rewrite; its owner
will retain website entry points while this export owns all Help routes.

Get started names published 1.7.0; its release record identifies the immutable
software source, artifacts and check boundaries. The reference guides
keep their published 1.5.1 identity. Their prerequisite links select the explicit
1.5.1 practice setup in Get started, which activates that release in an isolated
environment and defines its immutable example checkout as `R`. The separate
1.7.0 preparation links do not promote those historical observations to new
acceptance evidence. The manifest distinguishes the current
published version from that historical reference version.
Published 1.5.0 observations, captures and the preparation record keep their
original identities. A metadata-only validation wheel remains candidate evidence;
do not relabel it or an older result as a new published-artifact walkthrough.

Rejected alternative: retaining a separate React goals implementation would
restore two content owners and allow the cutover to discard either navigation
or controls. A portable HTML/CSS/JavaScript page keeps the source ownership and
the existing public URL together. Verify it through the real website rewrite,
including the worksheet, deep links and historical images, before cutover.

## Design and scope

Update the seven former 1.3.0 guides for published 1.5.0, correct the missing
retrieval session directory, put setup before dependent steps, and provide a
contents list and stable links to workflow headings. Preserve retained 1.3.0
and candidate evidence; do not relabel those observations as published-wheel
checks. The Harness changelog supplies changes and chronology. Released source
and fresh walkthroughs establish the current commands and control labels.

The build must render all registered topics, code, tables and nested headings;
resolve internal routes and fragments; and distinguish literal examples from
headings. It must refuse an existing output directory and invalid topic paths.
It makes no network or model calls. Account settings, deployment, production
routing and removal of the old website implementation belong to the cutover.

A disposable Markdown probe confirmed that the pinned renderer generates unique
IDs for repeated headings, includes second- and third-level headings in its
contents list, and excludes fenced example headings. The earlier retrieval
command reproduced the published source's session-directory refusal before any
provider work. Those probes informed the renderer and command corrections.

Rejected alternative: adding a second Next.js application would duplicate the
website's runtime and dependency stack for a static documentation site. A small
static build keeps Harness independent of Attune AI and gives the later website
cutover a portable artifact.

## Build and preview

Install the documentation dependency in a separate environment:

```sh
python3 -m venv /private/tmp/harness-help-build-env
/private/tmp/harness-help-build-env/bin/python -m pip install -r help/requirements.txt
/private/tmp/harness-help-build-env/bin/python scripts/build_help.py --output /private/tmp/harness-help-site
mkdir -p /private/tmp/harness-help-site/harness/learn
cp -R training/1.7.0-preparation training/archive /private/tmp/harness-help-site/harness/learn/
python3 -m http.server 8766 --bind 127.0.0.1 --directory /private/tmp/harness-help-site
```

Open <http://127.0.0.1:8766/harness/help/>. Choose unused environment and output
directories for a new run. Generated output stays outside the repository.
`build.json` records source hashes for the Help export. The copied course
files let you follow the Help-to-lesson links in the same preview. The website
imports those files separately. The renderer needs no provider SDK or Harness
runtime.

## Maintain the guides

Fenced examples use the shared `code-copy.js` enhancement. Click **Copy** to
copy a block's exact text; **Copied** appears after the clipboard write succeeds.
If the browser refuses access, the text is selected and manual-copy instructions
appear. Without JavaScript, examples remain readable and selectable. The script
follows the goals guide's clipboard/fallback pattern without loading its worksheet
controller. Keep controls outside code, preserve example wording and verify both
success and failure before changing this behavior.

Edit the registered Markdown or goal master and `manifest.json` together. Verify changed
commands and labels against the named release, and record actual walkthrough
results and limits. Check the built HTML's local routes and fragments. Keep
unpublished features in explicitly labeled preparation guidance. Historical walkthroughs remain
in their original versioned files under `docs/`.

The first PR supplies this self-contained site. A separate website PR will
publish or route to the verified artifact and retire the old implementation
after the replacement is available. A source PR does not deploy the Help Center.

## Maintain 1.7.0 onboarding and historical guidance

Published 1.7.0 onboarding uses the existing `/harness/help/get-started/`
route with an explicit topic version and published status. The global manifest
reference remains 1.5.1 so unchanged guides and goal captures keep their original
identities; `published_version` names the current 1.7.0 release. Each page states
its version and status.

Preserve the 1.5.1 and 1.6.0 release records, historical verification records
and goals captures. The 1.7.0 guide links to the
[GitHub release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
for the published source, artifacts and hashes.

The existing website importer in `attune-ai/website/scripts/harness-help-export.mjs`
validates and imports the static export. The current website importer expects
the 1.6.0 metadata. Update that check and refresh both the Help and training
exports from the same reviewed, merged Harness commit in the website PR.
Verify the lesson setup route before serving the refreshed Help navigation.


## Reproduce 1.7.0 preparation

`1-7-0-preparation.md` remains at its original URL under the archive, with
`noindex,follow`. Its software checkpoint is main `9ece` and rehearsal
41961339343. Keep the rehearsal results and any published-wheel observations
separate.
