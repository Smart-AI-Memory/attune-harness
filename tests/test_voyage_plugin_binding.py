"""Offline behavioral boundaries for accepted Voyage plugin selection."""
# ruff: noqa: F811 -- imported pytest fixtures are injected by name.

import copy
import json
import os
from pathlib import Path
import zipfile

import pytest

from attune_harness import extensions as ext, plugin_runtime
from attune_harness.features import FeatureUnavailable
from attune_harness.review_contract import digest
from attune_harness.voyage_index import build_index, index_plan
from attune_harness.voyage_plugin import inspect_selection
from attune_harness.voyage_provider import StageJournal
from attune_harness.voyage_retrieval import retrieve_voyage
from attune_harness.voyage_sources import config
from test_extensions import bundle  # noqa: F401
from test_plugin_signing import base_signer, signers, signer, sign_bundle  # noqa: F401
from test_review import change
from test_voyage import corpus  # noqa: F401

TOOL = {'binding': 'run', 'entry': 'main', 'input_schema': {'type': 'object'},
        'output_schema': {'type': 'object'}}
GRANT = {'secrets': ['VOYAGE_API_KEY'], 'scratch': True, 'time': 60,
         'output': {'result': 65536, 'diagnostics': 8192}}
DECLARES = {'imports': ['voyageai', 'lancedb'], 'network': ['api.voyageai.com']}
TOOLS = {'embed': 'embed', 'rerank': 'rerank', 'index': 'index'}


@pytest.fixture
def voyage_bundle(bundle, signer, tmp_path, monkeypatch, request):
    with zipfile.ZipFile(bundle.parent / 'plugin.zip', 'w') as stream:
        stream.writestr('main.py', 'pass\n')
    declares = copy.deepcopy(getattr(request, 'param', DECLARES))
    change(bundle, lambda d: d.update(id='voyage', code='plugin.zip',
                                     tools={name: copy.deepcopy(TOOL) for name in TOOLS.values()},
                                     grants=copy.deepcopy(GRANT), declares=declares))
    # This test checks the binding to the existing closure mechanism without
    # installing either paid SDK in the test interpreter.
    closure = {'versions': {'voyageai': '0.5.0', 'lancedb': '0.38.0'},
               'top_levels': ['voyageai', 'lancedb'], 'roots': [], 'files': [], 'metadata': {}}
    monkeypatch.setattr(plugin_runtime, 'resolve_imports', lambda _: copy.deepcopy(closure))
    artifact = sign_bundle(bundle, signer)
    state_dir = tmp_path / 'plugin-state'
    state = ext.install(bundle, state_dir)
    section = {'voyage': {'state_dir': str(state_dir), 'artifact_digest': artifact,
                          'grant': copy.deepcopy(GRANT)}, 'signers': [signer.entry]}
    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
    state = ext.mutate(state_dir, state['state_digest'], 'enable', registry=registry)
    return registry, section, state_dir, state


def selected(cfg, registry, *, pin=True):
    raw = copy.deepcopy(cfg)
    raw['voyage_plugin'] = {'registry': str(registry), 'extension_id': 'voyage', 'tools': TOOLS}
    if pin:
        raw['voyage_plugin']['registry_digest'] = digest(ext._registry_section(registry))
    return config(raw, Path.cwd())


def test_absent_selection_preserves_normalization_and_digest(corpus):
    _, cfg, _ = corpus
    normalized = config(cfg, Path.cwd())
    assert normalized == cfg
    assert digest(normalized) == digest(cfg)
    assert 'voyage_plugin' not in index_plan(cfg)


def test_draft_plan_reports_observed_digest_without_acceptance_or_writes(corpus, voyage_bundle):
    _, cfg, _ = corpus
    registry, _, _, _ = voyage_bundle
    draft = selected(cfg, registry, pin=False)
    before = registry.read_bytes()
    plan = index_plan(draft)
    assert plan['observed_registry_digest'] == digest(ext._registry_section(registry))
    assert plan['acceptance'] == 'unpinned' and plan['dispatch_available'] is False
    assert 'registry_digest' not in draft['voyage_plugin']
    assert registry.read_bytes() == before
    assert not Path(cfg['index_dir']).exists()


def test_pinned_plan_validates_selected_bundle_and_ignores_other_bundle(corpus, voyage_bundle):
    _, cfg, _ = corpus
    registry, section, _, _ = voyage_bundle
    section['other'] = {'state_dir': str(registry.parent / 'never-opened'), 'artifact_digest': 'a' * 64}
    registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
    bound = selected(cfg, registry)
    result = index_plan(bound)
    assert result['acceptance'] == 'pinned' and result['dispatch_available'] is False
    assert result['extension_id'] == 'voyage' and result['artifact_digest'] == section['voyage']['artifact_digest']
    assert not (registry.parent / 'never-opened').exists()


@pytest.mark.parametrize('draft', [True, False])
def test_selected_dispatch_refuses_before_index_work_or_stage_state(corpus, voyage_bundle, draft):
    _, cfg, provider = corpus
    registry, section, _, _ = voyage_bundle
    bound = selected(cfg, registry, pin=not draft)
    if not draft:
        section['revoked'] = ['a' * 64]  # unrelated section change breaks the pin
        registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
    stage = registry.parent / 'new-stage'
    work = registry.parent / 'new-retrieval'
    with pytest.raises(FeatureUnavailable, match='unpinned|digest changed'):
        build_index(bound, allow_provider=True, provider=provider)
    with pytest.raises(FeatureUnavailable, match='unpinned|digest changed'):
        StageJournal(stage, bound, allow_provider=True, provider=provider)
    selection = {'config': bound, 'config_digest': digest(bound), 'generation': 'a' * 64,
                 'scope': {'repo_ids': ['app'], 'exclude_paths': []}}
    with pytest.raises(FeatureUnavailable, match='unpinned|digest changed'):
        retrieve_voyage(selection, 'query', work_dir=work, allow_provider=True, provider=provider)
    assert not Path(cfg['index_dir']).exists() and not stage.exists() and not work.exists()
    assert provider.calls == []


def test_matching_pin_refuses_high_level_paths_and_injected_provider(corpus, voyage_bundle):
    _, cfg, provider = corpus
    registry, _, _, _ = voyage_bundle
    bound = selected(cfg, registry)
    with pytest.raises(FeatureUnavailable, match='dispatch is unavailable'):
        build_index(bound, allow_provider=True, provider=provider)
    with pytest.raises(FeatureUnavailable, match='signed plugin tool'):
        StageJournal(registry.parent / 'stages', bound, allow_provider=True, provider=provider)
    with pytest.raises(FeatureUnavailable, match='dispatch is unavailable'):
        retrieve_voyage({'config': bound}, 'query', work_dir=registry.parent / 'work',
                        allow_provider=True, provider=provider)
    assert provider.calls == [] and not Path(cfg['index_dir']).exists()
    assert not (registry.parent / 'stages').exists() and not (registry.parent / 'work').exists()


@pytest.mark.parametrize('edit,reason', [
    (lambda s: s['voyage']['grant'].pop('scratch'), 'scratch'),
    (lambda s: s['voyage']['grant'].update(secrets=['OTHER_KEY']), 'secrets exceeds'),
    (lambda s: s.update(revoked=[s['voyage']['artifact_digest']]), 'revocation'),
])
def test_refreshed_pin_still_checks_grant_and_revocation(corpus, voyage_bundle, edit, reason):
    _, cfg, _ = corpus
    registry, section, _, _ = voyage_bundle
    edit(section)
    registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
    with pytest.raises(FeatureUnavailable, match=reason):
        inspect_selection(selected(cfg, registry)['voyage_plugin'])


def test_disabled_selected_bundle_and_wrong_role_refuse(corpus, voyage_bundle):
    _, cfg, _ = corpus
    registry, _, state_dir, state = voyage_bundle
    bound = selected(cfg, registry)
    bound['voyage_plugin']['tools']['index'] = 'missing'
    with pytest.raises(FeatureUnavailable, match='index must name'):
        inspect_selection(bound['voyage_plugin'])
    ext.mutate(state_dir, state['state_digest'], 'disable')
    with pytest.raises(FeatureUnavailable, match='disabled'):
        inspect_selection(selected(cfg, registry)['voyage_plugin'])


def test_closure_drift_refuses_pinned_selection(corpus, voyage_bundle, monkeypatch):
    _, cfg, _ = corpus
    registry, _, _, _ = voyage_bundle
    bound = selected(cfg, registry)
    monkeypatch.setattr(plugin_runtime, 'resolve_imports', lambda _: {
        'versions': {'voyageai': 'different'}, 'top_levels': [], 'roots': [],
        'files': [], 'metadata': {}})
    with pytest.raises(FeatureUnavailable, match='closure changed'):
        inspect_selection(bound['voyage_plugin'])


@pytest.mark.parametrize('voyage_bundle,reason', [
    ({'imports': ['voyageai', 'lancedb'], 'network': ['other.example']}, 'exactly api.voyageai.com'),
    ({'imports': ['voyageai'], 'network': ['api.voyageai.com']}, 'declare voyageai and lancedb'),
], indirect=['voyage_bundle'])
def test_signed_bundle_wrong_declarations_refuse(corpus, voyage_bundle, reason):
    _, cfg, _ = corpus
    registry, _, _, _ = voyage_bundle
    with pytest.raises(FeatureUnavailable, match=reason):
        inspect_selection(selected(cfg, registry)['voyage_plugin'])


@pytest.mark.parametrize('tamper,reason', [
    ('signature', 'signature|artifact.sig'),
    ('artifact', 'bundle changed'),
])
def test_tampered_signed_bundle_refuses(corpus, voyage_bundle, tamper, reason):
    _, cfg, _ = corpus
    registry, _, _, _ = voyage_bundle
    manifest = registry.parent / 'bundle' / 'extension.json'
    if tamper == 'signature':
        (manifest.parent / 'artifact.sig').write_bytes(b'not a signature')
    else:
        with zipfile.ZipFile(manifest.parent / 'plugin.zip', 'w') as stream:
            stream.writestr('main.py', 'print("changed")\n')
    with pytest.raises(FeatureUnavailable, match=reason):
        inspect_selection(selected(cfg, registry)['voyage_plugin'])


def test_plan_never_reads_secret_or_invokes_provider_or_runner(corpus, voyage_bundle, monkeypatch):
    _, cfg, provider = corpus
    registry, _, _, _ = voyage_bundle
    class GuardedEnvironment(dict):
        def __getitem__(self, key):
            if key == 'VOYAGE_API_KEY':
                pytest.fail('plan read VOYAGE_API_KEY')
            return super().__getitem__(key)
        def get(self, key, default=None):
            if key == 'VOYAGE_API_KEY':
                pytest.fail('plan read VOYAGE_API_KEY')
            return super().get(key, default)
    monkeypatch.setattr(os, 'environ', GuardedEnvironment(os.environ))
    monkeypatch.setattr(plugin_runtime, 'run', lambda *a, **kw: pytest.fail('plugin runner called'))
    from attune_harness.voyage_provider import VoyageProvider
    monkeypatch.setattr(VoyageProvider, '__init__', lambda self: pytest.fail('Voyage client constructed'))
    plan = index_plan(selected(cfg, registry))
    assert plan['acceptance'] == 'pinned' and plan['provider_calls'] == 0
    assert provider.calls == []


def test_selection_normalization_is_pure_and_rejects_aliases(corpus, voyage_bundle):
    _, cfg, _ = corpus
    registry, _, _, _ = voyage_bundle
    raw = copy.deepcopy(cfg)
    raw['voyage_plugin'] = {'registry': registry.name, 'extension_id': 'voyage',
                            'tools': copy.deepcopy(TOOLS)}
    original = copy.deepcopy(raw)
    normalized = config(raw, registry.parent)
    assert raw == original
    assert normalized['voyage_plugin']['registry'] == str(registry.resolve())
    raw['voyage_plugin']['tools']['index'] = 'embed'
    with pytest.raises(ValueError, match='distinct'):
        config(raw, registry.parent)
