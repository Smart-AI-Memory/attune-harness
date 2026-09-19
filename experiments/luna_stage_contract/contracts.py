"""Disposable stage contracts; validation never authorizes memory writes."""

import json

from jsonschema import Draft202012Validator


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


TEXT = obj({'text': {'type': 'string'}})
INSPECT = obj({'actions': {'type': 'array', 'maxItems': 3, 'items': obj({
    'tool': {'type': 'string', 'enum': ['read']}, 'source_id': {'type': 'string'},
})}})
ANSWER = obj({
    'decision': {'type': 'string', 'enum': ['update', 'no_change', 'insufficient']},
    'memory': {'type': 'string'},
    'source_ids': {'type': 'array', 'maxItems': 4, 'items': {'type': 'string'}},
})


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Non-JSON number: ' + value)


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)


def stage_schema(stage):
    if stage not in ('inspect', 'answer'):
        raise ValueError('Unknown stage')
    return INSPECT if stage == 'inspect' else ANSWER


def assess(raw, arm, case):
    """Separate shape and fixture invariants; answer prose still needs grading."""
    value = parse(raw)
    if arm == 'text':
        Draft202012Validator(TEXT).validate(value)
        value = parse(value['text'])
    elif arm != 'stage':
        raise ValueError('Unknown arm')
    Draft202012Validator(stage_schema(case['stage'])).validate(value)
    source_ids = {source['id'] for source in case['input']['sources']}
    if case['stage'] == 'inspect':
        requested = [action['source_id'] for action in value['actions']]
        admissible = set(requested) <= source_ids and len(requested) == len(set(requested))
        useful = set(case['expected']['required_reads']) <= set(requested)
        correct = admissible and useful
    else:
        cited = value['source_ids']
        admissible = set(cited) <= source_ids and len(cited) == len(set(cited))
        correct = (admissible and value['decision'] == case['expected']['decision']
                   and set(case['expected']['required_sources']) <= set(cited)
                   and (bool(value['memory'].strip()) if value['decision'] == 'update'
                        else value['memory'] == ''))
    return {'shape_valid': True, 'mechanical_case_pass': correct, 'payload': value,
            'prose_grade': 'required' if case['stage'] == 'answer' else 'not_applicable'}


def select_message(stdout):
    """Accept one distinct final payload; count all usage, never retry ambiguity."""
    events = [parse(line) for line in stdout.splitlines() if line.strip()]
    terminals = [event for event in events if event.get('type') == 'turn.completed']
    if len(terminals) != 1 or any(event.get('type') in ('turn.failed', 'error') for event in events):
        raise ValueError('Missing, failed or ambiguous terminal event')
    if events[-1].get('type') != 'turn.completed':
        raise ValueError('Events after terminal completion')
    usage = terminals[0].get('usage', {})
    for key in ('input_tokens', 'output_tokens'):
        if type(usage.get(key)) is not int or usage[key] < 0:
            raise ValueError('Missing token usage')
    messages, warnings = [], []
    for event in events:
        if not event.get('type', '').startswith('item.'):
            continue
        item = event.get('item', {})
        kind = item.get('type')
        if kind not in ('agent_message', 'reasoning', 'error'):
            raise ValueError('Unexpected native tool/event: ' + str(kind))
        if event['type'] == 'item.completed' and kind == 'error':
            message = item.get('message', '')
            known = ('Under-development features enabled:',
                     'Code Mode is unavailable because code-mode host is disabled.',
                     'Exceeded skills context budget.')
            if not isinstance(message, str) or not message.startswith(known):
                raise ValueError('Unexpected native error item')
            warnings.append(message)
        if event['type'] == 'item.completed' and kind == 'agent_message':
            messages.append(item['text'])
    if not messages:
        raise ValueError('Missing model message')
    canonical = set()
    for message in messages:
        try:
            canonical.add(json.dumps(parse(message), sort_keys=True))
        except ValueError:
            canonical.add(message)
    if len(canonical) != 1:
        raise ValueError('Ambiguous distinct model messages')
    return messages[-1], usage, warnings, len(messages)
