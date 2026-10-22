"""Run the complete source suite with a deadline that preserves diagnostics."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from threading import Event

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def _run_suite(output, timeout, *, root=ROOT, shard=None, cancel=None, temporary_root=None):
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
    if shard is not None:
        argv += ('--harness-shard-index=' + str(shard), '--harness-shard-count=2',
                 '--basetemp=' + str(temporary_root / 'pytest'))
    receipt = {
        'schema_version': 1, 'suite': 'full_source', 'status': 'running',
        'root': str(root), 'command': list(argv), 'timeout_seconds': timeout,
        'python': sys.version, 'system': platform.system(),
        'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'diagnostics': 'Python watchdog requires the GIL; process deadline is independent',
    }
    if shard is not None:
        receipt['shard'] = {'index': shard, 'count': 2}
        receipt['temporary_root'] = str(temporary_root)
    path = output / 'source-suite.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    environment = dict(os.environ)
    environment.update(PYTHONUTF8='1', HARNESS_QUALIFICATION_OUTPUT=str(output),
                       PYTHONPATH=str(SCRIPTS) + os.pathsep + str(root / 'src'))
    if temporary_root is not None:
        # Native readers refuse directory churn while admitting a path. Keep
        # shard fixtures and nested process scratch in separate namespaces;
        # nested pytest cannot clean a peer's fixtures. Retain roots for
        # failure inspection on the runner.
        environment.update({name: str(temporary_root) for name in
                            ('TMP', 'TEMP', 'TMPDIR', 'PYTEST_DEBUG_TEMPROOT', 'RUNNER_TEMP')})
    started = time.monotonic()
    try:
        revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                  capture_output=True, timeout=10, check=True)
        receipt['revision'] = revision.stdout.decode('ascii').strip()
        result = invoke(argv, '', cwd=root, timeout=timeout, max_output_bytes=64 * 1024 * 1024,
                        environment=environment, capture_interrupt=True, cancel=cancel)
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
    if shard is None:
        print(json.dumps(receipt, indent=2))
    return code


def verify_partitions(output, revision):
    """Refuse missing, repeated or mismatched cases even when both exits are zero."""
    collected = None
    covered = []
    for index in range(2):
        folder = output / f'shard-{index}'
        receipt = json.loads((folder / 'source-suite.json').read_text(encoding='utf-8'))
        manifest = json.loads((folder / 'collection.json').read_text(encoding='utf-8'))
        if (receipt.get('status') != 'passed' or receipt.get('exit') != 0
                or receipt.get('returncode') != 0 or receipt.get('failure') is not None
                or receipt.get('revision') != revision
                or receipt.get('shard') != {'index': index, 'count': 2}
                or manifest.get('shard') != {'index': index, 'count': 2}
                or manifest.get('schema_version') != 1):
            raise ValueError('Shard identity or successful process evidence differs')
        all_cases, selected = manifest['collected'], manifest['selected']
        if (not isinstance(all_cases, list) or not all_cases
                or not all(isinstance(node, str) and node for node in all_cases)
                or len(set(all_cases)) != len(all_cases)):
            raise ValueError('Full collection must contain distinct test identities')
        if collected is not None and set(all_cases) != set(collected):
            raise ValueError('Shard full collections differ')
        collected = all_cases
        expected = [node for node in all_cases if
                    hashlib.sha256(node.split('::', 1)[0].encode('utf-8')).digest()[0] % 2 == index]
        if not selected or selected != expected:
            raise ValueError('Selected cases do not match the module partition')
        events = [json.loads(row) for row in
                  (folder / 'test-timings.jsonl').read_text(encoding='utf-8').splitlines()]
        starts = [row['nodeid'] for row in events if row['event'] == 'case_start']
        ends = [row['nodeid'] for row in events if row['event'] == 'case_end']
        if (Counter(starts) != Counter(selected) or Counter(ends) != Counter(selected)
                or not events or events[-1].get('event') != 'suite_end'
                or events[-1].get('exit_status') != 0):
            raise ValueError('Case journal does not prove every selected test finished once')
        covered.extend(selected)
    if Counter(covered) != Counter(collected):
        raise ValueError('Partitions do not cover the full collection exactly once')
    return {'collected_cases': len(collected), 'executed_cases': len(covered)}


def run_suite(output, timeout, *, root=ROOT, shards=1):
    """Keep the serial default; verify two concurrent supervised partitions on request."""
    if type(shards) is not int or shards not in (1, 2):
        raise ValueError('Source suite supports one or two shards')
    if shards == 1:
        return _run_suite(output, timeout, root=root)
    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError('Suite timeout must be in (0, 3600] seconds')
    output, root = Path(output).absolute(), Path(root).absolute()
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'schema_version': 1, 'suite': 'full_source', 'status': 'running',
               'root': str(root), 'timeout_seconds': timeout, 'shard_count': 2,
               'python': sys.version, 'system': platform.system(),
               'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path = output / 'source-suite.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    started, cancel = time.monotonic(), Event()
    try:
        revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                  capture_output=True, timeout=10, check=True)
        receipt['revision'] = revision.stdout.decode('ascii').strip()
        # Preserve the native temporary filesystem and inherited permissions.
        # Hosted RUNNER_TEMP can have different ACLs from the system temp.
        temporary_base = Path(tempfile.gettempdir()).resolve()
        if temporary_base.is_relative_to(root):
            raise ValueError('Partition temporary roots must be outside the source checkout')
        temporary_roots = [Path(tempfile.mkdtemp(prefix=f'harness-source-shard-{index}-',
                                               dir=temporary_base)).resolve()
                           for index in range(2)]
        receipt['temporary_roots'] = [str(folder) for folder in temporary_roots]
        with ThreadPoolExecutor(max_workers=2) as workers:
            try:
                futures = [workers.submit(_run_suite, output / f'shard-{index}', timeout,
                                          root=root, shard=index, cancel=cancel,
                                          temporary_root=temporary_roots[index]) for index in range(2)]
                codes = [future.result() for future in futures]
            except BaseException:
                cancel.set()
                raise
        receipt['shard_exits'] = codes
        code = 124 if 124 in codes else next((value for value in codes if value), 0)
        if code == 0:
            receipt['coverage'] = verify_partitions(output, receipt['revision'])
    except (Exception, KeyboardInterrupt) as exc:
        code = 2
        receipt.update(error_type=type(exc).__name__, error=str(exc))
    receipt.update(exit=code, status='passed' if code == 0 else 'failed',
                   elapsed_seconds=round(time.monotonic() - started, 6))
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('--shards', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    return run_suite(args.output, args.timeout, shards=args.shards)


if __name__ == '__main__':
    raise SystemExit(main())
