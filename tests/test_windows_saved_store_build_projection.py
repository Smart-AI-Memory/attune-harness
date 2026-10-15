"""Pure projection controls; never invoke a CLI, backend, GUI or native proof."""
import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('t2_projection_pure', ROOT / 'experiments/platform/project_windows_saved_store_build_v1.py')
project = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(project)


@pytest.fixture
def inputs(tmp_path):
    repo, owned = tmp_path / 'repository', tmp_path / 'owned'
    repo.mkdir()
    owned.mkdir()
    expected = {}
    for number in range(113):
        name = (f'src/attune_harness/module_{number}.py' if number < 106
                else f'src/attune_voyage_plugin/module_{number}.py')
        raw = f'constant = {number}\n'.encode()
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        expected[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    for name in ['LICENSE', 'README.md', 'pyproject.toml']:
        raw = (name + '\n').encode()
        (repo / name).write_bytes(raw)
        expected[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return repo, owned / 'source', expected


def test_hash_bound_actual_manifest():
    raw = (ROOT / 'experiments/platform/windows_saved_store_source_manifest_v2.json').read_bytes()
    assert len(project.inputs(raw)) == 116
    with pytest.raises(ValueError, match='manifest_identity'):
        project.inputs(raw + b' ')


def test_exact_projection_ignores_poisoned_original_root_build_controls(inputs):
    repo, projection, expected = inputs
    poison = 'raise RuntimeError("unreviewed root setup executed")\n'
    (repo / 'setup.py').write_text(poison)
    (repo / 'setup.cfg').write_text('[metadata]\nversion = attr: unreviewed.version\n')
    (repo / 'MANIFEST.in').write_text('recursive-include unreviewed *\n')
    (repo / 'unreviewed').mkdir()
    (repo / 'unreviewed/payload.py').write_text(poison)
    # Positive control proves this test file would fail if loaded as root setup.
    with pytest.raises(RuntimeError, match='unreviewed root setup'):
        exec(compile((repo / 'setup.py').read_text(), 'controlled-setup-trap', 'exec'), {})
    rows = project.create(repo, projection, expected)
    assert len(rows) == 116 and set(row['path'] for row in rows) == set(expected)
    assert not any((projection / name).exists() for name in ['setup.py', 'setup.cfg', 'MANIFEST.in', 'unreviewed'])
    assert project.verify(projection, expected) == rows
    assert (repo / 'setup.py').read_text() == poison


@pytest.mark.parametrize('name', ['setup.py', 'setup.cfg', 'MANIFEST.in', 'unreviewed.py', 'src/attune_harness/extra.py'])
def test_extra_projection_build_control_or_code_refused(inputs, name):
    repo, projection, expected = inputs
    project.create(repo, projection, expected)
    (projection / name).write_text('raise AssertionError("must not execute")\n')
    with pytest.raises(ValueError):
        project.verify(projection, expected)


def test_extra_empty_projection_directory_refused(inputs):
    repo, projection, expected = inputs
    project.create(repo, projection, expected)
    (projection / 'unreviewed').mkdir()
    with pytest.raises(ValueError):
        project.verify(projection, expected)


@pytest.mark.parametrize('change', ['content', 'missing', 'crlf'])
def test_changed_projection_refused_before_backend(inputs, change):
    repo, projection, expected = inputs
    project.create(repo, projection, expected)
    target = projection / next(iter(expected))
    if change == 'missing':
        target.rename(target.with_suffix('.retained'))
    elif change == 'crlf':
        target.write_bytes(target.read_bytes().replace(b'\n', b'\r\n'))
    else:
        target.write_text('changed = True\n')
    with pytest.raises(ValueError):
        project.verify(projection, expected)


def test_changed_original_input_refused(inputs):
    repo, projection, expected = inputs
    (repo / 'README.md').write_text('unreviewed metadata')
    with pytest.raises(ValueError, match='input_identity'):
        project.create(repo, projection, expected)


def test_retained_projection_untouched(inputs):
    repo, projection, expected = inputs
    projection.mkdir()
    (projection / 'keep').write_text('retained')
    with pytest.raises(ValueError, match='retained_projection'):
        project.create(repo, projection, expected)
    assert (projection / 'keep').read_text() == 'retained'


def test_projection_inside_original_repository_refused(inputs):
    repo, _, expected = inputs
    with pytest.raises(ValueError, match='projection_location'):
        project.create(repo, repo / 'source', expected)


def test_symlink_projection_member_refused(inputs):
    repo, projection, expected = inputs
    project.create(repo, projection, expected)
    target = projection / 'README.md'
    target.rename(target.with_suffix('.retained'))
    try:
        target.symlink_to(repo / 'README.md')
    except OSError as exc:
        if os.name == 'nt' and getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows symlink privilege unavailable; no link-path qualification claimed')
        raise
    with pytest.raises(ValueError, match='member_kind'):
        project.verify(projection, expected)


@pytest.mark.parametrize('winerror', [None, 5, 1314])
def test_symlink_fixture_errors_only_skip_the_exact_windows_capability(inputs, monkeypatch, winerror):
    exc = OSError('controlled symlink fixture error')
    if winerror is not None:
        exc.winerror = winerror

    def controlled_error(self, target):
        raise exc

    monkeypatch.setattr(Path, 'symlink_to', controlled_error)
    if os.name == 'nt' and winerror == 1314:
        with pytest.raises(pytest.skip.Exception, match='Windows symlink privilege'):
            test_symlink_projection_member_refused(inputs)
    else:
        with pytest.raises(OSError, match='controlled symlink fixture error') as caught:
            test_symlink_projection_member_refused(inputs)
        assert caught.value is exc


def test_hardlinked_projection_member_refused(inputs):
    repo, projection, expected = inputs
    project.create(repo, projection, expected)
    target = projection / 'README.md'
    (projection.parent / 'alias').hardlink_to(target)
    with pytest.raises(ValueError, match='member_kind'):
        project.verify(projection, expected)


def test_receipt_must_stay_outside_projection(inputs):
    repo, projection, _ = inputs
    with pytest.raises(ValueError, match='report_inside_projection'):
        project.execute(repo, projection, repo / 'manifest', projection / 'receipt.json')


def test_backend_plan_forces_same_interpreter_isolation_and_projection(tmp_path):
    source = tmp_path / 'owned-source'
    extra = {'_PYPROJECT_HOOKS_BUILD_BACKEND': 'setuptools.build_meta'}
    argv, environment = project.backend_plan(['controller-python', 'trusted-hook.py', 'build_wheel', 'hook-data'],
        str(source), extra, source, 'controller-python', {'_PYPROJECT_HOOKS_BACKEND_PATH': 'unreviewed',
        '_PYPROJECT_HOOKS_BACKEND_PATH_JSON': '["unreviewed"]', 'SystemRoot': 'C:/Windows'})
    assert argv == ['controller-python', '-I', 'trusted-hook.py', 'build_wheel', 'hook-data']
    assert environment == {'SystemRoot': 'C:/Windows', **extra}


@pytest.mark.parametrize('change', ['interpreter', 'cwd', 'backend', 'backend_path', 'missing_extra'])
def test_backend_plan_refuses_other_code_routes(tmp_path, change):
    source = tmp_path / 'owned-source'
    command = ['controller-python', 'trusted-hook.py', 'build_wheel', 'hook-data']
    cwd = str(source)
    extra = {'_PYPROJECT_HOOKS_BUILD_BACKEND': 'setuptools.build_meta'}
    if change == 'interpreter':
        command[0] = 'other-python'
    elif change == 'cwd':
        cwd = str(tmp_path / 'original-repo')
    elif change == 'backend':
        extra['_PYPROJECT_HOOKS_BUILD_BACKEND'] = 'unreviewed'
    elif change == 'backend_path':
        extra['_PYPROJECT_HOOKS_BACKEND_PATH_JSON'] = '["original-repo"]'
    else:
        extra = None
    with pytest.raises(ValueError, match='backend_route'):
        project.backend_plan(command, cwd, extra, source, 'controller-python', {})


def test_failed_build_preserves_projected_rows_and_attempt_receipt(inputs, monkeypatch):
    import json
    repo, projection, expected = inputs
    project.create(repo, projection, expected)
    monkeypatch.setattr(project, 'inputs', lambda raw: expected)
    manifest = projection.parent / 'manifest-data'
    manifest.write_bytes(b'unit data only')
    receipt = projection.parent / 'attempt.json'

    def controlled_failure(source, destination, selected, report, checkpoint):
        report['backend_launch_attempted'] = True
        report['backend_argv'] = ['same-interpreter', '-I', 'controlled-test-hook']
        checkpoint()
        observed = json.loads(receipt.read_text())
        assert len(observed['rows']) == 116 and observed['backend_launch_attempted']
        raise ValueError('controlled failure; no backend executed')

    monkeypatch.setattr(project, 'build_projection', controlled_failure)
    assert project.execute(repo, projection, manifest, receipt, build_output=projection.parent / 'wheel') == 1
    observed = json.loads(receipt.read_text())
    assert observed['status'] == 'projection_refused' and observed['failure_type'] == 'ValueError'
    assert len(observed['rows']) == 116 and observed['backend_argv'][1] == '-I'
    assert not observed['backend_returned']


def test_missing_manifest_retains_typed_no_backend_report(inputs):
    import json
    repo, projection, _ = inputs
    receipt = projection.parent / 'missing-input.json'
    assert project.execute(repo, projection, repo / 'missing-manifest', receipt) == 1
    observed = json.loads(receipt.read_text())
    assert observed['failure_type'] == 'FileNotFoundError'
    assert not observed['backend_launch_attempted'] and not observed['backend_returned']


def _assert_finite_workflow_python_isolated(text):
    # This finite workflow uses only direct python calls or a simple assignment.
    # Inspect their first argument without running PowerShell or any child CLI.
    import re
    routes = re.findall(r'(?m)^\s*(?:\$[A-Za-z][A-Za-z0-9_]*\s*=\s*)?python\s+([^\n]+)$', text)
    assert len(routes) == 11, 'Review a changed controller invocation inventory.'
    assert all(route.split()[0] == '-I' for route in routes), 'Unisolated controller Python route.'


def test_every_original_repository_controller_python_call_is_isolated():
    text = (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()
    _assert_finite_workflow_python_isolated(text)


@pytest.mark.parametrize('route', [
    'python -I -m venv $venv',
    "python -I -m pip install 'build==1.3.0' 'setuptools==84.0.0'",
])
def test_preprojection_venv_and_pip_isolation_regressions_are_detected(route):
    text = (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()
    assert text.count(route) == 1
    # Each original v3 route independently trips the guard; the accepted form passes.
    _assert_finite_workflow_python_isolated(text)
    with pytest.raises(AssertionError, match='Unisolated controller'):
        _assert_finite_workflow_python_isolated(text.replace(route, route.replace(' -I ', ' ')))


def _assert_finite_fixture_caller_closed(text):
    # Static assertions for this one written call site, not a PowerShell interpreter.
    block = text.split('      - name: Observe with the exact reviewed owned GUI fixture\n', 1)[1].split('      - name: Retain observations', 1)[0]
    call = '& $fixture -ExecuteApprovedFixture -ExecuteReviewedGuiLease -GuiHelper $helper -BasePython $basePython -Wheel $wheel -ProofScript $driver -Output $output'
    assert block.count(call) == 1, 'Fixture call must use only prebound absolute arguments.'
    before_call, after_call = block.split(call)
    location = 'Set-Location -LiteralPath $fixtureCwd'
    assert before_call.count(location) == 1 and not after_call.strip(), 'Owned cwd must precede the sole call.'
    before_location, after_location = before_call.split(location)
    assert not after_location.strip(), 'Do not add relative input work after changing cwd.'
    for binding in [
        '$fixture = (Resolve-Path experiments/platform/windows_saved_store_standard_user_gui_proposal_v3b3.ps1).Path',
        '$helper = (Resolve-Path experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1).Path',
        '$driver = (Resolve-Path experiments/platform/windows_saved_store_combined_driver_v2.py).Path',
        '$basePython = python -I -c "import sys; print(sys._base_executable)"',
        '$wheel = (Get-ChildItem "$env:RUNNER_TEMP/saved-store-reviewed-projection/wheel/attune_harness-*.whl").FullName',
        "$output = Join-Path $env:RUNNER_TEMP 'saved-store-reviewed-observations'",
        "$owned = (Resolve-Path (Join-Path $env:RUNNER_TEMP 'saved-store-reviewed-projection')).Path",
        'foreach ($absoluteInput in @($fixture, $helper, $driver, $basePython, $wheel, $output, $owned))',
        '[IO.Path]::IsPathFullyQualified($absoluteInput)',
    ]:
        assert binding in before_location, 'Resolve and verify all paths before changing cwd.'
    required = [
        '$ownedItem = Get-Item -LiteralPath $owned -Force',
        '$ownedItem.PSIsContainer',
        '[IO.FileAttributes]::ReparsePoint',
        '$ownedAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $controller.Value',
        '-not $ownedAcl.AreAccessRulesProtected -or $ownedRules.Count -ne 2',
        "@($ownedRules | Where-Object { $_.IdentityReference.Value -ceq $controller.Value }).Count -ne 1",
        "@($ownedRules | Where-Object { $_.IdentityReference.Value -ceq 'S-1-5-18' }).Count -ne 1",
        "$_.IdentityReference.Value -notin @($controller.Value, 'S-1-5-18')",
        "$fixtureCwd = Join-Path $owned 'fixture-cwd'",
        'if (Test-Path -LiteralPath $fixtureCwd)',
        '$null = New-Item -ItemType Directory -Path $fixtureCwd',
        '$cwdAcl.SetAccessRuleProtection($true, $false)',
        '$cwdAcl.SetOwner($controller)',
        "foreach ($sid in @($controller.Value, 'S-1-5-18'))",
        'Set-Acl -LiteralPath $fixtureCwd -AclObject $cwdAcl',
        'if (@(Get-ChildItem -LiteralPath $fixtureCwd -Force).Count)',
        '$env:PYTHONHOME = $null',
        '$env:PYTHONPATH = $null',
        '$env:PYTHONUSERBASE = $null',
        "$env:PYTHONNOUSERSITE = '1'",
    ]
    for guard in required:
        assert guard in before_location, 'Missing owned-cwd/privacy/environment guard.'
    offsets = [before_location.index(guard) for guard in required[8:]]
    assert offsets == sorted(offsets), 'Create, protect, check empty, then scrub environment in order.'
    assert 'EnvironmentVariableTarget' not in block, 'No user/machine environment write.'


def test_fixture_call_resolves_absolute_inputs_and_uses_fresh_private_cwd():
    _assert_finite_fixture_caller_closed((ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text())


@pytest.mark.parametrize('changed, replacement', [
    ('Set-Location -LiteralPath $fixtureCwd', '# cwd omitted'),
    ('-GuiHelper $helper', '-GuiHelper experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1'),
    ('$env:PYTHONPATH = $null', '# ambient module path retained'),
    ("$env:PYTHONNOUSERSITE = '1'", '# user site remains enabled'),
    ('if (Test-Path -LiteralPath $fixtureCwd)', 'if ($false)'),
    ('[IO.Path]::IsPathFullyQualified($absoluteInput)', '$true'),
    ('Set-Acl -LiteralPath $fixtureCwd -AclObject $cwdAcl', '# private ACL omitted'),
    ('if (@(Get-ChildItem -LiteralPath $fixtureCwd -Force).Count)', 'if ($false)'),
])
def test_fixture_caller_route_regressions_are_detected(changed, replacement):
    text = (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()
    assert text.count(changed) == 1
    _assert_finite_fixture_caller_closed(text)
    with pytest.raises(AssertionError):
        _assert_finite_fixture_caller_closed(text.replace(changed, replacement))


def test_environment_scrub_after_fixture_call_is_detected():
    text = (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()
    line = '          $env:PYTHONPATH = $null\n'
    call = '          & $fixture -ExecuteApprovedFixture'
    assert text.count(line) == 1
    text = text.replace(line, '')
    start = text.index(call)
    end = text.index('\n', start) + 1
    with pytest.raises(AssertionError):
        _assert_finite_fixture_caller_closed(text[:end] + line + text[end:])
