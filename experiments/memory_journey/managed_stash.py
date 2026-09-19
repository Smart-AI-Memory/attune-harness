"""Disposable, cooperative-writer adapter around the actual file stash."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/memory_worker'))
import worker
from attune_harness.review_contract import digest, parse_json
from attune_harness.review_store import RunStore, read_record
from attune.memory.file_stash import FileStashBackend


class Conflict(worker.old.StaleInput):
    pass


class PendingWrite(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('Explicit bounded identifier required')
    return value


def ordered(facts):
    return sorted(facts, key=lambda f: f['id'])


class ManagedStash:
    """Only explicit, separately provisioned project stores; no default backend."""
    def __init__(self, directory, scope):
        self.scope = identifier(scope)
        self.control = RunStore(Path(directory), existing=True)
        backend_dir = self.control.directory / 'backend'
        if backend_dir.is_symlink() or not backend_dir.is_dir():
            raise ValueError('Expected an existing isolated backend directory')
        if self._state()['scope'] != scope:
            raise ValueError('Requested project does not own this directory')
        self.backend = FileStashBackend(base_dir=backend_dir)
        self.path = backend_dir / 'findings.jsonl'

    @classmethod
    def create(cls, directory, scope):
        identifier(scope)
        control = RunStore(Path(directory))
        (control.directory / 'backend').mkdir()
        with control.lease():
            control.save(dict(schema_version=1, scope=scope, version=0, facts=[], sources=[],
                backend_sha=hashlib.sha256(b'').hexdigest(), pending=None, operations={}))
        return cls(directory, scope)

    def _state(self):
        return read_record(self.control.directory)

    def _fact(self, row):
        if not isinstance(row, dict) or not isinstance(row.get('topics'), list):
            raise ValueError('Malformed backend record')
        topics = row['topics']
        if any(not isinstance(t, str) for t in topics) or len(topics) != len(set(topics)):
            raise ValueError('Malformed backend topics')
        refs = [t[len('source:'):] for t in topics if t.startswith('source:')]
        if len(refs) > 8:
            raise ValueError('At most eight source IDs per note')
        for ref in refs:
            identifier(ref)
        expected = ['type:note', 'cwd:' + self.scope, *['source:' + id for id in refs]]
        if set(topics) != set(expected) or row.get('cwd') != self.scope or not refs:
            raise ValueError('Foreign scope, unknown kind or missing provenance')
        if not isinstance(row.get('text'), str) or not row['text'].strip() or len(row['text']) > 500:
            raise ValueError('Note content must be nonempty and at most 500 characters')
        return dict(id=identifier(row.get('id')), text=row['text'], scope=self.scope, kind='note', source_ids=refs)

    def _physical(self):
        if self.path.is_symlink():
            raise ValueError('Backend data must not be a symlink')
        raw = self.path.read_bytes() if self.path.exists() else b''
        if len(raw) > 65536:
            raise ValueError('Disposable backend exceeds 64 KiB')
        rows = [parse_json(line, 65536) for line in raw.decode('utf-8').splitlines() if line.strip()]
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'id','text','session_id','topics','cwd','ts'}:
                raise ValueError('Unknown physical record fields')
            if type(row['ts']) not in (int, float) or row['session_id'] is not None:
                raise ValueError('Unexpected physical timestamp or session')
        facts = [self._fact(row) for row in rows]
        if len(facts) > 8 or len({f['id'] for f in facts}) != len(facts):
            raise ValueError('Duplicate IDs or oversized backend')
        # Do not let malformed/expired physical rows disappear through forgiving API reads.
        visible = [self._fact(row) for row in self.backend.recent(limit=9)]
        if ordered(visible) != ordered(facts):
            raise ValueError('Physical records and backend-visible records disagree')
        return facts, hashlib.sha256(raw).hexdigest()

    def _stable(self):
        state = self._state()
        if state['pending'] is not None:
            raise PendingWrite('Pending write requires explicit reconciliation')
        facts, fingerprint = self._physical()
        if ordered(facts) != ordered(state['facts']) or fingerprint != state['backend_sha']:
            raise Conflict('Backend changed outside the captured control state')
        return state

    def snapshot(self):
        with self.control.lease():
            state = self._stable()
            return deepcopy({k: state[k] for k in ('scope', 'version', 'facts', 'sources', 'backend_sha')})

    def recall(self, query):
        with self.control.lease():
            state = self._stable()
            facts = [self._fact(row) for row in self.backend.search(query, limit=8, cwd=self.scope)]
            if len({f['id'] for f in facts}) != len(facts) or any(f not in state['facts'] for f in facts):
                raise ValueError('Recall contains an unknown or changed record')
            refs = {id for f in facts for id in f['source_ids']}
            return dict(scope=self.scope, version=state['version'], backend_sha=state['backend_sha'],
                        facts=facts, sources=[s for s in state['sources'] if s['id'] in refs])

    def assert_context(self, context):
        current = self.snapshot()
        if any(context.get(k) != current[k] for k in ('scope', 'version', 'backend_sha')):
            raise Conflict('Loaded context is stale; recall again')
        if any(f not in current['facts'] for f in context['facts']):
            raise Conflict('Loaded facts differ from active storage')
        refs = {id for f in context['facts'] for id in f['source_ids']}
        if context['sources'] != [s for s in current['sources'] if s['id'] in refs]:
            raise Conflict('Loaded evidence differs from active storage')

    def target(self, bound):
        grants = bound['grants']
        if grants['scopes'] != [self.scope] or grants['kinds'] != ['note'] or grants['classify_ids']:
            raise ValueError('Only scoped logical note mapping is supported')
        if any(s['scope'] != self.scope for s in bound['sources']):
            raise ValueError('Evidence crosses project scope')
        facts = bound['record']['facts']
        if len(facts) > 1 or any(f['scope'] != self.scope or f['kind'] != 'note' for f in facts):
            raise ValueError('A request must target one project note')
        create, remove = grants['create_ids'], grants['remove_ids']
        if len(create) == 1 and not remove and not facts:
            return 'capture', identifier(create[0])
        if len(facts) == 1 and not create:
            id = identifier(facts[0]['id'])
            if remove == [id]:
                return 'forget', id
            if not remove:
                return 'amend', id
        raise ValueError('Unsupported or ambiguous target grants')

    def _check_binding(self, state, bound):
        operation, target = self.target(bound)
        for source in bound['sources']:
            identifier(source['id'])
        if operation == 'capture' and len(state['facts']) >= 8:
            raise ValueError('Disposable project already contains eight notes')
        current = [f for f in state['facts'] if f['id'] == target]
        if state['version'] != bound['record']['version'] or current != bound['record']['facts']:
            raise Conflict('Proposal targets an old project version or changed note')
        refs = {id for f in current for id in f['source_ids']}
        supplied = {s['id']: s for s in bound['sources']}
        for source in state['sources']:
            if source['id'] in refs and supplied.get(source['id']) != source:
                raise Conflict('Captured source differs from stored provenance')
        return operation, target

    def assert_binding(self, bound):
        with self.control.lease():
            self._check_binding(self._stable(), bound)

    def _finish(self, state, fingerprint, disposition):
        pending = state['pending']
        if disposition == 'applied':
            state.update(deepcopy(pending['after']))
        receipt = dict(disposition=disposition, version=state['version'], request_digest=pending['request_digest'])
        state['operations'][pending['operation_id']] = receipt
        state.update(pending=None, backend_sha=fingerprint)
        self.control.save(state)
        return deepcopy(receipt)

    def apply(self, operation_id, request_digest, bound, candidate, operation):
        """Caller holds the worker lease; all backend changes hold this project lease."""
        with self.control.lease():
            state = self._stable()
            if operation_id in state['operations']:
                old = state['operations'][operation_id]
                if old['request_digest'] != request_digest:
                    raise ValueError('Conflicting reuse of a completed operation ID')
                return dict(old, replay=True)  # Never resurrect an older capture after forgetting.
            expected, target = self._check_binding(state, bound)
            if operation != expected or candidate['version'] != state['version'] + 1:
                raise ValueError('Operation or host version does not match the request')
            proposed = candidate['facts']
            if (operation == 'forget' and proposed) or (operation != 'forget' and len(proposed) != 1):
                raise ValueError('Expected exactly the selected resulting note')
            for fact in proposed:
                if fact['id'] != target or fact['kind'] != 'note' or fact['scope'] != self.scope:
                    raise ValueError('Unmapped kind, foreign scope or wrong target')
                if not fact['text'].strip() or len(fact['text']) > 500:
                    raise ValueError('Refusing note truncation')
            facts = ordered([f for f in state['facts'] if f['id'] != target] + deepcopy(proposed))
            if len(facts) > 8:
                raise ValueError('Disposable project exceeds eight notes')
            # Bound the actual append or rewrite before persisting intent/effects.
            # A 32-character timestamp placeholder exceeds this backend's float
            # representation. Existing append bytes may contain extra whitespace.
            def physical_size(items):
                total = 0
                for fact in items:
                    refs = fact['source_ids']
                    if not 1 <= len(refs) <= 8 or len(refs) != len(set(refs)):
                        raise ValueError('Expected one to eight unique source IDs')
                    for ref in refs:
                        identifier(ref)
                    row = dict(id=fact['id'], text=fact['text'], session_id=None,
                        topics=['type:note', 'cwd:' + self.scope, *['source:' + ref for ref in refs]],
                        cwd=self.scope, ts='9' * 32)
                    total += len((json.dumps(row, ensure_ascii=False) + '\n').encode('utf-8'))
                return total
            size = physical_size(facts)
            if operation == 'capture':
                size = (self.path.stat().st_size if self.path.exists() else 0) + physical_size(proposed)
            if size > 65536:
                raise ValueError('Resulting backend would exceed 64 KiB')
            sources = {s['id']: s for s in state['sources']}
            for source in bound['sources']:
                if source['id'] in sources and sources[source['id']] != source:
                    raise ValueError('Source ID reused for different evidence')
                sources[source['id']] = source
            refs = {id for f in facts for id in f['source_ids']}
            after = dict(version=state['version'] + 1, facts=facts,
                         sources=[sources[id] for id in sorted(refs)])
            state['pending'] = dict(operation_id=operation_id, request_digest=request_digest,
                                   before_sha=state['backend_sha'], after=after)
            self.control.save(state)
            if operation in ('amend', 'forget') and self.backend.forget([target]) != 1:
                raise PendingWrite('Removal acknowledgement failed; inspect before any retry')
            for fact in proposed:
                topics = ['type:note', 'cwd:' + self.scope, *['source:' + id for id in fact['source_ids']]]
                if not self.backend.remember(fact['text'], memory_id=target, topics=topics):
                    raise PendingWrite('Append acknowledgement failed; inspect before any retry')
            actual, fingerprint = self._physical()
            if ordered(actual) != facts:
                raise PendingWrite('Backend after-state differs from intended state')
            return self._finish(state, fingerprint, 'applied')

    def reconcile(self):
        """Observe actual files; never repeat a backend effect."""
        with self.control.lease():
            state = self._state()
            pending = state['pending']
            if pending is None:
                return dict(disposition='nothing_pending', version=state['version'])
            actual, fingerprint = self._physical()
            if ordered(actual) == ordered(pending['after']['facts']):
                return self._finish(state, fingerprint, 'applied')
            if fingerprint == pending['before_sha'] and ordered(actual) == ordered(state['facts']):
                return self._finish(state, fingerprint, 'not_applied')
            raise PendingWrite('Partial or foreign state; reconciliation cannot infer a safe outcome')
