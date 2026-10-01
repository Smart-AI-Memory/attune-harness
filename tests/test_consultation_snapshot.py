"""Behavioral offline receipts for the shared consultation source boundary."""

# qualify: platform

import copy
# qualify: platform
import hashlib
import os
import shutil

import pytest

from attune_harness import consultation_snapshot as snapshot
from attune_harness.review_contract import digest


@pytest.fixture
def root(tmp_path):
    root = tmp_path.resolve() / 'repo'
    root.mkdir()
    (root / 'src').mkdir()
    (root / 'src/calc.py').write_bytes(b'def add(a, b):\r\n    return a + b\r\n')
    (root / 'notes.md').write_text('Review café\n', encoding='utf-8')
    return root


def test_retained_bytes_survive_source_edits_and_removal(root, monkeypatch):
    captured = snapshot.capture(root, ['src/calc.py', 'notes.md'])
    assert captured['root'] == str(root.resolve())
    assert captured['files']['src/calc.py'] == {
        'text': 'def add(a, b):\r\n    return a + b\r\n',
        'sha256': hashlib.sha256((root / 'src/calc.py').read_bytes()).hexdigest(),
    }
    before = copy.deepcopy(captured)
    (root / 'src/calc.py').write_text('changed', encoding='utf-8')
    shutil.rmtree(root)
    monkeypatch.setattr(snapshot, '_posix_reader', lambda *args: pytest.fail('validation reopened source'))
    monkeypatch.setattr(snapshot, '_windows_reader', lambda *args: pytest.fail('validation reopened source'))
    assert snapshot.validate(captured) == before


@pytest.mark.parametrize('paths', [[], ['notes.md'] * 2, ['notes.md'] * 33, 'notes.md'])
def test_selection_requires_bounded_unique_explicit_list(root, paths):
    with pytest.raises(ValueError):
        snapshot.capture(root, paths)


def test_file_count_boundary_is_checked_for_capture_and_retained_records(root):
    paths = [f'file-{index}' for index in range(32)]
    for name in paths:
        (root / name).write_text('', encoding='utf-8')
    captured = snapshot.capture(root, paths)
    assert len(snapshot.validate(captured)['files']) == 32
    captured['files']['file-32'] = {'text': '', 'sha256': hashlib.sha256(b'').hexdigest()}
    captured['digest'] = digest(captured['files'])
    with pytest.raises(ValueError, match='1–32'):
        snapshot.validate(captured)


@pytest.mark.parametrize('name', ['/etc/passwd', '../notes.md', 'src/../notes.md',
                                 './notes.md', 'src//calc.py', '.', 'src/',
                                 'src\\calc.py', 'C:/notes.md', 'C:notes.md',
                                 '.git/config', 'src/.hg/store', '.svn/file',
                                 '.attune-harness/record.json', '.GIT/config', '', None])
def test_escaped_noncanonical_and_metadata_paths_refused(root, name):
    with pytest.raises(ValueError):
        snapshot.capture(root, [name])
    forged = {'root': str(root), 'files': {name: {'text': '', 'sha256': hashlib.sha256(b'').hexdigest()}},
              'digest': 'unused'}
    with pytest.raises(ValueError):
        snapshot.validate(forged)


@pytest.mark.parametrize('kind', ['file', 'directory', 'root'])
def test_symlinks_are_refused_at_every_component(root, kind):
    link = root.parent / 'linked-root' if kind == 'root' else root / 'linked'
    target = root if kind == 'root' else root / ('src' if kind == 'directory' else 'notes.md')
    try:
        link.symlink_to(target, target_is_directory=kind != 'file')
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f'Symlinks unavailable: {exc}')
    with pytest.raises(ValueError, match='symlink'):
        snapshot.capture(link if kind == 'root' else root,
                         ['notes.md'] if kind == 'root' else
                         ['linked/calc.py' if kind == 'directory' else 'linked'])


def test_binary_missing_and_directory_inputs_refused(root):
    (root / 'binary').write_bytes(b'\xff\x80')
    for name in ['binary', 'missing', 'src']:
        with pytest.raises(ValueError):
            snapshot.capture(root, [name])


@pytest.mark.skipif(os.name != 'posix', reason='POSIX openat interleaving; Windows needs native handle tests')
@pytest.mark.parametrize('component', ['leaf', 'parent', 'root'])
def test_swapped_symlink_is_refused_by_the_actual_descriptor_open(root, monkeypatch, component):
    outside = root.parent / 'outside'
    outside.mkdir()
    (outside / 'calc.py').write_text('OUTSIDE_SELECTED_SCOPE', encoding='utf-8')
    original_open = snapshot.os.open
    fired = False

    def swap_then_open(path, flags, *args, **kwargs):
        nonlocal fired
        expected = {'leaf': 'calc.py', 'parent': 'src', 'root': root.name}[component]
        if path == expected and not fired:
            fired = True
            selected = root / 'src/calc.py' if component == 'leaf' else root / 'src' if component == 'parent' else root
            selected.rename(selected.with_name(selected.name + '-retained'))
            selected.symlink_to(outside / 'calc.py' if component == 'leaf' else outside,
                                target_is_directory=component != 'leaf')
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(snapshot.os, 'open', swap_then_open)
    with pytest.raises(ValueError, match='Source open refused'):
        snapshot.capture(root, ['src/calc.py'])
    assert fired


@pytest.mark.skipif(os.name != 'posix', reason='POSIX descriptor lifetime behavior')
def test_parent_replaced_after_open_reads_only_the_pinned_directory(root, monkeypatch):
    outside = root.parent / 'outside'
    outside.mkdir()
    (outside / 'calc.py').write_text('OUTSIDE_SELECTED_SCOPE', encoding='utf-8')
    original_open = snapshot.os.open
    fired = False

    def swap_after_open(path, flags, *args, **kwargs):
        nonlocal fired
        fd = original_open(path, flags, *args, **kwargs)
        if path == 'src' and not fired:
            fired = True
            (root / 'src').rename(root / 'original-src')
            (root / 'src').symlink_to(outside, target_is_directory=True)
        return fd

    monkeypatch.setattr(snapshot.os, 'open', swap_after_open)
    captured = snapshot.capture(root, ['src/calc.py'])
    assert fired
    assert captured['files']['src/calc.py']['text'].startswith('def add')
    assert 'OUTSIDE_SELECTED_SCOPE' not in captured['files']['src/calc.py']['text']


@pytest.mark.skipif(os.name != 'posix', reason='POSIX nonblocking FIFO eligibility')
def test_fifo_is_refused_without_waiting_for_a_writer(root):
    os.mkfifo(root / 'pipe')
    with pytest.raises(ValueError, match='regular file'):
        snapshot.capture(root, ['pipe'])


@pytest.mark.skipif(os.name != 'nt', reason='Requires real Windows Native handle operations')
@pytest.mark.parametrize('component', ['leaf', 'parent'])
def test_windows_swaps_are_checked_by_native_child_open(root, monkeypatch, component):
    from attune_harness.windows_effects import Native

    outside = root.parent / 'outside'
    outside.mkdir()
    (outside / 'calc.py').write_text('OUTSIDE_SELECTED_SCOPE', encoding='utf-8')
    privilege = root / 'symlink-privilege'
    try:
        privilege.symlink_to(outside, target_is_directory=True)
        privilege.unlink()
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f'Symlinks unavailable: {exc}')
    original_child = Native.child
    fired = False

    def swap_then_child(self, parent, name, **kwargs):
        nonlocal fired
        if name == ('calc.py' if component == 'leaf' else 'src') and not fired:
            fired = True
            selected = root / 'src/calc.py' if component == 'leaf' else root / 'src'
            selected.rename(selected.with_name(selected.name + '-retained'))
            selected.symlink_to(outside / 'calc.py' if component == 'leaf' else outside,
                                target_is_directory=component != 'leaf')
        return original_child(self, parent, name, **kwargs)

    monkeypatch.setattr(Native, 'child', swap_then_child)
    with pytest.raises((ValueError, OSError)):
        snapshot.capture(root, ['src/calc.py'])
    assert fired


def test_aggregate_byte_limit_includes_utf8_and_accepts_exact_bound(root):
    (root / 'a').write_text('é' * (snapshot.MAX_BYTES // 4), encoding='utf-8')
    (root / 'b').write_bytes(b'x' * (snapshot.MAX_BYTES // 2))
    captured = snapshot.capture(root, ['a', 'b'])
    assert snapshot.validate(captured) == captured
    with (root / 'b').open('ab') as stream:
        stream.write(b'x')
    with pytest.raises(ValueError):
        snapshot.capture(root, ['a', 'b'])
    item = captured['files']['b']
    item['text'] += 'x'
    item['sha256'] = hashlib.sha256(item['text'].encode()).hexdigest()
    captured['digest'] = digest(captured['files'])
    with pytest.raises(ValueError, match='aggregate'):
        snapshot.validate(captured)


@pytest.mark.parametrize('mutation', ['text', 'hash', 'digest', 'extra', 'file-extra',
                                     'files-empty', 'files-type', 'root', 'non-text', 'surrogate'])
def test_contract_mutations_are_refused(root, mutation):
    captured = snapshot.capture(root, ['notes.md'])
    item = captured['files']['notes.md']
    if mutation == 'text':
        item['text'] += 'changed'
    elif mutation == 'hash':
        item['sha256'] = '0' * 64
    elif mutation == 'digest':
        captured['digest'] = '0' * 64
    elif mutation == 'extra':
        captured['extra'] = True
    elif mutation == 'file-extra':
        item['extra'] = True
    elif mutation == 'files-empty':
        captured['files'] = {}
    elif mutation == 'files-type':
        captured['files'] = []
    elif mutation == 'root':
        captured['root'] = 'relative'
    elif mutation == 'non-text':
        item['text'] = 7
    else:
        item['text'] = '\ud800'
    with pytest.raises(ValueError):
        snapshot.validate(captured)
