"""Private plan profiles; local inspection never opens Keychain or a network."""

import copy
import json
import math
import os
import re
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .features import FeatureUnavailable, replace_file
from .plan_oauth import OAuthClient, SCOPES, remaining
from .review_contract import parse_json

PROFILE = 'plan-responses-v1'
ID = re.compile(r'plan_[0-9a-f]{32}')


def profile_id(value):
    if not isinstance(value, str) or ID.fullmatch(value) is None:
        raise ValueError('An opaque plan profile ID is required')
    return value


class ProfileStore:
    def __init__(self, root=None, *, backend=None, oauth=None):
        self.root = Path(root) if root is not None else (
            Path.home()/'Library/Application Support/attune-harness/plan-oauth')
        self.backend, self.oauth = backend, oauth or OAuthClient()

    def _storage(self):
        if self.backend is None:
            from .plan_keychain import Keychain
            self.backend = Keychain()
        return self.backend

    def _paths(self):
        if not self.root.is_absolute() or any(p.is_symlink() for p in (self.root, *self.root.parents)):
            raise FeatureUnavailable('Plan storage path is unsafe')
        if self.root.exists():
            info = self.root.stat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) & 0o077):
                raise FeatureUnavailable('Plan storage must be owner-only')

    def _read(self):
        self._paths()
        path = self.root/'profiles.json'
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0))
        except FileNotFoundError:
            return {'version': 1, 'host_id': None, 'profiles': {}}
        except OSError:
            raise FeatureUnavailable('Plan metadata must be private') from None
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o077):
                raise ValueError('Unsafe metadata')
            with os.fdopen(fd, 'rb', closefd=False) as source:
                raw = source.read(131073)
            if len(raw) > 131072: raise ValueError('Metadata limit')
            value = parse_json(raw.decode('utf-8'), 131072)
            if (not isinstance(value, dict) or set(value) != {'version', 'host_id', 'profiles'}
                    or type(value['version']) is not int or value['version'] != 1):
                raise ValueError('Metadata version')
            if not isinstance(value['profiles'], dict) or len(value['profiles']) > 64:
                raise ValueError('Metadata profiles')
            host_id = value['host_id']
            if host_id is not None:
                if (not isinstance(host_id, str) or not host_id.startswith('urn:uuid:')
                        or str(UUID(host_id[9:])) != host_id[9:] or UUID(host_id[9:]).version != 4):
                    raise ValueError('Metadata host identifier')
            elif value['profiles']:
                raise ValueError('Metadata host identifier missing')
            labels = set()
            for pid, row in value['profiles'].items():
                profile_id(pid)
                if (set(row) != {'label', 'enabled', 'generation', 'expires_at', 'disconnecting', 'pending', 'refreshing'}
                        or not isinstance(row['label'], str) or not 1 <= len(row['label']) <= 128
                        or type(row['enabled']) is not bool or type(row['disconnecting']) is not bool
                        or type(row['pending']) is not bool
                        or (row['refreshing'] is not None and (not isinstance(row['refreshing'], str)
                            or not re.fullmatch('[0-9a-f]{32}', row['refreshing'])))
                        or not re.fullmatch('[0-9a-f]{32}', row['generation'])
                        or type(row['expires_at']) not in (int, float)
                        or not math.isfinite(row['expires_at'])):
                    raise ValueError('Metadata binding')
                if row['label'] in labels or (row['enabled'] and (row['pending'] or row['disconnecting'])):
                    raise ValueError('Metadata state')
                labels.add(row['label'])
            return value
        except Exception:
            raise FeatureUnavailable('Plan metadata is invalid') from None
        finally:
            os.close(fd)

    def _save(self, value):
        self._paths()
        raw = json.dumps(value, allow_nan=False).encode()
        if len(raw) > 131072: raise FeatureUnavailable('Plan metadata limit reached')
        fd, temporary = tempfile.mkstemp(prefix='.profiles-', dir=self.root)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(raw); f.flush(); os.fsync(f.fileno())
            replace_file(Path(temporary), self.root/'profiles.json')
            directory = os.open(self.root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    @contextmanager
    def _file_lock(self, name, deadline):
        import fcntl
        self._paths()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._paths()
        fd = os.open(self.root/name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o077):
                raise FeatureUnavailable('Plan lock must be owner-only')
            while True:
                remaining(deadline)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); break
                except BlockingIOError:
                    time.sleep(min(0.02, remaining(deadline)))
            yield
        finally:
            os.close(fd)

    def lock(self, deadline):
        return self._file_lock('.lock', deadline)

    def refresh_lock(self, pid, deadline):
        profile_id(pid)
        return self._file_lock('.refresh-' + pid, deadline)

    @staticmethod
    def _validate_record(record):
        try:
            if not isinstance(record, dict): raise ValueError('record')
            for name in ('client_id', 'subject', 'access_token', 'refresh_token'):
                value = record[name]
                limit = 32768 if name.endswith('_token') else 512
                if (not isinstance(value, str) or not 1 <= len(value) <= limit
                        or any(c.isspace() or ord(c) < 32 for c in value)):
                    raise ValueError('field')
            if record['client_id'] == 'dynamic_agent_client': raise ValueError('client')
            if record.get('id_token') is not None:
                value = record['id_token']
                if (not isinstance(value, str) or not 1 <= len(value) <= 32768
                        or any(c.isspace() or ord(c) < 32 for c in value)):
                    raise ValueError('identity token')
            scopes = record['scopes']
            if (not isinstance(scopes, list) or not scopes or
                    any(not isinstance(x, str) or not x or any(c.isspace() for c in x) for x in scopes)
                    or len(scopes) != len(set(scopes)) or not SCOPES <= set(scopes)):
                raise ValueError('scopes')
            if (type(record['expires_at']) not in (int, float) or not math.isfinite(record['expires_at'])
                    or not isinstance(record['generation'], str)
                    or re.fullmatch('[0-9a-f]{32}', record['generation']) is None):
                raise ValueError('expiry or generation')
        except Exception:
            raise FeatureUnavailable('Plan profile credential record is invalid') from None

    def _bound_record(self, index, pid, record):
        """Reconcile a protected successor, or refuse an uncertain rotation."""
        row = index['profiles'][pid]
        self._validate_record(record)
        if row['refreshing'] is not None:
            if (record.get('_previous_generation') != row['refreshing']
                    or record.get('generation') == row['generation']):
                raise FeatureUnavailable('Plan refresh outcome is uncertain; reconnect explicitly')
            row.update(generation=record['generation'], expires_at=record['expires_at'], refreshing=None)
            self._save(index)
        elif record.get('generation') != row['generation']:
            raise FeatureUnavailable('Plan profile credential binding differs')
        if row['expires_at'] != record['expires_at']:
            raise FeatureUnavailable('Plan profile credential binding differs')
        return record

    def inspect(self, pid):
        profile_id(pid)
        if os.name == 'nt' and self.backend is None:
            return {'profile_id': pid, 'state': 'unsupported_platform', 'qualification': PROFILE}
        row = self._read()['profiles'].get(pid)
        state = ('missing_profile' if row is None else 'disconnect_pending' if row['disconnecting']
                 else 'connection_pending' if row['pending'] else 'refresh_pending' if row['refreshing']
                 else 'disabled_profile' if not row['enabled']
                 else 'expired_profile' if row['expires_at'] <= time.time() else 'available')
        return {'profile_id': pid, 'state': state, 'qualification': PROFILE,
                **({'label': row['label'], 'expires_at': row['expires_at']} if row else {})}

    def connect(self, label, deadline):
        if (not isinstance(label, str) or not label.strip() or len(label) > 128
                or any(ord(c) < 32 for c in label)):
            raise ValueError('A bounded nonempty profile label is required')
        backend = self._storage()
        backend.probe(deadline)
        with self.lock(deadline):
            index = self._read()
            if index['host_id'] is None:
                index['host_id'] = 'urn:uuid:' + str(uuid4())
            pid = next((p for p, r in index['profiles'].items() if r['label'] == label), None)
            if pid is None:
                if len(index['profiles']) >= 64: raise FeatureUnavailable('Profile limit reached')
                pid = 'plan_' + uuid4().hex
                index['profiles'][pid] = {'label':label, 'enabled':False, 'disconnecting':False,
                    'pending':True, 'refreshing':None, 'generation':uuid4().hex, 'expires_at':0}
                self._save(index)
            row = index['profiles'][pid]
            if row['disconnecting']: raise FeatureUnavailable('Profile disconnect is incomplete')
            old, host_id = copy.deepcopy(row), index['host_id']
        previous = backend.get(pid, deadline)
        if previous is None and not old['pending']:
            raise FeatureUnavailable('Plan profile credential binding is missing')
        record = self.oauth.connect(host_id, previous, deadline)
        stored = False
        try:
            with self.refresh_lock(pid, deadline):
                with self.lock(deadline):
                    index = self._read()
                    if index['profiles'].get(pid) != old:
                        raise FeatureUnavailable('Profile changed during consent; inspect before reconnecting')
                    if previous and (record['subject'], record['client_id'], set(record['scopes'])) != (
                            previous['subject'], previous['client_id'], set(previous['scopes'])):
                        raise FeatureUnavailable('A different account or permission requires a new profile')
                generation = uuid4().hex
                record = {**record, 'generation':generation, '_previous_generation':old['generation']}
                backend.put(pid, record, deadline)
                stored = True
                with self.lock(deadline):
                    index = self._read()
                    if index['profiles'].get(pid) != old:
                        raise FeatureUnavailable('Profile changed during consent; inspect before reconnecting')
                    index['profiles'][pid].update(enabled=True, pending=False, refreshing=None,
                        generation=generation, expires_at=record['expires_at'])
                    self._save(index)
        except Exception:
            # A stored result is recoverable by explicit reconnect or disconnect.
            # A stale result not stored has no durable owner: attempt bounded revoke.
            if not stored:
                try: revoked = bool(self.oauth.revoke(record, deadline))
                except Exception: revoked = False
                if not revoked:
                    raise FeatureUnavailable('Profile change refused; new grant revocation is unconfirmed') from None
            raise
        return self.inspect(pid)

    def resolve(self, pid, deadline):
        profile_id(pid)
        with self.refresh_lock(pid, deadline):
            with self.lock(deadline):
                index = self._read(); row = index['profiles'].get(pid)
                if row is None or not row['enabled']:
                    raise FeatureUnavailable('Plan profile is missing or disabled')
                snapshot = copy.deepcopy(row)
            record = self._storage().get(pid, deadline)
            with self.lock(deadline):
                index = self._read(); row = index['profiles'].get(pid)
                if row != snapshot:
                    raise FeatureUnavailable('Plan profile changed during resolution')
                self._bound_record(index, pid, record)
                if not SCOPES <= set(record.get('scopes', [])):
                    raise FeatureUnavailable('Plan profile lacks granted permission')
                if record['expires_at'] > time.time() + 30:
                    remaining(deadline)
                    return {'profile_id':pid, 'generation':record['generation'],
                            'token':record['access_token'], 'qualification':PROFILE}
                before = row['generation']
                row['refreshing'] = before
                self._save(index)  # Written before a remote refresh can consume the token.
            rotated = self.oauth.refresh(record, deadline)
            rotated.update(generation=uuid4().hex, _previous_generation=before)
            self._storage().put(pid, rotated, deadline)
            with self.lock(deadline):
                index = self._read(); row = index['profiles'].get(pid)
                if row is None or not row['enabled'] or row['generation'] != before or row['refreshing'] != before:
                    raise FeatureUnavailable('Plan profile changed during refresh')
                row.update(generation=rotated['generation'], expires_at=rotated['expires_at'], refreshing=None)
                self._save(index)
            remaining(deadline)
            return {'profile_id':pid, 'generation':rotated['generation'],
                    'token':rotated['access_token'], 'qualification':PROFILE}

    @contextmanager
    def claim(self, pid, generation, deadline):
        with self.lock(deadline):
            row = self._read()['profiles'].get(pid)
            if (row is None or not row['enabled'] or row['refreshing'] is not None
                    or row['generation'] != generation):
                raise FeatureUnavailable('Plan profile changed before dispatch')
            yield

    def current(self, pid, generation):
        row = self._read()['profiles'].get(pid)
        return bool(row and row['enabled'] and not row['pending']
                    and row['refreshing'] is None and row['generation'] == generation)

    def disconnect(self, pid, deadline):
        profile_id(pid)
        with self.lock(deadline):
            index = self._read(); row = index['profiles'].get(pid)
            if row is None: raise FeatureUnavailable('Unknown plan profile')
            if not row['disconnecting']:
                row.update(enabled=False, disconnecting=True, generation=uuid4().hex, expires_at=0)
                self._save(index)
        try:
            with self.refresh_lock(pid, deadline):
                with self.lock(deadline):
                    row = self._read()['profiles'][pid]
                    refreshing = row['refreshing']
                record = self._storage().get(pid, deadline)
                uncertain = bool(refreshing and (not record or record.get('_previous_generation') != refreshing))
                confirmed = False
                try:
                    confirmed = bool(record and self.oauth.revoke(record, deadline)) and not uncertain
                except Exception:
                    pass
                if record:
                    retained = {k: record[k] for k in ('client_id', 'subject', 'scopes')}
                    retained['_revocation_confirmed'] = confirmed
                    self._storage().put(pid, retained, deadline)
                with self.lock(deadline):
                    index = self._read(); row = index['profiles'][pid]
                    row.update(disconnecting=False, refreshing=None)
                    self._save(index)
                return {'profile_id':pid, 'state':'disabled_profile',
                        'remote_revocation_confirmed':confirmed, 'cancellation_requested':True}
        except Exception:
            return {'profile_id':pid, 'state':'disabled_profile',
                    'remote_revocation_confirmed':False, 'cancellation_requested':True,
                    'cleanup_pending':True}


def store():
    return ProfileStore()
