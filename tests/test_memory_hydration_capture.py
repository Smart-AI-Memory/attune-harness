"""Real guarded synthetic source capture; no Redis or personal source access."""
# qualify: platform

from copy import deepcopy
import os
from pathlib import Path

import pytest

from attune_harness import memory_hydration_capture as capture
from attune_harness.memory_reader import NativeReader


def config_for(*paths):
    return dict(schema_version=1, actor='fixture-user', owners=['fixture-user'], scopes=['demo'],
                classifications=['internal'], profiles=['offline'], roots=[
                    dict(id=rid, path=str(path.resolve()), tier='personal', owner='fixture-user',
                         scope='demo', classification='internal') for rid, path in paths])


def sources_for(*rows):
    return dict(schema_version=1, sources=[dict(root_id=rid, layer=layer, corpus=corpus, path=path)
                                         for rid, layer, corpus, path in rows])


def put(root, name, data=b'ordinary'):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def test_exact_selector_inventories_capture_full_sources_and_sidecars(tmp_path):
    root = tmp_path / 'source'
    originals = [put(root, name, data) for name, data in [
        ('nodes/n.md', b'curated body'), ('notes/a.md', b'pointer body'),
        ('notes/MEMORY.md', b'index still captured'), ('notes/nested/ignored.md', b'not selected'),
        ('rules/nested/r.md', b'# Rule\ncomplete'), ('lessons.md', b'- **One**: complete'),
        ('unrelated/deep/ignored.md', b'not selected'), ('summaries_by_path.json', b'{}'),
    ]]
    before = {str(p): p.read_bytes() for p in originals}
    config = config_for(('r', root))
    sources = sources_for(('r', 'curated', 'nodes', 'nodes'), ('r', 'file', 'notes', 'notes'),
                          ('r', 'lesson', 'lessons', 'lessons.md'), ('r', 'rule', 'rules', 'rules'))
    with capture.capture_sources(config, sources) as snapshot:
        inventories = {s['layer']: names for s, names in zip(snapshot['sources'], snapshot['inventories'])}
        assert inventories == dict(curated=['nodes/n.md'], file=['notes/MEMORY.md', 'notes/a.md'],
                                   lesson=['lessons.md'], rule=['rules/nested/r.md'])
        assert snapshot['files'] == 6
        assert snapshot['entries'][('r', '.verdicts.jsonl')]['present'] is False
        assert snapshot['entries'][('r', 'notes/a.md')]['data'] == b'pointer body'
        assert snapshot['bytes'] == sum(len(before[str(root / name)]) for name in (
            'nodes/n.md', 'notes/MEMORY.md', 'notes/a.md', 'lessons.md',
            'rules/nested/r.md', 'summaries_by_path.json'))
    assert {str(p): p.read_bytes() for p in originals} == before


def test_overlap_reads_and_charges_one_logical_entry_but_preserves_roles(tmp_path):
    root = tmp_path / 'source'; put(root, 'rules/nested/r.md', b'rule')
    sources = sources_for(('r', 'rule', 'first', 'rules'), ('r', 'rule', 'second', 'rules/nested'))
    with capture.capture_sources(config_for(('r', root)), sources) as snapshot:
        assert snapshot['files'] == 1 and snapshot['bytes'] == 4
        assert snapshot['inventories'] == [['rules/nested/r.md'], ['rules/nested/r.md']]
        assert len([entry for entry in snapshot['entries'].values() if entry['present']]) == 1


def test_distinct_root_ids_are_not_collapsed_by_path_or_content(tmp_path):
    root = tmp_path / 'source'; put(root, 'a.md', b'same')
    sources = sources_for(('a', 'file', 'first', '.'), ('b', 'file', 'second', '.'))
    with capture.capture_sources(config_for(('a', root), ('b', root)), sources) as snapshot:
        assert snapshot['files'] == 2 and snapshot['bytes'] == 8
        assert snapshot['entries'][('a', 'a.md')]['data'] == snapshot['entries'][('b', 'a.md')]['data']


@pytest.mark.parametrize('layer,path', [('file', 'missing'), ('rule', 'missing'), ('lesson', 'missing.md')])
def test_missing_required_selection_does_not_become_empty(tmp_path, layer, path):
    root = tmp_path / 'source'; root.mkdir()
    with pytest.raises((ValueError, OSError)):
        with capture.capture_sources(config_for(('r', root)), sources_for(('r', layer, 'demo', path))):
            pytest.fail('Missing required selection was admitted')


def test_empty_selected_directory_has_private_identity_evidence(tmp_path):
    root = tmp_path / 'source'; (root / 'empty').mkdir(parents=True)
    config = config_for(('r', root)); sources = sources_for(('r', 'file', 'demo', 'empty'))
    with capture.capture_sources(config, sources) as first:
        assert first['files'] == first['bytes'] == 0 and first['inventories'] == [[]]
    (root / 'empty').rename(tmp_path / 'retained-empty')
    (root / 'empty').mkdir()
    with capture.capture_sources(config, sources) as second:
        assert first['binding'] == second['binding'] and first['inventories'] == second['inventories']
        assert first['entries'] == second['entries']
        assert first['observations']['r']['directories']['empty'] != second['observations']['r']['directories']['empty']


def test_optional_absence_is_distinct_from_empty_and_counts_even_without_bytes(tmp_path):
    root = tmp_path / 'source'; root.mkdir()
    config = config_for(('r', root)); sources = sources_for(('r', 'file', 'demo', '.'))
    with capture.capture_sources(config, sources) as absent:
        assert absent['files'] == absent['bytes'] == 0
    put(root, '.verdicts.jsonl', b'')
    with capture.capture_sources(config, sources) as present:
        assert present['files'] == 1 and present['bytes'] == 0
        assert present['entries'][('r', '.verdicts.jsonl')]['present']
        assert present['entries'] != absent['entries']


def test_all_root_barrier_catches_earlier_root_change_before_combined_yield(tmp_path, monkeypatch):
    a, b = tmp_path / 'a', tmp_path / 'b'
    put(a, 'a.md'); put(b, 'b.md')
    config = config_for(('a', a), ('b', b))
    sources = sources_for(('a', 'file', 'a', '.'), ('b', 'file', 'b', '.'))
    original = NativeReader._root
    def root(self, rid):
        result = original(self, rid)
        if rid == 'b':
            put(a, '.verdicts.jsonl', b'')
        return result
    monkeypatch.setattr(NativeReader, '_root', root)
    entered = False
    with pytest.raises((ValueError, OSError)):
        with capture.capture_sources(config, sources):
            entered = True
    assert not entered


@pytest.mark.parametrize('change', ['addition', 'sidecar', 'config', 'selectors', 'snapshot'])
def test_consumer_change_refuses_clean_completion(tmp_path, change):
    root = tmp_path / 'source'; put(root, 'a.md')
    config = config_for(('r', root)); sources = sources_for(('r', 'file', 'demo', '.'))
    with pytest.raises((ValueError, OSError)):
        with capture.capture_sources(config, sources) as snapshot:
            if change == 'addition': put(root, 'new.md')
            elif change == 'sidecar': put(root, '.verdicts.jsonl', b'')
            elif change == 'config': config['owners'].append('changed')
            elif change == 'selectors': sources['sources'][0]['corpus'] = 'changed'
            else: snapshot['entries'][('r', 'a.md')]['data'] = b'changed'


@pytest.mark.parametrize('extra_sidecar,accepted', [(False, True), (True, False)])
def test_present_sidecars_share_file_limit_with_selected_records(tmp_path, monkeypatch, extra_sidecar, accepted):
    root = tmp_path / 'source'; put(root, 'a.md'); put(root, 'b.md')
    put(root, 'summaries_by_path.json', b'')
    if extra_sidecar: put(root, '.verdicts.jsonl', b'')
    monkeypatch.setattr(capture, 'SNAPSHOT_FILES', 3)
    config = config_for(('r', root)); sources = sources_for(('r', 'file', 'demo', '.'))
    if accepted:
        with capture.capture_sources(config, sources) as snapshot: assert snapshot['files'] == 3
    else:
        with pytest.raises(ValueError):
            with capture.capture_sources(config, sources): pytest.fail('Exceeded file limit')


@pytest.mark.parametrize('extra_byte,accepted', [(b'', True), (b'x', False)])
def test_bytes_are_aggregated_across_roots_and_zero_remaining_allows_empty(tmp_path, monkeypatch, extra_byte, accepted):
    a, b = tmp_path / 'a', tmp_path / 'b'
    put(a, 'a.md', b'aa'); put(b, 'b.md', b'b'); put(b, 'last.md', extra_byte)
    monkeypatch.setattr(capture, 'SNAPSHOT_BYTES', 3)
    config = config_for(('a', a), ('b', b))
    sources = sources_for(('a', 'file', 'a', '.'), ('b', 'file', 'b', '.'))
    if accepted:
        with capture.capture_sources(config, sources) as snapshot:
            assert snapshot['files'] == 3 and snapshot['bytes'] == 3
    else:
        with pytest.raises(ValueError):
            with capture.capture_sources(config, sources): pytest.fail('Exceeded byte limit')


@pytest.mark.parametrize('excess', [0, 1])
def test_actual_per_file_8_mib_boundary(tmp_path, excess):
    root = tmp_path / 'source'; put(root, 'a.md', b'x' * (capture.FILE_LIMIT + excess))
    config = config_for(('r', root)); sources = sources_for(('r', 'file', 'demo', '.'))
    if excess:
        with pytest.raises(ValueError):
            with capture.capture_sources(config, sources): pytest.fail('Oversized source admitted')
    else:
        with capture.capture_sources(config, sources) as snapshot: assert snapshot['bytes'] == 8 * 1024 * 1024


def test_raw_root_is_refused_before_any_content_capture(tmp_path, monkeypatch):
    root = tmp_path / 'source'; put(root, 'a.md')
    config = config_for(('r', root)); config['roots'][0]['tier'] = 'raw'
    def forbidden(*a, **kw): pytest.fail('Unauthorized raw capture')
    monkeypatch.setattr(NativeReader, '_capture', forbidden)
    with pytest.raises(ValueError, match='personal or curated'):
        with capture.capture_sources(config, sources_for(('r', 'file', 'demo', '.'))): pass


@pytest.mark.skipif(os.name != 'posix', reason='Exercises POSIX reopened-file version binding')
def test_admitted_version_catches_same_byte_replacement_before_reopened_read(tmp_path, monkeypatch):
    root = tmp_path / 'source'; put(root, 'a.md', b'same')
    original = NativeReader._capture
    replaced = False
    def capture_file(self, selected, relative, **kwargs):
        nonlocal replaced
        if relative == 'a.md' and not replaced:
            replaced = True
            (root / 'a.md').rename(tmp_path / 'retained-original.md')
            put(root, 'a.md', b'same')
        return original(self, selected, relative, **kwargs)
    monkeypatch.setattr(NativeReader, '_capture', capture_file)
    with pytest.raises(ValueError, match='admitted file'):
        with capture.capture_sources(config_for(('r', root)), sources_for(('r', 'file', 'demo', '.'))): pass
    assert replaced


def test_shared_budget_exhaustion_has_no_successful_capture(tmp_path):
    root = tmp_path / 'source'; put(root, 'a.md')
    def expired(): raise TimeoutError('synthetic operation budget')
    with pytest.raises(TimeoutError):
        with capture.capture_sources(config_for(('r', root)), sources_for(('r', 'file', 'demo', '.')), check_budget=expired):
            pytest.fail('Expired operation yielded')


@pytest.mark.skipif(os.name != 'posix', reason='Exercises POSIX link/type admission before content reads')
@pytest.mark.parametrize('kind', ['hardlink', 'symlink', 'directory', 'fifo'])
def test_selected_unsafe_types_are_refused_before_content_reads(tmp_path, monkeypatch, kind):
    root = tmp_path / 'source'; root.mkdir()
    selected = root / 'unsafe.md'
    if kind == 'hardlink':
        original = put(tmp_path, 'retained-original.md'); os.link(original, selected)
    elif kind == 'symlink': selected.symlink_to(tmp_path / 'absent.md')
    elif kind == 'directory': selected.mkdir()
    else: os.mkfifo(selected)
    def forbidden(*a, **kw): pytest.fail('Unsafe source reached content reader')
    monkeypatch.setattr(NativeReader, '_capture', forbidden)
    with pytest.raises((ValueError, OSError)):
        with capture.capture_sources(config_for(('r', root)), sources_for(('r', 'file', 'demo', '.'))): pass


@pytest.mark.skipif(os.name != 'posix', reason='Exercises POSIX retained root/name rebinding')
def test_root_replacement_during_read_cannot_reuse_the_old_authorized_handle(tmp_path, monkeypatch):
    root = tmp_path / 'source'; put(root, 'a.md', b'same')
    config = config_for(('r', root)); sources = sources_for(('r', 'file', 'demo', '.'))
    original = NativeReader._capture
    replaced = False
    def capture_file(self, selected, relative, **kwargs):
        nonlocal replaced
        result = original(self, selected, relative, **kwargs)
        if relative == 'a.md' and not replaced:
            replaced = True
            root.rename(tmp_path / 'retained-root')
            put(root, 'a.md', b'same')
        return result
    monkeypatch.setattr(NativeReader, '_capture', capture_file)
    with pytest.raises((ValueError, OSError)):
        with capture.capture_sources(config, sources): pass
    assert replaced
