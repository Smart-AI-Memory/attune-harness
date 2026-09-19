"""Task-bound citation schemas; all existing host controls remain authoritative."""
from copy import deepcopy
from jsonschema import Draft202012Validator, ValidationError
from baseline import old


def source_ids(bound):
    sources = bound.get('sources')
    if not isinstance(sources, list) or not 1 <= len(sources) <= 8:
        raise ValueError('Supported input requires one to eight supplied sources')
    ids = [s.get('id') if isinstance(s, dict) else None for s in sources]
    if any(not isinstance(id, str) or not id.strip() for id in ids) or len(set(ids)) != len(ids):
        raise ValueError('Supplied source IDs must be nonempty unique strings')
    return ids


def schema_for(bound, *, audit=False):
    ids = source_ids(bound)
    schema = deepcopy(old.AUDIT if audit else old.SCHEMA)
    references = dict(type='array', minItems=1, maxItems=8,
                      items=dict(type='string', enum=ids))
    schema['properties']['evidence_ids'] = {
        **deepcopy(references),
        'description': ('One or more unique supplied source IDs supporting the verdict and explanation.' if audit else
            'One or more unique supplied source IDs supporting the operation, disposition and explanation.') +
            ' Cite the supplied note describing an absent attachment, not the attachment filename. Membership is not proof of relevance.',
    }
    if not audit:
        schema['properties']['facts']['items']['properties']['source_ids'] = {
            **deepcopy(references),
            'description': 'One or more unique supplied source IDs supporting this fact. Preserve all required provenance and use sources of the same scope.',
        }
    return schema


def prompt(bound, handoff=None, *, audit_proposal=None):
    audit = audit_proposal is not None
    value = old.audit_prompt(bound, audit_proposal) if audit else old.prompt(bound, handoff)
    value['schema'] = schema_for(bound, audit=audit)
    value['citation_contract'] = (
        'evidence_ids is required and nonempty for every verdict. Use only unique IDs of sources actually '
        'supplied in this packet, supporting the verdict and explanation. For an absent attachment, cite '
        'the supplied note describing it; its filename may appear in reason but never as a source ID. '
        'Do not invent source content, guess citations, or treat a valid ID as proof.'
    ) if audit else (
        'evidence_ids is required and nonempty for every outcome, including no_change and all needs_* outcomes. '
        'Use only unique IDs of sources actually supplied in this packet. Choose sources supporting the operation, '
        'disposition and explanation, not just the surviving fact content. A forgetting or kind-change decision '
        'may require a different supporting source from the facts that remain. Fact source_ids separately support '
        'each proposed fact and must also be nonempty, unique and drawn from supplied source IDs. '
        'For absent evidence, cite the supplied note that establishes the absence and name the missing attachment '
        'in request. Its name may also appear in a truthful explanation, but never substitute it for a supplied '
        'source ID. Do not invent source content, guess citations, or treat a valid ID as proof.'
    )
    return value


def assess(bound, reply, current, arm):
    if arm == 'legacy':
        return old.assess(bound, reply, current)
    try:
        old.check_current(bound, current)
        Draft202012Validator(schema_for(bound)).validate(reply['value'])
        candidate = old.normalize(bound, reply['value'], current)
        return dict(accepted=True, response=reply['value'], candidate=candidate)
    except (ValueError, ValidationError, KeyError, TypeError) as error:
        return dict(accepted=False, response=reply.get('value'), error=str(error),
                    failure_kind='stale' if isinstance(error, old.StaleInput) else 'contract')


def execute(case, arm, call, current=None):
    if arm not in ('legacy', 'repaired'):
        raise ValueError('Unknown comparison arm')
    bound = old.capture(case)
    source_ids(bound)  # Same supported-input preflight for both arms.
    current = current or (lambda: case['input'])
    model = bound['grants']['assigned_model']
    if model not in ('luna', 'astra'):
        raise ValueError('Unknown host assignment')
    make_prompt = old.prompt if arm == 'legacy' else prompt
    schema = old.SCHEMA if arm == 'legacy' else schema_for(bound)
    first = assess(bound, call('worker', model, make_prompt(bound), schema), current(), arm)
    result = dict(binding=bound, initial_model=model, final_model=model, first=first, final=first,
                  action=old.action(first, model), escalated=False, audit=None)
    if result['action'] == 'escalate':
        final = assess(bound, call('escalation', 'astra', make_prompt(bound, first), schema), current(), arm)
        result.update(final=final, final_model='astra', action=old.action(final, 'astra'), escalated=True)
    return result


def audit(case, result, call, current=None):
    if not result['final']['accepted'] or result['action'] == 'stale_stop':
        return dict(state='skipped_invalid')
    bound = result['binding']
    current = current or (lambda: case['input'])
    try:
        old.check_current(bound, current())
        schema = schema_for(bound, audit=True)
        reply = call('audit', 'astra', prompt(bound, audit_proposal=result['final']['response']), schema)
        old.check_current(bound, current())
        value = reply['value']
        Draft202012Validator(schema).validate(value)
        old.refs(bound, value['evidence_ids'])
        if value['verdict'] != 'supported':
            result['action'] = 'quarantined'
        return dict(state='completed', response=value)
    except (ValueError, ValidationError, KeyError, TypeError) as error:
        result['action'] = 'stale_stop' if isinstance(error, old.StaleInput) else 'quarantined'
        return dict(state='rejected', error=str(error), response=reply.get('value') if 'reply' in locals() else None)
