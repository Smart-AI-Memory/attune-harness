"""Release consumers refuse a changed artifact, source or installed provenance."""
import base64
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tarfile
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_windows_release_wheel.py'
SHA = 'a' * 40
VERSION = '1.7.0'
DIST_INFO = 'attune_harness-1.7.0.dist-info/'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('windows_release_wheel_check', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checkout, runner = tmp_path / 'source', tmp_path / 'runner'
    checkout.mkdir()
    runner.mkdir()
    (checkout / 'pyproject.toml').write_text('[project]\nname="attune-harness"\nversion="1.7.0"\n')
    dist, evidence = runner / 'distributions', runner / 'build-evidence'
    dist.mkdir()
    evidence.mkdir()
    source = {'attune_harness/__init__.py': b'VALUE = 1\n',
              'attune_voyage_plugin/__init__.py': b'VALUE = 2\n',
              'attune_harness/assets/lock.lua': b'return 1\n'}
    canonical = io.BytesIO()
    with tarfile.open(fileobj=canonical, mode='w') as archive:
        for name, raw in {**{'src/' + k: v for k, v in source.items()}, 'LICENSE': b'license\n'}.items():
            item = tarfile.TarInfo(name)
            item.size = len(raw)
            archive.addfile(item, io.BytesIO(raw))
    state = SimpleNamespace(head=SHA, module=module, dist=dist, evidence=evidence,
                            checkout=checkout, runner=runner, source=source)
    def git(argv, **kwargs):
        if argv[1:3] == ['rev-parse', 'HEAD']:
            return state.head + '\n'
        if argv[1] == 'status':
            return b''
        if argv[1] == 'archive':
            return canonical.getvalue()
        raise AssertionError(argv)
    monkeypatch.setattr(module, 'ROOT', checkout)
    monkeypatch.setattr(module.subprocess, 'check_output', git)
    environment = {'RUNNER_TEMP': str(runner), 'RELEASE_SHA': SHA, 'RELEASE_VERSION': VERSION,
                   'RELEASE_TARGET': 'pypi', 'GITHUB_SHA': SHA,
                   'GITHUB_REPOSITORY': 'Smart-AI-Memory/attune-harness',
                   'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1',
                   'DISTRIBUTIONS_ID': '100', 'DISTRIBUTIONS_DIGEST': '1' * 64,
                   'RELEASE_EVIDENCE_ID': '101', 'RELEASE_EVIDENCE_DIGEST': '2' * 64}
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    (evidence / 'preflight.json').write_text(json.dumps({'status': 'passed', 'commit': SHA, 'version': VERSION}))
    state.args = SimpleNamespace(dist=dist, evidence=evidence, installed=False)
    def write(*, payloads=None, metadata_version=VERSION, wrong_record=False):
        members = dict(source if payloads is None else payloads)
        members[DIST_INFO + 'METADATA'] = ('Metadata-Version: 2.4\nName: attune-harness\nVersion: ' + metadata_version + '\n').encode()
        members[DIST_INFO + 'WHEEL'] = b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
        members[DIST_INFO + 'licenses/LICENSE'] = b'license\n'
        record = io.StringIO()
        writer = csv.writer(record, lineterminator='\n')
        for name, raw in sorted(members.items()):
            encoded = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
            writer.writerow([name, 'sha256=' + ('invalid' if wrong_record else encoded), str(len(raw))])
        writer.writerow([DIST_INFO + 'RECORD', '', ''])
        members[DIST_INFO + 'RECORD'] = record.getvalue().encode()
        wheel = dist / 'attune_harness-1.7.0-py3-none-any.whl'
        with zipfile.ZipFile(wheel, 'w') as archive:
            for name, raw in members.items():
                archive.writestr(name, raw)
        (dist / 'attune_harness-1.7.0.tar.gz').write_bytes(b'synthetic sdist; not extracted or installed\n')
        files = {p.name: {'sha256': digest(p.read_bytes()), 'size': p.stat().st_size} for p in dist.iterdir()}
        (evidence / 'SHA256SUMS').write_text(''.join(v['sha256'] + '  dist/' + k + '\n' for k, v in sorted(files.items())))
        manifest = {'schema_version': 1, 'repository': environment['GITHUB_REPOSITORY'],
                    'workflow_run_id': 123, 'workflow_run_attempt': 1, 'commit': SHA,
                    'version': VERSION, 'target': 'pypi', 'files': files}
        (evidence / 'windows-consumer-manifest.json').write_text(json.dumps(manifest))
        state.members, state.wheel, state.manifest = members, wheel, manifest
    state.write = write
    write()
    return state


def test_exact_source_version_record_and_artifact_are_bound(candidate):
    receipt = candidate.module.verify(candidate.args)
    assert receipt['status'] == 'archive_verified'
    assert receipt['commit'] == SHA and receipt['version'] == VERSION
    assert receipt['wheel_sha256'] == digest(candidate.wheel.read_bytes())
    assert receipt['producer_manifest']['workflow_run_id'] == 123
    assert set(receipt['payload_sha256']) == set(candidate.source)


def test_changed_checkout_is_refused(candidate):
    candidate.head = 'b' * 40
    with pytest.raises(ValueError, match='reviewed release SHA'):
        candidate.module.verify(candidate.args)


def test_changed_source_version_is_refused(candidate):
    (candidate.checkout / 'pyproject.toml').write_text('[project]\nname="attune-harness"\nversion="1.7.1"\n')
    with pytest.raises(ValueError, match='Source metadata'):
        candidate.module.verify(candidate.args)


@pytest.mark.parametrize('field,value', [('workflow_run_id', 124), ('workflow_run_attempt', 2),
    ('repository', 'other/repository'), ('commit', 'b' * 40), ('version', '1.7.1'), ('target', 'testpypi')])
def test_wrong_run_attempt_or_release_manifest_is_refused(candidate, field, value):
    candidate.manifest[field] = value
    (candidate.evidence / 'windows-consumer-manifest.json').write_text(json.dumps(candidate.manifest))
    with pytest.raises(ValueError, match='exact run, attempt or release'):
        candidate.module.verify(candidate.args)


def test_changed_whole_wheel_bytes_are_refused(candidate):
    with candidate.wheel.open('ab') as stream:
        stream.write(b'tampered')
    with pytest.raises(ValueError, match='checksum mismatch'):
        candidate.module.verify(candidate.args)


def test_changed_wheel_metadata_version_is_refused(candidate):
    candidate.write(metadata_version='1.7.1')
    with pytest.raises(ValueError, match='Wheel metadata'):
        candidate.module.verify(candidate.args)


def test_invalid_wheel_record_is_refused(candidate):
    candidate.write(wrong_record=True)
    with pytest.raises(ValueError, match='RECORD mismatch'):
        candidate.module.verify(candidate.args)


def test_crlf_normalized_wheel_is_not_called_the_canonical_artifact(candidate):
    payload = {**candidate.source, 'attune_harness/__init__.py': b'VALUE = 1\r\n'}
    candidate.write(payloads=payload)
    with pytest.raises(ValueError, match='canonical Git'):
        candidate.module.verify(candidate.args)


@pytest.mark.parametrize('name', ['../escape.py', '/absolute.py', 'attune_harness\\escape.py'])
def test_unsafe_member_inventory_is_refused(candidate, name):
    candidate.write(payloads={**candidate.source, name: b'invalid\n'})
    with pytest.raises(ValueError, match='Unexpected wheel member'):
        candidate.module.verify(candidate.args)


def test_unexpected_safe_payload_is_refused(candidate):
    candidate.write(payloads={**candidate.source, 'other_package/__init__.py': b'extra\n'})
    with pytest.raises(ValueError, match='canonical Git'):
        candidate.module.verify(candidate.args)


def installed(candidate, monkeypatch):
    prefix = candidate.runner / 'profile'
    site = prefix / 'site-packages'
    for name, raw in candidate.members.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    origin = {'url': candidate.wheel.resolve().as_uri(), 'archive_info': {'hashes': {'sha256': digest(candidate.wheel.read_bytes())}}}
    class Distribution:
        version = VERSION
        def read_text(self, name):
            assert name == 'direct_url.json'
            return json.dumps(origin)
        def locate_file(self, name):
            return site / name
    monkeypatch.setattr(candidate.module, 'sys', SimpleNamespace(prefix=str(prefix)))
    monkeypatch.setattr(candidate.module, 'importlib', SimpleNamespace(metadata=SimpleNamespace(distribution=lambda name: Distribution())))
    monkeypatch.setattr(candidate.module, 'runpy', SimpleNamespace(run_path=lambda path: {'installed_partition_identity': lambda deadline: {'delegated_existing_RECORD_and_input_check': True}}))
    candidate.args.installed = True
    return origin, site


def test_installed_archive_entries_and_direct_url_are_bound(candidate, monkeypatch):
    installed(candidate, monkeypatch)
    assert candidate.module.verify(candidate.args)['status'] == 'installed_verified'


def test_changed_installed_file_is_refused(candidate, monkeypatch):
    origin, site = installed(candidate, monkeypatch)
    (site / 'attune_harness/__init__.py').write_bytes(b'changed\n')
    with pytest.raises(ValueError, match='Installed wheel payload/metadata differs'):
        candidate.module.verify(candidate.args)


def test_wrong_direct_url_archive_hash_is_refused(candidate, monkeypatch):
    origin, site = installed(candidate, monkeypatch)
    origin['archive_info']['hashes']['sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='Installed direct_url'):
        candidate.module.verify(candidate.args)


def test_existing_record_validation_failure_is_not_bypassed(candidate, monkeypatch):
    installed(candidate, monkeypatch)
    def refuse(deadline):
        raise ValueError('existing RECORD/source/input guard failed')
    monkeypatch.setattr(candidate.module, 'runpy', SimpleNamespace(run_path=lambda path: {'installed_partition_identity': refuse}))
    with pytest.raises(ValueError, match='existing RECORD/source/input guard failed'):
        candidate.module.verify(candidate.args)
