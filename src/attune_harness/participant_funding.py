"""Explicit funding configuration; admission stays closed until qualified."""

import re

from .features import FeatureUnavailable

UNSET = object()


def validate(adapter, policy):
    """Validate names only. Never read credentials or infer a legacy policy."""
    if adapter not in ('claude', 'codex'):
        raise ValueError('Funding is supported only for native Claude or Codex participants')
    if not isinstance(policy, dict) or policy.get('mode') not in ('subscription', 'api'):
        raise ValueError('Funding requires subscription or api mode')
    mode = policy['mode']
    expected = {'mode', 'credential_env'} if mode == 'api' else {'mode'}
    if set(policy) != expected:
        raise ValueError('Funding fields differ from the selected mode')
    if mode == 'api':
        if adapter != 'codex':
            raise ValueError('Explicit API funding is supported only for Codex')
        name = policy['credential_env']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', name):
            raise ValueError('API funding requires a portable credential environment variable name')
    return policy


def inspect(adapter, policy):
    """Report the qualified support boundary without probing auth or credentials."""
    validate(adapter, policy)
    return {'requested': policy['mode'], 'observed': 'unknown',
            'state': 'unsupported', 'basis': 'unqualified_invocation',
            'cli_version': None}


def require_admission(selected):
    """Prevent accepted policy from silently falling through to inherited auth.

    T1 did not qualify invocation-level selection. T2 accepts the configuration
    for inspection/binding only; no caller can authorize an unqualified route.
    """
    for item in selected.values():
        if 'funding' in item:
            validate(item['adapter'], item['funding'])
            raise FeatureUnavailable(
                'Explicit participant funding is not admitted: invocation-level route '
                'enforcement is unqualified. No provider call was started.')
