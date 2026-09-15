"""Native format fixtures are deterministic peers, not model receipts."""

import json
from pathlib import Path

import pytest

from attune_harness import Check, Status, Task
from attune_harness.adapters import Attempt, JsonParticipant
from attune_harness.native import NativeError, NativeExchange, decode_claude, decode_codex
from attune_harness.process import ProcessResult


def claude(text="4"):
    return dict(type="result", subtype="success", is_error=False, session_id="claude-session",
                structured_output={"text": text}, modelUsage={"fixture-model": {}})


def codex(text="4"):
    return [dict(type="thread.started", thread_id="codex-session"),
            dict(type="turn.started"),
            dict(type="item.completed", item=dict(type="agent_message", text=json.dumps({"text": text}))),
            dict(type="turn.completed", usage={})]


def lines(events):
    return '\n'.join(json.dumps(e) for e in events)


def attempt():
    return Attempt(Task("t", "Compute 2 + 2", ("Return 4",)), "a", "r", "native", "worker", "native-v1")


@pytest.mark.parametrize("provider", ["claude", "codex"])
@pytest.mark.parametrize("answer,status", [("4", Status.VERIFIED), ("5", Status.REJECTED)])
def test_native_translation_runs_through_independent_check(tmp_path, provider, answer, status):
    calls = []
    def runner(argv, prompt, **kwargs):
        calls.append(argv)
        assert attempt().request() in prompt
        assert kwargs["cwd"] == tmp_path
        assert "--model" in argv and argv[argv.index("--model")+1] == "chosen-model"
        if provider == "codex":
            assert json.loads(Path(argv[argv.index("--output-schema")+1]).read_text())["required"] == ["text"]
            assert argv[argv.index("--sandbox")+1] == "read-only"
        else:
            assert argv[argv.index("--tools")+1] == ""
        raw = json.dumps(claude(answer)) if provider == "claude" else lines(codex(answer))
        return ProcessResult(argv, 0, raw, "")
    exchange = NativeExchange(provider, cwd=tmp_path, runner=runner, model="chosen-model")
    result = JsonParticipant(attempt(), exchange).execute(lambda task, output: Check(output.text == "4", "oracle"))
    assert result.receipt.status is status
    assert exchange.identity.session_id == provider + "-session"
    assert exchange.last_process.stdout
    with pytest.raises(NativeError, match="already dispatched"):
        exchange(attempt().request())
    assert len(calls) == 1


@pytest.mark.parametrize("data", [[], {}, {**claude(), "type": "system"},
    {**claude(), "subtype": "error_max_structured_output_retries"},
    {**claude(), "is_error": True}, {**claude(), "is_error": 0},
    {**claude(), "session_id": ""}, {**claude(), "structured_output": {"text": ""}},
    {**claude(), "structured_output": {"text": "4", "success": True}},
    {**claude(), "modelUsage": []}, {**claude(), "modelUsage": {"": {}}},
])
def test_claude_malformed_success_and_error_results_fail(data):
    with pytest.raises((ValueError, NativeError)):
        decode_claude(json.dumps(data))


@pytest.mark.parametrize("events", [[], codex()[:-1], codex()[1:], codex()[2:],
    codex()+[dict(type="turn.completed")], [codex()[0], codex()[0]],
    codex()[:2]+[dict(type="turn.started")],
    [dict(type="turn.completed")], [dict(type="thread.started", thread_id="")],
    codex()[:2]+[dict(type="unknown.future.control")],
    codex()[:2]+[dict(type="turn.failed", error={"message": "quota"})],
    [dict(type="error", message="missing access")],
    codex()[:2]+[dict(type="item.completed", item=None)],
    codex()[:2]+[dict(type="turn.completed")],
    codex()[:2]+[[]],
])
def test_codex_requires_well_ordered_complete_turn(events):
    with pytest.raises((ValueError, NativeError)):
        decode_codex(lines(events))


@pytest.mark.parametrize("decode,raw", [(decode_claude, '{"type":'),
    (decode_claude, '{"type":"result","type":"result"}'),
    (decode_claude, '{"type":NaN}'), (decode_codex, '{"type":'),
    (decode_codex, lines(codex(""))),
])
def test_strict_json_and_empty_output(decode, raw):
    with pytest.raises((ValueError, NativeError)):
        decode(raw)


def test_codex_ignores_commentary_but_preserves_final_and_requires_json():
    events = codex()
    events.insert(2, dict(type="item.started", item=dict(type="reasoning")))
    events.insert(3, dict(type="item.updated", item=dict(type="reasoning")))
    events.insert(4, dict(type="item.completed", item=dict(type="agent_message", phase="commentary", text="Working")))
    assert decode_codex('\n'+lines(events)+'\n')[0] == "4"
    events[-2]["item"]["text"] = "Here is your answer: 4"
    with pytest.raises(ValueError):
        decode_codex(lines(events))


@pytest.mark.parametrize("failure", ["not_found", "nonzero_exit", "timeout_effects_unknown", "cancelled_effects_unknown", "output_limit"])
def test_process_failure_preserves_raw_evidence_and_skips_verification(tmp_path, failure):
    def runner(argv, prompt, **kwargs):
        return ProcessResult(argv, 1, "partial output", "diagnostic", failure)
    exchange = NativeExchange("codex", cwd=tmp_path, runner=runner)
    result = JsonParticipant(attempt(), exchange).execute(lambda *_: pytest.fail("verifier ran"))
    assert result.receipt.status is Status.FAILED
    assert failure in result.receipt.error
    assert exchange.last_process.stdout == "partial output"
    assert exchange.identity is None


def test_zero_exit_with_provider_error_never_verifies(tmp_path):
    def runner(argv, prompt, **kwargs):
        return ProcessResult(argv, 0, json.dumps({**claude(), "is_error": True}), "")
    result = JsonParticipant(attempt(), NativeExchange("claude", cwd=tmp_path, runner=runner)).execute(lambda *_: pytest.fail("verifier ran"))
    assert result.receipt.status is Status.FAILED


@pytest.mark.parametrize("kwargs", [{"provider": "other"}, {"provider": "claude", "model": ""}, {"provider": "codex", "executable": ""}])
def test_invalid_native_configuration(tmp_path, kwargs):
    with pytest.raises(ValueError):
        NativeExchange(cwd=tmp_path, **kwargs)


@pytest.mark.parametrize("raw_request", ['{}', '[]', '{"version":2}', '{"version":true}'])
def test_bad_request_never_launches(tmp_path, raw_request):
    exchange = NativeExchange("codex", cwd=tmp_path, runner=lambda *_: pytest.fail("launched"))
    with pytest.raises(ValueError):
        exchange(raw_request)


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_actual_cli_process_through_full_adapter(tmp_path, provider):
    import os
    import sys
    if os.name != 'posix':
        pytest.skip('POSIX native process qualification')
    executable = tmp_path/'native-fixture'
    raw = json.dumps(claude()) if provider == 'claude' else lines(codex())
    executable.write_text(
        f'#!{sys.executable}\nimport sys\nprompt=sys.stdin.read()\nassert "Compute 2 + 2" in prompt\nprint({raw!r})\n',
        encoding='utf-8',
    )
    executable.chmod(0o700)
    exchange = NativeExchange(provider, cwd=tmp_path, executable=str(executable))
    result = JsonParticipant(attempt(), exchange).execute(lambda t,o: Check(o.text == '4', 'oracle'))
    assert result.receipt.status is Status.VERIFIED
    assert exchange.last_process.returncode == 0
    assert exchange.identity.provider == provider


@pytest.mark.parametrize('message', ['Credit balance is too low', 'Authentication failed'])
def test_native_error_summary_includes_structured_cause(tmp_path, message):
    def runner(argv, prompt, **kwargs):
        raw = json.dumps({**claude(), 'is_error': True, 'result': message})
        return ProcessResult(argv, 1, raw, 'connector warning', 'nonzero_exit')
    exchange = NativeExchange('claude', cwd=tmp_path, runner=runner)
    result = JsonParticipant(attempt(), exchange).execute(lambda *_: pytest.fail('verifier ran'))
    assert message in result.receipt.error
    assert 'connector warning' in result.receipt.error
    assert result.receipt.status is Status.FAILED


@pytest.mark.parametrize('raw', ['truncated {', '[]', json.dumps({**claude(), 'result': 'ordinary output'})])
def test_native_error_summary_does_not_promote_nonerror_stdout(tmp_path, raw):
    def runner(argv, prompt, **kwargs):
        return ProcessResult(argv, 1, raw, 'native failure', 'nonzero_exit')
    exchange = NativeExchange('claude', cwd=tmp_path, runner=runner)
    result = JsonParticipant(attempt(), exchange).execute(lambda *_: pytest.fail('verifier ran'))
    assert result.receipt.error.endswith('native failure')
    assert raw not in result.receipt.error
