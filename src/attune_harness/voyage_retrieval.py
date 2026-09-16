"""Scoped hybrid application retrieval and same-run evidence reuse."""

import copy
import re
from pathlib import Path

from .features import report
from .review_contract import bounded_text, canonical, digest
from .review_store import RunStore, read_record
from .voyage_index import check_generation, database, load_selection, read_json, write_json
from .voyage_provider import StageJournal, embeddings, ranking
from .voyage_sources import PROFILE, in_scope, sha, source_bytes


def validate_query(query, k):
    bounded_text(query, 'query', 4096)
    if type(k) is not int or not 1 <= k <= 20:
        raise ValueError('k must be an integer in 1..20')


def predicate(scope):
    def quoted(s):
        return "'" + s.replace("'", "''") + "'"
    expression = 'repo_id IN (' + ','.join(quoted(r) for r in scope['repo_ids']) + ')'
    for item in scope['exclude_paths']:
        expression += f" AND NOT (repo_id = {quoted(item['repo_id'])} AND path = {quoted(item['path'])})"
    return expression


def fuse(*rankings):
    scores = {}
    for rows in rankings:
        for rank, key in enumerate(dict.fromkeys(rows), 1):
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    return sorted(scores, key=lambda key: (-scores[key], key)), scores


def candidates(directory, passages, scope, query, vector, limit):
    allowed = {p['passage_id']: p for p in passages if in_scope(p, scope)}
    if not allowed:
        return [], {}
    table = database(directory / 'db').open_table('passages')
    where = predicate(scope)
    dense_rows = table.search(vector).distance_type('cosine').where(where, prefilter=True).limit(limit).to_list()
    tokens = list(dict.fromkeys(re.findall(r'\w+', query, re.UNICODE)))[:64]
    lexical_rows = (table.search(' '.join(tokens), query_type='fts').where(where, prefilter=True).limit(limit).to_list()
                    if tokens else [])
    # Check database rows before any source text is sent to reranking.
    for row in dense_rows + lexical_rows:
        p = allowed.get(row['passage_id'])
        if p is None or row['repo_id'] != p['repo_id'] or row['path'] != p['path'] or row['text'] != p['embedding_text']:
            raise ValueError('Index returned evidence outside its accepted manifest/scope')
    exact = []
    for key, p in allowed.items():
        words = set(re.findall(r'\w+', p['embedding_text'], re.UNICODE))
        score = sum(t in words for t in tokens)
        if score:
            exact.append((score, key))
    identifiers = [key for score, key in sorted(exact, key=lambda pair: (-pair[0], pair[1]))[:limit]]
    lexical, _ = fuse(identifiers, [r['passage_id'] for r in lexical_rows])
    ordered, scores = fuse([r['passage_id'] for r in dense_rows], lexical[:limit])
    return [allowed[key] for key in ordered[:limit]], scores


def validate_evidence(selection, sources):
    cfg = selection['config']
    _, metadata = check_generation(cfg, selection['generation'])
    allowed = {p['passage_id']: p for p in metadata['passages'] if in_scope(p, selection['scope'])}
    roots = {r['repo_id']: Path(r['path']) for r in cfg['roots']}
    for p in sources:
        original = allowed.get(p['passage_id'])
        if original is None or any(p.get(key) != original[key] for key in original if key != 'embedding_text'):
            raise ValueError('Evidence does not match accepted passage')
        raw = source_bytes(roots[p['repo_id']], p['path'], cfg['max_file_bytes'])
        piece = raw[p['start_byte']:p['end_byte']]
        if sha(raw) != p['file_sha256'] or sha(piece) != p['passage_sha256'] or piece.decode('utf-8') != p['excerpt']:
            raise ValueError('Source or passage bytes changed')


def evidence_basis(sources):
    """Describe what retrieval proved, without equating relevance with truth."""
    return {'source_integrity': 'verified',
            'answer_support': 'not_established' if sources else 'insufficient_evidence',
            'required_action': ('Inspect the cited source before making a claim; if it does not support the '
                                'answer, report insufficient evidence. Verify behavioral claims with tests.'
                                if sources else 'Report insufficient evidence in the selected repository scope.'),
            'ranking_is_verification': False}


def retrieve_voyage(selection, query, *, k=3, work_dir: Path, allow_provider=False, provider=None):
    validate_query(query, k)
    load_selection(selection)
    cfg = selection['config']
    directory, metadata = check_generation(cfg, selection['generation'])
    if work_dir.is_symlink():
        raise ValueError('Retrieval work directory cannot be a symlink')
    work_dir.mkdir(exist_ok=True)
    store = RunStore(work_dir, existing=True)
    with store.lease():
        binding = digest(selection)
        if store.path.exists():
            record = read_record(work_dir)
            if record.get('binding') != binding:
                raise ValueError('Retrieval run is bound to a different accepted scope/configuration')
        else:
            record = {'schema_version': 1, 'recovery': {'profile': 'voyage-retrieval-v1'},
                      'binding': binding, 'invocations': []}
        if len(record['invocations']) >= 100:
            raise PermissionError('Retrieval invocation receipt limit reached')
        key = digest({'selection': selection, 'query': query, 'k': k})
        cached = work_dir / (key + '.json')
        invocation = {'query_digest': key, 'index': len(record['invocations']), 'state': 'prepared'}
        record['invocations'].append(invocation)
        store.save(record)
        if cached.exists():
            saved = read_json(cached)
            if saved['digest'] != digest(saved['result']) or saved['query_digest'] != key:
                raise ValueError('Retrieval evidence cache digest mismatch')
            result = copy.deepcopy(saved['result'])
            validate_evidence(selection, result['sources'])
            result['evidence_basis'] = evidence_basis(result['sources'])
            result['replay'] = {'reused': True, 'original_request_id': result['request_id'],
                                'original_invocation': saved['invocation'], 'provider_health_checked': False}
            result['usage'] = {'new_provider_calls': 0, 'new_tokens': 0, 'new_cost_usd': 0.0}
            for stage in result['stages']:
                stage.update(replayed=True, new_tokens=0, new_cost_usd=0.0)
            invocation.update(state='completed', evidence_digest=saved['digest'], replay=True)
            store.save(record)
            return result
        journal = StageJournal(work_dir / 'stages', cfg, allow_provider=allow_provider, provider=provider)
        stages, chosen, scores = [], [], {}
        available = [p for p in metadata['passages'] if in_scope(p, selection['scope'])]
        evidence_sizes = sorted((len(canonical({name: value for name, value in p.items() if name != 'embedding_text'}).encode())
                                 for p in available), reverse=True)
        if sum(evidence_sizes[:k]) + 16384 > 196608:
            raise ValueError('Requested evidence may exceed 192 KiB; reduce k or passage bounds before paid work')
        try:
            if available:
                embedded, receipt = journal.perform('embed', {'texts': [query], 'input_type': 'query'},
                                                    lambda v: embeddings(v, 1), reserve_calls=1)
                stages.append(receipt)
                chosen, scores = candidates(directory, metadata['passages'], selection['scope'], query,
                                            embedded['vectors'][0], cfg['candidates'])
            if chosen:
                check_generation(cfg, selection['generation'])
                reranked, receipt = journal.perform('rerank', {'query': query, 'documents': [p['embedding_text'] for p in chosen],
                                                              'k': min(k, len(chosen))},
                                                    lambda v: ranking(v, len(chosen), min(k, len(chosen))))
                stages.append(receipt)
                sources = [{**{name: val for name, val in chosen[r['index']].items() if name != 'embedding_text'},
                            'score': r['score'], 'fusion_score': scores[chosen[r['index']]['passage_id']],
                            'match_reason': 'Hybrid candidates ordered by Voyage rerank-2.5'} for r in reranked['ranking']]
            else:
                sources = []
            validate_evidence(selection, sources)
            total_tokens = None if any(s['new_tokens'] is None for s in stages) else sum(s['new_tokens'] for s in stages)
            total_cost = None if any(s['new_cost_usd'] is None for s in stages) else sum(s['new_cost_usd'] for s in stages)
            result = report('retrieve', 'retrieved' if sources else 'no_results', backend='voyage', evidence_version=2,
                            query=query, k=k, config_digest=selection['config_digest'], generation=selection['generation'],
                            profile=PROFILE, corpus={'version': selection['generation'], 'documents': len(metadata['manifest']['files']),
                                                    'roots': {r['repo_id']: r['path'] for r in cfg['roots']}},
                            sources=sources, candidates=len(chosen), stages=stages,
                            evidence_basis=evidence_basis(sources),
                            usage={'new_provider_calls': sum(not s['replayed'] for s in stages),
                                   'new_tokens': total_tokens, 'new_cost_usd': total_cost},
                            replay={'reused': False, 'provider_health_checked': bool(stages) and all(not s['replayed'] for s in stages)})
            if len(canonical(result).encode()) > 196608:
                raise ValueError('Retrieved evidence exceeds 192 KiB; reduce k or passage bounds')
            saved = {'query_digest': key, 'invocation': invocation['index'], 'result': result, 'digest': digest(result)}
            write_json(cached, saved)
            invocation.update(state='completed', evidence_digest=saved['digest'], replay=False)
            store.save(record)
            return result
        except BaseException:
            # Stage sidecars retain the precise completed/unknown billing boundaries.
            # Never overwrite after a persistence exception.
            raise
