"""Memory JSON remains lossless on narrow output encodings.

# qualify: platform
"""

import io
import json
import socket
import sys

import pytest

from attune_harness.memory_cli import main as memory_main
from test_memory_reader import config_for, seed_raw


@pytest.mark.parametrize('encoding', ['ascii', 'cp1252', 'utf-8'])
def test_recall_resolve_refresh_json_preserves_unicode_and_saved_bytes(tmp_path, monkeypatch, encoding):
    def forbidden(*args, **kwargs):
        raise AssertionError('Memory JSON encoding test attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    text = 'Aurora Ω ⟨evidence⟩ café e\u0301 🪁 "quoted" \\ preserved.\r\n'
    root = tmp_path / 'raw Ω'
    rows = seed_raw(root, [dict(id='row', text=text, type='finding', cwd='project-a')])
    source = root / 'findings.jsonl'
    source.write_bytes((json.dumps(rows[0], ensure_ascii=False) + '\n').encode('utf-8'))
    config = tmp_path / 'memory.json'
    config.write_bytes(json.dumps(config_for(('r', root, 'raw', 'project-a')), ensure_ascii=False).encode('utf-8'))
    unchanged = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (source, config)}

    def invoke(*arguments):
        data = io.BytesIO()
        stream = io.TextIOWrapper(data, encoding=encoding, write_through=True)
        with monkeypatch.context() as captured:
            captured.setattr(sys, 'stdout', stream)
            try:
                code = memory_main(['--config', str(config), *arguments])
                stream.flush()
            finally:
                stream.detach()
        wire = data.getvalue()
        assert wire.endswith(b'\n') and wire.isascii()
        return code, json.loads(wire.decode('ascii'))

    code, packet = invoke('recall', 'Aurora')
    assert code == 0 and packet['status'] == 'available' and packet['problems'] == []
    assert packet['items'][0]['excerpt'] == text
    handle = tmp_path / 'handle.json'
    handle.write_bytes(json.dumps(packet['items'][0]['handle'], ensure_ascii=False).encode('utf-8'))
    context = tmp_path / 'context.json'
    context.write_bytes(json.dumps(packet, ensure_ascii=False).encode('utf-8'))
    unchanged.update({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (handle, context)})
    code, resolved = invoke('resolve', str(handle))
    assert code == 0 and resolved['text'] == text
    code, refreshed = invoke('refresh', str(context))
    assert code == 0 and refreshed['invalidated_ids'] == []
    assert refreshed['context']['items'][0]['excerpt'] == text
    assert {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in unchanged} == unchanged
