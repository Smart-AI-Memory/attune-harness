"""Thin integration with attune-verify's strict public result contract."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from .features import read_text, report, require_feature

VERIFY_VERSION = '0.6.0'


def verify_document(document: Path, context_file: Path) -> dict:
    """Check supported claims in one artifact against explicit trusted context.

    Context can select an interpreter and allowlisted help commands. The library
    owns extraction, checking and strict outcomes; no semantic judge is enabled.
    Result hashes bind the document and declared context, not all mutable targets.
    """
    library = require_feature('attune-verify', 'attune_verify', VERIFY_VERSION, 'verify')
    from attune_verify.manifest import load_context

    document, context_file = Path(document).resolve(), Path(context_file).resolve()
    if document.suffix.lower() not in ('.md', '.markdown'):
        raise ValueError('Verification input must be Markdown')
    context_text = read_text(context_file)
    manifest = json.loads(context_text)
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
        raise ValueError('Context requires integer schema_version 1')
    context = load_context(context_file)
    root = Path(context.project_root).resolve()
    if not document.is_relative_to(root):
        raise ValueError('Document is outside the declared project_root')
    content = read_text(document)
    result = library.verify(content, replace(context, document_path=document))
    if not isinstance(result, library.VerifyResult):
        raise TypeError('attune-verify returned an invalid result')
    if read_text(context_file) != context_text or read_text(document) != content:
        raise ValueError('Input changed during verification; run again against a stable artifact')
    payload = result.to_dict()
    if payload.get('schema_version') != 1 or payload.get('status') not in ('verified', 'refuted', 'unknown'):
        raise ValueError('Unsupported attune-verify result contract')
    passed = result.passes()
    if passed != (payload['status'] == 'verified'):
        raise ValueError('Inconsistent attune-verify strict result')
    return report(
        'verify', payload['status'], dependency={'name': 'attune-verify', 'version': VERIFY_VERSION},
        artifacts={
            'document': {'path': str(document), 'sha256': hashlib.sha256(content.encode('utf-8')).hexdigest()},
            'context': {'path': str(context_file), 'sha256': hashlib.sha256(context_text.encode('utf-8')).hexdigest()},
        },
        passed=passed, result=payload,
    )
