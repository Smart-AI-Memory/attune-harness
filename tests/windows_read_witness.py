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
