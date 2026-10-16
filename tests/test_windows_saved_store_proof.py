"""The native T2 proof cannot promote syscall/crash observations to durability."""

import importlib.util
import ctypes
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'experiments/platform/windows_saved_store_proof.py'
spec = importlib.util.spec_from_file_location('saved_store_proof', SCRIPT)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


def token():
    return {'administrators_enabled': False, 'integrity_sid': 'S-1-16-8192',
            'enabled_privileges': ['SeChangeNotifyPrivilege'], 'token_is_elevated': False}


def receipt():
    rows = [{'where': where, 'returned_ntstatus': 0, 'io_status': 0, 'flags': 0}
            for where in ('prepared_file', 'replaced_file', 'parent_namespace', 'store_creation_parent')]
    return {
        'proof_schema': 1, 'status': 'observations_complete', 'token': token(),
        'token_profile': 'restricted-primary-medium-v1', 'platform': {'filesystem': 'NTFS'},
        'paid_model_calls': 0, 'provider_network_calls': 0, 'production_source_changed': False,
        'flush_observations': rows, 'durability_gate': proof.receipt_gate(rows),
        'locking': {'held_contender_acquired': False, 'released_contender_acquired': True,
                    'delete_access_ntstatus': proof.STATUS_SHARING, 'bounded_contender_seconds': 2.01},
        'concurrency': [
            {'writers': 8, 'identical_requests': identical, 'tokens': [token() for _ in range(8)],
             'history_count_including_seed': 2 if identical else 9,
             'replayed_count': 7 if identical else 0}
            for identical in (False, True)],
        'process_crashes': [{'stage': stage, 'history_count_after_retry': 2,
                            'power_loss_tested': False, 'observed_after': stage in proof.STAGES[2:]}
                           for stage in proof.STAGES],
    }


def test_complete_observations_still_require_semantic_review():
    result = receipt()
    proof.validate_receipt(result)
    assert result['durability_gate'] == {
        'status': 'requires_semantic_review', 'native_flush_refusals': [],
        'documented_equivalence': 'not_established_by_experiment',
        'power_loss_tested': False, 'production_port_allowed': False,
    }


def test_actual_standard_primary_has_distinct_profile_and_refuses_elevated_flag():
    result = receipt()
    result['token_profile'] = 'existing-standard-primary-v1'
    proof.validate_receipt(result)
    result['token']['token_is_elevated'] = True
    with pytest.raises(ValueError):
        proof.validate_receipt(result)


def test_actual_standard_primary_requires_unelevated_descendants_too():
    result = receipt()
    result['token_profile'] = 'existing-standard-primary-v1'
    result['concurrency'][0]['tokens'][0]['token_is_elevated'] = True
    with pytest.raises(ValueError):
        proof.validate_receipt(result)


@pytest.mark.parametrize('field', ['returned_ntstatus', 'io_status'])
def test_directory_flush_refusal_remains_visible_even_if_crash_cases_pass(field):
    result = receipt()
    result['flush_observations'][2][field] = 0xC0000022
    result['durability_gate'] = proof.receipt_gate(result['flush_observations'])
    proof.validate_receipt(result)
    assert result['durability_gate']['status'] == 'blocked'
    assert result['durability_gate']['native_flush_refusals'] == ['parent_namespace']


@pytest.mark.parametrize('change', [
    lambda r: r['token'].update(administrators_enabled=True),
    lambda r: r['token'].update(integrity_sid='S-1-16-12288'),
    lambda r: r['token'].update(enabled_privileges=['SeBackupPrivilege']),
    lambda r: r.update(status='observations_in_progress'),
    lambda r: r.update(provider_network_calls=1),
    lambda r: r.update(paid_model_calls=1),
    lambda r: r.update(production_source_changed=True),
    lambda r: r['durability_gate'].update(production_port_allowed=True),
    lambda r: r['durability_gate'].update(power_loss_tested=True),
    lambda r: r['flush_observations'].pop(2),
    lambda r: r['locking'].update(held_contender_acquired=True),
    lambda r: r['locking'].update(delete_access_ntstatus=0),
    lambda r: r['locking'].update(bounded_contender_seconds=0),
    lambda r: r['concurrency'][1].update(replayed_count=0),
    lambda r: r['concurrency'][1]['tokens'].pop(),
    lambda r: r['concurrency'][0]['tokens'][0].update(administrators_enabled=True),
    lambda r: r['process_crashes'].pop(),
    lambda r: r['process_crashes'][0].update(observed_after=True),
    lambda r: r['process_crashes'][2].update(history_count_after_retry=3),
])
def test_receipt_refuses_missing_or_overstated_evidence(change):
    result = receipt()
    change(result)
    with pytest.raises(ValueError):
        proof.validate_receipt(result)


def test_synthetic_commit_shape_retains_utf8_state_history_and_replay(tmp_path):
    record = {'text': 'Acceptance — 雪 🧭', 'revision': 1}
    state = {'proof_schema': 1, 'records': {'same': record}, 'history': ['same'], 'operations': {'same': record}}
    proof.assert_state(state)
    path = tmp_path / 'Receipt 雪.json'
    proof.save_json(path, state)
    assert proof.read_json(path) == state
    assert '雪'.encode('utf-8') in path.read_bytes()
    state['history'].append('same')
    with pytest.raises(ValueError):
        proof.assert_state(state)


def test_proof_read_and_write_refuse_oversize_whole(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, 'LIMIT', 64)
    path = tmp_path / 'oversize.json'
    path.write_bytes(b' ' * 65)
    with pytest.raises(ValueError):
        proof.read_json(path)
    with pytest.raises(ValueError):
        proof.encode({'value': 'x' * 65})


def test_native_flush_refusal_is_retained_before_later_case_failure(tmp_path):
    class IoStatus(ctypes.Structure):
        _fields_ = [('Status', ctypes.c_void_p)]
    binding = object.__new__(proof.ProofNative)
    binding.event_path = tmp_path / 'native-observations.jsonl'
    def refused(*args):
        return 0xC0000022
    binding.api = SimpleNamespace(IoStatus=IoStatus,
                                 nt=SimpleNamespace(NtFlushBuffersFileEx=refused))
    with pytest.raises(RuntimeError, match='later consistency check'):
        row = binding.flush(None, 'parent_namespace')
        raise RuntimeError('later consistency check')
    recorded = json.loads(binding.event_path.read_text(encoding='utf-8'))
    assert recorded['returned_ntstatus'] == row['returned_ntstatus'] == 0xC0000022
    assert recorded['where'] == 'parent_namespace'


def test_disposable_experiment_import_does_not_bind_windows_on_other_hosts():
    result = subprocess.run([sys.executable, '-I', '-c',
        "import importlib.util,sys; s=importlib.util.spec_from_file_location('probe',sys.argv[1]); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "assert 'attune_harness.windows_effects' not in sys.modules", str(SCRIPT)],
        capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')


def test_retired_launcher_stops_before_any_native_token_or_launch_call(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(proof, 'os', SimpleNamespace(name='nt'))
    def forbidden():
        raise AssertionError('Retired launcher must not bind a native API')
    monkeypatch.setattr(proof, 'ProofNative', forbidden)
    output = tmp_path / 'blocked'
    assert proof.main(['--output', str(output)]) == 2
    result = proof.read_json(output / 'blocked-launcher.json')
    assert result['error'] == 'restricted_launcher_retired'
    assert result['production_port_allowed'] is False
    assert result['storage_observations'] == 0
    assert 'restricted_launcher_retired' in capsys.readouterr().out
