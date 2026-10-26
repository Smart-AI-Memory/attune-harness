"""Supplemental coverage in a disposable venv; never a qualification replacement."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import runpy
import subprocess
import sys
import sysconfig
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/attune_harness'
VERSION = '7.13.5'
INPUT_TREES = ('tests', 'scripts', 'examples', 'experiments', 'docs',
               'plugin', '.agents', '.claude', '.github/workflows')
IGNORED_INPUT_DIRS = {'__pycache__', '.pytest_cache'}
ROOT_INPUTS = ('pyproject.toml', 'pytest.ini', '.pytest.ini', 'pytest.toml',
               '.pytest.toml', 'tox.ini', 'setup.cfg', 'setup.py', 'conftest.py',
               'MANIFEST.in', 'README.md', 'participants.json',
               'dependency-lock.json', '.github/workflows/coverage.yml')


def hashes(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*.py'))}


def _deadline_kwargs(deadline):
    if deadline is None:
        return {}
    if isinstance(deadline, bool) or not math.isfinite(deadline):
        raise ValueError('Installed-suite deadline must be a finite monotonic clock value')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Shared installed-suite identity deadline expired')
    return {'timeout': min(10, remaining)}


def input_hashes(*, deadline=None):
    """Bind tracked checkout bytes and untracked test/driver/fixture inputs."""
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--cached'], cwd=ROOT,
                                     **_deadline_kwargs(deadline))
    paths = {ROOT / os.fsdecode(name) for name in tracked.split(b'\0') if name}
    for name in INPUT_TREES:
        _deadline_kwargs(deadline)
        tree = ROOT / name
        if tree.is_symlink() or (tree.exists() and not tree.is_dir()):
            raise ValueError('Coverage input tree must be a real directory: ' + str(tree))
        if not tree.exists():
            continue
        for path in sorted(tree.rglob('*')):
            if any(part in IGNORED_INPUT_DIRS for part in path.relative_to(tree).parts):
                continue
            if path.is_symlink():
                raise ValueError('Coverage inputs cannot contain symlinks: ' + str(path))
            if path.is_file():
                paths.add(path)
    paths.update(path for path in (ROOT / name for name in ROOT_INPUTS)
                 if path.exists() or path.is_symlink())
    paths.update(ROOT.glob('requirements*.lock'))
    paths.update(ROOT.glob('requirements*.txt'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Coverage inputs cannot contain symlinks')
    result = {}
    for path in sorted(paths):
        _deadline_kwargs(deadline)
        result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def identity(*, deadline=None):
    return {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                                text=True, **_deadline_kwargs(deadline)).strip(),
            'sources': hashes(SOURCE), 'input_hashes': input_hashes() if deadline is None else input_hashes(deadline=deadline),
            'coverage_version': VERSION, 'pytest_version': importlib.metadata.version('pytest')}


def inputs_stable(frozen, installed):
    try:
        return identity() == frozen and hashes(installed) == frozen['sources']
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False


def compatible(receipts, expected):
    for receipt in receipts:
        if any(receipt.get(key) != value for key, value in expected.items()):
            raise ValueError('Coverage requires matching revision, source and executed input bytes, and tool versions')
        if receipt.get('test_exit') != 0 or receipt.get('input_drift') is not False:
            raise ValueError('Cannot combine a failed, unfinished or input-drifted test run')


def configuration(output, aliases):
    # Include both source and wheel at collection; combine maps identical wheel
    # bytes back to the checkout. No production module or branch is excluded.
    paths = [SOURCE.as_posix(), *dict.fromkeys(aliases)]
    config = output / 'coverage.ini'
    config.write_text('[run]\nbranch = true\nparallel = true\ndisable_warnings = no-data-collected\ndata_file = '
                      + (output / '.coverage').as_posix() + '\nsource =\n    '
                      + '\n    '.join(paths) + '\n[paths]\npackage =\n    '
                      + '\n    '.join(paths) + '\n', encoding='utf-8')
    return config


def startup_hook(config):
    # Runs even with -I or a replaced child environment. -S and forcibly killed
    # processes remain blind spots. Only installed in a dedicated measurement venv.
    code = ('import atexit, coverage\n'
            'if coverage.Coverage.current() is None:\n'
            f'    collector = coverage.Coverage(config_file={str(config)!r})\n'
            '    collector.start()\n'
            '    atexit.register(collector.save)\n')
    return f'import builtins; exec({code!r})\n'


def report(config, directories=None):
    import coverage
    collector = coverage.Coverage(config_file=str(config))
    collector.combine(data_paths=directories, strict=True, keep=True)
    collector.save()
    output = config.parent
    collector.json_report(outfile=str(output / 'coverage.json'))
    collector.html_report(directory=str(output / 'html'))
    totals = json.loads((output / 'coverage.json').read_text(encoding='utf-8'))['totals']
    summary = {'line_percent': 100 * totals['covered_lines'] / totals['num_statements'],
               'branch_percent': 100 * totals['covered_branches'] / totals['num_branches'],
               'covered_lines': totals['covered_lines'], 'statements': totals['num_statements'],
               'covered_branches': totals['covered_branches'], 'branches': totals['num_branches']}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))


def _validate_partition_junit(folder, selected):
    root = ET.parse(folder / 'tests.xml').getroot()
    suites, cases = list(root.iter('testsuite')), list(root.iter('testcase'))
    keys = ('tests', 'failures', 'errors', 'skipped')
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in keys}
    if (root.tag not in ('testsuites', 'testsuite') or not suites or not cases
            or len(cases) < len(selected)
            or any(int(s.get(key, 0)) < 0 for s in suites for key in keys)
            or counts['failures'] or counts['errors']
            or any(element.tag in ('failure', 'error') for element in root.iter())
            or counts['skipped'] != sum(c.find('skipped') is not None for c in cases)):
        raise ValueError('Partition JUnit does not retain successful selected cases')
    difference = counts['tests'] - len(cases)
    if difference:
        # Pytest 9 counts successful subtests without emitting testcase elements.
        transcript = (folder / 'stdout.txt').read_text(encoding='utf-8')
        summaries = re.findall(r'(?m)^.*\b(\d+) subtests passed.* in [0-9.]+s.*$', transcript)
        if difference < 0 or not summaries or difference != int(summaries[-1]):
            raise ValueError('Partition JUnit count lacks matching passing-subtest summary')


def _darwin_full(output, budget):
    """Share one deadline and retain live diagnostics in an already-uploaded directory."""
    deadline = time.monotonic() + budget
    spec = importlib.util.spec_from_file_location('coverage_source_suite', ROOT / 'scripts/run_source_suite.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # This entire directory is already included by coverage.yml, including
    # partial journals when an outer kill prevents Python finally blocks.
    partitions = output / 'instrumented-platform'
    code = runner.run_suite(partitions, budget, root=ROOT, shards=2, deadline=deadline)
    if code == 0:
        for index in range(2):
            folder = partitions / f'shard-{index}'
            selected = json.loads((folder / 'collection.json').read_text())['selected']
            _validate_partition_junit(folder, selected)
    return code


def _partitioned_full(suite):
    return suite == 'full' and platform.system() == 'Darwin'


def _validate_installed_aggregate(output, frozen):
    """Read back the completed parent's proof without extending its test deadline."""
    folder = output / 'instrumented-platform'
    receipt = json.loads((folder / 'installed-suite.json').read_text(encoding='utf-8'))
    raw = (folder / 'partition-context.json').read_bytes()
    context = json.loads(raw)
    context['context_sha256'] = hashlib.sha256(raw).hexdigest()
    qualifier = runpy.run_path(str(ROOT / 'scripts/qualify_platform.py'))
    qualifier['validate_installed_parent_receipt'](receipt, context, successful=True)
    if context['budget_seconds'] != 2520 or context['identity']['measurement'] != frozen:
        raise ValueError('Installed aggregate differs from the measurement budget or inputs')
    # Active verification already finished under the serialized shared deadline.
    # This is static proof readback after the parent's once-only postchecks.
    accounting = qualifier['verify_installed_partitions'](folder, context, None)
    if (accounting != receipt['accounting']
            or hashlib.sha256((folder / 'plugin-probe.json').read_bytes()).hexdigest()
            != accounting['plugin_probe_sha256']):
        raise ValueError('Installed aggregate or copied probe differs from child evidence')
    return accounting


def measure(output, suite):
    if sys.prefix == sys.base_prefix:
        raise ValueError('Use a dedicated disposable virtualenv')
    import attune_harness
    installed = Path(attune_harness.__file__).resolve().parent
    if installed == SOURCE or hashes(installed) != hashes(SOURCE):
        raise ValueError('Install a wheel with exactly the current source bytes')
    frozen = identity()
    hook = Path(sysconfig.get_path('purelib')) / 'harness_measure_coverage.pth'
    if hook.exists():
        raise ValueError('Measurement hook already exists; use a fresh virtualenv')
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / 'tmp'
    temporary.mkdir()
    config = configuration(output, [installed.as_posix()])
    receipt = {**frozen, 'system': platform.system(), 'python': platform.python_version(),
               'suite': suite, 'aliases': [SOURCE.as_posix(), installed.as_posix()],
               'test_exit': None, 'input_drift': True,
               'limits': ['no-site (-S) children', 'abrupt termination before save',
                          'instrumented run is not platform qualification']}
    manifest = output / 'manifest.json'
    def save():
        manifest.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    partitioned = _partitioned_full(suite)
    installed_partitions = suite == 'platform' and platform.system() == 'Windows'
    if partitioned:
        receipt['execution_topology'] = 'two_supervised_module_partitions'
        receipt['shared_test_budget_seconds'] = 1500
        receipt['partition_evidence'] = [f'instrumented-platform/shard-{index}' for index in range(2)]
        receipt['partition_supervisor'] = 'instrumented-platform/source-suite.json'
    if installed_partitions:
        receipt['execution_topology'] = 'two_supervised_installed_module_partitions'
        receipt['shared_test_budget_seconds'] = 2520
        receipt['partition_evidence'] = [f'instrumented-platform/shard-{index}' for index in range(2)]
        receipt['partition_supervisor'] = 'instrumented-platform/installed-suite.json'
    save()
    argv = ([sys.executable, '-m', 'pytest', '-q', '-p', 'harness_qualification_stacks',
             '-o', 'faulthandler_timeout=0', '--junitxml=' + str(output / 'tests.xml')]
            if suite == 'full' else
            [sys.executable, '-I', str(ROOT / 'scripts/qualify_platform.py'),
             '--output', str(output / 'instrumented-platform'), '--coverage-instrumented'])
    if installed_partitions:
        argv.append('--installed-coverage-partitions')
    environment = {**os.environ, 'TMPDIR': str(temporary), 'TMP': str(temporary),
                   'TEMP': str(temporary), 'PYTHONUTF8': '1'}
    if suite == 'full':
        # Retain the active case/phase even when the independent outer deadline
        # kills pytest before it writes JUnit. Reuse qualification's Python
        # watchdog; the native timed frame walker is deliberately disabled.
        environment['HARNESS_QUALIFICATION_OUTPUT'] = str(output)
        environment['PYTHONPATH'] = os.pathsep.join(filter(None, (
            str(ROOT / 'scripts'), environment.get('PYTHONPATH', ''))))
    stream = hook.open('x', encoding='utf-8')
    try:
        with stream:
            stream.write(startup_hook(config))
        with (output / 'tests.txt').open('w', encoding='utf-8') as log:
            if partitioned:
                log.write('Two supervised module partitions; see instrumented-platform/shard-* diagnostics.\n')
                log.flush()
                receipt['test_exit'] = _darwin_full(output, 1500)
            else:
                run = subprocess.run(argv, cwd=ROOT, env=environment, stdout=log,
                                     stderr=subprocess.STDOUT,
                                     timeout=(2700 if platform.system() == 'Windows' else 1080)
                                     if suite == 'platform' else
                                     (1500 if platform.system() == 'Darwin' else 1200))
                receipt['test_exit'] = run.returncode
    finally:
        hook.unlink(missing_ok=True)
        receipt['input_drift'] = not inputs_stable(frozen, installed)
        save()
    if (partitioned or installed_partitions) and (receipt['test_exit'] != 0 or receipt['input_drift']):
        return receipt['test_exit'] or 1
    if installed_partitions:
        try:
            receipt['partition_accounting'] = _validate_installed_aggregate(output, frozen)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            receipt.update(test_exit=1, aggregate_failure=type(error).__name__)
            save()
            return 1
        save()
    report(config)
    return 1 if receipt['input_drift'] else receipt['test_exit']


def combine(output, directories):
    receipts = [json.loads((p / 'manifest.json').read_text(encoding='utf-8')) for p in directories]
    expected = identity()
    compatible(receipts, expected)
    output.mkdir(parents=True, exist_ok=False)
    aliases = [path for receipt in receipts for path in receipt['aliases']]
    config = configuration(output, aliases)
    report(config, [str(p / '.coverage') for p in directories])
    (output / 'manifest.json').write_text(json.dumps({**expected, 'test_exit': 0,
        'input_drift': False, 'inputs': receipts}, indent=2) + '\n', encoding='utf-8')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--suite', choices=['full', 'platform'], default='full')
    parser.add_argument('--combine', type=Path, nargs='+')
    args = parser.parse_args()
    if importlib.metadata.version('coverage') != VERSION:
        raise ValueError('Install coverage==' + VERSION)
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Keep coverage evidence outside the measured checkout')
    return combine(output, args.combine) if args.combine else measure(output, args.suite)


if __name__ == '__main__':
    raise SystemExit(main())
