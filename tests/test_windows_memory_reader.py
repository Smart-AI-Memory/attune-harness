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

windows_only = pytest.mark.skipif(os.name != 'nt', reason='Actual Windows local-NTFS consumer observation')


@pytest.fixture(autouse=True)
def no_provider_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Reader qualification attempted network/provider access')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


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


def link_buffer(target, flags=1):
    encoded = target.encode('utf-16-le')
    return struct.pack('<IHHHHHHI', 0xA000000C, 12 + len(encoded), 0,
                       0, len(encoded), len(encoded), 0, flags) + encoded


@pytest.mark.parametrize('target,flags,expected', [
    ('../missing.jsonl', 1, r'C:\owned\missing.jsonl'),
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
    (root / 'findings.jsonl').symlink_to(target)
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
    (root / 'findings.jsonl').symlink_to('../missing.jsonl')
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
            (root / 'again').symlink_to('.', target_is_directory=True)
            (root / 'findings.jsonl').symlink_to('again/again/missing.jsonl')
        else:
            (root / 'findings.jsonl').symlink_to(target)
        if shape == 'growing-cycle':
            target.symlink_to('next.jsonl/more', target_is_directory=True)
        elif shape == 'chain':
            target.symlink_to('../absent.jsonl')
        elif shape == 'cycle':
            target.symlink_to('findings.jsonl')
    def forbidden(*args, **kwargs):
        pytest.fail('An absence probe requested source or target content')
    monkeypatch.setattr(native.Native, 'read', forbidden)
    packet = NativeReader(config_for(('r', root, 'raw', 'project-a'))).query('Aurora')
    assert packet['status'] == ('empty' if shape in ('chain', 'repeated-directory') else 'unavailable'), packet


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
])
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
