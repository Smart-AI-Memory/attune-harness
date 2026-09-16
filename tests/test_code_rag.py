"""Repository-first selection and the actual optional Attune host boundary."""

import asyncio
import json

import pytest

from attune_harness import voyage_provider
from attune_harness.cli import main
from attune_harness.retrieval_task import task_template
from attune_harness.review_store import read_record
from attune_harness.voyage_index import build_index, selection
from attune_harness.voyage_retrieval import retrieve_voyage
from attune_harness.voyage_sources import code_config, collect, config
from test_voyage import FakeProvider, repository, built, corpus


def test_repository_first_sources_and_explicit_configuration(tmp_path):
    root = repository(tmp_path / 'app', {
        'src/cart.ts': 'export const saveCart = () => true;\n',
        'tests/test_cart.py': 'def test_cart():\n    assert True\n',
        'README.md': '# Optional guidance\n',
        'schemas/cart.json': '{"type":"object"}\n',
        'config/app.yaml': 'mode: development\n',
        'receipt.json': '{"status":"passed"}',
        '.env.voyage': 'VOYAGE_API_KEY=not-a-real-key\n',
    })
    cfg = code_config(root, tmp_path / 'index', structured_paths=['schemas/cart.json', 'config/app.yaml'])
    manifest, passages = collect(cfg)
    assert {f['path'] for f in manifest['files']} == {
        'src/cart.ts', 'tests/test_cart.py', 'schemas/cart.json', 'config/app.yaml'}
    for passage in passages:
        raw = (root / passage['path']).read_bytes()
        assert raw[passage['start_byte']:passage['end_byte']].decode() == passage['excerpt']
    cfg = code_config(root, tmp_path / 'other', include_docs=True)
    assert {f['path'] for f in collect(cfg)[0]['files']} == {'src/cart.ts', 'tests/test_cart.py', 'README.md'}


@pytest.mark.parametrize('path', ['../secret.json', '/secret.json', '**/*.json', '.env/config.json', '.git/config.json'])
def test_structured_paths_cannot_expand_scope(tmp_path, path):
    with pytest.raises(ValueError):
        code_config(tmp_path, tmp_path / 'index', structured_paths=[path])


def test_legacy_normalized_config_is_unchanged(tmp_path):
    cfg = config({'schema_version': 1, 'roots': [{'repo_id': 'app', 'path': str(tmp_path)}],
                  'index_dir': str(tmp_path / 'index')}, tmp_path)
    assert 'structured_paths' not in cfg
    assert cfg['include'] == ['**/*.py', '**/*.md']
    assert config(cfg, tmp_path) == cfg


def test_code_config_cli(tmp_path, capsys):
    assert main(['code-config', '--repo', str(tmp_path), '--index-dir', str(tmp_path / 'index'),
                 '--structured-path', 'pyproject.toml']) == 0
    result = json.loads(capsys.readouterr().out)
    assert '**/*.md' not in result['include']
    assert '**/*.ts' in result['include'] and '**/*.py' in result['include']
    assert result['structured_paths'] == ['pyproject.toml']


def test_ranked_candidates_never_claim_answer_verification(built, tmp_path):
    _, selected, provider = built
    result = retrieve_voyage(selected, 'Where is the nonexistent Stripe webhook?',
                             work_dir=tmp_path / 'query', allow_provider=True, provider=provider)
    assert result['sources']
    assert result['evidence_basis']['answer_support'] == 'not_established'
    assert result['evidence_basis']['ranking_is_verification'] is False
    replay = retrieve_voyage(selected, result['query'], work_dir=tmp_path / 'query')
    assert replay['evidence_basis'] == result['evidence_basis']
    assert replay['usage']['new_provider_calls'] == 0


def test_empty_repository_evidence_is_explicit(tmp_path):
    root = repository(tmp_path / 'app', {'README.md': '# Not selected\n'})
    cfg = code_config(root, tmp_path / 'index')
    provider = FakeProvider()
    index = build_index(cfg, provider=provider)
    result = retrieve_voyage(selection(cfg, index['generation']), 'Find payment code', work_dir=tmp_path / 'query')
    assert result['status'] == 'no_results' and not result['sources']
    assert result['evidence_basis']['answer_support'] == 'insufficient_evidence'
    assert not provider.calls


@pytest.fixture
def host_plugin(built, tmp_path, monkeypatch):
    pytest.importorskip('attune.plugins.base')
    from attune_harness.attune_bridge import CodeEvidencePlugin
    root, selected, provider = built
    request = tmp_path / 'task.json'
    task = task_template(selected['config'], selected['generation'], 'Find source and its tests', max_calls=2)
    task['accepted'] = True
    request.write_text(json.dumps(task))
    monkeypatch.setenv('ATTUNE_VERSION_CHECK', '0')
    monkeypatch.setenv('ATTUNE_HOME', str(tmp_path / 'attune-home'))
    monkeypatch.setattr(voyage_provider, 'VoyageProvider', lambda: provider)
    provider.calls.clear()
    plugin = CodeEvidencePlugin(request, tmp_path / 'host-session', allow_provider=True)
    return plugin, provider, root


def test_real_attune_host_registration_dispatch_reuse_and_close(host_plugin):
    from attune.mcp.server import AttuneMCPServer
    from attune.plugins.registry import PluginRegistry
    plugin, provider, _ = host_plugin
    registry = PluginRegistry()
    with plugin.activate():
        registry.register_plugin('harness-code-rag', plugin)
        plugin.on_activate()
        server = AttuneMCPServer()
        plugin.register_mcp_tools(server)
        assert 'code_evidence_query' in server.tools
        args = {'query': 'save_cart', 'k': 2}
        first = asyncio.run(server.call_tool('code_evidence_query', args))
        assert first['status'] == 'retrieved', first
        assert 'save_cart' in first['sources'][0]['excerpt']
        second = asyncio.run(server.call_tool('code_evidence_query', args))
        assert first['sources'] == second['sources']
        assert second['usage']['new_provider_calls'] == 0
        assert [call[0] for call in provider.calls] == ['embed', 'rerank']
        exhausted = asyncio.run(server.call_tool('code_evidence_query', args))
        assert exhausted['success'] is False and 'budget' in exhausted['error']
    with pytest.raises(RuntimeError, match='inactive'):
        plugin.search(args)
    with pytest.raises(RuntimeError, match='closed'):
        with plugin.activate():
            pass
    assert read_record(plugin.scope.store.directory)['status'] == 'unresolved'


def test_host_rejects_changed_source_before_provider_call(host_plugin):
    plugin, provider, root = host_plugin
    with plugin.activate():
        (root / 'app.py').write_text('changed = True\n')
        with pytest.raises(ValueError, match='Stale index'):
            plugin.search({'query': 'save_cart', 'k': 2})
        assert not provider.calls


def test_host_refuses_caller_scope_override(host_plugin):
    plugin, provider, _ = host_plugin
    with plugin.activate():
        with pytest.raises(ValueError):
            plugin.search({'query': 'save_cart', 'k': 2, 'corpus': '/etc'})
        assert not provider.calls


def test_closed_successful_plugin_rejects_queries(host_plugin):
    plugin, provider, _ = host_plugin
    args = {'query': 'save_cart', 'k': 2}
    with plugin.activate():
        assert plugin.search(args)['sources']
    assert read_record(plugin.scope.store.directory)['status'] == 'completed'
    with pytest.raises(RuntimeError, match='inactive'):
        plugin.search(args)
    assert len(provider.calls) == 2


@pytest.mark.parametrize('error_type', [RuntimeError, KeyboardInterrupt, asyncio.CancelledError])
def test_host_context_exception_records_interruption(host_plugin, error_type):
    plugin, provider, _ = host_plugin
    error = error_type('host failed outside search')
    with pytest.raises(error_type) as raised:
        with plugin.activate():
            raise error
    assert raised.value is error
    saved = read_record(plugin.scope.store.directory)
    assert saved['status'] == 'unresolved'
    assert saved['events'] == [] and provider.calls == []
    with pytest.raises(RuntimeError, match='inactive'):
        plugin.search({'query': 'save_cart', 'k': 2})
