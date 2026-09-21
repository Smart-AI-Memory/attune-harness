"""Paired reranker experiment contracts. All provider effects are injected locally."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from attune_harness.review_store import PersistenceError, read_record
from attune_harness.voyage_index import read_generation, write_json
from test_voyage import built, corpus

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'experiments/voyage/compare_rerankers.py'
spec = importlib.util.spec_from_file_location('rerank_comparison', SCRIPT)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def save_packet(output, packet):
    saved = {'digest': comparison.digest(packet), 'packet': packet}
    write_json(output / 'packet.json', saved)
    return saved['digest']


@pytest.fixture
def prepared(tmp_path):
    passages = {}
    for n in range(6):
        excerpt = f'def function_{n}():\n    return "café"\n'
        p = {'repo_id': 'app', 'path': f'file_{n}.py', 'start_byte': 0,
             'end_byte': len(excerpt.encode()), 'excerpt': excerpt,
             'passage_sha256': hashlib.sha256(excerpt.encode()).hexdigest()}
        key = comparison.digest(p)
        passages[key] = {**p, 'passage_id': key, 'embedding_text': f'file_{n}.py\n' + excerpt}
    first = next(iter(passages.values()))
    criteria = [{'any_of': [[{'repo_id': 'app', 'path': first['path'], 'required_spans': [
        {'start_byte': 0, 'end_byte': first['end_byte'], 'text': first['excerpt']}]}]]}]
    packet = {'schema_version': 1, 'kind': 'retrospective-reranker-comparison',
              'models': list(comparison.MODELS), 'rates_per_million': comparison.RATES,
              'endpoint': comparison.ENDPOINT, 'passages': passages, 'top_k': 6,
              'code_hashes': comparison.source_hashes(),
              'limits': {'max_calls': 4, 'max_usd': 1, 'max_request_bytes': 262144},
              'cases': [{'id': 'answerable', 'query': 'Which function uses café?', 'criteria': criteria,
                         'candidate_ids': list(passages), 'models': list(comparison.MODELS)},
                        {'id': 'absent', 'query': 'Where is a payment submitted?', 'criteria': [],
                         'candidate_ids': list(reversed(passages)), 'models': list(reversed(comparison.MODELS))}]}
    output = tmp_path / 'comparison'
    output.mkdir()
    identity = save_packet(output, packet)
    return output, packet, identity


class Provider:
    def __init__(self, output, effect=None):
        self.output, self.effect, self.calls = output, effect, []

    def call(self, payload):
        # Dispatch must have a durable, model-specific intent before every effect.
        record = read_record(self.output / 'live')
        assert record['events'][-1]['state'] == 'pending'
        assert record['events'][-1]['request_digest'] == comparison.digest(payload)
        self.calls.append(copy.deepcopy(payload))
        if self.effect:
            self.effect(payload)
        order = list(range(len(payload['documents'])))
        if payload['model'].endswith('-lite'):
            order.reverse()
        return {'ranking': [{'index': i, 'score': 1 - rank / 10} for rank, i in enumerate(order[:payload['top_k']])],
                'total_tokens': 1000}


def execute(prepared, provider):
    output, _, identity = prepared
    return comparison.run(output, approved_digest=identity, allow_provider=True, provider=provider)


def test_paired_calls_share_inputs_alternate_order_and_keep_model_usage(prepared):
    output, packet, _ = prepared
    provider = Provider(output)
    record = execute(prepared, provider)
    assert record == read_record(output / 'live')
    assert record['status'] == 'completed'
    assert [p['model'] for p in provider.calls] == ['rerank-2.5', 'rerank-2.5-lite', 'rerank-2.5-lite', 'rerank-2.5']
    for a, b in (provider.calls[:2], provider.calls[2:]):
        assert {k: v for k, v in a.items() if k != 'model'} == {k: v for k, v in b.items() if k != 'model'}
        assert set(a) == {'query', 'documents', 'model', 'top_k', 'truncation'}
        assert a['truncation'] is False
    assert provider.calls[0]['documents'] == [packet['passages'][key]['embedding_text'] for key in packet['cases'][0]['candidate_ids']]
    assert record['spent_usd'] == pytest.approx(.00014)
    summary = record['summary']
    assert summary['lite_losses'] == ['answerable'] and summary['lite_gains'] == []
    assert summary['models']['rerank-2.5']['complete_at_5'] == 1
    assert summary['models']['rerank-2.5-lite']['complete_at_5'] == 0
    assert summary['models']['rerank-2.5-lite']['complete_at_10'] == 1
    assert summary['models']['rerank-2.5']['answerable_pairs'] == 1
    assert not summary['unknown_effects'] and not summary['unrun'] and not summary['unresolved']
    with pytest.raises(FileExistsError):
        execute(prepared, provider)
    assert len(provider.calls) == 4


@pytest.mark.parametrize('allow,identity', [(False, 'correct'), (True, None), (True, 'wrong')])
def test_live_dispatch_requires_permission_and_exact_digest(prepared, allow, identity):
    output, _, approved = prepared
    provider = Provider(output)
    with pytest.raises(ValueError):
        comparison.run(output, allow_provider=allow, approved_digest=approved if identity == 'correct' else identity, provider=provider)
    assert provider.calls == [] and not (output / 'live').exists()


@pytest.mark.parametrize('change', [
    lambda p: p['cases'][0].update(query='altered query'),
    lambda p: p['cases'][0]['candidate_ids'].reverse(),
    lambda p: next(iter(p['passages'].values())).update(embedding_text='changed uploaded text'),
    lambda p: p['code_hashes'].update({'src/attune_harness/voyage_provider.py': 'changed'}),
])
@pytest.mark.parametrize('rehash', [False, True])
def test_packet_edits_cannot_reuse_approved_identity(prepared, change, rehash):
    output, packet, identity = prepared
    change(packet)
    write_json(output / 'packet.json', {'digest': comparison.digest(packet) if rehash else identity, 'packet': packet})
    provider = Provider(output)
    with pytest.raises(ValueError):
        execute(prepared, provider)
    assert not provider.calls


def test_code_change_after_freeze_is_rejected(prepared, monkeypatch):
    output, _, _ = prepared
    monkeypatch.setattr(comparison, 'source_hashes', lambda: {'changed': 'hash'})
    with pytest.raises(ValueError, match='implementation changed'):
        execute(prepared, Provider(output))
    assert not (output / 'live').exists()


@pytest.mark.parametrize('change', [
    lambda p: p.update(endpoint='https://another.invalid/v1/rerank'),
    lambda p: p.update(top_k=True),
    lambda p: p['limits'].update(max_calls=5),
    lambda p: p['limits'].update(max_usd=1e-12),
    lambda p: p['limits'].update(max_request_bytes=10),
    lambda p: p['cases'][0].update(models=['rerank-2.5'] * 2),
    lambda p: p['cases'][0]['criteria'][0]['any_of'][0][0]['required_spans'][0].update(text='invented oracle'),
    lambda p: next(iter(p['passages'].values())).update(excerpt='altered source'),
])
def test_invalid_new_packet_rejected_before_dispatch(prepared, change):
    output, packet, _ = prepared
    change(packet)
    identity = save_packet(output, packet)
    provider = Provider(output)
    with pytest.raises(ValueError):
        comparison.run(output, approved_digest=identity, allow_provider=True, provider=provider)
    assert not provider.calls


@pytest.mark.parametrize('fault', ['timeout', 'interrupt', 'missing_usage', 'invalid_ranking'])
def test_uncertain_effect_stops_without_retry_and_preserves_completed_call(prepared, fault):
    output, _, _ = prepared

    class Broken(Provider):
        def call(self, payload):
            result = super().call(payload)
            if len(self.calls) == 2:
                if fault == 'timeout':
                    raise TimeoutError('secret-bearing message must not be persisted')
                if fault == 'interrupt':
                    raise KeyboardInterrupt()
                if fault == 'missing_usage':
                    result['total_tokens'] = None
                if fault == 'invalid_ranking':
                    result['ranking'][1]['index'] = result['ranking'][0]['index']
            return result

    provider = Broken(output)
    result = execute(prepared, provider)
    assert result['status'] == 'incomplete' and len(provider.calls) == 2
    assert [e['state'] for e in result['events']] == ['completed', 'unresolved']
    assert result['summary']['known_cost_usd'] == pytest.approx(.00005)
    assert result['events'][1]['cost_usd'] is None and result['summary']['unknown_effects']
    assert len(result['summary']['unrun']) == 2
    assert 'secret-bearing' not in json.dumps(read_record(output / 'live'))
    with pytest.raises(FileExistsError):
        execute(prepared, provider)
    assert len(provider.calls) == 2


@pytest.mark.parametrize('failure_at,expected_calls', [(1, 0), (2, 0), (3, 1), (4, 1)])
def test_persistence_failure_never_dispatches_next_call(prepared, monkeypatch, failure_at, expected_calls):
    output, _, _ = prepared
    save, count = comparison.RunStore.save, 0

    def broken_save(self, record):
        nonlocal count
        count += 1
        if count == failure_at:
            raise PersistenceError('injected storage failure')
        save(self, record)

    monkeypatch.setattr(comparison.RunStore, 'save', broken_save)
    provider = Provider(output)
    with pytest.raises(PersistenceError):
        execute(prepared, provider)
    assert len(provider.calls) == expected_calls
    with pytest.raises(FileExistsError):
        execute(prepared, provider)
    assert len(provider.calls) == expected_calls


def test_packet_changed_during_call_stops_before_next_request(prepared):
    output, packet, _ = prepared

    def change_packet(_):
        packet['cases'][0]['query'] = 'changed in flight'
        save_packet(output, packet)

    provider = Provider(output, change_packet)
    record = execute(prepared, provider)
    assert len(provider.calls) == 1 and record['status'] == 'incomplete'
    assert record['summary']['unknown_effects']


def test_reported_cost_over_budget_stops_next_dispatch(prepared):
    output, _, _ = prepared

    class Expensive(Provider):
        def call(self, payload):
            return {**super().call(payload), 'total_tokens': 30_000_000}

    provider = Expensive(output)
    record = execute(prepared, provider)
    assert len(provider.calls) == 1 and record['status'] == 'incomplete'
    assert record['spent_usd'] == 1.5  # Post-response stop is not an account billing cap.
    assert not record['summary']['unknown_effects']


def test_scorer_requires_every_span_with_exact_file_identity_and_all_bundle_parts(prepared):
    _, packet, _ = prepared
    criteria = packet['cases'][0]['criteria']
    first, second = list(packet['passages'].values())[:2]
    assert comparison.grade([first], criteria)['complete_at_5'] is True
    for changed in ({**first, 'repo_id': 'other'}, {**first, 'path': second['path']}, {**first, 'end_byte': first['end_byte'] - 1}):
        assert comparison.grade([changed] * 10, criteria)['complete_at_10'] is False
    criteria[0]['any_of'][0].append({'repo_id': 'app', 'path': second['path'], 'required_spans': [
        {'start_byte': 0, 'end_byte': second['end_byte'], 'text': second['excerpt']}]})
    assert comparison.grade([first] * 10, criteria)['complete_at_10'] is False
    assert comparison.grade([first, second], criteria)['complete_at_5'] is True
    control = comparison.grade([first], [])
    assert control['complete_at_5'] is None and control['answer_support'] == 'not_established'


def test_adapter_passes_model_and_disables_truncation_without_using_global_profile():
    from contextlib import nullcontext
    calls = []

    def create(**payload):
        calls.append(payload)
        return {'data': [{'index': 0, 'relevance_score': .8}], 'usage': {'total_tokens': 100}}

    provider = comparison.ModelProvider.__new__(comparison.ModelProvider)
    provider.sdk = SimpleNamespace(Reranking=SimpleNamespace(create=create))
    provider.client = SimpleNamespace(_params={'request_timeout': 60})
    provider.transport = nullcontext
    for model in comparison.MODELS:
        result = provider.call({'model': model, 'query': 'query', 'documents': ['doc'], 'top_k': 1, 'truncation': False})
        assert result == {'ranking': [{'index': 0, 'score': .8}], 'total_tokens': 100}
    assert [c['model'] for c in calls] == list(comparison.MODELS)
    assert all(c['truncation'] is False for c in calls)


def test_cli_offline_preflight_and_incomplete_exit_without_credentials(prepared, tmp_path):
    output, _, identity = prepared
    env = {key: value for key, value in os.environ.items() if key not in ('VOYAGE_API_KEY', 'PYTHONPATH')}
    command = [sys.executable, str(SCRIPT)]
    # Run outside the checkout and without PYTHONPATH: the script must select its own source.
    ready = subprocess.run(command + ['preflight', '--output', str(output)], cwd=tmp_path, env=env,
                           text=True, capture_output=True, timeout=30)
    assert ready.returncode == 0, ready.stderr
    assert json.loads(ready.stdout)['provider_calls'] == 0 and not (output / 'live').exists()
    failed = subprocess.run(command + ['run', '--output', str(output), '--allow-provider', '--approved-digest', identity],
                            cwd=tmp_path, env=env, text=True, capture_output=True, timeout=30)
    assert failed.returncode == 1, failed.stderr
    result = read_record(output / 'live')
    assert result['status'] == 'incomplete' and not result['events']
    assert len(result['summary']['unrun']) == 4


def test_freeze_verifies_archived_generation_and_reuses_exact_candidates(built, tmp_path):
    _, selected, _ = built
    _, metadata = read_generation(selected['config'], selected['generation'])
    passages = metadata['passages']
    old = {'config': selected['config'], 'generation': selected['generation'],
           'manifest': metadata['manifest'], 'passages_digest': comparison.digest(passages),
           'cases': [{'id': 'c1', 'query': 'save_cart', 'criteria': []}]}
    history = tmp_path / 'historical'
    history.mkdir()
    saved = {'packet': old, 'digest': comparison.digest(old)}
    write_json(history / 'freeze.json', saved)
    ids = [p['passage_id'] for p in reversed(passages)]
    write_json(history / 'results.json', {'status': 'completed', 'freeze_digest': saved['digest'],
        'cases': [{'id': 'c1', 'query': 'save_cart', 'status': 'completed', 'candidate_ids': ids}]})
    before = {p.name: p.read_bytes() for p in history.iterdir()}
    output = tmp_path / 'frozen'
    report = comparison.freeze(history, output)
    packet = comparison.load(output)['packet']
    assert report['provider_calls'] == 0 and report['max_calls'] == 2
    assert packet['cases'][0]['candidate_ids'] == ids
    assert packet['passages'] == {p['passage_id']: p for p in passages}
    assert {p.name: p.read_bytes() for p in history.iterdir()} == before
    with pytest.raises(ValueError, match='Preserve existing'):
        comparison.freeze(history, output)

