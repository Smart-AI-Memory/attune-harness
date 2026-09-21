"""Installed Windows effects qualification with bounded, retained native output."""

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
RECEIPT_DIR = ROOT / 'docs/receipts/release-readiness-current/windows-feature-effects'
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


def installed_identity():
    import attune_harness

    package = Path(attune_harness.__file__).resolve().parent
    if package.is_relative_to(ROOT) or not package.is_dir():
        raise ValueError('Harness import resolved inside source checkout')
    manifest = RECEIPT_DIR / 'backend-main-source67.json'
    expected = json.loads(manifest.read_text())['modules_git_lf_sha256']
    sources = ROOT / 'src/attune_harness'
    actual_names = {p.name for p in package.glob('*.py')}
    if actual_names != set(expected) or {p.name for p in sources.glob('*.py')} != set(expected):
        raise ValueError('Installed/source module set differs from frozen 67 modules')
    rows = {}
    for name, frozen in expected.items():
        installed = (package / name).read_bytes()
        source = (sources / name).read_bytes()
        if installed != source or sha(lf(installed)) != frozen:
            raise ValueError('Installed module bytes differ from source/Git identity: ' + name)
        rows[name] = {'executed_sha256': sha(installed), 'git_lf_sha256': frozen}
    for name in ('repair', 'work_effects', 'windows_effects', 'work_build', 'process', 'windows'):
        origin = Path(importlib.import_module('attune_harness.' + name).__file__).resolve()
        if origin != package / (name + '.py'):
            raise ValueError('Imported module origin differs from installed package: ' + name)
    return package, rows, sha(manifest.read_bytes())


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 'windows-effect-installed-journey-v1',
               'status': 'failed', 'python': platform.python_version(),
               'platform': platform.platform(), 'commit': os.environ.get('GITHUB_SHA'),
               'requested_runner': os.environ.get('ATTUNE_CI_WINDOWS_LABEL'),
               'provider_calls': 0, 'selected_tests': 'tests/test_windows_effects.py',
               'timeout_seconds': TEST_DEADLINE, 'max_log_bytes': MAX_LOG}
    try:
        package, modules, source_manifest_sha = installed_identity()
        receipt.update(installed_package=str(package), modules=modules,
                       source_manifest_sha256=source_manifest_sha)
        candidate = RECEIPT_DIR / 'backend-main-candidate-manifest.json'
        receipt['candidate_manifest_sha256'] = sha(candidate.read_bytes())
        frozen = json.loads(candidate.read_text())['paths']
        for relative, expected in frozen.items():
            if sha(lf((ROOT / relative).read_bytes())) != expected:
                raise ValueError('Candidate source/test evidence differs from frozen manifest: '
                                 + relative)
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
        if (code != 0 or stop is not None or receipt.get('counts') != {
            'tests': 10, 'failures': 0, 'errors': 0, 'skipped': 0}):
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
