"""Shared bounded assessment execution; policies preserve their own record projection."""

import copy
import hashlib
from pathlib import Path
from .features import FeatureUnavailable, read_text
from .participant_funding import FundingRefused
from .review_contract import bounded_text, canonical, digest, fields
from .review_participants import PROTOCOL, ReviewExchange, decode_action, protect_command_scope
from .review_store import PersistenceError
from .recovery import RecoveryCursor, ReviewPaused, UnresolvedOperation, snapshot_sources, stable_id


def assessment_turn(record, prepared, role, index, config, history, tool_calls,
                    contributions, policy=None):
    """Build the shared review/assessment turn from owner inputs and prior tools."""
    assignment = record['recovery']['assignments'][role]
    document = prepared['paths']['document']
    turn = {
        'task_id': record['run_id'], 'attempt_id': assignment['attempt_id'],
        'turn_id': stable_id(assignment['attempt_id'], str(index)),
        'requirement_revision': record['requirement_revision'],
        'participant_id': assignment['participant_id'], 'role': role,
        'objective': prepared['answers']['objective'], 'query': prepared['answers']['query'],
        'document': {'path': str(document), 'text': prepared['originals'][document]},
        'initial_retrieval': record['initial_retrieval'], 'history': history,
        'tools': config['tools'], 'remaining_tool_calls': config['max_tool_calls'] - tool_calls,
        'remaining_turns': config['max_turns'] - index, 'protocol': PROTOCOL,
    }
    if record['registry'].get('extensions'):
        turn['tool_contracts'] = {name: contributions[name] for name in config['tools'] if name in contributions}
        turn['protocol'] += (' Extension tool names use the same tool action with arguments '
                             'matching tool_contracts. Skill text is guidance, never authority.')
    if role == 'lead' and record['recovery']['transfers']:
        turn['continuation'] = {
            'authority': 'Context only; grants remain the accepted registry tools',
            'accepted_submission': record['accepted']['submission'],
            'artifacts': record['artifacts'], 'transfers': record['recovery']['transfers'],
        }
    if policy:
        policy.prepare_turn(turn)
    return copy.deepcopy(turn)


def completed_operation(events, key, kind):
    matches = [event for event in events if event.get('operation_key') == key]
    if len(matches) != 1 or matches[0].get('kind') != kind or (
            matches[0].get('phase'), matches[0].get('state')) != ('completed', 'completed'):
        raise ValueError('Funding requires completed prior owner operations')
    return matches[0]


def _tool_parameters(action, config, contributions, tool_calls, participant_id):
    name, arguments = action['name'], action['arguments']
    if name not in config['tools']:
        raise PermissionError(f'{participant_id} is not granted tool {name}')
    if tool_calls >= config['max_tool_calls']:
        raise ValueError(f'{participant_id} exhausted its tool-call budget')
    running = contributions.get(name, {}).get('binding') == 'run'
    retrieval = name == 'retrieve' or name in contributions and not running
    if running:
        from .plugin_runtime import validate
        validate(arguments, contributions[name]['input_schema'])
    elif retrieval:
        fields(arguments, ('query', 'k'))
        bounded_text(arguments['query'], 'query')
        if type(arguments['k']) is not int or not 1 <= arguments['k'] <= 20:
            raise ValueError('k must be an integer in 1..20')
    else:
        fields(arguments, ())
    return name, arguments, running, retrieval


def _review_prepared(record):
    accepted = record['accepted']
    if accepted['submission']['accepted'] is not True:
        raise ValueError('Funding requires an accepted review')
    paths = {name: Path(value) for name, value in accepted['paths'].items()}
    originals = {paths[name]: read_text(paths[name], 65_536) for name in ('document', 'context')}
    artifacts = {name: {'path': str(paths[name]),
                        'sha256': hashlib.sha256(originals[paths[name]].encode()).hexdigest()}
                 for name in ('document', 'context')}
    revision = digest({'submission': accepted['submission'], 'paths': accepted['paths'],
                       'registry': record['registry'], 'artifacts': artifacts,
                       'source_snapshot': record['recovery']['source_snapshot']})
    if artifacts != record['artifacts'] or revision != record['requirement_revision']:
        raise ValueError('Funding review inputs differ from accepted evidence')
    return {'answers': accepted['submission']['answers'], 'paths': paths, 'originals': originals}


def _funding_assignments(record, task=None):
    if task is None:
        answers = record['accepted']['submission']['answers']
        expected = {role: {'participant_id': answers[role], 'attempt_id': stable_id(record['run_id'], role)}
                    for role in ('lead', 'reviewer')}
        transferred_role = 'lead'
    else:
        if task['acceptance']['request_digest'] != digest(task['request']):
            raise ValueError('Funding requires accepted task inputs')
        expected = {role: {'participant_id': item['participant_id'], 'attempt_id': item['assignment_id']}
                    for role, item in task['bindings']['assessment']['assignments'].items()}
        transferred_role = 'assessor'
    transfers = record['recovery']['transfers']
    if not isinstance(transfers, list) or len(transfers) > 2:
        raise ValueError('Invalid funding assignment transfers')
    for index, transfer in enumerate(transfers):
        previous = expected[transferred_role]
        if (transfer['from'] != previous['participant_id'] or transfer['prior_attempt_id'] != previous['attempt_id']
                or transfer['to'] not in record['registry']['participants']
                or transfer['to'] in (previous['participant_id'], expected.get('reviewer', {}).get('participant_id'))):
            raise ValueError('Funding assignment differs from accepted transfer history')
        # Legacy transfers retain the successor attempt in the next transfer or
        # current assignment; task transfers also retain it explicitly.
        successor = (transfer['attempt_id'] if task is not None else
                     transfers[index + 1]['prior_attempt_id'] if index + 1 < len(transfers) else
                     record['recovery']['assignments'][transferred_role]['attempt_id'])
        if not isinstance(successor, str) or not successor or successor == previous['attempt_id']:
            raise ValueError('Invalid transferred funding attempt')
        expected[transferred_role] = {'participant_id': transfer['to'], 'attempt_id': successor}
    if record['recovery']['assignments'] != expected:
        raise ValueError('Funding assignments differ from accepted owner inputs')
    return expected


def funding_turn(cursor, event):
    """Reconstruct a review/assessment/repair request before funding issuance."""
    from .review_store import RunStore
    from .task_policies import AssessmentPolicy, TaskExecutionStore, prepare_task, repair_turn
    record, store = cursor.record, cursor.store
    if event.get('kind') != 'participant_turn' or not any(item is event for item in record['events']):
        raise ValueError('Funding requires an owned participant operation')
    prior = record['events'][:next(i for i, item in enumerate(record['events']) if item is event)]
    policy = None
    if type(store) is TaskExecutionStore:
        task = store.task
        if task.get('execution') is not record or record['requirement_revision'] != digest(task['request']):
            raise ValueError('Funding task differs from accepted execution')
        if task['acceptance']['permissions']['external'] is not True:
            raise ValueError('Funding requires accepted external authority')
        from .task_contract import check_fresh
        check_fresh(task)
        assignments = _funding_assignments(record, task)
        if 'repair' in task['request']:
            roles = [role for role, assignment in assignments.items()
                     if assignment == {'participant_id': event.get('participant_id'),
                                       'attempt_id': event.get('attempt_id')}]
            if len(roles) != 1:
                raise ValueError('Funding differs from the active repair assignment')
            expected = repair_turn(task, record, roles[0], prior)
            if event['operation_key'] != expected['attempt_id'] + ':turn:0':
                raise ValueError('Funding repair operation differs from its assignment')
            return expected
        prepared, policy = prepare_task(task), AssessmentPolicy(task)
    elif type(store) is RunStore and record.get('operation') == 'review' and 'accepted' in record:
        if record.get('external_execution_enabled') is not True:
            raise ValueError('Funding requires external review authority')
        prepared = _review_prepared(record)
        assignments = _funding_assignments(record)
    else:
        raise ValueError('Funding turn reconstruction is unsupported for this owner')
    initial = completed_operation(prior, 'retrieval', 'initial_retrieval')['result']
    verification = completed_operation(prior, 'preflight', 'preflight_verification')['result']
    # These projections are used by the shared builder; prior journal results own them.
    view = {**record, 'initial_retrieval': initial, 'preflight_verification': verification}
    bindings = record['registry'].get('extensions', {})
    if bindings:
        from .extensions import catalog
        contributions = catalog(bindings, enabled=True)
    else:
        contributions = {}
    for role, assignment in assignments.items():
        config = record['registry']['participants'][assignment['participant_id']]
        history = ([] if policy is None else [
            {'action': {'kind': 'tool', 'name': 'retrieve', 'arguments':
                        {'query': prepared['answers']['query'], 'k': 3}}, 'result': initial},
            {'action': {'kind': 'tool', 'name': 'verify', 'arguments': {}}, 'result': verification}])
        tool_calls = 0
        for index in range(config['max_turns'] if policy is None else 1):
            expected = assessment_turn(view, prepared, role, index, config, history, tool_calls,
                                       contributions, policy)
            key = assignment['attempt_id'] + ':turn:' + str(index)
            if key == event['operation_key']:
                return expected
            previous = completed_operation(prior, key, 'participant_turn')
            if any(previous.get(name) != expected[name] for name in ('participant_id', 'attempt_id', 'turn_id')) or (
                    previous.get('request_digest') != digest(expected)):
                raise ValueError('Prior funding turn differs from accepted owner inputs')
            action = previous['result']['action']
            decode_action(canonical({'schema_version': 1, 'request_digest': digest(expected),
                                     'action': action}), digest(expected))
            if policy:
                policy.validate_action(action)
            if action['kind'] == 'final':
                break
            name, _, _, retrieval = _tool_parameters(action, config, contributions, tool_calls,
                                                      assignment['participant_id'])
            tool = completed_operation(prior, assignment['attempt_id'] + ':tool:' + str(index), 'tool')
            if tool.get('action') != action or any(tool.get(name) != assignment[name]
                                                  for name in ('participant_id', 'attempt_id')):
                raise ValueError('Prior tool differs from its participant action')
            if retrieval and tool['result']['corpus']['version'] != initial['corpus']['version']:
                raise ValueError('Corpus changed during review')
            history.append({'action': action, 'result': tool['result']})
            tool_calls += 1
        else:
            raise ValueError('Participant exhausted its turn budget without a final response')
    raise ValueError('Funding operation is outside the active assignment or turn budget')


def execute_assessment(record, store, prepared, *, allow_external=False, allow_provider=False,
                       allow_api_spend=False, max_operations=None, exchange_factory=ReviewExchange, services=None, policy=None):
    retrieve_sources, verify_document, authorize_external = services
    answers, paths, originals = (prepared[name] for name in ('answers', 'paths', 'originals'))
    document, context, corpus = (paths[name] for name in ('document', 'context', 'corpus'))
    assignments = record['recovery']['assignments']
    selected = {role: record['registry']['participants'][assignment['participant_id']]
                for role, assignment in assignments.items()}
    authorize_external(selected, allow_external,
                       **({'allow_api_spend': True} if allow_api_spend else {}))
    cursor = RecoveryCursor(record, store, max_operations)
    record['status'] = 'running'
    record['external_execution_enabled'] = allow_external
    record.pop('error', None)
    store.save(record)

    def stable_inputs():
        if policy:
            policy.check_fresh()
        for path, original in prepared.get('authority_files', {}).items():
            if read_text(path, 131072) != original:
                raise ValueError('Accepted request or registry changed during review')
        for path, original in originals.items():
            if read_text(path, 65_536) != original:
                raise ValueError(f'Accepted input changed during review: {path}')

    def retrieve(query, k):
        stable_inputs()
        if 'retrieval' in record['registry']:
            from .voyage_retrieval import retrieve_voyage
            result = retrieve_voyage(record['registry']['retrieval'], query, k=k,
                                     work_dir=store.directory / 'retrieval-work', allow_provider=allow_provider)
        else:
            result = retrieve_sources(query, corpus, k=k)
        stable_inputs()
        return result

    def verify():
        stable_inputs()
        result = verify_document(document, context)
        stable_inputs()
        return result

    bindings = record['registry'].get('extensions', {})

    def extension_catalog():
        if not bindings:
            return {}
        from .extensions import catalog
        return catalog(bindings, enabled=True)

    def plan_steps():
        extension_catalog()
        # Reject missing dependencies or invalid context before any participant call.
        record['preflight_verification'] = cursor.perform('preflight', 'preflight_verification', verify, effect_class='unknown')
        retrieval_effect = 'paid_retrieval' if 'retrieval' in record['registry'] else 'read_only'
        initial = cursor.perform('retrieval', 'initial_retrieval', lambda: retrieve(answers['query'], 3), effect_class=retrieval_effect)
        record['initial_retrieval'] = initial
        for role, config in selected.items():
            participant_id = assignments[role]['participant_id']
            attempt_id = assignments[role]['attempt_id']
            exchange = protect_command_scope(exchange_factory(config, corpus), store.directory,
                                             *prepared.get('protected_roots', ()))
            history = ([] if policy is None else [
                {'action': {'kind': 'tool', 'name': 'retrieve', 'arguments': {'query': answers['query'], 'k': 3}}, 'result': initial},
                {'action': {'kind': 'tool', 'name': 'verify', 'arguments': {}}, 'result': record['preflight_verification']}])
            outcome = dict(record['participants'].get(role, {}))
            outcome.update(participant_id=participant_id, attempt_id=attempt_id,
                           adapter=config['adapter'], status='running', tool_calls=0)
            record['participants'][role] = outcome
            for index in range(config['max_turns'] if policy is None else 1):
                stable_inputs()
                contributions = extension_catalog()
                turn = assessment_turn(record, prepared, role, index, config, history,
                                       outcome['tool_calls'], contributions, policy)
                response = dispatch_assignment(cursor, f'{attempt_id}:turn:{index}', turn,
                                               config, exchange, outcome, allow_api_spend=allow_api_spend)
                stable_inputs()
                extension_catalog()
                action = response['action']
                if policy:
                    policy.validate_action(action)
                if action['kind'] == 'final':
                    outcome.update(status='completed', text=action['text'])
                    store.save(record)
                    break
                name, arguments, running, is_retrieval = _tool_parameters(
                    action, config, contributions, outcome['tool_calls'], participant_id)
                if running:
                    from .extensions import invoke_tool
                    operation = lambda: invoke_tool(bindings, name, arguments, retrieve,
                        paths=paths, guarded_paths=(store.path, *originals, *prepared.get('authority_files', {})), check_scope=stable_inputs)
                elif is_retrieval:
                    if name in contributions:
                        from .extensions import invoke_tool
                        operation = lambda: invoke_tool(bindings, name, arguments, retrieve)
                    else:
                        operation = lambda: retrieve(arguments['query'], arguments['k'])
                else:
                    operation = verify
                outcome['tool_calls'] += 1
                result = cursor.perform(f'{attempt_id}:tool:{index}', 'tool', operation,
                                 effect_class='scratch_write' if running else retrieval_effect if is_retrieval else 'unknown', participant_id=participant_id,
                                 attempt_id=attempt_id, action=action)
                if is_retrieval and result['corpus']['version'] != initial['corpus']['version']:
                    raise ValueError('Corpus changed during review')
                history.append({'action': action, 'result': result})
            else:
                raise ValueError(f'{participant_id} exhausted its turn budget without a final response')
        record['verification'] = cursor.perform('final', 'final_verification', verify, effect_class='unknown')
        # Recheck referenced source bytes after the final local operation too.
        for event in record['events']:
            result = event.get('result', {})
            if result.get('operation') == 'retrieve':
                if result.get('backend') == 'voyage':
                    from .voyage_retrieval import validate_evidence
                    validate_evidence(record['registry']['retrieval'], result['sources'])
                    continue
                for source in result['sources']:
                    source_path = (corpus / source['path']).resolve()
                    if not source_path.is_relative_to(corpus):
                        raise ValueError('Retrieved source now escapes the accepted corpus')
                    actual = hashlib.sha256(read_text(source_path).encode('utf-8')).hexdigest()
                    if actual != source['sha256']:
                        raise ValueError('Retrieved source changed during review')
        if 'retrieval' in record['registry']:
            from .voyage_index import check_generation
            selected_retrieval = record['registry']['retrieval']
            check_generation(selected_retrieval['config'], selected_retrieval['generation'])
        elif snapshot_sources(corpus) != record['recovery']['source_snapshot']:
            raise ValueError('Accepted corpus snapshot changed during review')
        extension_catalog()
        if any(event['state'] != 'completed' for event in record['events']):
            raise UnresolvedOperation('Saved operation was not consumed by this continuation')
        record['status'] = 'completed'
        record['document_outcome'] = record['verification']['status']
        record['retrieval_outcome'] = initial['status']
        if policy:
            record['integration'] = policy.integrate(record)
    return guarded_execution(record, store, plan_steps)


def guarded_execution(record, store, call):
    """Shared status/error/persistence handling; write failure forbids another dispatch."""
    try:
        call()
    except PersistenceError:
        raise  # No more dispatch or optimistic record overwrite after a write failure.
    except BaseException as exc:
        from .voyage_provider import PaidStageUnresolved
        record['status'] = ('paused' if isinstance(exc, (ReviewPaused, FundingRefused)) else
                            'unresolved' if isinstance(exc, (UnresolvedOperation, PaidStageUnresolved)) else
                            'unavailable' if isinstance(exc, FeatureUnavailable) else
                            'failed' if isinstance(exc, Exception) else 'unresolved')
        record['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        for outcome in record['participants'].values():
            if outcome['status'] == 'running':
                outcome['status'] = record['status']
        store.save(record)
        if not isinstance(exc, Exception):
            raise
        return record
    store.save(record)
    return record


def perform_probe(cursor, plan, key, *, expected=None):
    """Immutable repair acceptance probe on the same operation journal as assessment."""
    from .repair import expected_snapshot, run_probe
    if expected is None:
        expected = expected_snapshot(plan, cursor.record['events'])
    return cursor.perform(key, 'acceptance_probe', lambda: run_probe(plan, expected),
                          effect_class='unknown', plan_digest=digest(plan), artifact_digest=digest(expected))


def dispatch_assignment(cursor, key, turn, config, exchange, outcome, *, allow_api_spend=False):
    """Single transport/correlation boundary for legacy, assessment and repair."""
    participant_id, attempt_id = turn['participant_id'], turn['attempt_id']
    request_digest = digest(turn)
    wire = canonical({'schema_version': 1, 'request_digest': request_digest, 'turn': turn})
    if len(wire.encode('utf-8')) > 524_288:
        raise ValueError('Participant request exceeds 512 KiB')
    admission = None
    if 'funding' in config and not (
            isinstance(exchange, ReviewExchange) and exchange.is_host_step(wire)):
        def admission(event):
            from .participant_funding import admit
            if not isinstance(exchange, ReviewExchange):
                raise FeatureUnavailable('Explicit funding requires the shared owned exchange')
            exchange._funding_admission = admit(cursor, event, config, participant_id, turn['turn_id'],
                                                turn=turn,
                                                allow_api_spend=allow_api_spend)
    def dispatch():
        try:
            raw = exchange(wire)
            return {'action': decode_action(raw, request_digest),
                    'identity': getattr(exchange, 'last_identity', None)}
        finally:
            outcome['last_identity'] = getattr(exchange, 'last_identity', None)
    response = cursor.perform(key, 'participant_turn', dispatch,
                       **({'admission': admission} if admission is not None else {}),
                       effect_class='read_only' if config['adapter'] == 'deterministic' and type(exchange) is ReviewExchange else 'unknown',
                       participant_id=participant_id,
                       attempt_id=attempt_id, turn_id=turn['turn_id'], request_digest=request_digest)
    outcome['last_identity'] = response['identity']
    return response
