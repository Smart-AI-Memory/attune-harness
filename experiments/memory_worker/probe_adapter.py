"""Exercise the actual file stash only with explicit disposable synthetic data."""
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import tempfile


def probe():
    from attune.memory.file_stash import FileStashBackend
    import attune.memory.file_stash as module
    with tempfile.TemporaryDirectory(prefix='memory-adapter-only-') as temporary:
        directory = Path(temporary) / 'stash'
        backend = FileStashBackend(base_dir=directory)
        assert backend.remember('Synthetic violet worker note.', memory_id='note-a',
                                topics=['type:note', 'cwd:synthetic-cedar'])
        backend.close()
        backend = FileStashBackend(base_dir=directory)
        recalled = backend.search('violet worker', cwd='synthetic-cedar')
        assert [r['id'] for r in recalled] == ['note-a']
        assert backend.remember('Synthetic violet other-project note.', memory_id='note-b',
                                topics=['type:note', 'cwd:synthetic-elm'])
        cross_scope = backend.search('violet', cwd='synthetic-cedar')
        assert {r['cwd'] for r in cross_scope} == {'synthetic-cedar', 'synthetic-elm'}
        assert backend.remember('Synthetic violet duplicate ID.', memory_id='note-a',
                                topics=['type:note', 'cwd:synthetic-cedar'])
        duplicate_count = sum(r['id']=='note-a' for r in backend.recent(limit=10))
        assert duplicate_count == 2
        removed = backend.forget(['note-a'])
        assert removed == 2
        assert [r['id'] for r in backend.recent(limit=10)] == ['note-b']
        assert all(json.loads(line)['id'] != 'note-a' for line in
                   (directory/'findings.jsonl').read_text().splitlines() if line.strip())
        assert backend.forget(['note-a']) == 0
        backend.close()
    source = Path(module.__file__)
    return dict(mode='actual file-stash API; isolated temporary synthetic data only',
        package_version=version('attune-ai'), source=str(source),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        capture_reopen_recall='passed', exact_id_forget_and_physical_absence='passed',
        unrelated_record_preserved=True, duplicate_id_records=duplicate_count,
        duplicate_id_removal_count=removed, cwd_filter='soft ordering, not access isolation',
        limits='No versioned update, concurrent writer, crash durability, security, taxonomy mapping, service wrapper, live memory or context-refresh qualification.')


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
