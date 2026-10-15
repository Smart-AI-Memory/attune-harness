"""Run the complete source suite with a deadline that preserves diagnostics."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def run_suite(output, timeout, *, root=ROOT):
    """Keep process failure distinct from pytest success; never retry a suite."""
    from attune_harness.process import invoke

    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError('Suite timeout must be in (0, 3600] seconds')
    output = Path(output).absolute()
    root = Path(root).absolute()
    output.mkdir(parents=True, exist_ok=False)
    argv = (sys.executable, '-u', '-m', 'pytest', '-v', '--durations=30',
            '--junitxml=' + str(output / 'tests.xml'),
            '-p', 'harness_qualification_stacks', '-o', 'faulthandler_timeout=0',
            '-o', 'tmp_path_retention_policy=failed')
    receipt = {
        'schema_version': 1, 'suite': 'full_source', 'status': 'running',
        'root': str(root), 'command': list(argv), 'timeout_seconds': timeout,
        'python': sys.version, 'system': platform.system(),
        'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'diagnostics': 'Python watchdog requires the GIL; process deadline is independent',
    }
    path = output / 'source-suite.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    environment = dict(os.environ)
    environment.update(PYTHONUTF8='1', HARNESS_QUALIFICATION_OUTPUT=str(output),
                       PYTHONPATH=str(SCRIPTS) + os.pathsep + str(root / 'src'))
    started = time.monotonic()
    try:
        revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                  capture_output=True, timeout=10, check=True)
        receipt['revision'] = revision.stdout.decode('ascii').strip()
        result = invoke(argv, '', cwd=root, timeout=timeout, max_output_bytes=64 * 1024 * 1024,
                        environment=environment, capture_interrupt=True)
        (output / 'stdout.txt').write_text(result.stdout, encoding='utf-8')
        (output / 'stderr.txt').write_text(result.stderr, encoding='utf-8')
        receipt.update(returncode=result.returncode, failure=result.failure)
        if result.failure == 'timeout_effects_unknown':
            code = 124
        elif result.failure == 'nonzero_exit':
            code = result.returncode if result.returncode not in (None, 0) else 2
        elif result.failure not in (None, 'nonzero_exit'):
            code = 2
        else:
            code = result.returncode if result.returncode is not None else 2
        receipt.update(exit=code, status='passed' if code == 0 else 'failed')
    except Exception as exc:
        code = 2
        receipt.update(exit=code, status='failed', error_type=type(exc).__name__,
                       error=str(exc))
    receipt['elapsed_seconds'] = round(time.monotonic() - started, 6)
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, required=True)
    args = parser.parse_args()
    return run_suite(args.output, args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
