# Harness Help Center

Harness owns the Help Center's Markdown, version manifest, static renderer and
verification. The existing public URL remains
<https://smartaimemory.com/harness/help/> until a separate website cutover.

## Published 1.5.1 guidance and historical evidence

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

Versioned guidance names published 1.5.1 and its immutable release source. The
release record identifies the public artifacts and software-check boundaries.
The existing Get started route stages 1.6.0 onboarding with a topic-specific
preparation label; the site-wide manifest remains on published 1.5.1.
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
python3 -m http.server 8766 --bind 127.0.0.1 --directory /private/tmp/harness-help-site
```

Open <http://127.0.0.1:8766/harness/help/>. Choose unused environment and output
directories for a new run. Generated output stays outside the repository.
`build.json` records source hashes for the export. No provider SDK or CLI runtime
dependency is added by this build dependency.

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

## Stage 1.6.0 documentation without replacing published guidance

The selected next release is 1.6.0 with Python >=3.12. Stage onboarding at the
existing `/harness/help/get-started/` route with that topic's version set to
`1.6.0` and status set to `preparation`. Reuse the README's installation and local
demonstration commands, reviewed source links and existing goal guides. Keep the
global manifest on published 1.5.1 so unchanged topics retain their labels.

Preserve `1-5-1.md`, `release-1.5.1.json`, historical records, goal source and
assets under their existing identities. The local release preparation guide is
`docs/release-preparation-1.6.0.md`. Staging the existing route does not create a
versioned 1.6.0 Help route, publish a package or deploy a website. The renderer's
1.5.1 record references remain separate from the new onboarding topic.

Build with the existing renderer, validate internal links and provide local
rendered-file previews for review. A preview is not a server or a new website
deployment.
