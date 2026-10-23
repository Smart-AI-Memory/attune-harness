"""Scope dangling-target evidence to the selected namespace bindings.

# qualify: platform
"""

from contextlib import ExitStack, nullcontext
from copy import deepcopy
import os
from pathlib import PureWindowsPath
import struct
from types import SimpleNamespace

import pytest

from attune_harness import windows_reads
from attune_harness import windows_effects as native


def link_data(target):
    encoded = target.encode('utf-16-le')
    return (struct.pack('<IHHHHHHI', 0xA000000C, 12 + len(encoded), 0,
                        0, len(encoded), 0, 0, 1) + encoded)


@pytest.fixture
def target_walk(monkeypatch):
    """Portable namespace model; this does not qualify any native Windows API."""
    def node(identity, *, directory=True, data=None):
        return SimpleNamespace(identity={'volume': 1, 'file_id': identity},
                               directory=directory, data=data, children={},
                               attributes=0x400 if data is not None else 0,
                               times=dict(creation=1, last_write=2, change=3),
                               size=0, links=1, security='unchanged')

    volume, ancestor, selected = (node(name) for name in ('volume', 'ancestor', 'selected'))
    link = node('link', directory=False, data=link_data('missing.jsonl'))
    volume.children['base'] = ancestor
    ancestor.children['selected'] = selected
    selected.children['hop.jsonl'] = link

    def child(parent, name, **kwargs):
        assert kwargs.get('writable') is False
        # NtCreateFile's case-insensitive lookup is not exact-name admission.
        for actual, value in parent.children.items():
            if actual.casefold() == name.casefold():
                return value
        raise OSError(0xC0000034, 'missing exact leaf')

    api = SimpleNamespace(volume=lambda path: path.anchor,
                          volume_handle=lambda anchor: volume,
                          owned=nullcontext, child=child,
                          iter_names=lambda parent: iter(sorted(parent.children)))
    root = object.__new__(windows_reads.ReadRoot)
    root._api = api

    def stat(handle):
        return windows_reads._State(
            dict(kind='directory' if handle.directory else 'file',
                 identity=deepcopy(handle.identity), attributes=handle.attributes,
                 security_sha256=handle.security, links=handle.links),
            handle.size, deepcopy(handle.times))

    root._stat = stat
    root._probe_state = lambda handle: (deepcopy(handle.identity), deepcopy(handle.times),
                                        handle.attributes, handle.directory,
                                        handle.links, handle.size)
    root._reparse_data = lambda handle: handle.data
    monkeypatch.setattr(windows_reads, 'Path', PureWindowsPath)
    monkeypatch.setattr(windows_reads, '_require_volume_root', lambda api, handle: None)

    def walk(mutate, *, chained=False):
        name = 'hop.jsonl' if chained else 'missing.jsonl'
        path = PureWindowsPath(r'C:\base\selected') / name
        with ExitStack() as handles:
            checks = []
            assert root._target_absent(path, handles, checks, {}) is True
            mutate()
            for check in reversed(checks):
                check()

    return SimpleNamespace(walk=walk, volume=volume, ancestor=ancestor,
                           selected=selected, link=link, node=node, api=api)


@pytest.mark.parametrize('chained', [False, True], ids=['direct', 'chained'])
@pytest.mark.parametrize('change', ['names', 'times', 'names-and-times'])
def test_unrelated_ancestor_changes_do_not_invalidate_confirmed_absence(target_walk, change, chained):
    model = target_walk

    def mutate():
        if 'names' in change:
            model.ancestor.children['peer'] = model.node('peer')
        if 'times' in change:
            model.ancestor.times['last_write'] += 1
            model.ancestor.times['change'] += 1

    model.walk(mutate, chained=chained)


@pytest.mark.parametrize('change', ['sibling', 'times', 'target-appears'])
def test_missing_parent_namespace_changes_still_refuse(target_walk, change):
    model = target_walk

    def mutate():
        if change == 'times':
            model.selected.times['change'] += 1
        else:
            name = 'missing.jsonl' if change == 'target-appears' else 'peer'
            model.selected.children[name] = model.node(name, directory=False)

    with pytest.raises(ValueError, match='Absent target namespace changed'):
        model.walk(mutate)


@pytest.mark.parametrize('change', [
    'removed', 'case-alias', 'replaced', 'identity', 'attributes', 'type',
    'links', 'size', 'parent-security', 'parent-identity',
])
def test_selected_target_binding_changes_still_refuse(target_walk, change):
    model = target_walk

    def mutate():
        if change in ('removed', 'case-alias'):
            original = model.ancestor.children.pop('selected')
            if change == 'case-alias':
                model.ancestor.children['Selected'] = original
        elif change == 'replaced':
            # The retained handle still names the original directory.
            model.ancestor.children['selected'] = model.node('replacement')
        elif change == 'identity':
            model.ancestor.identity['file_id'] = 'changed'
        elif change == 'attributes':
            model.ancestor.attributes = 0x400
        elif change == 'type':
            model.ancestor.directory = False
        elif change == 'links':
            model.ancestor.links += 1
        elif change == 'size':
            model.ancestor.size += 1
        elif change == 'parent-security':
            model.ancestor.security = 'changed'
        else:
            model.ancestor.identity['file_id'] = 'changed'

    with pytest.raises((ValueError, OSError)):
        model.walk(mutate)


@pytest.mark.parametrize('change', ['times', 'reparse-data'])
def test_target_link_changes_still_refuse(target_walk, change):
    model = target_walk

    def mutate():
        if change == 'times':
            model.link.times['change'] += 1
        else:
            model.link.data = link_data('live.jsonl')

    with pytest.raises(ValueError, match='target (metadata changed|was retargeted)'):
        model.walk(mutate, chained=True)


def test_missing_target_recheck_does_not_convert_access_failure_to_absence(target_walk):
    model = target_walk
    original = model.api.child

    def mutate():
        def denied(parent, name, **kwargs):
            if name == 'missing.jsonl':
                raise OSError(0xC0000022, 'access denied')
            return original(parent, name, **kwargs)
        model.api.child = denied

    with pytest.raises(OSError) as error:
        model.walk(mutate)
    assert error.value.errno == 0xC0000022


def test_target_ancestor_changes_during_enumeration_still_refuse(target_walk):
    model = target_walk
    original = model.api.iter_names

    def changing(parent):
        names = tuple(original(parent))
        if parent is model.ancestor:
            parent.times['change'] += 1
        return iter(names)

    model.api.iter_names = changing
    with pytest.raises(ValueError, match='Source directory changed while enumerating it'):
        model.walk(lambda: None)


def test_nondirectory_target_prefix_retains_full_timestamp_evidence(target_walk):
    model = target_walk
    model.selected.directory = False

    def mutate():
        model.selected.times['change'] += 1

    with pytest.raises(ValueError, match='Symbolic-link target metadata changed'):
        model.walk(mutate)


@pytest.mark.skipif(os.name != 'nt', reason='Actual Windows local-NTFS target observations')
@pytest.mark.parametrize('change', ['ancestor-sibling', 'missing-parent-sibling',
                                  'selected-replacement', 'link-retarget'])
def test_native_target_ancestor_churn_and_path_change_controls(tmp_path, monkeypatch, change, record_property):
    raw = tmp_path / 'raw'
    raw.mkdir()
    ancestor = tmp_path / 'target-ancestor'
    selected = ancestor / 'selected'
    selected.mkdir(parents=True)
    hop = selected / 'hop.jsonl'
    source = raw / 'findings.jsonl'
    try:
        hop.symlink_to('missing.jsonl')
        # Windows can refuse renaming a directory with open descendants. The
        # replacement control retains the directory, but no child link handle.
        target = selected / 'missing.jsonl' if change == 'selected-replacement' else hop
        source.symlink_to(target)
    except OSError as error:
        if getattr(error, 'winerror', None) == 1314:
            pytest.skip('Symbolic-link fixture unavailable (WinError 1314)')
        raise

    calls = []
    original = windows_reads.ReadRoot._target_absent

    def changed(self, path, handles, checks, seen):
        answer = original(self, path, handles, checks, seen)
        assert answer is True
        if change == 'ancestor-sibling':
            (ancestor / 'peer').mkdir()
        elif change == 'missing-parent-sibling':
            (selected / 'peer').mkdir()
        elif change == 'selected-replacement':
            selected.rename(ancestor / 'moved')
            selected.mkdir()
        else:
            hop.unlink()
            hop.symlink_to('different-missing.jsonl')
        calls.append(change)
        return answer

    def forbidden_content(*args, **kwargs):
        pytest.fail('Target absence requested content access')

    monkeypatch.setattr(windows_reads.ReadRoot, '_target_absent', changed)
    monkeypatch.setattr(native.Native, 'read', forbidden_content)
    with windows_reads.open_read_root(raw) as root:
        if change == 'ancestor-sibling':
            assert root.read_optional('findings.jsonl', max_bytes=100,
                                      dangling_symlink_absent=True) is None
        else:
            with pytest.raises((ValueError, OSError)):
                root.read_optional('findings.jsonl', max_bytes=100,
                                   dangling_symlink_absent=True)
    assert calls == [change]
    record_property('target_namespace_change', change)
