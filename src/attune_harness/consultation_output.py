"""Pure, opt-in presentation of retained consultation envelopes.

Rendering neither reloads source nor mutates records or grants execution authority.
The caller supplies an already-loaded record; this module never opens source.
"""

import html
import re
import shlex
import unicodedata
from pathlib import Path

from .consultation_evidence import claims


def _visible(value):
    characters = []
    for char in str(value):
        code = ord(char)
        if (code < 32 and char not in '\n\t') or 127 <= code <= 159:
            characters.append(f'\\x{code:02x}')
        elif unicodedata.category(char) == 'Cf':
            characters.append(f'\\u{code:04x}' if code <= 0xffff else f'\\U{code:08x}')
        else:
            characters.append(char)
    return ''.join(characters)


def _text(value):
    value = html.escape(_visible(value), quote=True)
    value = re.sub(r'([\\`*_{}\[\]()#+.!|~-])', r'\\\1', value)
    return value.replace('\r', '&#13;').replace('\n', '<br>')


def _block(value, language='text'):
    value = _visible(value)
    longest = max((len(match.group()) for match in re.finditer(r'`+', value)), default=0)
    fence = '`' * max(3, longest + 1)
    return f'{fence}{language}\n{value.rstrip(chr(10))}\n{fence}'


def _reported(identity):
    if not identity:
        return 'not recorded'
    models = ', '.join(identity.get('reported_models', ())) or 'no model reported'
    return f'{identity.get("provider", "unknown provider")}: {models}'


def evidence_view(record):
    """Project the existing v1 evidence fields from one already-loaded record."""
    view = {'schema_version': 1, 'operation': record['operation'], 'status': record['status'],
            'contract_digest': record['contract_digest'], 'checkpoint_digest': record['checkpoint_digest'],
            'snapshot_digest': record['contract']['snapshot']['digest'], 'claims': claims(record),
            'authority': 'inspection_only'}
    if view['status'] == 'running':
        view = {**view, 'status': 'unresolved', 'persisted_status': 'running'}
    return view


def markdown(envelope, *, view, retained=None):
    """Render one validated envelope and optional already-loaded retained record."""
    record = retained if retained is not None else envelope
    contract = record.get('contract', {})
    operation = envelope.get('operation', 'consultation')
    output = [f'## {_text(operation)}: {_text(view)}', '',
              f'**Status:** {_text(envelope.get("status", "unknown"))}', '',
              'Retained model claims and this view grant no execution authority.']
    for name in ('contract_digest', 'checkpoint_digest', 'snapshot_digest'):
        value = envelope.get(name)
        if name == 'snapshot_digest' and not value:
            value = contract.get('snapshot', {}).get('digest')
        if value:
            output += ['', f'**{_text(name)}:** {_text(value)}']
    if envelope.get('persisted_status'):
        output += ['', '**Persisted status:** ' + _text(envelope['persisted_status'])]
    if envelope.get('error'):
        error = envelope['error']
        output += ['', f'**Error ({_text(error.get("type", "error"))}):** {_text(error.get("detail", ""))}']
    if envelope.get('status') == 'refused':
        return '\n'.join(output) + '\n'
    config = contract.get('configuration', {})
    seats = config.get('participants', {})
    if view == 'prepare':
        output += ['', '**Question:** ' + _text(config.get('question', '')),
                   '', '### Configured seats', '']
        for name, seat in seats.items():
            identity = seat['identity']
            output += [f'- {_text(name)}: {_text(identity["provider"])}/{_text(identity["model"])}; '
                       f'adapter {_text(seat["adapter"])}; timeout {_text(seat["timeout"])} seconds']
        output += ['', '### Frozen files', '']
        for path, item in contract.get('snapshot', {}).get('files', {}).items():
            output += [f'- {_text(path)}: SHA-256 {_text(item["sha256"])}; '
                       f'{len(item["text"].encode("utf-8"))} bytes']
        output += ['', '**Budget:** ' + '; '.join(f'{_text(k)}={_text(v)}' for k, v in contract.get('budget', {}).items())]
        if record.get('record_path'):
            output += ['', '**Saved record:** ' + _text(record['record_path'])]
            command = shlex.join(['attune-harness', operation, 'run', '--accept',
                                  record['contract_digest'], '--', str(Path(record['record_path']).parent)])
            output += ['', 'Scope acceptance command (POSIX shell):', '', _block(command, 'sh'), '',
                       'External and native dispatch grants remain separate; add their flags only when authorized.']
    else:
        for turn in record.get('answers', []):
            name = turn['participant']
            output += ['', f'### Round {_text(turn["round"])} / {_text(name)}', '',
                       '**Turn status:** ' + _text(turn['status'])]
            identity = turn.get('identity') or {}
            configured = identity.get('configured') or seats.get(name, {}).get('identity')
            if configured:
                output += ['**Configured identity:** ' + _text(configured['provider']) + '/' + _text(configured['model'])]
            reported = identity.get('reported')
            output += ['**Reported identity:** ' + _text(_reported(reported)),
                       '**Authenticated model:** ' + _text(identity.get('authenticated_model', False))]
            answer = turn.get('answer')
            if answer:
                output += ['**Verdict:** ' + _text(answer['verdict']), '', _text(answer['summary'])]
            if turn.get('error'):
                output += ['', '**Turn error:** ' + '; '.join(
                    f'{_text(key)}={_text(value)}' for key, value in turn['error'].items())]
        citations = envelope.get('claims', []) if view == 'evidence' else claims(record)
        for event in record.get('events', []):
            if event.get('phase') != 'completed':
                output += ['', '**Unresolved journal entry:** ' + _text(event['operation_key']) + '; phase '
                           + _text(event['phase']) + '; effects remain unknown.']
        for claim in citations:
            output += ['', f'### Citation {_text(claim["citation"])} / round {_text(claim["round"])} / {_text(claim["participant"])}', '',
                       f'**Source:** {_text(claim["path"])}:{_text(claim["line"])}',
                       '**Support:** ' + _text(claim['support']) + (
                           ' (advisory host assessment)' if claim.get('assessments')
                           else ' (no host assessment recorded)'), '',
                       _text(claim['detail']), '',
                       _block('\n'.join(f'{row["line"]}: {row["text"]}' for row in claim['source']))]
            for assessment in claim.get('assessments', []):
                output += ['', '**Assessment:** ' + _text(assessment['decision']) + ': ' + _text(assessment['note'])]
        if not record.get('answers'):
            output += ['', 'No retained participant turns.']
        if not citations:
            output += ['', 'No retained citations.']
    return '\n'.join(output) + '\n'
