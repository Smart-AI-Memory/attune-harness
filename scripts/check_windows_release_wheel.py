"""Bind a Windows release consumer to its same-run immutable Ubuntu wheel."""

import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import subprocess
import sys
import tarfile
import time
import tomllib
from urllib.parse import urlsplit
from urllib.request import url2pathname
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(args):
    """Require same-run identity, archive/RECORD bytes and canonical Git payloads."""
    sha, version = os.environ['RELEASE_SHA'], os.environ['RELEASE_VERSION']
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r'[a-f0-9]{40}', sha) or head != sha or os.environ['GITHUB_SHA'] != sha:
        raise ValueError('Checkout and dispatch must equal the reviewed release SHA')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT):
        raise ValueError('Tracked release inputs changed')
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    if project['name'] != 'attune-harness' or project['version'] != version:
        raise ValueError('Source metadata differs from the release request')
    evidence = args.evidence.resolve(strict=True)
    if not evidence.is_relative_to(Path(os.environ['RUNNER_TEMP']).resolve()):
        raise ValueError('Downloaded evidence must be in the owned runner temporary root')
    preflight = json.loads((evidence / 'preflight.json').read_text(encoding='utf-8'))
    statuses = {'pypi': 'passed', 'testpypi': 'provisional_rehearsal_preflight_passed'}
    if (preflight.get('commit') != sha or preflight.get('version') != version
            or preflight.get('status') != statuses[os.environ['RELEASE_TARGET']]):
        raise ValueError('Same-run preflight differs from the release request')
    if os.environ['GITHUB_REPOSITORY'] != 'Smart-AI-Memory/attune-harness':
        raise ValueError('Unexpected release repository')
    artifacts = {}
    for name in ('DISTRIBUTIONS', 'RELEASE_EVIDENCE'):
        artifact_id, artifact_digest = os.environ[name + '_ID'], os.environ[name + '_DIGEST']
        if not artifact_id.isdecimal() or int(artifact_id) < 1 or not re.fullmatch(r'[a-f0-9]{64}', artifact_digest):
            raise ValueError('Missing immutable same-run artifact identity')
        artifacts[name.lower()] = {'id': int(artifact_id), 'sha256': artifact_digest}
    manifest_path = evidence / 'windows-consumer-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    expected_identity = {'schema_version': 1, 'repository': os.environ['GITHUB_REPOSITORY'],
                         'workflow_run_id': int(os.environ['GITHUB_RUN_ID']),
                         'workflow_run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
                         'commit': sha, 'version': version, 'target': os.environ['RELEASE_TARGET']}
    if any(manifest.get(key) != value for key, value in expected_identity.items()):
        raise ValueError('Producer manifest differs from this exact run, attempt or release request')
    names = {f'attune_harness-{version}-py3-none-any.whl', f'attune_harness-{version}.tar.gz'}
    dist = args.dist.resolve(strict=True)
    if not dist.is_relative_to(Path(os.environ['RUNNER_TEMP']).resolve()):
        raise ValueError('Downloaded distributions must stay in the owned runner temporary root')
    if {p.name for p in dist.iterdir()} != names:
        raise ValueError('Exactly the matching wheel and sdist are required')
    sums = {}
    for line in (evidence / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  dist/([^/\\]+)', line)
        if match is None or match[2] in sums:
            raise ValueError('Unexpected or duplicate checksum entry')
        sums[match[2]] = match[1]
    if set(sums) != names:
        raise ValueError('Checksum inventory differs from the distributions')
    for name in names:
        path = dist / name
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != sums[name]:
            raise ValueError('Distribution checksum mismatch: ' + name)
    actual_files = {name: {'sha256': sums[name], 'size': (dist / name).stat().st_size} for name in names}
    if manifest.get('files') != actual_files:
        raise ValueError('Producer manifest differs from exact distribution bytes')
    wheel = dist / f'attune_harness-{version}-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        members = {}
        for info in infos:
            name = info.filename
            if (info.orig_filename != name or name in members or info.is_dir()
                    or '\\' in name or PurePosixPath(name).is_absolute()
                    or '..' in PurePosixPath(name).parts or info.external_attr >> 16 & 0o170000 == 0o120000):
                raise ValueError('Unexpected wheel member')
            members[name] = archive.read(info)
    metadata_root = f'attune_harness-{version}.dist-info/'
    metadata = BytesParser().parsebytes(members[metadata_root + 'METADATA'])
    if metadata['Name'] != 'attune-harness' or metadata['Version'] != version:
        raise ValueError('Wheel metadata differs from requested source version')
    records = list(csv.reader(io.StringIO(members[metadata_root + 'RECORD'].decode('utf-8'))))
    if len(records) != len(members) or {r[0] for r in records} != set(members):
        raise ValueError('Wheel RECORD inventory differs')
    for name, encoded, size in records:
        if name == metadata_root + 'RECORD':
            if encoded or size:
                raise ValueError('RECORD must omit its own hash and size')
        elif encoded != 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(members[name]).digest()).decode().rstrip('=') or size != str(len(members[name])):
            raise ValueError('Wheel RECORD mismatch: ' + name)
    raw = subprocess.check_output(['git', 'archive', '--format=tar', sha, '--', 'src', 'LICENSE'], cwd=ROOT)
    canonical = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for item in archive.getmembers():
            if item.isfile() and item.name.startswith('src/') and item.name.endswith(('.py', '.lua')):
                canonical[item.name[len('src/'):]] = archive.extractfile(item).read()
            elif item.isfile() and item.name == 'LICENSE':
                if members[metadata_root + 'licenses/LICENSE'] != archive.extractfile(item).read():
                    raise ValueError('License differs from canonical Git bytes')
    payloads = {name: value for name, value in members.items() if not name.startswith(metadata_root)}
    if payloads != canonical:
        raise ValueError('Packaged runtime payload set or bytes differ from canonical Git')
    receipt = {'schema_version': 1, 'status': 'archive_verified', 'commit': sha, 'version': version,
               'repository': os.environ['GITHUB_REPOSITORY'], 'workflow_run_id': int(os.environ['GITHUB_RUN_ID']),
               'workflow_run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']), 'artifacts': artifacts,
               'distributions_sha256': sums, 'wheel': str(wheel), 'wheel_sha256': sums[wheel.name],
               'producer_manifest': manifest, 'producer_manifest_sha256': digest(manifest_path.read_bytes()),
               'preflight_sha256': digest((evidence / 'preflight.json').read_bytes()),
               'sha256sums_sha256': digest((evidence / 'SHA256SUMS').read_bytes()),
               'payload_sha256': {name: digest(value) for name, value in payloads.items()}}
    if args.installed:
        check = runpy.run_path(str(ROOT / 'scripts/qualify_platform.py'))
        identity = check['installed_partition_identity'](time.monotonic() + 120)
        distribution = importlib.metadata.distribution('attune-harness')
        provenance = json.loads(distribution.read_text('direct_url.json'))
        origin = urlsplit(provenance['url'])
        if (distribution.version != version or origin.scheme != 'file' or origin.netloc not in ('', 'localhost')
                or Path(url2pathname(origin.path)).resolve() != wheel.resolve()
                or provenance.get('dir_info') or provenance.get('archive_info', {}).get('hashes', {}).get('sha256') != sums[wheel.name]):
            raise ValueError('Installed direct_url does not bind the verified wheel')
        for name, value in members.items():
            if name == metadata_root + 'RECORD':
                continue  # pip rewrites RECORD to include generated scripts/provenance.
            path = Path(distribution.locate_file(name))
            if (path.is_symlink() or not path.resolve().is_relative_to(Path(sys.prefix).resolve())
                    or not path.is_file() or path.read_bytes() != value):
                raise ValueError('Installed wheel payload/metadata differs: ' + name)
        receipt.update(status='installed_verified', direct_url=provenance, installed_identity=identity)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if (not output.is_relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
            or output.suffix != '.json' or output.exists()):
        raise ValueError('Choose a fresh JSON receipt in the owned runner temporary root')
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        receipt = verify(args)
    except Exception as error:
        output.write_text(json.dumps({'status': 'failed', 'error_type': type(error).__name__,
                                      'error': str(error)}, indent=2) + '\n', encoding='utf-8')
        raise
    output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
