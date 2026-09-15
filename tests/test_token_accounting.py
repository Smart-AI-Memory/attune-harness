"""Model-token accounting, profile identity, reserves and visible fallback."""
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_ollama import server
from test_output_budget import final_turn, saved_record
from test_ollama_review import wire
from attune_harness import llama_tokens, ollama_review
from attune_harness.llama_tokens import LlamaTokenizer, PIN
from attune_harness.ollama import LocalModel, LocalModelError, ModelPin, local_request

RECEIPTS = Path(__file__).resolve().parents[1] / 'docs/receipts/token-accounting'
PROFILE = RECEIPTS / 'llama3.1-tokenizer.json'
FIXTURES = json.loads((RECEIPTS / 'retained-count-fixtures.json').read_text())


@pytest.fixture(scope='module')
def tokenizer():
    pytest.importorskip('tiktoken')
    return LlamaTokenizer(PROFILE, ModelPin(**PIN))


@pytest.mark.parametrize('fixture', FIXTURES, ids=[str(i) for i in range(len(FIXTURES))])
def test_retained_real_server_counts_match_local_tokenizer(tokenizer, fixture):
    assert tokenizer.count(fixture['prompt'], fixture['system']) == fixture['server_input_tokens']


def test_real_pilot_fits_larger_reserve_with_all_input_preserved(tokenizer):
    fixture = FIXTURES[0]
    count = tokenizer.count(fixture['prompt'], fixture['system'])
    assert count == 4383
    assert len((fixture['prompt'] + fixture['system']).encode()) == 15338
    assert count + 2048 + 512 <= 16384 < 15338 + 2048 + 512


@pytest.mark.parametrize('change', [{'name': 'other'}, {'digest': 'a'*64}, {'server_version': '0.32.0'}])
def test_tokenizer_refuses_other_model_or_server_before_reading_file(tmp_path, change):
    with pytest.raises(ValueError, match='not qualified'):
        LlamaTokenizer(tmp_path/'absent.json', ModelPin(**{**PIN, **change}))


@pytest.mark.parametrize('body', [b'{}', b'not-json', b'x'*(llama_tokens.MAX_PROFILE_BYTES+1)])
def test_unqualified_or_oversized_profile_never_loads_tokenizer(tmp_path, monkeypatch, body):
    path = tmp_path/'profile.json'; path.write_bytes(body)
    monkeypatch.setattr(llama_tokens.importlib.metadata, 'version', lambda *a: pytest.fail('dependency accessed'))
    with pytest.raises(ValueError, match='qualified profile'):
        LlamaTokenizer(path, ModelPin(**PIN))


@pytest.mark.parametrize('missing', [True, False])
def test_missing_or_changed_dependency_is_explicit_and_never_falls_back(monkeypatch, missing):
    def version(name):
        if missing:
            raise llama_tokens.importlib.metadata.PackageNotFoundError(name)
        return '0.13.0'
    monkeypatch.setattr(llama_tokens.importlib.metadata, 'version', version)
    with pytest.raises(ValueError, match=r'attune-harness\[tokens\]'):
        LlamaTokenizer(PROFILE, ModelPin(**PIN))


def counted_model(server, count):
    original, state, calls = server
    seen = []
    def count_input(prompt, system):
        seen.append((prompt, system))
        return count
    counter = SimpleNamespace(pin=original.pin, count=count_input,
                              identity={'kind': 'model_tokens', 'profile_sha256': 'fixture'})
    return LocalModel(original.pin, request=original.request, tokenizer=counter), state, calls, seen


def run(model, prompt='full input', *, output=2048, context=4096, system='policy'):
    return model.generate(prompt, system=system, schema={'type': 'object'}, seed=1,
                          options={'num_ctx': context, 'num_predict': output})


def test_token_count_allows_input_that_byte_estimate_rejects_and_preserves_request(server):
    model, state, calls, seen = counted_model(server, 1000)
    state['generate']['prompt_eval_count'] = 1000
    prompt = 'Detailed evidence. ' * 1000
    run(model, prompt)
    assert seen == [(prompt, 'policy')]
    payload = next(payload for endpoint, payload in calls if endpoint == 'generate')
    assert payload['prompt'] == prompt and payload['system'] == 'policy'
    assert payload['options'] == {'num_ctx': 4096, 'num_predict': 2048, 'seed': 1}
    assert payload['truncate'] is False and payload['shift'] is False
    assert model.last_context_accounting['remaining_after_reserves'] == 536


@pytest.mark.parametrize('extra', [0, 1])
def test_exact_token_boundary_and_one_token_overflow(server, extra):
    model, state, calls, _ = counted_model(server, 1536 + extra)
    state['generate']['prompt_eval_count'] = 1536 + extra
    if extra:
        with pytest.raises(ValueError, match='context budget'):
            run(model)
        assert not calls and not model.generation_attempted
    else:
        run(model)
        assert model.generation_attempted
    accounting = model.last_context_accounting
    assert accounting['input_units'] == 1536 + extra
    assert accounting['output_token_reserve'] == 2048 and accounting['framing_margin'] == 512
    assert accounting['remaining_after_reserves'] == -extra


@pytest.mark.parametrize('bad_count', [0, -1, True, 2.5, None])
def test_invalid_counter_result_cannot_reach_model(server, bad_count):
    model, _, calls, _ = counted_model(server, bad_count)
    with pytest.raises(ValueError, match='invalid input count'):
        run(model)
    assert calls == []


@pytest.mark.parametrize('reported', [999, 1001])
def test_count_drift_keeps_failed_raw_generation_and_never_retries(server, tmp_path, reported):
    model, state, calls, _ = counted_model(server, 1000)
    state['generate'].update(prompt_eval_count=reported, response='{"review":"Unverified fixture"}')
    value = final_turn()
    with pytest.raises(LocalModelError, match='differs'):
        ollama_review.respond(wire(value), model, tmp_path, 1, max_output_tokens=2048)
    saved = saved_record(tmp_path, value)
    assert saved['status'] == 'failed' and saved['generation'] == model.last_response
    assert saved['context_accounting']['input_units'] == 1000
    assert sum(endpoint == 'generate' for endpoint, _ in calls) == 1


def test_counting_failure_does_not_fall_back_to_bytes(server):
    model, _, calls, _ = counted_model(server, 20)
    def fail(*a):
        raise ValueError('tokenizer unavailable')
    model.tokenizer.count = fail
    with pytest.raises(ValueError, match='tokenizer unavailable'):
        run(model)
    assert calls == []


def test_conservative_mode_is_visible_in_receipt(server, tmp_path):
    model, state, _ = server
    state['generate']['response'] = '{"review":"Unverified fixture"}'
    value = final_turn()
    ollama_review.respond(wire(value), model, tmp_path, 1)
    accounting = saved_record(tmp_path, value)['context_accounting']
    assert accounting['kind'] == 'conservative_utf8_bytes'
    assert accounting['reason'] == 'No qualified tokenizer selected'
    assert accounting['output_token_reserve'] == 512


def test_budget_failure_receipt_retains_accounting_without_generation(server, tmp_path):
    model, _, calls, _ = counted_model(server, 14000)
    value = final_turn()
    with pytest.raises(ValueError, match='context budget'):
        ollama_review.respond(wire(value), model, tmp_path, 1, max_output_tokens=2048)
    saved = saved_record(tmp_path, value)
    assert saved['status'] == 'failed' and saved['generation_attempted'] is False
    assert saved['context_accounting']['input_units'] == 14000 and calls == []


def test_server_count_cannot_consume_reserved_output_even_in_byte_mode(server):
    model, state, calls = server
    state['generate']['prompt_eval_count'] = 2000
    with pytest.raises(LocalModelError, match='reserved context budget'):
        run(model)
    assert sum(endpoint == 'generate' for endpoint, _ in calls) == 1


def test_oversized_input_rejected_before_tokenizer_or_model_access(server):
    model, _, calls, seen = counted_model(server, 1)
    with pytest.raises(ValueError, match='transport budget'):
        run(model, 'x'*65537)
    assert not calls and not seen


def test_constructor_rejects_counter_bound_to_different_model(server):
    model, _, _ = server
    counter = SimpleNamespace(pin=ModelPin(**PIN))
    with pytest.raises(ValueError, match='accepted model pin'):
        LocalModel(model.pin, tokenizer=counter)


def test_cli_tokenizer_selection_is_forwarded_before_generation(monkeypatch, tmp_path, tokenizer, capsys):
    value = final_turn()
    monkeypatch.setattr(sys, 'argv', ['peer', '--model', PIN['name'], '--digest', PIN['digest'],
        '--server-version', PIN['server_version'], '--receipts', str(tmp_path), '--seed', '1',
        '--max-output-tokens', '2048', '--tokenizer-file', str(PROFILE)])
    monkeypatch.setattr(sys, 'stdin', io.TextIOWrapper(io.BytesIO(wire(value).encode())))
    received = []
    def make_model(pin, **kwargs):
        received.append(kwargs['tokenizer'])
        from test_ollama_review import Model
        model = Model()
        model.last_context_accounting = kwargs['tokenizer'].identity
        return model
    monkeypatch.setattr(ollama_review, 'LocalModel', make_model)
    ollama_review.main()
    assert json.loads(capsys.readouterr().out)['action']['kind'] == 'final'
    assert received[0].count('evidence', '') == tokenizer.count('evidence', '')
    assert saved_record(tmp_path, value)['context_accounting']['profile_sha256'] == llama_tokens.PROFILE_SHA256


def test_export_profile_uses_metadata_only_and_refuses_overwrite(monkeypatch, tmp_path):
    show = json.loads((RECEIPTS/'disposable-show.json').read_text())
    calls = []
    def request(endpoint, payload=None, **kwargs):
        calls.append((endpoint, payload))
        assert endpoint == 'show'
        return copy.deepcopy(show)
    monkeypatch.setattr('attune_harness.ollama.local_request', request)
    monkeypatch.setattr(LocalModel, 'metadata', lambda s: {'fixture': 'unchanged'})
    output = tmp_path/'profile.json'
    result = llama_tokens.export_tokenizer(output)
    assert output.read_bytes() == PROFILE.read_bytes() and result['generation_calls'] == 0
    assert calls == [('show', {'model': PIN['name'], 'verbose': True})]
    with pytest.raises(FileExistsError):
        llama_tokens.export_tokenizer(output)
    assert len(calls) == 1


@pytest.mark.parametrize('fault', ['template', 'vocabulary', 'incomplete', 'metadata-drift'])
def test_export_failure_preserves_destination_absence(monkeypatch, tmp_path, fault):
    show = json.loads((RECEIPTS/'disposable-show.json').read_text())
    if fault == 'template': show['template'] = 'different'
    elif fault == 'vocabulary': show['model_info']['tokenizer.ggml.tokens'][0] = 'different'
    elif fault == 'incomplete': show.pop('model_info')
    monkeypatch.setattr('attune_harness.ollama.local_request', lambda *a, **k: show)
    metadata = iter([{'revision': 1}, {'revision': 2 if fault == 'metadata-drift' else 1}])
    monkeypatch.setattr(LocalModel, 'metadata', lambda s: next(metadata))
    output = tmp_path/'profile.json'
    with pytest.raises(ValueError): llama_tokens.export_tokenizer(output)
    assert not output.exists()


def test_show_metadata_has_separate_bound_without_relaxing_generation(monkeypatch):
    payload = json.dumps({'large': 'x'*1_100_000}).encode()
    monkeypatch.setattr('urllib.request.build_opener', lambda *a: SimpleNamespace(open=lambda *a, **k: io.BytesIO(payload)))
    assert len(local_request('show', {})['large']) == 1_100_000
    with pytest.raises(LocalModelError, match='exceeds'):
        local_request('generate', {})
    payload = b'x' * (16_777_216 + 1)
    with pytest.raises(LocalModelError, match='exceeds'):
        local_request('show', {})
