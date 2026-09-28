# Attune Harness 1.0.0rc1 release notes

`1.0.0rc1` is a release candidate for the v1 compatibility contract, not the
stable 1.0 release. This page describes the candidate prepared in the repository;
it does not assert that an artifact has been published. The exact published
commit, wheel and source-distribution hashes must come from the approved
PyPI publishing run and its `release-evidence` artifact.

The candidate pins CLI argument choices and defaults alongside the public
Python API, envelope keys, versioned protocol profiles and saved-state formats.
A fixture captured 33 byte-exact files from a clean, installed local candidate
writer. Reader tests cover supported in-place and relocated records, completed
replay without dispatch, and refusal when copied state no longer carries valid
checkout or stage authority. Local saved memories and tasks retain revision
history and optional pending-review checkpoints. `memory recall` now accepts a
single configuration with both native recall roots and saved storage; an explicit
saved record is not automatically served by recall.

The signed Python plugin profile checks signatures and revocation, accepted
effective grants, cooperating imports, bounded subprocesses and host-owned
evidence. The bounded live Voyage comparison produced four matching
request/result pairs across direct SDK and signed-plugin paths, eight paid
stages total. Recorded-response replay and interruption refusal run in platform
qualification. This candidate reuses that retained live evidence; it does not
claim another paid campaign or general retrieval quality.

Limits remain visible: supervised processes are not an OS sandbox for hostile
same-user code; live Voyage evidence was collected on macOS, while the six
platform jobs exercise recorded responses. Native memory and saved storage
retain their documented POSIX limits. GUI, automatic provider fallback, and
full Attune AI plugin/workflow parity are deferred. The
[migration guide](migration-from-attune-ai.md) names what a user should keep
running in Attune AI.

After publication, install `attune-harness[all]==1.0.0rc1` into a fresh
environment using the [runbook procedure](release-runbook.md#production-pypi-release-candidates).
Preserve existing environments and saved state. A useful candidate report names
the version and artifact hash, platform, attempted operation, observed outcome
and a redacted receipt; do not include API keys or private memory contents.

The observed candidate period starts only after PyPI publication and a
verified install. Stable release requires at least 14 days of observed candidate
use, a non-programmer walkthrough, migration and memory findings dispositions,
and a separate final gate review. A change to a frozen surface requires a new RC
and restarts that period.
