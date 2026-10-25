"""Portable controls of the test observer, not native Windows qualification.

# qualify: platform
"""

import json
from types import SimpleNamespace

import pytest

from attune_harness.windows_reads import ReadRoot
from windows_read_witness import MetadataWitness


def sample(*, creation=1, access=1, attributes=16):
    return SimpleNamespace(CreationTime=creation, LastAccessTime=access,
                           LastWriteTime=2, ChangeTime=3, FileAttributes=attributes)


class API:
    Basic = SimpleNamespace

    def __init__(self, samples):
        self.samples = iter(samples)
        self.calls = []

    def volume_handle(self, anchor):
        self.calls.append(('volume', anchor))
        return 1

    def child(self, parent, name, **kwargs):
        self.calls.append(('child', parent, name, kwargs))
        return 2

    def info(self, handle, kind, cls):
        self.calls.append(('info', handle, kind, cls))
        return next(self.samples)

    def metadata(self, handle, parent_identity=None):
        self.calls.append(('metadata', handle, parent_identity))
        basic = self.info(handle, self.Basic, 0)
        return {'attributes': basic.FileAttributes}, 12, True


class Root:
    def __init__(self, api):
        self._api, self.result, self.error = api, None, None

    def _stat(self, *args, **kwargs):
        try:
            self.result = ReadRoot._stat(self, *args, **kwargs)
            return self.result
        except ValueError as error:
            self.error = error
            raise


def install(monkeypatch, samples, record=None):
    records = []
    recorder = record if record is not None else lambda key, value: records.append((key, value))
    observer = MetadataWitness(monkeypatch, recorder, Root, API)
    api = API(samples)
    parent = api.volume_handle('C:\\')
    handle = api.child(parent, 'fixture', writable=False, metadata_only=True)
    return observer, Root(api), handle, records


def test_refusal_copies_existing_samples_and_keeps_exception(monkeypatch):
    observer, root, handle, records = install(monkeypatch, [sample(), sample(), sample(creation=9)])
    with observer.phase('after', 'findings.jsonl'):
        with pytest.raises(ValueError, match='Source metadata changed') as caught:
            root._stat(handle, 'parent-identity')
    assert caught.value is root.error
    assert [row[0] for row in root._api.calls] == ['volume', 'child', 'info', 'metadata', 'info', 'info']
    assert root._api.calls[1] == ('child', 1, 'fixture', {'writable': False, 'metadata_only': True})
    assert records[0][0] == 'raw_dotdot_metadata_refusal'
    evidence = json.loads(records[0][1])
    assert evidence['stage'] == 'after' and evidence['witness'] == 'findings.jsonl'
    assert evidence['path'] == 'C:\\fixture' and evidence['handle'] == handle
    assert [row['CreationTime'] for row in evidence['basic_samples']] == [1, 1, 9]
    assert evidence['metadata_attributes'] == [16] and not evidence['samples_truncated']
    assert observer.frames == [] and (observer.stage, observer.witness) == ('setup', None)


def test_access_time_changes_still_pass_the_original_guard(monkeypatch):
    observer, root, handle, records = install(monkeypatch, [sample(), sample(access=2), sample(access=3)])
    result = root._stat(handle)
    assert result is root.result and result.times == {'creation': 1, 'last_write': 2, 'change': 3}
    assert records == [] and observer.frames == []
    assert len(root._api.calls) == 6


def test_intermediate_attributes_are_retained(monkeypatch):
    _, root, handle, records = install(monkeypatch, [sample(), sample(attributes=32), sample()])
    with pytest.raises(ValueError, match='Source metadata changed'):
        root._stat(handle)
    evidence = json.loads(records[0][1])
    assert evidence['metadata_attributes'] == [32]
    assert [row['FileAttributes'] for row in evidence['basic_samples']] == [16, 32, 16]


def test_broken_diagnostic_sink_does_not_mask_refusal(monkeypatch):
    def broken(*args):
        raise RuntimeError('diagnostic sink failed')
    observer, root, handle, _ = install(monkeypatch, [sample(), sample(), sample(creation=9)], broken)
    with pytest.raises(ValueError, match='Source metadata changed') as caught:
        root._stat(handle)
    assert caught.value is root.error and observer.frames == []
    assert observer.diagnostic_errors == ['RuntimeError']


def test_other_errors_pass_through_without_extra_calls(monkeypatch):
    error = OSError('synthetic existing API refusal')
    def refused(api, handle, kind, cls):
        api.calls.append(('refused', handle))
        raise error
    monkeypatch.setattr(API, 'info', refused)
    observer, root, handle, records = install(monkeypatch, [])
    with pytest.raises(OSError) as caught:
        root._stat(handle)
    assert caught.value is error and records == [] and observer.frames == []
    assert [row[0] for row in root._api.calls] == ['volume', 'child', 'refused']


def test_diagnostic_storage_is_bounded_and_handles_are_relabelled(monkeypatch):
    def repeated(root, handle):
        for _ in range(12):
            root._api.info(handle, root._api.Basic, 0)
            root._api.metadata(handle)
        raise ValueError('Source metadata changed while observing it')
    monkeypatch.setattr(Root, '_stat', repeated)
    observer, root, handle, records = install(monkeypatch, [sample() for _ in range(24)])
    for index in range(300):
        root._api.volume_handle('X:' + str(index))
    assert len(observer.labels) <= 256
    root._api.volume_handle('C:\\')
    root._api.child(1, 'latest')
    with pytest.raises(ValueError, match='Source metadata changed'):
        root._stat(handle)
    evidence = json.loads(records[0][1])
    assert len(evidence['basic_samples']) == len(evidence['metadata_attributes']) == 8
    assert evidence['samples_truncated'] and evidence['path'] == 'C:\\latest'
