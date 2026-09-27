"""Small stdlib protocol shared by the three signed Voyage entry modules."""

import hashlib
import json
from pathlib import Path
import sys


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def request():
    if len(sys.argv) != 3:
        raise ValueError('Voyage runner needs request and result paths')
    path = Path(sys.argv[1])
    if path.stat().st_size > 1_048_576:
        raise ValueError('Voyage runner request exceeds 1 MiB')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != {'arguments', 'paths', 'scratch'}:
        raise ValueError('Invalid Voyage runner request')
    return value


def result(value):
    Path(sys.argv[2]).write_text(canonical(value), encoding='utf-8')
