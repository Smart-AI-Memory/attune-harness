"""Conservative local recovery: replay evidence, never guess away unknown effects."""

import copy
import hashlib
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL

from .features import FeatureUnavailable, read_text, require_feature
from .retrieval import MAX_CORPUS_BYTES, MAX_CORPUS_FILES, RAG_VERSION
from .verification import VERIFY_VERSION
from .review_contract import bounded_text, digest
from .review_participants import PROTOCOL, ReviewExchange, decode_action
from .review_store import RunStore, read_record

ENGINE_PROFILE = {'version': 1, 'turn_protocol_sha256': digest(PROTOCOL),
                  'verify': VERIFY_VERSION, 'rag': RAG_VERSION}


def engine_profile(registry):
    # Older engines reject extended turns while existing records stay resumable.
    return {**ENGINE_PROFILE, **({'extensions': 1} if registry.get('extensions') else {})}


class ReviewPaused(Exception):
    """Requested operation budget reached at a saved boundary."""


class UnresolvedOperation(RuntimeError):
    """An operation may have executed and cannot be repeated without evidence."""


def stable_id(*parts) -> str:
    return str(uuid5(NAMESPACE_URL, ':'.join(parts)))


def snapshot_sources(corpus: Path) -> dict:
    if not corpus.is_dir():
        raise ValueError('Corpus root must be an existing directory')
    snapshot, total = {}, 0
    for path in sorted(corpus.glob('**/*.md')):
        if not path.resolve().is_relative_to(corpus):
            raise ValueError('Corpus source escapes the accepted root')
        content = read_text(path).encode('utf-8')
        total += len(content)
        if len(snapshot) >= MAX_CORPUS_FILES or total > MAX_CORPUS_BYTES:
            raise ValueError('Corpus exceeds recovery snapshot limits')
        snapshot[path.relative_to(corpus).as_posix()] = hashlib.sha256(content).hexdigest()
    return snapshot


class RecoveryCursor:
    def __init__(self, record, store, max_operations=None):
        if max_operations is not None and (type(max_operations) is not int or not 1 <= max_operations <= 100):
            raise ValueError('max_operations must be an integer in 1..100')
        self.record, self.store, self.limit = record, store, max_operations
        self.completed = 0
        self.events = {event['operation_key']: event for event in record['events']}
        if len(self.events) != len(record['events']):
            raise ValueError('Duplicate operation keys in checkpoint')

    def perform(self, key, kind, call, *, effect_class, **details):
        expected = {'kind': kind, 'effect_class': effect_class, **details}
        event = self.events.get(key)
        if event is not None:
            if any(event.get(name) != value for name, value in expected.items()):
                raise ValueError('Saved operation does not match the reconstructed request')
            if event['state'] == 'completed':
                return copy.deepcopy(event['result'])
            if event['phase'] != 'prepared':
                raise UnresolvedOperation(f"Operation {event['event_id']} may have executed; reconcile before resume")
        else:
            event = {'event_id': str(uuid4()), 'operation_key': key, 'state': 'pending',
                     'phase': 'prepared', 'attempts': 1, **expected}
            self.events[key] = event
            self.record['events'].append(event)
            self.store.save(self.record)
        event['phase'] = 'dispatching'
        self.store.save(self.record)  # No call until the dispatch boundary is durable.
        try:
            result = call()
        except Exception as exc:
            event.update(state='failed', error={'type': type(exc).__name__, 'detail': str(exc)},
                         effects='unknown' if effect_class == 'unknown' else 'read_only')
            raise
        event.update(state='completed', phase='completed', result=copy.deepcopy(result))
        self.store.save(self.record)
        self.completed += 1
        if self.limit is not None and self.completed >= self.limit:
            raise ReviewPaused('Operation budget reached at a saved checkpoint')
        return result


def load_recovery(store: RunStore, checkpoint: str) -> dict:
    record = read_record(store.directory)
    profile = record.get('recovery', {}).get('profile')
    expected = engine_profile(record.get('registry', {}))
    if (not isinstance(profile, dict) or type(profile.get('version')) is not int
            or profile != expected or ('extensions' in profile and type(profile['extensions']) is not int)):
        raise FeatureUnavailable('This record has no supported recovery profile; old records remain inspectable')
    if record.get('checkpoint_digest') != checkpoint:
        raise ValueError('Stale checkpoint; inspect the current run before changing it')
    if Path(record['record_path']).resolve() != store.path.resolve():
        raise ValueError('Copied run cannot be resumed as another owner; use the original run directory')
    if record.get('operation') != 'review' or record.get('status') not in (
        'running', 'paused', 'unresolved', 'failed', 'unavailable', 'completed', 'cancelled',
    ):
        raise ValueError('Unsupported recovery state')
    seen = set()
    for event in record['events']:
        if event['kind'] not in ('preflight_verification', 'initial_retrieval', 'participant_turn', 'tool', 'final_verification'):
            raise ValueError('Unsupported saved operation kind')
        if type(event['attempts']) is not int or not 1 <= event['attempts'] <= 2:
            raise ValueError('Invalid saved attempt count')
        if event['operation_key'] in seen:
            raise ValueError('Duplicate operation keys')
        seen.add(event['operation_key'])
        if (event['phase'], event['state']) not in (
            ('prepared', 'pending'), ('dispatching', 'pending'), ('dispatching', 'failed'), ('completed', 'completed'),
        ):
            raise ValueError('Invalid saved operation state')
    return record


def ensure_active(record):
    if record['status'] in ('completed', 'cancelled'):
        raise ValueError(f"Run is already {record['status']}")


def resume_review(directory: Path, request: Path, config: Path, checkpoint: str, *,
                  allow_external=False, max_operations=None, exchange_factory=ReviewExchange):
    from .review import prepare_review, execute_review
    store = RunStore(directory, existing=True)
    with store.lease():
        record = load_recovery(store, checkpoint)
        if record['status'] == 'completed':
            return record
        ensure_active(record)
        prepared = prepare_review(request, config)
        if prepared['requirement_revision'] != record['requirement_revision']:
            raise ValueError('Accepted request, registry or source snapshot changed; continuation refused')
        for event in record['events']:
            if event['state'] != 'completed' and event['phase'] != 'prepared':
                raise UnresolvedOperation(f"Operation {event['event_id']} may have executed; reconcile before resume")
        require_feature('attune-verify', 'attune_verify', VERIFY_VERSION, 'review')
        require_feature('attune-rag', 'attune_rag', RAG_VERSION, 'review')
        return execute_review(record, store, prepared, allow_external=allow_external,
                              max_operations=max_operations, exchange_factory=exchange_factory)


def reconcile_review(directory: Path, checkpoint: str, event_id: str, *,
                     reply_file: Path | None = None, retry_read_only=False):
    if (reply_file is not None) == retry_read_only:
        raise ValueError('Choose one recovered reply or read-only retry')
    store = RunStore(directory, existing=True)
    with store.lease():
        record = load_recovery(store, checkpoint)
        ensure_active(record)
        event = next((item for item in record['events'] if item['event_id'] == event_id), None)
        if event is None or event['phase'] != 'dispatching' or event['state'] == 'completed':
            raise ValueError('Event is not an unresolved dispatch')
        before = copy.deepcopy(event)
        if reply_file is not None:
            if event['kind'] != 'participant_turn':
                raise ValueError('Recovered replies apply only to participant turns')
            raw = read_text(reply_file, 65_536)
            action = decode_action(raw, event['request_digest'])
            event.update(state='completed', phase='completed', result={'action': action, 'identity': None})
            evidence = {'kind': 'recovered_reply', 'path': str(reply_file.resolve()),
                        'sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(), 'raw': raw,
                        'identity': 'operator-supplied; not authenticated'}
        else:
            if event['effect_class'] != 'read_only':
                raise UnresolvedOperation('Unknown external effects cannot be retried as read-only')
            if event['attempts'] >= 2:
                raise ValueError('Read-only retry limit exhausted')
            event.update(state='pending', phase='prepared', attempts=event['attempts'] + 1)
            evidence = {'kind': 'explicit_read_only_retry'}
        event.pop('error', None)
        event.pop('effects', None)
        record['recovery']['reconciliations'].append({'event_id': event_id,
            'checkpoint': checkpoint, 'previous': before, 'evidence': evidence})
        record['status'] = 'paused'
        record.pop('error', None)
        store.save(record)
        return record


def transfer_lead(directory: Path, checkpoint: str, participant_id: str, reason: str):
    bounded_text(reason, 'transfer reason')
    store = RunStore(directory, existing=True)
    with store.lease():
        record = load_recovery(store, checkpoint)
        ensure_active(record)
        recovery = record['recovery']
        current = recovery['assignments']['lead']
        if participant_id not in record['registry']['participants'] or participant_id in (
            current['participant_id'], recovery['assignments']['reviewer']['participant_id'],
        ):
            raise ValueError('Choose a different lead already in the accepted registry, distinct from the reviewer')
        if len(recovery['transfers']) >= 2:
            raise ValueError('Transfer limit exhausted')
        if any(event['state'] != 'completed' for event in record['events']):
            raise UnresolvedOperation('Transfer requires reconciliation of every pending operation')
        reviewer_attempt = recovery['assignments']['reviewer']['attempt_id']
        if any(event.get('attempt_id') == reviewer_attempt for event in record['events']):
            raise ValueError('Transfer is unavailable after independent reviewer execution begins')
        prior = [copy.deepcopy(event) for event in record['events'] if event.get('attempt_id') == current['attempt_id']]
        transfer = {'from': current['participant_id'], 'to': participant_id, 'checkpoint': checkpoint,
                    'prior_attempt_id': current['attempt_id'], 'reason': reason,
                    'reason_provenance': 'operator assertion; not governance authority',
                    'prior_events': prior, 'prior_participant': copy.deepcopy(record['participants'].get('lead'))}
        recovery['transfers'].append(transfer)
        recovery['assignments']['lead'] = {'participant_id': participant_id, 'attempt_id': str(uuid4())}
        record['participants'].pop('lead', None)
        record['status'] = 'paused'
        record.pop('error', None)
        store.save(record)
        return record


def cancel_review(directory: Path, checkpoint: str, reason: str):
    bounded_text(reason, 'cancellation reason')
    store = RunStore(directory, existing=True)
    with store.lease():
        record = load_recovery(store, checkpoint)
        if record['status'] in ('completed', 'cancelled'):
            return record  # Terminal state wins; no mutation and no rollback claim.
        record['recovery']['cancellation'] = {'reason': reason, 'checkpoint': checkpoint,
                                             'effects': 'Pending external effects remain unresolved; no rollback was performed'}
        record['status'] = 'cancelled'
        store.save(record)
        return record
