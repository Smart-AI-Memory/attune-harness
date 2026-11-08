"""Literal four-layer projection through real, guarded synthetic capture."""
# qualify: platform

from copy import deepcopy
import pytest

from attune_harness.memory_hydration_capture import capture_sources
from attune_harness.memory_hydration_projection import generation_resources, project_snapshot
from attune_harness.memory_hydration_secrets import REFUSAL
from attune_harness.memory_redis import RedisMemory

TOKEN = 'sk-' + 'Ab1' * 7
ESCAPED = '\\u0073' + TOKEN[1:]


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.encode() if isinstance(value, str) else value)
    return path


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / 'source'
    put(root, 'nodes/n.md', '---\ncurated: true\nnode_id: n\nnode_type: note\n'
        'description: First label\ndescription: Last label\nstatus: active\n'
        'tags: alpha, beta, ,\nupdated_at: 2026-10-25T00:00:00Z\n'
        'edges_json: [{"target_id":"file:demo:a","description":"See the pointer.",'
        '"extra":"retained only in source"}]\n---\n  Full curated body.\n\nSecond paragraph.\n')
    put(root, 'nodes/old.md', '---\ncurated: true\nnode_id: old\nnode_type: note\nstatus: inactive\n---\nEarlier body.\n')
    put(root, 'notes/a.md', '---\nname: First\nname: "Last"\ndescription: A note\ntype: feedback\n'
        '---\nUse [[b]] twice [[b]], [[?later]] and [[missing]].\n')
    put(root, 'notes/b.md', 'Pointer body.\n')
    put(root, 'notes/MEMORY.md', 'Index is captured but not projected.\n')
    put(root, 'notes/deeper/not-selected.md', 'Outside direct selector.\n')
    put(root, 'lessons.md', '# Lessons\n\n- **First lesson**: Keep children.\n'
        '  Continuation.\n\n- **Second lesson**: Keep provenance.\n')
    put(root, 'rules/deeper/check.md', '---\nname: Ignored metadata\n---\n# Check inputs\nRead everything.\n')
    config = dict(schema_version=1, actor='fixture-user', owners=['fixture-user'], scopes=['demo'],
                  classifications=['internal'], profiles=['offline'], roots=[
                      dict(id='r', path=str(root.resolve()), tier='personal', owner='fixture-user',
                           scope='demo', classification='internal')])
    sources = dict(schema_version=1, sources=[dict(root_id='r', layer=layer, corpus=corpus, path=path)
        for layer, corpus, path in [('curated', 'nodes', 'nodes'), ('file', 'demo', 'notes'),
                                    ('lesson', 'lessons', 'lessons.md'), ('rule', 'rules', 'rules')]])
    return root, config, sources


def projected(corpus):
    root, config, sources = corpus
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with capture_sources(config, sources) as snapshot:
        saved = deepcopy(snapshot)
        result = project_snapshot(snapshot)
        assert snapshot == saved
    assert {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()} == before
    return result


def test_all_layer_fields_ids_memberships_edges_and_full_bodies(corpus, monkeypatch):
    root, _, _ = corpus
    def no_client(*args, **kwargs):
        pytest.fail('Pure projection constructed a Redis client owner')
    monkeypatch.setattr(RedisMemory, '__init__', no_client)
    result = projected(corpus)
    records = result['records']
    assert result['counts'] == dict(curated=2, file=2, lesson=2, rule=1)
    assert set(records) == {'n', 'old', 'file:demo:a', 'file:demo:b', 'lesson:3', 'lesson:6', 'rule:check'}
    assert records['n'] == dict(family='node', fields=dict(
        name='First label', description='Full curated body.\n\nSecond paragraph.', type='note',
        status='active', layer='curated', tags='alpha,beta', updated_at='2026-10-25T00:00:00Z'))
    assert records['file:demo:a']['fields'] == dict(name='"Last"', description='A note', type='feedback',
        layer='file', corpus='demo', path=str(root / 'notes/a.md'),
        text='\nUse [[b]] twice [[b]], [[?later]] and [[missing]].\n')
    assert records['lesson:3']['fields'] == dict(name='First lesson', description='First lesson',
        layer='lesson', corpus='lessons', path=str(root / 'lessons.md'), line='3',
        text='- **First lesson**: Keep children.\n  Continuation.')
    assert records['rule:check']['fields'] == dict(name='check', description='Check inputs', layer='rule',
        corpus='rules', path=str(root / 'rules/deeper/check.md'),
        text='---\nname: Ignored metadata\n---\n# Check inputs\nRead everything.\n')
    assert result['memberships'] == {'status:active': ['n'], 'status:inactive': ['old'], 'type:note': ['n', 'old']}
    assert result['edges'] == {'n': [dict(target='file:demo:a', type='', description='See the pointer.')],
                               'old': [], 'file:demo:a': [dict(target='file:demo:b', type='RELATED_TO')]}
    assert result['unresolved_links'] == result['forward_links'] == result['excluded_index_files'] == 1
    resources = generation_resources(result, 'demo', 'a' * 32, 'fixture context')
    prefix = 'attune:harness:hydration:demo:' + 'a' * 32 + ':'
    assert {r['key'] for r in resources} == {prefix + name for name in [
        'node:n', 'node:old', 'file:demo:a', 'file:demo:b', 'lesson:3', 'lesson:6', 'rule:check',
        'status:active', 'status:inactive', 'type:note', 'edges:n', 'edges:file:demo:a', 'context']}
    assert next(r['items'] for r in resources if r['key'] == prefix + 'edges:n') == [
        '{"description":"See the pointer.","target":"file:demo:a","type":""}']
    assert not any('extra' in r.get('fields', {}) for r in resources)


@pytest.mark.parametrize('secret', [False, True], ids=['clean', 'late-secret'])
def test_index_bound_scans_complete_pointer_first(corpus, secret):
    put(corpus[0], 'notes/b.md', 'X' * 35000 + (' ' + TOKEN if secret else ''))
    if secret:
        with pytest.raises(ValueError, match=REFUSAL):
            projected(corpus)
    else:
        result = projected(corpus)
        assert result['records']['file:demo:b']['fields']['text'] == 'X' * 32768
        assert result['index_truncations'] == dict(curated=0, file=1, lesson=0, rule=0)


@pytest.mark.parametrize('name,value', [
    ('summaries_by_path.json', '{"future":"' + ESCAPED + '","future":"safe"}'),
    ('notes/b.md', '---\nfuture: "' + ESCAPED + '"\nfuture: safe\n---\nbody'),
    ('notes/MEMORY.md', '---\nfuture: "' + ESCAPED + '"\nfuture: safe\n---\nindex'),
    ('nodes/n.md', '---\ncurated: false\nfuture: "' + ESCAPED + '"\nfuture: safe\n---\nbody'),
])
def test_unknown_overwritten_and_unprojected_records_are_still_scanned(corpus, name, value):
    pytest.importorskip('yaml')
    put(corpus[0], name, value)
    with pytest.raises(ValueError, match=REFUSAL):
        projected(corpus)


def test_safe_unknown_summary_shapes_do_not_gain_projection_fields(corpus):
    before = projected(corpus)
    put(corpus[0], 'summaries_by_path.json',
        '{"future":[0,false,null,{"contact":"reader@example.invalid"}],"future":{"other":"safe"}}')
    assert projected(corpus) == before


@pytest.mark.parametrize('value', ['{', '[]', 'null'])
def test_present_malformed_or_nonobject_summary_is_not_absence(corpus, value):
    put(corpus[0], 'summaries_by_path.json', value)
    with pytest.raises(ValueError):
        projected(corpus)


@pytest.mark.parametrize('value', [
    '{', '{"stem":"b","verdict":"unknown","digest":"fixture","who":"fixture-user","at":"fixture"}',
    '{"stem":"b","verdict":"keep","digest":"fixture","who":"fixture-user","at":""}',
    '{"stem":"b","verdict":"keep","digest":"fixture","who":"fixture-user","at":"fixture","future":"' + ESCAPED + '"}',
])
def test_verdict_sidecar_is_complete_validated_input(corpus, value):
    put(corpus[0], '.verdicts.jsonl', value)
    with pytest.raises(ValueError):
        projected(corpus)


@pytest.mark.parametrize('ident', ['file:demo:a', 'node:redirect', 'lesson:3', 'wrong/path'])
def test_curated_identity_must_roundtrip_through_existing_key_mapper(corpus, ident):
    put(corpus[0], 'nodes/n.md', '---\ncurated: true\nnode_id: ' + ident + '\n---\nbody')
    with pytest.raises(ValueError, match='identity'):
        projected(corpus)


def test_recursive_rule_stem_collision_refuses(corpus):
    put(corpus[0], 'rules/another/check.md', '# Duplicate rule\n')
    with pytest.raises(ValueError, match='duplicate record'):
        projected(corpus)


def test_ambiguous_serving_root_refuses_pointer(corpus):
    root, config, _ = corpus
    config['roots'].append({**config['roots'][0], 'id': 'other', 'path': str(root / 'notes')})
    with pytest.raises(ValueError, match='ambiguous or unservable'):
        projected(corpus)


def test_raw_newlines_remain_authoritative_while_projection_matches_textio(corpus):
    root, config, sources = corpus
    raw = b'first\r\nsecond\rthird\n'
    put(root, 'notes/b.md', raw)
    with capture_sources(config, sources) as snapshot:
        assert snapshot['entries'][('r', 'notes/b.md')]['data'] == raw
        result = project_snapshot(snapshot)
    assert result['records']['file:demo:b']['fields']['text'] == 'first\nsecond\nthird\n'
    assert (root / 'notes/b.md').read_bytes() == raw


def test_secret_context_is_checked_without_materializing_resources(corpus):
    result = projected(corpus)
    with pytest.raises(ValueError, match=REFUSAL):
        generation_resources(result, 'demo', 'a' * 32, TOKEN)


@pytest.mark.parametrize('same_corpus', [False, True])
def test_wikilinks_prefer_same_corpus_and_refuse_ambiguous_cross_corpus(corpus, same_corpus):
    root, _, sources = corpus
    for corpus_id in ('second', 'third'):
        put(root, corpus_id + '/b.md', 'A separate selected target.\n')
        sources['sources'].append(dict(root_id='r', layer='file', corpus=corpus_id, path=corpus_id))
    if same_corpus:
        result = projected(corpus)
        assert result['edges']['file:demo:a'] == [dict(target='file:demo:b', type='RELATED_TO')]
    else:
        (root / 'notes/b.md').unlink()
        with pytest.raises(ValueError, match='wikilink target is ambiguous'):
            projected(corpus)


@pytest.mark.parametrize('target', ['missing', 'rule:check', 'lesson:3'])
def test_explicit_edges_cannot_name_absent_or_unsupported_neighbors(corpus, target):
    import json
    put(corpus[0], 'nodes/n.md', '---\ncurated: true\nnode_id: n\nedges_json: '
        + json.dumps([dict(target_id=target)]) + '\n---\nA complete safe body.\n')
    with pytest.raises(ValueError, match='selected curated or file record'):
        projected(corpus)


def test_distinct_root_ids_do_not_silently_collapse_same_projected_file_id(corpus, tmp_path):
    root, config, sources = corpus
    other = tmp_path / 'other-source'
    put(other, 'a.md', 'Different authorized source with the same stem.\n')
    config['roots'].append({**config['roots'][0], 'id': 'other', 'path': str(other.resolve())})
    sources['sources'].append(dict(root_id='other', layer='file', corpus='demo', path='.'))
    with pytest.raises(ValueError, match='duplicate record identities'):
        projected(corpus)


@pytest.mark.parametrize('kind', ['int', 'float', 'timestamp', 'binary', 'bool', 'unknown'])
def test_malformed_decoding_has_a_sanitized_writer_diagnostic(corpus, kind):
    import traceback
    pytest.importorskip('yaml')
    text = '---\nfuture: !!' + kind + ' "' + ESCAPED + '"\n---\nbody'
    put(corpus[0], 'notes/b.md', text)
    with pytest.raises(ValueError) as caught:
        projected(corpus)
    assert str(caught.value) == 'Hydration source security metadata is malformed or unauthorized'
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    diagnostic = ''.join(traceback.format_exception(caught.type, caught.value, caught.tb))
    assert TOKEN not in str(caught.value) and ESCAPED not in str(caught.value)
    assert TOKEN not in diagnostic and ESCAPED not in diagnostic


@pytest.mark.parametrize('error_type', [ValueError, TypeError, OverflowError, RecursionError, TimeoutError])
def test_writer_metadata_boundary_preserves_exact_budget_exception(corpus, monkeypatch, error_type):
    from attune_harness import memory_hydration_projection as projection
    failure = error_type('synthetic original budget failure')
    def budget():
        raise failure
    def parsing_with_budget(root, text, metadata, *, _observe, _check_budget):
        _check_budget()
        pytest.fail('The original budget failure was swallowed')
    monkeypatch.setattr(projection, 'source_labels', parsing_with_budget)
    with pytest.raises(error_type) as caught:
        projection._source_labels({}, '', [], budget)
    assert caught.value is failure
