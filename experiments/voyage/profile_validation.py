"""Portable warm offline validation probe; synthetic vectors, real LanceDB, no API calls.

Prepare a fresh fixture once, then measure each source snapshot or installed wheel
in its own process against that fixture. Output directories are never overwritten.
"""

import argparse
from collections import defaultdict
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import sys
import time
import traceback

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('phase', choices=['prepare', 'measure'])
parser.add_argument('--source', type=Path, help='Source snapshot; omit to qualify the active installed package')
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--output', type=Path, help='New measurement directory outside the immutable fixture')
parser.add_argument('--files', type=int, default=105, help='Fixture size; use 105 for qualification')
parser.add_argument('--symbols', type=int, default=10, help='Symbols per file; use 10 for qualification')
args = parser.parse_args()
args.workspace = args.workspace.resolve()
if args.source:
    args.source = args.source.resolve()
    sys.path.insert(0, str(args.source / 'src'))
os.environ.pop('VOYAGE_API_KEY', None)

from attune_harness import voyage_index as index
from attune_harness import voyage_provider as provider
from attune_harness import voyage_retrieval as retrieval
from attune_harness.mcp_server import RetrievalSession
from attune_harness.review_contract import digest
from attune_harness.voyage_sources import config


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def forbidden(*a, **kw):
    raise RuntimeError('Live provider construction forbidden in offline measurement')


provider.VoyageProvider = forbidden
PACKAGE = Path(index.__file__).resolve().parent
if args.source:
    require(PACKAGE == args.source / 'src/attune_harness', 'Wrong source snapshot imported')
SOURCE_HASHES = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PACKAGE.glob('*.py'))}


class FixtureProvider:
    """Local deterministic values exercise float serialization, not semantic quality."""

    def __init__(self):
        self.calls = 0

    def embed(self, texts, input_type):
        self.calls += 1
        vectors = []
        for text in texts:
            rng = random.Random(hashlib.sha256(text.encode()).hexdigest())
            vectors.append([rng.uniform(-0.1, 0.1) for _ in range(1024)])
        return {'vectors': vectors, 'total_tokens': None}

    def rerank(self, query, documents, k):
        self.calls += 1
        return {'ranking': [{'index': i, 'score': 1 - i / 100} for i in range(k)], 'total_tokens': None}


def git(root, *command):
    return subprocess.run(['git', '-C', str(root), '-c', 'commit.gpgsign=false',
        '-c', 'core.hooksPath=' + str(root / '.no-hooks'), *command], check=True, capture_output=True,
        env={**os.environ, 'GIT_AUTHOR_DATE': '2026-09-16T00:00:00Z', 'GIT_COMMITTER_DATE': '2026-09-16T00:00:00Z'})


def fixture_hashes():
    # Querying LanceDB does not alter its publication. Exclude only Git internals.
    return {p.relative_to(args.workspace).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.workspace.rglob('*')) if p.is_file() and '.git' not in p.relative_to(args.workspace).parts}


def prepare():
    require(1 <= args.files <= 105 and 1 <= args.symbols <= 10, 'Fixture size outside bounds')
    args.workspace.mkdir(parents=True, exist_ok=False)
    app = args.workspace / 'app'
    app.mkdir()
    for n in range(args.files):
        text = ''.join(f'def operation_{n:03}_{i}(value):\n'
                       f'    """Fixture calculation {n:03}_{i}. ' + 'Local application evidence. ' * 20 +
                       f'"""\n    return value + {n * 10 + i}\n\n' for i in range(args.symbols))
        (app / f'component_{n:03}.py').write_text(text, encoding='utf-8')
    git(app, 'init')
    git(app, 'add', '.')
    git(app, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-m', 'Offline validation fixture')
    cfg = config({'schema_version': 1, 'roots': [{'repo_id': 'fixture', 'path': str(app)}],
                  'index_dir': str(args.workspace / 'index'), 'allow_overlays': True}, args.workspace)
    fake = FixtureProvider()
    built = index.build_index(cfg, allow_provider=True, provider=fake)
    require(built['passages'] == args.files * args.symbols, 'Unexpected synthetic corpus size')
    selected = index.selection(cfg, built['generation'])
    queries = [f'operation_{n:03}_{min(4, args.symbols-1)} value' for n in range(0, args.files, 20)]
    expected = []
    for i, query in enumerate(queries):
        result = retrieval.retrieve_voyage(selected, query, k=10,
            work_dir=args.workspace / f'seed-{i}', allow_provider=True, provider=fake)
        expected.append(result['sources'])
    index.write_json(args.workspace / 'fixture.json', {
        'selection': selected, 'queries': queries, 'expected': expected,
        'files': args.files, 'passages': built['passages'], 'dimensions': 1024,
        'fixture_provider_calls': fake.calls, 'live_provider_calls': 0,
        'source_hashes': SOURCE_HASHES})
    print(json.dumps({'prepared': str(args.workspace), 'passages': built['passages'],
                      'fixture_provider_calls': fake.calls, 'live_provider_calls': 0}), flush=True)


TIMINGS = defaultdict(list)
BOUNDARIES = []


def instrument(fn, label):
    def wrapped(*a, **kw):
        start = time.perf_counter()
        if label == 'generation_checks':
            BOUNDARIES.append([f'{f.name}:{f.lineno}' for f in traceback.extract_stack()[-5:-1]])
        try:
            return fn(*a, **kw)
        finally:
            TIMINGS[label].append(time.perf_counter() - start)
    return wrapped


def measure(fn):
    TIMINGS.clear()
    BOUNDARIES.clear()
    start = time.perf_counter()
    result = fn()
    return result, {'seconds': time.perf_counter() - start,
        'components': {key: {'calls': len(v), 'seconds': sum(v)} for key, v in TIMINGS.items()},
        'check_callers': list(BOUNDARIES)}


def check_result(result, expected, cached):
    require(result['usage'] == {'new_provider_calls': 0, 'new_tokens': 0, 'new_cost_usd': 0.0}, 'Unexpected provider effect')
    require(result['sources'] == expected, 'Evidence IDs, bytes, scores or source metadata changed')
    require(result['replay']['reused'] is cached, 'Wrong final-cache state')
    require(not result['replay']['provider_health_checked'], 'Unexpected provider health check')
    require(all(s['replayed'] and s['new_tokens'] == 0 and s['new_cost_usd'] == 0 for s in result['stages']), 'Stage replay changed')


def main():
    require(args.output is not None, 'Measurement requires a new --output directory')
    output = args.output.resolve()
    require(not output.is_relative_to(args.workspace) and not args.workspace.is_relative_to(output),
            'Output and fixture must be separate directories')
    output.mkdir(parents=True, exist_ok=False)
    fixture = index.read_json(args.workspace / 'fixture.json')
    before = fixture_hashes()
    selected = fixture['selection']
    for name in ('read_generation', 'snapshot', 'table_rows'):
        setattr(index, name, instrument(getattr(index, name), name))
    wrapped = instrument(index.check_generation, 'generation_checks')
    index.check_generation = retrieval.check_generation = wrapped
    retrieval.candidates = instrument(retrieval.candidates, 'candidates')
    index.check_generation(selected['config'], selected['generation'])  # Warm imports and table before timing.
    samples = []
    for i, query in enumerate(fixture['queries']):
        row = {'query': query, 'expected_evidence_digest': digest(fixture['expected'][i])}
        direct = output / f'direct-{i}'
        direct.mkdir()
        shutil.copytree(args.workspace / f'seed-{i}/stages', direct / 'stages')
        for cached in (False, True):
            result, timing = measure(lambda: retrieval.retrieve_voyage(selected, query, k=10, work_dir=direct))
            check_result(result, fixture['expected'][i], cached)
            row['direct_cached' if cached else 'direct_recompute'] = timing
        request = output / f'task-{i}.json'
        index.write_json(request, {'schema_version': 1, 'kind': 'retrieval-task', 'accepted': True,
            'objective': 'Offline synthetic timing only', 'retrieval': selected,
            'participants': {'probe': {'tools': ['retrieve'], 'max_tool_calls': 2}}})
        session, row['session_setup'] = measure(lambda: RetrievalSession(request, None, 'probe', output / f'session-{i}'))
        work = session.store.directory / 'retrieval-work'
        work.mkdir()
        shutil.copytree(args.workspace / f'seed-{i}/stages', work / 'stages')
        with session.store.lease():
            session.save()
            for cached in (False, True):
                result, timing = measure(lambda: session.invoke('harness.retrieve', {'query': query, 'k': 10}))
                check_result(result, fixture['expected'][i], cached)
                row['session_cached' if cached else 'session_recompute'] = timing
            session.finish()
        samples.append(row)
        print(json.dumps({'sample': i + 1, 'seconds': {k: v['seconds'] for k, v in row.items() if isinstance(v, dict)}}), flush=True)
    require(before == fixture_hashes(), 'Fixture was altered during measurement')
    modes = ('direct_recompute', 'direct_cached', 'session_setup', 'session_recompute', 'session_cached')
    summary = {mode: {'mean_seconds': statistics.mean(s[mode]['seconds'] for s in samples),
        'median_seconds': statistics.median(s[mode]['seconds'] for s in samples),
        'full_check_counts': sorted({s[mode]['components']['generation_checks']['calls'] for s in samples})} for mode in modes}
    result = {'interpreter': sys.executable, 'package': str(PACKAGE), 'source_hashes': SOURCE_HASHES,
        'dependencies': {name: version(name) for name in ('lancedb', 'pyarrow', 'voyageai', 'jsonschema')},
        'python': sys.version, 'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'fixture': {k: v for k, v in fixture.items() if k not in ('expected', 'source_hashes')},
        'fixture_files_digest': digest(before), 'summary': summary, 'samples': samples, 'live_provider_calls': 0,
        'scope': 'Serial warm offline stage/final-cache reuse with synthetic vectors; excludes cold startup, live transport, concurrency and answer generation.'}
    index.write_json(output / 'result.json', result)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    if args.phase == 'prepare':
        prepare()
    else:
        main()
