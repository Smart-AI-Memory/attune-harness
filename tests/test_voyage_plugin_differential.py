"""Offline signed Voyage versus in-process journal evidence, not a live R6 receipt."""
# qualify: platform
# ruff: noqa: F811 -- imported pytest fixtures are injected by name.

import copy
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from attune_harness import plugin_runtime
from attune_harness.review_store import RunStore, read_record
from attune_harness.voyage_index import build_index, read_generation, selection
from attune_harness.voyage_provider import (PaidStageInterrupted, PaidStageUnresolved,
                                            StageJournal, embeddings)
from attune_harness.voyage_retrieval import retrieve_voyage
from attune_harness.voyage_sources import config
from attune_voyage_plugin.bundle import GRANTS
from test_plugin_signing import base_signer, signers, signer  # noqa: F401
from test_voyage import FakeProvider, corpus  # noqa: F401
from test_voyage_index_plugin import signed_index  # noqa: F401

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/voyage_plugin_differential.py'
spec = importlib.util.spec_from_file_location('voyage_plugin_differential', SCRIPT)
differential = importlib.util.module_from_spec(spec)
spec.loader.exec_module(differential)


def test_signed_and_inprocess_recorded_journeys_replay_without_key(signed_index, corpus, tmp_path, monkeypatch):
    # Enable and every runtime pre/post-check use the real installed closure.
    selected_cfg, _, _, _ = signed_index(real_closure=True)
    plain_raw = copy.deepcopy(selected_cfg)
    plain_raw.pop('voyage_plugin')
    plain_raw['index_dir'] = str(tmp_path / 'plain-index')
    plain_cfg = config(plain_raw, tmp_path)
    provider = FakeProvider()

    selected_build = build_index(selected_cfg, allow_provider=True)
    plain_build = build_index(plain_cfg, allow_provider=True, provider=provider)
    selected_dir, _ = read_generation(selected_cfg, selected_build['generation'])
    plain_dir, _ = read_generation(plain_cfg, plain_build['generation'])
    index_pair = differential.compare(plain_dir / 'stages', selected_dir / 'stages',
                                      identical_responses=True)
    assert index_pair['status'] == 'synthetic_offline_compared'
    assert index_pair['live_qualified'] is False
    assert index_pair['inprocess'] == index_pair['selected']

    selected_work, plain_work = tmp_path / 'selected-retrieve', tmp_path / 'plain-retrieve'
    query = 'save_cart'
    selected_result = retrieve_voyage(selection(selected_cfg, selected_build['generation']), query,
                                      k=2, work_dir=selected_work, allow_provider=True)
    plain_result = retrieve_voyage(selection(plain_cfg, plain_build['generation']), query,
                                   k=2, work_dir=plain_work, allow_provider=True, provider=provider)
    assert selected_result['status'] == plain_result['status'] == 'retrieved'
    assert selected_result['usage']['new_provider_calls'] == plain_result['usage']['new_provider_calls'] == 2
    retrieval_pair = differential.compare(plain_work / 'stages', selected_work / 'stages',
                                          identical_responses=True)
    assert [stage['kind'] for stage in retrieval_pair['selected']] == ['embed', 'rerank']
    assert retrieval_pair['inprocess'] == retrieval_pair['selected']
    assert all(stage['status'] == 'completed' for stage in retrieval_pair['selected'])

    output = tmp_path / 'comparison'
    run = subprocess.run([sys.executable, '-I', str(SCRIPT), '--inprocess', str(plain_work / 'stages'),
                          '--selected', str(selected_work / 'stages'), '--output', str(output),
                          '--identical-recorded-responses'], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'synthetic_offline_compared' in (output / 'comparison.json').read_text()
    with pytest.raises(FileExistsError):
        output.mkdir()

    monkeypatch.delenv('VOYAGE_API_KEY')
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid',
                        lambda *a, **kw: pytest.fail('completed replay launched a child'))
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index',
                        lambda *a, **kw: pytest.fail('published replay launched a child'))
    assert build_index(selected_cfg)['provider_calls'] == build_index(plain_cfg)['provider_calls'] == 0
    selected_replay = retrieve_voyage(selection(selected_cfg, selected_build['generation']), query,
                                      k=2, work_dir=selected_work)
    plain_replay = retrieve_voyage(selection(plain_cfg, plain_build['generation']), query,
                                   k=2, work_dir=plain_work)
    assert selected_replay['replay']['reused'] is plain_replay['replay']['reused'] is True
    assert selected_replay['usage']['new_provider_calls'] == plain_replay['usage']['new_provider_calls'] == 0


def test_signed_child_kill_matches_inprocess_dispatching_without_redispatch(signed_index, tmp_path,
                                                                             monkeypatch):
    sleeping = "from .common import request\nimport time\nrequest()\ntime.sleep(60)\n"
    selected_cfg, _, _, _ = signed_index(embed_script=sleeping, grant={**GRANTS, 'time': 1})
    selected_cfg['max_provider_calls'] = 1
    plain_cfg = copy.deepcopy(selected_cfg)
    plain_cfg.pop('voyage_plugin')
    request = {'texts': ['offline passage'], 'input_type': 'document'}
    selected_dir, plain_dir = tmp_path / 'selected-stages', tmp_path / 'plain-stages'

    class Interrupted:
        calls = 0
        def embed(self, *_):
            self.calls += 1
            raise PaidStageInterrupted('synthetic interrupted in-process call')

    provider = Interrupted()
    with pytest.raises(PaidStageUnresolved, match='subprocess interrupted'):
        StageJournal(selected_dir, selected_cfg, allow_provider=True).perform(
            'embed', request, lambda value: embeddings(value, 1))
    with pytest.raises(PaidStageUnresolved, match='subprocess interrupted'):
        StageJournal(plain_dir, plain_cfg, allow_provider=True, provider=provider).perform(
            'embed', request, lambda value: embeddings(value, 1))
    compared = differential.compare(plain_dir, selected_dir, identical_responses=True)
    assert compared['inprocess'] == compared['selected']
    assert compared['selected'][0]['status'] == 'dispatching'
    assert read_record(selected_dir / compared['selected'][0]['stage_id'])['status'] == 'dispatching'

    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid',
                        lambda *a, **kw: pytest.fail('uncertain replay launched a child'))
    for allow in (False, True):
        with pytest.raises(PaidStageUnresolved, match='No automatic retry'):
            StageJournal(selected_dir, selected_cfg, allow_provider=allow).perform(
                'embed', request, lambda value: embeddings(value, 1))
        with pytest.raises(PaidStageUnresolved, match='No automatic retry'):
            StageJournal(plain_dir, plain_cfg, allow_provider=allow, provider=provider).perform(
                'embed', request, lambda value: embeddings(value, 1))
    assert provider.calls == 1
    with pytest.raises(PermissionError, match='budget'):
        StageJournal(selected_dir, selected_cfg, allow_provider=True).perform(
            'embed', {'texts': ['another input'], 'input_type': 'document'},
            lambda value: embeddings(value, 1))
    with pytest.raises(PermissionError, match='budget'):
        StageJournal(plain_dir, plain_cfg, allow_provider=True, provider=provider).perform(
            'embed', {'texts': ['another input'], 'input_type': 'document'},
            lambda value: embeddings(value, 1))
    assert provider.calls == 1


def test_projection_does_not_claim_live_qualification_or_equate_different_requests(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    for directory, name in ((left, 'left'), (right, 'right')):
        ledger = StageJournal(directory, {'max_request_bytes': 8192, 'max_provider_calls': 1},
                              allow_provider=True, provider=FakeProvider())
        ledger.perform('embed', {'texts': [name], 'input_type': 'query'},
                       lambda value: embeddings(value, 1))
    observed = differential.compare(left, right)
    assert observed['status'] == 'offline_structure_compared' and observed['live_qualified'] is False
    assert observed['inprocess'][0]['stage_id'] != observed['selected'][0]['stage_id']
    with pytest.raises(ValueError, match='Recorded Voyage stage 1 differs'):
        differential.compare(left, right, identical_responses=True)


@pytest.mark.parametrize('change,reason', [
    (lambda ledger: ledger['recovery'].update(profile='foreign'), 'Unsupported Voyage stage ledger'),
    (lambda ledger: ledger.update(stages=[]), 'empty'),
    (lambda ledger: ledger.update(stages=['../outside']), 'path identity'),
])
def test_projection_rejects_forged_ledger_even_with_valid_checkpoint(tmp_path, change, reason):
    directory = tmp_path / 'stages'
    journal = StageJournal(directory, {'max_request_bytes': 8192, 'max_provider_calls': 1},
                           allow_provider=True, provider=FakeProvider())
    journal.perform('embed', {'texts': ['one'], 'input_type': 'query'},
                    lambda value: embeddings(value, 1))
    ledger = read_record(directory)
    change(ledger)
    RunStore(directory, existing=True).save(ledger)
    with pytest.raises(ValueError, match=reason):
        differential.stages(directory)


def test_projection_rejects_forged_stage_receipt_with_valid_checkpoint(tmp_path):
    directory = tmp_path / 'stages'
    journal = StageJournal(directory, {'max_request_bytes': 8192, 'max_provider_calls': 1},
                           allow_provider=True, provider=FakeProvider())
    journal.perform('embed', {'texts': ['one'], 'input_type': 'query'},
                    lambda value: embeddings(value, 1))
    stage_id = read_record(directory)['stages'][0]
    stage_dir = directory / stage_id
    record = read_record(stage_dir)
    record['receipt']['kind'] = 'rerank'
    RunStore(stage_dir, existing=True).save(record)
    with pytest.raises(ValueError, match='receipt disagrees'):
        differential.stages(directory)


def test_strict_projection_detects_different_valid_rate_and_cost(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    cfg = {'max_request_bytes': 8192, 'max_provider_calls': 1}
    request = {'texts': ['same input'], 'input_type': 'query'}
    for directory in (left, right):
        StageJournal(directory, cfg, allow_provider=True, provider=FakeProvider()).perform(
            'embed', request, lambda value: embeddings(value, 1))
    stage_id = read_record(right)['stages'][0]
    stage_dir = right / stage_id
    record = read_record(stage_dir)
    record['receipt']['rate_snapshot']['embedding_per_million'] *= 2
    record['receipt']['new_cost_usd'] *= 2
    RunStore(stage_dir, existing=True).save(record)
    observed = differential.compare(left, right)
    assert observed['inprocess'][0]['result_digest'] == observed['selected'][0]['result_digest']
    assert observed['inprocess'][0]['new_cost_usd'] != observed['selected'][0]['new_cost_usd']
    with pytest.raises(ValueError, match='Recorded Voyage stage 1 differs'):
        differential.compare(left, right, identical_responses=True)


def test_projection_reports_malformed_usage_as_value_error(tmp_path):
    directory = tmp_path / 'stages'
    StageJournal(directory, {'max_request_bytes': 8192, 'max_provider_calls': 1},
                 allow_provider=True, provider=FakeProvider()).perform(
        'embed', {'texts': ['one'], 'input_type': 'query'}, lambda value: embeddings(value, 1))
    stage_id = read_record(directory)['stages'][0]
    stage_dir = directory / stage_id
    record = read_record(stage_dir)
    record['result']['total_tokens'] = ['malformed']
    RunStore(stage_dir, existing=True).save(record)
    with pytest.raises(ValueError, match='invalid token usage'):
        differential.stages(directory)
