"""Detect a removed Windows environment-forwarding guard in a disposable copy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('This guard check requires actual Windows')
    import attune_harness
    source = Path(attune_harness.__file__).resolve().parent
    root = Path(__file__).resolve().parents[2]
    if source == root / 'src/attune_harness':
        raise RuntimeError('Install the wheel before checking the native guard')
    expected = root / 'src/attune_harness/windows.py'
    assert (source / 'windows.py').read_bytes() == expected.read_bytes()
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='harness-env-mutation-') as temporary:
        copied = Path(temporary) / 'attune_harness'
        shutil.copytree(source, copied, ignore=shutil.ignore_patterns('__pycache__'))
        windows = copied / 'windows.py'
        before = windows.read_bytes()
        assert before.count(b'env=environment') == 1
        windows.write_bytes(before.replace(b'env=environment', b'env=None'))
        env = dict(os.environ, PYTHONPATH=str(copied.parent),
                   PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        env.pop('PYTEST_ADDOPTS', None)
        env.pop('PYTEST_PLUGINS', None)
        command = [sys.executable, '-B', '-m', 'pytest', '-q', '-o', 'pythonpath=',
                   '-p', 'no:cacheprovider', '--junitxml=' + str(output / 'negative.xml'),
                   str(root / 'tests/test_windows_runtime.py') +
                   '::test_windows_explicit_environment_reaches_target_exactly']
        run = subprocess.run(command, cwd=temporary, env=env, capture_output=True,
                             text=True, encoding='utf-8', timeout=30)
        (output / 'negative.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        suites = ET.parse(output / 'negative.xml').getroot().iter('testsuite')
        totals = {key: 0 for key in ('tests', 'failures', 'errors', 'skipped')}
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.get(key, '0'))
        detected = run.returncode == 1 and totals == dict(tests=1, failures=1, errors=0, skipped=0)
        receipt = {'schema': 'windows-environment-guard-removal-v1',
                   'python': sys.version, 'installed': str(source), 'command': command,
                   'original_sha256': hashlib.sha256(before).hexdigest(),
                   'mutated_sha256': hashlib.sha256(windows.read_bytes()).hexdigest(),
                   'exit': run.returncode, 'counts': totals, 'detected': detected,
                   'guard_removals_detected': int(detected), 'guard_removals_total': 1,
                   'provider_calls': 0, 'github_sha': os.environ.get('GITHUB_SHA')}
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipt, indent=2))
        if not detected:
            raise AssertionError('Removed environment forwarding was not detected by its behavioral check')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
