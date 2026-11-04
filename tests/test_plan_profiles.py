"""Offline profile lifecycle controls; no native storage or live account access."""
# qualify: platform
import copy
import importlib.util
import sys
import threading
import time
from pathlib import Path

import pytest
import attune_harness
from attune_harness.features import FeatureUnavailable

from attune_harness import plan_oauth as oauth_mod, plan_profiles as profiles
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='POSIX profile-lock doubles')
PID = 'plan_' + 'a' * 32
GEN = 'b' * 32

class Backend:
    def __init__(self): self.data = {}; self.available = True
    def probe(self, deadline):
        if not self.available: raise FeatureUnavailable('storage unavailable')
    def get(self, pid, deadline=None): return copy.deepcopy(self.data.get(pid))
    def put(self, pid, record, deadline=None): self.data[pid] = copy.deepcopy(record)

class OAuth:
    def __init__(self): self.started = threading.Event(); self.resume = threading.Event(); self.block = False; self.revoked = []
    def connect(self, host_id, previous, deadline): return credential()
    def refresh(self, record, deadline):
        self.started.set()
        if self.block: assert self.resume.wait(3)
        return {**record, 'refresh_token':'rotated', 'access_token':'new', 'expires_at':time.time()+300}
    def revoke(self, record, deadline): self.revoked.append(record['refresh_token']); return True

def credential():
    return {'client_id':'issued', 'subject':'person', 'scopes':sorted(oauth_mod.SCOPES),
            'id_token':'id', 'access_token':'old', 'refresh_token':'old', 'expires_at':0}

def store(tmp_path):
    backend, oauth = Backend(), OAuth()
    obj = profiles.ProfileStore(tmp_path.resolve(), backend=backend, oauth=oauth)
    backend.put(PID, {**credential(), 'generation':GEN})
    obj._save({'version':1, 'host_id':'urn:uuid:12345678-1234-4567-89ab-123456789abc', 'profiles':{PID:{
        'label':'test', 'enabled':True, 'disconnecting':False, 'pending':False, 'refreshing':None, 'generation':GEN, 'expires_at':0}}})
    return obj, backend, oauth

def response(**changes):
    return {'access_token':'access','refresh_token':'refresh','token_type':'Bearer',
            'expires_in':60,'scope':' '.join(sorted(oauth_mod.SCOPES)), **changes}

def test_reconnect_requires_fresh_id_token_and_nonce(monkeypatch):
    client = oauth_mod.OAuthClient()
    calls = []
    def validate(token, client_id, deadline, *, nonce, access_token):
        calls.append((token, nonce))
        if token is None: raise FeatureUnavailable('missing identity')
        return 'person'
    monkeypatch.setattr(client, 'validate_identity', validate)
    with pytest.raises(FeatureUnavailable):
        client.credentials(response(), 'issued', time.monotonic()+2, nonce='fresh', previous=credential())
    assert calls == [(None, 'fresh')]
    result = client.credentials(response(id_token='new-id'), 'issued', time.monotonic()+2, nonce='fresh', previous=credential())
    assert result['subject'] == 'person'
    assert calls[-1] == ('new-id', 'fresh')

def test_reconnect_and_refresh_refuse_changed_client_or_scope(monkeypatch):
    client = oauth_mod.OAuthClient()
    monkeypatch.setattr(client, 'validate_identity', lambda *args, **kw: 'person')
    previous = credential()
    for nonce in (None, 'fresh'):
        with pytest.raises(FeatureUnavailable):
            client.credentials(response(scope=' '.join(sorted(oauth_mod.SCOPES | {'other'})), id_token='id'),
                               'issued', time.monotonic()+2, nonce=nonce, previous=previous)
        with pytest.raises(FeatureUnavailable):
            client.credentials(response(id_token='id'), 'different-client', time.monotonic()+2,
                               nonce=nonce, previous=previous)

def test_missing_protected_record_refuses_before_consent(tmp_path):
    obj, backend, oauth = store(tmp_path)
    del backend.data[PID]
    oauth.connect = lambda *a: pytest.fail('consent was opened')
    with pytest.raises(FeatureUnavailable): obj.connect('test', time.monotonic()+2)

def test_storage_probe_failure_refuses_before_consent(tmp_path):
    obj, backend, oauth = store(tmp_path)
    backend.available = False
    oauth.connect = lambda *a: pytest.fail('consent was opened')
    with pytest.raises(FeatureUnavailable): obj.connect('new', time.monotonic()+2)

def test_rotation_index_failure_recovers_new_token(tmp_path, monkeypatch):
    obj, backend, oauth = store(tmp_path)
    save = obj._save
    writes = []
    def fail(value):
        writes.append(1)
        if len(writes) == 2: raise OSError('injected interrupted metadata update')
        save(value)
    monkeypatch.setattr(obj, '_save', fail)
    with pytest.raises(OSError): obj.resolve(PID, time.monotonic()+2)
    assert backend.get(PID)['refresh_token'] == 'rotated'
    monkeypatch.setattr(obj, '_save', save)
    recovered = obj.resolve(PID, time.monotonic()+2)
    assert recovered['token'] == 'new'
    assert obj._read()['profiles'][PID]['generation'] == recovered['generation']

def test_disconnect_marks_disabled_while_refresh_blocked(tmp_path):
    obj, backend, oauth = store(tmp_path); oauth.block = True
    errors = []
    def do_refresh():
        try: obj.resolve(PID, time.monotonic()+3)
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=do_refresh); thread.start()
    assert oauth.started.wait(1)
    result = obj.disconnect(PID, time.monotonic()+0.15)
    assert result['cleanup_pending'] and not result['remote_revocation_confirmed']
    assert not obj.current(PID, GEN)
    oauth.resume.set(); thread.join(2)
    assert errors and not thread.is_alive()
    result = obj.disconnect(PID, time.monotonic()+2)
    assert result['remote_revocation_confirmed']
    assert oauth.revoked == ['rotated']
    assert 'refresh_token' not in backend.get(PID)


def test_claim_reconciles_interrupted_rotation_and_refuses_old_generation(tmp_path, monkeypatch):
    obj, backend, oauth = store(tmp_path)
    save = obj._save
    writes = []
    def fail_second(value):
        writes.append(1)
        if len(writes) == 2: raise OSError('failed save')
        save(value)
    monkeypatch.setattr(obj, '_save', fail_second)
    with pytest.raises(OSError): obj.resolve(PID, time.monotonic()+2)
    monkeypatch.setattr(obj, '_save', save)
    with pytest.raises(FeatureUnavailable):
        with obj.claim(PID, GEN, time.monotonic()+2):
            pytest.fail('old capability was claimed')

def test_reconnect_refuses_different_validated_subject(monkeypatch):
    client = oauth_mod.OAuthClient()
    monkeypatch.setattr(client, 'validate_identity', lambda *args, **kw: 'different-person')
    with pytest.raises(FeatureUnavailable):
        client.credentials(response(id_token='new-id'), 'issued', time.monotonic()+2,
                           nonce='fresh', previous=credential())

def test_disconnect_cancels_another_profile_during_blocked_refresh(tmp_path):
    obj, backend, oauth = store(tmp_path); oauth.block = True
    second = 'plan_' + 'c' * 32
    backend.put(second, {**credential(), 'generation':GEN})
    with obj.lock(time.monotonic()+2):
        index = obj._read()
        index['profiles'][second] = {'label':'other', 'enabled':True, 'disconnecting':False, 'pending':False, 'refreshing':None,
                                     'generation':GEN, 'expires_at':0}
        obj._save(index)
    errors = []
    def do_refresh():
        try: obj.resolve(PID, time.monotonic()+3)
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=do_refresh); thread.start()
    try:
        assert oauth.started.wait(1)
        result = obj.disconnect(second, time.monotonic()+1)
        assert result['remote_revocation_confirmed']
        assert not obj.current(second, GEN)
    finally:
        oauth.resume.set(); thread.join(2)
    assert not thread.is_alive() and not errors

def hold_profile_lock(obj, ready, release):
    with obj.refresh_lock(PID, time.monotonic()+3):
        ready.set()
        release.wait(3)

def test_disconnect_across_processes_marks_disabled_before_lock_wait(tmp_path):
    import multiprocessing
    obj, backend, oauth = store(tmp_path)
    ctx = multiprocessing.get_context('fork')
    ready, release = ctx.Event(), ctx.Event()
    child = ctx.Process(target=hold_profile_lock, args=(obj, ready, release))
    child.start()
    try:
        assert ready.wait(2)
        result = obj.disconnect(PID, time.monotonic()+0.1)
        assert result['cleanup_pending'] and not obj.current(PID, GEN)
    finally:
        release.set(); child.join(3)
    assert child.exitcode == 0
    result = obj.disconnect(PID, time.monotonic()+2)
    assert result['remote_revocation_confirmed']

def test_uncertain_rotation_never_retries_until_explicit_reconnect(tmp_path):
    obj, backend, oauth = store(tmp_path)
    calls = []
    def uncertain(record, deadline):
        calls.append('refresh'); raise FeatureUnavailable('response lost')
    oauth.refresh = uncertain
    with pytest.raises(FeatureUnavailable): obj.resolve(PID, time.monotonic()+2)
    with pytest.raises(FeatureUnavailable, match='uncertain'):
        obj.resolve(PID, time.monotonic()+2)
    assert calls == ['refresh']
    result = obj.connect('test', time.monotonic()+2)
    assert result['state'] in ('available', 'expired_profile')
    assert obj._read()['profiles'][PID]['refreshing'] is None

def test_failed_protected_write_does_not_retry_consumed_refresh(tmp_path):
    obj, backend, oauth = store(tmp_path)
    original = backend.put
    def fail(pid, record, deadline=None): raise FeatureUnavailable('protected write failed')
    backend.put = fail
    with pytest.raises(FeatureUnavailable): obj.resolve(PID, time.monotonic()+2)
    backend.put = original
    oauth.refresh = lambda *args: pytest.fail('refresh token was reused')
    with pytest.raises(FeatureUnavailable, match='uncertain'): obj.resolve(PID, time.monotonic()+2)

def test_new_profile_failure_after_protected_write_needs_explicit_connect(tmp_path, monkeypatch):
    obj = profiles.ProfileStore(tmp_path.resolve(), backend=Backend(), oauth=OAuth())
    original = obj._save; writes = []
    def fail_second(index):
        writes.append(1)
        if len(writes) == 2: raise OSError('index failed')
        original(index)
    monkeypatch.setattr(obj, '_save', fail_second)
    with pytest.raises(OSError): obj.connect('new', time.monotonic()+2)
    row = obj._read()['profiles']; pid = next(iter(row))
    assert row[pid]['pending'] and not row[pid]['enabled']
    assert obj.backend.get(pid)['client_id'] == 'issued'
    with pytest.raises(FeatureUnavailable): obj.resolve(pid, time.monotonic()+2)
    seen = []
    def reconnect(host, previous, deadline):
        seen.append(previous['client_id']); return credential()
    obj.oauth.connect = reconnect
    monkeypatch.setattr(obj, '_save', original)
    assert obj.connect('new', time.monotonic()+2)['profile_id'] == pid
    assert seen == ['issued']

def test_stale_consent_result_attempts_revocation(tmp_path):
    obj, backend, oauth = store(tmp_path)
    def stale(host, previous, deadline):
        obj.disconnect(PID, deadline)
        return {**credential(), 'refresh_token':'orphan'}
    oauth.connect = stale
    with pytest.raises(FeatureUnavailable): obj.connect('test', time.monotonic()+2)
    assert oauth.revoked == ['old', 'orphan']

def test_supervised_helpers_send_secrets_only_through_stdin(monkeypatch):
    import subprocess
    from attune_harness import plan_keychain as keychain
    started = []
    class Child:
        returncode = 0
        pid = 424242
        def __init__(self, argv, **kwargs): self.argv = argv; started.append(self)
        def communicate(self, payload, timeout):
            self.payload, self.timeout = payload, timeout
            return (b'null', b'')
        def poll(self): return 0
        def wait(self): return 0
    monkeypatch.setattr(subprocess, 'Popen', Child)
    keychain.Keychain().put('plan_abc', {'refresh_token':'secret-token'}, time.monotonic()+2)
    assert b'secret-token' in started[-1].payload
    assert all('secret-token' not in arg for arg in started[-1].argv)
    oauth_mod.open_browser('https://example.invalid/?id_token=secret-token', time.monotonic()+2)
    assert b'secret-token' in started[-1].payload
    assert all('secret-token' not in arg for arg in started[-1].argv)

def test_supervised_storage_timeout_terminates_worker(monkeypatch):
    import os
    import subprocess
    from attune_harness import plan_keychain as keychain
    calls = []
    class Child:
        pid = 424242
        def __init__(self, *args, **kwargs): pass
        def communicate(self, payload, timeout): raise subprocess.TimeoutExpired('worker', timeout)
        def poll(self): return None
        def wait(self): calls.append('wait'); return 0
    monkeypatch.setattr(subprocess, 'Popen', Child)
    monkeypatch.setattr(os, 'killpg', lambda pid, sig: calls.append(('killed', pid)))
    with pytest.raises(FeatureUnavailable): keychain.Keychain().get(PID, time.monotonic()+1)
    assert calls == [('killed', 424242), 'wait']

def test_connect_uses_injectable_browser_and_fresh_nonce_without_network(monkeypatch):
    import io
    from urllib.parse import parse_qs, urlencode, urlsplit
    captured = {}
    class Server:
        def __init__(self, addr, handler): self.handler, self.server_port = handler, 12345
        def handle_request(self):
            request = object.__new__(self.handler)
            request.path = '/auth/callback?' + urlencode({'state':captured['state'], 'code':'test-code', 'client_id':'issued'})
            request.send_response = lambda code: None
            request.end_headers = lambda: None
            request.wfile = io.BytesIO()
            request.do_GET()
        def server_close(self): pass
    monkeypatch.setattr(oauth_mod, 'ThreadingHTTPServer', Server)
    def browser(url, deadline):
        args = parse_qs(urlsplit(url).query)
        captured.update(state=args['state'][0], nonce=args['nonce'][0])
        return True
    client = oauth_mod.OAuthClient(transport=lambda *args: response(id_token='fresh-id'))
    monkeypatch.setattr(client, 'preflight', lambda: None)  # OAuth flow double; real validators are tested separately.
    def validate(token, client_id, deadline, *, nonce, access_token):
        assert token == 'fresh-id' and nonce == captured['nonce']
        return 'person'
    monkeypatch.setattr(client, 'validate_identity', validate)
    result = client.connect('urn:uuid:host', None, time.monotonic()+2, browser=browser)
    assert result['client_id'] == 'issued'

def test_browser_timeout_terminates_worker(monkeypatch):
    import os
    import subprocess
    calls = []
    class Child:
        pid = 424243
        def __init__(self, *args, **kwargs): pass
        def communicate(self, payload, timeout): raise subprocess.TimeoutExpired('browser', timeout)
        def poll(self): return None
        def wait(self): calls.append('wait')
    monkeypatch.setattr(subprocess, 'Popen', Child)
    monkeypatch.setattr(os, 'killpg', lambda pid, sig: calls.append(('killed', pid)))
    with pytest.raises(FeatureUnavailable): oauth_mod.open_browser('https://example.invalid', time.monotonic()+1)
    assert calls == [('killed', 424243), 'wait']

def crash_during_refresh(obj):
    import os
    obj.oauth.refresh = lambda *args: os._exit(73)
    obj.resolve(PID, time.monotonic()+3)

def test_process_death_after_refresh_marker_never_reuses_token(tmp_path):
    import multiprocessing
    obj, backend, oauth = store(tmp_path)
    ctx = multiprocessing.get_context('fork')
    child = ctx.Process(target=crash_during_refresh, args=(obj,))
    child.start(); child.join(3)
    assert child.exitcode == 73
    oauth.refresh = lambda *args: pytest.fail('uncertain token was retried')
    with pytest.raises(FeatureUnavailable, match='uncertain'):
        obj.resolve(PID, time.monotonic()+2)
    result = obj.disconnect(PID, time.monotonic()+2)
    assert not result['remote_revocation_confirmed']
    assert result['cancellation_requested']

def test_refresh_marker_cancels_current_generation_before_provider_returns(tmp_path):
    obj, backend, oauth = store(tmp_path); oauth.block = True
    errors = []
    def refresh():
        try: obj.resolve(PID, time.monotonic()+3)
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=refresh); thread.start()
    try:
        assert oauth.started.wait(1)
        assert not obj.current(PID, GEN)
        with pytest.raises(FeatureUnavailable):
            with obj.claim(PID, GEN, time.monotonic()+1): pass
    finally:
        oauth.resume.set(); thread.join(2)
    assert not errors

def test_missing_access_token_is_generic_refusal(tmp_path):
    obj, backend, oauth = store(tmp_path)
    del backend.data[PID]['access_token']
    with pytest.raises(FeatureUnavailable, match='credential record is invalid'):
        obj.resolve(PID, time.monotonic()+2)

def test_invalid_host_identifier_is_refused(tmp_path):
    obj, backend, oauth = store(tmp_path)
    index = obj._read(); index['host_id'] = 'urn:uuid:not-a-uuid'; obj._save(index)
    with pytest.raises(FeatureUnavailable): obj.inspect(PID)

@pytest.mark.parametrize('raw', [b'{"version":1,"version":1,"host_id":null,"profiles":{}}',
                                 b'{"version":NaN,"host_id":null,"profiles":{}}'])
def test_metadata_rejects_duplicate_keys_and_nan(tmp_path, raw):
    obj, backend, oauth = store(tmp_path)
    (tmp_path/'profiles.json').write_bytes(raw)
    with pytest.raises(FeatureUnavailable): obj.inspect(PID)

def test_symlinked_root_and_metadata_are_refused(tmp_path):
    actual = tmp_path/'actual'; actual.mkdir(mode=0o700)
    alias = tmp_path/'alias'; alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(FeatureUnavailable): profiles.ProfileStore(alias, backend=Backend()).inspect(PID)
    root = tmp_path/'safe'; root.mkdir(mode=0o700)
    (root/'profiles.json').symlink_to(tmp_path/'missing')
    with pytest.raises(FeatureUnavailable): profiles.ProfileStore(root, backend=Backend()).inspect(PID)

def test_metadata_refuses_nonprivate_permissions(tmp_path):
    obj, backend, oauth = store(tmp_path)
    (tmp_path/'profiles.json').chmod(0o644)
    with pytest.raises(FeatureUnavailable): obj.inspect(PID)


def test_repeated_disconnect_preserves_unconfirmed_remote_result(tmp_path):
    obj, backend, oauth = store(tmp_path)
    def refuse(*args): raise FeatureUnavailable('inert revoke failed')
    oauth.revoke = refuse
    first = obj.disconnect(PID, time.monotonic()+2)
    assert not first['remote_revocation_confirmed']
    assert backend.get(PID).get('_revocation_confirmed') is False
    # Exercise the production missing-token branch; it must not invent remote success.
    obj.oauth = oauth_mod.OAuthClient(transport=lambda *a: pytest.fail('unexpected request'))
    second = obj.disconnect(PID, time.monotonic()+2)
    assert not second['remote_revocation_confirmed']


def test_inspect_exposes_refresh_marker_without_keychain_or_network(tmp_path):
    obj, backend, oauth = store(tmp_path)
    index = obj._read(); index['profiles'][PID]['refreshing'] = GEN; obj._save(index)
    backend.get = lambda *a: pytest.fail('inspect opened protected storage')
    assert obj.inspect(PID)['state'] == 'refresh_pending'



def test_repeat_disconnect_remains_unconfirmed(tmp_path):
    obj,backend,_=store(tmp_path); calls=[]
    def failed(*args):
        calls.append(1); raise FeatureUnavailable('inert failure')
    obj.oauth=oauth_mod.OAuthClient(transport=failed)
    assert not obj.disconnect(PID,time.monotonic()+2)['remote_revocation_confirmed']
    assert not obj.disconnect(PID,time.monotonic()+2)['remote_revocation_confirmed']
    assert len(calls)==1 and 'refresh_token' not in backend.get(PID)

def test_interrupted_refresh_is_visible_to_inspection(tmp_path):
    obj,backend,oauth=store(tmp_path); expiry=time.time()+20
    backend.data[PID]['expires_at']=expiry
    index=obj._read(); index['profiles'][PID]['expires_at']=expiry; obj._save(index)
    def failed(*args): raise FeatureUnavailable('lost refresh')
    oauth.refresh=failed
    with pytest.raises(FeatureUnavailable): obj.resolve(PID,time.monotonic()+2)
    assert obj.inspect(PID)['state']=='refresh_pending'


@pytest.mark.parametrize('missing', ['Authlib', 'joserfc', 'cryptography', 'certifi'])
def test_missing_dependency_refuses_before_listener_browser_or_exchange(monkeypatch, missing):
    calls = []
    def require(distribution, *args):
        calls.append(distribution)
        if distribution == missing: raise FeatureUnavailable('inert missing dependency')
        return type('Dependency', (), {'where': staticmethod(lambda: '/inert/ca.pem')})
    monkeypatch.setattr(oauth_mod, 'require_feature', require)
    if missing == 'certifi':
        # The production import check still runs; skip only when this optional
        # dependency is absent from a base-install test environment.
        pytest.importorskip('authlib')
    client = oauth_mod.OAuthClient(transport=lambda *a: pytest.fail('code exchange before preflight'))
    monkeypatch.setattr(oauth_mod, 'ThreadingHTTPServer', lambda *a: pytest.fail('listener before preflight'))
    with pytest.raises(FeatureUnavailable):
        client.connect('urn:uuid:host', None, time.monotonic()+1,
                       browser=lambda *a: pytest.fail('browser before preflight'))
    assert missing in calls


def test_expired_deadline_refuses_before_any_helper_or_listener(monkeypatch):
    import subprocess
    from attune_harness.plan_keychain import Keychain
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('expired helper launched'))
    monkeypatch.setattr(oauth_mod, 'ThreadingHTTPServer', lambda *a, **k: pytest.fail('expired listener opened'))
    client = oauth_mod.OAuthClient()
    monkeypatch.setattr(client, 'preflight', lambda: None)
    expired = time.monotonic()-1
    for action in (lambda: Keychain().get(PID, expired),
                   lambda: oauth_mod.open_browser('https://inert.invalid', expired),
                   lambda: client.connect('urn:uuid:host', None, expired)):
        with pytest.raises(FeatureUnavailable): action()
