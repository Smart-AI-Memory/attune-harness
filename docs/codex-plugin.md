# Attune Harness in Codex Plugins

**Attune Harness** is a Codex plugin containing the existing
[Harness workflow skill](../.agents/skills/attune-harness/SKILL.md). It is separate
from **Attune-AI**. The plugin adds discovery and workflow instructions; install
the `attune-harness` Python runtime separately as described in the
[CLI guide](cli-guide.md#codex-skill).

The plugin version is independent of the Python package version. This initial
plugin is 0.1.0. Its skill is copied from the checkout, and since 1.1.0 a test checks
the commands it shows against that checkout's CLI.

## Package from a checkout

From the repository root, create a new output directory named `attune-harness`:

```sh
python3 scripts/package_codex_plugin.py /tmp/harness-plugin-package/attune-harness
```

Choose a fresh parent directory on repeated runs. The command refuses an existing
destination. It copies the manifest, license and complete skill, including its
references and agent metadata. `plugins/attune-harness` is the manifest template;
the generated directory is the installable plugin. Neither is in the Python wheel.

## Prepare a local marketplace

The checkout includes its own preparation tool; no bundled scaffolding skill or
extra Python dependency is needed. Pick a fresh destination and a marketplace
name not already in use. Names contain lowercase words separated by hyphens.
This command creates files only in the selected output; it does not install,
register, enable or change Codex settings:

```sh
python3 scripts/package_codex_plugin.py "$HOME/harness-plugin-catalog" --marketplace harness-local
```

The resulting root contains `.agents/plugins/marketplace.json` and
`plugins/attune-harness`. The tool refuses existing destinations, symlink parents,
parent traversal, outputs inside the source checkout and an invalid source package before creating output. Use a
new destination for every update; keep previous packages until you have reviewed
the installed snapshot. The tool validates Harness's package contract, not an
arbitrary third-party plugin schema.

Check the exact prepared root without saving marketplace configuration:

```sh
codex plugin list -c 'marketplaces.harness-local.source_type="local"' -c "marketplaces.harness-local.source=\"$HOME/harness-plugin-catalog\"" --marketplace harness-local --available --json
```

Expect `attune-harness@harness-local` under `available`, with `installed: false`
and `enabled: false` for a fresh selector. If that name is already installed,
inspect it before proceeding. These options and the catalog shape were observed
with Codex CLI 0.153.4. Check `codex plugin list --help` on another version; a
successful listing proves local CLI discovery, not fresh desktop skill selection.

## Register and install after reviewing the package

Registration changes Codex's marketplace configuration. Inspect the existing
names first with `codex plugin marketplace list --json`; choose another name and
prepare a fresh catalog if `harness-local` is already present. After approving
registration of this prepared directory:

```sh
codex plugin marketplace add "$HOME/harness-plugin-catalog"
```

List it again with `codex plugin list --marketplace harness-local --available --json`.
After separately approving installation of the listed selector:

```sh
codex plugin add attune-harness@harness-local
```

Start a new Codex task, select **Attune Harness** from Plugins, and inspect a saved
task or test scoped changes. Installation alone does not run a workflow or grant
permission for paid calls. The Python runtime remains a separate installation.
An earlier standalone skill or the repository skill can produce another entry;
keep those copies intact until you have checked which one is in use. Installed
plugins are snapshots, not live views of the checkout. This guide prepares an
independent local catalog rather than rewriting a personal catalog in place.

See the [packaging design note](design-codex-plugin.md) and the
[installation preparation design](design-codex-install-journey.md) for scope and checks.
