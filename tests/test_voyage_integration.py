"""Voyage review/recovery/provenance guards across real local index and intake."""

import json
from pathlib import Path

import pytest

from attune_harness import voyage_provider, voyage_retrieval
from attune_harness.grounded_review import sources
from attune_harness.passage_review import catalog
from attune_harness.recovery import resume_review, reconcile_review
from attune_harness.review import review
from attune_harness.review_contract import load_registry, review_form
from attune_harness.voyage_index import build_index, selection
from attune_harness.voyage_provider import PaidStageUnresolved
from attune_harness.voyage_sources import config
from test_review import case, change_config
from test_voyage import repository, FakeProvider, corpus, built


@pytest.fixture
def voyage_review(case, monkeypatch):
    request, registry_path, run = case
    root = request.parent / 'project'
    # Initialize the existing review fixture as a real, unchanged source repository.
    from test_voyage import git
    git(root, 'init')
    (root / 'code.py').write_text('def quartz_retention():\n    return "policy"\n\ndef quartz_cleanup():\n    return "retained"\n')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
    cfg = config({'schema_version': 1, 'roots': [{'repo_id': 'app', 'path': str(root)}],
                  'index_dir': str(request.parent / 'index')}, request.parent)
    provider = FakeProvider()
    index = build_index(cfg, allow_provider=True, provider=provider)
    selected = selection(cfg, index['generation'])
    selected['scope']['exclude_paths'] = [{'repo_id': 'app', 'path': 'guide.md'}]
    change_config(case, lambda d: d.update(retrieval=selected))
    monkeypatch.setattr(voyage_provider, 'VoyageProvider', lambda: provider)
    provider.calls.clear()
    return case, provider


def test_two_role_review_reuses_three_identical_retrievals(voyage_review):
    case, provider = voyage_review
    result = review(*case, allow_provider=True)
    assert result['status'] == 'completed', result.get('error')
    assert result['recovery']['profile']['version'] == 2 and 'rag' not in result['recovery']['profile']
    assert [c[0] for c in provider.calls] == ['embed', 'rerank']
    retrievals = [e['result'] for e in result['events'] if e.get('result', {}).get('operation') == 'retrieve']
    assert len(retrievals) == 3
    assert [r['usage']['new_provider_calls'] for r in retrievals] == [2, 0, 0]
    assert all(p['path'] != 'guide.md' for r in retrievals for p in r['sources'])


def test_pause_resume_without_repeated_paid_calls(voyage_review):
    case, provider = voyage_review
    paused = review(*case, allow_provider=True, max_operations=2)
    assert paused['status'] == 'paused'
    finished = resume_review(case[2], case[0], case[1], paused['checkpoint_digest'])
    assert finished['status'] == 'completed', finished.get('error')
    assert len(provider.calls) == 2


def test_resume_local_failure_after_completed_embedding(voyage_review, monkeypatch):
    case, provider = voyage_review
    real = voyage_retrieval.candidates
    def fail(*args):
        raise ValueError('local search interrupted')
    monkeypatch.setattr(voyage_retrieval, 'candidates', fail)
    failed = review(*case, allow_provider=True)
    assert failed['status'] == 'failed'
    monkeypatch.setattr(voyage_retrieval, 'candidates', real)
    finished = resume_review(case[2], case[0], case[1], failed['checkpoint_digest'], allow_provider=True)
    assert finished['status'] == 'completed', finished.get('error')
    assert [c[0] for c in provider.calls] == ['embed', 'rerank']


def test_unknown_paid_review_cannot_use_read_only_retry(voyage_review, monkeypatch):
    case, provider = voyage_review
    monkeypatch.setattr(provider, 'rerank', lambda *a: (_ for _ in ()).throw(TimeoutError()))
    result = review(*case, allow_provider=True)
    assert result['status'] == 'unresolved'
    event = next(e for e in result['events'] if e['effect_class'] == 'paid_retrieval')
    with pytest.raises(Exception, match='cannot be retried as read-only'):
        reconcile_review(case[2], result['checkpoint_digest'], event['event_id'], retry_read_only=True)
    with pytest.raises(PaidStageUnresolved):
        resume_review(case[2], case[0], case[1], result['checkpoint_digest'], allow_provider=True)


def test_distinct_passages_per_file_retain_original_offsets(built, tmp_path):
    root, selected, provider = built
    result = voyage_retrieval.retrieve_voyage(selected, 'save_cart', k=4, work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    turn = {'history': [{'result': result}], 'document': {'path': str(tmp_path / 'review.md'), 'text': 'Review the implementation.'},
            'objective': 'Check code'}
    references = sources(turn)
    assert len(references) == len(result['sources'])
    assert sum(p['path'] == 'app.py' for p in result['sources']) >= 2
    projected = catalog(turn)
    for ref in projected['reference'].values():
        raw = (root / ref['source_path']).read_bytes()
        assert raw[ref['start']:ref['end']].decode() == ref['text']
        assert ref['offset_unit'] == 'utf8-byte'


def test_scope_tampering_and_modified_source_refused(built, tmp_path):
    root, selected, provider = built
    selected['scope']['repo_ids'] = ['outside']
    with pytest.raises(ValueError, match='repository IDs'):
        voyage_retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    assert not (tmp_path / 'run').exists()


def test_self_corroboration_must_be_excluded_in_accepted_registry(voyage_review):
    case, provider = voyage_review
    change_config(case, lambda d: d['retrieval']['scope'].update(exclude_paths=[]))
    with pytest.raises(ValueError, match='exclude the reviewed document'):
        review(*case, allow_provider=True)
    assert not provider.calls
