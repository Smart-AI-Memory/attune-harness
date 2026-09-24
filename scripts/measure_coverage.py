"""Supplemental coverage in a disposable venv; never a qualification replacement."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/attune_harness'
VERSION = '7.13.5'


def hashes(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*.py'))}


def identity():
    return {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                                text=True).strip(),
            'sources': hashes(SOURCE), 'coverage_version': VERSION}


def compatible(receipts, expected):
    for receipt in receipts:
        if any(receipt.get(key) != value for key, value in expected.items()):
            raise ValueError('Coverage requires matching revision, source bytes and collector version')
        if receipt.get('test_exit') != 0:
            raise ValueError('Cannot combine a failed or unfinished test run')


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


def measure(output, suite):
    if sys.prefix == sys.base_prefix:
        raise ValueError('Use a dedicated disposable virtualenv')
    import attune_harness
    installed = Path(attune_harness.__file__).resolve().parent
    if installed == SOURCE or hashes(installed) != hashes(SOURCE):
        raise ValueError('Install a wheel with exactly the current source bytes')
    hook = Path(sysconfig.get_path('purelib')) / 'harness_measure_coverage.pth'
    if hook.exists():
        raise ValueError('Measurement hook already exists; use a fresh virtualenv')
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / 'tmp'
    temporary.mkdir()
    config = configuration(output, [installed.as_posix()])
    receipt = {**identity(), 'system': platform.system(), 'python': platform.python_version(),
               'suite': suite, 'aliases': [SOURCE.as_posix(), installed.as_posix()],
               'test_exit': None,
               'limits': ['no-site (-S) children', 'abrupt termination before save',
                          'instrumented run is not platform qualification']}
    manifest = output / 'manifest.json'
    def save():
        manifest.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    save()
    argv = ([sys.executable, '-m', 'pytest', '-q', '--junitxml=' + str(output / 'tests.xml')]
            if suite == 'full' else
            [sys.executable, '-I', str(ROOT / 'scripts/qualify_platform.py'),
             '--output', str(output / 'instrumented-platform')])
    environment = {**os.environ, 'TMPDIR': str(temporary), 'TMP': str(temporary),
                   'TEMP': str(temporary), 'PYTHONUTF8': '1'}
    stream = hook.open('x', encoding='utf-8')
    try:
        with stream:
            stream.write(startup_hook(config))
        with (output / 'tests.txt').open('w', encoding='utf-8') as log:
            run = subprocess.run(argv, cwd=ROOT, env=environment, stdout=log,
                                 stderr=subprocess.STDOUT, timeout=900)
        receipt['test_exit'] = run.returncode
    finally:
        hook.unlink(missing_ok=True)
        save()
    report(config)
    return receipt['test_exit']


def combine(output, directories):
    receipts = [json.loads((p / 'manifest.json').read_text(encoding='utf-8')) for p in directories]
    expected = identity()
    compatible(receipts, expected)
    output.mkdir(parents=True, exist_ok=False)
    aliases = [path for receipt in receipts for path in receipt['aliases']]
    config = configuration(output, aliases)
    report(config, [str(p / '.coverage') for p in directories])
    (output / 'manifest.json').write_text(json.dumps({**expected, 'test_exit': 0,
        'inputs': receipts}, indent=2) + '\n', encoding='utf-8')
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
