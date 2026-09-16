"""Evaluator contracts and source-grounded oracle preparation; no live inference."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_voyage import corpus, built
from attune_harness.voyage_index import build_index, selection
from attune_harness.voyage_retrieval import retrieve_voyage

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('voyage_eval', ROOT / 'experiments/voyage/evaluate.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_prepared_questions_resolve_to_real_source_symbols():
    heldout = json.loads((ROOT / 'experiments/voyage/heldout.json').read_text())
    tuning = json.loads((ROOT / 'experiments/voyage/tuning.json').read_text())
    assert len(heldout) == 60 and len(tuning) == 4
    assert len({c['id'] for c in heldout+tuning}) == 64
    assert sum(not c['expected'] for c in heldout) == 12
    for case in heldout+tuning:
        for expected in case['expected']:
            raw = (ROOT / expected['path']).read_bytes()
            start, end = evaluation.symbol_span(raw, expected['symbol'])
            assert expected['symbol'].split('.')[-1].encode() in raw[start:end]


def test_freeze_and_three_retrieval_variants_keep_evidence(built, tmp_path):
    _, selected, provider = built
    output = tmp_path / 'evaluation'
    cases = [{'id': 'save', 'query': 'save_cart', 'expected': [{'repo_id': 'app', 'path': 'app.py', 'symbol': 'save_cart'}]},
             {'id': 'absent', 'query': 'Stripe webhook billing', 'expected': []}]
    frozen = evaluation.freeze(selected['config'], selected['generation'], cases, output)
    assert frozen['provider_calls'] == 0
    provider.calls.clear()
    result = evaluation.run(output, allow_provider=True, provider=provider)
    assert result['status'] == 'completed'
    first, second = result['cases']
    assert set(first['variants']) == {'passage_lexical', 'hybrid', 'hybrid_rerank'}
    assert first['variants']['hybrid_rerank']['recall_at_5'] == 1
    assert second['variants']['hybrid_rerank']['answer_absent']
    assert second['variants']['hybrid_rerank']['recall_at_5'] is None
    assert len(provider.calls) == 4  # Share query embeddings across variants.
    with pytest.raises(FileExistsError):
        evaluation.run(output, allow_provider=True, provider=provider)


def test_duplicate_passages_cannot_inflate_ranking_metric():
    sources = [{'repo_id': 'r', 'path': 'a.py', 'start_byte': 0, 'end_byte': 10}] * 10
    expected = [{'repo_id': 'r', 'path': 'a.py', 'start_byte': 0, 'end_byte': 10},
                {'repo_id': 'r', 'path': 'b.py', 'start_byte': 0, 'end_byte': 10}]
    result = evaluation.metrics(sources, expected)
    assert result['recall_at_10'] == .5 and 0 < result['ndcg_at_10'] < 1


@pytest.mark.parametrize('cached', [False, True])
def test_evaluation_cli_exit_matches_saved_campaign(corpus, tmp_path, cached):
    _, cfg, provider = corpus
    index = build_index(cfg, allow_provider=True, provider=provider)
    output = tmp_path / 'campaign'
    cases = [{'id': name, 'query': name, 'expected': []} for name in ('save_cart', 'login_user')]
    config_path = tmp_path / 'config.json'
    cases_path = tmp_path / 'cases.json'
    config_path.write_text(json.dumps(cfg))
    cases_path.write_text(json.dumps(cases))
    frozen = subprocess.run(
        [sys.executable, str(ROOT / 'experiments/voyage/evaluate.py'), 'freeze',
         '--config', str(config_path), '--generation', index['generation'],
         '--cases', str(cases_path), '--output', str(output)],
        capture_output=True, text=True, timeout=60,
    )
    assert frozen.returncode == 0, frozen.stderr
    assert json.loads(frozen.stdout)['status'] == 'frozen'
    if cached:
        for case in cases:
            retrieve_voyage(selection(cfg, index['generation']), case['query'], k=10,
                            work_dir=output / 'retrieval-work', allow_provider=True, provider=provider)
    completed = subprocess.run(
        [sys.executable, str(ROOT / 'experiments/voyage/evaluate.py'), 'run', '--output', str(output)],
        capture_output=True, text=True, timeout=60,
    )
    report = json.loads(completed.stdout)
    assert report == json.loads((output / 'results.json').read_text())
    assert report['status'] == ('completed' if cached else 'incomplete')
    assert [case['status'] for case in report['cases']] == (['completed', 'completed'] if cached else ['failed', 'unrun'])
    assert completed.returncode == (0 if cached else 1)
