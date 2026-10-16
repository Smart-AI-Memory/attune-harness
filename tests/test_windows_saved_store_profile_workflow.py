"""Data controls and an offline Git checkout control; no native or account entry."""
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / '.github/workflows/windows-saved-store-platform-build-safe-preflight.yml'
OLD = ROOT / '.github/workflows/windows-saved-store-build-safe-preflight.yml'
RETIRE = '    # Retained failed LF-only wheel experiment; replacement has finite platform pairs.\n    if: ${{ false }}\n'




def frozen_bytes(name):
    # Historical data has its own identity; it never imports or qualifies SRC.
    path = ROOT / 'tests/fixtures/windows_saved_store_ffc_campaign_v1.zip'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '2aa85e0b712cd82a1776bd1a021c5dca9098007c8775bbbd68fded22afaefde3'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.infolist()) == 144
        return archive.read(name)


PROFILE_RETIRE = '    # Retained FFC campaign; fixed-component successor owns new observations.\n    if: ${{ false }}\n'


def historical_profile():
    current = NEW.read_text()
    assert current.count(PROFILE_RETIRE) == 1
    frozen = frozen_bytes(NEW.relative_to(ROOT).as_posix()).decode('utf-8')
    assert current.replace(PROFILE_RETIRE, '') == frozen
    return frozen


def inline(path):
    block, = re.findall(r"          \$materialize = @'\n(.*?)\n          '@", (historical_profile() if path == NEW else path.read_text()), re.S)
    return '\n'.join(line.removeprefix('          ') for line in block.splitlines())


def fixed(path):
    block, = re.findall(r'\$expected = \[ordered\]@\{(.*?)\n          \}', (historical_profile() if path == NEW else path.read_text()), re.S)
    return dict(re.findall(r"'([^']+)' = '([0-9a-f]{64})'", block))


def test_old_job_retired_explicitly_without_unused_replacement_code():
    text = OLD.read_text()
    assert text.count(RETIRE) == 1
    assert hashlib.sha256(text.replace(RETIRE, '').encode()).hexdigest() == 'bd8da13606ce857e6a9c365eb8b189af3f7b48905f0095346655f3ae5e11f0d1'
    assert 'platform-build-safe-preflight' not in text


def test_one_new_four_cell_safe_route_and_unchanged_bounds():
    text = historical_profile()
    assert 'branches: [main]' in text and 'pull_request:' in text and 'workflow_dispatch' not in text
    assert text.count('os: [windows-2022, windows-2025]') == 1
    assert text.count("python: ['3.10', '3.12']") == 1 and text.count('timeout-minutes: 20') == 1
    assert 'cancel-in-progress: false' in text and 'persist-credentials: false' in text
    assert 'ref:' not in text and 'contents: read' in text and 'contents: write' not in text
    assert '-ExecuteApprovedFixture' not in text and '-ExecuteReviewedGuiLease' not in text
    assert "-Output (Join-Path $env:RUNNER_TEMP 'saved-store-build-safe')" in text
    assert '$script = (Resolve-Path experiments/platform/windows_saved_store_build_preflight_v2.ps1).Path' in text
    assert 'python -I -m venv' in text and "'setuptools==84.0.0'" in text
    assert 'check_windows_saved_store_merge_inputs_v1.py --repo (Get-Location).Path' in text
    assert '--manifest experiments/platform/windows_saved_store_source_manifest_v3.json' in text
    assert 'check_windows_saved_store_account_inputs_v3.py --repo' in text
    assert 'if: always()' in text and 'saved-store-platform-build-safe-${{ matrix.os }}-${{ matrix.python }}' in text
    assert text.count('python -I -B -c $materialize ') == 2
    assert 'if: ${{ false }}' in (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()


def test_finite27_map_preserves_old18_and_binds_nine_new_files():
    old, new = fixed(OLD), fixed(NEW)
    assert len(old) == 18 and len(new) == 27 and len({p.casefold() for p in new}) == 27
    assert {name: new[name] for name in old} == old
    added = set(new) - set(old)
    assert len(added) == 9
    for name in added:
        assert hashlib.sha256(frozen_bytes(name)).hexdigest() == new[name]


def test_raw_materializer_changes_only_three_selection_constants():
    before, after = ast.parse(inline(OLD)), ast.parse(inline(NEW))
    for tree in [before, after]:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant):
                continue
            if node.value in [18, 27]:
                node.value = 'fixed-count'
            elif node.value in ['experiments/platform/windows_saved_store_source_manifest_v2.json',
                                 'experiments/platform/windows_saved_store_source_manifest_v3.json']:
                node.value = 'reviewed-manifest-path'
            elif node.value in ['d6e80ebd18c19d5b17b35bfdd4c0dc521a24e1dbb0a18eeba14247fcd7e875d8',
                                 'fcf8365fc00aeade30d8bdfa4c4f3e0f5ea869aabb1fbc1ce80466c3b999ae5a']:
                node.value = 'reviewed-manifest-digest'
    assert ast.dump(before) == ast.dump(after)


def materializer():
    namespace = {'__name__': 'pure_profile_materializer'}
    exec(compile(inline(NEW), 'profile-materializer-data', 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('change', [None, 'short', 'long', 'case_alias'])
def test_fixed_selection_is_finite_without_running_git(tmp_path, change):
    namespace = materializer()
    mapping = {f'item_{i}.py': '0' * 64 for i in range(27)}
    if change == 'short':
        mapping.pop('item_0.py')
    if change == 'long':
        mapping['extra.py'] = '0' * 64
    if change == 'case_alias':
        mapping['ITEM_0.py'] = mapping.pop('item_1.py')
    if change:
        with pytest.raises(ValueError):
            namespace['selection']('fixed', json.dumps(mapping), tmp_path)
    else:
        assert namespace['selection']('fixed', json.dumps(mapping), tmp_path) == mapping


@pytest.mark.parametrize('changed', [False, True])
def test_manifest_selection_binds_exact116_before_any_git(tmp_path, changed):
    namespace = materializer()
    name = 'experiments/platform/windows_saved_store_source_manifest_v3.json'
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / name).read_bytes() + (b' ' if changed else b''))
    if changed:
        with pytest.raises(ValueError):
            namespace['selection']('manifest', '{}', tmp_path)
    else:
        result = namespace['selection']('manifest', '{}', tmp_path)
        assert len(result) == 116 and 'src/attune_harness/windows_effects.py' in result


def test_nested_attributes_are_exact_and_touch_only_new_paths():
    experiment = frozen_bytes('experiments/platform/.gitattributes').decode().splitlines()
    tests = frozen_bytes('tests/.gitattributes').decode().splitlines()
    assert experiment == ['.gitattributes -text', 'check_windows_saved_store_account_inputs_v3.py -text',
                          'project_windows_saved_store_build_v2.py -text', 'windows_saved_store_build_preflight_v2.ps1 -text',
                          'windows_saved_store_source_manifest_v3.json -text']
    assert tests == ['.gitattributes -text', 'test_windows_saved_store_wheel_profiles.py -text',
                     'test_windows_saved_store_profile_workflow.py -text',
                     'fixtures/windows_saved_store_wheel_metadata_v1.json -text']


@pytest.mark.parametrize('self_rules', [False, True])
def test_offline_git_autocrlf_control_protects_new_bytes_and_attribute_files(tmp_path, self_rules):
    git = shutil.which('git')
    assert git, 'The required offline checkout control needs Git.'
    owned = tmp_path / 'repo'
    owned.mkdir()
    hooks = tmp_path / 'empty-hooks'
    hooks.mkdir()
    attributes = tmp_path / 'empty-global-attributes'
    attributes.write_bytes(b'')
    environment = {name: value for name, value in os.environ.items() if not name.startswith('GIT_')}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                       GIT_ATTR_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')

    def run(*arguments):
        return subprocess.run(
            [git, '-c', 'core.autocrlf=true', '-c', 'core.eol=crlf',
             '-c', 'core.attributesFile=' + str(attributes), '-c', 'core.hooksPath=' + str(hooks),
             '-c', 'commit.gpgsign=false', '-c', 'user.name=T2 offline control',
             '-c', 'user.email=t2-control@example.invalid', *arguments],
            cwd=owned, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=True)

    run('init', '-q')
    (owned / '.gitattributes').write_bytes(b'* text eol=crlf\n')
    attribute_paths = ['experiments/platform/.gitattributes', 'tests/.gitattributes']
    originals = {}
    protected = []
    for name in attribute_paths:
        body = (ROOT / name).read_bytes()
        if not self_rules:
            body = body.replace(b'.gitattributes -text\n', b'', 1)
        path = owned / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        originals[name] = body
        for row in body.decode().splitlines():
            relative, setting = row.split()
            if relative == '.gitattributes':
                continue
            assert setting == '-text'
            target = path.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'controlled LF bytes\n')
            protected.append(target.relative_to(owned).as_posix())
    (owned / 'control.txt').write_bytes(b'control LF\n')
    run('add', '--', '.')
    run('commit', '-qm', 'Offline newline control')
    for name in protected:
        (owned / name).write_bytes(b'dirty\n')
    for name in attribute_paths:
        (owned / name).write_bytes(originals[name] + b'# dirty\n')
    (owned / 'control.txt').write_bytes(b'dirty\n')
    run('checkout-index', '--force', '--', *attribute_paths, *protected, 'control.txt')
    assert (owned / 'control.txt').read_bytes() == b'control LF\r\n'
    for name in protected:
        assert (owned / name).read_bytes() == b'controlled LF bytes\n'
    for name in attribute_paths:
        expected = originals[name] if self_rules else originals[name].replace(b'\n', b'\r\n')
        assert (owned / name).read_bytes() == expected
