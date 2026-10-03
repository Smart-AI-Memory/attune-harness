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

Reject editing a personal catalog in place: independent prepared roots avoid
name collisions, partially replaced installations and dependence on hidden
bundled helper availability. Do not call Codex or change host settings from the
packager. Registration and installation are separate operator commands.

| Command | Owner refusal | Earlier output satisfies it |
| --- | --- | --- |
| `python3 scripts/package_codex_plugin.py ROOT --marketplace NAME` | Existing output, invalid marketplace name, unsafe path or invalid source package | Operator selects a fresh root and valid explicit name; source validation precedes output creation |
| `codex plugin list -c marketplaces.NAME.source_type=\"local\" -c marketplaces.NAME.source=\"ROOT\" --marketplace NAME --available --json` | Unknown catalog, malformed manifest or missing source | Packager writes runtime-observed local catalog and complete plugin under root-relative path |
| `codex plugin marketplace add ROOT` (approval required) | Invalid or conflicting catalog source | Explicit listing verifies this exact prepared root; operator checks existing names before registration |
| `codex plugin add attune-harness@NAME` (separate approval required) | Unavailable plugin or installation policy | Approved registration exposes the AVAILABLE entry; fresh listing verifies selector |

Codex owns the last three refusals, documented by local help and observed listing;
no installation is claimed until the latter two commands are expressly approved
and observed. Tests cover output ownership, valid catalog shape, manifest and
skill-path invariants. Full software suite and wheel qualification remain gates.
