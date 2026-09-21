"""Paired retrospective reranker comparison. Preflight is offline; no automatic retry."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

# This repository experiment must not silently use an older installed wheel.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from attune_harness.review_contract import canonical, digest
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.voyage_index import read_generation, read_json, table_rows, write_json
from attune_harness.voyage_provider import VoyageProvider, ranking

MODELS = ('rerank-2.5', 'rerank-2.5-lite')
RATES = {'rerank-2.5': 0.05, 'rerank-2.5-lite': 0.02}
ENDPOINT = 'https://api.voyageai.com/v1/rerank'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_hashes():
    for name, module in list(sys.modules.items()):
        if name == 'attune_harness' or name.startswith('attune_harness.'):
            require(Path(module.__file__).resolve().is_relative_to(ROOT / 'src/attune_harness'),
                    'Evaluator imported Harness from outside this checkout')
    files = [Path(__file__).resolve(), *sorted((ROOT / 'src/attune_harness').glob('*.py'))]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


LOADED_HASHES = source_hashes()


def complete(sources, criteria):
    """All criteria; any accepted bundle per criterion; all exact spans per file."""
    return all(any(all(all(any(
        p['repo_id'] == part['repo_id'] and p['path'] == part['path'] and
        p['start_byte'] <= span['start_byte'] and p['end_byte'] >= span['end_byte']
        for p in sources) for span in part['required_spans']) for part in bundle)
        for bundle in criterion['any_of']) for criterion in criteria)


def grade(sources, criteria):
    return {'answer_absent': not bool(criteria), 'returned': len(sources),
            'complete_at_5': complete(sources[:5], criteria) if criteria else None,
            'complete_at_10': complete(sources[:10], criteria) if criteria else None,
            'context_bytes_at_5': sum(len(p['excerpt'].encode()) for p in sources[:5]),
            'answer_support': 'not_established'}


def request(packet, case, model):
    return {'query': case['query'], 'documents': [packet['passages'][key]['embedding_text']
            for key in case['candidate_ids']], 'model': model,
            'top_k': min(packet['top_k'], len(case['candidate_ids'])), 'truncation': False}


def reserve_usd(payload):
    # Conservative byte-based reservation, not provider tokenization or a billing guarantee.
    tokens = (len(payload['query'].encode()) * len(payload['documents']) +
              sum(len(d.encode()) for d in payload['documents']) + 32 * (len(payload['documents']) + 1))
    return tokens * RATES[payload['model']] / 1_000_000


def freeze(history, output):
    require(source_hashes() == LOADED_HASHES, 'Evaluator source changed after import')
    require(not output.exists(), 'Preserve existing output; choose a new directory')
    saved = read_json(history / 'freeze.json')
    old = saved['packet']
    require(digest(old) == saved['digest'], 'Historical freeze digest mismatch')
    results = read_json(history / 'results.json')
    require(results['status'] == 'completed' and results['freeze_digest'] == saved['digest'],
            'Historical evaluation must be complete and bound to its freeze')
    # This deliberately validates an archived generation, not current source freshness.
    directory, metadata = read_generation(old['config'], old['generation'])
    table_rows(directory, metadata)
    require(metadata['manifest'] == old['manifest'] and digest(metadata['passages']) == old['passages_digest'],
            'Historical source snapshot mismatch')
    passages = {p['passage_id']: p for p in metadata['passages']}
    rows = {row['id']: row for row in results['cases']}
    require(len(rows) == len(old['cases']) == len(results['cases']), 'Duplicate or missing historical case')
    cases = []
    for n, case in enumerate(old['cases']):
        row = rows[case['id']]
        require(row['status'] == 'completed' and row['query'] == case['query'], 'Historical query mismatch')
        ids = row['candidate_ids']
        require(ids and len(ids) == len(set(ids)) and all(key in passages for key in ids), 'Invalid candidates')
        cases.append({key: copy.deepcopy(case[key]) for key in ('id', 'query', 'criteria')})
        cases[-1].update(candidate_ids=ids, models=list(MODELS if n % 2 == 0 else reversed(MODELS)))
    packet = {'schema_version': 1, 'kind': 'retrospective-reranker-comparison',
        'endpoint': ENDPOINT, 'models': list(MODELS), 'rates_per_million': RATES,
        'rate_date': '2026-09-16', 'rate_source': 'https://docs.voyageai.com/docs/pricing',
        'source': {'generation': old['generation'], 'historical_freeze_digest': saved['digest'],
                   'historical_results_sha256': hashlib.sha256((history / 'results.json').read_bytes()).hexdigest(),
                   'manifest': old['manifest'], 'freshness': 'archived source snapshot; not the current working tree'},
        'passages': passages, 'cases': cases, 'top_k': 10, 'code_hashes': source_hashes(),
        'limits': {'max_calls': len(cases) * 2, 'max_usd': 1.0, 'max_request_bytes': 262144},
        'criteria': {'scope': 'Retrospective evidence completeness, context and reranker latency; no generated answers',
                     'preference': 'Lite is the latency candidate recommended by Voyage FAQ.',
                     'candidate_gate': 'No loss on a case supported by baseline at top five; lower paired median latency.',
                     'promotion': 'No automatic promotion; fresh validation is required before changing the default.'}}
    validate(packet)
    output.mkdir()
    write_json(output / 'packet.json', {'digest': digest(packet), 'packet': packet})
    return preflight(output)


def validate(packet):
    require(type(packet['schema_version']) is int and packet['schema_version'] == 1 and
            packet['kind'] == 'retrospective-reranker-comparison', 'Wrong packet kind')
    require(packet['models'] == list(MODELS) and packet['rates_per_million'] == RATES and packet['endpoint'] == ENDPOINT,
            'Model, rate or destination mismatch')
    require(type(packet['top_k']) is int and 1 <= packet['top_k'] <= 10, 'Invalid top_k')
    cases, passages = packet['cases'], packet['passages']
    require(1 <= len(cases) <= 100 and len({c['id'] for c in cases}) == len(cases), 'Invalid cases')
    limits = packet['limits']
    require(type(limits['max_calls']) is int and limits['max_calls'] == len(cases) * 2, 'Call bound mismatch')
    require(type(limits['max_usd']) in (int, float) and 0 < limits['max_usd'] <= 1, 'Invalid spend bound')
    require(type(limits['max_request_bytes']) is int and 1 <= limits['max_request_bytes'] <= 262144, 'Invalid byte bound')
    for key, p in passages.items():
        require(p['passage_id'] == key and digest({k: v for k, v in p.items() if k not in ('passage_id', 'embedding_text')}) == key,
                'Passage identity mismatch')
        require(hashlib.sha256(p['excerpt'].encode()).hexdigest() == p['passage_sha256'], 'Passage byte mismatch')
    for case in cases:
        require(isinstance(case['query'], str) and 0 < len(case['query'].encode()) <= 4096, 'Invalid query')
        ids = case['candidate_ids']
        require(1 <= len(ids) <= 50 and len(set(ids)) == len(ids) and all(key in passages for key in ids), 'Invalid candidates')
        require(sorted(case['models']) == sorted(MODELS), 'Both models required exactly once')
        for criterion in case['criteria']:
            require(criterion['any_of'] and all(criterion['any_of']), 'Empty evidence alternative')
            for bundle in criterion['any_of']:
                for part in bundle:
                    require(part['required_spans'], 'Empty evidence span')
                    for span in part['required_spans']:
                        require(span['end_byte'] > span['start_byte'] >= 0, 'Invalid evidence span')
                        require(any(p['repo_id'] == part['repo_id'] and p['path'] == part['path'] and
                            p['start_byte'] <= span['start_byte'] and p['end_byte'] >= span['end_byte'] and
                            p['excerpt'].encode()[span['start_byte']-p['start_byte']:span['end_byte']-p['start_byte']].decode() == span['text']
                            for p in passages.values()), 'Oracle span is not bound to archived source bytes')
        for model in MODELS:
            require(len(canonical(request(packet, case, model)).encode()) <= limits['max_request_bytes'], 'Request exceeds byte bound')
    reserved = sum(reserve_usd(request(packet, case, model)) for case in cases for model in MODELS)
    require(reserved <= limits['max_usd'], 'Reservation exceeds total study budget')


def load(output, expected=None):
    saved = read_json(output / 'packet.json')
    require(digest(saved['packet']) == saved['digest'], 'Packet digest mismatch')
    require(expected is None or saved['digest'] == expected, 'Approved packet digest mismatch')
    require(saved['packet']['code_hashes'] == source_hashes() == LOADED_HASHES,
            'Evaluator or implementation changed; freeze a new packet')
    validate(saved['packet'])
    return saved


def preflight(output):
    saved = load(output)
    p = saved['packet']
    input_bytes = sum(len(c['query'].encode()) * len(c['candidate_ids']) +
                      sum(len(p['passages'][key]['embedding_text'].encode()) for key in c['candidate_ids']) for c in p['cases'])
    reservation = sum(reserve_usd(request(p, c, m)) for c in p['cases'] for m in MODELS)
    return {'status': 'ready', 'packet_digest': saved['digest'], 'cases': len(p['cases']),
        'answerable': sum(bool(c['criteria']) for c in p['cases']), 'models': list(MODELS),
        'max_calls': p['limits']['max_calls'], 'embedding_calls': 0, 'provider_calls': 0,
        'billed_pair_text_bytes_both_models': input_bytes * 2,
        'upload_json_bytes_both_models': sum(len(canonical(request(p, c, m)).encode()) for c in p['cases'] for m in MODELS),
        'estimated_usd_bytes_divided_by_four': input_bytes / 4 * sum(RATES.values()) / 1_000_000,
        'reserved_usd_bytes_plus_allowance': reservation, 'stop_budget_usd': p['limits']['max_usd'],
        'estimate_scope': 'Byte-based estimates before credits, not exact token counts or an account billing cap.',
        'output': str(output.absolute())}


class ModelProvider(VoyageProvider):
    def call(self, payload):
        with self.transport():
            raw = self.sdk.Reranking.create(**payload, **self.client._params)
        return {'ranking': [{'index': r['index'], 'score': r['relevance_score']} for r in raw['data']],
                'total_tokens': raw.get('usage', {}).get('total_tokens')}


def summarize(record, packet):
    completed = [e for e in record['events'] if e['state'] == 'completed']
    by_case = {c['id']: {} for c in packet['cases']}
    for event in completed:
        by_case[event['case_id']][event['model']] = event
    pairs = [v for v in by_case.values() if len(v) == 2]
    answerable = [v for v in pairs if not v[MODELS[0]]['grade']['answer_absent']]
    dispatched = {(e['case_id'], e['model']) for e in record['events']}
    return {'completed_calls': len(completed), 'planned_calls': packet['limits']['max_calls'],
        'unresolved': [{'case_id': e['case_id'], 'model': e['model']} for e in record['events'] if e['state'] != 'completed'],
        'unrun': [{'case_id': c['id'], 'model': m} for c in packet['cases'] for m in c['models']
                  if (c['id'], m) not in dispatched],
        'complete_pairs': len(pairs), 'known_cost_usd': sum(e['cost_usd'] for e in completed),
        'unknown_effects': any(e['state'] != 'completed' for e in record['events']),
        'models': {m: {'complete_at_5': sum(v[m]['grade']['complete_at_5'] for v in answerable),
                       'complete_at_10': sum(v[m]['grade']['complete_at_10'] for v in answerable),
                       'answerable_pairs': len(answerable),
                       'median_context_bytes_at_5': statistics.median(v[m]['grade']['context_bytes_at_5'] for v in pairs) if pairs else None,
                       'median_provider_seconds': statistics.median(v[m]['provider_seconds'] for v in pairs) if pairs else None}
                   for m in MODELS},
        'lite_losses': [cid for cid, v in by_case.items() if len(v) == 2 and
                         v[MODELS[0]]['grade']['complete_at_5'] is True and v[MODELS[1]]['grade']['complete_at_5'] is False],
        'lite_gains': [cid for cid, v in by_case.items() if len(v) == 2 and
                        v[MODELS[0]]['grade']['complete_at_5'] is False and v[MODELS[1]]['grade']['complete_at_5'] is True],
        'paired_median_lite_minus_baseline_seconds': statistics.median(v[MODELS[1]]['provider_seconds'] -
                    v[MODELS[0]]['provider_seconds'] for v in pairs) if pairs else None,
        'promotion': 'Unqualified: retrospective comparison; fresh validation remains required.'}


def run(output, *, approved_digest=None, allow_provider=False, provider=None):
    saved = load(output, approved_digest)
    require(allow_provider and approved_digest == saved['digest'], 'Explicit provider permission and exact approved digest required')
    p = saved['packet']
    store = RunStore(output / 'live')  # Never reuse an existing live run, including failed/partial runs.
    with store.lease():
        record = {'schema_version': 1, 'recovery': {'profile': 'paired-reranker-v1'},
                  'packet_digest': saved['digest'], 'status': 'running', 'events': [], 'spent_usd': 0.0}
        store.save(record)
        started = time.perf_counter()
        try:
            client = provider if provider is not None else ModelProvider()
            for case in p['cases']:
                for model in case['models']:
                    load(output, saved['digest'])
                    payload = request(p, case, model)
                    reserve = reserve_usd(payload)
                    require(len(record['events']) < p['limits']['max_calls'] and
                            record['spent_usd'] + reserve <= p['limits']['max_usd'], 'Study budget exhausted')
                    event = {'case_id': case['id'], 'model': model, 'request_digest': digest(payload),
                             'state': 'pending', 'reserved_usd': reserve, 'cost_usd': None}
                    record['events'].append(event)
                    store.save(record)  # Durable dispatch intent before invoking the provider.
                    before = time.perf_counter()
                    result = client.call(copy.deepcopy(payload))
                    event['provider_seconds'] = time.perf_counter() - before
                    event['result'] = result
                    ranking(result, len(payload['documents']), payload['top_k'])
                    require(result.get('total_tokens') is not None, 'Provider usage unknown; stop without retry')
                    load(output, saved['digest'])
                    ranked = [p['passages'][case['candidate_ids'][r['index']]] for r in result['ranking']]
                    event.update(state='completed', cost_usd=result['total_tokens'] * RATES[model] / 1_000_000,
                                 grade=grade(ranked, case['criteria']), source_ids=[x['passage_id'] for x in ranked])
                    record['spent_usd'] += event['cost_usd']
                    store.save(record)
                    require(record['spent_usd'] <= p['limits']['max_usd'], 'Returned usage exceeded study budget; stop')
            record['status'] = 'completed'
        except PersistenceError:
            raise  # Never overwrite uncertain persisted state or issue another request.
        except BaseException as exc:
            record['status'] = 'incomplete'
            record['error_type'] = type(exc).__name__
            if record['events'] and record['events'][-1]['state'] == 'pending':
                record['events'][-1]['state'] = 'unresolved'
            store.save(record)
        record['evaluator_seconds'] = time.perf_counter() - started
        record['summary'] = summarize(record, p)
        store.save(record)
        return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['freeze', 'preflight', 'run'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--history', type=Path)
    parser.add_argument('--allow-provider', action='store_true')
    parser.add_argument('--approved-digest')
    args = parser.parse_args(argv)
    try:
        if args.phase == 'freeze':
            require(args.history is not None, '--history is required')
            result = freeze(args.history, args.output)
        elif args.phase == 'preflight':
            result = preflight(args.output)
        else:
            result = run(args.output, approved_digest=args.approved_digest, allow_provider=args.allow_provider)
        print(json.dumps(result.get('summary', result) | {'status': result['status']}, indent=2))
        return 0 if result['status'] in ('ready', 'completed') else 1
    except Exception as exc:
        print(json.dumps({'status': 'refused', 'error_type': type(exc).__name__, 'detail': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
