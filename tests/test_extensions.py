"""Behavioral receipts for the data-only extension contract and review boundary."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from attune_harness import extensions as ext
from attune_harness.features import FeatureUnavailable
from attune_harness.review import review
from attune_harness.review_contract import load_registry
from attune_harness.recovery import resume_review
from attune_harness.review_store import PersistenceError, inspect_run
from test_review import case, change, change_config, scripted


@pytest.fixture
def bundle(tmp_path):
    source = Path(__file__).resolve().parent.parent / 'examples/extensions/plugin/src/attune_harness_evidence'
    target = tmp_path / 'bundle'
    shutil.copytree(source, target)
    return target / 'extension.json'


@pytest.fixture
def installed(bundle, tmp_path):
    directory = tmp_path / 'extension-state'
    first = ext.install(bundle, directory)
    return directory, ext.mutate(directory, first['state_digest'], 'enable')


@pytest.fixture
def extended(case, installed):
    directory, state = installed
    def update(config):
        config['extensions'] = {'evidence': {'state_dir': str(directory), 'artifact_digest': state['artifact_digest']}}
        for item in config['participants'].values():
            item['tools'] = ['evidence.search', 'verify']
    change_config(case, update)
    return case


def test_discovery_lifecycle_and_data_preservation(bundle, tmp_path):
    discovered = ext.discover(bundle)
    assert discovered['availability'] == 'declared; invocation not qualified'
    assert 'evidence.search' in discovered['skill_text']
    directory = tmp_path / 'state'
    state = ext.install(bundle, directory)
    user_data = directory / 'user-data.txt'
    user_data.write_text('keep', encoding='utf-8')
    assert state['status'] == 'disabled'
    for action, expected in [('enable', 'enabled'), ('disable', 'disabled'), ('remove', 'removed')]:
        state = ext.mutate(directory, state['state_digest'], action)
        assert state['status'] == expected
    assert state == ext.inspect_extension(directory)
    assert user_data.read_text() == 'keep' and bundle.exists()
    with pytest.raises(ValueError, match='tombstone'):
        ext.mutate(directory, state['state_digest'], 'enable')
    with pytest.raises(FileExistsError):
        ext.install(bundle, directory)


@pytest.mark.parametrize('update,error', [
    (lambda d: d.update(schema_version=2), ValueError),
    (lambda d: d.update(schema_version=True), ValueError),
    (lambda d: d.update(extra='bad'), ValueError),
    (lambda d: d.update(id='retrieve'), ValueError),
    (lambda d: d.update(id='A.B'), ValueError),
    (lambda d: d.update(version='1'), ValueError),
    (lambda d: d.update(version=1), ValueError),
    (lambda d: d.update(skill='../SKILL.md'), ValueError),
    (lambda d: d.update(skill='/SKILL.md'), ValueError),
    (lambda d: d.update(skill='other.md'), ValueError),
    (lambda d: d.update(tools={}), ValueError),
    (lambda d: d.update(tools={'bad.name': 'retrieve'}), ValueError),
    (lambda d: d.update(tools={'search': 'exec'}), FeatureUnavailable),
])
def test_invalid_bundle_rejected_before_install(bundle, tmp_path, update, error):
    change(bundle, update)
    with pytest.raises(error):
        ext.install(bundle, tmp_path / 'state')
    assert not (tmp_path / 'state').exists()


def test_duplicate_json_names_and_symlinks_refused(bundle):
    raw = bundle.read_text()
    bundle.write_text(raw.replace('"search": "retrieve"', '"search":"retrieve","search":"retrieve"'))
    with pytest.raises(ValueError):
        ext.discover(bundle)
    bundle.write_text(raw)
    skill = bundle.parent / 'SKILL.md'
    renamed = skill.rename(bundle.parent / 'other.md')
    skill.symlink_to(renamed)
    with pytest.raises(ValueError, match='symlink'):
        ext.discover(bundle)
    link = bundle.parent / 'link.json'
    link.symlink_to(bundle)
    with pytest.raises(ValueError, match='symlink'):
        ext.discover(link)


def test_stale_and_tampered_state(installed):
    directory, state = installed
    disabled = ext.mutate(directory, state['state_digest'], 'disable')
    with pytest.raises(ValueError, match='Stale'):
        ext.mutate(directory, state['state_digest'], 'enable')
    change(directory / 'record.json', lambda d: d.update(status='enabled'))
    with pytest.raises(ValueError, match='digest'):
        ext.inspect_extension(directory)
    assert disabled['status'] == 'disabled'


def test_unrelated_record_cannot_be_managed(tmp_path):
    (tmp_path / 'record.json').write_text(json.dumps({'schema_version': 1, 'operation': 'review'}))
    with pytest.raises(ValueError, match='Expected fields'):
        ext.mutate(tmp_path, 'x', 'remove')


def test_enable_needs_dependency_but_discovery_does_not(bundle, tmp_path, monkeypatch):
    state = ext.install(bundle, tmp_path / 'state')
    def missing(*args):
        raise FeatureUnavailable('missing dependency')
    monkeypatch.setattr(ext, 'require_feature', missing)
    with pytest.raises(FeatureUnavailable, match='missing'):
        ext.mutate(tmp_path / 'state', state['state_digest'], 'enable')
    assert ext.discover(bundle)['artifact_digest'] == state['artifact_digest']
    assert ext.inspect_extension(tmp_path / 'state')['status'] == 'disabled'


@pytest.mark.parametrize('changed', ['skill', 'manifest'])
def test_changed_artifact_requires_disabled_replacement(bundle, installed, changed):
    directory, state = installed
    original = state['artifact_digest']
    if changed == 'skill':
        with (bundle.parent / 'SKILL.md').open('a') as f:
            f.write('\nUpdated guidance.\n')
    else:
        change(bundle, lambda d: d.update(version='0.2.0'))
    with pytest.raises(FeatureUnavailable, match='bundle changed'):
        ext.catalog({'evidence': {'state_dir': str(directory), 'artifact_digest': original}})
    with pytest.raises(ValueError, match='disabled'):
        ext.mutate(directory, state['state_digest'], 'replace', manifest=bundle)
    state = ext.mutate(directory, state['state_digest'], 'disable')
    state = ext.mutate(directory, state['state_digest'], 'replace', manifest=bundle)
    assert state['status'] == 'disabled' and state['artifact_digest'] != original
    state = ext.mutate(directory, state['state_digest'], 'enable')
    with pytest.raises(FeatureUnavailable, match='artifact changed'):
        ext.catalog({'evidence': {'state_dir': str(directory), 'artifact_digest': original}}, enabled=True)


def test_leased_call_prevents_disable_and_preserves_real_result(extended, installed):
    directory, state = installed
    registry = load_registry(extended[1])
    from attune_harness.retrieval import retrieve_sources
    def retrieve(query, k):
        with pytest.raises(PersistenceError, match='busy'):
            ext.mutate(directory, state['state_digest'], 'disable')
        return retrieve_sources(query, extended[0].parent / 'project', k=k)
    result = ext.invoke_tool(registry['extensions'], 'evidence.search', {'query': 'quartz policy', 'k': 3}, retrieve)
    assert result['status'] == 'retrieved' and result['sources']
    assert result['extension']['artifact_digest'] == state['artifact_digest']
    state = ext.mutate(directory, state['state_digest'], 'disable')
    with pytest.raises(FeatureUnavailable, match='disabled'):
        ext.invoke_tool(registry['extensions'], 'evidence.search', {'query': 'quartz policy', 'k': 3},
                        lambda *a: pytest.fail('disabled tool invoked'))


def test_real_review_binds_skill_and_artifact(extended, installed):
    from attune_harness.review_participants import ReviewExchange
    seen = []
    def factory(config, cwd):
        exchange = ReviewExchange(config, cwd)
        def record(raw):
            seen.append(json.loads(raw)['turn'])
            return exchange(raw)
        return record
    result = review(*extended, exchange_factory=factory)
    assert result['status'] == 'completed'
    assert result['document_outcome'] == 'verified'
    assert result['recovery']['profile']['extensions'] == 1
    assert all('evidence.search' in turn['tool_contracts'] for turn in seen)
    events = [e for e in result['events'] if e['kind'] == 'tool' and e['action']['name'] == 'evidence.search']
    assert len(events) == 2
    assert all(e['result']['status'] == 'retrieved' and e['result']['extension']['artifact_digest'] == installed[1]['artifact_digest'] for e in events)
    assert seen[3]['history'] == []  # Reviewer remains independent.


@pytest.mark.parametrize('action', ['disable', 'remove'])
def test_paused_run_cannot_resume_disabled_or_removed_extension(extended, installed, action):
    directory, state = installed
    paused = review(*extended, max_operations=4)
    events = copy.deepcopy(paused['events'])
    assert paused['status'] == 'paused' and events[-1]['result']['extension']
    state = ext.mutate(directory, state['state_digest'], action)
    with pytest.raises(FeatureUnavailable, match='disabled|removed'):
        resume_review(extended[2], extended[0], extended[1], paused['checkpoint_digest'],
                      exchange_factory=lambda *a: pytest.fail('dispatched'))
    assert inspect_run(extended[2])['events'] == events
    if action == 'disable':
        ext.mutate(directory, state['state_digest'], 'enable')
        completed = resume_review(extended[2], extended[0], extended[1], paused['checkpoint_digest'])
        assert completed['status'] == 'completed' and completed['events'][:4] == events


def test_disable_during_participant_turn_stops_before_tool(extended, installed):
    directory, state = installed
    def disable(_):
        ext.mutate(directory, state['state_digest'], 'disable')
    result = review(*extended, exchange_factory=scripted(
        {'kind': 'tool', 'name': 'evidence.search', 'arguments': {'query': 'quartz policy', 'k': 3}}, disable))
    assert result['status'] == 'unavailable'
    assert not any(e['kind'] == 'tool' for e in result['events'])
    assert all(e['state'] == 'completed' for e in result['events'])


def test_upgraded_extension_refuses_old_checkpoint(bundle, extended, installed):
    paused = review(*extended, max_operations=4)
    directory, state = installed
    state = ext.mutate(directory, state['state_digest'], 'disable')
    change(bundle, lambda d: d.update(version='0.2.0'))
    state = ext.mutate(directory, state['state_digest'], 'replace', manifest=bundle)
    ext.mutate(directory, state['state_digest'], 'enable')
    with pytest.raises(FeatureUnavailable, match='artifact changed'):
        resume_review(extended[2], extended[0], extended[1], paused['checkpoint_digest'])
    change_config(extended, lambda d: d['extensions']['evidence'].update(artifact_digest=state['artifact_digest']))
    with pytest.raises(ValueError, match='changed'):
        resume_review(extended[2], extended[0], extended[1], paused['checkpoint_digest'])


@pytest.mark.parametrize('name,args', [
    ('evidence.search', {'query': 'quartz', 'k': 3, 'corpus': '/tmp'}),
    ('evidence.search', {'query': 'quartz', 'k': True}),
    ('evidence.other', {'query': 'quartz', 'k': 3}),
])
def test_extension_arguments_cannot_expand_scope(extended, name, args):
    result = review(*extended, exchange_factory=scripted({'kind': 'tool', 'name': name, 'arguments': args}))
    assert result['status'] == 'failed'
    assert not any(e['kind'] == 'tool' for e in result['events'])


def test_extension_grant_cannot_be_invented(extended):
    change(extended[1], lambda d: d['participants']['alpha'].update(tools=['evidence.unknown']))
    with pytest.raises(ValueError, match='supported names'):
        load_registry(extended[1])


def test_missing_permission_never_invokes_contribution(extended):
    change_config(extended, lambda d: d['participants']['alpha'].update(tools=['verify']))
    result = review(*extended, exchange_factory=scripted(
        {'kind': 'tool', 'name': 'evidence.search', 'arguments': {'query': 'quartz', 'k': 3}}))
    assert result['status'] == 'failed' and 'not granted' in result['error']['detail']
    assert not any(e['kind'] == 'tool' for e in result['events'])


@pytest.mark.parametrize('adapter', ['claude', 'codex'])
def test_native_leads_use_extension_via_real_translator(extended, monkeypatch, adapter):
    from attune_harness import review_participants as peers
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    change_config(extended, lambda d: d['participants']['alpha'].update(adapter=adapter, model='fixture', timeout=2))
    calls = []
    def runner(argv, prompt, **kwargs):
        wire = json.loads(prompt.split('\n', 1)[1])['attempt']['task']['objective']
        calls.append(json.loads(wire)['turn'])
        output = {'text': peers.ReviewExchange({'adapter': 'deterministic'}, kwargs['cwd'])(wire)}
        if adapter == 'claude':
            raw = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,
                              'session_id': 'fixture', 'structured_output': output})
        else:
            raw = '\n'.join(json.dumps(item) for item in [
                {'type': 'thread.started', 'thread_id': 'fixture'}, {'type': 'turn.started'},
                {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(output)}},
                {'type': 'turn.completed', 'usage': {}}])
        return ProcessResult(argv, 0, raw, '', None)
    monkeypatch.setattr(peers, 'NativeExchange', lambda name, **kwargs: NativeExchange(name, **kwargs, runner=runner))
    result = review(*extended, allow_external=True)
    assert result['status'] == 'completed' and result['document_outcome'] == 'verified'
    assert len(calls) == 3 and 'skill_text' in calls[0]['tool_contracts']['evidence.search']
    assert calls[1]['history'][0]['result']['extension']['tool'] == 'evidence.search'


def test_extension_profile_marker_is_required_on_resume(extended):
    from attune_harness.review_store import RunStore
    paused = review(*extended, max_operations=1)
    paused['recovery']['profile'].pop('extensions')
    RunStore(extended[2], existing=True).save(paused)
    with pytest.raises(FeatureUnavailable, match='profile'):
        resume_review(extended[2], extended[0], extended[1], paused['checkpoint_digest'])


def test_cli_lifecycle_routing(bundle, tmp_path, capsys):
    from attune_harness.cli import main
    directory = tmp_path / 'state'
    assert main(['extension', 'discover', str(bundle)]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'ready'
    assert main(['extension', 'install', str(bundle), '--state-dir', str(directory)]) == 0
    state = json.loads(capsys.readouterr().out)
    assert main(['extension', 'enable', '--state-dir', str(directory), '--checkpoint', state['state_digest']]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state['status'] == 'enabled'
    assert main(['extension', 'inspect', '--state-dir', str(directory)]) == 0
    assert json.loads(capsys.readouterr().out) == state
    assert main(['extension', 'disable', '--state-dir', str(directory), '--checkpoint', 'stale']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_binding_identity_collision_rejected(extended):
    change(extended[1], lambda d: d['extensions'].update(other=d['extensions']['evidence']))
    with pytest.raises(ValueError, match='collides'):
        load_registry(extended[1])


@pytest.mark.parametrize('bindings', [[], {}, {'evidence': {'state_dir': '.', 'artifact_digest': 'bad'}}])
def test_malformed_registration_references_refused(case, bindings):
    change(case[1], lambda d: d.update(extensions=bindings))
    with pytest.raises(ValueError):
        load_registry(case[1])


def test_removed_bundle_still_inspectable_and_removable(installed, bundle):
    directory, state = installed
    shutil.rmtree(bundle.parent)
    assert ext.inspect_extension(directory) == state
    removed = ext.mutate(directory, state['state_digest'], 'remove')
    assert removed['status'] == 'removed'


def test_mutation_during_real_call_cannot_emit_current_evidence(extended, installed, bundle):
    bindings = load_registry(extended[1])['extensions']
    from attune_harness.retrieval import retrieve_sources
    def changed(query, k):
        result = retrieve_sources(query, extended[0].parent / 'project', k=k)
        (bundle.parent / 'SKILL.md').write_text('Changed in place', encoding='utf-8')
        return result
    with pytest.raises(FeatureUnavailable, match='bundle changed'):
        ext.invoke_tool(bindings, 'evidence.search', {'query': 'quartz policy', 'k': 3}, changed)


def test_disabled_after_final_verification_is_not_completed(extended, installed, monkeypatch):
    import importlib
    module = importlib.import_module('attune_harness.review')
    real = module.verify_document
    directory, state = installed
    count = 0
    def verify(*args):
        nonlocal count
        result = real(*args)
        count += 1
        if count == 4:  # preflight, lead, reviewer, final
            ext.mutate(directory, state['state_digest'], 'disable')
        return result
    monkeypatch.setattr(module, 'verify_document', verify)
    result = review(*extended)
    assert result['status'] == 'unavailable' and count == 4


def test_native_extension_protocol_is_carried_in_outer_contract(extended, monkeypatch):
    from attune_harness import review_participants as peers
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    change_config(extended, lambda d: d['participants']['alpha'].update(adapter='claude', model='fixture', timeout=2))
    def runner(argv, prompt, **kwargs):
        task = json.loads(prompt.split('\n', 1)[1])['attempt']['task']
        assert 'Extension tool names' in task['requirements'][0]
        wire = task['objective']
        output = {'text': peers.ReviewExchange({'adapter': 'deterministic'}, kwargs['cwd'])(wire)}
        return ProcessResult(argv, 0, json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,
                          'session_id': 'fixture', 'structured_output': output}), '', None)
    monkeypatch.setattr(peers, 'NativeExchange', lambda name, **kwargs: NativeExchange(name, **kwargs, runner=runner))
    assert review(*extended, allow_external=True)['status'] == 'completed'
