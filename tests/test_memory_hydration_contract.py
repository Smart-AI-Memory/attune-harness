"""Proposed hydration boundaries, using synthetic records only."""
# qualify: platform

from copy import deepcopy
import json
from pathlib import Path

import pytest

from attune_harness.memory_hydration_contract import (
    generation_index, generation_prefix, namespace, validate_manifest, validate_sources,
)

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/hydration/contract.json').read_text(encoding='utf-8'))
ROOT_IDS = {'curated', 'personal', 'reference'}


def test_synthetic_contract_covers_all_layers_and_root_identities():
    sources = validate_sources(FIXTURE['sources'], ROOT_IDS)
    assert {source['layer'] for source in sources} == {'curated', 'file', 'lesson', 'rule'}
    assert len(sources) == 4
    manifest = FIXTURE['manifest']
    assert validate_manifest(json.dumps(manifest), manifest['binding'], manifest['function_digest']) == manifest
    base = namespace('demo')
    prefix = generation_prefix('demo', manifest['generation'])
    assert base == 'attune:harness:hydration:demo:'
    assert prefix == base + manifest['generation'] + ':'
    assert generation_index('demo', manifest['generation']) == 'idx:attune_harness_memory:demo:' + manifest['generation']
    assert not prefix.startswith('attune:memory:')


@pytest.mark.parametrize('dataset', ['', '../escape', 'other:dataset', 'x' * 33, 'a\n', 'é', 1, True])
def test_cache_names_cannot_select_foreign_namespaces(dataset):
    with pytest.raises(ValueError):
        namespace(dataset)


@pytest.mark.parametrize('generation', ['', 'A' * 32, 'a' * 31, 'a' * 33, '../escape', 1])
def test_generation_name_is_opaque_and_bounded(generation):
    with pytest.raises(ValueError):
        generation_prefix('demo', generation)


@pytest.mark.parametrize('field,value', [
    ('schema_version', True), ('schema_version', 2), ('generation', 'foreign:key'),
    ('previous', 'bad'), ('previous', 'a' * 32), ('publication_id', 'bad'),
    ('binding', '0' * 64), ('source_digest', 'broken'), ('context_digest', None),
    ('function_digest', '0' * 64), ('hydrated_at', '2026-10-24'),
    ('hydrated_at', '2026-10-24T12:00:00+01:00'), ('hydrated_at', 'not a date'),
    ('projection_bytes', True), ('projection_bytes', -1), ('projection_bytes', 64 * 1024 * 1024 + 1),
    ('counts', {'curated': 2}), ('counts', {'curated': True, 'file': 1, 'lesson': 1, 'rule': 1}),
    ('counts', {'curated': -1, 'file': 1, 'lesson': 1, 'rule': 1}),
])
def test_malformed_foreign_or_incompatible_manifest_is_refused(field, value):
    expected = FIXTURE['manifest']
    record = {**expected, field: value}
    with pytest.raises(ValueError):
        validate_manifest(json.dumps(record), expected['binding'], expected['function_digest'])


@pytest.mark.parametrize('raw', ['null', '[]', '{}', '{"schema_version":1,"schema_version":1}', 'x' * 65537])
def test_manifest_parser_does_not_accept_ambiguous_or_unbounded_input(raw):
    manifest = FIXTURE['manifest']
    with pytest.raises(ValueError):
        validate_manifest(raw, manifest['binding'], manifest['function_digest'])


@pytest.mark.parametrize('field,value', [
    ('root_id', 'unconfigured'), ('layer', 'raw'), ('layer', 'unknown'),
    ('corpus', 'foreign:corpus'), ('path', '../escape'), ('path', '/absolute'),
    ('path', 'C:\\absolute'), ('path', '..\\escape'), ('path', 'C:relative'),
    ('path', ''), ('path', 'part/../escape'), ('path', 1),
])
def test_source_mapping_never_expands_root_authority(field, value):
    sources = deepcopy(FIXTURE['sources'])
    sources['sources'][0][field] = value
    with pytest.raises(ValueError):
        validate_sources(sources, ROOT_IDS)


def test_source_schema_and_duplicate_mapping_are_refused():
    for value in (None, {}, {'schema_version': True, 'sources': []},
                  {'schema_version': 1, 'sources': []}, {**FIXTURE['sources'], 'extra': True}):
        with pytest.raises(ValueError):
            validate_sources(value, ROOT_IDS)
    duplicate = deepcopy(FIXTURE['sources'])
    duplicate['sources'].append(deepcopy(duplicate['sources'][0]))
    with pytest.raises(ValueError):
        validate_sources(duplicate, ROOT_IDS)
    lesson = deepcopy(FIXTURE['sources'])
    lesson['sources'][2]['path'] = '.'
    with pytest.raises(ValueError):
        validate_sources(lesson, ROOT_IDS)
