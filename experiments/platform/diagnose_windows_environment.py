"""Retain bounded native Windows diagnostics even when pytest cannot finish."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    if os.name != 'nt':
        raise RuntimeError('This diagnostic requires a native Windows runner')
    import attune_harness
    root = Path(__file__).resolve().parents[2]
    output = root / 'windows-environment-diagnostic'
    output.mkdir(parents=True, exist_ok=False)
    installed = Path(attune_harness.__file__).resolve().parent
    receipt = {'installed': str(installed), 'model_calls': 0, 'sources': {}}
    for name in ('process.py', 'windows.py', '_windows_worker.py'):
        actual = (installed / name).read_bytes()
        if actual != (root / 'src' / 'attune_harness' / name).read_bytes():
            raise ValueError('Installed source differs: ' + name)
        receipt['sources'][name] = hashlib.sha256(actual).hexdigest()
    argv = [sys.executable, '-u', '-m', 'pytest', '-vv', '-o', 'pythonpath=',
            '-o', 'faulthandler_timeout=20',
            '--junitxml=' + str(output / 'tests.xml'),
            str(root / 'tests' / 'test_windows_runtime.py')]
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTEST_ADDOPTS', None)
    environment.pop('PYTEST_PLUGINS', None)
    environment['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    cwd = tempfile.mkdtemp(prefix='attune-win-diagnostic-')
    receipt['scratch_cwd'] = cwd
    with (output / 'tests.txt').open('wb') as log:
        try:
            run = subprocess.run(argv, cwd=cwd, env=environment, stdout=log,
                                 stderr=subprocess.STDOUT, timeout=180)
            receipt.update(exit=run.returncode, status='finished')
        except subprocess.TimeoutExpired:
            receipt.update(exit=124, status='timed_out')
    receipt['command'] = argv
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return receipt['exit']


if __name__ == '__main__':
    raise SystemExit(main())
