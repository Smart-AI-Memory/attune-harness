"""Accepted MCP sessions refuse changed authority and retain uncertain reads."""
# qualify: platform

from copy import deepcopy

import pytest

from attune_harness import mcp_server as module
from attune_harness.review_store import PersistenceError, read_record
from test_review import case, change, change_config  # noqa: F401


@pytest.fixture
def session(case, monkeypatch):
    change_config(case, lambda registry: [p.update(tools=['retrieve'])
                                         for p in registry['participants'].values()])
    scope = module.RetrievalSession(case[0], case[1], 'alpha', case[2])
    calls = []
    retrieve = module.retrieve_sources

    def observed(*args, **kwargs):
        calls.append((args, kwargs))
        return retrieve(*args, **kwargs)

    monkeypatch.setattr(module, 'retrieve_sources', observed)
    with scope.store.lease():
        scope.save()
    return scope, calls


@pytest.mark.parametrize('artifact', ['request', 'registry', 'context'])
def test_changed_accepted_authority_stops_before_dispatch(case, session, artifact):
    scope, calls = session
    before = scope.store.path.read_bytes()
    if artifact == 'request':
        change(case[0], lambda value: value['answers'].update(objective='Different accepted objective'))
        message = 'Accepted request/grants changed'
    elif artifact == 'registry':
        change(case[1], lambda value: value['participants']['alpha'].update(max_tool_calls=8))
        message = 'Accepted registry/grants changed'
    else:
        change(case[0].parent / 'context.json', lambda value: value.update(note='Changed context'))
        message = 'Accepted input changed'
    with scope.store.lease(), pytest.raises(ValueError, match=message):
        scope.invoke('harness.retrieve', {'query': 'quartz policy', 'k': 3})
    assert calls == []
    assert scope.record['events'] == []
    assert scope.store.path.read_bytes() == before


def test_authority_change_during_real_read_retains_failure_instead_of_success(case, session, monkeypatch):
    scope, calls = session
    retrieve = module.retrieve_sources

    def changed_after_read(*args, **kwargs):
        result = retrieve(*args, **kwargs)
        assert result['status'] == 'retrieved'
        change(case[0], lambda value: value.update(accepted=False))
        return result

    monkeypatch.setattr(module, 'retrieve_sources', changed_after_read)
    with scope.store.lease():
        with pytest.raises(ValueError, match='Accepted request/grants changed'):
            scope.invoke('harness.retrieve', {'query': 'quartz policy', 'k': 3})
        scope.finish()
    saved = read_record(case[2])
    assert len(calls) == 1
    assert saved['status'] == 'completed'  # Lifecycle completion does not certify the call.
    assert len(saved['events']) == 1
    event = saved['events'][0]
    assert event['state'] == 'failed' and event['error']['type'] == 'ValueError'
    assert 'result' not in event


def test_failed_completion_save_preserves_pending_receipt_and_stops_all_further_work(session, monkeypatch):
    scope, calls = session
    save = scope.store.save
    writes = []

    def fail_completion(record):
        writes.append(deepcopy(record))
        if record['events'][-1]['state'] == 'completed':
            raise PersistenceError('completion write unavailable')
        save(record)

    monkeypatch.setattr(scope.store, 'save', fail_completion)
    with scope.store.lease():
        with pytest.raises(PersistenceError, match='completion write unavailable'):
            scope.invoke('harness.retrieve', {'query': 'quartz policy', 'k': 3})
        before = scope.store.path.read_bytes()
        pending = read_record(scope.store.directory)
        assert pending['events'][0]['state'] == 'pending'
        assert 'result' not in pending['events'][0]
        with pytest.raises(PersistenceError, match='dispatch is stopped'):
            scope.invoke('harness.retrieve', {'query': 'quartz policy', 'k': 3})
        with pytest.raises(PersistenceError, match='dispatch is stopped'):
            scope.save()
        scope.finish()
        assert scope.store.path.read_bytes() == before
    assert len(calls) == 1 and len(writes) == 2
    inspected = module.inspect_session(scope.store.directory)
    assert inspected['status'] == 'unresolved' and inspected['persisted_status'] == 'running'
    assert scope.store.path.read_bytes() == before


def test_existing_session_cannot_be_recreated_to_reset_budget(case, session):
    scope, calls = session
    with scope.store.lease():
        scope.invoke('harness.retrieve', {'query': 'quartz policy', 'k': 3})
        scope.finish()
    before = scope.store.path.read_bytes()
    with pytest.raises(FileExistsError):
        module.RetrievalSession(case[0], case[1], 'alpha', case[2])
    assert len(calls) == 1
    assert scope.store.path.read_bytes() == before


def test_inspection_refuses_foreign_record_without_rewriting_it(session):
    scope, calls = session
    with scope.store.lease():
        foreign = deepcopy(scope.record)
        foreign['operation'] = 'review'
        scope.store.save(foreign)
    before = scope.store.path.read_bytes()
    with pytest.raises(ValueError, match='Unsupported MCP session record'):
        module.inspect_session(scope.store.directory)
    assert calls == []
    assert scope.store.path.read_bytes() == before
