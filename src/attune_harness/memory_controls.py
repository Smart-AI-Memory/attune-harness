"""The strict content gate the legacy memory reader applies to every surfaced string.

Native memory Phase 2, step 2.2 (D19). The attune-ai adapter refuses to
surface a memory item when the sanitizer would change any string in it: a
secret it detects at high or critical severity, or personal data it would
rewrite. Harness needs the same refusal with nothing from attune-ai on the
path, so the detection is carried here. Only detection is carried, because
the contract is "any change means refused": nothing here redacts, and the
refusal text is the adapter's. The provenance fields and the instruction-shape
flags follow in step 2.3, with the differential that proves both sides agree.

The patterns are those of ``attune/memory/security/secrets_detector.py`` and
``pii_scrubber.py`` on the ``codex/shared-memory-adoption`` branch, read on
2026-09-22, at the severities that block. Medium and low findings there (JWT
shapes, bearer tokens, entropy) do not block and are not carried.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re

REFUSAL = "Source is unsafe or requires redaction; governed exposure refused"

# Secrets the sanitizer raises on (HIGH or CRITICAL). Names are the detector's.
_SECRETS = (
    ("anthropic_api_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{90,}")),
    ("openai_api_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}")),
    ("aws_access_key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws[_-]?secret[_-]?(?:access[_-]?)?key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("stripe_key", re.compile(r"\b[sp]k_(?:live|test)_[A-Za-z0-9]{24,}")),
    ("generic_api_key", re.compile(r"(?i)\b(?:api[_-]?key|apikey|access[_-]?token)\s*[=:]\s*['\"]?[A-Za-z0-9_\-./+=]{20,}")),
    ("password", re.compile(r"(?i)\b(?:password|passwd|pwd|pass)\s*[=:]\s*['\"][^'\"]{4,}['\"]")),
    ("basic_auth", re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/]{16,}={0,2}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----")),
    ("database_url", re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:/@]+:[^\s@]+@[^\s/]+")),
    ("connection_string", re.compile(r"(?i)\bconnection[_-]?string\s*[=:]\s*['\"]?[^'\"\s]{16,}")),
)
_MIXED = re.compile(r"(?=.*\d)(?=.*[a-z])(?=.*[A-Z])")
_LABELLED_KEY = re.compile(r"(?i)api[_-]?key\s*[=:]")

# Personal data the scrubber rewrites; a rewrite is a change, so a match refuses.
_PII = (
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ssn", re.compile(r"\b(?!000|666|9\d{2})\d{3}-?(?!00)\d{2}-?(?!0000)\d{4}\b")),
    ("phone", re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("ipv6", re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b")),
    ("street_address", re.compile(r"(?i)\b\d{1,6}\s+(?:[A-Za-z0-9.-]+\s){1,4}(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|way|place|pl)\b\.?")),
    ("mrn", re.compile(r"(?i)\bMRN[:\s#-]*\d{6,10}\b")),
    ("patient_id", re.compile(r"(?i)\b(?:Patient ID|PID)[:\s#-]*\d{5,10}\b")),
)


def _secret_hits(text):
    """The blocking secret detections in ``text``, by name."""
    found = []
    for name, pattern in _SECRETS:
        for match in pattern.finditer(text):
            token = match.group(0)
            if name in ("anthropic_api_key", "openai_api_key"):
                # A bare key-shaped run counts only with a digit and both cases, or a key label before it.
                before = text[max(0, match.start() - 24):match.start()]
                if not (_MIXED.search(token) or _LABELLED_KEY.search(before)):
                    continue
            found.append(name)
            break
    return found


def findings(text):
    """What the strict gate would change or refuse in ``text``: ``(secrets, personal)`` name lists."""
    if not isinstance(text, str):
        return ([], [])
    secrets = _secret_hits(text)
    personal = [name for name, pattern in _PII if pattern.search(text)]
    return (secrets, personal)


def strict(label, value):
    """True when the sanitizer would leave ``label=value`` unchanged, as the adapter tests it."""
    if not isinstance(value, str) or not value.strip():
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
        elif isinstance(value, (list, tuple)):
            stack.extend((label, item) for item in value)
        elif isinstance(value, str):
            if not strict(label, value):
                raise ValueError(REFUSAL)
