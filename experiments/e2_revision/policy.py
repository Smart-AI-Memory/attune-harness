"""Disposable replacement: history is evidence, not current availability."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

TOOL = 'evidence.search'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def valid_result(descriptor, result):
    try:
        sources = result['sources']
        return (result['operation'] == 'retrieve' and result['status'] == 'retrieved'
            and result['dependency'] == {'name': 'attune-rag', 'version': descriptor['dependencies']['attune-rag']}
            and result['query'] == descriptor['arguments']['query']
            and type(result['k']) is int and result['k'] == descriptor['arguments']['k']
            and result['extension']['tool'] == descriptor['tool'] == TOOL
            and result['extension']['artifact_digest'] == descriptor['artifact']['digest']
            and result['extension']['version'] == descriptor['artifact']['version']
            and result['corpus']['root'] == descriptor['corpus_root']
            and isinstance(sources, list) and bool(sources)
            and len({source['path'] for source in sources}) == len(sources)
            and all(source['sha256'] == descriptor['sources'][source['path']] for source in sources))
    except (KeyError, TypeError):
        return False


def observation(descriptor, result):
    if not valid_result(descriptor, result):
        raise ValueError('Not a valid successful observation')
    value = copy.deepcopy({'descriptor': descriptor, 'result': result})
    return {**value, 'digest': fingerprint(value)}


def history_status(current, historical):
    if historical is None:
        return 'absent'
    try:
        if (set(historical) != {'descriptor', 'result', 'digest'}
                or historical['digest'] != fingerprint({k: historical[k] for k in ('descriptor', 'result')})
                or not valid_result(historical['descriptor'], historical['result'])):
            return 'invalid'
        return 'matching_success' if fingerprint(historical['descriptor']) == fingerprint(current) else 'stale'
    except (KeyError, TypeError, ValueError):
        return 'invalid'


def plan(current, historical, run_directory):
    """Permit an attempt from current guards; never predict that it will succeed."""
    if current['tool'] != TOOL or not Path(run_directory).is_absolute():
        raise ValueError('Unsupported tool profile or nonabsolute invocation directory')
    if current['lifecycle'] != 'enabled':
        status = 'denied'
    elif TOOL not in current['declared_tools'] or TOOL not in current['grants']:
        status = 'denied'
    elif any(current['dependencies'].get(name) != version for name, version in current['required_dependencies'].items()):
        status = 'unavailable'
    else:
        status = 'invoke'
    return {'status': status, 'invocation_allowed': status == 'invoke',
        'predicted_usable': False, 'verified_availability_claim': False, 'availability': 'unverified',
        'history_status': history_status(current, historical), 'descriptor_digest': fingerprint(current),
        'record_path': str(Path(run_directory) / 'record.json')}


def finish(decision, before, after, raw):
    """Consume this requested invocation's result; no separate availability probe."""
    def report(status, result=None):
        result = copy.deepcopy(result)
        return {'status': status, 'availability': 'unverified', 'verified_availability_claim': False,
            'descriptor_digest': decision['descriptor_digest'], 'record_path': decision['record_path'],
            'raw_digest': fingerprint(raw), 'result': result,
            'observation': observation(before, result) if result is not None else None}
    if not decision['invocation_allowed']:
        return report('not_invoked')
    if fingerprint(before) != decision['descriptor_digest'] or fingerprint(after) != decision['descriptor_digest']:
        return report('scope_changed')
    if raw.get('target_result') is None:
        return report('observed_failure')
    result = raw['target_result']
    try:
        record = raw['record']
        if record['record_path'] != decision['record_path'] or not valid_result(before, result):
            return report('invalid_evidence')
        if before['adapter'] == 'command-review':
            events = [event for event in record['events'] if event.get('kind') == 'tool'
                      and event.get('participant_id') == 'lead' and event.get('action', {}).get('name') == TOOL]
            arguments = events[0]['action']['arguments'] if len(events) == 1 else None
        elif before['adapter'] == 'mcp-stdio-2026-07-28':
            events = [event for event in record['events'] if event.get('tool') == 'harness.' + TOOL]
            arguments = events[0]['arguments'] if len(events) == 1 else None
            responses = [frame['result'] for frame in raw['frames'] if 'structuredContent' in frame.get('result', {})]
            if (len(responses) != 1 or responses[0]['structuredContent'] != result
                    or json.loads(responses[0]['content'][0]['text']) != result):
                return report('invalid_evidence')
        else:
            return report('invalid_evidence')
        if (len(events) != 1 or events[0]['state'] != 'completed' or events[0]['result'] != result
                or arguments != before['arguments']):
            return report('invalid_evidence')
    except (KeyError, TypeError, ValueError):
        return report('invalid_evidence')
    return report('observed_success', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'finish'))
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--history', type=Path)
    parser.add_argument('--run-directory', type=Path)
    parser.add_argument('--decision', type=Path)
    parser.add_argument('--after', type=Path)
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    if args.action == 'plan':
        result = plan(read(args.descriptor), read(args.history) if args.history else None, args.run_directory)
    else:
        result = finish(read(args.decision), read(args.descriptor), read(args.after), read(args.raw))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
