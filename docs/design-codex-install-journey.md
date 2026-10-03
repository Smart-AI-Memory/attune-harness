# Self-contained Codex installation preparation

A3 repairs the first-install guide: it currently requires an absent bundled
`plugin-creator` scaffold and validator. Prepare a fresh local marketplace with
Harness's own checkout script, then let the installed Codex CLI read it by
explicit path. Preparation must not register, install, enable or change settings.

## Evidence before code

On October 1, 2026, local `codex-cli 0.153.4` help exposes `plugin marketplace add`,
`plugin list --available --json` and transient `-c` configuration overrides.
The runtime's own `.agents/plugins/marketplace.json` uses a local source with
`source: local`, a root-relative `./plugins/<name>` path, and AVAILABLE policy.
A disposable catalog using that shape was read with an explicit marketplace
source override: Harness was available, installed false, enabled false.
The retained receipt lives in the private A3 audit evidence directory. No native
inference or installation was performed. This proves CLI catalog discovery,
not refreshed desktop skill selection.

## Choice and refusal boundaries

Extend `scripts/package_codex_plugin.py` with `--marketplace NAME`. Without it,
retain the standalone plugin output. With it, destination is a fresh marketplace
root, containing `.agents/plugins/marketplace.json` and `plugins/attune-harness`.
Validate the name, source manifest and canonical skill's regular-file tree;
reject existing destinations, symlink parents and outputs inside the source
checkout before writing. Existing ancestor filesystem identity also rejects
case aliases on case-insensitive volumes. The tool's
validation is scoped to the emitted Harness manifest/catalog, not a generic Codex
schema validator. Preserve the canonical workflow skill and the cross-review and
roundtable skills from merged #208. Validate all three before creating output;
both standalone and marketplace layouts carry the same complete skill trees.

The emitted Harness contract requires all template metadata fields, their expected
types and nonempty text, fixed Harness identity/repository/license/skills path,
empty capabilities, and one to three default prompts of at most 128 characters.
Unknown or duplicate fields are refused. Plugin versions follow
[SemVer 2.0](https://semver.org/) as Harness's own convention. Codex CLI 0.153.4's
[legacy parser](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/manifest.rs#L309-L312)
only trims an optional version; it does not impose this SemVer requirement.

Reject editing a personal catalog in place: independent prepared roots avoid
name collisions, partially replaced installations and dependence on hidden
bundled helper availability. Do not call Codex or change host settings from the
packager. Registration and installation are separate operator commands.

| Command | Owner refusal | Earlier output satisfies it |
| --- | --- | --- |
| `python3 scripts/package_codex_plugin.py ROOT --marketplace NAME` | Marketplace-name [`ValueError`](../scripts/package_codex_plugin.py#L93-L96); destination traversal/nesting/case alias/existing output/symlink-parent [`ValueError` or `FileExistsError`](../scripts/package_codex_plugin.py#L98-L111); unsafe or incomplete source-tree [`ValueError`](../scripts/package_codex_plugin.py#L75-L88); duplicate or invalid Harness manifest [`ValueError`](../scripts/package_codex_plugin.py#L18-L65) | Operator selects a fresh root and valid explicit name; all source/manifest validation runs before `mkdir` at line 113, and both layouts carry all three skills |
| `codex plugin list -c marketplaces.NAME.source_type=\"local\" -c marketplaces.NAME.source=\"ROOT\" --marketplace NAME --available --json` | Configured catalog-snapshot failures reach [`bail!` with the failed paths](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/cli/src/plugin_cmd.rs#L930-L962). An unknown marketplace can instead [filter to an empty successful listing](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/cli/src/plugin_cmd.rs#L303-L313) | Packager writes a local catalog and complete plugin under the root-relative path. Inspect `available` for the exact `attune-harness@NAME` entry from this root with AVAILABLE policy; empty/missing output is a stop condition, even at exit zero |
| `codex plugin marketplace add ROOT` (approval required) | Invalid local source/root reaches [`MarketplaceAddError::InvalidRequest`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/marketplace_add/source.rs#L17-L61) or [root-validation error conversion](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/marketplace_add/source.rs#L90-L96); a name already added from another source returns [`InvalidRequest`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/marketplace_add.rs#L134-L143) | The operator first verifies the exact prepared available entry, inspects existing names/sources and approves this root's registration; no preparation or listing grants that approval |
| `codex plugin add attune-harness@NAME` (separate approval required) | Missing or ambiguous selector reaches [`bail!`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/cli/src/plugin_cmd.rs#L901-L925); snapshot loading has the same refusal above. NOT_AVAILABLE/product policy returns [`PluginNotAvailable`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/marketplace.rs#L271-L291), and configured marketplace restrictions can [return an install-resolution error](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/manager.rs#L2031-L2047) | Approved registration plus a fresh exact-selector listing establishes catalog selection and AVAILABLE/no-product-restriction metadata. The operator still inspects applicable host restrictions and separately approves installation; this does not guarantee installation succeeds |

All external source citations pin the official `rust-v0.153.4` commit
`3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`; these Rust error returns and `bail!`
calls are the counterparts of Python `raise`. Listing is catalog discovery,
not a full manifest-validation or install receipt. The separate plugin-details
path can [refuse a missing source directory or invalid manifest](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/manager.rs#L2614-L2635);
this is not an additional guarantee from the basic listing command.
No registration or installation is claimed until those commands are expressly
approved and observed. Tests cover output ownership, complete Harness metadata,
version/prompt boundaries and skill-path invariants. Full software suite and
wheel qualification remain gates.
