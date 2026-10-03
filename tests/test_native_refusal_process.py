"""Offline process receipts distinguish a CLI refusal from uncertain execution."""
# qualify: platform

import json
import sys

import pytest

from attune_harness.native import NativeError, NativeExchange
from attune_harness.process import ProcessResult, invoke


REFUSAL = {'type': 'result', 'is_error': True, 'result': 'Usage credits unavailable',
           'modelUsage': {}}
REQUEST = json.dumps({'version': 1})


@pytest.mark.parametrize('usage,expected', [({}, True), ({'fixture-model': {}}, False)])
def test_real_nonzero_process_preserves_only_reported_no_model_refusal(tmp_path, usage, expected):
    """Use invoke's actual nonzero_exit classification, not an invented result."""
    envelope = {**REFUSAL, 'modelUsage': usage}
    script = tmp_path / 'refusing_cli.py'
    script.write_text(
        'import sys\nprint(' + repr(json.dumps(envelope)) + ')\nsys.exit(1)\n',
        encoding='utf-8',
    )
    def runner(argv, prompt, **kwargs):
        return invoke((sys.executable, str(script)), prompt, **kwargs)
    exchange = NativeExchange('claude', cwd=tmp_path, runner=runner)
    with pytest.raises(NativeError) as caught:
        exchange(REQUEST)
    assert exchange.last_process.returncode == 1
    assert exchange.last_process.failure == 'nonzero_exit'
    assert caught.value.failure == 'nonzero_exit'
    assert caught.value.process_stopped is True
    assert exchange.identity is None
    if expected:
        assert caught.value.refusal == {
            'kind': 'claude_structured_error', 'returncode': 1,
            'result': REFUSAL['result'], 'model_usage': {},
        }
    else:
        assert caught.value.refusal is None


@pytest.mark.parametrize('failure', [
    'timeout_effects_unknown', 'cancelled_effects_unknown', 'interrupted_effects_unknown',
    'output_limit', 'invalid_utf8', 'not_found', 'launch_failed', 'cancelled_before_start',
])
def test_supervision_failure_cannot_promote_partial_envelope_to_refusal(tmp_path, failure):
    def runner(argv, prompt, **kwargs):
        return ProcessResult(argv, 1, json.dumps(REFUSAL), '', failure)
    exchange = NativeExchange('claude', cwd=tmp_path, runner=runner)
    with pytest.raises(NativeError) as caught:
        exchange(REQUEST)
    assert caught.value.failure == failure
    assert caught.value.refusal is None
