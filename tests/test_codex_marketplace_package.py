"""Fresh local catalogs preserve user-owned outputs and bind one complete skill."""
# qualify: platform

import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]


def packager():
    spec = importlib.util.spec_from_file_location('codex_packager', ROOT / 'scripts/package_codex_plugin.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_marketplace_points_to_complete_plugin(tmp_path):
    module = packager()
    output = tmp_path / 'catalog'
    assert module.package(output, marketplace='harness-local') == output
    catalog = json.loads((output / '.agents/plugins/marketplace.json').read_text())
    assert catalog['name'] == 'harness-local'
    assert len(catalog['plugins']) == 1
    entry = catalog['plugins'][0]
    assert entry['name'] == 'attune-harness'
    assert entry['source'] == {'source': 'local', 'path': './plugins/attune-harness'}
    assert entry['policy'] == {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}
    plugin = output / entry['source']['path']
    source = ROOT / '.agents/skills/attune-harness'
    packaged = plugin / 'skills/attune-harness'
    expected = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    assert {str(p.relative_to(packaged)): p.read_bytes() for p in packaged.rglob('*') if p.is_file()} == expected
    assert json.loads((plugin / '.codex-plugin/plugin.json').read_text())['skills'] == './skills/'


def test_existing_catalog_is_never_rewritten(tmp_path):
    output = tmp_path / 'catalog'
    output.mkdir()
    marker = output / 'marketplace.json'
    marker.write_bytes(b'user catalog')
    with pytest.raises(FileExistsError):
        packager().package(output, marketplace='harness-local')
    assert list(output.iterdir()) == [marker]
    assert marker.read_bytes() == b'user catalog'


@pytest.mark.parametrize('name', ['', 'Personal', '../personal', 'x.y', 'x@y', '-personal', 'x' * 65])
def test_invalid_marketplace_name_writes_nothing(tmp_path, name):
    output = tmp_path / 'catalog'
    with pytest.raises(ValueError, match='Marketplace name'):
        packager().package(output, marketplace=name)
    assert not output.exists()


def test_destination_symlink_and_symlink_parent_are_refused(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('Symlinks unavailable to this user')
    with pytest.raises(FileExistsError):
        packager().package(link, marketplace='harness-local')
    with pytest.raises(ValueError, match='parents cannot be symlinks'):
        packager().package(link / 'new', marketplace='harness-local')
    assert list(target.iterdir()) == []


@pytest.mark.parametrize('defect', ['wrong_name', 'escaping_skills', 'missing_skill', 'source_symlink', 'manifest_symlink'])
def test_invalid_source_package_is_refused_before_output(tmp_path, defect):
    module = packager()
    fixture = tmp_path / 'source'
    manifest = fixture / 'plugins/attune-harness/.codex-plugin/plugin.json'
    manifest.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'plugins/attune-harness/.codex-plugin/plugin.json', manifest)
    shutil.copy2(ROOT / 'LICENSE', fixture / 'LICENSE')
    skill = fixture / '.agents/skills/attune-harness'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('canonical skill', encoding='utf-8')
    if defect in ('wrong_name', 'escaping_skills'):
        data = json.loads(manifest.read_text())
        data['name' if defect == 'wrong_name' else 'skills'] = 'wrong' if defect == 'wrong_name' else '../../outside'
        manifest.write_text(json.dumps(data))
    elif defect == 'missing_skill':
        (skill / 'SKILL.md').rename(skill / 'other.md')
    else:
        try:
            link = skill / 'outside.md' if defect == 'source_symlink' else manifest.parent / 'outside.json'
            link.symlink_to(ROOT / 'README.md')
        except OSError:
            pytest.skip('Symlinks unavailable to this user')
    module.ROOT = fixture
    output = tmp_path / 'catalog'
    with pytest.raises(ValueError):
        module.package(output, marketplace='harness-local')
    assert not output.exists()


def test_parent_traversal_is_refused_before_output(tmp_path):
    with pytest.raises(ValueError, match='parent traversal'):
        packager().package(tmp_path / 'unused/../catalog', marketplace='harness-local')
    assert not (tmp_path / 'unused').exists()
    assert not (tmp_path / 'catalog').exists()


def test_output_inside_copied_skill_is_refused_before_creation(tmp_path):
    module = packager()
    source = tmp_path / 'source'
    skill = source / '.agents/skills/attune-harness'
    skill.mkdir(parents=True)
    marker = skill / 'SKILL.md'
    marker.write_bytes(b'preserve canonical source')
    manifest = source / 'plugins/attune-harness/.codex-plugin/plugin.json'
    manifest.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'plugins/attune-harness/.codex-plugin/plugin.json', manifest)
    shutil.copy2(ROOT / 'LICENSE', source / 'LICENSE')
    module.ROOT = source
    output = skill / 'nested-catalog'
    with pytest.raises(ValueError, match='inside the source checkout'):
        module.package(output, marketplace='harness-local')
    assert list(skill.iterdir()) == [marker]
    assert marker.read_bytes() == b'preserve canonical source'


def test_case_alias_cannot_place_output_inside_source_checkout(tmp_path):
    module = packager()
    source = tmp_path / 'source'
    skill = source / '.agents/skills/attune-harness'
    skill.mkdir(parents=True)
    marker = skill / 'SKILL.md'
    marker.write_bytes(b'preserve canonical source')
    manifest = source / 'plugins/attune-harness/.codex-plugin/plugin.json'
    manifest.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'plugins/attune-harness/.codex-plugin/plugin.json', manifest)
    shutil.copy2(ROOT / 'LICENSE', source / 'LICENSE')
    alias = tmp_path / 'SOURCE'
    if not alias.exists() or not alias.samefile(source):
        pytest.skip('Filesystem does not resolve this case alias')
    module.ROOT = source
    output = alias / '.agents/skills/attune-harness/nested-catalog'
    with pytest.raises(ValueError, match='inside the source checkout'):
        module.package(output, marketplace='harness-local')
    assert list(skill.iterdir()) == [marker]
    assert marker.read_bytes() == b'preserve canonical source'
