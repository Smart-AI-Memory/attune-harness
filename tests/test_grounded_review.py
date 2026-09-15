"""Grounded mode rejects fabricated provenance without certifying interpretation."""
import copy
import io
import json
import sys
from types import SimpleNamespace

import pytest

from attune_harness import grounded_review as grounded, ollama_review
from attune_harness.review_contract import digest
from attune_harness.review_participants import decode_action
from attune_harness.review import review
from attune_harness.recovery import resume_review
from test_ollama_review import Model, turn, history, wire
from test_review import case, change_config


def evidence():
    value = turn(); value['history'] = history()
    value['document']['text'] = 'Retry automatically. Café recovery 🧪.'
    value['history'][0]['result']['sources'][0]['excerpt'] = 'Do not retry automatically. Café recovery 🧪.'
    return value


def answer(assessment='contradiction'):
    return {'verdict': {'contradiction': 'issues_found', 'consistent': 'no_supported_defect', 'uncertain': 'uncertain'}[assessment],
        'reasoning': 'The retry instruction conflicts with the reference policy.',
        'uncertainty': 'Whether the timed-out operation executed remains unknown.',
        'assessments': [{'document_quote': 'Retry automatically.', 'reference_path': 'source.md',
            'reference_quote': 'Do not retry automatically.', 'assessment': assessment,
            'reasoning': 'Retrying automatically violates the explicit reference prohibition.'}]}


def invoke(tmp_path, value=None, output=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    value = evidence() if value is None else value
    model = Model(answer() if output is None else output)
    response = ollama_review.respond(wire(value), model, tmp_path, 42, max_output_tokens=2048, grounded=True)
    return decode_action(response, digest(value)), model


def test_real_adapter_returns_cited_verdict_and_retains_structured_judgment(tmp_path):
    action, model = invoke(tmp_path)
    assert 'Verdict: issues_found' in action['text']
    assert 'Reference (source.md): Do not retry automatically.' in action['text']
    assert 'interpretations are not tool-verified' in action['text']
    assert model.calls[0][1]['options']['num_predict'] == 2048
    assert model.calls[0][1]['schema'] == grounded.SCHEMA
    saved = json.loads(next(tmp_path.glob('*/record.json')).read_text())
    assert saved['output_contract'] == 'grounded-v1' and saved['response'] == answer()


@pytest.mark.parametrize('change', [
    lambda a: a.update(verdict='verified'),
    lambda a: a.update(verdict='no_supported_defect'),
    lambda a: a.update(reasoning=''),
    lambda a: a.update(reasoning='The following findings were made:'),
    lambda a: a.update(uncertainty='   '),
    lambda a: a.update(uncertainty='Important uncertainties:'),
    lambda a: a.update(assessments=[]),
    lambda a: a.update(assessments={}),
    lambda a: a.update(claim_id='invented'),
    lambda a: a['assessments'][0].update(document_quote='No retry was requested.'),
    lambda a: a['assessments'][0].update(reference_quote='Retry automatically.'),
    lambda a: a['assessments'][0].update(reference_path='/etc/passwd'),
    lambda a: a['assessments'][0].update(reference_path='../source.md'),
    lambda a: a['assessments'][0].update(reference_path='absent.md'),
    lambda a: a['assessments'][0].update(document_quote=' '),
    lambda a: a['assessments'][0].update(document_quote='.'),
    lambda a: a['assessments'][0].update(reference_quote='.'),
    lambda a: a['assessments'][0].update(assessment='tool_verified'),
    lambda a: a['assessments'][0].update(claim_id='eaf405'),
    lambda a: a['assessments'][0].update(reasoning='Findings:'),
    lambda a: a['assessments'].append(copy.deepcopy(a['assessments'][0])),
])
def test_rejected_output_is_retained_without_fallback_or_retry(tmp_path, change):
    output = answer(); change(output)
    model = Model(output); value = evidence()
    with pytest.raises(ValueError):
        ollama_review.respond(wire(value), model, tmp_path, 42, grounded=True)
    saved = json.loads(next(tmp_path.glob('*/record.json')).read_text())
    assert saved['status'] == 'failed' and saved['generation'] == model.last_response
    assert saved['output_contract'] == 'grounded-v1'
    assert len(model.calls) == 1 and saved['generation_attempted'] is True


@pytest.mark.parametrize('id', ['q006', 'q035', 'q033'])
def test_retained_free_text_failures_are_no_longer_accepted(tmp_path, id):
    from pathlib import Path
    packet = json.loads((Path(__file__).resolve().parents[1]/'docs/receipts/review-quality/run-01/blind-packet.json').read_text())
    raw = next(x['text'] for x in packet if x['id'] == id)
    with pytest.raises(ValueError):
        invoke(tmp_path, output={'review': raw})


@pytest.mark.parametrize('kind', ['empty', 'self', 'ambiguous', 'escape'])
def test_unusable_references_fail_before_generation(tmp_path, kind):
    value = evidence(); sources = value['history'][0]['result']['sources']
    if kind == 'empty': sources.clear()
    elif kind == 'self': sources[0]['path'] = value['document']['path']
    elif kind == 'ambiguous': sources.append({**sources[0], 'excerpt': 'different content'})
    else: sources[0]['path'] = '../escaped.md'
    model = Model(answer())
    with pytest.raises(ValueError):
        ollama_review.respond(wire(value), model, tmp_path, 42, grounded=True)
    assert model.calls == []


def test_unicode_citations_are_exact_not_normalized(tmp_path):
    output = answer()
    for name in ('document_quote', 'reference_quote'):
        output['assessments'][0][name] = 'Café recovery 🧪.'
    action, _ = invoke(tmp_path/'valid', output=output)
    assert 'Café recovery 🧪.' in action['text']
    output['assessments'][0]['document_quote'] = 'Cafe\u0301 recovery 🧪.'
    with pytest.raises(ValueError, match='Document quote'):
        invoke(tmp_path/'altered', output=output)


def test_projected_claims_cannot_be_confused_with_model_finding_ids():
    value = evidence(); before = copy.deepcopy(value)
    projected = grounded.project(value)
    claim = projected['limited_tool_checks'][0]['claims'][0]
    assert claim == {'kind': 'links', 'subject': 'missing.md', 'status': 'unknown', 'location': 'line 1'}
    assert 'id' not in claim and 'lead_narrative' not in json.dumps(projected)
    assert value == before


@pytest.mark.parametrize('assessment', ['consistent', 'uncertain'])
def test_nondefect_verdicts_still_require_a_cited_assessment(tmp_path, assessment):
    action, _ = invoke(tmp_path, output=answer(assessment))
    assert 'Verdict: ' + answer(assessment)['verdict'] in action['text']


def test_matching_citations_do_not_prove_semantic_correctness(tmp_path):
    output = answer('consistent')  # Intentionally wrong interpretation of true quotations.
    action, _ = invoke(tmp_path, output=output)
    assert 'unverified proposal' in action['text']
    assert 'interpretations are not tool-verified' in action['text']
    # This is for the independent quality evaluator to reject, not a fake truth check.


@pytest.mark.parametrize('character', ['x', '🧪'])
@pytest.mark.parametrize('extra', [0, 1])
def test_grounded_rendering_obeys_exact_existing_utf8_boundary(tmp_path, character, extra):
    value, output = evidence(), answer()
    output['reasoning'] = 'x'
    available = 32768 - len(grounded.render(output, value).encode())
    count, remainder = divmod(available + extra, len(character.encode()))
    output['reasoning'] = 'x' + character*count + 'x'*remainder
    assert len(grounded.render(output, value).encode()) == 32768 + extra
    if extra:
        with pytest.raises(ValueError, match='final text'):
            invoke(tmp_path, output=output)
    else:
        action, model = invoke(tmp_path, output=output)
        assert len(action['text'].encode()) == 32768
        assert 'maxLength' not in json.dumps(model.calls[0][1]['schema'])


def test_grounded_escaping_overflow_is_failed(tmp_path):
    output = answer(); output['reasoning'] = 'Explanation. ' + '\x00'*12000
    with pytest.raises(ValueError):
        invoke(tmp_path, output=output)
    saved = json.loads(next(tmp_path.glob('*/record.json')).read_text())
    assert saved['status'] == 'failed' and saved['generation'] is not None


def test_changing_grounded_contract_invalidates_accepted_resume(case):
    change_config(case, lambda d: d['participants']['alpha'].update(adapter='command',
        command=[sys.executable, '-I', '-m', 'attune_harness.ollama_review', '--grounded'], timeout=60))
    paused = review(*case, max_operations=1, allow_external=True)
    before = (case[2]/'record.json').read_bytes()
    change_config(case, lambda d: d['participants']['alpha']['command'].remove('--grounded'))
    with pytest.raises(ValueError, match='changed'):
        resume_review(case[2], case[0], case[1], paused['checkpoint_digest'], allow_external=True,
                      exchange_factory=lambda *a: pytest.fail('Changed contract dispatched'))
    assert (case[2]/'record.json').read_bytes() == before


def test_no_defect_cannot_bypass_assessment_requirement(tmp_path):
    output = answer('consistent'); output['assessments'] = []
    with pytest.raises(ValueError, match='at least one'):
        invoke(tmp_path, output=output)


def test_cli_selects_grounded_contract_and_preserves_output_budget(tmp_path, monkeypatch, capsys):
    model = Model(answer())
    monkeypatch.setattr(ollama_review, 'LocalModel', lambda *a, **kw: model)
    monkeypatch.setattr(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(wire(evidence()).encode())))
    monkeypatch.setattr(sys, 'argv', ['peer', '--model', 'local', '--digest', 'a'*64,
        '--server-version', '1', '--receipts', str(tmp_path), '--seed', '42',
        '--max-output-tokens', '2048', '--grounded'])
    ollama_review.main()
    assert 'Verdict: issues_found' in json.loads(capsys.readouterr().out)['action']['text']
    assert model.calls[0][1]['schema'] == grounded.SCHEMA
    assert model.calls[0][1]['options']['num_predict'] == 2048
