"""Behavioral checks for configurable generation and the existing wire boundary."""
import copy
import io
import json
import sys

import pytest

from test_ollama import server
from test_ollama_review import Model, history, turn, wire
from test_review import case, change_config
from attune_harness import ollama_review
from attune_harness.ollama import LocalModelError
from attune_harness.review import review
from attune_harness.recovery import resume_review
from attune_harness.review_contract import digest
from attune_harness.review_participants import decode_action

PREFIX = 'Local model review (unverified proposal):\n'


def final_turn():
    value = turn()
    value['history'] = history()
    return value


def saved_record(directory, value):
    return json.loads((directory / digest(value) / 'record.json').read_text())


def test_long_review_survives_without_character_or_word_restriction(tmp_path):
    text = 'Detailed evidence review. ' * 160  # 4,160 characters, 480 words.
    value, model = final_turn(), Model({'review': text})
    raw = ollama_review.respond(wire(value), model, tmp_path, 1)
    assert decode_action(raw, digest(value))['text'] == PREFIX + text
    assert saved_record(tmp_path, value)['response']['review'] == text
    system = model.calls[0][1]['system']
    assert '120 words' not in system and '3000' not in system
    assert 'maxLength' not in model.calls[0][1]['schema']['properties']['review']


@pytest.mark.parametrize('character', ['x', '🧪'])
@pytest.mark.parametrize('extra', [0, 1])
def test_exact_utf8_narrative_boundary_includes_label(tmp_path, character, extra):
    available = 32768 - len(PREFIX.encode())
    repetitions, remainder = divmod(available, len(character.encode()))
    text = character * repetitions + 'x' * (remainder + extra)
    value, model = final_turn(), Model({'review': text})
    assert len((PREFIX + text).encode()) == 32768 + extra
    if extra:
        with pytest.raises(ValueError, match='final text'):
            ollama_review.respond(wire(value), model, tmp_path, 1)
        saved = saved_record(tmp_path, value)
        assert saved['status'] == 'failed' and saved['generation'] == model.last_response
    else:
        raw = ollama_review.respond(wire(value), model, tmp_path, 1)
        assert decode_action(raw, digest(value))['text'] == PREFIX + text
        assert saved_record(tmp_path, value)['status'] == 'completed'
    assert len(model.calls) == 1


def test_json_escaping_overflow_retains_failure_before_claiming_completion(tmp_path):
    text = '\x00' * 12000  # <32 KiB narrative, >64 KiB escaped JSON.
    value, model = final_turn(), Model({'review': text})
    with pytest.raises(ValueError):
        ollama_review.respond(wire(value), model, tmp_path, 1)
    saved = saved_record(tmp_path, value)
    assert saved['status'] == 'failed' and saved['generation'] == model.last_response
    assert saved['generation_attempted'] is True and len(model.calls) == 1


def test_workflow_budgets_are_forwarded_recorded_and_do_not_leak(tmp_path):
    original = copy.deepcopy(ollama_review.OPTIONS)
    for index, budget in enumerate([2048, 1024, None]):
        value, model = final_turn(), Model()
        value['turn_id'] = str(index)
        kwargs = {} if budget is None else {'max_output_tokens': budget}
        ollama_review.respond(wire(value), model, tmp_path, 1, **kwargs)
        expected = 512 if budget is None else budget
        assert model.calls[0][1]['options']['num_predict'] == expected
        saved = saved_record(tmp_path, value)
        assert saved['options']['num_predict'] == saved['generation_request']['options']['num_predict'] == expected
    assert ollama_review.OPTIONS == original


@pytest.mark.parametrize('budget', [0, -1, True, 1.5, '2048', None, 15872, 16384])
def test_invalid_output_budget_never_dispatches_or_creates_receipt(tmp_path, budget):
    model = Model()
    with pytest.raises(ValueError):
        ollama_review.respond(wire(final_turn()), model, tmp_path, 1, max_output_tokens=budget)
    assert model.calls == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('budget', [None, 2048])
def test_cli_budget_reaches_actual_generation_and_receipt(monkeypatch, tmp_path, capsys, budget):
    value, model = final_turn(), Model({'review': 'Evidence review. ' * 300})
    argv = ['peer', '--model', 'local', '--digest', 'a'*64, '--server-version', '1',
            '--receipts', str(tmp_path), '--seed', '1']
    if budget is not None:
        argv += ['--max-output-tokens', str(budget)]
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setattr(sys, 'stdin', io.TextIOWrapper(io.BytesIO(wire(value).encode())))
    monkeypatch.setattr(ollama_review, 'LocalModel', lambda *a, **kw: model)
    ollama_review.main()
    output = capsys.readouterr()
    assert decode_action(output.out, digest(value))['text'] == PREFIX + model.value['review']
    assert model.calls[0][1]['options']['num_predict'] == (512 if budget is None else budget)
    assert saved_record(tmp_path, value)['status'] == 'completed'
    assert 'local_model_receipt' in output.err


@pytest.mark.parametrize('budget', ['0', '-1', '1.5', '15872'])
def test_cli_invalid_budget_fails_before_setup(monkeypatch, tmp_path, budget):
    receipts = tmp_path / 'must-not-exist'
    monkeypatch.setattr(sys, 'argv', ['peer', '--model', 'local', '--digest', 'a'*64,
        '--server-version', '1', '--receipts', str(receipts), '--seed', '1', '--max-output-tokens', budget])
    monkeypatch.setattr(ollama_review, 'LocalModel', lambda *a, **kw: pytest.fail('model was accessed'))
    with pytest.raises(SystemExit) as error:
        ollama_review.main()
    assert error.value.code == 2 and not receipts.exists()


@pytest.mark.parametrize('budget', [512, 2048, 15871])
def test_context_reserves_output_and_framing_before_model_access(server, budget):
    model, state, calls = server
    available = 16384 - budget - 512
    state['generate']['prompt_eval_count'] = available
    kwargs = {'system': '', 'schema': {'type': 'object'}, 'seed': 1,
              'options': {'num_ctx': 16384, 'num_predict': budget}}
    model.generate('x' * available, **kwargs)
    assert calls[2][1]['options']['num_predict'] == budget
    calls.clear()
    with pytest.raises(ValueError, match='context budget'):
        model.generate('x' * (available + 1), **kwargs)
    assert not calls and not model.generation_attempted


def test_context_accounts_for_system_and_multibyte_input(server):
    model, _, calls = server
    kwargs = {'system': 'policy', 'schema': {'type': 'object'}, 'seed': 1,
              'options': {'num_ctx': 4096, 'num_predict': 2048}}
    # 1,536 bytes remain; system uses 6 and each accented character uses 2.
    model.generate('é' * 765, **kwargs)
    calls.clear()
    with pytest.raises(ValueError, match='context budget'):
        model.generate('é' * 766, **kwargs)
    assert calls == []


@pytest.mark.parametrize('budget', [0, -1, True, 1.5, 15872, 16384])
def test_invalid_client_output_budget_never_accesses_model(server, budget):
    model, _, calls = server
    with pytest.raises(ValueError):
        model.generate('input', system='', schema={'type': 'object'}, seed=1,
                       options={'num_ctx': 16384, 'num_predict': budget})
    assert calls == []


def test_token_exhaustion_is_failed_and_retained_without_retry(server, tmp_path):
    model, state, calls = server
    state['generate'].update(done_reason='length', response='{"review":"Plausible but truncated."}')
    value = final_turn()
    with pytest.raises(LocalModelError, match='truncated'):
        ollama_review.respond(wire(value), model, tmp_path, 1, max_output_tokens=2048)
    saved = saved_record(tmp_path, value)
    assert saved['status'] == 'failed' and saved['generation']['done_reason'] == 'length'
    assert saved['options']['num_predict'] == 2048
    assert sum(call[0] == 'generate' for call in calls) == 1


def test_budget_change_cannot_silently_resume_accepted_workflow(case):
    change_config(case, lambda d: d['participants']['alpha'].update(
        adapter='command', command=[sys.executable, '-I', '-m', 'attune_harness.ollama_review',
                                    '--max-output-tokens', '512'], timeout=60))
    paused = review(*case, max_operations=1, allow_external=True)
    assert paused['status'] == 'paused'
    before = (case[2] / 'record.json').read_bytes()
    change_config(case, lambda d: d['participants']['alpha']['command'].__setitem__(-1, '2048'))
    with pytest.raises(ValueError, match='changed'):
        resume_review(case[2], case[0], case[1], paused['checkpoint_digest'], allow_external=True,
                      exchange_factory=lambda *a: pytest.fail('changed budget reached dispatch'))
    assert (case[2] / 'record.json').read_bytes() == before
