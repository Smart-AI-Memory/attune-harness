# Attune Harness 1.0.0 release notes

`1.0.0` makes the v1 compatibility contract the default stable install on PyPI.
It promotes the `1.0.0rc2` runtime without a CLI, API or saved-state format
change. The rc2 correction to fresh `[all]` and `[voyage]` dependency resolution
is included. Install in a separate environment:

```sh
pipx install 'attune-harness[all]==1.0.0'
```

The supported core covers explicit plan, acceptance, build, review, fix, test
and saved-task inspection with local receipts and bounded execution. The
[compatibility list](compatibility.md) states the surfaces protected from
incompatible changes without deprecation. The [qualification guide](qualification.md)
and [README limits](../README.md#what-is-qualified-and-what-is-not) distinguish
installed-wheel checks from model quality and human acceptance. Native
model-driven planning/building and the `memory-native` extra remain experimental.
The signed-plugin profile is for cooperating plugins with explicit grants;
it is not an OS sandbox. Windows memory and `fix`/`test` limitations remain.

The six-platform installed-wheel qualification and exact-main release gate
precede publication; a fresh stable PyPI `[all]` installation verifies it
afterward. The published
rc2 has [six-platform qualification](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36438831710),
a [successful PyPI publication run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36440914448),
and a fresh `[all]` install with `pip check`, installed checks and an offline
Forms plan/accept/build/review journey. These software checks do not
substitute for the originally planned fourteen days of observed candidate use.
At release preparation, a named non-programmer walkthrough, ordinary host and
memory observations, and a candidate migration trial remain unverified. This
is an accelerated release decision; those gaps remain visible in the
[release plan](project-plan.md) and should be followed during stabilization.

Keep Attune AI and Harness in separate environments. Harness does not yet
replace every Attune AI host workflow, hydration writer or MCP tool. The
[migration guide](migration-from-attune-ai.md) names the supported paths and
workarounds; this release does not announce Attune AI deprecation.

Historical candidate notes: [rc1](release-notes-1.0.0rc1.md),
[rc2](release-notes-1.0.0rc2.md).
