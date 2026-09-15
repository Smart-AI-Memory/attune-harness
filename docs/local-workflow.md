# Local verification and retrieval

This milestone adds two independent optional features. They run locally without
provider sign-ins, model calls or embedding downloads. Verification checks only
the claim types supported by attune-verify; retrieval returns source material,
not a generated or verified answer.

## Run the prepared environment

From the Harness directory:

```sh
.venv-workflow/bin/attune-harness verify examples/local-workflow/project/guide.md --context examples/local-workflow/context.json --output examples/local-workflow/verification-report.json
.venv-workflow/bin/attune-harness retrieve "quartz retention policy" --corpus examples/local-workflow/project --output examples/local-workflow/retrieval-report.json
```

Both commands print JSON. The optional output file receives the same report,
written atomically. Choose an existing directory and a distinct `.json` output;
input documents, context files, symlinks and repository metadata are protected.
`python -m attune_harness` still runs the original deterministic demo.

## Meaning of the results

| Operation | Status | CLI exit | Meaning |
|---|---|---|---|
| verify | verified | 0 | Extracted supported claims satisfy the library's strict policy |
| verify | refuted | 1 | A checked claim is contradicted by its declared source |
| verify | unknown | 1 | Claims are unverifiable, checks are incomplete, or no supported claims were extracted |
| retrieve | retrieved | 0 | Local keyword search returned sources; this is not verification |
| retrieve | no_results | 1 | The selected corpus yielded no keyword matches |
| either | unavailable | 2 | The optional dependency is missing, incompatible or cannot load |
| either | failed | 2 | Input, library execution, result contract or report output failed |

Reports include a schema revision, unique request ID and dependency version.
Verification preserves native claim IDs, statuses, evidence, source locations,
findings and counts. Document/context SHA256 values identify the input artifacts;
they do not freeze all referenced files or interpreter state. Strict outcomes
come from `VerifyResult.passes()` and `status`, not its legacy error-only `ok`.

The context is an explicit attune-verify JSON manifest. Paths inside it resolve
relative to the manifest; links inside Markdown resolve relative to the document.
It is trusted configuration: a selected interpreter and allowlisted help commands
can execute installed code. `semantic` generation/judging is not enabled by this
adapter. Consult attune-verify's own public context contract for supported fields.

Retrieval uses `DirectoryCorpus` and `KeywordRetriever` directly. Sources include
corpus-relative paths, original-byte SHA256, keyword score, match reason and a
500-character excerpt. Scores are ranking signals, not calibrated confidence.
The corpus fingerprint identifies the library's loaded text (with normalized
newlines); file hashes preserve original UTF-8 bytes, including CRLF. Returned
instructions remain source data. No model consumes or executes them here.

Input bound: 4 MiB per file; retrieval additionally permits at most 1,000 Markdown
files and 16 MiB total. `k` is 1–20. The adapter detects changes during initial
loading; these checks are not a sandbox against concurrent filesystem mutation.
DirectoryCorpus's selected `**/*.md` set defines the corpus; external symlink
sources in that set are rejected. Reinvoke to check updated documents or sources.

## Reproduce the dependency boundary

`dependency-lock.json` records full Git commits, reproducible wheel hashes and
build tool versions. `requirements-workflow.lock` records the local validation
environment's package versions. Both Attune wheels are built from immutable
snapshots, leaving the original checkouts unchanged. The pins identify tested
sources, not the current remote branch or current PyPI release.

```sh
python3 scripts/build_local_dependencies.py
python3 -m build --wheel --no-isolation
python3 -m venv .venv-local
uv pip install --offline --python .venv-local/bin/python -c requirements-workflow.lock --find-links dist/dependencies 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl[verify,rag]'
python3 scripts/check_installed.py --python .venv-local/bin/python --mode all
```

The offline command requires the third-party wheels in the local uv cache. It
fails rather than downloading missing distributions. Without `--offline`, a
normal install can obtain those dependencies from the configured package index.
Do not use `--no-deps` for a new rag installation; it has regular Python library
dependencies. The verify extra has no transitive runtime requirements.

The installed checks run from a temporary directory using `python -I`, execute
real library calls, verify exit statuses and JSON output, test strict negatives,
and confirm provider SDKs and attune-ai are absent. Core-only, verify-only and
rag-only environments are also exercised independently. The source tests use
`.venv-workflow/bin/python -m pytest tests` with both pinned dependencies installed.

## Boundary of this milestone

The feature functions are importable as
`attune_harness.verification.verify_document` and
`attune_harness.retrieval.retrieve_sources`. Their operation reports are distinct
from the model execution Receipt. A caller can retain them as evidence for an
accepted task; no general model tool loop or authority registry has been added.

The verification checkpoint preceded retrieval implementation. This completes
the authorized local feature milestone while the wider review workflow, forms
intake, native tool access, direct-model/ACP comparisons and portable recovery
remain future work. Claude qualification remains on hold.
