"""Evidence-bound, operator-selected consultation retries; no dispatch authority."""

import copy
import re

from .recovery import validate_events
from .review_contract import fields

PROVENANCE = {
    'not_launched': 'Process launch raised before a process existed; retry authorized by the operator',
    'cli_refusal': 'CLI structured error result with no reported model usage; '
                   'retry authorized by the operator, and usage may repeat',
}


def retry_basis(error, process, adapter):
    """Use process/structured evidence only, never diagnostic text or an exit alone."""
    if (not isinstance(error, dict) or not isinstance(process, dict)
            or 'returncode' not in process):
        return None
    if (process.get('failure') in ('not_found', 'launch_failed')
            and error.get('failure') == process['failure'] and process.get('returncode') is None):
        return 'not_launched'
    refusal = error.get('refusal')
    if (adapter == 'claude' and isinstance(refusal, dict)
            and process.get('failure') in (None, 'nonzero_exit')
            and error.get('failure') == 'nonzero_exit'
            and refusal.get('kind') == 'claude_structured_error'
            and refusal.get('model_usage') == {} and isinstance(refusal.get('result'), str)
            and type(refusal.get('returncode')) is int
            and type(process['returncode']) is int
            and refusal['returncode'] == process.get('returncode')):
        return 'cli_refusal'
    return None


def _basis(record, event):
    result = event.get('result')
    if not isinstance(result, dict) or result.get('status') != 'failed':
        return None
    try:
        round_number, participant = event['operation_key'].split(':')
        seat = record['contract']['configuration']['participants'][participant]
        int(round_number)
    except (ValueError, KeyError):
        return None
    error = result.get('error')
    basis = retry_basis(error, result.get('process'), seat['adapter'])
    return basis if basis and error.get('retry_basis') == basis else None


def validate_history(record):
    history = record['recovery'].get('reconciliations', [])
    if not isinstance(history, list) or len(history) > record['contract']['budget']['max_calls']:
        raise ValueError('Invalid consultation reconciliation history')
    events = {event['event_id']: event for event in record['events']}
    seen = set()
    for item in history:
        fields(item, ('event_id', 'checkpoint', 'previous', 'evidence'))
        previous, evidence = item['previous'], item['evidence']
        if (not isinstance(previous, dict) or not isinstance(evidence, dict)
                or not isinstance(item['checkpoint'], str)
                or re.fullmatch('[0-9a-f]{64}', item['checkpoint']) is None
                or item['event_id'] in seen or item['event_id'] not in events):
            raise ValueError('Invalid consultation reconciliation history')
        seen.add(item['event_id'])
        current = events[item['event_id']]
        if (previous.get('attempts') != 1 or current['attempts'] != 2
                or previous.get('phase') != 'completed' or previous.get('state') != 'completed'
                or any(previous.get(key) != current.get(key) for key in
                       ('event_id', 'operation_key', 'kind', 'effect_class', 'request_digest'))):
            raise ValueError('Invalid consultation prior attempt')
        validate_events({**record, 'events': [previous]}, kinds=('consultation_turn',))
        basis = _basis(record, previous)
        if not basis or evidence != {'kind': 'consultation_refusal_retry', 'retry_basis': basis,
                                      'provenance': PROVENANCE[basis]}:
            raise ValueError('Invalid consultation retry evidence')
    if any(event['attempts'] == 2 and event['event_id'] not in seen for event in record['events']):
        raise ValueError('Consultation retry omitted its prior attempt')


def reconcile_turn(record, store, checkpoint, round_number, participant, *, retry_refused=False):
    if checkpoint != record['checkpoint_digest']:
        raise ValueError('Stale checkpoint; inspect the current consultation')
    if retry_refused is not True:
        raise ValueError('Choose explicit --retry-refused')
    config = record['contract']['configuration']
    if (type(round_number) is not int or not 0 <= round_number < config['rounds']
            or not isinstance(participant, str) or participant not in config['participants']):
        raise ValueError('Unknown consultation turn')
    if record['status'] not in ('partial', 'failed'):
        raise ValueError('Only a stopped partial or failed consultation can reopen a turn')
    key = f'{round_number}:{participant}'
    event = next((item for item in record['events'] if item['operation_key'] == key), None)
    if event is None or (event['phase'], event['state']) != ('completed', 'completed'):
        raise ValueError('Turn is not a completed failed result')
    basis = _basis(record, event)
    if basis is None:
        raise ValueError('Unknown external effects cannot be retried without saved refusal evidence')
    if event['attempts'] >= 2:
        raise ValueError('Refused-turn retry limit exhausted')
    # The stopped round follows only complete rounds and precedes all undispatched rounds.
    for number in range(config['rounds']):
        for name in config['participants']:
            other = next((e for e in record['events'] if e['operation_key'] == f'{number}:{name}'), None)
            if ((number < round_number and (other is None or other.get('result', {}).get('status') != 'completed'))
                    or (number > round_number and other is not None)):
                raise ValueError('Selected turn is not in the stopped round')
    previous = copy.deepcopy(event)
    event.update(state='pending', phase='prepared', attempts=2)
    for name in ('result', 'error', 'effects', 'runtime_origin'):
        event.pop(name, None)
    record['answers'] = [answer for answer in record['answers']
                         if (answer['round'], answer['participant']) != (round_number, participant)]
    record['recovery'].setdefault('reconciliations', []).append({
        'event_id': event['event_id'], 'checkpoint': checkpoint, 'previous': previous,
        'evidence': {'kind': 'consultation_refusal_retry', 'retry_basis': basis, 'provenance': PROVENANCE[basis]},
    })
    record['status'] = 'paused'
    from .consultation import validate_record
    from .review_store import checkpoint_digest
    record['checkpoint_digest'] = checkpoint_digest(record)
    validate_record(record, store.directory)
    store.save(record)
    return record
