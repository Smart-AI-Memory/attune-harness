"""Frozen collaboration orchestration, with no answer-key access."""
import copy
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

SCHEMA = {'type': 'object', 'properties': {
    'verdict': {'type': 'string', 'enum': ['ready', 'revise', 'blocked']},
    'findings': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 16},
    'uncertain': {'type': 'boolean'}, 'critical_risk': {'type': 'boolean'},
    'disagree': {'type': 'boolean'}, 'rationale': {'type': 'string', 'maxLength': 160}},
    'required': ['verdict', 'findings', 'uncertain', 'critical_risk', 'disagree', 'rationale'],
    'additionalProperties': False}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate(value):
    if not isinstance(value, dict) or set(value) != set(SCHEMA['required']):
        raise ValueError('Unexpected participant response fields')
    if value['verdict'] not in ('ready', 'revise', 'blocked'):
        raise ValueError('Invalid participant verdict')
    if any(type(value[k]) is not bool for k in ('uncertain', 'critical_risk', 'disagree')):
        raise ValueError('Routing signals must be booleans')
    findings = value['findings']
    if (not isinstance(findings, list) or len(findings) > 16
            or any(not isinstance(f, str) or not f or len(f) > 100 for f in findings)
            or len(set(findings)) != len(findings)):
        raise ValueError('Findings must be bounded unique strings')
    if not isinstance(value['rationale'], str) or len(value['rationale']) > 160:
        raise ValueError('Rationale exceeds its bound')
    return copy.deepcopy(value)


def answer(value):
    return {'verdict': value['verdict'], 'findings': sorted(value['findings'])}


def orchestrate(strategy, call):
    if strategy not in ('solo', 'fixed-cross-review', 'fixed-roundtable', 'adaptive'):
        raise ValueError('Unknown collaboration strategy')
    draft = validate(call('draft', None, []))
    if strategy == 'solo' or (strategy == 'adaptive' and not draft['uncertain'] and not draft['critical_risk']):
        return answer(draft)
    reviews = [validate(call('review-1', copy.deepcopy(draft), []))]
    disagree = reviews[0]['disagree'] or answer(reviews[0]) != answer(draft)
    if strategy == 'fixed-roundtable' or (strategy == 'adaptive' and (draft['critical_risk'] or disagree)):
        reviews += [validate(call(stage, copy.deepcopy(draft), [])) for stage in ('review-2', 'review-3')]
    return answer(validate(call('final', copy.deepcopy(draft), copy.deepcopy(reviews))))


def execute(trial, directory, protocol):
    # Import only the installed dependency when invoked with python -I.
    import attune_harness
    from attune_harness import Task
    from attune_harness.adapters import Attempt, JsonParticipant
    from attune_harness.ollama import LocalJsonExchange, LocalModel, ModelPin, parse
    from attune_harness.review_store import RunStore
    store = RunStore(directory)
    model = LocalModel(ModelPin(protocol['model'], protocol['model_digest'], protocol['server_version']),
                       timeout=protocol['call_timeout_seconds'])
    record = {'schema_version': 1, 'operation': 'collaboration-experiment', 'kind': 'local-model',
        'trial': trial, 'protocol_revision': digest(protocol), 'status': 'running', 'calls': [],
        'output': None, 'harness_location': attune_harness.__file__, 'human_interventions': 0,
        'human_repair_seconds': None, 'paid_api_cost_usd': 0, 'uncertain_generation': False}
    started_trial = time.monotonic()
    with store.lease():
        store.save(record)
        def call(stage, draft, reviews):
            if len(record['calls']) >= protocol['max_calls_per_trial']:
                raise ValueError('Trial exhausted its frozen call budget')
            instruction = protocol['stage_instructions']['review' if stage.startswith('review-') else stage]
            body = {'instruction': instruction, 'task': trial['input']['prompt']}
            if draft is not None:
                body['initial_draft'] = draft
            if stage == 'final':
                body['independent_reviews'] = reviews
            seed = protocol['repeat_seeds'][trial['repeat']] + protocol['stage_seed_offsets'][stage]
            task = Task(trial['trial_id'], json.dumps(body, sort_keys=True), ('Respond to the supplied task in the required JSON schema.',))
            attempt = Attempt(task, str(uuid4()), trial['task_revision'],
                stage if stage.startswith('review-') else 'lead', 'reviewer' if stage.startswith('review-') else 'lead', 'ollama-local-v1')
            exchange = LocalJsonExchange(model, system=protocol['system_prompt'], schema=SCHEMA, seed=seed, options=protocol['settings'])
            entry = {'stage': stage, 'seed': seed, 'wire_request': attempt.request(),
                     'state': 'dispatching', 'response': None, 'usage': None}
            record['calls'].append(entry)
            store.save(record)  # Before the generation dispatch; no automatic resume.
            started = time.monotonic()
            try:
                output = JsonParticipant(attempt, exchange).run(task)
                value = validate(parse(output.text))
                entry.update(state='completed', response=value)
                return value
            except Exception as exc:
                entry.update(state='failed', error={'type': type(exc).__name__, 'detail': str(exc)})
                record['uncertain_generation'] = model.generation_attempted and model.last_response is None
                raise
            finally:
                entry['elapsed_seconds'] = time.monotonic() - started
                entry['raw_generation'] = model.last_response
                entry['generation_request'] = model.last_request
                if model.last_response is not None:
                    raw = model.last_response
                    entry['usage'] = {k: raw.get(k) for k in ('prompt_eval_count', 'eval_count', 'total_duration',
                        'load_duration', 'prompt_eval_duration', 'eval_duration')}
                store.save(record)
        try:
            record['output'] = orchestrate(trial['strategy'], call)
            record['status'] = 'completed'
        except Exception as exc:
            record.update(status='failed', error={'type': type(exc).__name__, 'detail': str(exc)})
        record['elapsed_seconds'] = time.monotonic() - started_trial
        store.save(record)
    return record
