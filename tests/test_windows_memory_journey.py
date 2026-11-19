"""Offline recall, complete-source resolve and refresh through fresh native shells.

The platform qualifier runs these installed CLI journeys on Windows/Python 3.12
in PowerShell 5.1 and 7. Other platforms execute the same sequence as a control.
"""
# qualify: platform

import json
import os

import pytest

from attune_harness.memory_reader import SIDECARS
from attune_harness.review_contract import digest
from test_memory_reader import FIXTURE, config_for, seed_raw
from test_windows_task_journey import run_cli


def snapshot(root):
    """Observe every source/input file and its write time, including new sidecars."""
    return {path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob('*') if path.is_file()}


@pytest.mark.parametrize('engine', ['powershell.exe', 'pwsh.exe'] if os.name == 'nt' else ['posix-control'])
@pytest.mark.parametrize('directory_name', ['plain', "space's $literal` café 雪"])
def test_offline_memory_recall_resolve_refresh(tmp_path, monkeypatch, engine, directory_name):
    """Refresh replaces actual captured handles after source, sidecar and deletion changes."""
    home = tmp_path.resolve() / directory_name
    home.mkdir()
    sources, inputs = home / 'sources', home / 'inputs'
    inputs.mkdir()
    raw, personal, curated = (sources / tier for tier in ('raw', 'personal', 'curated'))
    raw_text = 'Aurora policy raw Ω café 雪 "quoted" evidence.\r\n'
    rows = seed_raw(raw, [dict(id='note', text=raw_text, type='note', cwd='project-a')])
    personal_source = personal / 'nested café' / 'policy.md'
    personal_source.parent.mkdir(parents=True)
    personal_bytes = '# Aurora\r\n\r\nAurora policy personal Ω café 雪 complete evidence.\r\n'.encode('utf-8')
    personal_source.write_bytes(personal_bytes)
    curated.mkdir()
    curated_source = curated / FIXTURE['curated']['path']
    curated_bytes = (FIXTURE['curated']['content'] + '\nAurora curated Ω café 雪.\n').encode('utf-8')
    curated_source.write_bytes(curated_bytes)
    config = inputs / 'memory.json'
    config.write_text(json.dumps(config_for(
        ('raw', raw, 'raw', 'project-a'), ('personal', personal, 'personal', 'global'),
        ('curated', curated, 'curated', 'global')), ensure_ascii=False), encoding='utf-8')

    # Console entry points load this test-only guard in the actual child.
    # A parent monkeypatch would leave the fresh PowerShell/CLI process unguarded.
    guard = home / 'offline-guard'
    guard.mkdir()
    started, denied = guard / 'started.txt', guard / 'denied.txt'
    (guard / 'sitecustomize.py').write_text(
        'import socket\nfrom pathlib import Path\n'
        'def forbidden(*args, **kwargs):\n'
        f'    with Path({str(denied)!r}).open("ab") as log: log.write(b"denied\\n")\n'
        '    raise AssertionError("Offline memory journey attempted network access")\n'
        'socket.socket.connect = forbidden\nsocket.socket.connect_ex = forbidden\n'
        'socket.create_connection = forbidden\nsocket.getaddrinfo = forbidden\n'
        f'with Path({str(started)!r}).open("ab") as log: log.write(b"guarded\\n")\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('PYTHONPATH', str(guard))
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    calls = 0

    def memory(*arguments, expected_code=0):
        nonlocal calls
        code, result, output = run_cli(['memory', '--config', str(config), *arguments], home, engine)
        calls += 1
        assert code == expected_code and result, output
        assert started.read_bytes().splitlines() == [b'guarded'] * calls
        assert not denied.exists(), 'The CLI attempted network access'
        return result

    original_sources, original_inputs = snapshot(sources), snapshot(inputs)
    packet = memory('recall', 'Aurora policy', '--k', '10', '--max-chars', '12')
    assert packet['status'] == 'available' and packet['problems'] == []
    items = {item['handle']['locator']['root_id']: item for item in packet['items']}
    assert set(items) == {'raw', 'personal', 'curated'}
    assert sum(len(item['excerpt']) for item in items.values()) <= 12
    assert all(item['truncated'] and item['classification'] == 'internal' for item in items.values())
    assert items['personal']['handle']['locator']['path'] == 'nested café/policy.md'
    assert snapshot(sources) == original_sources and snapshot(inputs) == original_inputs
    context = inputs / 'context.json'
    context.write_text(json.dumps(packet, ensure_ascii=False), encoding='utf-8')
    handles = {}
    for tier, item in items.items():
        handles[tier] = inputs / f'{tier}-handle.json'
        handles[tier].write_text(json.dumps(item['handle'], ensure_ascii=False), encoding='utf-8')
    saved_inputs = snapshot(inputs)
    expected_text = {'raw': raw_text, 'personal': personal_bytes.decode('utf-8'),
                     'curated': curated_bytes.decode('utf-8')}
    for tier, path in handles.items():
        resolved = memory('resolve', str(path))
        assert resolved['text'] == expected_text[tier]
        assert resolved['version'] == items[tier]['handle']['version']
        assert resolved['authority'] == packet['authority']
    refreshed = memory('refresh', str(context))
    assert refreshed['invalidated_ids'] == [] and refreshed['replaces'] == digest(packet)
    assert {item['handle']['id']: item['handle'] for item in refreshed['context']['items']} == {
        item['handle']['id']: item['handle'] for item in items.values()}
    assert snapshot(sources) == original_sources and snapshot(inputs) == saved_inputs

    rows[0]['text'] += 'Aurora corrected Ω.'
    (raw / 'findings.jsonl').write_bytes((json.dumps(rows[0], ensure_ascii=False) + '\n').encode('utf-8'))
    personal_source.write_bytes(personal_bytes + b'Aurora corrected personal advice.\r\n')
    (curated / SIDECARS[0]).write_text(
        json.dumps({FIXTURE['curated']['path']: 'Aurora policy corrected curated summary'}), encoding='utf-8')
    corrected_sources = snapshot(sources)
    refreshed = memory('refresh', str(context))
    assert refreshed['replaces'] == digest(packet)
    assert set(refreshed['invalidated_ids']) == {item['handle']['id'] for item in items.values()}
    current = refreshed['context']
    assert current['status'] == 'available' and current['problems'] == []
    replacements = {item['handle']['locator']['root_id']: item for item in current['items']}
    assert set(replacements) == set(items)
    expected_text.update(raw=rows[0]['text'], personal=personal_source.read_bytes().decode('utf-8'))
    for tier, path in handles.items():
        failure = memory('resolve', str(path), expected_code=2)
        assert failure['error'] == 'ValueError' and 'refresh context' in failure['detail']
        assert replacements[tier]['handle']['id'] == items[tier]['handle']['id']
        assert replacements[tier]['handle']['version'] != items[tier]['handle']['version']
        replacement = inputs / f'{tier}-replacement.json'
        replacement.write_text(json.dumps(replacements[tier]['handle'], ensure_ascii=False), encoding='utf-8')
        assert memory('resolve', str(replacement))['text'] == expected_text[tier]
    assert snapshot(sources) == corrected_sources
    current_inputs = snapshot(inputs)
    assert {name: current_inputs[name] for name in saved_inputs} == saved_inputs

    current_path = inputs / 'current-context.json'
    current_path.write_text(json.dumps(current, ensure_ascii=False), encoding='utf-8')
    # Withdraw only this fixture's inputs and keep both captured packets intact.
    (raw / 'findings.jsonl').write_bytes(b'')
    personal_source.unlink()
    curated_source.unlink()
    withdrawn_sources, saved_inputs = snapshot(sources), snapshot(inputs)
    withdrawn = memory('refresh', str(current_path))
    assert withdrawn['replaces'] == digest(current)
    assert set(withdrawn['invalidated_ids']) == {item['handle']['id'] for item in replacements.values()}
    assert withdrawn['context']['status'] == 'empty' and withdrawn['context']['items'] == []
    assert withdrawn['context']['problems'] == []
    for tier in replacements:
        failure = memory('resolve', str(inputs / f'{tier}-replacement.json'), expected_code=2)
        assert failure['error'] in ('KeyError', 'FileNotFoundError', 'ValueError')
    recalled = memory('recall', 'Aurora policy')
    assert recalled['status'] == 'empty' and recalled['items'] == [] and recalled['problems'] == []
    assert snapshot(sources) == withdrawn_sources and snapshot(inputs) == saved_inputs
