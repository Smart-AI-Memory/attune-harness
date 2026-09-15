import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location('e3_local_' + name, ROOT / 'experiments/e3_local' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine, analysis = load('engine'), load('analyze')


def reply(**kwargs):
    return {'verdict': 'ready', 'findings': [], 'uncertain': False,
            'critical_risk': False, 'disagree': False, 'rationale': 'Fixture.', **kwargs}


@pytest.mark.parametrize('strategy,signals,disagree,count', [
    ('solo', {}, False, 1), ('fixed-cross-review', {}, False, 3), ('fixed-roundtable', {}, False, 5),
    ('adaptive', {}, False, 1), ('adaptive', {'uncertain': True}, False, 3),
    ('adaptive', {'critical_risk': True}, False, 5), ('adaptive', {'uncertain': True}, True, 5)])
def test_strategies_dispatch_expected_independent_stages(strategy, signals, disagree, count):
    seen = []
    def call(stage, draft, reviews):
        seen.append((stage, copy.deepcopy(draft), copy.deepcopy(reviews)))
        if stage == 'draft': return reply(**signals)
        if stage.startswith('review-'):
            assert reviews == []
            return reply(disagree=disagree)
        assert len(reviews) in (1, 3)
        return reply()
    assert engine.orchestrate(strategy, call) == {'verdict': 'ready', 'findings': []}
    assert len(seen) == count
    assert all(draft == seen[1][1] for stage, draft, _ in seen[1:] if stage.startswith('review-'))


def test_different_review_answer_escalates_even_when_disagree_flag_is_false():
    stages = []
    def call(stage, draft, reviews):
        stages.append(stage)
        return reply(uncertain=True) if stage == 'draft' else reply(verdict='revise', findings=['defect'])
    engine.orchestrate('adaptive', call)
    assert stages == ['draft', 'review-1', 'review-2', 'review-3', 'final']


def test_invalid_response_stops_before_any_further_call():
    stages = []
    def call(stage, draft, reviews):
        stages.append(stage)
        return reply(uncertain='false')
    with pytest.raises(ValueError): engine.orchestrate('fixed-roundtable', call)
    assert stages == ['draft']


@pytest.mark.parametrize('bad', [reply(findings=['same', 'same']), reply(verdict='verified'), reply(rationale='x' * 161), {}])
def test_response_schema_is_enforced(bad):
    with pytest.raises(ValueError): engine.validate(bad)


def test_cost_reduction_is_unmeasured_even_with_token_savings():
    summary = {s: {'completed_correct': 36, 'critical_misses': 0, 'median_tokens': 100,
                   'median_latency_seconds': 10} for s in analysis.STRATEGIES}
    summary['adaptive']['median_tokens'] = 50
    result = analysis.comparison(summary)
    assert result['token_reduction'] == 0.5 and result['paid_cost_reduction'] is None


def test_quality_ranks_before_resource_cost_in_fixed_baseline():
    summary = {s: {'completed_correct': 36, 'critical_misses': 0, 'median_tokens': 100,
                   'median_latency_seconds': 10} for s in analysis.STRATEGIES}
    summary['fixed-cross-review']['completed_correct'] = 35
    assert analysis.comparison(summary)['baseline'] == 'fixed-roundtable'
