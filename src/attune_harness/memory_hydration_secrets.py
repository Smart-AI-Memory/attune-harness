"""Secret-only writer gate over complete captured and decoded source records.

The six reference patterns preserve the approved writer's blocking cases.
Existing Harness patterns add their blocking cases without importing its broader
personal-data policy. Placeholder exceptions apply to exact shared token spans.
"""

import re

from .memory_controls import _SECRETS, _plausible

REFUSAL = 'Hydration source contains blocking secrets'
_REFERENCE = tuple(re.compile(pattern) for pattern in (
    r'sk-ant-[A-Za-z0-9_-]{90,}',
    r'sk-(?:proj-)?[A-Za-z0-9]{20,}',
    r'AKIA[0-9A-Z]{16}',
    r'gh[pousr]_[A-Za-z0-9]{36,}',
    r'xox[baprs]-[A-Za-z0-9-]{10,}',
    r'-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----',
))
_PLACEHOLDER = re.compile(r'EXAMPLE|XXXX|REDACTED|PLACEHOLDER|YOUR[-_]', re.I)
# The broad OpenAI detector also matches the complete Anthropic token. That
# exact-span alias preserves reference placeholders without exempting a second,
# independent generic labelled API-key match or any Harness-only format.
_SHARED = {
    'anthropic_api_key': (0,), 'openai_api_key': (0, 1),
    'aws_access_key': (2,), 'github_token': (3,), 'slack_token': (4,),
    'rsa_private_key': (5,), 'ssh_private_key': (5,), 'ec_private_key': (5,),
    'pgp_private_key': (5,), 'tls_certificate_key': (5,),
}


def _blocked(text, check_budget):
    exempt = set()
    for family, pattern in enumerate(_REFERENCE):
        check_budget()
        for match in pattern.finditer(text):
            check_budget()
            if not _PLACEHOLDER.search(match.group(0)):
                return True
            exempt.add((family, match.span()))
    for name, blocks, pattern in _SECRETS:
        if not blocks:
            continue
        check_budget()
        for match in pattern.finditer(text):
            check_budget()
            if _plausible(name, match):
                span = match.span(1 if pattern.groups else 0)
                if not any((family, span) in exempt for family in _SHARED.get(name, ())):
                    return True
    return False


def _inspection_text(value):
    # Existing YAML binary keys and values use the same lossless inspection
    # text. This never rewrites source bytes or their capture identity.
    return value.decode('latin-1') if isinstance(value, bytes) else str(value)


def check_secrets(text, metadata=None, *, check_budget=lambda: None):
    """Refuse the complete record, including unknown decoded keys and values.

    Match the existing guard's label context but leave personal data alone.
    Walk iteratively and refuse cyclic YAML aliases rather than looping. The
    operation owner supplies the shared budget callback; this callback cannot
    interrupt a blocked parser or operating-system read.
    """
    if not isinstance(text, str):
        raise ValueError('Hydration source text must be UTF-8 text')
    if _blocked(text, check_budget) or _blocked('content=' + text, check_budget):
        raise ValueError(REFUSAL)
    active = set()
    stack = [('metadata', metadata, False)]
    while stack:
        check_budget()
        label, value, leaving = stack.pop()
        if leaving:
            active.remove(id(value))
        elif isinstance(value, (dict, list, tuple, set, frozenset)):
            if id(value) in active:
                raise ValueError('Hydration source metadata contains a cyclic alias')
            active.add(id(value))
            stack.append((label, value, True))
            if isinstance(value, dict):
                pairs = value.items()
            elif isinstance(value, tuple) and len(value) == 2:
                # PyYAML represents existing !!omap/!!pairs entries as tuples.
                # Preserve key=value context, not merely two isolated strings.
                pairs = (value,)
            else:
                stack.extend((label, item, False) for item in value)
                continue
            for key, item in pairs:
                key_text = _inspection_text(key)
                if (_blocked(key_text, check_budget)
                        or _blocked('metadata_key=' + key_text, check_budget)):
                    raise ValueError(REFUSAL)
                stack.append((key_text, item, False))
                if isinstance(key, (dict, list, tuple, set, frozenset, bytes)):
                    stack.append(('metadata_key', key, False))
        elif isinstance(value, (str, bytes)):
            decoded = _inspection_text(value)
            if (_blocked(decoded, check_budget)
                    or _blocked(f'{label}={decoded}', check_budget)):
                raise ValueError(REFUSAL)
