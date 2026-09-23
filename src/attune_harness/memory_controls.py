"""The strict content gate the legacy memory reader applies to every surfaced string.

Native memory Phase 2, step 2.2 (D19). The attune-ai adapter refuses to
surface a memory item when the sanitizer would change any string in it: a
secret it detects at high or critical severity, or personal data it would
rewrite. Harness needs the same refusal with nothing from attune-ai on the
path, so the detection is carried here. Only detection is carried, because
the contract is "any change means refused": nothing here redacts, and the
refusal text is the adapter's. The provenance fields and the instruction-shape
flags follow in step 2.3, with the differential that proves both sides agree.

The patterns are the regex text of ``attune/memory/security/secrets_detector.py``
and ``pii_scrubber.py`` on the ``codex/shared-memory-adoption`` branch at
``b89f7953f``, verbatim, with their flags. Medium findings there (JWT shapes,
OAuth and bearer tokens) and the entropy heuristic are low severity: the
sanitizer neither blocks nor rewrites on them, so they are not carried.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re

REFUSAL = "Source is unsafe or requires redaction; governed exposure refused"

# (name, blocks, pattern): the detector's table. Group 1 is the token where the pattern has one.
_SECRETS = (
    ("anthropic_api_key", True, re.compile(
        r"(?i)(?:(?:anthropic[_-]?api[_-]?key|ANTHROPIC_API_KEY)\s*[=:]\s*[\"']?)?(sk-ant-[a-zA-Z0-9_-]{90,})[\"']?", re.M)),
    ("openai_api_key", True, re.compile(
        r"(?i)(?:(?:openai[_-]?api[_-]?key|OPENAI_API_KEY)\s*[=:]\s*[\"']?)?(sk-(?:proj-)?[a-zA-Z0-9_-]{40,})[\"']?", re.M)),
    ("aws_access_key", True, re.compile(r"\b(AKIA[A-Z0-9]{16})\b", re.M)),
    ("aws_secret_key", True, re.compile(
        r"(?i)(?:aws[_-]?secret[_-]?access[_-]?key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*[\"']?([a-zA-Z0-9/+=]{40})[\"']?", re.M)),
    ("github_token", True, re.compile(r"\b(gh[pousr]_[a-zA-Z0-9]{36,})\b", re.M)),
    ("slack_token", True, re.compile(r"\b(xox[abprs]-[a-zA-Z0-9-]+)\b", re.M)),
    ("stripe_key", True, re.compile(r"\b([sp]k_(?:live|test)_[a-zA-Z0-9]{24,})\b", re.M)),
    ("generic_api_key", True, re.compile(
        r"(?i)(?:api[_-]?key|apikey|access[_-]?token)\s*[=:]\s*[\"']?([a-zA-Z0-9_-]{20,})[\"']?", re.M)),
    ("password", True, re.compile(r"(?i)(?:password|passwd|pwd|pass)\s*[=:]\s*[\"']([^\"'\s]{4,})[\"']", re.M)),
    ("basic_auth", True, re.compile(
        r"(?i)(?:authorization:\s*basic\s+|basic\s+auth\s*[=:]\s*)([a-zA-Z0-9+/]{20,}={0,2})", re.M)),
    ("rsa_private_key", True, re.compile(r"-----BEGIN RSA PRIVATE KEY-----", re.M)),
    ("ssh_private_key", True, re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----", re.M)),
    ("ec_private_key", True, re.compile(r"-----BEGIN EC PRIVATE KEY-----", re.M)),
    ("pgp_private_key", True, re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----", re.M)),
    ("tls_certificate_key", True, re.compile(r"-----BEGIN PRIVATE KEY-----", re.M)),
    ("jwt_token", False, re.compile(r"\b(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b", re.M)),
    ("oauth_token", False, re.compile(r"(?i)(?:oauth[_-]?token|access[_-]?token)\s*[=:]\s*[\"']?([a-zA-Z0-9_-]{20,})[\"']?", re.M)),
    ("bearer_token", False, re.compile(r"(?i)(?:authorization:\s*bearer\s+|bearer\s+token\s*[=:]\s*)([a-zA-Z0-9_-]{20,})", re.M)),
    ("database_url", True, re.compile(r"(?i)(?:postgres|mysql|mongodb|redis)://[a-zA-Z0-9_-]+:[^@\s]+@[a-zA-Z0-9.-]+", re.M)),
    ("connection_string", True, re.compile(
        r"(?i)(?:connection[_-]?string|database[_-]?url|db[_-]?url)\s*[=:]\s*[\"']([^\"']+)[\"']", re.M)),
)
_BARE_KEY_TYPES = ("anthropic_api_key", "openai_api_key")
_KEY_LABEL = re.compile(r"(?i)api[_-]?key\s*[=:]")

# The scrubber's enabled patterns; a match is rewritten, and a rewrite is a change.
_PII = (
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.I)),
    ("ssn", re.compile(r"\b(?!000|666|9\d{2})\d{3}-?(?!00)\d{2}-?(?!0000)\d{4}\b")),
    ("phone", re.compile(r"""
                (?:
                    \+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}
                    |
                    \(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}
                    |
                    \b\d{3}[-.]?\d{3}[-.]?\d{4}\b
                )
                """, re.X)),
    ("credit_card", re.compile(r"""
                \b(?:
                    4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}
                    |
                    5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}
                    |
                    3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}
                    |
                    6(?:011|5\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}
                )\b
                """, re.X)),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")),
    ("ipv6", re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|\b:(?::[0-9a-fA-F]{1,4}){1,7}\b")),
    ("address", re.compile(
        r"\b\d{1,6}\s+(?:[A-Z][a-z]+\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct)"
        r"(?:\s+(?:Apt|Apartment|Suite|Ste|Unit|#)\s*\w+)?\b", re.I)),
    ("mrn", re.compile(r"\bMRN[:\s#-]*(\d{6,10})\b", re.I)),
    ("patient_id", re.compile(r"\b(?:Patient\s*ID|PID)[:\s#-]*(\d{5,10})\b", re.I)),
)


def _plausible(name, match):
    """The detector's bare-key rule: a labelled key is trusted; a bare one needs a digit and both cases."""
    if name not in _BARE_KEY_TYPES:
        return True
    if _KEY_LABEL.search(match.group(0)):
        return True
    token = match.group(1)
    has_digit = any(c.isdigit() for c in token)
    has_mixed = any(c.isupper() for c in token) and any(c.islower() for c in token)
    return has_digit and has_mixed


def findings(text):
    """What the strict gate would refuse or change in ``text``: ``(blocking secrets, personal data)`` name lists."""
    if not isinstance(text, str):
        return ([], [])
    secrets = [name for name, blocks, pattern in _SECRETS
               if blocks and any(_plausible(name, match) for match in pattern.finditer(text))]
    personal = [name for name, pattern in _PII if pattern.search(text)]
    return (secrets, personal)


def strict(label, value):
    """True when the sanitizer would leave ``label=value`` unchanged, as the adapter tests it.

    The adapter builds the candidate from the label and the value, so an empty
    value is a non-blank candidate and passes; only a non-string is refused.
    """
    if not isinstance(value, str):
        return False
    secrets, personal = findings(f"{label}={value}")
    return not secrets and not personal


def guard(text, metadata):
    """Refuse an item whose text or any metadata string the sanitizer would change.

    The adapter walks the same way: the text under the label ``content``,
    each metadata value under its key (nested values under their own keys),
    and every dict key under ``metadata_key``.
    """
    if not strict("content", text):
        raise ValueError(REFUSAL)
    stack = [("metadata", metadata)]
    while stack:
        label, value = stack.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if not strict("metadata_key", str(key)):
                    raise ValueError(REFUSAL)
                stack.append((str(key), item))
        elif isinstance(value, list):
            stack.extend((label, item) for item in value)
        elif isinstance(value, str):
            if not strict(label, value):
                raise ValueError(REFUSAL)
