"""Test-only copies of existing native samples; no extra filesystem operations."""

from contextlib import contextmanager
import json


class MetadataWitness:
    def __init__(self, monkeypatch, record_property, reader_type, native_type):
        self.stage, self.witness = 'setup', None
        self.frames, self.labels = [], {}
        self.diagnostic_errors = []
        self.record = record_property
        original_stat, original_info = reader_type._stat, native_type.info
        original_metadata = native_type.metadata
        original_child, original_volume = native_type.child, native_type.volume_handle

        def label(api, handle, name):
            key = (id(api), self.handle_id(handle))
            if key not in self.labels and len(self.labels) >= 256:
                self.labels.pop(next(iter(self.labels)))
            self.labels[key] = name[:1024]

        def volume(api, anchor, *args, **kwargs):
            result = original_volume(api, anchor, *args, **kwargs)
            label(api, result, str(anchor))
            return result

        def child(api, parent, name, *args, **kwargs):
            result = original_child(api, parent, name, *args, **kwargs)
            parent_label = self.labels.get((id(api), self.handle_id(parent)), '<unknown>')
            label(api, result, parent_label.rstrip('\\') + '\\' + name)
            return result

        def info(api, handle, kind, cls):
            result = original_info(api, handle, kind, cls)
            if self.matches(api, handle) and kind is api.Basic:
                frame = self.frames[-1][2]
                frame['basic_samples'].append({
                    name: int(getattr(result, name)) for name in
                    ('CreationTime', 'LastAccessTime', 'LastWriteTime', 'ChangeTime', 'FileAttributes')
                })
                if len(frame['basic_samples']) > 8:
                    frame['basic_samples'].pop(0)
                    frame['samples_truncated'] = True
            return result

        def metadata(api, handle, *args, **kwargs):
            result = original_metadata(api, handle, *args, **kwargs)
            if self.matches(api, handle):
                frame = self.frames[-1][2]
                frame['metadata_attributes'].append(int(result[0]['attributes']))
                if len(frame['metadata_attributes']) > 8:
                    frame['metadata_attributes'].pop(0)
                    frame['samples_truncated'] = True
            return result

        def observe_stat(reader, handle, *args, **kwargs):
            api, ident = reader._api, self.handle_id(handle)
            frame = dict(stage=self.stage, witness=self.witness, handle=ident,
                         path=self.labels.get((id(api), ident), '<unknown>'),
                         basic_samples=[], metadata_attributes=[], samples_truncated=False)
            self.frames.append((api, ident, frame))
            try:
                return original_stat(reader, handle, *args, **kwargs)
            except ValueError as error:
                if str(error) == 'Source metadata changed while observing it':
                    try:
                        self.record('raw_dotdot_metadata_refusal', json.dumps(frame, sort_keys=True))
                    except Exception as diagnostic_error:
                        self.diagnostic_errors[:] = [type(diagnostic_error).__name__]
                raise
            finally:
                self.frames.pop()

        monkeypatch.setattr(native_type, 'volume_handle', volume)
        monkeypatch.setattr(native_type, 'child', child)
        monkeypatch.setattr(native_type, 'info', info)
        monkeypatch.setattr(native_type, 'metadata', metadata)
        monkeypatch.setattr(reader_type, '_stat', observe_stat)

    @staticmethod
    def handle_id(handle):
        return getattr(handle, 'value', handle)

    def matches(self, api, handle):
        return bool(self.frames and self.frames[-1][:2] == (api, self.handle_id(handle)))

    @contextmanager
    def phase(self, stage, witness=None):
        previous = self.stage, self.witness
        self.stage, self.witness = stage, witness
        try:
            yield
        finally:
            self.stage, self.witness = previous


class ListingWitness:
    """Copy existing listing State returns; never repeat native observations."""

    def __init__(self, monkeypatch, record, reader_type, native_type, *, max_records=64,
                 max_bytes=1024 * 1024):
        from copy import deepcopy
        from threading import RLock, local, get_ident

        if not callable(getattr(reader_type, '_listing', None)):
            raise ValueError('Listing witness requires the original listing owner')
        self.labels, self.diagnostic_errors = {}, []
        self._local, self._lock = local(), RLock()
        self._records = self._bytes = self._invocation = self.active_invocations = 0
        self.truncated = False
        original_listing, original_stat = reader_type._listing, reader_type._stat
        original_child, original_volume = native_type.child, native_type.volume_handle

        def stack():
            if not hasattr(self._local, 'frames'):
                self._local.frames = []
            return self._local.frames

        self.frames = stack

        def diagnostic_error(error):
            with self._lock:
                self.diagnostic_errors[:] = [type(error).__name__]

        def label(api, handle, name):
            try:
                with self._lock:
                    key = (id(api), MetadataWitness.handle_id(handle))
                    if key not in self.labels and len(self.labels) >= 256:
                        self.labels.pop(next(iter(self.labels)))
                    self.labels[key] = name[:1024]
            except Exception as error:
                diagnostic_error(error)

        def volume(api, anchor, *args, **kwargs):
            result = original_volume(api, anchor, *args, **kwargs)
            try:
                label(api, result, str(anchor))
            except Exception as error:
                diagnostic_error(error)
            return result

        def child(api, parent, name, *args, **kwargs):
            result = original_child(api, parent, name, *args, **kwargs)
            try:
                with self._lock:
                    parent_label = self.labels.get((id(api), MetadataWitness.handle_id(parent)), '<unknown>')
                label(api, result, parent_label.rstrip('\\') + '\\' + name)
            except Exception as error:
                diagnostic_error(error)
            return result

        def observe_stat(reader, handle, *args, **kwargs):
            result = original_stat(reader, handle, *args, **kwargs)
            try:
                frames = stack()
                if (frames and frames[-1][0] is reader and frames[-1][1] is reader._api
                        and frames[-1][2] == MetadataWitness.handle_id(handle)):
                    frame = frames[-1][3]
                    frame['state_samples'] += 1
                    try:
                        if len(frame['states']) < 2:
                            frame['states'].append({'entry': deepcopy(result.entry),
                                                    'size': deepcopy(result.size),
                                                    'times': deepcopy(result.times)})
                        else:
                            frame['samples_truncated'] = True
                    except Exception as error:
                        if len(frame['copy_errors']) < 2:
                            frame['copy_errors'].append(type(error).__name__)
                        else:
                            frame['copy_errors_truncated'] = True
                        diagnostic_error(error)
            except Exception as error:
                diagnostic_error(error)
            return result

        def emit(frame, error):
            try:
                frame.update(event='windows_listing_refusal', schema_version=1,
                             error_type=type(error).__name__, error_message=str(error)[:1024],
                             complete_pair=frame['state_samples'] == 2 and not frame['copy_errors'])
                value = json.dumps(frame, sort_keys=True, allow_nan=False)
                if len(value.encode('utf-8')) > 32768:
                    frame = {**frame, 'states': [], 'state_values_omitted': True}
                    value = json.dumps(frame, sort_keys=True, allow_nan=False)
                size = len(value.encode('utf-8')) + 1
                with self._lock:
                    if self._records >= max_records or self._bytes + size > max_bytes:
                        self.truncated = True
                        return
                    self._records += 1
                    self._bytes += size
                    record('windows_listing_refusal', value)
            except Exception as diagnostic:
                diagnostic_error(diagnostic)

        def listing(reader, handle, *args, **kwargs):
            if not isinstance(reader, reader_type):
                return original_listing(reader, handle, *args, **kwargs)
            try:
                api, ident = reader._api, MetadataWitness.handle_id(handle)
                with self._lock:
                    self._invocation += 1
                    frame = {'thread': get_ident(), 'invocation': self._invocation,
                             'handle': ident, 'path': self.labels.get((id(api), ident), '<unknown>'),
                             'states': [], 'state_samples': 0, 'copy_errors': [], 'samples_truncated': False}
                frames = stack()
                frames.append((reader, api, ident, frame))
                with self._lock:
                    self.active_invocations += 1
            except Exception as error:
                diagnostic_error(error)
                return original_listing(reader, handle, *args, **kwargs)
            try:
                return original_listing(reader, handle, *args, **kwargs)
            except Exception as error:
                emit(frame, error)
                raise
            finally:
                frames.pop()
                with self._lock:
                    self.active_invocations -= 1

        monkeypatch.setattr(native_type, 'volume_handle', volume)
        monkeypatch.setattr(native_type, 'child', child)
        monkeypatch.setattr(reader_type, '_stat', observe_stat)
        monkeypatch.setattr(reader_type, '_listing', listing)
