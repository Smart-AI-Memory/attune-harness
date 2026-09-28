# Attune Harness 1.0.0rc2 release notes

`1.0.0rc2` is a release candidate for the v1 compatibility contract, not the
stable 1.0 release. It corrects the `voyage` extra's dependency metadata: a
fresh `attune-harness[all]` or `attune-harness[voyage]` install now selects
`httpx2==2.13.0`, which the signed Voyage plugin's import closure requires.
An unconstrained rc1 install could select `httpx2==2.13.1` and refuse that
plugin path. No saved-state format or public CLI contract changed.

The [rc1 release notes](release-notes-1.0.0rc1.md) describe the frozen
candidate surface and bounded qualification claims. Rc1 remains available on
PyPI as a historical candidate; its published files and evidence are retained.
Use rc2 for new installation and observation after it is published. The exact
rc2 commit, distribution hashes and qualification result must come from the
approved publishing run.

After publication, install `attune-harness[all]==1.0.0rc2` in a fresh
environment. Preserve existing environments and saved state. The observed
candidate period starts from a published, installed rc2 and requires real
usage evidence before a stable 1.0 decision.
