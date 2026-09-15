"""Evaluation-only scorer checks and real-tool rehearsal with no inference calls."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'experiments/review_quality'


def module(name):
    spec = importlib.util.spec_from_file_location('quality_' + name, HERE/(name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


runner, scorer = module('run'), module('score')
ORACLE = runner.read(HERE/'oracle.json')


def judgment(detected=(), unsupported=(), uncertainty=True):
    return {'detected': list(detected), 'unsupported': list(unsupported),
            'uncertainty_preserved': uncertainty, 'rationale': 'Explicit fixture judgment; no model graded itself.'}


def row(case='c02', arm='harness', status='completed', grades=None):
    if grades is None:
        grades = [judgment(['unsafe_retry']), judgment()]
    return {'trial_id': case + '.' + arm, 'case_id': case, 'arm': arm, 'status': status,
            'narratives': [{'text': 'Specific contradiction. Unsupported assertion.', 'grade': g} for g in grades]}


def test_reviewer_can_catch_miss_but_other_role_falsehood_still_fails():
    item = row(grades=[judgment(), judgment(['unsafe_retry'])])
    result = scorer.aggregate([item], ORACLE)
    assert result['trials'][0]['pass']
    item['narratives'][0]['grade']['unsupported'] = [{'quote': 'Unsupported assertion.', 'reason': 'Contradicts the fixture reference.'}]
    result = scorer.aggregate([item], ORACLE)
    assert not result['trials'][0]['pass']
    assert result['arms']['harness']['critical_misses'] == 0
    assert result['arms']['harness']['unsupported_assertions'] == 1


def test_generic_caution_does_not_detect_specific_critical_issue():
    result = scorer.aggregate([row(grades=[judgment(), judgment()])], ORACLE)
    assert result['arms']['harness']['critical_misses'] == 1
    assert result['arms']['harness']['correction_instances'] == 1


@pytest.mark.parametrize('case', ['c01', 'c03', 'c05', 'c06'])
def test_clean_and_uncertain_controls_pass_without_invented_findings(case):
    assert scorer.aggregate([row(case, grades=[judgment(), judgment()])], ORACLE)['trials'][0]['pass']


def test_every_ambiguous_narrative_must_preserve_uncertainty():
    result = scorer.aggregate([row('c06', grades=[judgment(), judgment(uncertainty=False)])], ORACLE)
    assert not result['trials'][0]['pass']
    assert result['arms']['harness']['ambiguous_preserved'] == 0


@pytest.mark.parametrize('status', ['failed', 'unrun', 'prepared', 'completed'])
def test_missing_output_remains_in_denominator_and_cannot_pass(status):
    result = scorer.aggregate([row(status=status, grades=[])], ORACLE)
    assert result['arms']['harness']['planned'] == 1
    assert result['arms']['harness']['completed'] == 0
    assert result['arms']['harness']['critical_misses'] == 1
    assert not result['trials'][0]['pass']


@pytest.mark.parametrize('change', [
    {'detected': ['imaginary']}, {'detected': ['unsafe_retry', 'unsafe_retry']},
    {'unsupported': [{'quote': 'not present', 'reason': 'reason'}]},
    {'unsupported': [{'quote': '', 'reason': 'reason'}]},
    {'unsupported': [{'quote': 'Specific', 'reason': ''}]},
    {'rationale': ''}, {'uncertainty_preserved': 'yes'},
])
def test_invalid_judgments_fail_closed(change):
    grade = {**judgment(), **change}
    with pytest.raises(ValueError):
        scorer.aggregate([row(grades=[grade, judgment()])], ORACLE)


def test_duplicate_trial_cannot_inflate_sample():
    with pytest.raises(ValueError, match='Duplicate trial'):
        scorer.aggregate([row(), row()], ORACLE)


@pytest.fixture(scope='module')
def rehearsed(tmp_path_factory):
    """Exercise both runners, real retrieval/verification, and blinded audit end to end."""
    from attune_harness import ollama, ollama_review
    from attune_harness.llama_tokens import LlamaTokenizer
    review_module = importlib.import_module('attune_harness.review')
    real_review = review_module.review
    output = tmp_path_factory.mktemp('quality')/'campaign'
    profile = ROOT/'docs/receipts/token-accounting/exported-tokenizer.json'
    runner.prepare(Path(sys.executable).absolute(), profile, output)
    calls = []

    def fake_generate(self, prompt, *, system, schema, seed, options):
        # No HTTP: exercise accepted generation shape and token counts offline.
        calls.append(seed)
        count = self.tokenizer.count(prompt, system)
        self.last_request = {'model': self.pin.name, 'system': system, 'prompt': prompt, 'format': schema,
            'stream': False, 'keep_alive': '5m', 'truncate': False, 'shift': False, 'options': {**options, 'seed': seed}}
        self.generation_attempted = True
        self.last_context_accounting = {**self.tokenizer.identity, 'input_units': count,
            'output_token_reserve': options['num_predict'], 'framing_margin': 512, 'context_tokens': options['num_ctx'],
            'remaining_after_reserves': options['num_ctx'] - count - options['num_predict'] - 512}
        self.last_response = {'response': json.dumps({'review': 'Offline fixture narrative; not quality evidence.'}),
            'model': self.pin.name, 'done': True, 'done_reason': 'stop', 'prompt_eval_count': count, 'eval_count': 12,
            'local_identity': {'model': self.pin.name, 'digest': self.pin.digest, 'server_version': self.pin.server_version}}
        return self.last_response

    class Exchange:
        last_identity = None

        def __init__(self, config, corpus):
            command = config['command']
            self.seed = int(command[command.index('--seed')+1])
            self.receipts = Path(command[command.index('--receipts')+1])
            pin = ollama.ModelPin(**runner.read(HERE/'protocol.json')['model_pin'])
            self.model = ollama.LocalModel(pin, tokenizer=LlamaTokenizer(profile, pin))

        def __call__(self, wire):
            return ollama_review.respond(wire, self.model, self.receipts, self.seed, max_output_tokens=2048)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(ollama.LocalModel, 'generate', fake_generate)
        patch.setattr(review_module, 'review', lambda *a, **kw: real_review(*a, **kw, exchange_factory=Exchange))
        for index, trial in enumerate(runner.read(output/'plan.json')):
            directory = output/f'{index:03}'
            runner.worker(output/'envelopes'/f'{index:03}.json', directory)
            result = runner.read(directory/'result.json')
            assert result['status'] == 'completed', result
            if trial['arm'] == 'harness':
                native = result['verification']['result']
                assert any(c['subject'] == 'reference.md' and c['status'] == 'verified' for c in native['claims'])
                # The reference link is verified; count prose may remain unknown.
                # Neither status is used as the narrative-quality answer key.
                assert native['coverage']['unknown'] == {'c03': 1, 'c04': 2}.get(trial['case_id'], 0)
    assert len(calls) == 54
    runner.blind(output)
    grades = {p['id']: judgment(ORACLE[p['case_id']]['critical_issues']) for p in runner.read(output/'blind-packet.json')}
    runner.write(output/'grades.json', grades)
    return output


def test_frozen_36_trial_rehearsal_has_complete_evidence_and_valid_audit(rehearsed):
    result = scorer.audit_and_score(rehearsed, rehearsed/'grades.json')
    assert result['audit'] == 'passed' and result['disposition'] == 'pass'
    assert result['generation_records'] == 54
    assert result['arms']['harness']['completed'] == 18
    assert result['arms']['single']['completed'] == 18
    assert result['arms']['harness']['critical_opportunities'] == 6


@pytest.mark.parametrize('kind', ['missing_grade', 'extra_grade', 'result_hash', 'blind_hash', 'input_hash', 'source_hash'])
def test_evidence_tampering_is_detected(rehearsed, kind):
    # Restore bytes even on assertion failure; the shared rehearsal stays immutable.
    if kind in ('missing_grade', 'extra_grade'):
        path = rehearsed/'grades.json'; value = runner.read(path)
        if kind == 'missing_grade': value.pop(next(iter(value)))
        else: value['q999'] = judgment()
    elif kind == 'result_hash':
        path = rehearsed/'000/result.json'; value = runner.read(path); value['elapsed_seconds'] += 1
    elif kind == 'blind_hash':
        path = rehearsed/'blind-packet.json'; value = runner.read(path); value[0]['text'] += ' changed'
    elif kind == 'input_hash':
        path = rehearsed/'plan.json'; value = runner.read(path); value[0]['seed'] += 1
    else:
        path = rehearsed/'freeze.json'; value = runner.read(path)
        value['sources']['experiments/review_quality/score.py'] = '0'*64
    original = path.read_bytes()
    try:
        runner.write(path, value)
        with pytest.raises(ValueError):
            scorer.audit_and_score(rehearsed, rehearsed/'grades.json')
    finally:
        path.write_bytes(original)
