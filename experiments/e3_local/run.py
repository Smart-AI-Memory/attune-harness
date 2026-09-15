"""Execute the frozen 144-trial local-model campaign, retaining every failure."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def load_engine():
    spec = importlib.util.spec_from_file_location('e3_local_engine', HERE / 'engine.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    # The evaluator alone reads answer-key.json. This process only verifies its recorded hash.
    for name, expected in read(ROOT / 'docs/receipts/e3-local/freeze.json')['sha256'].items():
        assert sha(ROOT / name) == expected, 'Frozen input changed'
    protocol, tasks = read(HERE / 'protocol.json'), read(ROOT / 'experiments/e3/tasks.json')
    engine = load_engine()
    trials = [{'trial_id': f'{task["id"]}:{strategy}:{repeat}', 'task_id': task['id'],
               'task_revision': engine.digest(task), 'strategy': strategy, 'repeat': repeat, 'input': task}
              for task in tasks for strategy in protocol['strategies'] for repeat in range(protocol['repeats'])]
    random.Random(protocol['order_seed']).shuffle(trials)
    return protocol, trials


def run(python, output):
    import attune_harness
    protocol, trials = prepare()
    output.mkdir()
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [*sorted(HERE.glob('*.py')), HERE / 'protocol.json',
        ROOT / 'experiments/e3/tasks.json', ROOT / 'experiments/e3/answer-key.json',
        *sorted((ROOT / 'src/attune_harness').glob('*.py'))]}
    for name in sources:
        dest = output / 'sources' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
    write(output / 'sources.json', sources)
    write(output / 'protocol.json', protocol)
    write(output / 'plan.json', trials)
    package = Path(attune_harness.__file__).parent
    installed = {p.name: sha(p) for p in sorted(package.glob('*.py'))}
    assert installed == {p.name: sha(p) for p in sorted((ROOT / 'src/attune_harness').glob('*.py'))}, 'Installed package differs from source'
    write(output / 'installed.json', {'location': str(package), 'sources': installed})
    started, rows, calls = time.monotonic(), [], 0
    for index, trial in enumerate(trials):
        if time.monotonic() - started > protocol['max_campaign_seconds'] or calls >= protocol['max_campaign_calls']:
            raise RuntimeError('Campaign exhausted its frozen budget; keep partial results')
        trial_path = output / f'trial-{index:03}.json'
        write(trial_path, trial)
        directory = output / f'{index:03}'
        result = subprocess.run([str(python), '-I', str(HERE / 'run.py'), '--trial', str(trial_path),
            '--output', str(directory)], cwd=output, capture_output=True, text=True,
            timeout=protocol['max_calls_per_trial'] * (protocol['call_timeout_seconds'] + 20))
        write(output / f'process-{index:03}.json', {'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode or not (directory / 'record.json').exists():
            raise RuntimeError(f'Trial worker failed; preserve artifacts: {result.stderr}')
        record = read(directory / 'record.json')
        calls += len(record['calls'])
        rows.append({'directory': directory.name, 'trial_id': trial['trial_id'], 'status': record['status'], 'calls': len(record['calls'])})
        write(output / 'progress.json', {'trials': len(rows), 'calls': calls, 'rows': rows})
        print(f'{index + 1}/144 {trial["trial_id"]}: {record["status"]}, {len(record["calls"])} calls', flush=True)
        if record['uncertain_generation']:
            raise RuntimeError('Generation state is uncertain; no further calls or automatic retry')
    assert all(sha(ROOT / name) == expected for name, expected in sources.items()), 'Sources changed during campaign'
    write(output / 'execution-summary.json', {'trials': len(rows), 'calls': calls, 'paid_api_cost_usd': 0,
         'elapsed_seconds': time.monotonic() - started, 'status': 'execution_complete', 'rows': rows})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--trial', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.trial:
        load_engine().execute(read(args.trial), args.output.resolve(), read(HERE / 'protocol.json'))
    else:
        if args.python is None:
            parser.error('--python required for campaign')
        run(args.python.absolute(), args.output.resolve())
