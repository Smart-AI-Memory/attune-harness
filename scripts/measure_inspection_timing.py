"""Measure installed local inspection paths against disposable, pinned inputs.

Run with a noneditable baseline wheel installed in a disposable environment:
  python -I -B measure_inspection_timing.py --baseline /absolute/clean/clone \
      --revision FULL_SHA --wheel /absolute/baseline.whl \
      --forms-wheel /absolute/attune_forms.whl --output /new/private/run

Only disposable fixture tests execute; no provider calls, cache eviction,
cleanup or production edits are used.
The output directory is exclusive and retained, including failed runs.
Use a new environment installed with --no-compile; existing package caches are
refused, never removed. Isolated Python ignores PYTHONHASHSEED, so hash
randomization and operating-system caches remain uncontrolled.
"""

import argparse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from email.parser import BytesParser
import functools
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run(argv, *, cwd=None, env=None):
    return subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                          capture_output=True, check=True)


def git(root, *args):
    return run(['git', '--no-optional-locks', '-c', 'diff.autoRefreshIndex=false',
                '-C', root, *args]).stdout


def identity(root):
    """Independent byte/mode/index guard; reads never refresh the Git index."""
    names = git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z')
    files = {}
    for name in sorted(set(os.fsdecode(p) for p in names.split(b'\0') if p)):
        path = root / name
        if path.is_symlink():
            raise ValueError('Fixture contains a symlink: ' + name)
        files[name] = ([sha(path), path.stat().st_size, path.stat().st_mode & 0o777]
                       if path.exists() else None)
    return {'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
            'tree': git(root, 'rev-parse', 'HEAD^{tree}').decode().strip(),
            'files': files, 'files_digest': digest(files),
            'index_bytes_sha256': sha(root / '.git' / 'index'),
            'index_entries_sha256': hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest(),
            'status_hex': git(root, 'status', '--porcelain=v1', '-z').hex()}


def tree_identity(root):
    """Saved evidence guard, including names, bytes and permission modes."""
    return {p.relative_to(root).as_posix(): [sha(p), p.stat().st_mode & 0o777]
            for p in sorted(root.rglob('*')) if p.is_file()}


def dependencies():
    return dict(sorted((d.metadata['Name'], d.version)
                       for d in importlib.metadata.distributions()))


def require_fresh_process():
    """Refuse an interpreter that may already have executed unverified code."""
    if (not sys.flags.isolated or not sys.dont_write_bytecode or sys.flags.optimize
            or sys.pycache_prefix is not None):
        raise ValueError('Use a fresh interpreter with -I -B, without -O or a pycache prefix')
    if any(name == package or name.startswith(package + '.')
           for name in sys.modules for package in ('attune_harness', 'attune_forms')):
        raise ValueError('Measured packages must not be loaded before preflight')


def validate_output(baseline, output):
    """Keep all output writes outside the immutable standalone checkout."""
    if output == baseline or baseline in output.parents or output in baseline.parents:
        raise ValueError('Output must be outside the immutable baseline and its Git storage')
    environment = {name: value for name, value in os.environ.items() if not name.startswith('GIT_')}
    local_names = run(['git', 'rev-parse', '--local-env-vars'], env=environment).stdout.decode().splitlines()
    if set(local_names).intersection(os.environ):
        raise ValueError('Run without Git repository environment overrides before validating the baseline')
    marker = baseline / '.git'
    if marker.is_symlink() or not marker.is_dir():
        raise ValueError('Baseline must be a standalone checkout with its own .git directory')
    directory = Path(os.fsdecode(git(baseline, 'rev-parse', '--absolute-git-dir')).strip()).resolve()
    common = Path(os.fsdecode(git(baseline, 'rev-parse', '--git-common-dir')).strip())
    if not common.is_absolute():
        common = baseline / common
    top = Path(os.fsdecode(git(baseline, 'rev-parse', '--show-toplevel')).strip()).resolve()
    if directory != marker.resolve() or common.resolve() != directory or top != baseline:
        raise ValueError('Baseline must be a standalone checkout without separate Git storage')
    if any(path.is_symlink() for path in marker.rglob('*')):
        raise ValueError('Baseline Git storage must not contain symlinks')
    alternates = marker / 'objects/info/alternates'
    if alternates.exists() and alternates.read_bytes().strip():
        raise ValueError('Baseline must not borrow alternate Git object storage')


def artifact_identity(package_name, wheel_path):
    """Check distribution-owned payload bytes and caches before any package import."""
    name = package_name.replace('_', '-')
    distribution = importlib.metadata.distribution(name)
    direct = json.loads(distribution.read_text('direct_url.json') or '{}')
    if direct.get('dir_info', {}).get('editable') or not distribution.read_text('WHEEL'):
        raise ValueError(f'Install the pinned {name} wheel, not an editable source tree')
    package = Path(distribution.locate_file(package_name))
    if package.is_symlink() or not package.is_dir():
        raise ValueError(f'Installed {name} package must be a regular directory')
    package = package.resolve()
    wheel_bytes = Path(wheel_path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as wheel:
        metadata = [n for n in wheel.namelist() if n.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError(f'{name} wheel must contain one distribution metadata record')
        if metadata[0].removesuffix('METADATA') + 'WHEEL' not in wheel.namelist():
            raise ValueError(f'{name} artifact lacks wheel metadata')
        headers = BytesParser().parsebytes(wheel.read(metadata[0]), headersonly=True)
        if (headers.get('Name', '').lower().replace('_', '-') != name
                or headers.get('Version') != distribution.version):
            raise ValueError(f'{name} wheel metadata differs from the installed distribution')
        expected = {}
        prefix = package_name + '/'
        for member in wheel.namelist():
            if not member.startswith(prefix) or member.endswith('/'):
                continue
            relative = member.removeprefix(prefix)
            parts = relative.split('/')
            if any(p in ('', '.', '..') for p in parts) or '\\' in relative or relative in expected:
                raise ValueError(f'{name} wheel contains an ambiguous package path')
            if '__pycache__' in parts or Path(relative).suffix.lower() in ('.pyc', '.pyo'):
                raise ValueError(f'{name} bytecode caches are refused; use a new --no-compile environment')
            expected[relative] = hashlib.sha256(wheel.read(member)).hexdigest()
    installed = {}
    for path in sorted(package.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'{name} package contains a symlink')
        relative = path.relative_to(package)
        if '__pycache__' in relative.parts or path.suffix.lower() in ('.pyc', '.pyo'):
            raise ValueError(f'{name} bytecode caches are refused; use a new --no-compile environment')
        if path.is_file():
            installed[relative.as_posix()] = sha(path)
    if '__init__.py' not in expected or expected != installed:
        raise ValueError(f'{name} wheel and installed package files must agree')
    return {'version': distribution.version, 'installed_package': str(package), 'files': installed,
            'wheel_sha256': hashlib.sha256(wheel_bytes).hexdigest()}


def bind_import(identity, package_name):
    """Bind executed imports to the package whose payload was just verified."""
    package = Path(identity['installed_package'])
    if package_name not in sys.modules:
        spec = importlib.util.find_spec(package_name)
        if (spec is None or not spec.origin
                or Path(spec.origin).resolve() != package / '__init__.py'
                or [Path(path).resolve() for path in (spec.submodule_search_locations or ())] != [package]):
            raise ValueError(f'Imported {package_name.replace("_", "-")} origin differs from the installed artifact')
    module = importlib.import_module(package_name)
    origin = getattr(module, '__file__', None)
    paths = getattr(module, '__path__', ())
    if (not origin or Path(origin).is_symlink()
            or Path(origin).resolve() != package / '__init__.py'
            or [Path(path).resolve() for path in paths] != [package]):
        raise ValueError(f'Imported {package_name.replace("_", "-")} origin differs from the installed artifact')
    return {**identity, 'imported_origin': str(Path(origin).resolve())}


def forms_identity(wheel_path):
    return bind_import(artifact_identity('attune_forms', wheel_path), 'attune_forms')


def harness_identity(wheel_path):
    return bind_import(artifact_identity('attune_harness', wheel_path), 'attune_harness')


def identities(harness_wheel, forms_wheel, source_hashes):
    """Validate both payloads before either import, including Harness source equality."""
    harness = artifact_identity('attune_harness', harness_wheel)
    forms = artifact_identity('attune_forms', forms_wheel)
    installed_sources = {name: value for name, value in harness['files'].items() if name.endswith('.py')}
    if not source_hashes or '__init__.py' not in source_hashes or source_hashes != installed_sources:
        raise ValueError('Imported attune-harness package differs from baseline source')
    return bind_import(harness, 'attune_harness'), bind_import(forms, 'attune_forms')


def verify_identities(config):
    harness, forms = identities(config['harness_wheel'], config['forms_wheel'], config['harness_sources'])
    if digest(harness) != config['harness_identity_digest']:
        raise ValueError('Worker attune-harness identity differs from preflight')
    if digest(forms) != config['forms_identity_digest']:
        raise ValueError('Worker attune-forms identity differs from preflight')
    return harness, forms


def retain_wheel(source, output, expected_sha256, package_name):
    directory = output / 'artifacts'
    if package_name == 'attune_harness':
        directory /= package_name
    retained = directory / Path(source).name
    retained.parent.mkdir(parents=True, exist_ok=True)
    retained.write_bytes(Path(source).read_bytes())
    if sha(retained) != expected_sha256:
        raise ValueError(f'{package_name.replace("_", "-")} wheel changed while retaining the artifact')
    return retained


def retain_forms_wheel(source, output, expected_sha256):
    return retain_wheel(source, output, expected_sha256, 'attune_forms')


def pair_schedule(repetitions, seed):
    """Keep the first pair separate from a seeded, counterbalanced warm schedule."""
    randomizer = random.Random(seed)
    warm = [False, True] * (repetitions // 2)
    if repetitions % 2:
        warm.append(bool(randomizer.getrandbits(1)))
    randomizer.shuffle(warm)
    first = [False, True]
    random.Random(f'{seed}:process-first').shuffle(first)
    return [first] + [[measured, not measured] for measured in warm]


def load_targets():
    import attune_forms
    from attune_harness import (human_output, review_contract, review_store,
                               task_contract, task_policies, test_change,
                               test_execution, test_scope)
    return [test_scope, test_change, test_execution, review_store, task_contract,
            task_policies, review_contract, human_output, attune_forms]


@contextmanager
def instrument(modules):
    """Patch loaded function aliases only; nested rows are inclusive and self."""
    names = {
        'test_scope': ('git', 'file_hash', 'capture', 'fresh', 'select'),
        'test_change': ('validate_test_task', 'check_test_fresh',
                        'present_test_task', 'public_test_task', 'create_test_task'),
        'test_execution': ('validate_artifacts',),
        'review_store': ('read_record', 'checkpoint_digest'),
        'task_contract': ('read_task',),
        'task_policies': ('inspect_task',),
        'review_contract': ('digest',),
        'human_output': ('markdown', 'document'),
        'attune_forms': ('workspace_from_dict', 'workspace_to_markdown'),
    }
    originals, replacements, stack = {}, {}, []
    totals = defaultdict(lambda: {'calls': 0, 'inclusive_ns': 0, 'self_ns': 0})
    for module in modules:
        for name in names.get(module.__name__.split('.')[-1], ()):
            function = getattr(module, name, None)
            if function is None:
                raise ValueError(f'Baseline lacks instrumentation target {module.__name__}.{name}')
            originals[function] = module.__name__ + '.' + name

    def wrap(function, label):
        @functools.wraps(function)
        def measured(*args, **kwargs):
            frame = [0]
            stack.append(frame)
            started = time.perf_counter_ns()
            try:
                return function(*args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - started
                stack.pop()
                entry = totals[label]
                entry['calls'] += 1
                entry['inclusive_ns'] += elapsed
                entry['self_ns'] += elapsed - frame[0]
                if stack:
                    stack[-1][0] += elapsed
        return measured

    replacements = {fn: wrap(fn, label) for fn, label in originals.items()}
    patches = []
    for module in list(sys.modules.values()):
        name = getattr(module, '__name__', '')
        if not (name.startswith('attune_harness.') or name == 'attune_forms'):
            continue
        for name, value in list(vars(module).items()):
            if callable(value) and id(value) in {id(f) for f in replacements}:
                patches.append((module, name, value))
                setattr(module, name, replacements[value])
    try:
        yield totals
    finally:
        for module, name, value in patches:
            setattr(module, name, value)


def worker(config):
    """One process-first pair followed by warm pairs; setup is outside timers."""
    require_fresh_process()
    verify_identities(config)
    load_targets()
    from attune_harness import test_change, test_scope, task_contract, task_policies
    from attune_harness import review_store
    import attune_forms
    root, task = Path(config['root']), Path(config['task'])
    # This read validates the checkpoint but does not capture/freshen the repo.
    if config['operation'].endswith('-completed'):
        task = Path(config['completed_task'])
    record = review_store.read_record(task)
    snapshot = record['request']['snapshot']
    definition = json.loads(Path(config['definition']).read_text())
    op = config['operation'].removesuffix('-completed')
    rows = []
    for repeat, order in enumerate(pair_schedule(config['repetitions'], config['seed'])):
        for position, measured in enumerate(order):
            directory = Path(config['new_tasks']) / f'{config["operation"]}-{repeat}-{int(measured)}'

            def invoke():
                if op == 'capture':
                    value = test_scope.capture(root)
                    assert value == snapshot
                elif op == 'fresh':
                    assert test_scope.fresh(snapshot)
                elif op == 'validate':
                    assert task_contract.read_task(task)['checkpoint_digest'] == record['checkpoint_digest']
                elif op == 'status':
                    value = task_policies.inspect_task(task)
                    assert value['presentation']['current_result']['outcome'] != 'blocked'
                elif op == 'render':
                    view = attune_forms.workspace_from_dict(definition)
                    assert attune_forms.workspace_to_markdown(view)
                elif op == 'preview':
                    value = test_change.create_test_task(
                        root, directory, scope=[config['scope']],
                        interpreter=sys.executable, tests=[config['test']])
                    value = test_change.present_test_task(value)
                    assert test_change.public_test_task(value)['status'] == 'draft'
                else:
                    raise ValueError(op)

            if measured:
                with instrument(load_targets()) as components:
                    started = time.perf_counter_ns()
                    invoke()
                    elapsed = time.perf_counter_ns() - started
            else:
                components = {}
                started = time.perf_counter_ns()
                invoke()
                elapsed = time.perf_counter_ns() - started
            rows.append({'repeat': repeat, 'condition': 'process_first_pair' if repeat == 0 else 'warm',
                         'order': position, 'instrumented': measured,
                         'elapsed_ns': elapsed, 'components': dict(components)})
    verify_identities(config)
    print(json.dumps(rows))


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        key = (row['fixture'], row['operation'], row['boundary'], row['condition'],
               row.get('instrumented', False))
        groups[key].append(row['elapsed_ns'] / 1e6)
    result = []
    for key, values in sorted(groups.items()):
        ordered = sorted(values)
        result.append(dict(zip(('fixture', 'operation', 'boundary', 'condition', 'instrumented'), key),
                           n=len(values), min_ms=min(values), median_ms=statistics.median(values),
                           mean_ms=statistics.mean(values), stdev_ms=statistics.stdev(values) if len(values)>1 else None,
                           p95_ms=ordered[math.ceil(.95 * len(values))-1], max_ms=max(values)))
    return result


def prepare(root, baseline, kind):
    if kind == 'repository':
        run(['git', 'clone', '--no-hardlinks', baseline, root])
        git(root, 'checkout', '--detach', git(baseline, 'rev-parse', 'HEAD').decode().strip())
        scope, test = 'README.md', 'tests/test_contract.py'
    else:
        root.mkdir()
        git(root, 'init', '-q')
        (root / 'src').mkdir()
        (root / 'tests').mkdir()
        (root / '.gitignore').write_text('__pycache__/\n.pytest_cache/\n')
        (root / 'src' / 'sample.py').write_text('VALUE = 1\n')
        (root / 'tests' / 'test_sample.py').write_text('def test_value():\n    assert 1 + 1 == 2\n')
        count = 8 if kind == 'small' else 512
        (root / 'data').mkdir()
        for i in range(count):
            (root / 'data' / f'{i:04d}.txt').write_text(f'{i:04d}\n' + 'a' * 4091)
        git(root, 'add', '.')
        environment = {**os.environ, 'GIT_AUTHOR_NAME': 'Measurement Fixture',
                       'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                       'GIT_COMMITTER_NAME': 'Measurement Fixture',
                       'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
                       'GIT_AUTHOR_DATE': '2000-01-01T00:00:00Z',
                       'GIT_COMMITTER_DATE': '2000-01-01T00:00:00Z'}
        run(['git', '-C', root, '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Pinned fixture'], env=environment)
        scope, test = 'src/sample.py', 'tests/test_sample.py'
    with (root / scope).open('a') as stream:
        stream.write('\n# Disposable measurement change\n')
    return scope, test


def measure(args):
    baseline, output = args.baseline.resolve(strict=True), args.output.resolve()
    validate_output(baseline, output)
    require_fresh_process()
    revision = git(baseline, 'rev-parse', 'HEAD').decode().strip()
    if revision != args.revision or git(baseline, 'status', '--porcelain=v1'):
        raise ValueError('Baseline must be clean and exactly match --revision')
    source = baseline / 'src/attune_harness'
    source_hashes = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*.py')}
    harness_before, forms_before = identities(args.wheel, args.forms_wheel, source_hashes)
    installed = Path(harness_before['installed_package'])
    installed_hashes = {name: value for name, value in harness_before['files'].items() if name.endswith('.py')}
    baseline_before = identity(baseline)
    output.mkdir(parents=True, exist_ok=False)
    forms_wheel = retain_forms_wheel(args.forms_wheel, output, forms_before['wheel_sha256'])
    harness_wheel = retain_wheel(args.wheel, output, harness_before['wheel_sha256'], 'attune_harness')
    for name in ('fixtures', 'tasks', 'new-tasks', 'commands'):
        (output / name).mkdir()
    env = {k: v for k, v in os.environ.items()
           if k not in ('PYTHONPATH', 'PYTHONHOME') and not k.startswith('GIT_')}
    env.update(PYTHONDONTWRITEBYTECODE='1',
               PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', ATTUNE_USAGE_PING='0', ATTUNE_VERSION_CHECK='0')
    os.environ.update({k: env[k] for k in ('PYTHONDONTWRITEBYTECODE',
                                         'PYTEST_DISABLE_PLUGIN_AUTOLOAD')})
    meta = {'schema_version': 1, 'started_utc': datetime.now(timezone.utc).isoformat(),
            'revision': revision, 'baseline': str(baseline), 'baseline_before': baseline_before,
            'wheel': str(args.wheel.resolve()), 'wheel_sha256': harness_before['wheel_sha256'],
            'harness_wheel': str(harness_wheel), 'harness_before': harness_before,
            'interpreter_flags': ['-I', '-B'], 'python_hash_seed': 'uncontrolled: isolated interpreter',
            'script_sha256': sha(__file__), 'platform': platform.platform(),
            'machine': platform.machine(), 'processor': platform.processor(),
            'cpu_count': os.cpu_count(), 'python': sys.version, 'executable': sys.executable,
            'interpreter_sha256': sha(Path(sys.executable).resolve()), 'installed': str(installed),
            'installed_sources': installed_hashes, 'dependencies': dependencies(),
            'forms_wheel': str(forms_wheel), 'forms_before': forms_before,
            'pair_schedule': pair_schedule(args.repetitions, args.seed),
            'repetitions': args.repetitions, 'cold_repetitions': args.cold_repetitions,
            'seed': args.seed, 'argv': sys.argv, 'fixtures': {}}
    (output / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    from attune_harness.test_change import (accept_test_task, create_test_task,
                                           execute_test_task, present_test_task)
    rows = []
    randomizer = random.Random(args.seed)
    for kind in ('small', 'medium', 'repository'):
        root = output / 'fixtures' / kind
        scope, test = prepare(root, baseline, kind)
        before = identity(root)
        task = output / 'tasks' / kind
        record = create_test_task(root, task, scope=[scope], interpreter=sys.executable, tests=[test])
        completed_task = output / 'tasks' / (kind + '-completed')
        completed = create_test_task(root, completed_task, scope=[scope],
                                     interpreter=sys.executable, tests=[test])
        accept_test_task(completed_task, completed['checkpoint_digest'])
        completed = execute_test_task(completed_task)
        if completed['presentation']['current_result']['outcome'] != 'passed':
            raise ValueError('Fixture test setup did not pass: ' + kind)
        definition = output / 'tasks' / f'{kind}-definition.json'
        definition.write_text(json.dumps(present_test_task(record)['presentation']['definition']))
        guard = tree_identity(task)
        completed_guard = tree_identity(completed_task)
        files = [v for v in before['files'].values() if v is not None]
        meta['fixtures'][kind] = {'before': before, 'files': len(files),
                                  'bytes': sum(v[1] for v in files), 'scope': scope, 'test': test,
                                  'task_before': guard, 'task_bytes': sum(p.stat().st_size for p in task.iterdir()),
                                  'completed_before': completed_guard,
                                  'completed_result': completed['presentation']['current_result'],
                                  'task_definition_sha256': sha(definition)}
        operations = ['capture', 'fresh', 'validate', 'validate-completed',
                      'status', 'status-completed', 'render', 'preview']
        randomizer.shuffle(operations)
        for operation in operations:
            config = {'root': str(root), 'task': str(task), 'definition': str(definition),
                      'completed_task': str(completed_task),
                      'operation': operation, 'scope': scope, 'test': test,
                      'repetitions': args.repetitions, 'seed': args.seed,
                      'forms_wheel': str(forms_wheel),
                      'harness_wheel': str(harness_wheel), 'harness_sources': source_hashes,
                      'harness_identity_digest': digest(harness_before),
                      'forms_identity_digest': digest(forms_before),
                      'new_tasks': str(output / 'new-tasks' / kind)}
            Path(config['new_tasks']).mkdir(exist_ok=True)
            values = json.loads(run([sys.executable, '-I', '-B', __file__, '--worker', json.dumps(config)],
                                    cwd=output, env=env).stdout)
            for row in values:
                rows.append(dict(row, fixture=kind, operation=operation, boundary='in_process'))
            (output / 'raw.json').write_text(json.dumps(rows, indent=2) + '\n')
            print(f'{kind}: {operation}', flush=True)
        verify_identities(config)
        jobs = []
        for operation in ('preview', 'status-json', 'status-markdown', 'status-html',
                          'status-completed-json', 'status-completed-markdown', 'status-completed-html'):
            for repeat in range(args.cold_repetitions):
                jobs.append((operation, repeat))
        randomizer.shuffle(jobs)
        for operation, repeat in jobs:
            if operation == 'preview':
                argv = [sys.executable, '-I', '-B', '-m', 'attune_harness', 'test', '--project', str(root),
                        '--scope', scope, '--tests', test, '--interpreter', sys.executable,
                        '--task-dir', str(output / 'new-tasks' / kind / f'cli-{repeat}')]
                expected = 1
            else:
                target = completed_task if '-completed-' in operation else task
                argv = [sys.executable, '-I', '-B', '-m', 'attune_harness', 'status', str(target),
                        '--format', operation.split('-')[-1]]
                expected = 0
            started = time.perf_counter_ns()
            value = subprocess.run(argv, cwd=output, env=env, capture_output=True)
            elapsed = time.perf_counter_ns() - started
            stem = f'{kind}-{operation}-{repeat}'
            (output / 'commands' / (stem + '.stdout')).write_bytes(value.stdout)
            (output / 'commands' / (stem + '.stderr')).write_bytes(value.stderr)
            if value.returncode != expected:
                raise ValueError(f'Unexpected command exit {value.returncode}: {stem}')
            if operation == 'preview' or operation.endswith('-json'):
                result = json.loads(value.stdout)
                assert result['status'] == ('completed' if '-completed-' in operation else 'draft')
                assert result['presentation']['current_result']['outcome'] != 'blocked'
            else:
                assert b'Test scope and evidence' in value.stdout
            rows.append({'fixture': kind, 'operation': operation, 'repeat': repeat,
                         'boundary': 'command_wall', 'condition': 'fresh_process_os_cache_uncontrolled',
                         'elapsed_ns': elapsed, 'command': argv, 'returncode': value.returncode,
                         'stdout_bytes': len(value.stdout),
                         'stdout_sha256': hashlib.sha256(value.stdout).hexdigest()})
        after, task_after = identity(root), tree_identity(task)
        completed_after = tree_identity(completed_task)
        meta['fixtures'][kind].update(after=after, task_after=task_after,
                                     completed_after=completed_after,
                                     unchanged=before == after and guard == task_after and completed_guard == completed_after,
                                     definition_unchanged=sha(definition) == meta['fixtures'][kind]['task_definition_sha256'])
        assert meta['fixtures'][kind]['unchanged'] and meta['fixtures'][kind]['definition_unchanged']
        (output / 'raw.json').write_text(json.dumps(rows, indent=2) + '\n')
        (output / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    meta['baseline_after'] = identity(baseline)
    meta['harness_after'], meta['forms_after'] = verify_identities(config)
    meta['installed_after'] = {name: value for name, value in meta['harness_after']['files'].items() if name.endswith('.py')}
    meta['harness_unchanged'] = harness_before == meta['harness_after']
    meta['forms_unchanged'] = forms_before == meta['forms_after']
    meta['baseline_unchanged'] = meta['baseline_before'] == meta['baseline_after']
    meta['installed_unchanged'] = installed_hashes == meta['installed_after']
    meta['script_unchanged'] = sha(__file__) == meta['script_sha256']
    assert (meta['baseline_unchanged'] and meta['installed_unchanged']
            and meta['script_unchanged'] and meta['forms_unchanged'] and meta['harness_unchanged'])
    meta['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (output / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    (output / 'summary.json').write_text(json.dumps(summarize(rows), indent=2) + '\n')
    print(json.dumps({'output': str(output), 'rows': len(rows), 'unchanged': True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--revision')
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--forms-wheel', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repetitions', type=int, default=20)
    parser.add_argument('--cold-repetitions', type=int, default=10)
    parser.add_argument('--seed', type=int, default=20261022)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error('Run without -O; measurement integrity checks require assertions')
    if args.worker:
        return worker(json.loads(args.worker))
    if not all((args.baseline, args.revision, args.wheel, args.forms_wheel, args.output)):
        parser.error('--baseline, --revision, --wheel, --forms-wheel and --output are required')
    if args.repetitions < 2 or args.cold_repetitions < 2:
        parser.error('Use at least two repetitions per condition')
    measure(args)


if __name__ == '__main__':
    main()
