"""Explicit public-client plan consent and maintained OIDC validation."""

import base64
import hashlib
import hmac
import json
import math
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from .features import FeatureUnavailable, require_feature
from .review_contract import parse_json

ISSUER = 'https://auth.openai.com'
RESOURCE = 'https://api.openai.com/v1'
SCOPES = frozenset('openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'.split())
TOKEN = ISSUER + '/api/accounts/oauth/token'


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0: raise FeatureUnavailable('Plan operation deadline reached')
    return seconds


def tls_bundle():
    certifi = require_feature('certifi', 'certifi', '2026.10.23', 'plan-oauth')
    return certifi.where()


def request(url, deadline, form=None):
    """Supervise auth I/O, including DNS, without writing credentials to disk."""
    import os
    from pathlib import Path
    import signal
    import subprocess
    import sys
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname != 'auth.openai.com'
            or parts.port not in (None, 443) or parts.username or parts.password
            or parts.fragment or parts.query):
        raise FeatureUnavailable('Unsupported plan authorization endpoint')
    payload = json.dumps({'url': url, 'form': form, 'timeout': remaining(deadline),
                          'ca_file': tls_bundle()}).encode()
    if len(payload) > 262144: raise FeatureUnavailable('Plan authorization input limit')
    child = subprocess.Popen((sys.executable, '-I', '-S',
        str(Path(__file__).with_name('plan_auth_worker.py'))), stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={}, start_new_session=True)
    try:
        output, _ = child.communicate(payload, timeout=remaining(deadline))
        if child.returncode or len(output) > 131072:
            raise FeatureUnavailable('Plan authorization request refused')
        remaining(deadline)
        return parse_json(output.decode(), 131072)
    except FeatureUnavailable:
        raise
    except Exception:
        raise FeatureUnavailable('Plan authorization transport failed') from None
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
        child.wait()

def open_browser(url, deadline):
    """Launch through a supervised child; the consent URL travels over stdin."""
    import os
    from pathlib import Path
    import signal
    import subprocess
    import sys
    remaining(deadline)
    payload = url.encode()
    if len(payload) > 131072: raise FeatureUnavailable('Plan consent URL limit')
    child = subprocess.Popen((sys.executable, '-I', '-S',
        str(Path(__file__).with_name('plan_browser_worker.py'))),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={}, start_new_session=True)
    try:
        child.communicate(payload, timeout=remaining(deadline))
        if child.returncode: raise FeatureUnavailable('Could not open the plan consent browser')
        remaining(deadline)
        return True
    except FeatureUnavailable:
        raise
    except Exception:
        raise FeatureUnavailable('Could not open the plan consent browser') from None
    finally:
        if child.poll() is None:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        child.wait()


class OAuthClient:
    def __init__(self, transport=request):
        self.transport = transport

    def preflight(self):
        """Refuse missing validators before consent can create a registration."""
        require_feature('Authlib', 'authlib', '1.9.3', 'plan-oauth')
        require_feature('joserfc', 'joserfc', '1.8.0', 'plan-oauth')
        require_feature('cryptography', 'cryptography', '50.0.2', 'plan-oauth')
        from authlib.jose import JsonWebToken
        from authlib.oidc.core import CodeIDToken
        if not callable(JsonWebToken) or not callable(CodeIDToken):
            raise FeatureUnavailable('Plan identity validators are unavailable')
        tls_bundle()

    def discovery(self, deadline):
        value = self.transport(ISSUER + '/.well-known/openid-configuration', deadline)
        if value.get('issuer') != ISSUER:
            raise FeatureUnavailable('Plan issuer differs from the accepted issuer')
        return value

    def validate_identity(self, token, client_id, deadline, *, nonce=None, access_token=None):
        require_feature('Authlib', 'authlib', '1.9.3', 'plan-oauth')
        require_feature('joserfc', 'joserfc', '1.8.0', 'plan-oauth')
        require_feature('cryptography', 'cryptography', '50.0.2', 'plan-oauth')
        from authlib.jose import JsonWebToken
        from authlib.oidc.core import CodeIDToken
        try:
            metadata = self.discovery(deadline)
            keys = self.transport(metadata['jwks_uri'], deadline)
            if not isinstance(keys.get('keys'), list) or not 1 <= len(keys['keys']) <= 64:
                raise ValueError('Invalid key set')
            options = {'iss': {'essential': True, 'value': ISSUER},
                       'aud': {'essential': True, 'value': client_id},
                       'exp': {'essential': True}, 'iat': {'essential': True},
                       'sub': {'essential': True}}
            params = {'nonce': nonce, 'access_token': access_token, 'client_id': client_id}
            claims = JsonWebToken(['RS256', 'ES256']).decode(token, keys,
                claims_cls=CodeIDToken, claims_options=options, claims_params=params)
            claims.validate(leeway=0)
            if any(type(claims[k]) not in (int, float) or not math.isfinite(claims[k])
                   for k in ('exp', 'iat')):
                raise ValueError('Invalid identity lifetime')
            subject = claims['sub']
            if not isinstance(subject, str) or not 1 <= len(subject) <= 512:
                raise ValueError('Invalid identity')
            remaining(deadline)
            return subject
        except Exception:
            raise FeatureUnavailable('Plan identity validation failed') from None

    def credentials(self, value, client_id, deadline, *, nonce=None, previous=None):
        try:
            if not isinstance(client_id, str) or not client_id or client_id == 'dynamic_agent_client':
                raise ValueError('Missing issued client')
            scopes = value.get('scope')
            if scopes is None and previous and nonce is None:
                scopes = previous['scopes']
            else:
                scopes = scopes.split()
            if not SCOPES <= set(scopes): raise ValueError('Plan permission missing')
            if previous and set(scopes) != set(previous['scopes']):
                raise ValueError('Plan permission changed')
            for name in ('access_token', 'refresh_token'):
                token = value[name]
                if (not isinstance(token, str) or not 1 <= len(token) <= 32768
                        or any(c.isspace() or ord(c) < 32 for c in token)):
                    raise ValueError('Invalid token')
            if value.get('token_type', '').lower() != 'bearer': raise ValueError('Invalid token type')
            seconds = value['expires_in']
            if type(seconds) not in (int, float) or not 0 < seconds <= 604800:
                raise ValueError('Invalid expiry')
            identity_token = value.get('id_token')
            if identity_token is None and previous and nonce is None:
                subject, identity_token = previous['subject'], previous.get('id_token')
            else:
                subject = self.validate_identity(identity_token, client_id, deadline,
                    nonce=nonce, access_token=value['access_token'])
            if previous and (subject != previous['subject'] or client_id != previous['client_id']):
                raise ValueError('Identity switch')
            return {'client_id': client_id, 'subject': subject, 'id_token': identity_token,
                    'access_token': value['access_token'], 'refresh_token': value['refresh_token'],
                    'scopes': sorted(set(scopes)), 'expires_at': time.time() + seconds}
        except FeatureUnavailable:
            raise
        except Exception:
            raise FeatureUnavailable('Plan grant is incomplete or differs from its profile') from None

    def refresh(self, previous, deadline):
        value = self.transport(TOKEN, deadline, {'grant_type': 'refresh_token',
            'client_id': previous['client_id'], 'refresh_token': previous['refresh_token'],
            'resource': RESOURCE})
        return self.credentials(value, previous['client_id'], deadline, previous=previous)

    def revoke(self, previous, deadline):
        if not previous.get('refresh_token'): return previous.get('_revocation_confirmed') is True
        metadata = self.discovery(deadline)
        self.transport(metadata['revocation_endpoint'], deadline,
            {'token': previous['refresh_token'], 'token_type_hint': 'refresh_token',
             'client_id': previous['client_id']})
        return True

    def connect(self, host_id, previous, deadline, browser=None):
        self.preflight()
        remaining(deadline)
        state, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(3))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        outcome = []
        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                parts = urlsplit(self.path)
                if parts.path != '/auth/callback':
                    self.send_error(404); return
                self.send_response(200); self.end_headers()
                self.wfile.write(b'Return to Attune Harness to inspect the connection result.')
                if outcome: return
                try:
                    args = parse_qs(parts.query, keep_blank_values=True, max_num_fields=12)
                    if any(len(v) != 1 for v in args.values()): raise ValueError('Duplicate callback field')
                    args = {k: v[0] for k, v in args.items()}
                    if not hmac.compare_digest(args.get('state', ''), state): raise ValueError('Invalid state')
                    if 'error' in args: raise ValueError('Consent refused')
                    client = args.get('client_id') or (previous or {}).get('client_id')
                    if not args.get('code') or not client or client == 'dynamic_agent_client':
                        raise ValueError('Incomplete registration')
                    if previous and client != previous['client_id']: raise ValueError('Client changed')
                    outcome.append((args['code'], client))
                except Exception:
                    outcome.append(None)
        class Loopback(ThreadingHTTPServer):
            daemon_threads = True
            def get_request(self):
                sock, address = super().get_request()
                sock.settimeout(min(1, remaining(deadline)))
                return sock, address
        server = Loopback(('127.0.0.1', 0), Callback)
        redirect = f'http://127.0.0.1:{server.server_port}/auth/callback'
        params = {'client_id': previous['client_id'] if previous else 'dynamic_agent_client',
                  'ext_agent_host_id': host_id, 'response_type': 'code', 'redirect_uri': redirect,
                  'scope': ' '.join(sorted(SCOPES)), 'resource': RESOURCE,
                  'state': state, 'nonce': nonce, 'code_challenge': challenge,
                  'code_challenge_method': 'S256'}
        if previous:
            if previous.get('id_token'): params['id_token_hint'] = previous['id_token']
        else: params['agent_name_hint'] = 'Attune Harness'
        try:
            # Never log the URL: reauthorization can contain a retained ID token.
            launcher = browser or open_browser
            if not launcher(ISSUER + '/api/accounts/authorize?' + urlencode(params), deadline):
                raise FeatureUnavailable('Could not open the plan consent browser')
            while not outcome:
                server.timeout = min(0.25, remaining(deadline)); server.handle_request()
            if outcome[0] is None: raise FeatureUnavailable('Plan callback or consent refused')
            code, client = outcome[0]
            value = self.transport(TOKEN, deadline, {'grant_type': 'authorization_code',
                'client_id': client, 'code': code, 'code_verifier': verifier,
                'redirect_uri': redirect, 'resource': RESOURCE})
            return self.credentials(value, client, deadline, nonce=nonce, previous=previous)
        finally:
            server.server_close()
