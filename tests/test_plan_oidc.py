"""Actual OIDC signature/claim checks against local keys, never auth endpoints."""
# qualify: platform
import time

import pytest

from attune_harness.features import FeatureUnavailable
from attune_harness.plan_oauth import OAuthClient, ISSUER, SCOPES


@pytest.fixture
def signed():
    pytest.importorskip('authlib')
    from authlib.jose import JsonWebKey, JsonWebToken
    key = JsonWebKey.generate_key('RSA', 2048, is_private=True)
    private, public = key.as_dict(is_private=True), key.as_dict()
    claims = {'iss': ISSUER, 'sub': 'inert-subject', 'aud': 'inert-issued-client',
              'iat': int(time.time()), 'exp': int(time.time()) + 120, 'nonce': 'inert-nonce'}
    def encode(value):
        return JsonWebToken(['RS256']).encode({'alg': 'RS256'}, value, private).decode()
    def transport(url, deadline, form=None):
        assert form is None
        if url.endswith('/.well-known/openid-configuration'):
            return {'issuer': ISSUER, 'jwks_uri': ISSUER+'/inert-jwks'}
        assert url == ISSUER+'/inert-jwks'
        return {'keys': [public]}
    return OAuthClient(transport), claims, encode


def test_oidc_valid_signature_issuer_audience_expiry_nonce(signed):
    client, claims, encode = signed
    assert client.validate_identity(encode(claims), 'inert-issued-client', time.monotonic()+2,
                                    nonce='inert-nonce') == 'inert-subject'


@pytest.mark.parametrize('field,value', [('iss', 'https://inert.invalid'), ('aud', 'other-client'),
    ('exp', 0), ('exp', float('nan')), ('iat', float('inf')), ('nonce', 'other-nonce'), ('sub', ''), ('iat', 999999999999)])
def test_oidc_refuses_invalid_claims(signed, field, value):
    client, claims, encode = signed
    with pytest.raises(FeatureUnavailable):
        client.validate_identity(encode({**claims, field: value}), 'inert-issued-client',
                                 time.monotonic()+2, nonce='inert-nonce')


def test_oidc_refuses_invalid_signature_and_absent_token(signed):
    client, claims, encode = signed
    token = encode(claims)
    signature = token.rsplit('.', 1)[1]
    bad = token.rsplit('.', 1)[0] + '.' + ('A' if signature[0] != 'A' else 'B') + signature[1:]
    for value in (None, bad, 'not-an-id-token'):
        with pytest.raises(FeatureUnavailable):
            client.validate_identity(value, 'inert-issued-client', time.monotonic()+2, nonce='inert-nonce')


def test_actual_returned_scope_is_required_even_with_valid_identity(signed):
    client, claims, encode = signed
    value = {'access_token': 'inert-access', 'refresh_token': 'inert-refresh', 'token_type': 'Bearer',
             'expires_in': 120, 'id_token': encode(claims)}
    for scope in (None, 'openid profile email', ' '.join(SCOPES - {'chatgpt.tokens.use.direct'})):
        with pytest.raises(FeatureUnavailable):
            client.credentials({**value, 'scope': scope}, 'inert-issued-client',
                               time.monotonic()+2, nonce='inert-nonce')
