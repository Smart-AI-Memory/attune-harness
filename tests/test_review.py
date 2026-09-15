import json

import pytest

from attune_harness import features
from attune_harness.cli import main
from attune_harness.review import review
from attune_harness.review_contract import accept_request, load_registry, review_form
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import PersistenceError, RunStore, inspect_run


@pytest.fixture
def case(tmp_path):
    corpus = tmp_path / 'project'
    corpus.mkdir()
    (corpus / 'guide.md').write_text('[Quartz retention policy](reference.md)', encoding='utf-8')
    (corpus / 'reference.md').write_text('Quartz retention policy is a test fixture.', encoding='utf-8')
    (tmp_path / 'context.json').write_text(json.dumps({'schema_version': 1, 'project_root': 'project'}), encoding='utf-8')
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'schema_version': 1, 'participants': {
        name: {'adapter': 'deterministic', 'tools': ['retrieve', 'verify'], 'max_turns': 3, 'max_tool_calls': 2}
        for name in ('alpha', 'beta')
    }}), encoding='utf-8')
    request = tmp_path / 'request.json'
    data = review_form(load_registry(config))['submission']
    data.update(accepted=True, answers={'objective': 'Check evidence', 'query': 'quartz retention policy',
                                      'document': 'project/guide.md', 'context': 'context.json',
                                      'corpus': 'project', 'lead': 'alpha', 'reviewer': 'beta'})
    request.write_text(json.dumps(data), encoding='utf-8')
    return request, config, tmp_path / 'run'


def change(path, update):
    data = json.loads(path.read_text(encoding='utf-8'))
    update(data)
    path.write_text(json.dumps(data), encoding='utf-8')


def change_config(case, update):
    request, config, _ = case
    change(config, update)
    change(request, lambda data: data.update(form_revision=review_form(load_registry(config))['form_revision']))


def scripted(action, observe=None):
    def factory(config, cwd):
        def exchange(raw):
            data = json.loads(raw)
            if observe:
                observe(data)
            result = action(data) if callable(action) else action
            return json.dumps({'schema_version': 1, 'request_digest': data['request_digest'], 'action': result})
        return exchange
    return factory


def test_real_two_participant_journey_and_independent_context(case):
    seen = []
    def factory(config, cwd):
        real = ReviewExchange(config, cwd)
        def exchange(raw):
            seen.append(json.loads(raw))
            return real(raw)
        return exchange
    result = review(*case, exchange_factory=factory)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == 'verified'
    assert result['verification']['result']['claims']
    assert len([event for event in result['events'] if event['kind'] == 'tool']) == 4
    assert all(item['tool_calls'] == 2 for item in result['participants'].values())
    assert inspect_run(case[2]) == result
    first_reviewer = next(item['turn'] for item in seen if item['turn']['role'] == 'reviewer')
    assert first_reviewer['history'] == []
    assert 'participants' not in first_reviewer
    assert 'Deterministic demonstration' not in json.dumps(first_reviewer)
    assert len({item['request_digest'] for item in seen}) == 6
    assert len({item['turn']['attempt_id'] for item in seen}) == 2


@pytest.mark.parametrize('content,expected', [('[broken](missing.md)', 'refuted'), ('No supported claims.', 'unknown')])
def test_completed_is_not_verified(case, content, expected):
    (case[0].parent / 'project/guide.md').write_text(content, encoding='utf-8')
    result = review(*case)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == expected
    assert result['verification']['passed'] is False


def test_no_sources_remains_visible(case):
    change(case[0], lambda data: data['answers'].update(query='nonmatchingzzzz'))
    result = review(*case)
    assert result['status'] == 'completed'
    assert result['retrieval_outcome'] == 'no_results'


@pytest.mark.parametrize('update,match', [
    (lambda d: d.update(accepted=False), 'not been explicitly'),
    (lambda d: d.update(accepted=1), 'not been explicitly'),
    (lambda d: d.update(form_revision='old'), 'Stale'),
    (lambda d: d['answers'].update(lead='unknown'), 'not in options'),
    (lambda d: d['answers'].update(reviewer='alpha'), 'distinct'),
    (lambda d: d['answers'].update(query=''), 'required'),
    (lambda d: d['answers'].update(query='x' * 4097), 'at most'),
    (lambda d: d['answers'].update(extra='ignored?'), 'Expected fields'),
    (lambda d: d.update(schema_version=True), 'integer'),
    (lambda d: d.update(extra='ignored?'), 'Expected fields'),
])
def test_invalid_intake_never_dispatches_or_creates_record(case, update, match):
    change(case[0], update)
    with pytest.raises(ValueError, match=match):
        review(*case, exchange_factory=lambda *args: pytest.fail('dispatched'))
    assert not case[2].exists()


def test_registry_change_invalidates_form(case):
    change(case[1], lambda d: d['participants']['alpha'].update(max_tool_calls=1))
    with pytest.raises(ValueError, match='Stale'):
        accept_request(case[0], load_registry(case[1]))


@pytest.mark.parametrize('adapter', ['claude', 'codex', 'command'])
def test_external_execution_requires_explicit_selection(case, adapter):
    def update(data):
        item = data['participants']['alpha']
        item.update(adapter=adapter, timeout=2)
        item.update({'command': ['never-execute']} if adapter == 'command' else {'model': 'specified-model'})
    change_config(case, update)
    with pytest.raises(features.FeatureUnavailable, match='allow-external'):
        review(*case, exchange_factory=lambda *args: pytest.fail('dispatched'))
    assert not case[2].exists()


@pytest.mark.parametrize('action,match', [
    ({'kind': 'tool', 'name': 'delete', 'arguments': {}}, 'not granted'),
    ({'kind': 'tool', 'name': 'verify', 'arguments': {'document': '/elsewhere'}}, 'Expected fields'),
    ({'kind': 'tool', 'name': 'retrieve', 'arguments': {'query': 'quartz', 'k': 3, 'corpus': '/elsewhere'}}, 'Expected fields'),
    ({'kind': 'tool', 'name': 'retrieve', 'arguments': {'query': '', 'k': 3}}, 'nonempty'),
    ({'kind': 'tool', 'name': 'retrieve', 'arguments': {'query': 'quartz', 'k': True}}, 'integer'),
])
def test_unauthorized_tool_arguments_never_invoke_tool(case, action, match):
    result = review(*case, exchange_factory=scripted(action))
    assert result['status'] == 'failed'
    assert match in result['error']['detail']
    assert not any(event['kind'] == 'tool' for event in result['events'])


def test_grants_and_budget_are_enforced(case):
    change_config(case, lambda d: d['participants']['alpha'].update(tools=['retrieve']))
    result = review(*case, exchange_factory=scripted({'kind': 'tool', 'name': 'verify', 'arguments': {}}))
    assert 'not granted' in result['error']['detail']


def test_tool_budget_stops_before_extra_invocation(case):
    change_config(case, lambda d: d['participants']['alpha'].update(max_tool_calls=1))
    result = review(*case, exchange_factory=scripted({'kind': 'tool', 'name': 'verify', 'arguments': {}}))
    assert 'tool-call budget' in result['error']['detail']
    assert len([event for event in result['events'] if event['kind'] == 'tool']) == 1


def test_turn_budget_is_terminal_without_retry(case):
    change_config(case, lambda d: d['participants']['alpha'].update(max_turns=1))
    result = review(*case, exchange_factory=scripted({'kind': 'tool', 'name': 'verify', 'arguments': {}}))
    assert 'turn budget' in result['error']['detail']
    assert len(result['participants']) == 1


def test_provider_failure_stops_and_preserves_evidence(case):
    def factory(*args):
        def fail(raw):
            raise RuntimeError('credit unavailable')
        return fail
    result = review(*case, exchange_factory=factory)
    assert result['status'] == 'failed'
    assert result['initial_retrieval']['sources']
    assert result['events'][-1]['effects'] == 'unknown'
    assert result['error']['detail'] == 'credit unavailable'
    assert inspect_run(case[2]) == result
    assert len(result['participants']) == 1


@pytest.mark.parametrize('target', ['project/guide.md', 'context.json', 'project/reference.md'])
def test_changed_inputs_cannot_complete(case, target):
    def mutate(data):
        (case[0].parent / target).write_text('changed input', encoding='utf-8')
    result = review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'ok'}, mutate))
    assert result['status'] == 'failed'
    assert 'changed' in result['error']['detail']


def test_missing_dependency_fails_before_participant(case, monkeypatch):
    original = features.version
    def version(name):
        if name == 'attune-verify':
            raise features.PackageNotFoundError(name)
        return original(name)
    monkeypatch.setattr(features, 'version', version)
    result = review(*case, exchange_factory=lambda *args: pytest.fail('dispatched'))
    assert result['status'] == 'unavailable'
    assert not result['participants']
    assert 'missing' in result['error']['detail']


def test_interruption_is_recorded_and_propagated(case):
    def stop(data):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'never'}, stop))
    saved = inspect_run(case[2])
    assert saved['status'] == 'unresolved'
    assert saved['events'][-1]['state'] == 'pending'
    assert saved['participants']['lead']['status'] == 'unresolved'


@pytest.mark.parametrize('after', [False, True])
def test_persistence_failure_never_dispatches_past_uncertain_turn(case, monkeypatch, after):
    original = RunStore.save
    calls = []
    def save(store, record):
        if record['events'] and record['events'][-1]['kind'] == 'participant_turn':
            if (record['events'][-1]['state'] == 'completed') == after:
                raise PersistenceError('disk full')
        original(store, record)
    monkeypatch.setattr(RunStore, 'save', save)
    with pytest.raises(PersistenceError):
        review(*case, exchange_factory=scripted({'kind': 'final', 'text': 'done'}, lambda d: calls.append(d)))
    assert len(calls) == int(after)
    saved = inspect_run(case[2])
    assert saved['status'] == 'unresolved'
    if after:
        assert saved['events'][-1]['state'] == 'pending'


def test_existing_run_is_never_overwritten(case):
    result = review(*case)
    with pytest.raises(FileExistsError):
        review(*case)
    assert inspect_run(case[2]) == result


def test_cli_form_review_and_inspect(case, capsys):
    request, config, folder = case
    assert main(['review-form', '--config', str(config)]) == 0
    form = json.loads(capsys.readouterr().out)
    assert form['status'] == 'ready'
    assert form['submission']['accepted'] is False
    assert 'Lead' in form['markdown']
    assert main(['review', str(request), '--config', str(config), '--run-dir', str(folder)]) == 0
    record = json.loads(capsys.readouterr().out)
    assert main(['inspect-review', str(folder)]) == 0
    assert json.loads(capsys.readouterr().out) == record


def test_cli_negative_and_failed_outcomes(case, capsys):
    request, config, folder = case
    (request.parent / 'project/guide.md').write_text('[missing](absent.md)', encoding='utf-8')
    assert main(['review', str(request), '--config', str(config), '--run-dir', str(folder)]) == 1
    assert json.loads(capsys.readouterr().out)['document_outcome'] == 'refuted'
    assert main(['inspect-review', str(folder / 'missing')]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_cli_reports_absent_forms(case, monkeypatch, capsys):
    monkeypatch.setattr(features, 'version', lambda name: 'incompatible')
    assert main(['review-form', '--config', str(case[1])]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'unavailable'


def test_reference_change_during_final_verification_cannot_complete(case, monkeypatch):
    import importlib
    module = importlib.import_module('attune_harness.review')
    original = module.verify_document
    calls = []
    def verify(*args):
        result = original(*args)
        calls.append(result)
        if len(calls) == 4:
            (case[0].parent / 'project/reference.md').write_text('changed after check', encoding='utf-8')
        return result
    monkeypatch.setattr(module, 'verify_document', verify)
    result = review(*case)
    assert result['status'] == 'failed'
    assert 'changed' in result['error']['detail']


def test_duplicate_turn_response_never_dispatches_tool_twice(case):
    previous = []
    def factory(*args):
        def exchange(raw):
            data = json.loads(raw)
            if not previous:
                previous.append(json.dumps({'schema_version': 1, 'request_digest': data['request_digest'],
                                            'action': {'kind': 'tool', 'name': 'verify', 'arguments': {}}}))
            return previous[0]
        return exchange
    result = review(*case, exchange_factory=factory)
    assert result['status'] == 'failed'
    assert 'current turn' in result['error']['detail']
    assert len([e for e in result['events'] if e['kind'] == 'tool']) == 1


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_each_native_lead_completes_feature_journey_with_injected_transport(case, monkeypatch, provider):
    from attune_harness import review_participants
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    change_config(case, lambda data: data['participants']['alpha'].update(
        adapter=provider, model='fixture-model', timeout=2))
    calls = []
    def runner(argv, prompt, **kwargs):
        calls.append(argv)
        attempt = json.loads(prompt.split('\n', 1)[1])['attempt']
        wire = attempt['task']['objective']
        output = {'text': ReviewExchange({'adapter': 'deterministic'}, kwargs['cwd'])(wire)}
        if provider == 'claude':
            raw = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,
                              'session_id': 'fixture-session', 'structured_output': output})
        else:
            raw = '\n'.join(json.dumps(item) for item in [
                {'type': 'thread.started', 'thread_id': 'fixture-session'}, {'type': 'turn.started'},
                {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(output)}},
                {'type': 'turn.completed', 'usage': {}},
            ])
        return ProcessResult(argv, 0, raw, '', None)
    monkeypatch.setattr(review_participants, 'NativeExchange',
                        lambda name, **kwargs: NativeExchange(name, **kwargs, runner=runner))
    result = review(*case, allow_external=True)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == 'verified'
    assert result['participants']['lead']['adapter'] == provider
    assert result['participants']['lead']['tool_calls'] == 2
    assert len(calls) == 3
