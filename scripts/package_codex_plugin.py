"""Prepare a standalone Codex plugin or local marketplace without installing it."""

import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def skill_sources() -> list[Path]:
    return [ROOT / '.agents/skills/attune-harness',
            ROOT / 'plugin/attune-harness/skills/cross-review',
            ROOT / 'plugin/attune-harness/skills/roundtable']


def _manifest_object(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('Manifest contains duplicate fields')
        data[key] = value
    return data


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_manifest(data) -> None:
    """Require our complete emitted manifest, not the looser Codex schema."""
    fields = {'name', 'version', 'description', 'author', 'skills', 'interface',
              'repository', 'license', 'keywords'}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError('Manifest differs from the Harness plugin contract')
    if (data['name'] != 'attune-harness' or data['skills'] != './skills/'
            or data['author'] != {'name': 'Smart AI Memory'}
            or data['repository'] != 'https://github.com/Smart-AI-Memory/attune-harness'
            or data['license'] != 'Apache-2.0' or not _nonempty(data['description'])):
        raise ValueError('Manifest differs from the Harness plugin contract')
    # SemVer is Harness's own convention; Codex's legacy parser only trims it.
    version = data['version']
    pattern = (r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
               r'(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
               r'(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?')
    matched = re.fullmatch(pattern, version) if isinstance(version, str) else None
    if matched is None or any(part.isdecimal() and len(part) > 1 and part.startswith('0')
                              for part in (matched.group('prerelease') or '').split('.')):
        raise ValueError('Harness plugin version must be SemVer 2.0')
    keywords = data['keywords']
    if not isinstance(keywords, list) or not keywords or not all(_nonempty(k) for k in keywords):
        raise ValueError('Harness plugin keywords require nonempty strings')
    interface = data['interface']
    text_fields = {'displayName', 'shortDescription', 'longDescription', 'developerName', 'category'}
    if (not isinstance(interface, dict) or set(interface) != text_fields | {'capabilities', 'defaultPrompt'}
            or not all(_nonempty(interface[k]) for k in text_fields)
            or interface['displayName'] != 'Attune Harness'
            or interface['developerName'] != 'Smart AI Memory' or interface['category'] != 'Productivity'
            or interface['capabilities'] != []):
        raise ValueError('Interface differs from the Harness plugin contract')
    prompts = interface['defaultPrompt']
    if (not isinstance(prompts, list) or not 1 <= len(prompts) <= 3
            or not all(_nonempty(p) and len(p) <= 128 for p in prompts)):
        raise ValueError('Harness plugin prompts require 1-3 nonempty strings of at most 128 characters')


def validate_sources() -> None:
    """Validate the Harness package contract, not arbitrary Codex plugins."""
    manifest = ROOT / 'plugins/attune-harness/.codex-plugin/plugin.json'
    skills = skill_sources()
    sources = [manifest.parent, *manifest.parent.rglob('*'), ROOT / 'LICENSE']
    for skill in skills:
        sources += [skill, *skill.rglob('*')]
    if any(path.is_symlink() for path in sources):
        raise ValueError('Package sources cannot be symlinks')
    parents = [*manifest.parents]
    for skill in skills:
        parents += list(skill.parents)
    if any(path.is_symlink() for path in parents):
        raise ValueError('Package source parents cannot be symlinks')
    if not manifest.is_file() or not (ROOT / 'LICENSE').is_file() or any(not skill.is_dir() for skill in skills):
        raise ValueError('Package sources are incomplete')
    if any(not (skill / 'SKILL.md').is_file() for skill in skills):
        raise ValueError('Each packaged skill must contain SKILL.md')
    if any(not path.is_file() and not path.is_dir() for path in sources):
        raise ValueError('Package sources must be regular files or directories')
    validate_manifest(json.loads(manifest.read_text(encoding='utf-8'), object_pairs_hook=_manifest_object))


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
    for skill in skill_sources():
        shutil.copytree(skill, plugin / 'skills' / skill.name)
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
