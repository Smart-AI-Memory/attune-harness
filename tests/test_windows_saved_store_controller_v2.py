"""Current controller inputs, retained component evidence and account-free gates."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / 'experiments/platform'
CURRENT = PLATFORM / 'windows_saved_store_controller_v2'
WORKFLOWS = (
    '.github/workflows/windows-saved-store-component-build-safe-preflight.yml',
    '.github/workflows/windows-saved-store-prefixture-join.yml',
)
ARCHIVE = ROOT / 'tests/fixtures/windows_saved_store_controller_v2.zip'


def load(path):
    spec = importlib.util.spec_from_file_location('controller_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected(text):
    block, = re.findall(r'\$expected = \[ordered\]@\{(.*?)\n          \}', text, re.S)
    return dict(re.findall(r"'([^']+)' = '([0-9a-f]{64})'", block))


def canonical_bytes(path):
    # Match the existing pure checkout-rendering witness. Runtime admission
    # always consumes exact Git bytes; this only handles Windows text checkout.
    raw = path.read_bytes()
    if path.suffix == '.zip':
        return raw
    if b'\r\n' in raw:
        assert b'\n' not in raw.replace(b'\r\n', b'')
        raw = raw.replace(b'\r\n', b'\n')
    return raw


def test_historical_scripts_and_manifest_are_unchanged():
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in archive.namelist():
            if name not in WORKFLOWS:
                assert canonical_bytes(ROOT / name) == archive.read(name)
        historical = expected(archive.read(WORKFLOWS[0]).decode())
    assert historical['requirements-mcp.lock'] == '50f956aff914ee8ca2e85e00e3cc35aa56fff07213b659d962d7c9d91be94735'
    assert hashlib.sha256((ROOT / 'requirements-mcp.lock').read_bytes()).hexdigest() != historical['requirements-mcp.lock']


def test_successor_changes_controller_inputs_and_keeps_fixed_component():
    old = load(PLATFORM / 'windows_saved_store_component_route_v1.py')
    new = load(CURRENT / 'route.py')
    inputs = json.loads((CURRENT / 'inputs.json').read_bytes())
    assert inputs['account_fixture_authorized'] is False
    assert inputs['provider_calls_authorized'] is False
    assert new.ADAPTER_SHA == old.ADAPTER_SHA
    assert inputs['fixed_component_manifest'] == old.PROTOCOL['manifest.json']
    assert len(inputs['locks']) == 5 and len(new.PROTOCOL) == 12
    for name, row in inputs['locks'].items():
        assert row == new.PROTOCOL[name]
        raw = (ROOT / row['source']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    for name, row in old.PROTOCOL.items():
        if name not in inputs['locks']:
            assert new.PROTOCOL[name] == row


@pytest.mark.parametrize('damage', [False, True])
def test_actual_successor_protocol_admits_exact_inputs_or_refuses_before_output(tmp_path, damage):
    route = load(CURRENT / 'route.py')
    projector = load(PLATFORM / 'project_windows_saved_store_build_v2.py')
    repo, target = tmp_path / 'repo', tmp_path / 'protocol'
    repo.mkdir()
    for row in route.PROTOCOL.values():
        path = repo / row['source']; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / row['source']).read_bytes())
    if damage:
        (repo / 'requirements-mcp.lock').write_bytes(b'changed\n')
        with pytest.raises(ValueError): route.stage_protocol(repo, target, projector)
        assert not target.exists()
    else:
        rows = route.stage_protocol(repo, target, projector)
        assert len(rows) == 12 and projector.verify(target, route.PROTOCOL) == rows


def test_preflight_keeps_capture_startup_and_refusal_contracts():
    old = (PLATFORM / 'windows_saved_store_build_preflight_v3.ps1').read_text()
    new = (CURRENT / 'preflight.ps1').read_text()
    for name in ('query', 'installedQuery'):
        pattern = r'\$' + name + " = @'\n(.*?)\n'@"
        assert re.findall(pattern, old, re.S) == re.findall(pattern, new, re.S)
    pattern = r"Add-Type -TypeDefinition @'\n(.*?)\n'@"
    assert re.findall(pattern, old, re.S) == re.findall(pattern, new, re.S)
    assert new.index('$wheelLease = [IO.File]::Open(') < new.index("Run-Recorded 'startup-child'") < new.index('$wheelLease.Dispose()')
    assert "windows_saved_store_controller_v2/route.py" in new
    protocol_count, = re.findall(r'\$report.component.protocol_rows.Count -ne (\d+)', new)
    assert int(protocol_count) == len(load(CURRENT / 'route.py').PROTOCOL)
    assert '-ExecuteApprovedFixture' not in new and '-ExecuteReviewedGuiLease' not in new


def test_new_caller_refuses_account_mode_and_closes_the_complete_pinned_set():
    text = (CURRENT / 'pre_fixture.ps1').read_text()
    guard = "if (-not $PreFixtureOnly) { throw 'This controller version is account-free only.' }"
    assert text.index(guard) < text.index('[Security.Principal.WindowsIdentity]::GetCurrent()')
    block, = re.findall(r"\$pinsJson = @'\n(.*?)\n'@", text, re.S)
    pins = json.loads(block)
    gate = load(CURRENT / 'entry.py')
    assert len(pins) == len({p.casefold() for p in pins}) == gate.ENTRY_COUNT
    for name, digest in pins.items():
        assert hashlib.sha256(canonical_bytes(ROOT / name)).hexdigest() == digest
    assert text.count(f'$sourceLeases.Count -eq {gate.ENTRY_COUNT}') == 1
    assert text.count(f'$caller.sources_verified_count -ne {gate.ENTRY_COUNT}') == 1
    with pytest.raises(ValueError, match='entry_finite'):
        gate.admit(ROOT, ROOT / 'unused-test-output', {}, '0' * 64)


@pytest.mark.parametrize('workflow', WORKFLOWS, ids=['build', 'pre-fixture'])
@pytest.mark.parametrize('damage', [None, 'blob', 'event'], ids=['valid', 'wrong-blob', 'wrong-event'])
def test_extracted_current_git_bootstrap_accepts_or_refuses_exact_inputs(tmp_path, workflow, damage):
    text = (ROOT / workflow).read_text()
    pins = expected(text)
    script, = re.findall(r"\$materialize = @'\n(.*?)\n          '@", text, re.S)
    script = textwrap.dedent(script)
    repo, reports = tmp_path / 'repo', tmp_path / 'reports'
    repo.mkdir(); reports.mkdir()
    for name in pins:
        path = repo / name; path.parent.mkdir(parents=True, exist_ok=True)
        raw = canonical_bytes(ROOT / name) if path.suffix != '.zip' else (ROOT / name).read_bytes()
        path.write_bytes(raw)
    if damage == 'blob':
        (repo / 'requirements-mcp.lock').write_bytes(b'changed\n')
    environment = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    def git(*args):
        result = subprocess.run(['git', *args], cwd=repo, env=environment,
                                capture_output=True, timeout=30, check=True)
        return result.stdout.decode().strip()
    git('init', '-q'); git('add', '.')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Frozen input fixture')
    head = git('rev-parse', 'HEAD')
    environment.update(RUNNER_TEMP=str(reports), T2_EVENT_SHA='f' * 40 if damage == 'event' else head)
    result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(repo), json.dumps(pins)],
                            env=environment, capture_output=True, timeout=120)
    report = json.loads((reports / 'saved-store-component-bootstrap.json').read_text())
    assert result.returncode == (1 if damage else 0), result.stderr.decode(errors='replace')
    assert report['status'] == ('bootstrap_refused' if damage else 'current_C_raw_inputs_materialized')
    assert report['account_fixture_invoked'] is False and report['accounts_or_credentials_created'] is False
    if not damage:
        assert len(report['rows']) == len(pins) and all(r['status'] == 'materialized' for r in report['rows'])


def test_current_workflows_cover_successors_and_retain_account_gates():
    for workflow in WORKFLOWS:
        text = (ROOT / workflow).read_text()
        pins = expected(text)
        for name in ('inputs.json', 'route.py', 'entry.py', 'preflight.ps1', 'pre_fixture.ps1', '.gitattributes'):
            relative = 'experiments/platform/windows_saved_store_controller_v2/' + name
            assert relative in pins and text.count("      - '" + relative + "'") == 2
        assert 'workflow_dispatch' not in text and 'branches: [main]' in text
        assert 'cancel-in-progress: false' in text and 'contents: read' in text
        assert 'test_windows_saved_store_controller_v2.py' in text
    text = (ROOT / WORKFLOWS[1]).read_text()
    assert 'GITHUB_RUN_ATTEMPT' in text and '-PreFixtureOnly' in text
    for path in ('windows-saved-store-reviewed-execution.yml', 'windows-saved-store-component-account-proposal.yml'):
        assert 'if: ${{ false }}' in (ROOT / '.github/workflows' / path).read_text()
