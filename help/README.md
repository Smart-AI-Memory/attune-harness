# Harness Help Center

Harness owns the Help Center's Markdown, version manifest, static renderer and
verification. The existing public URL remains
<https://smartaimemory.com/harness/help/> until a separate website cutover.

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

Edit the registered Markdown files and `manifest.json` together. Verify changed
commands and labels against the named release, and record actual walkthrough
results and limits. Check the built HTML's local routes and fragments. Keep
unpublished features out of the current guides. Historical walkthroughs remain
in their original versioned files under `docs/`.

The first PR supplies this self-contained site. A separate website PR will
publish or route to the verified artifact and retire the old implementation
after the replacement is available. A source PR does not deploy the Help Center.
