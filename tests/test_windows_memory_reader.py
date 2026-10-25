"""Reader consumers over actual native handles; portable journeys also run on POSIX.

# qualify: platform
"""

from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import struct
import socket
import time

import pytest

from attune_harness import memory_reader, memory_serving, windows_reads
from attune_harness import windows_effects as native
from attune_harness.features import FeatureUnavailable
from attune_harness.memory_cli import main as memory_main
from attune_harness.memory_context import MemoryHost
from attune_harness.memory_reader import FILE_LIMIT, SNAPSHOT_BYTES, NativeReader
from test_memory_reader import config_for, seed_raw
from test_memory_serving import file_case, render
from test_windows_reads import junction
from windows_read_witness import MetadataWitness

windows_only = pytest.mark.skipif(os.name != 'nt', reason='Actual Windows local-NTFS consumer observation')


@pytest.fixture(autouse=True)
def no_provider_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Reader qualification attempted network/provider access')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


def symlink(path, target, *, directory=False):
    try:
        path.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
            pytest.skip('Symbolic-link fixture unavailable (WinError 1314); no native link behavior observed')
        raise


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.mark.parametrize('tier', ['raw', 'personal', 'curated'])
def test_cli_recall_resolve_refresh_preserve_complete_sources_and_replace_handles(tmp_path, capsys, tier):
    root = tmp_path / 'Owned α with spaces' / tier
    if tier == 'raw':
        seed_raw(root)
        source = root / 'findings.jsonl'
    else:
        source = write(root / 'nested' / 'policy.md', b'# Aurora\r\n\r\nAurora policy retained advice.\r\n')
    config = write(tmp_path / 'memory.json', json.dumps(config_for(('r', root, tier, 'project-a'))).encode())
    base = ['--config', str(config)]
    query = 'Aurora' if tier == 'raw' else 'Aurora policy'
    assert memory_main([*base, 'recall', query, '--k', '10', '--max-chars', '4']) == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet['status'] == 'available' and not packet['problems']
    item = packet['items'][0]
    before = source.read_bytes(), source.stat().st_mtime_ns
    handle = write(tmp_path / 'handle.json', json.dumps(item['handle']).encode())
    assert memory_main([*base, 'resolve', str(handle)]) == 0
    resolved = json.loads(capsys.readouterr().out)
    if tier == 'raw':
        assert resolved['text'].startswith('Aurora')
    else:
        assert resolved['text'].encode() == before[0]  # actual CRLF is not rewritten
        assert resolved['locator']['path'] == 'nested/policy.md'
    context = write(tmp_path / 'context.json', json.dumps(packet).encode())
    assert memory_main([*base, 'refresh', str(context)]) == 0
    assert json.loads(capsys.readouterr().out)['invalidated_ids'] == []
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before
    if tier == 'raw':
        rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
        for row in rows:
            row['text'] += ' corrected'
        source.write_bytes(('\n'.join(json.dumps(row) for row in rows) + '\n').encode())
    else:
        source.write_bytes(before[0] + b'Aurora corrected policy.\n')
    assert memory_main([*base, 'refresh', str(context)]) == 0
    refreshed = json.loads(capsys.readouterr().out)
    assert item['handle']['id'] in refreshed['invalidated_ids']
    assert memory_main([*base, 'resolve', str(handle)]) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure['error'] == 'ValueError' and 'refresh context' in failure['detail']


def link_buffer(target, flags=1, *, print_name=''):
    encoded = target.encode('utf-16-le')
    printed = print_name.encode('utf-16-le')
    return struct.pack('<IHHHHHHI', 0xA000000C, 12 + len(encoded) + len(printed), 0,
                       0, len(encoded), len(encoded), len(printed), flags) + encoded + printed


@pytest.mark.parametrize('target,flags,expected', [
    (r'..\missing.jsonl', 1, r'C:\owned\missing.jsonl'),
    (r'\??\C:\outside\missing.jsonl', 0, r'C:\outside\missing.jsonl'),
])
def test_reparse_target_parser_uses_only_documented_local_lexical_semantics(target, flags, expected):
    source = PureWindowsPath(r'C:\owned\raw\findings.jsonl')
    assert str(windows_reads._symlink_target(source, link_buffer(target, flags))) == expected


@pytest.mark.parametrize('target,flags', [
    (r'\??\UNC\server\share\missing', 0), (r'\\server\share\missing', 0),
    (r'\\?\GLOBALROOT\Device\x', 0), (r'C:\outside\bad:stream\..\missing', 0),
    ('bad\x00name', 1), (r'C:\outside\missing', 1),
])
def test_reparse_target_parser_refuses_remote_alias_device_and_invalid_target_grammar(target, flags):
    with pytest.raises(ValueError):
        windows_reads._symlink_target(PureWindowsPath(r'C:\owned\findings.jsonl'), link_buffer(target, flags))


@pytest.mark.parametrize('target,flags', [
    ('../missing.jsonl', 1), ('../../missing', 1), ('.././missing', 1),
    ('sub/../../missing', 1), ('../../../missing', 1), ('sub/../../../../missing', 1),
    (r'sub\../missing', 1), ('missing/name', 1),
    ('again/again/missing.jsonl', 1), ('next.jsonl/more', 1), ('../absent.jsonl', 1),
    (r'\??\C:\outside/missing', 0), ('C:/outside/missing', 0),
])
def test_raw_substitute_forward_separator_refuses_before_normalization(monkeypatch, target, flags):
    source = PureWindowsPath(r'C:\owned\raw\findings.jsonl')
    def forbidden(*args, **kwargs):
        raise AssertionError('Malformed raw substitute name reached normalization')
    monkeypatch.setattr(windows_reads.ntpath, 'normpath', forbidden)
    with pytest.raises(ValueError, match='requires backslash separators'):
        windows_reads._symlink_target(source, link_buffer(target, flags))


@pytest.mark.parametrize('target,flags,expected', [
    (r'..\missing.jsonl', 1, r'C:\owned\missing.jsonl'),
    (r'\??\C:\outside\missing.jsonl', 0, r'C:\outside\missing.jsonl'),
])
def test_print_name_forward_separator_does_not_change_substitute_authority(target, flags, expected):
    source = PureWindowsPath(r'C:\owned\raw\findings.jsonl')
    data = link_buffer(target, flags, print_name='display/only')
    assert str(windows_reads._symlink_target(source, data)) == expected


def test_unsupported_volume_stays_inside_serving_suppression(tmp_path, monkeypatch):
    config, fake, _ = file_case(tmp_path)
    def unavailable(*args, **kwargs):
        raise FeatureUnavailable('Windows effects require local NTFS')
    monkeypatch.setattr(NativeReader, '_capture', unavailable)
    text, reason = render(fake, config)
    assert reason is None and '- n1' in text and '- file:' not in text


@windows_only
@pytest.mark.parametrize('layout', ['flat', 'nested'])
def test_real_whole_query_at_4096_documents_has_bound_discovery_and_capture(tmp_path, monkeypatch, record_property, layout):
    root = tmp_path / 'Corpus α'
    expected = {}
    for at in range(4096):
        prefix = '' if layout == 'flat' else f'group-{at // 64:02}/'
        name = prefix + f'note-{at:04}.md'
        expected[name] = f'# Aurora\n\nAurora capacity record {at:04}.\n'.encode()
        write(root / name, expected[name])
    for at in range(2049):
        write(root / f'incidental-{at:04}', b'not a document')
    write(root / 'summaries_by_path.json', b'{}')
    write(root / '.verdicts.jsonl', b'')
    original, rank = windows_reads.ReadRoot.observe, memory_reader._rank_documents
    witnessed = {}
    @contextmanager
    def observe(self, *args, **kwargs):
        start = time.perf_counter()
        with original(self, *args, **kwargs) as observations:
            witnessed['capture_seconds'] = time.perf_counter() - start
            documents = {name: value for name, value in observations.items() if name.endswith('.md')}
            assert set(documents) == set(expected)
            assert {name: value.data for name, value in documents.items()} == expected
            witnessed['ids'] = len({json.dumps(value.entry['identity'], sort_keys=True) for value in documents.values()})
            witnessed['hashes'] = len({value.sha256 for value in documents.values()})
            yield observations
        witnessed['observation_seconds'] = time.perf_counter() - start
    def ranking(*args, **kwargs):
        start = time.perf_counter()
        result = rank(*args, **kwargs)
        witnessed['ranking_seconds'] = time.perf_counter() - start
        return result
    monkeypatch.setattr(windows_reads.ReadRoot, 'observe', observe)
    monkeypatch.setattr(memory_reader, '_rank_documents', ranking)
    reader = NativeReader(config_for(('p', root, 'personal', 'global')))
    start = time.perf_counter()
    packet = reader.query('Aurora capacity', k=100)
    seconds = time.perf_counter() - start
    assert packet['status'] == 'available' and len(packet['items']) == 100 and not packet['problems'], packet['problems']
    assert witnessed['ids'] == witnessed['hashes'] == 4096
    for name, value in {**witnessed, 'query_seconds': seconds, 'files':4096}.items():
        record_property('reader_' + name, value)
    write(root / 'one-too-many.md', b'Aurora overflow')
    failure = reader.query('Aurora capacity', k=1)
    assert failure['status'] == 'unavailable' and 'snapshot file limit' in failure['problems'][0]['detail']


@windows_only
@pytest.mark.parametrize('target_outside', [False, True])
@pytest.mark.parametrize('target_exists', [False, True])
def test_raw_dangling_link_is_positive_absence_but_live_target_never_reads_content(tmp_path, monkeypatch, target_outside, target_exists):
    root = tmp_path / 'raw'
    root.mkdir()
    target = (tmp_path / 'outside-target.jsonl') if target_outside else (root / 'target.jsonl')
    if target_exists:
        target.write_bytes(b'OUTSIDE_SENTINEL')
    symlink(root / 'findings.jsonl', target)
    calls, opens = [], []
    read, child = native.Native.read, native.Native.child
    def observed(self, *args, **kwargs):
        value = read(self, *args, **kwargs)
        calls.append(value)
        return value
    def opened(self, parent, name, **kwargs):
        if name == target.name:
            opens.append(kwargs)
            actual = self.nt.NtCreateFile
            def metadata_only(out, access, *rest):
                assert not access & (native.FILE_READ_DATA | native.READ_CONTROL)
                return actual(out, access, *rest)
            self.nt.NtCreateFile = metadata_only
            try:
                return child(self, parent, name, **kwargs)
            finally:
                self.nt.NtCreateFile = actual
        return child(self, parent, name, **kwargs)
    monkeypatch.setattr(native.Native, 'read', observed)
    monkeypatch.setattr(native.Native, 'child', opened)
    reader = NativeReader(config_for(('r', root, 'raw', 'project-a')))
    packet = reader.query('Aurora', k=1)
    assert packet['status'] == ('unavailable' if target_exists else 'empty'), packet
    if target_exists:
        assert 'Live symbolic-link' in packet['problems'][0]['detail']
    assert calls == []
    assert opens and all(call.get('metadata_only') is True for call in opens)


@windows_only
def test_raw_relative_parent_target_and_target_appearance_refuse_false_absence(tmp_path, monkeypatch):
    root = tmp_path / 'raw'
    root.mkdir()
    symlink(root / 'findings.jsonl', r'..\missing.jsonl')
    reader = NativeReader(config_for(('r', root, 'raw', 'project-a')))
    assert reader.query('Aurora policy')['status'] == 'empty'
    original = windows_reads.ReadRoot._target_absent
    fired = []
    def appeared(self, target, handles, checks, seen):
        answer = original(self, target, handles, checks, seen)
        if not fired:
            write(tmp_path / 'missing.jsonl', b'OUTSIDE_SENTINEL')
            fired.append(True)
        return answer
    monkeypatch.setattr(windows_reads.ReadRoot, '_target_absent', appeared)
    assert reader.query('Aurora policy')['status'] == 'unavailable'
    assert fired == [True]


@windows_only
@pytest.mark.parametrize('target', ['selected', 'incidental', 'sidecar'])
def test_only_unselected_regular_hardlinks_are_ignored(tmp_path, target):
    root = tmp_path / 'docs'
    source = write(root / 'policy.md', b'# Aurora\n\nAurora policy.\n')
    outside = write(tmp_path / 'outside', b'not a document')
    if target == 'selected':
        os.link(source, root / 'alias.md')
    elif target == 'incidental':
        os.link(outside, root / 'ignored.txt')
    else:
        os.link(outside, root / 'summaries_by_path.json')
    packet = NativeReader(config_for(('p', root, 'personal', 'global'))).query('Aurora policy')
    assert packet['status'] == ('available' if target == 'incidental' else 'unavailable'), packet


@windows_only
@pytest.mark.parametrize('change', ['new-document', 'sidecar-appears', 'source-replaced', 'sidecar-replaced', 'incidental-junction'])
def test_capture_remains_bound_through_real_ranking(tmp_path, monkeypatch, change):
    root = tmp_path / 'docs'
    source = write(root / 'policy.md', b'# Aurora\n\nAurora policy.\n')
    sidecar = write(root / '.verdicts.jsonl', b'')
    outside = tmp_path / 'outside'
    outside.mkdir()
    write(outside / 'escaped.md', b'OUTSIDE_SENTINEL')
    rank = memory_reader._rank_documents
    fired = []
    def changed(*args, **kwargs):
        result = rank(*args, **kwargs)
        if change == 'new-document':
            write(root / 'new.md', b'Aurora new')
        elif change == 'sidecar-appears':
            write(root / 'summaries_by_path.json', b'{}')
        elif change.endswith('replaced'):
            selected = source if change == 'source-replaced' else sidecar
            retained = selected.read_bytes(), selected.stat().st_mtime_ns
            selected.rename(selected.with_name(selected.name + '-retained'))
            selected.write_bytes(retained[0])
            os.utime(selected, ns=(retained[1], retained[1]))
        else:
            junction(root / 'unselected-link', outside)
        fired.append(True)
        return result
    monkeypatch.setattr(memory_reader, '_rank_documents', changed)
    packet = NativeReader(config_for(('p', root, 'personal', 'global'))).query('Aurora policy')
    assert fired == [True] and packet['status'] == 'unavailable' and not packet['items'], packet


@windows_only
@pytest.mark.parametrize('changed', ['source-time', 'same-byte-replacement', 'sidecar-appearance', 'sidecar-deletion', 'sidecar-time'])
def test_document_handles_and_refresh_follow_native_versions(tmp_path, changed):
    root = tmp_path / 'docs'
    source = write(root / 'policy.md', b'# Aurora\n\nAurora policy.\n')
    sidecar = root / 'summaries_by_path.json'
    if changed != 'sidecar-appearance':
        write(sidecar, b'{}')
    host = MemoryHost(config_for(('p', root, 'personal', 'global')))
    packet = host.context('Aurora policy', k=1)
    handle = packet['items'][0]['handle']
    if changed == 'same-byte-replacement':
        before = source.read_bytes(), source.stat().st_mtime_ns
        source.rename(source.with_name('retained'))
        source.write_bytes(before[0])
        os.utime(source, ns=(before[1], before[1]))
    elif changed in ('source-time', 'sidecar-time'):
        selected = source if changed == 'source-time' else sidecar
        stamp = selected.stat().st_mtime_ns + 1000000000
        os.utime(selected, ns=(stamp, stamp))
    elif changed == 'sidecar-deletion':
        sidecar.unlink()
    else:
        write(sidecar, b'{}')
    with pytest.raises((ValueError, OSError)):
        host.adapter.resolve(handle)
    refreshed = host.refresh(packet)
    assert refreshed['invalidated_ids'] == [handle['id']]
    assert refreshed['context']['status'] == 'available'


@windows_only
@pytest.mark.parametrize('bound', ['file', 'total'])
def test_reader_capture_exact_byte_limits_and_one_over(tmp_path, monkeypatch, bound):
    root = tmp_path / 'docs'
    size = FILE_LIMIT
    count = 1 if bound == 'file' else SNAPSHOT_BYTES // FILE_LIMIT
    for index in range(count):
        write(root / f'doc-{index}.md', b'A' * size)
    seen = []
    def rank_snapshot(snapshot, query, k):
        seen.append(sum(p.stat().st_size for p in snapshot.glob('*.md')))
        return []  # This witness checks capture limits; capacity test runs actual ranking.
    monkeypatch.setattr(memory_reader, '_rank_documents', rank_snapshot)
    reader = NativeReader(config_for(('p', root, 'personal', 'global')))
    assert reader.query('Aurora policy')['status'] == 'empty'
    assert seen == [FILE_LIMIT if bound == 'file' else SNAPSHOT_BYTES]
    if bound == 'file':
        with (root / 'doc-0.md').open('ab') as stream:
            stream.write(b'!')
    else:
        write(root / 'extra.md', b'!')
    packet = reader.query('Aurora policy')
    assert packet['status'] == 'unavailable'
    assert ('read limit' if bound == 'file' else '64 MiB') in packet['problems'][0]['detail']
    assert len(seen) == 1  # one-over refuses before snapshot ranking


@windows_only
def test_unsupported_volume_is_a_root_problem_and_file_pointer_suppression(tmp_path, monkeypatch):
    root = tmp_path / 'docs'
    write(root / 'policy.md', b'Aurora policy')
    def unsupported(*args, **kwargs):
        raise FeatureUnavailable('Windows effects require local NTFS')
    monkeypatch.setattr(native.Native, 'volume', unsupported)
    reader = NativeReader(config_for(('p', root, 'personal', 'global')))
    packet = reader.query('Aurora policy')
    assert packet['status'] == 'unavailable' and packet['problems'][0]['reason'] == 'FeatureUnavailable'
    config, fake, _ = file_case(tmp_path)
    text, reason = render(fake, config)
    assert reason is None and '- n1' in text and '- file:' not in text


def test_markdown_named_directory_refuses_as_in_the_frozen_reader(tmp_path):
    root = tmp_path / 'docs'
    (root / 'directory.md').mkdir(parents=True)
    packet = NativeReader(config_for(('p', root, 'personal', 'global'))).query('Aurora policy')
    assert packet['status'] == 'unavailable' and not packet['items']


@windows_only
@pytest.mark.parametrize('shape', ['chain', 'cycle', 'growing-cycle', 'repeated-directory', 'drive-root', 'junction'])
def test_raw_absence_probes_chained_links_and_refuses_unproven_shapes(tmp_path, monkeypatch, shape):
    root = tmp_path / 'raw'
    root.mkdir()
    if shape == 'junction':
        target = tmp_path / 'target'
        target.mkdir()
        junction(root / 'findings.jsonl', target)
    else:
        target = root / 'next.jsonl'
        if shape == 'drive-root':
            target = Path(root.anchor)
        if shape == 'repeated-directory':
            symlink(root / 'again', '.', directory=True)
            symlink(root / 'findings.jsonl', r'again\again\missing.jsonl')
        else:
            symlink(root / 'findings.jsonl', target)
        if shape == 'growing-cycle':
            symlink(target, r'next.jsonl\more', directory=True)
        elif shape == 'chain':
            symlink(target, r'..\absent.jsonl')
        elif shape == 'cycle':
            symlink(target, 'findings.jsonl')
    def forbidden(*args, **kwargs):
        pytest.fail('An absence probe requested source or target content')
    monkeypatch.setattr(native.Native, 'read', forbidden)
    packet = NativeReader(config_for(('r', root, 'raw', 'project-a'))).query('Aurora')
    assert packet['status'] == ('empty' if shape in ('chain', 'repeated-directory') else 'unavailable'), packet
    if shape == 'growing-cycle':
        assert packet['problems'] == [{'root_id': 'r', 'reason': 'ValueError',
                                      'detail': 'Symbolic-link target cycle cannot prove absence'}], packet


@pytest.mark.skipif(os.name != 'posix', reason='Exact legacy POSIX digest oracle')
def test_posix_capture_digest_retains_the_legacy_fields(tmp_path):
    from attune_harness.review_contract import digest
    source = write(tmp_path / 'source.md', b'Aurora policy\n')
    before = source.stat()
    reader = NativeReader(config_for(('p', tmp_path, 'personal', 'global')))
    content, version, mtime_ns = reader._capture(reader.config['roots'][0], 'source.md')
    expected = digest({'sha256':hashlib.sha256(content).hexdigest(), 'device':before.st_dev,
                       'inode':before.st_ino, 'mtime_ns':before.st_mtime_ns,
                       'ctime_ns':before.st_ctime_ns, 'size':before.st_size})
    assert version == expected and mtime_ns == before.st_mtime_ns



def test_cycle_detection_distinguishes_consumed_suffix_from_reentry():
    identity, parent = {'volume':1, 'file_id':'link'}, {'volume':1, 'file_id':'parent'}
    seen = {}
    windows_reads._remember_link(seen, identity, parent, ('again', 'missing'))
    windows_reads._remember_link(seen, identity, parent, ('missing',))
    with pytest.raises(ValueError, match='cycle'):
        windows_reads._remember_link(seen, identity, parent, ('more', 'missing'))
    other_parent = {'volume':1, 'file_id':'other-parent'}
    windows_reads._remember_link(seen, identity, other_parent, ('missing',))
    terminal = {}
    windows_reads._remember_link(terminal, identity, parent, ())
    with pytest.raises(ValueError, match='cycle'):
        windows_reads._remember_link(terminal, identity, parent, ('growing',))


@pytest.mark.parametrize('data', [
    b'', struct.pack('<I', 0) + b'\x00\x00',
    struct.pack('<I', 1) + b'\\\x00', struct.pack('<I', 4) + b'\\\x00',
    struct.pack('<I', 2) + b'\x00\xd8', struct.pack('<I', 2) + b'\x00\x00',
    struct.pack('<I', 2) + b'\\\x00' + bytes(windows_reads._NAME_INFO_LIMIT),
], ids=['empty', 'zero-count', 'odd-count', 'truncated', 'unpaired-surrogate', 'nul', 'oversized'])
def test_volume_name_parser_refuses_malformed_byte_counts_encoding_and_metadata_bound(data):
    with pytest.raises(ValueError, match='volume-anchor name'):
        windows_reads._file_name_info(data)


def test_volume_name_parser_uses_count_without_assuming_a_trailing_nul():
    assert windows_reads._file_name_info(struct.pack('<I', 2) + b'\\\x00') == '\\'
    encoded = '\\Owned α'.encode('utf-16-le')
    assert windows_reads._file_name_info(struct.pack('<I', len(encoded)) + encoded + b'ignored') == '\\Owned α'


@windows_only
def test_actual_volume_root_is_distinct_from_an_owned_subdirectory_anchor(tmp_path):
    api = native.Native()
    anchor = api.volume(tmp_path)
    with api.owned(api.volume_handle(anchor)) as physical_root:
        windows_reads._require_volume_root(api, physical_root)
    with api.owned(api.volume_handle(str(tmp_path))) as subdirectory:
        with pytest.raises(FeatureUnavailable, match='physical volume-root anchor'):
            windows_reads._require_volume_root(api, subdirectory)


@windows_only
def test_unsafe_anchor_control_reaches_redirected_sentinel_only_without_guard(tmp_path, monkeypatch):
    # Real handles emulate an unsafe drive-anchor binding; no SUBST mapping is made.
    supplied = tmp_path / 'source'
    supplied.mkdir()
    redirect = tmp_path / 'redirected-anchor'
    sentinel = write(redirect.joinpath(*supplied.parts[1:]) / 'note.md', b'unsafe anchor sentinel')
    original = native.Native.volume_handle
    children, reads = [], []
    original_child, original_read = native.Native.child, native.Native.read
    def redirected(self, anchor):
        return original(self, str(redirect))
    def child(self, *args, **kwargs):
        children.append(args[1])
        return original_child(self, *args, **kwargs)
    def read(self, *args, **kwargs):
        reads.append(True)
        return original_read(self, *args, **kwargs)
    monkeypatch.setattr(native.Native, 'volume_handle', redirected)
    monkeypatch.setattr(native.Native, 'child', child)
    monkeypatch.setattr(native.Native, 'read', read)
    with pytest.raises(FeatureUnavailable, match='physical volume-root anchor'):
        with windows_reads.open_read_root(supplied):
            pytest.fail('Unsafe anchor admitted')
    assert children == [] and reads == []
    # The one-guard-disabled control proves reachability, rather than merely
    # testing an unrelated early failure or an unreachable sentinel spelling.
    monkeypatch.setattr(windows_reads, '_require_volume_root', lambda *args: None)
    with windows_reads.open_read_root(supplied) as root:
        assert root.read('note.md', max_bytes=100).data == sentinel.read_bytes()
    assert children and reads


@windows_only
def test_dangling_target_probe_also_refuses_an_unsafe_anchor_before_child_access(tmp_path, monkeypatch):
    raw = tmp_path / 'raw'
    raw.mkdir()
    target = tmp_path / 'outside' / 'missing.jsonl'
    redirect = tmp_path / 'redirected-target-anchor'
    redirect.mkdir()
    original = native.Native.volume_handle
    original_child = native.Native.child
    attempted_target_children = []
    with windows_reads.open_read_root(raw) as root:
        def redirected(self, anchor):
            return original(self, str(redirect))
        def forbidden_target_child(self, *args, **kwargs):
            attempted_target_children.append(args[1])
            pytest.fail('Unsafe target anchor received child authority')
        # Call the target walker directly so ordinary source-root freshness
        # checks do not obscure which retained anchor owns the refusal.
        monkeypatch.setattr(native.Native, 'volume_handle', redirected)
        monkeypatch.setattr(native.Native, 'child', forbidden_target_child)
        from contextlib import ExitStack
        with ExitStack() as handles:
            with pytest.raises(FeatureUnavailable, match='physical volume-root anchor'):
                root._target_absent(target, handles, [], {})
        assert attempted_target_children == []
        monkeypatch.setattr(native.Native, 'child', original_child)



@windows_only
def test_anchor_name_retry_is_bounded_and_forwards_the_actual_root_handle(tmp_path, monkeypatch):
    api = native.Native()
    original = api.k.GetFileInformationByHandleEx
    sizes = []
    def retry(handle, kind, data, size):
        if kind == 2:
            sizes.append(size)
            if len(sizes) == 1:
                struct.pack_into('<I', data, 0, 600)
                ctypes.set_last_error(234)
                return 0
        return original(handle, kind, data, size)
    monkeypatch.setattr(api.k, 'GetFileInformationByHandleEx', retry)
    with api.owned(api.volume_handle(api.volume(tmp_path))) as handle:
        windows_reads._require_volume_root(api, handle)
    assert sizes == [520, 1040]


@windows_only
@pytest.mark.parametrize('required,error', [(0, 234), (3, 234), (516, 234), (65538, 234), (0, 5)])
def test_anchor_refuses_inconsistent_retry_lengths_and_native_errors(tmp_path, monkeypatch, required, error):
    api = native.Native()
    original = api.k.GetFileInformationByHandleEx
    calls = []
    def refused(handle, kind, data, size):
        if kind == 2:
            calls.append(size)
            struct.pack_into('<I', data, 0, required)
            ctypes.set_last_error(error)
            return 0
        return original(handle, kind, data, size)
    monkeypatch.setattr(api.k, 'GetFileInformationByHandleEx', refused)
    with api.owned(api.volume_handle(api.volume(tmp_path))) as handle:
        with pytest.raises(ValueError if error == 234 else OSError):
            windows_reads._require_volume_root(api, handle)
    assert calls == [520]


@windows_only
def test_anchor_repeated_name_growth_stops_at_the_metadata_ceiling(tmp_path, monkeypatch):
    api = native.Native()
    original = api.k.GetFileInformationByHandleEx
    sizes = []
    def growing(handle, kind, data, size):
        if kind == 2:
            sizes.append(size)
            struct.pack_into('<I', data, 0, size)
            ctypes.set_last_error(234)
            return 0
        return original(handle, kind, data, size)
    monkeypatch.setattr(api.k, 'GetFileInformationByHandleEx', growing)
    with api.owned(api.volume_handle(api.volume(tmp_path))) as handle:
        with pytest.raises(ValueError, match='required volume-anchor name length'):
            windows_reads._require_volume_root(api, handle)
    assert sizes[0] == 520 and sizes[-1] == windows_reads._NAME_INFO_LIMIT
    assert len(sizes) <= 9 and all(a < b for a, b in zip(sizes, sizes[1:]))


def _legacy_recursion_failure(error):
    """Classify only the two observed errors from the old recursive control."""
    if (type(error) is RecursionError or
            (type(error) is ctypes.ArgumentError and str(error) ==
             'argument 2: RecursionError: maximum recursion depth exceeded while calling a Python object')):
        return {'error': 'RecursionError', 'outer_type': type(error).__name__, 'detail': str(error)}
    raise error


@pytest.mark.parametrize('error', [
    RecursionError('maximum recursion depth exceeded'),
    ctypes.ArgumentError('argument 2: RecursionError: maximum recursion depth exceeded while calling a Python object'),
], ids=['bare-recursion', 'observed-ctypes-wrapper'])
def test_old_recursive_control_classifies_only_observed_recursion_errors(error):
    result = _legacy_recursion_failure(error)
    assert result == {'error': 'RecursionError', 'outer_type': type(error).__name__, 'detail': str(error)}


@pytest.mark.parametrize('error', [
    ctypes.ArgumentError('argument 2: ValueError: invalid value'),
    ctypes.ArgumentError('argument 1: RecursionError: maximum recursion depth exceeded while calling a Python object'),
    ctypes.ArgumentError('argument 2: RecursionError: unrelated detail'),
    ctypes.ArgumentError('argument 2: RecursionError: maximum recursion depth exceeded while calling a Python object extra'),
    ValueError('argument 2: RecursionError: maximum recursion depth exceeded while calling a Python object'),
    RuntimeError('maximum recursion depth exceeded'),
], ids=['unrelated-argument', 'other-argument', 'other-recursion-detail', 'extra-suffix', 'wrong-wrapper-type', 'wrong-error-type'])
def test_old_recursive_control_propagates_every_other_error(error):
    with pytest.raises(type(error)) as caught:
        _legacy_recursion_failure(error)
    assert caught.value is error


@windows_only
@pytest.mark.parametrize('live_target', [False, True])
def test_distinct_raw_chain_has_no_python_stack_cap_and_old_recursive_control_fails(tmp_path, live_target, record_property):
    import inspect
    import subprocess
    import sys
    root = tmp_path / 'raw-chain'
    root.mkdir()
    names = ['findings.jsonl'] + [f'link-{at:03}.jsonl' for at in range(1, 80)]
    for at, name in enumerate(names):
        symlink(root / name, names[at + 1] if at + 1 < len(names) else 'target.jsonl')
    if live_target:
        write(root / 'target.jsonl', b'LIVE CHAIN SENTINEL')
    config = write(tmp_path / 'config.json', json.dumps(config_for(('r', root, 'raw', 'project-a'))).encode())
    legacy = Path(__file__).parent / 'fixtures' / 'windows_b36_recursive_target_walker.txt'
    assert hashlib.sha256(legacy.read_bytes()).hexdigest() == '1bc02abd699bd0625d8c2bef11aae6481baf68042fbdf15bb707bdbcb3aac162'
    worker = 'import ctypes\n' + inspect.getsource(_legacy_recursion_failure) + r'''
import hashlib,json,socket,sys,time
from pathlib import Path
package, config_path, legacy_path = sys.argv[1:]
sys.path.insert(0, package)
from attune_harness import windows_reads,windows_effects
from attune_harness.memory_reader import NativeReader
config=json.loads(Path(config_path).read_text(encoding='utf-8'))
reads=[]
def forbidden(*args,**kwargs):
    reads.append(True)
    raise AssertionError('Chain proof attempted content or network authority')
socket.socket.connect=forbidden
socket.socket.connect_ex=forbidden
windows_effects.Native.read=forbidden
production=windows_reads.ReadRoot._target_absent
namespace=dict(vars(windows_reads))
exec(compile(Path(legacy_path).read_text(encoding='utf-8'),legacy_path,'exec'),namespace)
def probe(method):
    windows_reads.ReadRoot._target_absent=method
    saved=sys.getrecursionlimit()
    start=time.perf_counter()
    try:
        sys.setrecursionlimit(80)
        packet=NativeReader(config).query('Aurora')
        outcome={'status':packet['status'],'problems':packet['problems']}
    except (RecursionError,ctypes.ArgumentError) as error:
        if method is not namespace['_target_absent']:
            raise
        outcome=_legacy_recursion_failure(error)
    finally:
        sys.setrecursionlimit(saved)
        windows_reads.ReadRoot._target_absent=production
    outcome['seconds']=time.perf_counter()-start
    return outcome
production_receipt={'phase':'production','production':probe(production),
        'forbidden_calls':len(reads),'source_sha256':hashlib.sha256(Path(windows_reads.__file__).read_bytes()).hexdigest(),
        'chain_links':80,'child_recursion_budget':80}
print(json.dumps(production_receipt),flush=True)
old_recursive=probe(namespace['_target_absent'])
result={**production_receipt,'phase':'complete','old_recursive':old_recursive,'forbidden_calls':len(reads)}
print(json.dumps(result),flush=True)
'''
    allowed = {'systemroot', 'windir', 'tmp', 'temp', 'path'}
    child = subprocess.run([sys.executable, '-I', '-c', worker,
                            str(Path(windows_reads.__file__).parent.parent), str(config), str(legacy)],
                           env={key:value for key,value in os.environ.items() if key.casefold() in allowed},
                           capture_output=True, text=True, timeout=120)
    lines = child.stdout.splitlines()
    if lines:
        record_property('raw_chain_production', lines[0])
    assert child.returncode == 0, (child.stdout, child.stderr)
    assert len(lines) == 2, child.stdout
    production_receipt, result = map(json.loads, lines)
    assert production_receipt['phase'] == 'production' and result['phase'] == 'complete'
    assert production_receipt['production'] == result['production']
    assert production_receipt['forbidden_calls'] == 0
    assert production_receipt['source_sha256'] == result['source_sha256']
    assert result['source_sha256'] == hashlib.sha256(Path(windows_reads.__file__).read_bytes()).hexdigest()
    assert result['old_recursive'].get('error') == 'RecursionError', result
    assert result['forbidden_calls'] == 0, result
    assert result['production']['status'] == ('unavailable' if live_target else 'empty'), result
    if live_target:
        assert 'Live symbolic-link' in result['production']['problems'][0]['detail']
    else:
        assert result['production']['problems'] == []
    record_property('raw_chain_control', json.dumps(result, sort_keys=True))



@pytest.mark.parametrize('target,flags', [
    (r'..\..\..\missing', 1), (r'sub\..\..\..\..\missing', 1),
    (r'\??\C:\..\missing', 0),
])
def test_symbolic_target_cannot_hide_excess_parents_through_normalization(target, flags):
    with pytest.raises(ValueError, match='above its drive root'):
        windows_reads._symlink_target(PureWindowsPath(r'C:\owned\raw\findings.jsonl'), link_buffer(target, flags))


@pytest.mark.parametrize('target,expected', [
    (r'..\..\missing', r'C:\missing'), (r'..\.\missing', r'C:\owned\missing'),
    (r'sub\..\..\missing', r'C:\owned\missing'),
])
def test_symbolic_target_keeps_documented_valid_dot_component_replacement(target, expected):
    assert str(windows_reads._symlink_target(PureWindowsPath(r'C:\owned\raw\findings.jsonl'), link_buffer(target))) == expected



@windows_only
def test_root_disappearing_between_pointer_check_and_verdict_capture_is_suppressed(tmp_path, monkeypatch):
    root = tmp_path / 'verdict-root'
    root.mkdir()
    config, fake, sidecar = file_case(root)
    write(root / 'state.md', b'Aurora policy')
    sidecar.write_text(json.dumps(dict(stem='state', verdict='wrong', digest='fixture', who='fixture', at='2026-09-24')) + '\n', encoding='utf-8')
    check_path, capture = windows_reads.ReadRoot.check_path, NativeReader._capture
    attack, refused_roots = [], []
    def vanished(self, name):
        check_path(self, name)
        root.rename(tmp_path / 'retained-moved-verdict-root')
        attack.append('after completed pointer check, before verdict capture')
    def observed_capture(self, *args, **kwargs):
        try:
            return capture(self, *args, **kwargs)
        except ValueError as error:
            if isinstance(error.__cause__, FileNotFoundError):
                refused_roots.append(str(error))
            raise
    monkeypatch.setattr(windows_reads.ReadRoot, 'check_path', vanished)
    monkeypatch.setattr(NativeReader, '_capture', observed_capture)
    text, reason = render(fake, config)
    assert attack == ['after completed pointer check, before verdict capture']
    assert refused_roots == ['Explicit memory root is unavailable']
    assert reason is None and '- n1' in text and '- file:' not in text


@windows_only
def test_query_exact_and_one_over_64mib_includes_optional_sidecar_bytes(tmp_path, monkeypatch):
    root = tmp_path / 'sidecar-bound'
    for at in range(8):
        write(root / f'doc-{at}.md', b'A' * (FILE_LIMIT - 2 if at == 0 else FILE_LIMIT))
    sidecar = write(root / 'summaries_by_path.json', b'{}')
    totals = []
    def rank_snapshot(snapshot, query, k):
        totals.append(sum(p.stat().st_size for p in snapshot.rglob('*') if p.is_file()))
        return []
    monkeypatch.setattr(memory_reader, '_rank_documents', rank_snapshot)
    reader = NativeReader(config_for(('p', root, 'personal', 'global')))
    packet = reader.query('Aurora policy')
    assert packet['status'] == 'empty' and packet['problems'] == []
    assert totals == [SNAPSHOT_BYTES]
    sidecar.write_bytes(b'{} ')
    packet = reader.query('Aurora policy')
    assert packet['status'] == 'unavailable' and '64 MiB' in packet['problems'][0]['detail']
    assert totals == [SNAPSHOT_BYTES]


@pytest.mark.parametrize('tail', ['Windows/System32/owned', 'Program Files/owned', 'Program Files (x86)/owned'])
def test_protected_windows_tail_refuses_equally_under_different_drive_letters(tail):
    from attune_harness.paths import _protected
    original = _protected('C:/' + tail, windows=True)
    alternate = _protected('X:/' + tail, windows=True)
    assert original is not None and original == alternate


@windows_only
@pytest.mark.parametrize('component', ['ordinary', 'absent', 'linked'])
@pytest.mark.parametrize('form', ['relative', 'absolute', 'chained-relative'])
@pytest.mark.parametrize('terminal', ['live', 'missing'])
@pytest.mark.parametrize('separator', ['\\', '/'], ids=['backslash', 'forward-slash'])
def test_raw_canceled_component_absence_matches_actual_windows_stat(tmp_path, monkeypatch, record_property, component, form, terminal, separator):
    """Observe target semantics without treating lexical collapse as an oracle."""
    root = tmp_path / 'raw'
    root.mkdir()
    sub = root / 'sub'
    live = root / 'live'
    if component == 'ordinary':
        sub.mkdir()
    if component == 'linked':
        outside = tmp_path / 'owned-target'
        (outside / 'child').mkdir(parents=True)
        live = write(outside / 'live', b'synthetic physical-parent sentinel')
        symlink(sub, outside / 'child', directory=True)
    else:
        write(live, b'synthetic lexical-parent sentinel')
    source = root / 'findings.jsonl'
    target = separator.join(('sub', '..', terminal))
    if form == 'absolute':
        target = str(root / 'sub' / '..' / terminal).replace('\\', separator)
    links = [source]
    if component == 'linked':
        links.append(sub)
    if form == 'chained-relative':
        hop = root / 'next.jsonl'
        symlink(hop, target)
        links.append(hop)
        symlink(source, hop.name)
    else:
        symlink(source, target)

    def stat_evidence(path, *, follow):
        try:
            value = os.stat(path) if follow else os.lstat(path)
        except OSError as error:
            missing = isinstance(error, FileNotFoundError) and error.winerror in (2, 3)
            return {'status': 'missing' if missing else 'error', 'error': type(error).__name__,
                    'errno': error.errno, 'winerror': error.winerror, 'detail': str(error)}
        return {'status': 'live', 'mode': value.st_mode, 'size': value.st_size,
                'identity': [value.st_dev, value.st_ino], 'links': value.st_nlink,
                'attributes': value.st_file_attributes, 'reparse_tag': value.st_reparse_tag}

    observer = MetadataWitness(monkeypatch, record_property, windows_reads.ReadRoot, native.Native)

    def stored_link(path, phase):
        with observer.phase(phase, path.name), windows_reads.open_read_root(path.parent) as admitted:
            api = admitted._api
            with api.owned(api.child(admitted._root, path.name, writable=False, metadata_only=True)) as handle:
                data = admitted._reparse_data(handle)
        tag, length, _ = struct.unpack_from('<IHH', data)
        offset, size, printed, print_size, flags = struct.unpack_from('<HHHHI', data, 8)
        assert tag == 0xA000000C and length + 8 == len(data) and flags in (0, 1)
        assert all(start % 2 == count % 2 == 0 and 20 + start + count <= len(data)
                   for start, count in ((offset, size), (printed, print_size)))
        substitute = data[20 + offset:20 + offset + size].decode('utf-16-le')
        return {'readlink': os.readlink(path), 'lstat': stat_evidence(path, follow=False),
                'flags': flags, 'substitute': substitute,
                'print_name': data[20 + printed:20 + printed + print_size].decode('utf-16-le'),
                'reparse_hex': data.hex()}

    before = {path.name: stored_link(path, 'before') for path in links}
    active = before['next.jsonl' if form == 'chained-relative' else 'findings.jsonl']
    components = active['substitute'].replace('\\', '/').split('/')
    if form != 'absolute':
        assert active['flags'] == 1 and active['substitute'] == target, before
        assert active['readlink'] == target and '..' in components, before
    else:
        assert active['flags'] == 0, before
    oracle = stat_evidence(source, follow=True)
    receipt = {'component': component, 'form': form, 'terminal': terminal, 'separator': separator,
               'input_target': target,
               'stored_links': before, 'stored_target_has_dotdot': '..' in components,
               'absolute_target_normalized_at_creation': form == 'absolute' and '..' not in components,
               'sub_lstat': stat_evidence(sub, follow=False), 'following_stat': oracle,
               'lexical_terminal_stat': stat_evidence(root / terminal, follow=True),
               'owned_live_stat': stat_evidence(live, follow=True)}
    record_property('raw_dotdot_inputs', json.dumps(receipt, sort_keys=True))

    reads = []
    def forbidden_read(*args, **kwargs):
        reads.append(True)
        raise AssertionError('Raw link semantics witness attempted a content read')
    monkeypatch.setattr(native.Native, 'read', forbidden_read)
    with observer.phase('query'):
        packet = NativeReader(config_for(('r', root, 'raw', 'project-a'))).query('Aurora policy')
    record_property('raw_dotdot_reader', json.dumps({'packet': packet, 'content_reads': len(reads)}, sort_keys=True))
    receipt['reader'] = {'status': packet['status'], 'problems': packet['problems']}
    receipt['after_following_stat'] = stat_evidence(source, follow=True)
    receipt['after_stored_links'] = {path.name: stored_link(path, 'after') for path in links}
    receipt['content_reads'] = len(reads)
    record_property('raw_dotdot_result', json.dumps(receipt, sort_keys=True))
    assert reads == [] and receipt['after_stored_links'] == before, receipt
    assert receipt['after_following_stat'] == oracle, receipt
    if separator == '/' and form != 'absolute':
        assert active['flags'] == 1 and active['substitute'] == target and active['readlink'] == target, receipt
        assert oracle['status'] == 'error' and oracle['error'] == 'OSError', receipt
        assert oracle['winerror'] == 123 and oracle['errno'] == 22, receipt
        assert packet['status'] == 'unavailable' and packet['problems'] == [{
            'root_id': 'r', 'reason': 'ValueError',
            'detail': 'Symbolic-link substitute name requires backslash separators'}], receipt
        return
    assert oracle['status'] in ('live', 'missing'), receipt
    if component == 'linked' and terminal == 'live':
        assert receipt['lexical_terminal_stat']['status'] == 'missing', receipt
        assert receipt['owned_live_stat']['status'] == 'live', receipt
    if oracle['status'] == 'live':
        assert oracle['identity'] == receipt['owned_live_stat']['identity'], receipt
        assert packet['status'] == 'unavailable' and 'Live symbolic-link' in packet['problems'][0]['detail'], receipt
    else:
        assert packet['status'] == 'empty' and packet['problems'] == [], receipt
