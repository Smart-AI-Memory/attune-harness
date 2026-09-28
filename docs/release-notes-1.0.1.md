# Attune Harness 1.0.1 release notes

`1.0.1` fixes documentation links on the PyPI project page. PyPI renders the
package README outside GitHub, so repository-relative links in `1.0.0` led to
404 pages. The README now links to release-specific GitHub documentation, and
the link check catches this class of error before a future release.

The runtime files, dependency pins and v1 compatibility contract are unchanged
from `1.0.0`. Use an isolated environment:

```sh
pipx install 'attune-harness[all]==1.0.1'
```

See the [1.0.0 release notes](release-notes-1.0.0.md) for the stable scope,
qualification evidence and limits. This patch does not add model or platform
qualification. The originally planned fourteen days of candidate observation,
named non-programmer walkthrough, ordinary host and memory observations, and
migration trial remain unverified.
