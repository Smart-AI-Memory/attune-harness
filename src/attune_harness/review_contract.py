"""Headless review intake and explicit, locally trusted participant configuration."""

import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path

from .adapters import _unique_object
from .features import FeatureUnavailable, read_text, require_feature

FORMS_VERSION = '0.17.0'
TOOLS = ('retrieve', 'verify')


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def parse_json(raw: str, limit: int = 131_072):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > limit:
        raise ValueError('JSON exceeds byte limit or is not text')
    def invalid(value):
        raise ValueError(f'Non-finite JSON number: {value}')
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=invalid)


def fields(value, expected):
    expected = set(expected)
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f'Expected fields: {sorted(expected)}')


def versioned(value):
    if type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        raise ValueError('Requires integer schema_version 1')


def bounded_text(value, name, limit=4096):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > limit:
        raise ValueError(f'{name} must be nonempty text of at most {limit} bytes')
    return value


def load_registry(path: Path) -> dict:
    value = parse_json(read_text(path, 131_072))
    return validate_registry(value, path)


def validate_registry(value: dict, path: Path, *, minimum_participants: int = 2) -> dict:
    """Shared configuration checks; legacy callers retain the two-role minimum."""
    extended = isinstance(value, dict) and 'extensions' in value
    fields(value, ('schema_version', 'participants', *(['extensions'] if extended else []),
                   *(['retrieval'] if isinstance(value, dict) and 'retrieval' in value else [])))
    versioned(value)
    if 'retrieval' in value:
        from .voyage_index import load_selection
        load_selection(value['retrieval'])
    available_tools = set(TOOLS)
    if 'extensions' in value:
        from .extensions import catalog, validate_bindings
        validate_bindings(value['extensions'], path.absolute().parent)
        available_tools.update(catalog(value['extensions']))
    roster = value['participants']
    if not isinstance(roster, dict) or not minimum_participants <= len(roster) <= 16:
        raise ValueError(f'Registry requires {minimum_participants}–16 participants')
    for name, item in roster.items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name) or not isinstance(item, dict):
            raise ValueError('Invalid participant identity or configuration')
        adapter = item.get('adapter')
        if adapter not in ('deterministic', 'claude', 'codex', 'command'):
            raise FeatureUnavailable(f'Unsupported adapter for {name}: {adapter}')
        keys = {'adapter', 'tools', 'max_turns', 'max_tool_calls'}
        if adapter in ('claude', 'codex'):
            keys |= {'model', 'timeout'}
            bounded_text(item.get('model'), 'model', 200)
        if adapter == 'codex' and 'reasoning_effort' in item:
            from .native import validate_reasoning_effort
            keys.add('reasoning_effort')
            validate_reasoning_effort(item['reasoning_effort'])
        if adapter == 'codex' and 'skills_context_tokens' in item:
            from .native import validate_skills_context_tokens
            keys.add('skills_context_tokens')
            validate_skills_context_tokens(item['skills_context_tokens'])
        if adapter in ('claude', 'codex') and 'review_mode' in item:
            keys.add('review_mode')
            if item['review_mode'] != 'evidence':
                raise ValueError('Native review_mode must be evidence')
        if adapter == 'command':
            keys |= {'command', 'timeout'}
            command = item.get('command')
            if not isinstance(command, list) or not 1 <= len(command) <= 32:
                raise ValueError('command must be an argument list')
            for arg in command:
                bounded_text(arg, 'command argument')
        fields(item, keys)
        grants = item['tools']
        if (not isinstance(grants, list) or any(not isinstance(tool, str) or tool not in available_tools for tool in grants)
                or len(grants) != len(set(grants))):
            raise ValueError('tools must be a unique list of supported names')
        for key, low, high in (('max_turns', 1, 10), ('max_tool_calls', 0, 8)):
            if type(item[key]) is not int or not low <= item[key] <= high:
                raise ValueError(f'{key} must be an integer in {low}..{high}')
        if item.get('review_mode') == 'evidence' and (
                grants != ['retrieve', 'verify'] or item['max_turns'] < 3 or item['max_tool_calls'] < 2):
            raise ValueError('Evidence review requires retrieve then verify, three turns and two tool calls')
        if adapter != 'deterministic' and (type(item['timeout']) not in (int, float)
                                            or not 1 <= item['timeout'] <= 300):
            raise ValueError('timeout must be 1..300 seconds')
    return value


def review_form(registry: dict) -> dict:
    library = require_feature('attune-forms', 'attune_forms', FORMS_VERSION, 'review')
    definitions = [
        {'id': name, 'text': label, 'type': 'text_input', 'required': True}
        for name, label in (
            ('objective', 'What should this evidence review address?'),
            ('query', 'Search terms for supporting evidence'),
            ('document', 'Markdown document to review'),
            ('context', 'Trusted verification context manifest'),
            ('corpus', 'Local Markdown source directory'),
        )
    ]
    definitions += [
        {'id': role, 'text': role.title(), 'type': 'single_select',
         'options': sorted(registry['participants']), 'required': True}
        for role in ('lead', 'reviewer')
    ]
    definition = {'title': 'Bounded evidence review', 'fields': definitions}
    if 'retrieval' in registry:
        definition['title'] = 'Bounded evidence review with Voyage code embeddings and paid rerank-2.5'
        next(f for f in definitions if f['id'] == 'corpus')['text'] = 'Selected application repository root'
    form = library.form_from_dict(definition)
    return {'schema_version': 1, 'form_revision': digest({'form': definition, 'registry': registry}),
            'definition': definition, 'markdown': library.form_to_markdown(form),
            'submission': {'schema_version': 1, 'form_revision': digest({'form': definition, 'registry': registry}),
                           'accepted': False, 'answers': {item['id']: None for item in definitions}}}


def accept_request(path: Path, registry: dict) -> dict:
    value = parse_json(read_text(path, 131_072))
    fields(value, ('schema_version', 'form_revision', 'accepted', 'answers'))
    versioned(value)
    if value['accepted'] is not True:
        raise ValueError('Request has not been explicitly accepted')
    specification = review_form(registry)
    if value['form_revision'] != specification['form_revision']:
        raise ValueError('Stale form revision; regenerate the form for this registry')
    library = require_feature('attune-forms', 'attune_forms', FORMS_VERSION, 'review')
    form = library.form_from_dict(specification['definition'])
    answers = value['answers']
    fields(answers, (item['id'] for item in specification['definition']['fields']))
    response = library.collect_form_response(form, answers, template_id='harness-review-v1')
    for name, answer in response.responses.items():
        bounded_text(answer, name)
    if answers['lead'] == answers['reviewer']:
        raise ValueError('Lead and reviewer must be distinct participant identities')
    resolved = {name: str((path.resolve().parent / answers[name]).resolve())
                for name in ('document', 'context', 'corpus')}
    return {'submission': value, 'form_response': asdict(response), 'paths': resolved,
            'forms_version': FORMS_VERSION}
