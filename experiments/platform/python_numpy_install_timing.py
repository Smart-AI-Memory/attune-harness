"""Time an isolated published-package install and offline smoke checks.

This is an experiment, not platform qualification or a model-quality test.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

PACKAGE_VERSION = '1.5.1'
WHEEL_SHA256 = '1d61b8d337227a293516f42eac304e954fd44f10fd9fd0ec35d416a18661d6e9'
NUMPY_VERSION = '2.5.4'
LOCKS = ('workflow', 'voyage', 'mcp', 'tokens', 'redis')
ROOT = Path(__file__).resolve().parents[2]

IMPORTS = '''
import importlib.metadata as m, importlib.util, json, sys
import attune_harness, numpy, pyarrow, lancedb, redis, voyageai
assert importlib.util.find_spec('attune') is None
assert m.version('attune-harness') == '1.5.1'
assert numpy.__version__ == '2.5.4'
from pathlib import Path
assert Path(attune_harness.__file__).resolve().is_relative_to(Path(sys.prefix))
print(json.dumps({'python':sys.version.split()[0], 'package':m.version('attune-harness'),
 'numpy':numpy.__version__, 'pyarrow':pyarrow.__version__, 'lancedb':lancedb.__version__,
 'redis':redis.__version__, 'voyageai':m.version('voyageai'),
 'installed_package':attune_harness.__file__, 'attune_ai_absent':True}))
'''

ENCODING = '''
import json, sys
observation = {'stdout_encoding':sys.stdout.encoding}
try:
    'Aurora \\u96ea'.encode(sys.stdout.encoding)
except UnicodeError as error:
    observation.update(unicode_encodable=False, error_type=type(error).__name__)
else:
    observation['unicode_encodable'] = True
print(json.dumps(observation))
'''

SMOKE = '''
import json, sys
from pathlib import Path
import lancedb, numpy as np
from attune_harness.process import invoke
root = Path(sys.argv[1])
database = lancedb.connect(str(root / 'local-index'))
table = database.create_table('smoke', [
 {'id':'aurora','vector':np.array([1,0,0], dtype=np.float32).tolist()},
 {'id':'other','vector':np.array([0,1,0], dtype=np.float32).tolist()}])
assert table.search([1.,0.,0.]).limit(1).to_list()[0]['id'] == 'aurora'
directory = root / 'Child with spaces'; directory.mkdir()
result = invoke((sys.executable,'-I','-X','utf8','-c','print("Aurora \\u96ea")'), '',
                cwd=directory, timeout=10)
assert result.returncode == 0 and result.failure is None, result
assert result.stdout.strip() == 'Aurora \\u96ea', result
print(json.dumps({'local_vector_retrieval':'passed','owned_process_unicode':'passed',
                  'model_calls':0,'production_services':0}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'home').mkdir()
    (output / 'constraints').mkdir()
    (output / 'wheel').mkdir()
    # These are fresh experiment copies. Retained locks and environments stay intact.
    constraints = []
    for name in LOCKS:
        text = (ROOT / f'requirements-{name}.lock').read_text(encoding='utf-8')
        if name == 'voyage':
            if text.count('numpy==2.2.6') != 1:
                raise ValueError('Expected the unchanged baseline NumPy constraint')
            text = text.replace('numpy==2.2.6', f'numpy=={NUMPY_VERSION}')
        copied = output / 'constraints' / f'requirements-{name}.lock'
        copied.write_text(text, encoding='utf-8')
        constraints.extend(('-c', str(copied)))
    names = ('PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP',
             'SystemDrive', 'PATHEXT', 'PROCESSOR_ARCHITECTURE', 'LANG', 'LC_ALL')
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment.update(HOME=str(output / 'home'), USERPROFILE=str(output / 'home'),
                       PIP_CONFIG_FILE=os.devnull, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    receipt = dict(schema_version=1, status='running', system=platform.system(),
                   release=platform.release(), machine=platform.machine(),
                   controller_python=platform.python_version(), logical_cpus=os.cpu_count(),
                   image_os=os.environ.get('ImageOS'), image_version=os.environ.get('ImageVersion'),
                   driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   package_version=PACKAGE_VERSION, expected_wheel_sha256=WHEEL_SHA256,
                   numpy_version=NUMPY_VERSION, phases=[], model_calls=0,
                   limit='One cold install and smoke observation; no full-suite, durability or desktop qualification')
    started = time.perf_counter()

    def phase(name, command, *, timeout=180):
        before = time.perf_counter()
        log = output / f'{name}.txt'
        with log.open('wb') as stream:
            try:
                result = subprocess.run(command, cwd=output, env=environment, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=timeout)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
        receipt['phases'].append(dict(name=name, seconds=round(time.perf_counter()-before, 3),
                                      returncode=code, log=log.name))
        if code:
            raise RuntimeError(f'{name} failed with exit {code}; inspect {log.name}')
        return log

    try:
        phase('venv', [sys.executable, '-I', '-m', 'venv', str(output / 'venv')])
        scripts = output / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
        python = scripts / ('python.exe' if os.name == 'nt' else 'python')
        pip = [str(python), '-I', '-m', 'pip']
        options = ['--index-url', 'https://pypi.org/simple', '--no-cache-dir',
                   '--disable-pip-version-check', '--no-input', '--only-binary=:all:']
        phase('wheel_download', [*pip, 'download', *options, '--no-deps',
                                '--dest', str(output / 'wheel'), f'attune-harness=={PACKAGE_VERSION}'])
        wheel, = (output / 'wheel').glob('*.whl')
        observed = hashlib.sha256(wheel.read_bytes()).hexdigest()
        receipt['observed_wheel_sha256'] = observed
        if observed != WHEEL_SHA256:
            raise ValueError('Published wheel differs from the verified release hash')
        phase('dependency_install', [*pip, 'install', *options, *constraints,
                                    f'attune-harness[voyage,redis] @ {wheel.as_uri()}'])
        phase('pip_check', [*pip, 'check'])
        imports = phase('imports', [str(python), '-I', '-c', IMPORTS])
        receipt['runtime'] = json.loads(imports.read_text(encoding='utf-8'))
        encoding = phase('default_stdout_encoding', [str(python), '-I', '-c', ENCODING])
        receipt['default_stdout_encoding'] = json.loads(encoding.read_text(encoding='utf-8'))
        phase('cli_help', [str(python), '-I', '-m', 'attune_harness', '--help'])
        smoke = phase('offline_smoke', [str(python), '-I', '-c', SMOKE, str(output)], timeout=60)
        receipt['smoke'] = json.loads(smoke.read_text(encoding='utf-8'))
        receipt['status'] = 'passed'
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        receipt.update(status='failed', error=str(error))
        return 1
    finally:
        receipt['total_seconds'] = round(time.perf_counter()-started, 3)
        (output / 'result.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
