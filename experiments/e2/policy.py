"""DISPOSABLE E2 policies. No production availability cache or authorization API."""
import argparse
import hashlib
import json
from pathlib import Path

TOOL = 'evidence.search'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def valid_observation(observation):
    """Validate the recorded call against its original descriptor, never the oracle."""
    if not isinstance(observation, dict) or set(observation) != {'descriptor', 'result', 'digest'}:
        return False
    if fingerprint({key: observation[key] for key in ('descriptor', 'result')}) != observation['digest']:
        return False
    try:
        descriptor, result = observation['descriptor'], observation['result']
        extension = result['extension']
        return (result['operation'] == 'retrieve' and result['status'] == 'retrieved'
                and result['dependency'] == {'name': 'attune-rag', 'version': descriptor['dependencies']['attune-rag']}
                and result['query'] == descriptor['arguments']['query'] and result['k'] == descriptor['arguments']['k']
                and extension['tool'] == descriptor['tool'] and extension['artifact_digest'] == descriptor['artifact']['digest']
                and extension['version'] == descriptor['artifact']['version']
                and result['corpus']['root'] == descriptor['corpus_root'] and bool(result['sources'])
                and all(source['sha256'] == descriptor['sources'][source['path']] for source in result['sources']))
    except (KeyError, TypeError):
        return False


def decide(condition, current, observation):
    def answer(status, predict, reason, verified=False):
        return {'status': status, 'predicted_usable': predict, 'verified_availability_claim': verified,
                'reason': reason, 'descriptor_digest': fingerprint(current)}
    if condition == 'declaration-only':
        declared = TOOL in current['declared_tools']
        return answer('declared' if declared else 'not_declared', declared,
                      'Hypothetical usability inference from manifest only; existing Harness does not verify declarations')
    if condition != 'version-bound-cache':
        raise ValueError('Unknown E2 policy')
    if current['lifecycle'] != 'enabled':
        return answer('denied', False, 'Extension is not enabled')
    if TOOL not in current['grants']:
        return answer('denied', False, 'Selected participant lacks the target grant')
    if any(current['dependencies'].get(name) != version for name, version in current['required_dependencies'].items()):
        return answer('unavailable', False, 'Required dependency is absent or incompatible')
    if not valid_observation(observation):
        return answer('needs_probe', False, 'No matching validated successful observation')
    if fingerprint(observation['descriptor']) != fingerprint(current):
        return answer('needs_probe', False, 'Version or scope changed since the successful observation')
    return answer('verified_available', True, 'Candidate promotion of a matching historical successful call', True)


def score(decision, usable):
    return {'false_usable_prediction': decision['predicted_usable'] and not usable,
            'false_verified_availability_claim': decision['verified_availability_claim'] and not usable,
            'unnecessary_rejection': usable and decision['status'] in ('denied', 'unavailable', 'not_declared'),
            'deferred_usable_case': usable and decision['status'] == 'needs_probe'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition', required=True)
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--observation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = decide(args.condition, json.loads(args.descriptor.read_text(encoding='utf-8')),
                    json.loads(args.observation.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
