"""Run the revised E2 contract against the unchanged original cache and fixtures."""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OLD = ROOT / 'experiments/e2'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load('e2_revised_policy', HERE / 'policy.py')
original = load('e2_original_evaluator', OLD / 'evaluate.py')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(python, missing_python, output):
    protocol = read(HERE / 'protocol.json')
    for name, expected in read(ROOT / 'docs/receipts/e2-revision/freeze.json')['sha256'].items():
        assert sha(ROOT / name) == expected, 'Frozen protocol or original baseline changed'
    assert sha(ROOT / 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl') == protocol['baseline_wheel_sha256']
    output.mkdir()
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [*sorted(HERE.glob('*.py')), HERE / 'protocol.json',
               *sorted(OLD.glob('*.py')), OLD / 'protocol.json', ROOT / 'scripts/check_mcp_installed.py']}
    for name in sources:
        archived = output / 'sources' / name
        archived.parent.mkdir(parents=True, exist_ok=True)
        archived.write_bytes((ROOT / name).read_bytes())
    write(output / 'sources.json', sources)
    write(output / 'protocol.json', protocol)
    rows = []
    for adapter, condition, state in itertools.product(protocol['adapters'], protocol['conditions'], protocol['states']):
        cell = output / f'{len(rows):02}'
        cell.mkdir()
        row = {'cell': cell.name, 'adapter': adapter, 'condition': condition, 'state': state}
        write(cell / 'spec.json', row)
        chronology = []
        def command(label, runtime, script, arguments):
            result = subprocess.run([str(runtime), '-I', str(script), *map(str, arguments)],
                                    cwd=cell, capture_output=True, text=True, timeout=30)
            chronology.append({'action': label, 'python': str(runtime), 'script': str(script),
                'arguments': list(map(str, arguments)), 'returncode': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr, 'ended_ns': time.time_ns()})
            write(cell / 'chronology.json', chronology)
            assert result.returncode == 0, f'{label}: {result.stderr}'
        def worker(action, runtime=python, label=None, **kwargs):
            args = [action, '--cell', cell, '--adapter', adapter]
            for name, value in kwargs.items():
                args += ['--' + name.replace('_', '-'), value]
            command(label or action, runtime, OLD / 'worker.py', args)
        def revised(prefix, history, descriptor, runtime):
            directory = cell / (prefix + '-requested-run')
            decision = cell / (prefix + '-decision.json')
            command(prefix + '-plan', python, HERE / 'policy.py', ['plan', '--descriptor', descriptor,
                '--history', history, '--run-directory', directory, '--output', decision])
            chronology[-1]['output_sha256'] = sha(decision)
            write(cell / 'chronology.json', chronology)
            worker('describe', runtime, label=prefix + '-before', output=cell / (prefix + '-before.json'))
            plan = read(decision)
            # A changed plan cannot dispatch; production rechecks lifecycle and grants inside its call too.
            before = read(cell / (prefix + '-before.json'))
            raw_path = cell / (prefix + '-raw.json')
            if plan['invocation_allowed'] and plan['descriptor_digest'] == policy.fingerprint(before):
                worker('invoke', runtime, label=prefix + '-requested-invocation', run_dir=directory, output=raw_path)
            else:
                write(raw_path, {'target_result': None, 'target_dispatches': 0, 'not_invoked': True})
            worker('describe', runtime, label=prefix + '-after', output=cell / (prefix + '-after.json'))
            completion = cell / (prefix + '-completion.json')
            command(prefix + '-finish', python, HERE / 'policy.py', ['finish', '--descriptor', cell / (prefix + '-before.json'),
                '--decision', decision, '--after', cell / (prefix + '-after.json'), '--raw', raw_path, '--output', completion])
            chronology[-1]['output_sha256'] = sha(completion)
            write(cell / 'chronology.json', chronology)
            # Evaluation-only second call. The consumer uses the requested invocation's own result above.
            worker('invoke', runtime, label=prefix + '-oracle', run_dir=cell / (prefix + '-oracle-run'),
                   output=cell / (prefix + '-oracle.json'))
            return read(completion)
        try:
            worker('setup')
            worker('describe', output=cell / 'before.json')
            worker('invoke', run_dir=cell / 'qualification-run', output=cell / 'qualification.json')
            qualification = read(cell / 'qualification.json')
            assert original.usable(qualification, cell)
            write(cell / 'history.json', policy.observation(read(cell / 'before.json'), qualification['target_result']))
            worker('alter', state=state)
            runtime = missing_python if state == 'dependency-missing' else python
            worker('describe', runtime, output=cell / 'current.json')
            if condition == 'version-bound-cache':
                command('baseline-plan', python, OLD / 'policy.py', ['--condition', condition, '--descriptor', cell / 'current.json',
                    '--observation', cell / 'history.json', '--output', cell / 'decision.json'])
                chronology[-1]['output_sha256'] = sha(cell / 'decision.json')
                write(cell / 'chronology.json', chronology)
                worker('invoke', runtime, label='baseline-oracle', run_dir=cell / 'oracle-run', output=cell / 'oracle.json')
                row['oracle_usable'] = original.usable(read(cell / 'oracle.json'), cell)
            else:
                result = revised('current', cell / 'history.json', cell / 'current.json', runtime)
                row['oracle_usable'] = original.usable(read(cell / 'current-oracle.json'), cell)
                if state == 'working':
                    assert result['status'] == 'observed_success'
                    write(cell / 'recent-history.json', result['observation'])
                    worker('alter', state='advertised-but-broken')
                    worker('describe', output=cell / 'post-success.json')
                    assert read(cell / 'post-success.json') == read(cell / 'current.json')
                    revised('next', cell / 'recent-history.json', cell / 'post-success.json', runtime)
            assert row['oracle_usable'] is (state in ('working', 'upgraded')), 'Unexpected oracle outcome'
            row['evaluated'] = True
        except Exception as exc:
            row.update(evaluated=False, error={'type': type(exc).__name__, 'detail': str(exc)})
        write(cell / 'row.json', row)
        rows.append(row)
        print(f"{cell.name}: {adapter} / {condition} / {state}: {'evaluated' if row['evaluated'] else 'INFRASTRUCTURE FAILURE'}", flush=True)
    for name, expected in sources.items():
        assert sha(ROOT / name) == expected, 'Evaluator changed during run'
    write(output / 'rows.json', rows)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--missing-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = run(args.python.absolute(), args.missing_python.absolute(), args.output.resolve())
    if not all(row['evaluated'] for row in rows):
        raise SystemExit(1)
