"""Deterministic triage and complete-chain economics; neither dispatches agents."""

import math
import re

from .review_contract import bounded_text, digest, fields, versioned


def count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + ' must be a nonnegative integer')
    return value


def amount(value, name):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be null or nonnegative and finite')
    return value


def triage(event, *, handled_keys=(), max_attempts=2):
    """Return a suggestion; callers must atomically claim its key before dispatch.

    One key spans reruns of the same check at the same revision. A model's log
    interpretation cannot change the trusted check status or authorize a retry.
    """
    fields(event, ('repository', 'revision', 'check', 'run_id', 'status',
                   'failure_kind', 'effects', 'attempts'))
    for key in ('repository', 'revision', 'check', 'run_id'):
        bounded_text(event[key], key)
    for key, choices in (
        ('status', ('pending', 'passed', 'failed', 'cancelled', 'unknown')),
        ('failure_kind', ('test', 'infrastructure', 'unknown')),
        ('effects', ('none', 'unknown')),
    ):
        if event[key] not in choices:
            raise ValueError('Invalid ' + key)
    count(event['attempts'], 'attempts')
    if not 1 <= count(max_attempts, 'max_attempts') <= 10:
        raise ValueError('max_attempts must be 1..10')
    if not isinstance(handled_keys, (tuple, list, set)) or any(
            not isinstance(k, str) or not re.fullmatch('[0-9a-f]{64}', k) for k in handled_keys):
        raise ValueError('handled_keys must contain digests')
    key = digest({k: event[k] for k in ('repository', 'revision', 'check')})
    status = event['status']
    if event['effects'] == 'unknown':
        action, reason = 'reconcile', 'Prior effects are unresolved; do not repeat work.'
    elif status == 'passed':
        action, reason = 'observe', 'The named check passed; this alone does not verify a repair.'
    elif status == 'pending':
        action, reason = 'wait', 'The check has no terminal result.'
    elif status in ('cancelled', 'unknown'):
        action, reason = 'human_review', 'No trustworthy failure classification is available.'
    elif key in handled_keys:
        action, reason = 'duplicate', 'This revision/check has already been handled.'
    elif event['attempts'] >= max_attempts:
        action, reason = 'human_review', 'The configured repair-attempt limit is exhausted.'
    elif event['failure_kind'] == 'test':
        action, reason = 'propose_repair_team', 'Diagnose code, tests and specification before proposing a repair.'
    elif event['failure_kind'] == 'infrastructure':
        action, reason = 'propose_infrastructure_review', 'Investigate the runner or service failure.'
    else:
        action, reason = 'human_review', 'Failure cause is unknown.'
    return {'schema_version': 1, 'key': key, 'action': action, 'reason': reason,
            'dispatch_authorized': False, 'atomic_claim_required': True}


def repair_economics(ledger):
    """Account for every attempt in a strategy, including failures and escalation.

    USD amounts must come from operator/provider accounting. Missing price or
    human-time evidence prevents economic ranking. Fixture ledgers remain fixtures.
    """
    fields(ledger, ('schema_version', 'scope', 'quality_floor', 'attempts'))
    versioned(ledger)
    if ledger['scope'] not in ('synthetic', 'real'):
        raise ValueError('scope must be synthetic or real')
    floor = ledger['quality_floor']
    fields(floor, ('minimum_verified_repairs', 'max_critical_misses', 'max_unsupported_assertions'))
    for key, value in floor.items():
        count(value, key)
    if floor['minimum_verified_repairs'] < 1:
        raise ValueError('At least one verified repair is required')
    attempts = ledger['attempts']
    if not isinstance(attempts, list) or not attempts:
        raise ValueError('attempts must be a nonempty list')
    seen, repair_strategies, groups, finalized = set(), {}, {}, set()
    for attempt in attempts:
        fields(attempt, ('attempt_id', 'repair_id', 'strategy', 'model', 'stage', 'outcome',
                         'verification', 'input_tokens', 'output_tokens', 'reasoning_output_tokens',
                         'model_cost_usd', 'verification_cost_usd', 'human_minutes', 'human_hourly_usd',
                         'critical_misses', 'unsupported_assertions'))
        for key in ('attempt_id', 'repair_id', 'strategy', 'model'):
            bounded_text(attempt[key], key)
        if attempt['attempt_id'] in seen:
            raise ValueError('Duplicate attempt_id')
        seen.add(attempt['attempt_id'])
        repair = attempt['repair_id']
        if repair in finalized:
            raise ValueError('A verified repair cannot receive another attempt')
        if attempt['stage'] not in ('initial', 'retry', 'escalation'):
            raise ValueError('Invalid attempt stage')
        if (repair not in repair_strategies) != (attempt['stage'] == 'initial'):
            raise ValueError('Each repair starts with exactly one initial attempt')
        if repair_strategies.setdefault(repair, attempt['strategy']) != attempt['strategy']:
            raise ValueError('Escalation costs cannot move to a different strategy')
        if attempt['outcome'] not in ('failed', 'unverified', 'verified'):
            raise ValueError('Invalid outcome')
        check = attempt['verification']
        fields(check, ('independent', 'passed', 'evidence_sha256'))
        if type(check['independent']) is not bool or type(check['passed']) is not bool:
            raise ValueError('Verification flags must be booleans')
        if check['evidence_sha256'] is not None and (
                not isinstance(check['evidence_sha256'], str) or
                not re.fullmatch('[0-9a-f]{64}', check['evidence_sha256'])):
            raise ValueError('Invalid verification evidence digest')
        if attempt['outcome'] == 'verified' and not (
                check['independent'] and check['passed'] and check['evidence_sha256']):
            raise ValueError('Verified repair requires independent passing evidence')
        if attempt['outcome'] == 'verified':
            finalized.add(repair)
        for key in ('input_tokens', 'output_tokens', 'reasoning_output_tokens'):
            if attempt[key] is not None:
                count(attempt[key], key)
        if (attempt['output_tokens'] is not None and attempt['reasoning_output_tokens'] is not None
                and attempt['reasoning_output_tokens'] > attempt['output_tokens']):
            raise ValueError('Reasoning tokens cannot exceed total output tokens')
        for key in ('model_cost_usd', 'verification_cost_usd', 'human_minutes', 'human_hourly_usd'):
            amount(attempt[key], key)
        for key in ('critical_misses', 'unsupported_assertions'):
            count(attempt[key], key)
        groups.setdefault(attempt['strategy'], []).append(attempt)
    summary = []
    for strategy, rows in groups.items():
        verified = len({r['repair_id'] for r in rows if r['outcome'] == 'verified'})
        misses = sum(r['critical_misses'] for r in rows)
        unsupported = sum(r['unsupported_assertions'] for r in rows)
        quality = (verified >= floor['minimum_verified_repairs'] and
                   misses <= floor['max_critical_misses'] and
                   unsupported <= floor['max_unsupported_assertions'])
        missing = [r['attempt_id'] + ':' + k for r in rows
                   for k in ('model_cost_usd', 'verification_cost_usd', 'human_minutes', 'human_hourly_usd')
                   if r[k] is None]
        total = None if missing else sum(r['model_cost_usd'] + r['verification_cost_usd'] +
                                        r['human_minutes'] * r['human_hourly_usd'] / 60 for r in rows)
        amount(total, 'total cost')
        tokens = {k: None if any(r[k] is None for r in rows) else sum(r[k] for r in rows)
                  for k in ('input_tokens', 'output_tokens', 'reasoning_output_tokens')}
        summary.append({'strategy': strategy, 'attempts': len(rows), 'verified_repairs': verified,
                        'critical_misses': misses, 'unsupported_assertions': unsupported,
                        'quality_passed': quality, 'cost_complete': not missing,
                        'missing_cost_evidence': missing, 'total_cost_usd': total,
                        'cost_per_verified_repair_usd': total / verified if total is not None and verified else None,
                        **tokens})
    eligible = [r for r in summary if r['quality_passed'] and r['cost_complete']]
    return {'schema_version': 1, 'scope': ledger['scope'], 'strategies': summary,
            'eligible_cost_ranking': [r['strategy'] for r in sorted(
                eligible, key=lambda r: (r['cost_per_verified_repair_usd'], r['strategy']))],
            'note': 'Ranking covers only quality-passing strategies with complete recorded costs; '
                    'ledger attestations are not authentication. Reasoning is already in output tokens.'}
