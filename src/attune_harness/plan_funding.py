"""Private plan admission preparation and strict names-only v2 evidence."""

import hashlib
import re
import time

from .features import FeatureUnavailable


EXTRA = ('profile_id', 'generation', 'worker_profile', 'plan_wire_digest')


def prepare(config, raw):
    from .plan_exchange import runtime, body
    from .plan_worker import wire
    from .plan_profiles import store
    deadline = time.monotonic() + config['timeout']
    report = {'requested': 'subscription', 'observed': 'unknown', 'state': 'unsupported',
              'basis': 'plan_profile_refused', 'cli_version': None,
              'profile_id': config['funding']['profile_id'], 'generation': None,
              'worker_profile': None, 'plan_wire_digest': None}
    try:
        qualified = runtime()
        model = config.get('model') or config['identity']['model']
        effort = config.get('reasoning_effort')
        wire_digest = hashlib.sha256(wire(body(raw, model, effort))).hexdigest()
        profiles = store()
        resolved = profiles.resolve(report['profile_id'], deadline)
        context = {**qualified, 'store': profiles, 'deadline': deadline, 'effort': effort,
                   'profile_id': report['profile_id'], 'generation': resolved['generation']}
        report.update(observed='subscription', state='matched', basis='isolated_plan_request',
                      generation=resolved['generation'], worker_profile=qualified['worker_profile'],
                      plan_wire_digest=wire_digest)
        return report, {'ATTUNE_CHATGPT_ACCESS_TOKEN': resolved['token']}, context
    except Exception:
        return report, None, None


def validate(value, *, config=None, participant=None, attempt_id=None,
             attempt=None, request_digest=None):
    from .review_contract import fields, digest
    from .plan_profiles import profile_id
    fields(value, ('profile', 'requested', 'observed', 'state', 'basis', 'cli_version',
                   'api_authorized', 'dispatch_outcome', 'participant_id',
                   'configuration_digest', 'attempt_id', 'attempt', 'request_digest', *EXTRA))
    profile_id(value['profile_id'])
    if (value['profile'] != 'participant-funding-v2' or value['requested'] != 'subscription'
            or value['cli_version'] is not None or type(value['api_authorized']) is not bool
            or value['dispatch_outcome'] not in ('not_started', 'started', 'completed', 'unknown')
            or type(value['attempt']) is not int or not 1 <= value['attempt'] <= 2
            or any(not isinstance(value[k], str) or not 1 <= len(value[k]) <= 200
                   for k in ('participant_id', 'attempt_id'))
            or any(not isinstance(value[k], str) or re.fullmatch('[0-9a-f]{64}', value[k]) is None
                   for k in ('configuration_digest', 'request_digest'))):
        raise ValueError('Invalid plan funding evidence')
    if value['state'] == 'matched':
        if (value['observed'] != 'subscription' or value['basis'] != 'isolated_plan_request'
                or not isinstance(value['generation'], str)
                or re.fullmatch('[0-9a-f]{32}', value['generation']) is None
                or any(not isinstance(value[k], str) or re.fullmatch('[0-9a-f]{64}', value[k]) is None
                       for k in ('worker_profile', 'plan_wire_digest'))):
            raise ValueError('Invalid matched plan funding evidence')
    elif (value['state'] != 'unsupported' or value['observed'] != 'unknown'
          or value['basis'] != 'plan_profile_refused' or value['dispatch_outcome'] != 'not_started'
          or any(value[k] is not None for k in EXTRA[1:])):
        raise ValueError('Invalid refused plan funding evidence')
    expected = {'participant_id': participant, 'attempt_id': attempt_id, 'attempt': attempt,
                'request_digest': request_digest}
    if config is not None:
        if config['adapter'] != 'openai-plan':
            raise ValueError('Plan evidence requires the plan adapter')
        expected.update(configuration_digest=digest(config), profile_id=config['funding']['profile_id'])
    if any(value[k] != v for k, v in expected.items() if v is not None):
        raise ValueError('Plan evidence differs from its owner')
    return value


def context(issued):
    if issued['receipt']['profile'] != 'participant-funding-v2' or not issued.get('plan'):
        raise ValueError('Plan execution requires a plan admission')
    return dict(issued['plan'])


def verify_runtime(selected):
    from .plan_exchange import runtime
    observed = runtime()
    if any(observed[k] != selected[k] for k in ('ca_file', 'ca_sha256', 'worker_profile')):
        raise FeatureUnavailable('Plan runtime changed before dispatch')


def precheck_pending(pending, allow_api_spend, *, selected=None):
    """Check static mixed authority before resolving any selected sibling profile."""
    from .participant_funding import _environment, FundingPrecheckRefused
    selected = pending if selected is None else selected
    if not any(c['adapter'] == 'openai-plan' for c in selected.values()):
        return  # Preserve established API-only per-turn refusal evidence.
    api = [c for c in pending.values() if c['adapter'] == 'openai']
    if api and allow_api_spend is not True:
        raise FundingPrecheckRefused('api_authority_required')
    for config in api:
        try:
            _environment(config['funding']).clear()
        except ValueError:
            raise FundingPrecheckRefused('missing_credential') from None


def completed_model(event):
    return bool(event and event.get('kind') == 'participant_turn'
                and event.get('phase') == 'completed' and event.get('state') == 'completed')


def pending_assignments(selected, assignments, events):
    return {role: config for role, config in selected.items() if not any(
        completed_model(e) and e.get('participant_id') == assignments[role]['participant_id']
        and e.get('attempt_id') == assignments[role]['attempt_id']
        and e.get('result', {}).get('action', {}).get('kind') == 'final' for e in events)}
