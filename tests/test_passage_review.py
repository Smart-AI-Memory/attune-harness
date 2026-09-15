"""Real adapter boundary and host-owned citations, without model truth claims."""
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from attune_harness import ollama_review, passage_review as passages
from attune_harness.review_contract import digest
from attune_harness.review_participants import decode_action
from attune_harness.review import review
from attune_harness.recovery import resume_review
from test_ollama_review import Model, turn, history, wire
from test_review import case, change_config


def evidence():
    value = turn()
    value['history'] = history()
    value['document']['text'] = 'Retry automatically.\r\n\r\nCafé recovery 🧪.'
    value['history'][0]['result']['sources'][0]['excerpt'] = (
        'Do not retry automatically.\r\n\r\nCafé recovery 🧪.')
    return value


def answer(value, assessment='contradiction'):
    selected = passages.catalog(value)
    return {'uncertainty': 'Whether the operation already executed remains unknown.',
            'assessments': [{'document_id': next(iter(selected['document'])),
                'reference_id': next(iter(selected['reference'])), 'assessment': assessment,
                'reasoning': 'The retry instruction conflicts with the reference prohibition.'}]}


def invoke(tmp_path, value=None, output=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    value = evidence() if value is None else value
    model = Model(answer(value) if output is None else output)
    response = ollama_review.respond(wire(value), model, tmp_path, 42,
                                     max_output_tokens=2048, grounded_passages=True)
    return decode_action(response, digest(value)), model


def test_adapter_sends_closed_choices_and_retains_host_catalog(tmp_path):
    value = evidence(); before = copy.deepcopy(value)
    action, model = invoke(tmp_path, value)
    assert 'Document: Retry automatically.' in action['text']
    assert 'Reference (source.md): Do not retry automatically.' in action['text']
    assert 'Verdict: issues_found' in action['text']
    assert 'interpretations are not tool-verified' in action['text']
    prompt = json.loads(model.calls[0][0]); schema = model.calls[0][1]['schema']
    assert set(schema['properties']) == {'assessments', 'uncertainty'}
    assert schema['properties']['assessments']['items']['properties']['document_id']['enum'] == [p['id'] for p in prompt['document_passages']]
    assert schema['properties']['assessments']['items']['properties']['reference_id']['enum'] == [p['id'] for p in prompt['reference_passages']]
    assert 'guide.md' not in model.calls[0][0] and 'source.md' not in model.calls[0][0]
    assert model.calls[0][1]['options']['num_predict'] == 2048
    saved = json.loads(next(tmp_path.glob('*/record.json')).read_text())
    assert saved['output_contract'] == 'grounded-passages-v1'
    assert saved['citation_catalog'] == passages.catalog(value)
    assert saved['response'] == answer(value) and saved['request']['turn'] == value
    assert value == before


@pytest.mark.parametrize('change', [
    lambda a: a.update(verdict='verified'),
    lambda a: a.update(uncertainty=''),
    lambda a: a.update(uncertainty='Uncertainties:'),
    lambda a: a.update(assessments=[]),
    lambda a: a.update(assessments={}),
    lambda a: a['assessments'][0].update(document_id='unknown'),
    lambda a: a['assessments'][0].update(reference_id='/etc/passwd'),
    lambda a: a['assessments'][0].update(reference_id=a['assessments'][0]['document_id']),
    lambda a: a['assessments'][0].update(document_id=a['assessments'][0]['reference_id']),
    lambda a: a['assessments'][0].update(document_id=[]),
    lambda a: a['assessments'][0].update(reference_path='source.md'),
    lambda a: a['assessments'][0].update(document_quote='Invented text.'),
    lambda a: a['assessments'][0].update(reference_quote='Invented text.'),
    lambda a: a['assessments'][0].update(assessment='verified'),
    lambda a: a['assessments'][0].update(reasoning='Findings:'),
    lambda a: a['assessments'].append(copy.deepcopy(a['assessments'][0])),
])
def test_invalid_selection_is_retained_without_retry(tmp_path, change):
    value = evidence(); output = answer(value); change(output); model = Model(output)
    with pytest.raises(ValueError):
        ollama_review.respond(wire(value), model, tmp_path, 42, grounded_passages=True)
    saved = json.loads(next(tmp_path.glob('*/record.json')).read_text())
    assert saved['status'] == 'failed' and saved['generation'] == model.last_response
    assert saved['output_contract'] == 'grounded-passages-v1'
    assert saved['citation_catalog'] == passages.catalog(value)
    assert len(model.calls) == 1


@pytest.mark.parametrize('changed', ['document', 'reference', 'identity'])
def test_selection_cannot_be_reused_against_changed_evidence(tmp_path, changed):
    value = evidence(); old = answer(value)
    if changed == 'document': value['document']['text'] += '\r\n\r\nNew requirement.'
    elif changed == 'reference': value['history'][0]['result']['sources'][0]['excerpt'] += ' Changed.'
    else: value['history'][0]['result']['sources'][0]['sha256'] = 'b'*64
    with pytest.raises(ValueError, match='stale'):
        invoke(tmp_path, value, old)


@pytest.mark.parametrize('kind', ['empty', 'self', 'ambiguous', 'escape', 'punctuation'])
def test_unusable_reference_never_calls_model(tmp_path, kind):
    value = evidence(); sources = value['history'][0]['result']['sources']
    if kind == 'empty': sources.clear()
    elif kind == 'self': sources[0]['path'] = value['document']['path']
    elif kind == 'ambiguous': sources.append({**sources[0], 'excerpt': 'Different.'})
    elif kind == 'escape': sources[0]['path'] = '../source.md'
    else: sources[0]['excerpt'] = '...\n\n---'
    model = Model()
    with pytest.raises(ValueError):
        ollama_review.respond(wire(value), model, tmp_path, 42, grounded_passages=True)
    assert not model.calls


def test_exact_slices_preserve_unicode_line_endings_and_offsets(tmp_path):
    value = evidence(); value['document']['text'] = '  Line one.\r\nLine two.\r\n\r\nCafe\u0301 🧪.  '
    selected = passages.catalog(value)
    quotes = list(selected['document'].values())
    assert [q['text'] for q in quotes] == ['Line one.\r\nLine two.', 'Cafe\u0301 🧪.']
    for quote in quotes:
        assert value['document']['text'][quote['start']:quote['end']] == quote['text']
    output = answer(value); output['assessments'][0]['document_id'] = list(selected['document'])[1]
    action, _ = invoke(tmp_path, value, output)
    assert 'Document: Cafe\u0301 🧪.' in action['text'] and 'Document: Café' not in action['text']


@pytest.mark.parametrize('relationships,expected', [
    (['consistent'], 'no_supported_defect'), (['uncertain'], 'uncertain'),
    (['consistent', 'uncertain'], 'uncertain'),
    (['uncertain', 'contradiction'], 'issues_found'),
])
def test_host_derives_verdict_from_all_assessments(tmp_path, relationships, expected):
    value = evidence(); output = answer(value); selected = passages.catalog(value)
    output['assessments'] = [dict(output['assessments'][0],
        document_id=list(selected['document'])[i], assessment=relationship)
        for i, relationship in enumerate(relationships)]
    action, _ = invoke(tmp_path, value, output)
    assert 'Verdict: ' + expected in action['text']
    assert 'unverified proposal' in action['text']  # Even a deliberately wrong "consistent" judgment.


@pytest.mark.parametrize('extra', [0, 1])
def test_existing_rendered_output_limit_is_enforced(tmp_path, extra):
    value = evidence(); output = answer(value)
    available = 32768 - len(passages.render(output, value).encode())
    output['assessments'][0]['reasoning'] += 'x'*(available+extra)
    assert len(passages.render(output, value).encode()) == 32768+extra
    if extra:
        with pytest.raises(ValueError, match='final text'): invoke(tmp_path, value, output)
        saved = json.loads(next(tmp_path.glob('*/record.json')).read_text())
        assert saved['status'] == 'failed'
    else:
        action, _ = invoke(tmp_path, value, output)
        assert len(action['text'].encode()) == 32768


def test_every_old_raw_failure_remains_rejected(tmp_path):
    root = Path(__file__).resolve().parents[1]/'docs/receipts/grounded-review/run-01'
    records = list(root.glob('[0-9][0-9][0-9]/generations/*/record.json'))
    assert len(records) == 27
    for index, path in enumerate(records):
        record = json.loads(path.read_text())
        with pytest.raises(ValueError):
            invoke(tmp_path/str(index), record['request']['turn'], json.loads(record['generation']['response']))


def test_duplicate_dispatch_and_bad_turn_digest_do_not_generate(tmp_path):
    value = evidence(); model = Model(answer(value))
    ollama_review.respond(wire(value), model, tmp_path, 42, grounded_passages=True)
    with pytest.raises((ValueError, FileExistsError)):
        ollama_review.respond(wire(value), model, tmp_path, 42, grounded_passages=True)
    raw = json.loads(wire(value)); raw['request_digest'] = 'b'*64
    with pytest.raises(ValueError, match='digest'):
        ollama_review.respond(json.dumps(raw), model, tmp_path, 42, grounded_passages=True)
    assert len(model.calls) == 1


def test_new_mode_changes_invalidate_accepted_resume(case):
    change_config(case, lambda d: d['participants']['alpha'].update(adapter='command',
        command=[sys.executable, '-I', '-m', 'attune_harness.ollama_review', '--grounded'], timeout=60))
    paused = review(*case, max_operations=1, allow_external=True)
    before = (case[2]/'record.json').read_bytes()
    change_config(case, lambda d: d['participants']['alpha']['command'].__setitem__(-1, '--grounded-passages'))
    with pytest.raises(ValueError, match='changed'):
        resume_review(case[2], case[0], case[1], paused['checkpoint_digest'], allow_external=True,
                      exchange_factory=lambda *a: pytest.fail('Changed mode dispatched'))
    assert (case[2]/'record.json').read_bytes() == before


def test_cli_uses_new_contract_and_rejects_conflicting_modes(tmp_path, monkeypatch, capsys):
    value = evidence(); model = Model(answer(value))
    monkeypatch.setattr(ollama_review, 'LocalModel', lambda *a, **kw: model)
    monkeypatch.setattr(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(wire(value).encode())))
    argv = ['peer', '--model', 'local', '--digest', 'a'*64, '--server-version', '1',
            '--receipts', str(tmp_path), '--seed', '42', '--max-output-tokens', '2048', '--grounded-passages']
    monkeypatch.setattr(sys, 'argv', argv)
    ollama_review.main()
    assert 'Verdict: issues_found' in json.loads(capsys.readouterr().out)['action']['text']
    assert model.calls[0][1]['schema'] == passages.schema(value)
    monkeypatch.setattr(sys, 'argv', argv+['--grounded'])
    with pytest.raises(SystemExit): ollama_review.main()
    with pytest.raises(ValueError, match='only one'):
        ollama_review.respond(wire(value), model, tmp_path, 42, grounded=True, grounded_passages=True)
    assert len(model.calls) == 1
