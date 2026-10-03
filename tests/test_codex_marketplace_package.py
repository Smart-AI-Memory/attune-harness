"""Fresh local catalogs preserve user-owned outputs and bind all three skills."""
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
    assert sorted(p.name for p in (plugin / 'skills').iterdir()) == ['attune-harness', 'cross-review', 'roundtable']
    for name in ('cross-review', 'roundtable'):
        source = ROOT / 'plugin/attune-harness/skills' / name
        packaged = plugin / 'skills' / name
        assert {str(p.relative_to(packaged)): p.read_bytes() for p in packaged.rglob('*') if p.is_file()} == {
            str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}


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
    for name in ('cross-review', 'roundtable'):
        extra = fixture / 'plugin/attune-harness/skills' / name
        extra.mkdir(parents=True)
        (extra / 'SKILL.md').write_text(name, encoding='utf-8')
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


@pytest.mark.parametrize('name', ['cross-review', 'roundtable'])
@pytest.mark.parametrize('defect', ['missing_skill', 'symlink'])
def test_consultation_skill_refusal_precedes_any_output(tmp_path, name, defect):
    module = packager()
    fixture = tmp_path / 'source'
    fixture.mkdir()
    shutil.copy2(ROOT / 'LICENSE', fixture / 'LICENSE')
    shutil.copytree(ROOT / 'plugins/attune-harness/.codex-plugin', fixture / 'plugins/attune-harness/.codex-plugin')
    shutil.copytree(ROOT / '.agents/skills/attune-harness', fixture / '.agents/skills/attune-harness')
    shutil.copytree(ROOT / 'plugin/attune-harness/skills', fixture / 'plugin/attune-harness/skills')
    source = fixture / 'plugin/attune-harness/skills' / name
    if defect == 'missing_skill':
        (source / 'SKILL.md').rename(source / 'other.md')
    else:
        try:
            (source / 'outside.md').symlink_to(ROOT / 'README.md')
        except OSError:
            pytest.skip('Symlinks unavailable to this user')
    module.ROOT = fixture
    output = tmp_path / 'catalog'
    with pytest.raises(ValueError):
        module.package(output, marketplace='harness-local')
    assert not output.exists()


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


def manifest_fixture(tmp_path):
    module = packager()
    source = tmp_path / 'source'
    source.mkdir()
    shutil.copy2(ROOT / 'LICENSE', source / 'LICENSE')
    for path in ('plugins/attune-harness/.codex-plugin', '.agents/skills/attune-harness',
                 'plugin/attune-harness/skills'):
        shutil.copytree(ROOT / path, source / path)
    module.ROOT = source
    manifest = source / 'plugins/attune-harness/.codex-plugin/plugin.json'
    return module, manifest, json.loads(manifest.read_text(encoding='utf-8'))


@pytest.mark.parametrize('field', [
    'name', 'version', 'description', 'author', 'skills', 'interface', 'repository', 'license', 'keywords',
    'author.name', 'interface.displayName', 'interface.shortDescription', 'interface.longDescription',
    'interface.developerName', 'interface.category', 'interface.capabilities', 'interface.defaultPrompt',
])
@pytest.mark.parametrize('marketplace', [None, 'harness-local'])
def test_missing_required_manifest_field_creates_no_output(tmp_path, field, marketplace):
    module, manifest, data = manifest_fixture(tmp_path)
    owner = data
    parts = field.split('.')
    for part in parts[:-1]:
        owner = owner[part]
    del owner[parts[-1]]
    manifest.write_text(json.dumps(data), encoding='utf-8')
    parent = tmp_path / 'uncreated'
    with pytest.raises(ValueError):
        module.package(parent / 'attune-harness', marketplace=marketplace)
    assert not parent.exists()


@pytest.mark.parametrize('field,value', [
    ('description', ''), ('description', 1), ('author', 'Smart AI Memory'),
    ('author.name', 'other'), ('repository', False), ('license', 'other'),
    ('keywords', 'testing'), ('keywords', []), ('keywords', ['']), ('keywords', [1]),
    ('interface', []), ('interface.shortDescription', False), ('interface.longDescription', '  '),
    ('interface.developerName', 'other'), ('interface.category', 'other'),
    ('interface.capabilities', ['external-effect']), ('interface.capabilities', None),
    ('interface.defaultPrompt', 'Use Harness'), ('interface.defaultPrompt', []),
    ('interface.defaultPrompt', ['x'] * 4), ('interface.defaultPrompt', ['x' * 129]),
    ('interface.defaultPrompt', ['']), ('interface.defaultPrompt', [None]),
    ('apps', './apps.json'), ('interface.authority', True),
])
@pytest.mark.parametrize('marketplace', [None, 'harness-local'])
def test_invalid_manifest_metadata_creates_no_output(tmp_path, field, value, marketplace):
    module, manifest, data = manifest_fixture(tmp_path)
    owner = data
    parts = field.split('.')
    for part in parts[:-1]:
        owner = owner[part]
    owner[parts[-1]] = value
    manifest.write_text(json.dumps(data), encoding='utf-8')
    parent = tmp_path / 'uncreated'
    with pytest.raises(ValueError):
        module.package(parent / 'attune-harness', marketplace=marketplace)
    assert not parent.exists()


@pytest.mark.parametrize('version', ['dev', '1', '1.2', '01.2.3', '1.2.3-01', '1.2.3-',
                                     '1.2.3+', 'v1.2.3', '1.2.3 ', '\u0661.2.3', 1])
def test_invalid_harness_version_refuses_before_output(tmp_path, version):
    module, manifest, data = manifest_fixture(tmp_path)
    data['version'] = version
    manifest.write_text(json.dumps(data), encoding='utf-8')
    output = tmp_path / 'uncreated/catalog'
    with pytest.raises(ValueError, match='SemVer'):
        module.package(output, marketplace='harness-local')
    assert not output.parent.exists()


@pytest.mark.parametrize('version', ['0.1.0', '1.2.3', '1.2.3-alpha.1+build.01', '1.2.3-0',
                                     '1.2.3-01x', '1.2.3-x-y-z.--+001'])
@pytest.mark.parametrize('marketplace', [None, 'harness-local'])
def test_valid_version_and_prompt_boundary_preserve_manifest(tmp_path, version, marketplace):
    module, manifest, data = manifest_fixture(tmp_path)
    data['version'] = version
    data['interface']['defaultPrompt'] = ['x' * 128, '\u00e9' * 128, 'Inspect saved work']
    manifest.write_text(json.dumps(data), encoding='utf-8')
    output = tmp_path / 'attune-harness'
    module.package(output, marketplace=marketplace)
    plugin = output / 'plugins/attune-harness' if marketplace else output
    assert (plugin / '.codex-plugin/plugin.json').read_bytes() == manifest.read_bytes()
    assert sorted(path.name for path in (plugin / 'skills').iterdir()) == [
        'attune-harness', 'cross-review', 'roundtable']


@pytest.mark.parametrize('defect', ['duplicate_field', 'invalid_json'])
def test_ambiguous_or_malformed_manifest_creates_no_output(tmp_path, defect):
    module, manifest, _ = manifest_fixture(tmp_path)
    text = manifest.read_text(encoding='utf-8')
    if defect == 'duplicate_field':
        text = text.replace('"version": "0.1.0"', '"version": "dev", "version": "0.1.0"')
    else:
        text += ' not-json'
    manifest.write_text(text, encoding='utf-8')
    parent = tmp_path / 'uncreated'
    with pytest.raises(ValueError):
        module.package(parent / 'catalog', marketplace='harness-local')
    assert not parent.exists()
