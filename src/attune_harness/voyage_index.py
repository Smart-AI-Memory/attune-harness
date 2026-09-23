"""Explicit immutable local index generations. Provider work is never hidden in reads."""

import json
import os
import tempfile
from pathlib import Path

from .features import read_text, replace_file, report, require_feature
from .review_contract import canonical, digest, fields, parse_json
from .review_store import RunStore, read_record
from .voyage_provider import LANCEDB_VERSION, StageJournal, embeddings, RATES
from .voyage_sources import PROFILE, collect, config, generation, hex_digest, snapshot, validate_scope

MAX_INDEX_JSON = 64 * 1024 * 1024


def write_json(path, value):
    payload = canonical(value).encode('utf-8')
    if len(payload) > MAX_INDEX_JSON:
        raise ValueError('Index metadata exceeds 64 MiB')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        replace_file(temporary, path)
        if os.name == 'posix':
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_json(path):
    if path.is_symlink():
        raise ValueError('Index metadata cannot be a symlink')
    return parse_json(read_text(path, MAX_INDEX_JSON), MAX_INDEX_JSON)


def index_plan(cfg):
    manifest, passages = collect(cfg)
    total = sum(len(p['embedding_text'].encode('utf-8')) for p in passages)
    batches = list(embedding_batches(passages, cfg))
    return report('index-plan', 'ready', generation=generation(cfg, manifest, passages),
                  config_digest=digest(cfg), profile=PROFILE, manifest=manifest,
                  passages=len(passages), embedding_input_bytes=total,
                  estimated_tokens=total / 4, estimated_embedding_cost_usd=total / 4 * 0.12 / 1_000_000,
                  planned_embedding_calls=len(batches), rate_snapshot=RATES,
                  estimate_scope='Advisory bytes/4 estimate, not exact tokens or a USD ceiling; full build before reuse',
                  provider_calls=0)


def embedding_key(passage):
    return digest({'text': passage['embedding_text'], 'model': PROFILE['embedding_model'],
                   'dimensions': PROFILE['dimensions'], 'input_type': 'document'})


def embedding_batches(passages, cfg):
    batch = []
    for p in passages:
        candidate = batch + [p]
        request = {'texts': [x['embedding_text'] for x in candidate], 'input_type': 'document'}
        if batch and (len(candidate) > cfg['batch_size'] or len(canonical(request).encode()) + 2048 > cfg['max_request_bytes']):
            yield batch
            batch = []
        batch.append(p)
        if len(canonical({'texts': [p['embedding_text']], 'input_type': 'document'}).encode()) + 2048 > cfg['max_request_bytes']:
            raise ValueError('Passage context exceeds provider request byte limit')
    if batch:
        yield batch


def read_generation(cfg, identity):
    hex_digest(identity)
    directory = Path(cfg['index_dir']) / 'generations' / identity
    if any(p.is_symlink() for p in (Path(cfg['index_dir']), directory.parent, directory)):
        raise ValueError('Index generation cannot be a symlink')
    published = read_json(directory / 'published.json')
    metadata = read_json(directory / 'manifest.json')
    receipt = read_json(directory / 'build-receipt.json')
    if published != {'generation': identity, 'metadata_digest': digest(metadata), 'receipt_digest': digest(receipt)}:
        raise ValueError('Index publication digest mismatch')
    if metadata['config'] != cfg or metadata['profile'] != PROFILE:
        raise ValueError('Index configuration/profile mismatch')
    if generation(cfg, metadata['manifest'], metadata['passages']) != identity:
        raise ValueError('Index generation identity mismatch')
    return directory, metadata


def check_generation(cfg, identity):
    directory, metadata = read_generation(cfg, identity)
    manifest, _ = snapshot(cfg)
    if manifest != metadata['manifest']:
        raise ValueError('Stale index: selected repository sources or revision changed; explicitly update and accept a new generation')
    table_rows(directory, metadata)
    return directory, metadata


def load_selection(value):
    fields(value, ('config', 'config_digest', 'generation', 'scope'))
    cfg = config(value['config'], Path.cwd())
    if cfg != value['config'] or digest(cfg) != value['config_digest']:
        raise ValueError('Accepted retrieval configuration digest mismatch; use normalized absolute paths')
    hex_digest(value['generation'])
    validate_scope(value['scope'], cfg)
    check_generation(cfg, value['generation'])
    return value


def selection(cfg, identity):
    check_generation(cfg, identity)
    return {'config': cfg, 'config_digest': digest(cfg), 'generation': identity,
            'scope': {'repo_ids': [r['repo_id'] for r in cfg['roots']], 'exclude_paths': []}}


def database(path):
    sdk = require_feature('lancedb', 'lancedb', LANCEDB_VERSION, 'voyage')
    if path.is_symlink():
        raise ValueError('Database path cannot be a symlink')
    return sdk.connect(str(path))


def table_rows(directory, metadata):
    """Bind persisted vectors and row identities to the publication receipt."""
    if metadata['passages'] and not (directory / 'db/passages.lance').is_dir():
        raise ValueError('Published index database is missing')
    rows = database(directory / 'db').open_table('passages').to_arrow().to_pylist() if metadata['passages'] else []
    receipt = read_json(directory / 'build-receipt.json')
    rows.sort(key=lambda row: row['passage_id'])
    if digest(rows) != receipt.get('rows_digest'):
        raise ValueError('Index table contents changed after publication')
    return rows


def inspect_index(cfg, identity):
    hex_digest(identity)
    directory = Path(cfg['index_dir']) / 'generations' / identity
    if any(p.is_symlink() for p in (directory, directory.parent, directory.parent.parent)):
        raise ValueError('Index generation cannot be a symlink')
    metadata = read_json(directory / 'manifest.json')
    if metadata['config'] != cfg:
        raise ValueError('Index configuration mismatch')
    stages = []
    ledger = directory / 'stages'
    if (ledger / 'record.json').exists():
        for key in read_record(ledger)['stages']:
            stage = read_record(ledger / hex_digest(key))
            stages.append({name: stage[name] for name in ('kind', 'status', 'receipt', 'error') if name in stage})
    status = 'unpublished'
    if (directory / 'published.json').exists():
        read_generation(cfg, identity)
        status = 'ready' if snapshot(cfg)[0] == metadata['manifest'] else 'stale'
        table_rows(directory, metadata)
    return report('index-inspect', status, generation=identity, config_digest=digest(cfg),
                  files=len(metadata['manifest']['files']), passages=len(metadata['passages']),
                  stages=stages, provider_calls=0)


def build_index(cfg, *, base_generation=None, allow_provider=False, provider=None):
    manifest, passages = collect(cfg)
    identity = generation(cfg, manifest, passages)
    metadata = {'config': cfg, 'profile': PROFILE, 'manifest': manifest, 'passages': passages}
    if len(canonical(metadata).encode()) > MAX_INDEX_JSON:
        raise ValueError('Index metadata exceeds 64 MiB')
    parent = Path(cfg['index_dir'])
    parent.mkdir(exist_ok=True)  # Parent must already be deliberately chosen/available.
    owner = RunStore(parent, existing=True)
    with owner.lease():
        generations = parent / 'generations'
        if generations.is_symlink():
            raise ValueError('Generation directory cannot be a symlink')
        generations.mkdir(exist_ok=True)
        directory = generations / identity
        if (directory / 'published.json').exists():
            check_generation(cfg, identity)
            return report('index-build', 'completed', generation=identity, provider_calls=0, reused_generation=True)
        if directory.is_symlink():
            raise ValueError('Generation directory cannot be a symlink')
        directory.mkdir(exist_ok=True)
        # A generation is queryable only after the final publication marker.
        write_json(directory / 'manifest.json', metadata)
        journal = StageJournal(directory / 'stages', cfg, allow_provider=allow_provider, provider=provider)
        vectors, reused, receipts = {}, 0, []
        if base_generation:
            old_directory, old = read_generation(cfg, base_generation)
            if old['passages']:
                rows = table_rows(old_directory, old)
                for row in rows:
                    embeddings({'vectors': [row['vector']], 'total_tokens': None}, 1)
                    vectors[row['embedding_key']] = row['vector']
        missing = {}
        for p in passages:
            key = embedding_key(p)
            if key in vectors:
                reused += 1
            else:
                missing[key] = p
        batches = list(embedding_batches(list(missing.values()), cfg))
        if len(batches) > cfg['max_provider_calls']:
            raise PermissionError('Planned embedding batches exceed accepted provider-call budget')
        for batch in batches:
            result, receipt = journal.perform('embed', {'texts': [p['embedding_text'] for p in batch], 'input_type': 'document'},
                                               lambda v: embeddings(v, len(batch)))
            receipts.append(receipt)
            for p, vector in zip(batch, result['vectors']):
                vectors[embedding_key(p)] = vector
        if snapshot(cfg)[0] != manifest:
            raise ValueError('Selected sources changed during indexing; generation remains unpublished')
        db = database(directory / 'db')
        stored_rows = []
        if passages:
            from lancedb.index import FTS
            rows = [{'passage_id': p['passage_id'], 'repo_id': p['repo_id'], 'path': p['path'],
                     'text': p['embedding_text'], 'embedding_key': embedding_key(p),
                     'vector': vectors[embedding_key(p)]} for p in passages]
            table = db.create_table('passages', rows, mode='overwrite')
            table.create_index('text', config=FTS(stem=False, remove_stop_words=False,
                                                ascii_folding=False, max_token_length=256))
            if table.count_rows() != len(passages):
                raise ValueError('Index row count mismatch')
            stored_rows = sorted(table.to_arrow().to_pylist(), key=lambda row: row['passage_id'])
        receipt = {'generation': identity, 'stages': receipts, 'reused_embeddings': reused, 'rows_digest': digest(stored_rows)}
        write_json(directory / 'build-receipt.json', receipt)
        write_json(directory / 'published.json', {'generation': identity, 'metadata_digest': digest(metadata), 'receipt_digest': digest(receipt)})
        return report('index-build', 'completed', generation=identity, passages=len(passages),
                      provider_calls=sum(not r['replayed'] for r in receipts), reused_embeddings=reused, stages=receipts)
