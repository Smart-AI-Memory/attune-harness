"""Accepted coding-agent retrieval intake without a synthetic review document."""

from pathlib import Path

from .features import read_text
from .review_contract import bounded_text, digest, fields, parse_json, versioned
from .voyage_index import load_selection, selection
from .voyage_sources import identifier


def task_template(cfg, generation, objective, participant='coding-agent', max_calls=8):
    bounded_text(objective, 'objective')
    identifier(participant, 'participant')
    if type(max_calls) is not int or not 1 <= max_calls <= 8:
        raise ValueError('max_calls must be an integer in 1..8')
    return {'schema_version': 1, 'kind': 'retrieval-task', 'accepted': False, 'objective': objective,
            'retrieval': selection(cfg, generation),
            'participants': {participant: {'tools': ['retrieve'], 'max_tool_calls': max_calls}}}


def prepare_task(path):
    value = parse_json(read_text(path, 131072))
    fields(value, ('schema_version', 'kind', 'accepted', 'objective', 'retrieval', 'participants'))
    versioned(value)
    if value['kind'] != 'retrieval-task' or value['accepted'] is not True:
        raise ValueError('Coding retrieval task must be explicitly accepted')
    bounded_text(value['objective'], 'objective')
    load_selection(value['retrieval'])
    roster = value['participants']
    if not isinstance(roster, dict) or not 1 <= len(roster) <= 16:
        raise ValueError('Select 1..16 coding-agent principals')
    for name, item in roster.items():
        identifier(name, 'participant')
        fields(item, ('tools', 'max_tool_calls'))
        if item['tools'] != ['retrieve'] or type(item['max_tool_calls']) is not int or not 1 <= item['max_tool_calls'] <= 8:
            raise ValueError('Coding retrieval requires a retrieve grant and 1..8 calls')
    return {'accepted': {'submission': value}, 'registry': {'schema_version': 1, 'participants': roster,
             'retrieval': value['retrieval']}, 'requirement_revision': digest(value),
             'source_snapshot': {'generation': value['retrieval']['generation']}, 'originals': {}, 'paths': {},
             'retrieval': value['retrieval']}


def safe_stage_continuation(directory):
    """A durable completed paid stage may replay; unknown dispatch may not."""
    from .review_store import read_record
    from .voyage_provider import PaidStageUnresolved
    stages = directory / 'stages'
    if not (stages / 'record.json').is_file():
        raise PaidStageUnresolved('Provider stage ledger is missing; automatic continuation refused')
    ledger = read_record(stages)
    for identity in ledger['stages']:
        path = stages / identity
        if (path.is_symlink() or not (path / 'record.json').is_file() or
                read_record(path)['status'] not in ('completed', 'prepared')):
            raise PaidStageUnresolved('Provider stage has unknown billing; automatic continuation refused')
