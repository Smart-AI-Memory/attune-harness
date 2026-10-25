"""Versioned, source-independent contracts for the native Redis projection."""

from datetime import datetime, timedelta
import hashlib
from importlib.resources import files
from pathlib import PurePosixPath, PureWindowsPath
import re

from .review_contract import fields, parse_json, versioned

PROJECTION = 'harness-v1'
LIBRARY = 'attune_harness_memory_v1'
LAYERS = ('curated', 'file', 'lesson', 'rule')
MAX_BYTES = 64 * 1024 * 1024
MANIFEST_LIMIT = 65536
_TOKEN = re.compile(r'[A-Za-z0-9_-]{1,32}', re.ASCII)
_GENERATION = re.compile(r'[a-f0-9]{32}', re.ASCII)
_SHA = re.compile(r'[a-f0-9]{64}', re.ASCII)
_MANIFEST_FIELDS = ('schema_version', 'generation', 'previous', 'publication_id',
                    'binding', 'source_digest', 'context_digest', 'function_digest',
                    'hydrated_at', 'counts', 'projection_bytes')


def token(value):
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError('Hydration dataset and corpus IDs require 1–32 ASCII letters, digits, underscore or hyphen')
    return value


def generation_id(value):
    if not isinstance(value, str) or not _GENERATION.fullmatch(value):
        raise ValueError('Hydration generation requires 32 lowercase hex characters')
    return value


def namespace(dataset):
    return f'attune:harness:hydration:{token(dataset)}:'


def generation_prefix(dataset, generation):
    return namespace(dataset) + generation_id(generation) + ':'


def generation_index(dataset, generation):
    return f'idx:attune_harness_memory:{token(dataset)}:{generation_id(generation)}'


def function_source():
    return files('attune_harness').joinpath('assets', 'memory_hydration_v1.lua').read_text(encoding='utf-8')


def function_digest():
    return hashlib.sha256(function_source().encode('utf-8')).hexdigest()


def validate_manifest(raw, binding, bundle):
    """Accept only a complete, host-bound manifest for the installed function bundle."""
    value = parse_json(raw, MANIFEST_LIMIT)
    fields(value, _MANIFEST_FIELDS)
    versioned(value)
    generation_id(value['generation'])
    generation_id(value['publication_id'])
    previous = value['previous']
    if previous is not None:
        generation_id(previous)
        if previous == value['generation']:
            raise ValueError('Hydration previous generation cannot be current')
    for key in ('binding', 'source_digest', 'context_digest', 'function_digest'):
        if not isinstance(value[key], str) or not _SHA.fullmatch(value[key]):
            raise ValueError('Hydration manifest requires SHA-256 digests')
    if value['binding'] != binding or value['function_digest'] != bundle:
        raise ValueError('Hydration manifest differs from host authority or installed function bundle')
    stamp = value['hydrated_at']
    if not isinstance(stamp, str) or len(stamp) > 64:
        raise ValueError('Hydration completion time must be UTC')
    try:
        parsed = datetime.fromisoformat(stamp[:-1] + '+00:00' if stamp.endswith('Z') else stamp)
    except ValueError as error:
        raise ValueError('Hydration completion time must be UTC') from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError('Hydration completion time must be UTC')
    fields(value['counts'], LAYERS)
    for count in (*value['counts'].values(), value['projection_bytes']):
        if type(count) is not int or not 0 <= count <= MAX_BYTES:
            raise ValueError('Hydration counts and projection bytes must be bounded nonnegative integers')
    return value


def validate_sources(value, root_ids):
    """Validate selectors without discovering or reading a source directory."""
    fields(value, ('schema_version', 'sources'))
    versioned(value)
    sources = value['sources']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 4096:
        raise ValueError('Hydration requires 1–4096 explicit source mappings')
    result, seen = [], set()
    for source in sources:
        fields(source, ('root_id', 'layer', 'corpus', 'path'))
        if not isinstance(source['root_id'], str) or source['root_id'] not in root_ids:
            raise ValueError('Hydration source requires an authorized root ID')
        if source['layer'] not in LAYERS:
            raise ValueError('Unsupported hydration layer')
        token(source['corpus'])
        path = source['path']
        if (not isinstance(path, str) or not path or len(path.encode('utf-8')) > 4096
                or '\x00' in path or PurePosixPath(path).is_absolute()
                or PureWindowsPath(path).drive or PureWindowsPath(path).root
                or '..' in path.replace('\\', '/').split('/')
                or (path == '.' and source['layer'] == 'lesson')):
            raise ValueError('Hydration source path must stay relative to its authorized root')
        identity = (source['root_id'], source['layer'], source['corpus'], path.replace('\\', '/'))
        if identity in seen:
            raise ValueError('Duplicate hydration source mapping')
        seen.add(identity)
        result.append(dict(source))
    return result
