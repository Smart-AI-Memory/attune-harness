"""Repository-first selection."""

import json

import pytest

from attune_harness.cli import main
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
