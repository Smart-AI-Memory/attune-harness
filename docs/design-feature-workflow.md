# Local verification and retrieval milestone

Status: executable bounded increment, requested by Patrick (steps 1–4). No
provider calls; Claude qualification stays pending. Harness owns the operation
envelope and CLI; the libraries retain checking and retrieval semantics.

Dependency decision: use attune-verify 0.6.0 at
`a877e31a17ee088c3163dec29eba4a31a3a06ff0` and attune-rag 1.2.0 at
`f00815d22cfa28c0abca6ab7b4bcd5d6a1059dcd`, observed cached origin/main commits.
Build wheels from immutable `git archive` snapshots. The verify checkout is one
commit behind; the rag checkout is behind and dirty. Neither checkout is changed.
These are pinned local sources, not a claim about current remote/PyPI freshness.

Scratch evidence before Harness source edits: both dependency wheels built from
the pinned snapshots and installed offline in an isolated venv with dependencies.
The real verify API returned verified for an existing local link, refuted for a
missing link, and unknown for an external link and for prose with no supported
claims. KeywordRetriever returned the expected Markdown source for a matching
query and no hits for an unrelated token. No paid generation or semantic judge
was invoked. CLI/library source confirms semantic checking is opt-in.

Implementation: optional extras `verify` and `rag` pin the tested versions; imports
are lazy and missing/wrong versions yield explicit unavailable reports. A small
operation envelope records request ID, operation, status, dependency version,
artifact SHA256 and native library payload. It does not certify arbitrary prose.
`verify` reads one Markdown file and an explicit trusted context manifest, calls
the public verify API with document_path, and preserves its strict outcome and
per-claim evidence. `retrieve` uses DirectoryCorpus and KeywordRetriever to return
ranked source references, hashes and excerpts; no hits means no_results, never a
verified answer. Reports are JSON on stdout and optionally written atomically to
a distinct .json file. CLI exits: 0 verified/retrieved, 1 refuted/unknown/no_results,
2 invalid invocation/unavailable/failed. Existing no-argument demo remains usable.

Cases: valid/broken/unverifiable/no claims; missing/wrong dependency; malformed
library response; wrong root, unreadable or oversized input, context changes
during checking; output/input collision, symlink output, failed output write;
matched/no-match/empty corpus; source changes between retrieval calls; core-only
install; extras installed independently; invocation outside the source checkout.
Declared context is trusted configuration: interpreter and allowlisted help
commands can execute code. Semantic judge and automatic model use are absent.
Input/corpus size bounds protect this local CLI, not adversarial filesystem races.

Rejected alternative: rebuild verification policies and evidence extraction in
Harness. The 0.6.0 public result already owns them. Rejected alternative: wire all
RAG/model features now; local keyword retrieval establishes the optional boundary
before adding generation, model downloads or calibration claims.

Acceptance / execution order:
1. Record exact dependency commits, wheel hashes and installed versions.
2. Ship verification adapter + CLI with real-library failure-sensitive tests.
3. Run installed-wheel journeys, including core-only absence and strict negatives;
   record a verification checkpoint before retrieval source edits.
4. Add the local retrieval adapter, rerun relevant package checks, and retain a
   runnable example plus a milestone receipt. Broader phase qualifications remain
   open; this is the local feature milestone, not the complete review workflow.
