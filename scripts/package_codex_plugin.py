"""Prepare a standalone Codex plugin or local marketplace without installing it."""

import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def validate_sources() -> None:
    """Validate the Harness package contract, not arbitrary Codex plugins."""
    manifest = ROOT / 'plugins/attune-harness/.codex-plugin/plugin.json'
    skill = ROOT / '.agents/skills/attune-harness'
    sources = [manifest.parent, *manifest.parent.rglob('*'),
               ROOT / 'LICENSE', skill, *skill.rglob('*')]
    if any(path.is_symlink() for path in sources):
        raise ValueError('Package sources cannot be symlinks')
    if any(path.is_symlink() for path in (*manifest.parents, *skill.parents)):
        raise ValueError('Package source parents cannot be symlinks')
    if not manifest.is_file() or not (ROOT / 'LICENSE').is_file() or not skill.is_dir():
        raise ValueError('Package sources are incomplete')
    if not (skill / 'SKILL.md').is_file():
        raise ValueError('Canonical skill must contain SKILL.md')
    if any(not path.is_file() and not path.is_dir() for path in sources):
        raise ValueError('Package sources must be regular files or directories')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or data.get('name') != 'attune-harness'
            or data.get('skills') != './skills/'
            or not isinstance(data.get('version'), str) or not data['version'].strip()
            or not isinstance(data.get('interface'), dict)
            or data['interface'].get('displayName') != 'Attune Harness'):
        raise ValueError('Manifest differs from the Harness plugin contract')


def package(destination: Path, *, marketplace: str | None = None) -> Path:
    """Create a new package or catalog; never modify an existing destination."""
    if marketplace is not None and (not isinstance(marketplace, str)
            or re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', marketplace) is None
            or len(marketplace) > 64):
        raise ValueError('Marketplace name must be lowercase words separated by hyphens (max 64 characters)')
    destination = destination.expanduser().absolute()
    if '..' in destination.parts:
        raise ValueError('Destination cannot contain parent traversal')
    # Existing ancestor identity catches case aliases on case-insensitive
    # filesystems; lexical ancestry alone does not identify the same checkout.
    if (destination.is_relative_to(ROOT.resolve())
            or any(parent.exists() and parent.samefile(ROOT)
                   for parent in (destination, *destination.parents))):
        raise ValueError('Destination cannot be inside the source checkout')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination already exists')
    if any(parent.is_symlink() for parent in destination.parents):
        raise ValueError('Destination parents cannot be symlinks')
    if marketplace is None and destination.name != 'attune-harness':
        raise ValueError('Standalone destination must be named attune-harness')
    validate_sources()
    destination.mkdir(parents=True, exist_ok=False)
    plugin = destination / 'plugins/attune-harness' if marketplace else destination
    if marketplace:
        plugin.mkdir(parents=True)
    shutil.copytree(ROOT / 'plugins/attune-harness/.codex-plugin', plugin / '.codex-plugin')
    shutil.copytree(ROOT / '.agents/skills/attune-harness', plugin / 'skills/attune-harness')
    shutil.copy2(ROOT / 'LICENSE', plugin / 'LICENSE')
    if marketplace:
        catalog = destination / '.agents/plugins/marketplace.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text(json.dumps({
            'name': marketplace,
            'interface': {'displayName': marketplace},
            'plugins': [{
                'name': 'attune-harness',
                'source': {'source': 'local', 'path': './plugins/attune-harness'},
                'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                'category': 'Productivity',
            }],
        }, indent=2) + '\n', encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='Fresh plugin directory or marketplace root')
    parser.add_argument('--marketplace', metavar='NAME', help='Prepare a self-contained local marketplace')
    args = parser.parse_args()
    try:
        print(package(args.destination, marketplace=args.marketplace))
    except (ValueError, OSError) as error:
        parser.exit(2, f'Preparation refused: {error}\n')
