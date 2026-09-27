"""Explicit immutable local index generations. Provider work is never hidden in reads."""

import copy
import math
import os
import re
import stat
import struct
import tempfile
from pathlib import Path

from .features import FeatureUnavailable, REPLACE_RETRY_SECONDS, read_text, replace_file, report, require_feature
from .review_contract import canonical, digest, fields, parse_json
from .review_store import RunStore, read_record
from .voyage_provider import LANCEDB_VERSION, StageJournal, embeddings, RATES
from .voyage_sources import PROFILE, collect, config, generation, hex_digest, snapshot, validate_scope
from .voyage_plugin import inspect_selection, selected_stage

MAX_INDEX_JSON = 64 * 1024 * 1024
MAX_INDEX_FILES = 4096
MAX_INDEX_BYTES = 512 * 1024 * 1024


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
        replace_file(temporary, path, retry_seconds=REPLACE_RETRY_SECONDS)
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
    plugin = inspect_selection(cfg['voyage_plugin']) if 'voyage_plugin' in cfg else {}
    manifest, passages = collect(cfg)
    total = sum(len(p['embedding_text'].encode('utf-8')) for p in passages)
    batches = list(embedding_batches(passages, cfg))
    return report('index-plan', 'ready', generation=generation(cfg, manifest, passages),
                  config_digest=digest(cfg), profile=PROFILE, manifest=manifest,
                  passages=len(passages), embedding_input_bytes=total,
                  estimated_tokens=total / 4, estimated_embedding_cost_usd=total / 4 * 0.12 / 1_000_000,
                  planned_embedding_calls=len(batches), rate_snapshot=RATES,
                  estimate_scope='Advisory bytes/4 estimate, not exact tokens or a USD ceiling; full build before reuse',
                  provider_calls=0, **plugin)


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
    if 'voyage_plugin' in metadata['config'] and (directory / 'db').exists():
        validate_database_tree(directory / 'db')
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


def selected_index_preflight(cfg, provider):
    """Refuse an unaccepted index tool before any host index state is created."""
    if 'voyage_plugin' not in cfg:
        return False
    with selected_stage(cfg, 'index') as (bundle, _, _, _):
        if provider is not None:
            raise FeatureUnavailable('Selected Voyage index uses only its signed plugin tool, not an injected provider')
        if 'index_staging' not in bundle['plugin']['grant'].get('paths', ()):
            raise FeatureUnavailable('Voyage index requires an accepted index_staging path grant')
    return True


def selected_row_bound(passages):
    """Reject predictable staging overflow before any paid embedding stage."""
    text_bytes = sum(len(p['embedding_text'].encode('utf-8')) for p in passages)
    # A JSON double needs at most 25 characters, with comma and structure room.
    if len(passages) * (PROFILE['dimensions'] * 26 + 4096) + text_bytes > MAX_INDEX_JSON:
        raise ValueError('Selected index rows exceed the 64 MiB staging bound')


def selected_result_bound(cfg, passages):
    """Require enough accepted output for the largest predictable embed result."""
    batches = list(embedding_batches(passages, cfg))
    needed = max((len(batch) * (PROFILE['dimensions'] * 26 + 64) + 4096
                  for batch in batches), default=0)
    with selected_stage(cfg, 'embed') as (bundle, _, _, _):
        available = bundle['plugin']['grant']['output']['result']
    if needed > available:
        raise ValueError('Accepted Voyage result bound cannot hold the planned embedding batch')


def expected_rows(passages, vectors):
    """Freeze finite float32 index values before hashing and serialization."""
    selected_row_bound(passages)
    def index_vector(raw):
        if not isinstance(raw, list) or len(raw) != PROFILE['dimensions']:
            raise ValueError('Selected index vector has invalid dimensions')
        normalized = []
        for value in raw:
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError('Selected index vector has a nonfinite value')
            try:
                rounded = struct.unpack('!f', struct.pack('!f', value))[0]
            except (OverflowError, struct.error) as exc:
                raise ValueError('Selected index vector exceeds float32 range') from exc
            if not math.isfinite(rounded):
                raise ValueError('Selected index vector exceeds float32 range')
            normalized.append(rounded)
        if not any(normalized):
            raise ValueError('Selected index vector underflowed to zero')
        return normalized
    rows = [{'passage_id': p['passage_id'], 'repo_id': p['repo_id'], 'path': p['path'],
             'text': p['embedding_text'], 'embedding_key': embedding_key(p),
             'vector': index_vector(vectors[embedding_key(p)])} for p in passages]
    if len(canonical(rows).encode('utf-8')) > MAX_INDEX_JSON:
        raise ValueError('Selected index rows exceed the 64 MiB staging bound')
    return rows


def validate_staged_tree(staging):
    entries, total = 0, 0
    for path in staging.rglob('*'):
        entries += 1
        if entries > MAX_INDEX_FILES:
            raise ValueError('Index staging exceeds its entry bound')
        if path.is_symlink() or not path.resolve().is_relative_to(staging.resolve()):
            raise ValueError('Index staging has a symlink or path outside its root')
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError('Index staging has a nonregular entry')
        if path != staging / 'rows.json' and not path.is_relative_to(staging / 'db'):
            raise ValueError('Index staging has an unexpected file')
        if stat.S_ISREG(mode):
            total += path.stat().st_size
            if total > MAX_INDEX_BYTES:
                raise ValueError('Index staging exceeds file or byte bounds')


def validate_database_tree(db_path):
    if db_path.is_symlink() or not db_path.is_dir():
        raise ValueError('Selected index database is missing or a symlink')
    entries, total = 0, 0
    for path in db_path.rglob('*'):
        entries += 1
        if entries > MAX_INDEX_FILES:
            raise ValueError('Selected index database exceeds its entry bound')
        if path.is_symlink() or not path.resolve().is_relative_to(db_path.resolve()):
            raise ValueError('Selected index database contains a symlink or escaped path')
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError('Selected index database has a nonregular entry')
        if stat.S_ISREG(mode):
            total += path.stat().st_size
            if total > MAX_INDEX_BYTES:
                raise ValueError('Selected index database exceeds file or byte bounds')


def validate_selected_table(db_path, rows):
    if not rows:
        if db_path.exists():
            raise ValueError('Empty selected index has unexpected database files')
        return []
    if db_path.is_symlink() or not (db_path / 'passages.lance').is_dir():
        raise ValueError('Selected index database is missing or a symlink')
    validate_database_tree(db_path)
    table = database(db_path).open_table('passages')
    arrow = table.to_arrow()
    import pyarrow as pa
    expected_schema = pa.schema([pa.field(name, pa.string()) for name in
        ('embedding_key', 'passage_id', 'path', 'repo_id', 'text')] +
        [pa.field('vector', pa.list_(pa.float32(), PROFILE['dimensions']))])
    if not arrow.schema.equals(expected_schema, check_metadata=False):
        raise ValueError('Selected index schema differs from the frozen passage/vector schema')
    actual = sorted(arrow.to_pylist(), key=lambda row: row['passage_id'])
    expected = sorted(rows, key=lambda row: row['passage_id'])
    if actual != expected or table.count_rows() != len(rows):
        raise ValueError('Selected index rows differ from the host passage/vector map')
    indices = [index for index in table.list_indices()
               if index.index_type == 'FTS' and index.columns == ['text']]
    if len(indices) != 1 or any(indices[0].index_details.get(key) != value for key, value in {
            'base_tokenizer': 'simple', 'stem': False, 'remove_stop_words': False,
            'ascii_folding': False, 'max_token_length': 256}.items()):
        raise ValueError('Selected index FTS profile differs from the frozen tokenizer')
    table.search(rows[0]['vector']).distance_type('cosine').limit(1).to_list()
    tokens = re.findall(r'\w+', rows[0]['text'], re.UNICODE)
    table.search(tokens[0] if tokens else 'passage', query_type='fts').limit(1).to_list()
    return actual


def index_authority(directory):
    """Checkpoint host evidence that an interrupted local child may not replace."""
    from .plugin_runtime import checkpoint

    ledger = directory / 'stages'
    guarded = [directory / 'manifest.json', ledger / 'record.json']
    if (ledger / 'record.json').exists():
        guarded += [ledger / key / 'record.json' for key in read_record(ledger)['stages']]
    return digest(checkpoint(guarded))


def materialize_selected_index(cfg, directory, identity, passages, vectors, receipts):
    """Only the signed index tool writes the database; the host publishes it."""
    from .plugin_runtime import run_voyage_index
    from .voyage_plugin import VoyageIndexContext

    if (directory / 'index-error.json').exists():
        raise ValueError('Retained index error requires inspection before publication')
    rows = expected_rows(passages, vectors)
    staging = directory / 'index_staging'
    if staging.is_symlink():
        raise ValueError('Index staging cannot be a symlink')
    staging.mkdir(exist_ok=True)
    rows_file = staging / 'rows.json'
    if rows_file.exists():
        if read_json(rows_file) != rows:
            raise ValueError('Retained index staging rows differ from the host; inspect before retry')
    else:
        write_json(rows_file, rows)
    validate_staged_tree(staging)
    attempt = directory / 'index-attempt.json'
    db_path = directory / 'db'
    if db_path.exists() and (staging / 'db').exists():
        raise ValueError('Both staged and final index databases exist; inspect before retry')
    plugin_receipt = None
    if not attempt.exists():
        if db_path.exists() or (staging / 'db').exists():
            raise ValueError('Unrecorded index database exists; inspect before retry')
        with selected_stage(cfg, 'index') as selected:
            bundle, tool_name, tool, postcheck = selected
            authority = index_authority(directory)
            write_json(attempt, {'status': 'dispatching', 'generation': identity,
                'rows_digest': digest(rows), 'row_count': len(rows),
                'authority_digest': authority, 'artifact_digest': bundle['artifact_digest']})
            context = VoyageIndexContext(directory, staging, identity, digest(cfg),
                cfg['voyage_plugin']['extension_id'], bundle['artifact_digest'], digest(rows),
                len(rows), copy.deepcopy(cfg))
            ledger = directory / 'stages'
            guarded = [directory / 'manifest.json', attempt, ledger / 'record.json']
            if (ledger / 'record.json').exists():
                guarded += [ledger / key / 'record.json' for key in read_record(ledger)['stages']]
            try:
                wrapped, plugin_receipt = run_voyage_index(bundle, tool_name, tool,
                    {'generation': identity, 'rows_digest': digest(rows), 'row_count': len(rows)},
                    context=context, guarded_paths=guarded, postcheck=postcheck)
                if wrapped['plugin_result'] != {'rows_digest': digest(rows), 'row_count': len(rows)}:
                    raise ValueError('Voyage index child summary differs from host rows')
                write_json(attempt, {'status': 'child_completed', 'generation': identity,
                    'rows_digest': digest(rows), 'row_count': len(rows), 'plugin_receipt': plugin_receipt,
                    'authority_digest': authority, 'artifact_digest': bundle['artifact_digest']})
            except Exception as exc:
                error = {'generation': identity, 'type': type(exc).__name__,
                    'detail': 'Index child or staged output failed; inspect before retry'}
                if hasattr(exc, 'receipt'):
                    error['plugin_receipt'] = exc.receipt
                write_json(directory / 'index-error.json', error)
                raise
    else:
        saved = read_json(attempt)
        if (saved.get('status') not in ('dispatching', 'child_completed') or
                saved.get('generation') != identity or saved.get('rows_digest') != digest(rows) or
                saved.get('row_count') != len(rows) or
                saved.get('authority_digest') != index_authority(directory)):
            raise ValueError('Retained index attempt changed; inspect before retry')
        with selected_stage(cfg, 'index') as (bundle, _, _, postcheck):
            if saved.get('artifact_digest') != bundle['artifact_digest']:
                raise ValueError('Retained index selected artifact changed; inspect before retry')
            postcheck()
        plugin_receipt = saved.get('plugin_receipt')
        if not rows and saved['status'] == 'dispatching':
            raise ValueError('Interrupted empty index needs inspection before publication')
        if not db_path.exists() and not (staging / 'db').exists() and rows:
            raise ValueError('Interrupted index has no complete database; inspect before retry')
    try:
        validate_staged_tree(staging)
        actual = validate_selected_table(db_path if db_path.exists() else staging / 'db', rows)
        if not db_path.exists() and (staging / 'db').exists():
            (staging / 'db').rename(db_path)
        if snapshot(cfg)[0] != read_json(directory / 'manifest.json')['manifest']:
            raise ValueError('Selected sources changed after local indexing')
        with selected_stage(cfg, 'index') as (_, _, _, postcheck):
            postcheck()
    except Exception as exc:
        write_json(directory / 'index-error.json', {'generation': identity, 'type': type(exc).__name__,
            'detail': 'Index child or staged output failed; inspect before retry'})
        raise
    receipt = {'generation': identity, 'stages': receipts, 'reused_embeddings': 0,
               'rows_digest': digest(actual), 'index_plugin': plugin_receipt}
    return receipt


def build_index(cfg, *, base_generation=None, allow_provider=False, provider=None):
    selected = selected_index_preflight(cfg, provider)
    manifest, passages = collect(cfg)
    if selected:
        selected_row_bound(passages)
        selected_result_bound(cfg, passages)
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
        metadata_path = directory / 'manifest.json'
        if selected and metadata_path.exists():
            if read_json(metadata_path) != metadata:
                raise ValueError('Retained selected index manifest changed; inspect before retry')
        elif selected and any(directory.iterdir()):
            raise ValueError('Selected index evidence exists without its manifest; inspect before retry')
        else:
            write_json(metadata_path, metadata)
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
        if selected:
            receipt = materialize_selected_index(cfg, directory, identity, passages, vectors, receipts)
            receipt['reused_embeddings'] = reused
        else:
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
            receipt = {'generation': identity, 'stages': receipts, 'reused_embeddings': reused,
                       'rows_digest': digest(stored_rows)}
        write_json(directory / 'build-receipt.json', receipt)
        write_json(directory / 'published.json', {'generation': identity, 'metadata_digest': digest(metadata), 'receipt_digest': digest(receipt)})
        return report('index-build', 'completed', generation=identity, passages=len(passages),
                      provider_calls=sum(not r['replayed'] for r in receipts), reused_embeddings=reused, stages=receipts)
