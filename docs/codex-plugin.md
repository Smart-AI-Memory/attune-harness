# Attune Harness in Codex Plugins

**Attune Harness** is a Codex plugin containing the existing
[Harness workflow skill](../.agents/skills/attune-harness/SKILL.md). It is separate
from **Attune-AI**. The plugin adds discovery and workflow instructions; install
the `attune-harness` Python runtime separately as described in the
[CLI guide](cli-guide.md#codex-skill).

The plugin version is independent of the Python package version. This initial
plugin is 0.1.0 and its skill targets the Harness 0.6.0 CLI.

## Package from a checkout

From the repository root, create a new output directory named `attune-harness`:

```sh
python3 scripts/package_codex_plugin.py /tmp/harness-plugin-package/attune-harness
```

Choose a fresh parent directory on repeated runs. The command refuses an existing
destination. It copies the manifest, license and complete skill, including its
references and agent metadata. `plugins/attune-harness` is the manifest template;
the generated directory is the installable plugin. Neither is in the Python wheel.

## First personal installation

These commands use the bundled Codex `plugin-creator` skill at
`~/.codex/skills/.system/plugin-creator`. Confirm that skill is present first.
Run the scaffold to create the personal catalog entry and destination:

```sh
python3 "$HOME/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py" attune-harness --with-marketplace
```

The scaffold preserves other entries and refuses an existing Harness entry or
manifest. Inspect an existing installation before updating it. For a fresh
installation, replace only the newly generated scaffold with the package:

```sh
cp /tmp/harness-plugin-package/attune-harness/.codex-plugin/plugin.json "$HOME/plugins/attune-harness/.codex-plugin/plugin.json"
cp -R /tmp/harness-plugin-package/attune-harness/skills "$HOME/plugins/attune-harness/skills"
cp /tmp/harness-plugin-package/attune-harness/LICENSE "$HOME/plugins/attune-harness/LICENSE"
python3 "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py" "$HOME/plugins/attune-harness"
python3 "$HOME/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py"
```

Use a Python interpreter with PyYAML available for the validator. The last command
prints the validated marketplace name; substitute it for `personal` below if the
existing personal catalog has another name:

```sh
codex plugin list --marketplace personal --available --json
codex plugin add attune-harness@personal
```

The default catalog at `~/.agents/plugins/marketplace.json` is discovered
implicitly. This registers a personal plugin, not a public catalog listing.
Start a new Codex task after installation, select **Attune Harness** from Plugins,
and ask it to inspect a saved task or test scoped changes. Installation alone does
not run a workflow or grant permission for paid calls.

An earlier standalone copy at `~/.agents/skills/attune-harness`, or this checkout's
repository skill, may produce an additional skill entry. Keep the copies intact
until you have checked which one you use. For later plugin updates, use the
plugin-creator skill's cachebuster and reinstall procedure; an installed plugin
is a snapshot, not a live view of the checkout.

See the [packaging design note](design-codex-plugin.md) for scope and checks.
