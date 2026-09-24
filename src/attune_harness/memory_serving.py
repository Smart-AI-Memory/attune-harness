"""Read-time eligibility for the bounded Redis hook banner (Phase 3.3, D21).

Redis paths are evidence, never permission to read outside configured roots.
No mutation, hydration, or lifecycle inference happens here.
"""

from pathlib import Path

from .memory_controls import VERDICT_VALUES
from .memory_reader import FILE_LIMIT, NativeReader, roots_config
from .memory_redis import LIMIT_MAX, PREFIX, MemoryRedisUnavailable
from .review_contract import parse_json


class FileVerdicts:
    """One bounded sidecar snapshot per authorized root, local to a serve call."""

    def __init__(self, config):
        self.reader = None
        self.logs = {}
        self.bytes_read = 0
        if isinstance(config, dict) and config.get('roots'):
            self.reader = NativeReader(roots_config(config))

    def permits(self, item, bare):
        if self.reader is None or not isinstance(item.get('path'), str):
            return False
        path = Path(item['path'])
        if (not path.is_absolute() or '..' in path.parts or path != path.resolve()
                or path.stem != bare.rsplit(':', 1)[-1]):
            return False
        roots = [r for r in self.reader.config['roots'] if r['tier'] in ('personal', 'curated')
                 and path != Path(r['path']) and Path(r['path']) in path.parents]
        if len(roots) != 1:
            return False
        root = roots[0]
        if root['id'] not in self.logs:
            self.logs[root['id']] = self._read(root)
        latest = self.logs[root['id']]
        return latest is not None and latest.get(path.stem) != 'wrong'

    def _read(self, root):
        if self.bytes_read >= FILE_LIMIT:
            return None
        try:
            content, _, _ = self.reader._capture(root, '.verdicts.jsonl', limit=FILE_LIMIT - self.bytes_read)
        except FileNotFoundError:
            return {}  # no verdict has been recorded; never read a Redis-supplied directory
        except (ValueError, OSError):
            # A rejected capture can have read its full allowance before failing.
            self.bytes_read = FILE_LIMIT
            return None
        self.bytes_read += len(content)
        if self.bytes_read > FILE_LIMIT:
            return None
        latest = {}
        try:
            for line in content.decode('utf-8').splitlines():
                if not line.strip():
                    continue
                record = parse_json(line, FILE_LIMIT)
                if not isinstance(record, dict) or any(
                    not isinstance(record.get(key), str) or not record[key]
                    for key in ('stem', 'verdict', 'digest', 'who', 'at')
                ) or record['verdict'] not in VERDICT_VALUES:
                    return None
                latest[record['stem']] = record['verdict']
        except (ValueError, UnicodeError):
            return None
        return latest


def filter_packet(memory, packet, config, limit):
    """Filter candidates before display; a failed membership check serves nothing."""
    # Validate packet shape before any authority reads, even with an empty list.
    packet['authority'].get('host')
    candidates = []
    for item in packet['items'][:LIMIT_MAX]:
        if not isinstance(item, dict):
            continue
        try:
            family, bare = memory._split(item.get('id'))
        except ValueError:
            continue
        candidates.append((item, family, bare))
    ids = list(dict.fromkeys(bare for _, family, bare in candidates if family == 'node'))
    active = set()
    if ids:
        reply = memory._call('checking active memories', memory.client.execute_command,
                             'SMISMEMBER', PREFIX + 'status:active', *ids)
        if (not isinstance(reply, (list, tuple)) or len(reply) != len(ids)
                or any(type(value) not in (int, bool) or value not in (0, 1) for value in reply)):
            raise MemoryRedisUnavailable('Redis memory returned malformed active membership')
        active = {ident for ident, value in zip(ids, reply) if value}
    verdicts = None
    try:
        if any(family == 'file' for _, family, _ in candidates):
            verdicts = FileVerdicts(config)
    except ValueError:
        pass  # bad roots cannot authorize pointers; curated eligibility is independent
    kept = []
    for item, family, bare in candidates:
        if family == 'node' and bare not in active:
            continue
        if family == 'file' and (verdicts is None or not verdicts.permits(item, bare)):
            continue
        kept.append(item)
        if len(kept) == limit:
            break
    return {**packet, 'items': kept, 'status': 'ok' if kept else 'no_results'}
