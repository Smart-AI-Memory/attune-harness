"""Freeze and evaluate source-bound retrieval cases; never grade generated code here."""

import argparse
import ast
from collections import Counter
import json
import math
from pathlib import Path
import re
import time

from attune_harness.review_contract import digest, fields
from attune_harness.voyage_index import (check_generation, read_json, selection, write_json)
from attune_harness.voyage_provider import StageJournal, embeddings
from attune_harness.voyage_retrieval import candidates, retrieve_voyage
from attune_harness.voyage_sources import load_config, in_scope, source_bytes


def lexical(passages, query, k=10):
    """Passage BM25 plus exact identifier/path matching, using the complete text."""
    tokens = lambda s: re.findall(r'\w+', s.lower())
    words = [Counter(tokens(p['embedding_text'])) for p in passages]
    query_tokens = set(tokens(query))
    n = len(passages)
    average = sum(sum(w.values()) for w in words) / n if n else 1
    df = {t: sum(t in w for w in words) for t in query_tokens}
    ranked = []
    for p, counts in zip(passages, words):
        score = 0
        for t in query_tokens:
            tf = counts[t]
            denominator = tf + 1.2 * (1 - 0.75 + 0.75 * sum(counts.values()) / max(average, 1))
            if tf:
                score += math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) * tf * 2.2 / denominator
        if score:
            ranked.append((score, p))
    return [p for _, p in sorted(ranked, key=lambda pair: (-pair[0], pair[1]['passage_id']))[:k]]


def symbol_span(raw, symbol):
    lines = raw.splitlines(keepends=True)
    found = []
    def visit(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                if name == symbol:
                    found.append((sum(map(len, lines[:child.lineno-1])), sum(map(len, lines[:child.end_lineno]))))
                visit(child, name + '.')
            else:
                visit(child, prefix)
    visit(ast.parse(raw.decode('utf-8')))
    if len(found) != 1:
        raise ValueError('Expected exactly one source symbol: ' + symbol)
    return found[0]


def freeze(cfg, generation, cases, output):
    accepted = selection(cfg, generation)
    _, metadata = check_generation(cfg, generation)
    roots = {r['repo_id']: Path(r['path']) for r in cfg['roots']}
    manifest = {(f['repo_id'], f['path']): f for f in metadata['manifest']['files']}
    if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
        raise ValueError('Select 1..100 evaluation cases')
    seen = set()
    frozen = []
    for case in cases:
        fields(case, ('id', 'query', 'expected'))
        if case['id'] in seen or not isinstance(case['query'], str) or not case['query'].strip():
            raise ValueError('Duplicate case or empty query')
        seen.add(case['id'])
        expected = []
        for e in case['expected']:
            fields(e, ('repo_id', 'path', 'symbol'))
            source = manifest[(e['repo_id'], e['path'])]
            raw = source_bytes(roots[e['repo_id']], e['path'], cfg['max_file_bytes'])
            start, end = symbol_span(raw, e['symbol'])
            expected.append({**e, 'sha256': source['sha256'], 'start_byte': start, 'end_byte': end})
        frozen.append({**case, 'expected': expected})
    packet = {'schema_version': 1, 'selection': accepted, 'cases': frozen,
              'measurement': 'Symbol-level source discovery; not proof of answer correctness or application quality'}
    output.mkdir(exist_ok=False)
    write_json(output / 'freeze.json', {'digest': digest(packet), 'packet': packet})
    return {'status': 'frozen', 'cases': len(frozen), 'digest': digest(packet), 'provider_calls': 0}


def metrics(sources, expected):
    def matches(p, e):
        return (p['repo_id'] == e['repo_id'] and p['path'] == e['path'] and
                p['start_byte'] < e['end_byte'] and p['end_byte'] > e['start_byte'])
    if not expected:
        return {'answer_absent': True, 'candidates_returned': len(sources), 'recall_at_5': None,
                'recall_at_10': None, 'reciprocal_rank': None, 'ndcg_at_10': None}
    ranks = [next((i for i, p in enumerate(sources, 1) if matches(p, e)), None) for e in expected]
    # Credit the first appearance of each expected symbol; repeated chunks of one
    # symbol cannot inflate nDCG. Ideal ranking discovers each expected symbol once.
    credited, relevant = set(), []
    for p in sources[:10]:
        new = next((i for i, e in enumerate(expected) if i not in credited and matches(p, e)), None)
        relevant.append(new is not None)
        if new is not None:
            credited.add(new)
    ideal = sum(1 / math.log2(i+2) for i in range(min(len(expected), 10)))
    return {'answer_absent': False, 'candidates_returned': len(sources),
            'recall_at_5': sum(r is not None and r <= 5 for r in ranks) / len(expected),
            'recall_at_10': sum(r is not None and r <= 10 for r in ranks) / len(expected),
            'reciprocal_rank': max((1/r for r in ranks if r is not None), default=0),
            'ndcg_at_10': sum(v / math.log2(i+2) for i, v in enumerate(relevant)) / ideal if ideal else 0}


def run(output, *, allow_provider=False, provider=None):
    saved = read_json(output / 'freeze.json')
    packet = saved['packet']
    if digest(packet) != saved['digest']:
        raise ValueError('Evaluation freeze changed')
    selected, cases = packet['selection'], packet['cases']
    cfg = selected['config']
    directory, metadata = check_generation(cfg, selected['generation'])
    passages = [p for p in metadata['passages'] if in_scope(p, selected['scope'])]
    result_path = output / 'results.json'
    if result_path.exists():
        raise FileExistsError('Evaluation results already exist; preserve them and freeze a new campaign')
    results = [{'id': c['id'], 'status': 'unrun', 'variants': {}} for c in cases]
    report = {'schema_version': 1, 'freeze_digest': saved['digest'], 'status': 'running', 'cases': results,
              'quality_disposition': 'Unqualified; retrieval metrics do not certify application changes'}
    write_json(result_path, report)
    for case, result in zip(cases, results):
        started = time.monotonic()
        try:
            result['variants']['passage_lexical'] = metrics(lexical(passages, case['query']), case['expected'])
            ranked = retrieve_voyage(selected, case['query'], k=10, work_dir=output / 'retrieval-work',
                                     allow_provider=allow_provider, provider=provider)
            result['variants']['hybrid_rerank'] = metrics(ranked['sources'], case['expected'])
            journal = StageJournal(output / 'retrieval-work/stages', cfg, allow_provider=allow_provider, provider=provider)
            vector, _ = journal.perform('embed', {'texts': [case['query']], 'input_type': 'query'}, lambda v: embeddings(v, 1))
            hybrid, _ = candidates(directory, metadata['passages'], selected['scope'], case['query'], vector['vectors'][0], cfg['candidates'])
            result['variants']['hybrid'] = metrics(hybrid[:10], case['expected'])
            result['evidence_request_id'] = ranked['request_id']
            result['usage'] = ranked['usage']
            result.update(status='completed', elapsed_seconds=time.monotonic() - started)
        except Exception as exc:
            result.update(status='failed', error={'type': type(exc).__name__, 'detail': str(exc)})
            report['status'] = 'incomplete'
            write_json(result_path, report)
            return report  # Retain failed and unrun cases; do not spend past an unknown effect.
        write_json(result_path, report)
    report['status'] = 'completed'
    write_json(result_path, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('freeze')
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--generation', required=True)
    p.add_argument('--cases', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('run')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-provider', action='store_true')
    args = parser.parse_args(argv)
    result = (freeze(load_config(args.config), args.generation, read_json(args.cases), args.output) if args.command == 'freeze'
              else run(args.output, allow_provider=args.allow_provider))
    print(json.dumps(result, indent=2))
    return 0 if result['status'] in ('frozen', 'completed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
