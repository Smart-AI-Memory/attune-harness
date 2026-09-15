"""Single-writer run records. Inspection never resumes or repeats an operation."""

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .features import read_text
from .features import FeatureUnavailable
from .review_contract import digest, parse_json, versioned


class PersistenceError(OSError):
    """The caller must stop dispatch when a run record cannot be persisted."""


class RunStore:
    def __init__(self, directory: Path, *, existing: bool = False):
        if directory.is_symlink() or any(part in ('.git', '.hg', '.svn') for part in directory.resolve().parts):
            raise ValueError('Run directory cannot be a symlink or repository metadata')
        self.directory = directory.absolute()
        if existing:
            if not self.directory.is_dir():
                raise ValueError('Run directory does not exist')
        else:
            self.directory.mkdir()  # Exclusive creation of new runs.
        self.path = self.directory / 'record.json'

    @contextmanager
    def lease(self):
        """One process owns mutation; the OS releases the lock after a crash."""
        if os.name not in ('posix', 'nt'):
            raise FeatureUnavailable('Review mutation/recovery requires POSIX or Windows file locks')
        lock = self.directory / '.writer.lock'
        if os.name == 'nt':
            from .windows import open_lock
            fd = open_lock(lock)
        else:
            fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise PersistenceError('Run is busy; another owner holds the writer lock') from exc
            yield
        finally:
            os.close(fd)

    def save(self, record: dict) -> None:
        temporary = None
        try:
            if 'recovery' in record:
                record['checkpoint_digest'] = checkpoint_digest(record)
            payload = json.dumps(record, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
            if len(payload.encode('utf-8')) > 8 * 1024 * 1024:
                raise ValueError('Run record exceeds 8 MiB')
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.directory, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            if os.name == 'posix':
                fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except (OSError, ValueError, TypeError) as exc:
            raise PersistenceError(f'Run record persistence failed: {exc}') from exc
        finally:
            if temporary is not None and temporary.exists():
                try:
                    temporary.unlink()
                except OSError as exc:
                    raise PersistenceError(f'Run record cleanup failed: {exc}') from exc


def checkpoint_digest(record: dict) -> str:
    return digest({key: value for key, value in record.items() if key != 'checkpoint_digest'})


def read_record(directory: Path) -> dict:
    record = parse_json(read_text(directory / 'record.json', 8 * 1024 * 1024), 8 * 1024 * 1024)
    if not isinstance(record, dict):
        raise ValueError('Run record must be an object')
    versioned(record)
    if 'recovery' in record and record.get('checkpoint_digest') != checkpoint_digest(record):
        raise ValueError('Run checkpoint digest does not match its contents')
    return record


def inspect_run(directory: Path) -> dict:
    record = read_record(directory)
    if record.get('operation') != 'review' or record.get('status') not in (
        'running', 'completed', 'failed', 'unavailable', 'unresolved', 'paused', 'cancelled',
    ):
        raise ValueError('Unsupported review record')
    if record['status'] == 'running':
        record['persisted_status'] = 'running'
        record['status'] = 'unresolved'
        record['inspection_note'] = 'Work may still be running or was interrupted; inspect the owner before any new attempt. No resume was performed.'
    return record
