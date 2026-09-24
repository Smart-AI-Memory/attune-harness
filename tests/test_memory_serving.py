"""Host eligibility checks over stale Redis candidates, without a live service."""
# qualify: platform

import json
import os
from pathlib import Path

import pytest

from attune_harness import memory_redis, memory_serving
from attune_harness.memory_cli import main
from attune_harness.memory_redis import PREFIX, RedisMemory, serve
from test_memory_reader import config_for
from test_memory_redis import FakeError, FakeRedis, SETTINGS


class Candidates(FakeRedis):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows
        self.membership = None

    def execute_command(self, name, *args):
        if name == 'SMISMEMBER' and self.membership is not None:
            if isinstance(self.membership, Exception):
                raise self.membership
            return self.membership
        return super().execute_command(name, *args)

    def _function(self, name, args):
        if name == 'recall_digest':
            return [json.dumps({**row, 'edges': []}) for row in self.rows]
        return super()._function(name, args)


def render(fake, config=None, **kwargs):
    return serve(config or {'redis': SETTINGS}, connect_with=lambda settings: RedisMemory(
        fake, settings, 'fixture', errors=(FakeError,)), **kwargs)


def test_withdrawn_digest_is_filtered_before_limit_and_direct_read_retains_it():
    fake = Candidates([{'id': 'withdrawn', 'name': 'stale'}, {'id': 'n2', 'name': 'current'}])
    text, reason = render(fake, limit=1)
    assert reason is None and '- n2' in text and 'withdrawn' not in text
    assert ('SMISMEMBER', PREFIX + 'status:active', 'withdrawn', 'n2') in fake.calls
    assert 'source=redis; trust=untrusted-evidence' in text
    assert 'disclose memory IDs' in text
    direct = RedisMemory(fake, SETTINGS, 'fixture').digest()
    assert direct['items'][0]['id'] == 'withdrawn'
    fake.sets[PREFIX + 'status:active'] = set()
    assert render(fake) == (None, 'no eligible memory remains after serving filters')


@pytest.mark.parametrize('reply', [[], [1], ['1', '0'], [2, 1], None, FakeError('offline')])
def test_failed_or_malformed_membership_never_emits_unfiltered_banner(reply):
    fake = Candidates([{'id': 'n1'}, {'id': 'n2'}])
    fake.membership = reply if reply is not None else 'not a list'
    text, reason = render(fake)
    assert text is None and reason


def file_case(tmp_path):
    root = tmp_path.resolve()
    config = {**config_for(('files', root, 'personal', 'global')), 'redis': SETTINGS}
    pointer = {'id': 'file:untrusted-corpus:state', 'family': 'file', 'name': 'State',
               'path': str(root / 'state.md'), 'text': 'NEVER PRINT POINTER BODY'}
    fake = Candidates([pointer, {'id': 'n1', 'name': 'curated'}])
    return config, fake, root / '.verdicts.jsonl'


def row(verdict, stem='state'):
    return json.dumps(dict(stem=stem, verdict=verdict, digest='any-digest', who='fixture', at='2026-09-24')) + '\n'


@pytest.mark.skipif(os.name != 'posix', reason='authorized descriptor reads are POSIX-only')
@pytest.mark.parametrize('log,allowed', [('', True), (row('wrong'), False),
    (row('wrong') + row('keep'), True), (row('keep') + row('wrong'), False),
    (row('sharper'), True), (row('wrong', 'different'), True), ('{broken\n', False),
    ('{"stem":"state","verdict":"keep"}\n', False), (row('wrong') + '{broken\n', False)])
def test_file_verdicts_use_last_record_without_age_or_digest_inference(tmp_path, log, allowed):
    config, fake, sidecar = file_case(tmp_path)
    sidecar.write_text(log, encoding='utf-8')
    text, reason = render(fake, config)
    assert reason is None and '- n1' in text
    assert ('- file:' in text) == allowed
    assert 'NEVER PRINT POINTER BODY' not in text


def test_unmapped_pointer_is_omitted_without_reading_arbitrary_path(tmp_path):
    config, fake, _ = file_case(tmp_path)
    for modified in ({'redis': SETTINGS}, {**config, 'actor': None}):
        text, reason = render(fake, modified)
        assert reason is None and '- n1' in text and '- file:' not in text
    for bad_path in (str(tmp_path.parent / 'state.md'), '../state.md', str(tmp_path / 'other.md')):
        fake.rows[0]['path'] = bad_path
        text, reason = render(fake, config)
        assert reason is None and '- file:' not in text


@pytest.mark.skipif(os.name != 'posix', reason='authorized descriptor reads are POSIX-only')
def test_absent_sidecar_is_allowed_but_unsafe_sidecar_is_not(tmp_path):
    config, fake, sidecar = file_case(tmp_path)
    assert '- file:' in render(fake, config)[0]
    target = tmp_path / 'target'
    target.write_text(row('keep'), encoding='utf-8')
    sidecar.symlink_to(target)
    assert '- file:' not in render(fake, config)[0]
    sidecar.unlink()
    os.link(target, sidecar)
    assert '- file:' not in render(fake, config)[0]
    sidecar.unlink()
    sidecar.write_bytes(b'\xff')
    assert '- file:' not in render(fake, config)[0]


@pytest.mark.skipif(os.name != 'posix', reason='authorized descriptor reads are POSIX-only')
def test_ambiguous_root_and_symlinked_source_are_omitted(tmp_path):
    config, fake, _ = file_case(tmp_path)
    config['roots'].append({**config['roots'][0], 'id': 'overlap'})
    assert '- file:' not in render(fake, config)[0]
    config['roots'].pop()
    (tmp_path / 'state.md').symlink_to(tmp_path / 'elsewhere.md')
    assert '- file:' not in render(fake, config)[0]


@pytest.mark.skipif(os.name != 'posix', reason='authorized descriptor reads are POSIX-only')
def test_total_verdict_budget_suppresses_later_roots(tmp_path, monkeypatch):
    config, fake, sidecar = file_case(tmp_path)
    sidecar.write_text(row('keep'), encoding='utf-8')
    monkeypatch.setattr(memory_serving, 'FILE_LIMIT', len(sidecar.read_bytes()) - 1)
    assert '- file:' not in render(fake, config)[0]


def test_windows_keeps_curated_memory_but_refuses_file_verdict_reads(tmp_path, monkeypatch):
    from attune_harness import memory_reader
    config, fake, _ = file_case(tmp_path)
    monkeypatch.setattr(memory_reader, '_posix', lambda: False)
    text, reason = render(fake, config)
    assert reason is None and '- n1' in text and '- file:' not in text


def test_prompt_recall_uses_search_and_checks_active_status(tmp_path, monkeypatch, capsys):
    fake = FakeRedis()
    fake.sets[PREFIX + 'status:active'].remove('n1')
    monkeypatch.setattr(memory_redis, 'connect', lambda settings: RedisMemory(fake, settings, 'fixture'))
    config = tmp_path / 'memory.json'
    config.write_text(json.dumps({'redis': SETTINGS}))
    assert main(['--config', str(config), 'serve', '--for', 'release']) == 0
    out, err = capsys.readouterr()
    assert out == '' and 'no eligible memory' in err
    fake.sets[PREFIX + 'status:active'].add('n1')
    assert main(['--config', str(config), 'serve', '--for', 'release']) == 0
    out, err = capsys.readouterr()
    assert 'by prompt search' in out and '- n1' in out and not err
    assert not any(call[:2] == ('FCALL_RO', 'recall_digest') for call in fake.calls)


@pytest.mark.parametrize('query', ['', '   ', 'x' * 513])
def test_bad_prompt_never_falls_back_to_digest(query):
    fake = FakeRedis()
    text, reason = render(fake, prompt=query)
    assert text is None and reason
    assert not any(call[0] in ('FCALL_RO', 'FT.SEARCH') for call in fake.calls)


def test_prompt_operators_are_escaped_and_metadata_is_one_line():
    fake = FakeRedis()
    render(fake, prompt='@layer:{curated}|*')
    query = next(call[2] for call in fake.calls if call[0] == 'FT.SEARCH')
    assert query == r'\@layer\:\{curated\}\|\*'
    fake.strings[PREFIX + 'hydrated_at'] = 'stamp\nFORGED\x1b'
    text, reason = render(fake)
    assert reason is None and 'stamp FORGED' in text and '\x1b' not in text
    assert len(text.splitlines()) == 4
