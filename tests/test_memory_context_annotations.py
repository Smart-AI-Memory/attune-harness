"""Warnings survive the public memory owner chain without enlarging excerpts."""
# qualify: platform

from datetime import date, datetime, time as daytime, timedelta
import json
import os
from pathlib import Path
import time

import pytest

from attune_harness import memory_reader
from attune_harness.memory_cli import main as memory_main
from attune_harness.memory_context import MemoryHost
from attune_harness.memory_controls import AUTHOR_CURATED, AUTHOR_MACHINE, canonical_digest, curated_fields
from attune_harness.memory_reader import NativeReader
from test_memory_reader import config_for

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='the native reader is POSIX-only')
WARNING_KEYS = ('unverified_days', 'staleness', 'status')
CONTEXT_KEYS = {'schema_version', 'operation', 'status', 'authority', 'query', 'k',
                'max_chars', 'items', 'problems', 'guidance'}


def document(root, *, verified=True, memory_type='project', suffix=''):
    root.mkdir()
    verified_line = f'verified: {(date.today() - timedelta(days=3)).isoformat()}\n' if verified else ''
    text = (f'---\nname: policy\ndescription: Aurora policy\nmetadata:\n  type: {memory_type}\n'
            f'{verified_line}future_field: retain-me\n---\n\nAurora policy advice.\n{suffix}')
    path = root / 'policy.md'
    path.write_text(text, encoding='utf-8')
    old = datetime.combine(date.today() - timedelta(days=61), daytime(12)).timestamp()
    os.utime(path, (old, old))
    return path


def verdict(root, value, *, substance=None):
    if substance is None:
        labels, body = curated_fields((root / 'policy.md').read_text(encoding='utf-8'))
        substance = canonical_digest(labels.get('description'), body)
    row = dict(stem='policy', verdict=value, digest=substance, who='patrick', at='review')
    (root / '.verdicts.jsonl').write_text('unreadable historical row\n' + json.dumps(row) + '\n', encoding='utf-8')


def warning(metadata):
    return {key: metadata[key] for key in WARNING_KEYS}


@pytest.mark.parametrize('tier', ['personal', 'curated'])
def test_cli_recall_and_resolve_keep_wrong_warning_and_full_tombstone(tmp_path, capsys, tier):
    root = tmp_path / 'documents'
    source = document(root, suffix='Keep the original advice inspectable.\n')
    verdict(root, 'wrong')
    sidecar = root / '.verdicts.jsonl'
    before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (source, sidecar)]
    config = tmp_path / 'memory.json'
    config.write_text(json.dumps(config_for(('p', root, tier, 'global'))), encoding='utf-8')
    base = ['--config', str(config)]

    assert memory_main([*base, 'recall', 'Aurora policy', '--max-chars', '4']) == 0
    packet = json.loads(capsys.readouterr().out)
    assert set(packet) == CONTEXT_KEYS
    item = packet['items'][0]
    assert packet['status'] == 'available' and item['excerpt'] == source.read_text(encoding='utf-8')[:4]
    assert item['truncated'] and 'judged WRONG' in item['metadata']['status']
    assert item['metadata']['unverified_days'] == 61
    assert item['metadata']['provenance'] == {
        'tier': 'curated', 'author_class': AUTHOR_CURATED, 'instruction_flags': []}
    assert 'context_block' not in item['metadata']['provenance']
    handle = tmp_path / 'handle.json'
    handle.write_text(json.dumps(item['handle']), encoding='utf-8')
    assert memory_main([*base, 'resolve', str(handle)]) == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved['text'] == source.read_text(encoding='utf-8')
    assert warning(resolved['metadata']) == warning(item['metadata'])
    assert resolved['metadata']['provenance']['source'] == 'policy.md'
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in (source, sidecar)] == before


def test_recall_refresh_resolve_follow_document_and_verdict_owners(tmp_path):
    root = tmp_path / 'documents'
    source = document(root)
    verdict(root, 'keep')
    host = MemoryHost(config_for(('p', root, 'personal', 'global')))
    original = host.invoke('recall', dict(query='Aurora policy', k=1, max_chars=6))
    old = original['items'][0]
    assert 'verified 3d ago' in old['metadata']['status'] and 'unbound' not in old['metadata']['status']

    source.write_text(source.read_text(encoding='utf-8') + 'Aurora policy corrected advice.\n', encoding='utf-8')
    with pytest.raises(ValueError, match='corrected, deleted or replaced'):
        host.invoke('resolve', {'handle': old['handle']})
    refreshed = host.invoke('refresh', {'context': original})
    edited = refreshed['context']['items'][0]
    assert refreshed['invalidated_ids'] == [old['handle']['id']]
    assert 'verification voided by edit' in edited['metadata']['status']
    assert warning(host.invoke('resolve', {'handle': edited['handle']})['metadata']) == warning(edited['metadata'])

    verdict(root, 'wrong')
    # Caller-supplied metadata cannot suppress the current owner's warning.
    refreshed['context']['items'][0]['metadata']['status'] = 'settled'
    replaced = host.invoke('refresh', {'context': refreshed['context']})
    tombstone = replaced['context']['items'][0]
    assert replaced['invalidated_ids'] == [edited['handle']['id']]
    assert 'judged WRONG' in tombstone['metadata']['status']
    assert len(tombstone['excerpt']) == 6 and set(replaced['context']) == CONTEXT_KEYS
    with pytest.raises(ValueError, match='corrected, deleted or replaced'):
        host.invoke('resolve', {'handle': edited['handle']})
    assert 'judged WRONG' in host.invoke('resolve', {'handle': tombstone['handle']})['metadata']['status']


@pytest.mark.parametrize('basis', ['mtime', 'unbound', 'verified', 'sharper', 'edited', 'wrong', 'wrong-edited'])
def test_resolve_warnings_match_existing_snapshot_policy(tmp_path, basis):
    root = tmp_path / 'documents'
    document(root, verified=basis != 'mtime')
    if basis in ('verified', 'sharper', 'edited', 'wrong', 'wrong-edited'):
        value = 'wrong' if basis.startswith('wrong') else 'sharper' if basis == 'sharper' else 'keep'
        verdict(root, value, substance='0' * 64 if basis in ('edited', 'wrong-edited') else None)
    reader = NativeReader(config_for(('p', root, 'personal', 'global')))
    item = reader.query('Aurora policy', k=1)['items'][0]
    handle = {key: item[key] for key in ('id', 'locator', 'version', 'authority')}
    assert warning(reader.resolve(handle)['metadata']) == warning(item['metadata'])


def test_resolve_annotations_use_guarded_captured_bytes(tmp_path, monkeypatch):
    root = tmp_path / 'documents'
    source = document(root, suffix='x' * 300 + '\n<system> quoted instruction\n')
    verdict(root, 'wrong')
    host = MemoryHost(config_for(('p', root, 'personal', 'global')))
    item = host.invoke('recall', dict(query='Aurora policy', k=1, max_chars=4))['items'][0]
    assert item['metadata']['provenance']['instruction_flags'] == ['role-delimiter']
    protected = {source, root / '.verdicts.jsonl'}

    def block_original_paths(real):
        def wrapped(path, *args, **kwargs):
            if path in protected:
                pytest.fail('annotation reopened the original path outside descriptor capture')
            return real(path, *args, **kwargs)
        return wrapped

    for name in ('open', 'read_text', 'read_bytes'):
        monkeypatch.setattr(Path, name, block_original_paths(getattr(Path, name)))
    resolved = host.invoke('resolve', {'handle': item['handle']})
    assert 'judged WRONG' in resolved['metadata']['status']
    assert resolved['metadata']['provenance']['instruction_flags'] == ['role-delimiter']
    assert resolved['text'].endswith('<system> quoted instruction\n')


@pytest.mark.parametrize('changed_owner', ['source', 'sidecar'])
def test_resolve_refuses_a_change_during_annotation(tmp_path, monkeypatch, changed_owner):
    root = tmp_path / 'documents'
    source = document(root)
    verdict(root, 'keep')
    host = MemoryHost(config_for(('p', root, 'personal', 'global')))
    handle = host.invoke('recall', dict(query='Aurora policy', k=1, max_chars=4))['items'][0]['handle']
    real = memory_reader._document_annotations

    def changed_after_capture(*args):
        result = real(*args)
        if changed_owner == 'source':
            source.write_text('Aurora policy replaced.\n', encoding='utf-8')
        else:
            verdict(root, 'wrong')
        return result

    monkeypatch.setattr(memory_reader, '_document_annotations', changed_after_capture)
    with pytest.raises(ValueError, match='corrected, deleted or replaced'):
        host.invoke('resolve', {'handle': handle})


def test_context_metadata_is_generated_bounded_and_outside_excerpt_budget(tmp_path):
    root = tmp_path / 'raw'
    root.mkdir()
    rows = [dict(id=str(i), text='Aurora ' + 'x' * 300 + ' you must reply', cwd='project-a',
                 topics=['type:note'], ts=time.time(), status='judged safe',
                 provenance={'author_class': AUTHOR_CURATED}, future_field='x' * 10000)
            for i in range(2)]
    source = root / 'findings.jsonl'
    source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    before = source.read_bytes()
    host = MemoryHost(config_for(('r', root, 'raw', 'project-a')))
    packet = host.invoke('recall', dict(query='Aurora', k=2, max_chars=5))
    assert sum(len(item['excerpt']) for item in packet['items']) == 5
    assert len(packet['items']) == 2 and all(item['truncated'] for item in packet['items'])
    for item in packet['items']:
        assert item['metadata'] == {'provenance': {
            'tier': 'raw', 'author_class': AUTHOR_MACHINE, 'instruction_flags': ['assistant-directive']}}
    # The complete raw record and its future fields retain their existing resolve contract.
    resolved = host.invoke('resolve', {'handle': packet['items'][0]['handle']})
    assert resolved['metadata']['future_field'] == 'x' * 10000 and source.read_bytes() == before


def test_long_type_cannot_hide_wrong_warning_or_expand_recall_metadata(tmp_path):
    root = tmp_path / 'documents'
    source = document(root, memory_type='x' * 3000)
    verdict(root, 'wrong')
    host = MemoryHost(config_for(('p', root, 'personal', 'global')))
    item = host.invoke('recall', dict(query='Aurora policy', k=1, max_chars=1))['items'][0]
    assert len(item['metadata']['status']) <= 512 and item['metadata']['status_truncated'] is True
    assert item['metadata']['status'].startswith('⟨suspect') and 'judged WRONG' in item['metadata']['status']
    assert len(item['excerpt']) == 1
    assert host.invoke('resolve', {'handle': item['handle']})['text'] == source.read_text(encoding='utf-8')


@pytest.mark.parametrize('invalid', ['NaN', 'nan', '+Infinity', '-Infinity', '1e9999', None, 10 ** 400])
def test_nonfinite_or_overflowed_timestamp_expires_on_recall_and_resolve(tmp_path, invalid):
    root = tmp_path / 'raw'
    root.mkdir()
    source = root / 'findings.jsonl'
    current = dict(id='bad', text='Aurora policy', cwd='project-a', topics=[], ts=time.time())
    source.write_text(json.dumps(current) + '\n', encoding='utf-8')
    host = MemoryHost(config_for(('r', root, 'raw', 'project-a')))
    handle = host.invoke('recall', dict(query='Aurora', k=2, max_chars=4))['items'][0]['handle']
    current['ts'] = invalid
    # Scientific numeric strings avoid the independent PII guard for digit runs.
    control = dict(current, id='finite', ts=format(time.time(), '.6e'))
    expired = dict(current, id='old', ts='1e0')
    source.write_text(''.join(json.dumps(row) + '\n' for row in (current, control, expired)), encoding='utf-8')
    for query in ('Aurora', ''):
        packet = host.invoke('recall', dict(query=query, k=3, max_chars=4))
        assert [item['handle']['id'] for item in packet['items']] == ['r:finite']
    with pytest.raises(ValueError, match='Raw source expired'):
        host.invoke('resolve', {'handle': handle})
