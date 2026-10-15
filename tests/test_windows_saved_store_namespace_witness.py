"""Pure claim-validation regressions; these do not exercise native Windows."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = REPO_ROOT / 'experiments/platform/windows_saved_store_namespace_witness_v3.py'
ORIGINAL_PATH = REPO_ROOT / 'experiments/platform/windows_saved_store_proof.py'
spec = importlib.util.spec_from_file_location('namespace_claims', ADAPTER_PATH)
witness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(witness)
original = witness.load_original(ORIGINAL_PATH)


def identity(number):
    return {'volume': 17, 'file_id': f'{number:032x}'}


def token():
    return {'user_sid': 'S-1-5-21-1-2-3-1000', 'administrators_enabled': False,
            'administrators_attributes': [16], 'integrity_sid': 'S-1-16-8192',
            'enabled_privileges': ['SeChangeNotifyPrivilege'], 'token_is_elevated': False}


def flush(where):
    return {'where': where, 'flags': 0, 'returned_ntstatus': 0, 'io_status': 0}


def refresh_aggregate(result):
    # Model a consistently rewritten receipt, not Python shared object aliases.
    result['flush_observations'] = copy.deepcopy(
        [row['flush'] for row in result['creation_barriers']] +
        [row for commit in result['commits'] for row in commit['flushes']])
    result['durability_gate'] = original.receipt_gate(result['flush_observations'])


def receipt():
    stages = ('output_creation_parent', 'scratch_creation_parent', 'store_creation_parent')
    result = {
        'witness_schema': 1, 'experiment': 'native_saved_namespace_creation_v2',
        'status': 'observations_complete', 'coverage': 'creation_chain_and_two_commits_only',
        'identity': {'original_sha256': witness.ORIGINAL_SHA}, 'token': token(),
        'supervisor_token': token(), 'anchor_identity': identity(0), 'filesystem': 'NTFS',
        'token_profile': 'existing-standard-primary-v1', 'production_port_allowed': False,
        'power_loss_tested': False, 'paid_model_calls': 0, 'provider_network_calls': 0,
        'creation_barriers': [
            {'stage': stage, 'parent_identity': identity(i), 'child_identity': identity(i + 1),
             'flush': flush(stage)} for i, stage in enumerate(stages)],
        'commits': [
            {'result': {'request_id': key, 'revision': i + 1}, 'replayed': False,
             'lock_identity': identity(9),
             'rename': {'returned_ntstatus': 0, 'io_status_block_status': 0},
             'flushes': [flush(where) for where in ('prepared_file', 'replaced_file', 'parent_namespace')]}
            for i, key in enumerate(('first', 'second'))],
        'final_counts': {'records': 2, 'history': 2, 'operations': 2},
    }
    refresh_aggregate(result)
    return json.loads(json.dumps(result))


def test_complete_narrow_witness_keeps_production_and_power_loss_unclaimed():
    result = receipt()
    witness.validate(original, result)
    assert result['coverage'] == 'creation_chain_and_two_commits_only'
    assert result['durability_gate']['status'] == 'requires_semantic_review'
    assert result['durability_gate']['production_port_allowed'] is False
    assert result['durability_gate']['power_loss_tested'] is False


@pytest.mark.parametrize('commit_index', (0, 1))
@pytest.mark.parametrize('flush_index', (0, 1, 2))
def test_non_normal_commit_flush_is_rejected_even_with_consistent_aggregate_and_gate(commit_index, flush_index):
    result = receipt()
    result['commits'][commit_index]['flushes'][flush_index]['flags'] = 1
    refresh_aggregate(result)
    # The original gate intentionally ignores flags; the adapter must refuse.
    assert result['durability_gate']['status'] == 'requires_semantic_review'
    with pytest.raises(ValueError):
        witness.validate(original, result)


@pytest.mark.parametrize('status_field', ('returned_ntstatus', 'io_status'))
def test_commit_flush_refusal_is_rejected_with_consistent_aggregate_and_gate(status_field):
    result = receipt()
    result['commits'][1]['flushes'][2][status_field] = 0xC0000022
    refresh_aggregate(result)
    with pytest.raises(ValueError):
        witness.validate(original, result)


def test_missing_creation_parent_barrier_is_rejected():
    result = receipt()
    result['creation_barriers'].pop(1)
    refresh_aggregate(result)
    with pytest.raises(ValueError):
        witness.validate(original, result)


def test_mismatched_creation_parent_identity_is_rejected():
    result = receipt()
    result['creation_barriers'][2]['parent_identity'] = identity(99)
    refresh_aggregate(result)
    with pytest.raises(ValueError):
        witness.validate(original, result)


def test_aggregate_cannot_substitute_a_different_parent_barrier():
    result = receipt()
    result['flush_observations'][-1]['where'] = 'different_parent'
    result['durability_gate'] = original.receipt_gate(result['flush_observations'])
    with pytest.raises(ValueError):
        witness.validate(original, result)


@pytest.mark.parametrize('commit_index', (0, 1))
def test_replayed_commit_cannot_claim_first_publication_or_distinct_replacement(commit_index):
    result = receipt()
    result['commits'][commit_index]['replayed'] = True
    with pytest.raises(ValueError):
        witness.validate(original, result)
