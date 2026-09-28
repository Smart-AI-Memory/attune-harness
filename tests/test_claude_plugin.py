"""The published Claude Code plugin (first-run journey T2, R4 and Q4).

``.claude-plugin/marketplace.json`` publishes one plugin whose source is the
repository root. Because the entry lists its skill folders, Claude Code loads
exactly those and does not scan a default ``skills/``: the Harness skill from
its one source, ``.agents/skills/attune-harness``, plus ``cross-review`` and
``smart-test``. The Spec workspace skill, its MCP server and the two
maintainer-only release skills stay out until their own gates land.

Codex must not notice any of this. Codex reads ``.codex-plugin`` manifests and
its own catalogs, never ``.claude-plugin/``, and the Harness skill is not added
to the shared ``plugin/attune-harness/skills/``, where a Codex user with both
Harness plugins would see it twice. ``plugins/attune-harness/`` keeps its own
version (docs/codex-plugin.md).
"""

import json
import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / '.claude-plugin' / 'marketplace.json'
SKILL = ROOT / '.agents' / 'skills' / 'attune-harness'
SHARED = ROOT / 'plugin' / 'attune-harness'
PUBLISHED_SKILLS = ('./.agents/skills/attune-harness', './plugin/attune-harness/skills/cross-review',
                    './plugin/attune-harness/skills/smart-test')


def version():
    # tomllib arrives in Python 3.11; the project supports 3.10.
    return re.search(r'^version = "([^"]+)"$', (ROOT / 'pyproject.toml').read_text(encoding='utf-8'), re.M).group(1)


def entry():
    (plugin,) = json.loads(MARKETPLACE.read_text(encoding='utf-8'))['plugins']
    return plugin


def test_marketplace_carries_the_package_version():
    marketplace = json.loads(MARKETPLACE.read_text(encoding='utf-8'))
    assert marketplace['metadata']['version'] == entry()['version'] == version()


def test_shared_plugin_manifests_carry_the_package_version():
    """D30.2: the shared plugin is versioned with the package."""
    for host in ('.claude-plugin', '.codex-plugin'):
        assert json.loads((SHARED / host / 'plugin.json').read_text(encoding='utf-8'))['version'] == version(), host


def test_entry_publishes_exactly_the_chosen_skills():
    plugin = entry()
    assert plugin['name'] == 'attune-harness' and plugin['source'] == './'
    assert tuple(plugin['skills']) == PUBLISHED_SKILLS
    for path in plugin['skills']:
        assert (ROOT / path / 'SKILL.md').is_file(), path
    # No MCP server: the workspace server belongs with the Spec skill, which waits for M3.
    assert not {'mcpServers', 'lspServers', 'hooks', 'commands', 'agents'} & set(plugin)
    # A root-source plugin must not have a plugin.json at the root, or the entry stops being its manifest.
    assert not (ROOT / '.claude-plugin' / 'plugin.json').exists()


def test_codex_sees_the_harness_skill_once():
    """The shared skills folder, read by both hosts' manifests, does not gain the Harness skill."""
    shared = sorted(p.name for p in (SHARED / 'skills').iterdir() if p.is_dir())
    assert 'attune-harness' not in shared
    assert shared == ['attune-release-check', 'cross-review', 'release-execute', 'smart-test', 'spec']
    for host in ('.claude-plugin', '.codex-plugin'):
        assert json.loads((SHARED / host / 'plugin.json').read_text(encoding='utf-8'))['skills'] == './skills/', host
    codex = json.loads((ROOT / 'plugins' / 'attune-harness' / '.codex-plugin' / 'plugin.json').read_text(encoding='utf-8'))
    assert codex['version'] == '0.1.0' and codex['skills'] == './skills/'


def _commands(text):
    """Every ``attune-harness`` command line in a Markdown file's shell blocks, continuations joined."""
    found = []
    for block in re.findall(r'^```(?:sh|bash)\n(.*?)^```', text, re.M | re.S):
        pending = ''
        for line in block.splitlines():
            line = line.strip()
            if line.endswith('\\'):
                pending += line[:-1] + ' '
                continue
            line, pending = pending + line, ''
            if line.startswith('attune-harness '):
                found.append(shlex.split(line))
    return found


def test_skill_commands_exist_in_the_cli_it_ships_with():
    """Each verb and option the skill shows is in the frozen CLI surface for this version."""
    surface = json.loads((ROOT / 'tests' / 'fixtures' / 'compatibility' / 'surface.json').read_text(encoding='utf-8'))['verbs']
    commands = [c for path in sorted(SKILL.rglob('*.md')) for c in _commands(path.read_text(encoding='utf-8'))]
    assert len(commands) >= 10, commands
    for argv in commands:
        verb = argv[1]
        assert verb in surface, argv
        options = {token.split('=', 1)[0] for token in argv[2:] if token.startswith('--')}
        unknown = options - set(surface[verb]['options']) - {'--help'}
        assert not unknown, (argv, unknown)


def test_skill_names_no_fixed_cli_version():
    """The skill ships with the version it describes; a pinned older number is the 0.6.0 defect."""
    for path in SKILL.rglob('*.md'):
        assert not re.search(r'\b\d+\.\d+\.\d+\b', path.read_text(encoding='utf-8')), path
