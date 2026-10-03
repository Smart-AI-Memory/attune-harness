# Codex plugin packaging

Attune Harness already has a repository skill, but no plugin manifest or
marketplace entry. Package that skill under the distinct Attune Harness name.
The Python distribution and the Attune-AI plugin remain separate installations.

## Cases and checks

- A fresh package contains the manifest, license and complete canonical skill,
  including its workflow reference and agent metadata.
- Refuse an existing destination before writing anything; never silently replace
  a user plugin or a retained package.
- Package from an arbitrary working directory using paths relative to the script.
- Prepare a fresh local marketplace using the checkout tool, preserving existing
  catalogs. Verify discovery through the actual Codex CLI before separately
  approving registration and installation.
- Compare the installed skill bytes with the repository source. Opening a new task
  is still needed to check the app's refreshed skill selector.

## Evidence before implementation

The installed Codex CLI exposes `plugin list --available --json`, `plugin add`
and marketplace management. Its personal marketplace currently lists no plugins.
The bundled plugin validator requires the skills path to resolve to `skills`;
the canonical Harness skill lives at `.agents/skills/attune-harness`.

## Choice

Keep one canonical skill and assemble a small standalone plugin directory from
it. The manifest template lives under `plugins/attune-harness`; a packaging script
copies only the manifest, license and skill, avoiding checkout files and receipts.
Reject a second maintained skill copy because its workflow instructions could
silently diverge. Use the personal marketplace for local discovery; a public or
team catalog is a separate distribution decision.

## October 1 installation follow-up

The bundled scaffold mentioned in the original experiment is not required by
the supported preparation path. The [A3 design](design-codex-install-journey.md)
records the local catalog shape and explicit-path listing probe. Fresh desktop
discovery and installation remain separate checks.
