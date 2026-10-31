"""Writer capture/check seams over synthetic inputs; no Redis or source writes."""
# qualify: platform

from copy import deepcopy
import json

import pytest

from attune_harness.memory_controls import REFUSAL as READER_REFUSAL
from attune_harness.memory_hydration_contract import MAX_BYTES, generation_prefix
from attune_harness.memory_hydration_ledger import finalize_manifest, payload_bytes
from attune_harness.memory_hydration_secrets import REFUSAL, check_secrets
from attune_harness.memory_reader import NativeReader, source_labels
from attune_harness.review_contract import canonical


ROOT = dict(id='demo', tier='curated', owner='fixture-user', scope='demo', classification='internal')
PREFIX = generation_prefix('d', 'a' * 32)
SHORT = 'sk-' + 'Ab1' * 7
ANTHROPIC = 'sk-ant-' + 'Ab1' * 31


@pytest.mark.parametrize('prefix,newline', [('', '\n'), ('\ufeff', '\r\n'), ('', '\r')])
def test_authority_parser_preserves_bom_and_newline_handling(prefix, newline):
    text = prefix + newline.join(('---', 'owner: "fixture-user"', 'scope: demo', '---', 'fixture@example.invalid'))
    assert source_labels(ROOT, text, {}) == {'owner': 'fixture-user', 'scope': 'demo'}
    check_secrets(text, source_labels(ROOT, text, {}))
    # Extracting authority must not weaken the original reader's PII policy.
    reader = NativeReader.__new__(NativeReader)
    reader.binding = 'fixture'
    with pytest.raises(ValueError, match=READER_REFUSAL):
        reader._item(ROOT, {'path': 'n.md'}, text, 'version', 'note', {})


@pytest.mark.parametrize('key', ['owner', 'scope', 'classification'])
def test_writer_authority_still_refuses_conflicting_labels(key):
    with pytest.raises(ValueError, match='conflicts with root authority'):
        source_labels(ROOT, f'---\n{key}: elsewhere\n---\nbody', {})


def test_authority_malformed_frontmatter_and_raw_labels_are_unchanged():
    with pytest.raises(ValueError, match='Unterminated source security metadata'):
        source_labels(ROOT, '---\nowner: fixture-user\n', {})
    with pytest.raises(ValueError, match='conflicts with root authority'):
        source_labels({**ROOT, 'tier': 'raw'}, 'plain', {'owner': 'elsewhere'})
    assert source_labels(ROOT, 'plain', {'future': 'retained'}) == {'future': 'retained'}


@pytest.mark.parametrize('text', [
    SHORT, ANTHROPIC, 'AKIA' + 'A1' * 8, 'ghp_' + 'Ab1' * 12,
    'xoxb-' + 'Ab1' * 4, '-----BEGIN PRIVATE KEY-----',
    '-----BEGIN RSA PRIVATE KEY-----', '-----BEGIN EC PRIVATE KEY-----',
    '-----BEGIN OPENSSH PRIVATE KEY-----', '-----BEGIN PGP PRIVATE KEY BLOCK-----',
    "password='EXAMPLEprivate'", 'redis://fixture:EXAMPLEprivate@localhost',
    'access_token=' + 'Ab1' * 9, 'api_key=' + 'EXAMPLE' + 'Ab1' * 10,
    'xoxb-EXAMPLE', 'EXAMPLE prose; -----BEGIN PRIVATE KEY-----',
    pytest.param('safe ' * 7000 + SHORT, id='late-secret-after-index-bound'),
])
def test_complete_source_secret_union_refuses_without_echoing_input(text):
    with pytest.raises(ValueError) as caught:
        check_secrets(text)
    assert str(caught.value) == REFUSAL
    assert text not in str(caught.value)


@pytest.mark.parametrize('word', ['EXAMPLE', 'xxxx', 'REDACTED', 'placeholder', 'YOUR_'])
def test_reference_placeholders_survive_only_exact_shared_token_spans(word):
    # Includes the exact Anthropic -> broad OpenAI alias, not a generic waiver.
    check_secrets('sk-ant-' + word + 'Ab1' * 31)


def test_placeholder_cannot_waive_another_match_or_a_labelled_generic_match():
    placeholder = 'AKIAIOSFODNN7EXAMPLE'
    check_secrets(placeholder)
    for text in (placeholder + ' ' + SHORT, 'api_key=' + placeholder):
        with pytest.raises(ValueError, match=REFUSAL):
            check_secrets(text)


def test_writer_does_not_promote_personal_data_or_nonblocking_shapes():
    check_secrets('fixture@example.invalid; ordinary prose')
    check_secrets('oauth_token=' + 'Ab1' * 9)
    check_secrets('Authorization: Bearer ' + 'Ab1' * 9)


@pytest.mark.parametrize('location', ['unknown-value', 'unknown-key', 'edge-extra', 'labelled-token'])
def test_complete_decoded_metadata_and_existing_label_context_are_scanned(location):
    escaped = '\\u0073' + SHORT[1:]
    if location == 'unknown-value':
        raw = '{"future":"' + escaped + '"}'
    elif location == 'unknown-key':
        raw = '{"' + escaped + '":"value"}'
    elif location == 'edge-extra':
        raw = '{"edges":[{"target_id":"n","extra":"' + escaped + '"}]}'
    else:
        raw = '{"access_token":"' + 'Ab1' * 9 + '"}'
    if location != 'labelled-token':
        check_secrets(raw)  # JSON escapes hide this short reference-only shape.
    with pytest.raises(ValueError, match=REFUSAL):
        check_secrets('', json.loads(raw))


def test_metadata_cycles_refuse_but_shared_finite_aliases_and_budget_work():
    repeated = {'future': ['ordinary']}
    check_secrets('', [repeated, repeated])
    cyclic = {}; cyclic['future'] = cyclic
    with pytest.raises(ValueError, match='cyclic alias'):
        check_secrets('', cyclic)
    def expired():
        raise TimeoutError('budget expired')
    with pytest.raises(TimeoutError, match='budget expired'):
        check_secrets('ordinary', check_budget=expired)


def manifest():
    return dict(schema_version=1, generation='a' * 32, previous=None, publication_id='b' * 32,
                binding='c' * 64, source_digest='d' * 64, context_digest='e' * 64,
                function_digest='f' * 64, hydrated_at='2026-10-25T00:00:00Z',
                counts=dict(curated=1, file=1, lesson=1, rule=1), projection_bytes=0)


def small_resources():
    def hash_record(suffix, **values):
        return dict(kind='hash', key=PREFIX + suffix, fields=values)
    return [
        hash_record('node:n', name='n', description='Aé😀\n', type='note', status='active',
                    layer='curated', tags='alpha,beta', updated_at='2026-10-25T00:00:00Z'),
        hash_record('file:c:u', name='u', description='reference', type='note', layer='file',
                    corpus='c', path='/fixture/Δ/u.md', text='full pointer é\n'),
        hash_record('lesson:1', name='lesson', description='lesson', layer='lesson', corpus='lessons',
                    path='/fixture/lessons.md', line='1', text='- **lesson**: keep all.\n'),
        hash_record('rule:r', name='r', description='rule', layer='rule', corpus='rules-tail',
                    path='/fixture/r.md', text='# rule\nKeep all.\n'),
        dict(kind='set', key=PREFIX + 'status:active', members=['n']),
        dict(kind='set', key=PREFIX + 'type:note', members=['n']),
        dict(kind='list', key=PREFIX + 'edges:n', items=[
            canonical(dict(target='file:c:u', type='RELATED_TO', description='é')),
            canonical(dict(target='n', type='', description=''))]),
        dict(kind='string', key=PREFIX + 'context', value='alpha beta'),
    ]


def test_exact_logical_bytes_count_unicode_and_manifest_itself():
    resources = small_resources()
    assert payload_bytes('d', 'a' * 32, resources) == 1040
    complete, raw = finalize_manifest('d', manifest(), resources)
    assert complete['projection_bytes'] == 1686
    assert len(raw.encode()) == 578
    assert raw == canonical(complete)
    assert len('Aé😀\n'.encode()) == 8 and len(canonical('Aé😀\n').encode()) == 23
    prior, _ = finalize_manifest('d', {**manifest(), 'previous': '9' * 32}, resources)
    assert prior['projection_bytes'] == 1716


def test_empty_projection_still_counts_context_and_marker_without_mutating_inputs():
    original = manifest(); snapshot = deepcopy(original)
    complete, _ = finalize_manifest('d', original, [dict(kind='string', key=PREFIX + 'context', value='')])
    assert complete['projection_bytes'] == 712
    assert original == snapshot


def test_sets_count_distinct_members_and_lists_count_every_ordered_item():
    resources = small_resources()
    baseline = payload_bytes('d', 'a' * 32, resources)
    resources[4]['members'].append('n')
    assert payload_bytes('d', 'a' * 32, resources) == baseline
    resources[6]['items'].append(resources[6]['items'][0])
    assert payload_bytes('d', 'a' * 32, resources) == baseline + 64


@pytest.mark.parametrize('resource', [
    dict(kind='string', key='attune:memory:context', value=''),
    dict(kind='string', key=PREFIX + 'manifest', value=''),
    dict(kind='string', key=PREFIX, value=''),
    dict(kind='string', key=PREFIX + 'context', value='\ud800'),
    dict(kind='hash', key=PREFIX + 'node:n', fields={}),
    dict(kind='hash', key=PREFIX + 'node:n', fields={'name': 1}),
    dict(kind='set', key=PREFIX + 'status:active', members=[]),
    dict(kind='list', key=PREFIX + 'edges:n', items=[]),
    dict(kind='string', key=PREFIX + 'context', value='', extra='ignored'),
])
def test_ambiguous_foreign_or_unmaterialized_resources_are_refused(resource):
    with pytest.raises(ValueError):
        payload_bytes('d', 'a' * 32, [resource])


def test_duplicate_resource_keys_are_not_silently_undercounted():
    resource = dict(kind='string', key=PREFIX + 'context', value='x')
    with pytest.raises(ValueError, match='duplicate'):
        payload_bytes('d', 'a' * 32, [resource, resource])


@pytest.mark.parametrize('last_text_bytes,accepted', [(6542, True), (6543, False)])
def test_exact_64_mib_boundary_includes_canonical_marker(last_text_bytes, accepted):
    # Shared ASCII body keeps the test allocation small; count 2,040 real keys.
    body = 'x' * 32768
    resources = []
    for i in range(2040):
        stem = f'f{i:04d}'
        resources.append(dict(kind='hash', key=PREFIX + 'file:c:' + stem, fields=dict(
            name=stem, description='', type='note', layer='file', corpus='c',
            path='/fixture/' + stem + '.md', text=body if i < 2039 else 'x' * last_text_bytes)))
    resources.append(dict(kind='string', key=PREFIX + 'context', value='alpha beta'))
    proposed = {**manifest(), 'counts': dict(curated=0, file=2040, lesson=0, rule=0)}
    if accepted:
        complete, raw = finalize_manifest('d', proposed, resources)
        assert complete['projection_bytes'] == MAX_BYTES and len(raw.encode()) == 585
    else:
        with pytest.raises(ValueError, match='64 MiB'):
            finalize_manifest('d', proposed, resources)
