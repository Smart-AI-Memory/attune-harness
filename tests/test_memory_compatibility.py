"""Document-format probes through the native reader and attune-rag (D28).

The digest-pinned fixture is the sole retained attune-ai behavior witness.
These tests exercise its document formats without importing attune or writing sources.
"""
# qualify: platform
import json
import os
from pathlib import Path
import socket

import pytest

from attune_harness.memory_reader import NativeReader

FIXTURE = Path(__file__).parent / 'fixtures' / 'memory_compatibility.json'
pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Native descriptor reads require POSIX')


@pytest.fixture(autouse=True)
def isolated_services(monkeypatch):
    pytest.importorskip('attune_rag')
    def forbidden(*args, **kwargs):
        raise AssertionError('Document-format probe attempted network/provider access')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


@pytest.fixture
def legacy():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def seed_documents(tmp_path, legacy):
    sources = {}
    for entry in legacy['documents']:
        path = tmp_path / entry['root'] / entry['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (entry['body'] + '\n\n') * entry.get('repeat', 1) + entry.get('tail', '')
        path.write_text('# Aurora\n\n' + body, encoding='utf-8')
        sources[(entry['root'], entry['path'])] = path.read_bytes()
    return sources


def reader(root):
    return NativeReader(dict(schema_version=1, actor='p', owners=['p'], scopes=['global'],
                             classifications=['internal'], profiles=['claude'],
                             roots=[dict(id='r', path=str(root.resolve()), tier='personal',
                                         scope='global', owner='p', classification='internal')]))


@pytest.mark.parametrize('index', range(5))
def test_personal_reads_each_existing_kind_and_preserves_full_source(tmp_path, legacy, index):
    sources = seed_documents(tmp_path, legacy)
    entry = legacy['documents'][index]
    memory = reader(tmp_path / entry['root'])
    packet = memory.query(entry['query'], k=20)
    assert packet['status'] == 'available'
    hit = next(h for h in packet['items'] if h['locator']['path'] == entry['path'])
    resolved = memory.resolve(dict(hit, authority=memory.binding))
    assert resolved['text'].encode() == sources[(entry['root'], entry['path'])]
    assert all((tmp_path / root / path).read_bytes() == body for (root, path), body in sources.items())
    if entry.get('tail'):
        assert len(resolved['text']) > 500 and entry['tail'] in resolved['text']


def test_single_roots_preserve_document_identity(tmp_path, legacy):
    seed_documents(tmp_path, legacy)
    scoped = {}
    for name in ('global', 'project'):
        memory = reader(tmp_path / name)
        hit = next(h for h in memory.query('Aurora reminder', k=20)['items']
                   if h['locator']['path'] == 'aurora/decision.md')
        scoped[name] = memory.resolve(dict(hit, authority=memory.binding))['text']
    assert '09:15' in scoped['global']
    assert '10:45' in scoped['project']


def test_curated_legacy_links_and_unknown_fields_survive(tmp_path, legacy):
    entry = legacy['curated']
    source = tmp_path / 'curated' / entry['path']
    source.parent.mkdir()
    source.write_text(entry['content'], encoding='utf-8')
    before = source.read_bytes()
    memory = reader(source.parent)
    packet = memory.query('Aurora preservation policy', k=10)
    assert packet['status'] == 'available'
    hit = next(h for h in packet['items'] if h['locator']['path'] == entry['path'])
    assert memory.resolve(dict(hit, authority=memory.binding))['text'] == entry['content']
    assert source.read_bytes() == before
    assert 'review_response_id: synthetic-review' in source.read_text()
