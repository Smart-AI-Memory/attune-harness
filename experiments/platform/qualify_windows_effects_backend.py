"""Installed Windows effects qualification with bounded, retained native output.

Two modes, because two different questions get asked of this script.

Observed (the default, and what CI runs on pull requests and on main): build,
install, prove the installed package is the source in this checkout, and run the
native tests. It records every module's hash in the receipt but compares them
with nothing, so it keeps working as main moves.

Frozen (--source-manifest and --candidate-manifest together): additionally
require the exact bytes named by two frozen manifests. This qualifies one
candidate. Any later change to any module fails it, by design.

If frozen mode fails with a hash mismatch, the manifests are not broken and the
fix is not to regenerate them. They record what was qualified. Freezing a new
candidate is Patrick Roebuck's decision; ask him, and add new manifests beside
the old ones rather than editing these.
"""

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MAX_LOG = 2 * 1024 * 1024
TEST_DEADLINE = 180


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def lf(raw):
    normalized = raw.replace(b'\r\n', b'\n')
    if b'\r' in normalized:
        raise ValueError('Standalone carriage return in module bytes')
    return normalized


def counts(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else root.findall('testsuite')
    return {name: sum(int(s.get(name, '0')) for s in suites)
            for name in ('tests', 'failures', 'errors', 'skipped')}


FROZEN_HELP = (' This is frozen evidence of one qualified candidate, not a defect in your change.'
               ' Do not regenerate or edit the manifest to make it pass; ask Patrick Roebuck'
               ' whether to freeze a new candidate.')


def module_identity(package, sources, expected=None):
    """Return per-module hashes after proving installed bytes are the source bytes.

    `expected` is a frozen {module name: LF-normalized sha256}; None observes only.
    """
    installed_names = {p.name for p in package.glob('*.py')}
    source_names = {p.name for p in sources.glob('*.py')}
    if installed_names != source_names:
        raise ValueError('Installed module set differs from this checkout: '
                         + ', '.join(sorted(installed_names ^ source_names)))
    if expected is not None and installed_names != set(expected):
        raise ValueError('Module set differs from the frozen source manifest: '
                         + ', '.join(sorted(installed_names ^ set(expected))) + '.' + FROZEN_HELP)
    rows = {}
    for name in sorted(installed_names):
        installed = (package / name).read_bytes()
        if installed != (sources / name).read_bytes():
            raise ValueError('Installed module bytes differ from this checkout: ' + name)
        identity = sha(lf(installed))
        if expected is not None and identity != expected[name]:
            raise ValueError('Module differs from the frozen source manifest: ' + name + '.'
                             + FROZEN_HELP)
        rows[name] = {'executed_sha256': sha(installed), 'git_lf_sha256': identity}
    return rows


def installed_identity(source_manifest=None):
    import attune_harness

    package = Path(attune_harness.__file__).resolve().parent
    if package.is_relative_to(ROOT) or not package.is_dir():
        raise ValueError('Harness import resolved inside source checkout')
    expected = None
    if source_manifest is not None:
        expected = json.loads(source_manifest.read_text())['modules_git_lf_sha256']
    rows = module_identity(package, ROOT / 'src/attune_harness', expected)
    for name in ('repair', 'work_effects', 'windows_effects', 'work_build', 'process', 'windows'):
        origin = Path(importlib.import_module('attune_harness.' + name).__file__).resolve()
        if origin != package / (name + '.py'):
            raise ValueError('Imported module origin differs from installed package: ' + name)
    return package, rows, None if source_manifest is None else sha(source_manifest.read_bytes())


def stream_run(argv, cwd, env, log_path):
    start = time.monotonic()
    stop = []
    with log_path.open('wb') as log:
        process = subprocess.Popen(argv, cwd=cwd, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        def drain():
            retained = 0
            while True:
                chunk = process.stdout.read1(4096)
                if not chunk:
                    break
                remaining = MAX_LOG - retained
                if remaining > 0:
                    selected = chunk[:remaining]
                    log.write(selected)
                    log.flush()
                    sys.stdout.write(selected.decode('utf-8', errors='replace'))
                    sys.stdout.flush()
                    retained += len(selected)
                if len(chunk) > remaining:
                    stop.append('log_limit')
                    process.kill()
                    break
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            process.wait(timeout=TEST_DEADLINE)
        except subprocess.TimeoutExpired:
            stop.append('timeout')
            process.kill()
            process.wait(timeout=10)
        reader.join(timeout=10)
        if reader.is_alive():
            stop.append('reader_unfinished')
        else:
            # A grandchild can retain the write end after pytest is killed.
            # close() could wait on read1's internal lock forever here.
            process.stdout.close()
    return process.returncode, stop[0] if stop else None, round(time.monotonic() - start, 3)


def optional_path(value):
    # A dispatch input left blank arrives as an empty string, not as absence.
    return Path(value) if value else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-manifest', type=optional_path,
                        help='frozen mode: manifest of every module hash (needs --candidate-manifest)')
    parser.add_argument('--candidate-manifest', type=optional_path,
                        help='frozen mode: manifest of candidate file hashes (needs --source-manifest)')
    args = parser.parse_args()
    if (args.source_manifest is None) != (args.candidate_manifest is None):
        parser.error('--source-manifest and --candidate-manifest are used together')
    frozen_mode = args.source_manifest is not None
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 'windows-effect-installed-journey-v2',
               'identity': 'frozen' if frozen_mode else 'observed',
               'status': 'failed', 'python': platform.python_version(),
               'platform': platform.platform(), 'commit': os.environ.get('GITHUB_SHA'),
               'requested_runner': os.environ.get('ATTUNE_CI_WINDOWS_LABEL'),
               'provider_calls': 0, 'selected_tests': 'tests/test_windows_effects.py',
               'timeout_seconds': TEST_DEADLINE, 'max_log_bytes': MAX_LOG}
    try:
        package, modules, source_manifest_sha = installed_identity(args.source_manifest)
        receipt.update(installed_package=str(package), modules=modules,
                       source_manifest_sha256=source_manifest_sha)
        if frozen_mode:
            candidate = args.candidate_manifest
            receipt['candidate_manifest_sha256'] = sha(candidate.read_bytes())
            for relative, expected in json.loads(candidate.read_text())['paths'].items():
                if sha(lf((ROOT / relative).read_bytes())) != expected:
                    raise ValueError('File differs from the frozen candidate manifest: '
                                     + relative + '.' + FROZEN_HELP)
        wheel = next((ROOT / 'dist').glob('attune_harness-*.whl'))
        receipt['wheel_sha256'] = sha(wheel.read_bytes())
        env = dict(os.environ)
        env.update(ATTUNE_USAGE_PING='0', ATTUNE_VERSION_CHECK='0',
                   DO_NOT_TRACK='1', PYTHONDONTWRITEBYTECODE='1',
                   PYTHONNOUSERSITE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        env.pop('PYTEST_ADDOPTS', None)
        env.pop('PYTEST_PLUGINS', None)
        consumer = Path(tempfile.mkdtemp(prefix='attune-windows-effects-consumer-'))
        config = consumer / 'pytest.ini'
        config.write_text('[pytest]\n')
        xml = out / 'tests.xml'
        log = out / 'tests.log'
        argv = [sys.executable, '-I', '-m', 'pytest', '-q', '-c', str(config),
                '-o', 'pythonpath=', '--junitxml=' + str(xml),
                str(ROOT / 'tests/test_windows_effects.py')]
        receipt['consumer_cwd'] = str(consumer)
        receipt['argv'] = argv
        code, stop, duration = stream_run(argv, consumer, env, log)
        receipt.update(returncode=code, stop_reason=stop, duration_seconds=duration,
                       log_sha256=sha(log.read_bytes()))
        if xml.is_file():
            receipt['counts'] = counts(xml)
            receipt['junit_sha256'] = sha(xml.read_bytes())
        found = receipt.get('counts') or {}
        # On a native runner nothing may skip: a skip means the test did not run here.
        clean = (code == 0 and stop is None and found.get('tests', 0) > 0
                 and not (found.get('failures') or found.get('errors') or found.get('skipped')))
        if not clean or (frozen_mode and found.get('tests') != 10):
            raise ValueError('Installed native test selection did not pass exactly')
        receipt['status'] = 'passed'
    except BaseException as exc:
        receipt['error'] = {'type': type(exc).__name__, 'detail': str(exc)[:1000]}
    result = out / 'receipt.json'
    result.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': receipt['status'], 'counts': receipt.get('counts'),
                      'receipt': str(result)}, sort_keys=True))
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
