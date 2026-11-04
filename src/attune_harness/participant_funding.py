"""Explicit funding configuration; admission stays closed until qualified."""

import re
import os
import copy
from threading import RLock
from weakref import WeakKeyDictionary

from .features import FeatureUnavailable

UNSET = object()
_ISSUED = WeakKeyDictionary()
_ISSUANCE_LOCK = RLock()


def validate(adapter, policy):
    """Validate names only. Never read credentials or infer a legacy policy."""
    if adapter not in ('claude', 'codex', 'openai', 'openai-plan'):
        raise ValueError('Funding is supported only for native Claude or Codex participants')
    if not isinstance(policy, dict) or policy.get('mode') not in ('subscription', 'api'):
        raise ValueError('Funding requires subscription or api mode')
    mode = policy['mode']
    expected = ({'mode', 'profile_id'} if adapter == 'openai-plan' else
                {'mode', 'credential_env'} if mode == 'api' else {'mode'})
    if set(policy) != expected:
        raise ValueError('Funding fields differ from the selected mode')
    if mode == 'api':
        if adapter not in ('codex', 'openai'):
            raise ValueError('Explicit API funding is supported only for Codex')
        name = policy['credential_env']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', name):
            raise ValueError('API funding requires a portable credential environment variable name')
    if adapter == 'openai-plan':
        from .plan_profiles import profile_id
        if mode != 'subscription':
            raise ValueError('The plan adapter requires subscription funding')
        profile_id(policy['profile_id'])
    if adapter == 'openai' and mode != 'api':
        raise ValueError('The OpenAI adapter requires explicit API funding')
    return policy


def inspect(adapter, policy):
    """Report the qualified support boundary without probing auth or credentials."""
    validate(adapter, policy)
    if adapter == 'openai-plan':
        from .plan_profiles import store
        local = store().inspect(policy['profile_id'])
        return {'requested': 'subscription', 'observed': 'unknown', 'state': 'unknown',
                'basis': local['state'], 'cli_version': None, 'profile_id': policy['profile_id']}
    if adapter == 'openai':
        try:
            _environment(policy)
        except ValueError:
            return {'requested': 'api', 'observed': 'unknown', 'state': 'missing_credential',
                    'basis': 'missing_credential', 'cli_version': None}
        return {'requested': 'api', 'observed': 'api', 'state': 'matched',
                'basis': 'scoped_api_request', 'cli_version': None}
    return {'requested': policy['mode'], 'observed': 'unknown',
            'state': 'unsupported', 'basis': 'unqualified_invocation',
            'cli_version': None}


def require_admission(selected, allow_api_spend=False):
    """Prevent accepted policy from silently falling through to inherited auth.

    T1 did not qualify invocation-level selection. T2 accepts the configuration
    for inspection/binding only; no caller can authorize an unqualified route.
    """
    if type(allow_api_spend) is not bool:
        raise ValueError('API spending authority must be a boolean')
    for item in selected.values():
        if item['adapter'] in ('openai', 'openai-plan') and 'funding' not in item:
            raise ValueError('The OpenAI adapter requires explicit API funding')
        if 'funding' in item:
            validate(item['adapter'], item['funding'])
            if item['adapter'] in ('openai', 'openai-plan'):
                # Actual spending is checked per pending model turn, after the
                # owner has a prepared event in which to retain a refusal.
                continue
            raise FeatureUnavailable(
                'Explicit participant funding is not admitted: invocation-level route '
                'enforcement is unqualified. No provider call was started.')


def model_key(provider, model):
    """Compare transport-independent identity without rewriting configuration."""
    return ('openai' if provider in ('codex', 'openai', 'openai-plan') else provider, model)


def distinct_api_models(configurations):
    """A new API transport cannot create reviewer independence by itself."""
    values = list(configurations)
    if any(c['adapter'] in ('openai', 'openai-plan') for c in values):
        keys = [model_key(c['adapter'], c.get('model')) for c in values if c.get('model')]
        if len(keys) != len(set(keys)):
            raise ValueError('OpenAI and Codex review seats require distinct configured models')


def _environment(policy, source=None):
    source = os.environ if source is None else source
    name = policy['credential_env']
    if os.name == 'nt':
        names = [key for key in source if key.casefold() == name.casefold()]
        if len(names) != 1:
            raise ValueError('Selected API credential is unavailable or ambiguous')
        name = names[0]
    value = source.get(name)
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9_-]{20,8192}', value) is None:
        raise ValueError('Selected API credential is missing or invalid')
    # The worker needs no shell, native provider settings, proxy or SDK defaults.
    environment = {key: source[key] for key in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP') if key in source}
    environment['OPENAI_API_KEY'] = value
    return environment


class FundingRefused(FeatureUnavailable):
    def __init__(self, evidence):
        detail = ('Explicit API funding requires --allow-api-spend for this execution (api_authority_required)'
                  if evidence['basis'] == 'api_authority_required' else
                  'Funding admission refused: ' + evidence['basis'])
        super().__init__(detail + '. No provider call was started.')
        self.funding = copy.deepcopy(evidence)


class FundingPrecheckRefused(FundingRefused):
    def __init__(self, basis):
        FeatureUnavailable.__init__(self, 'Pending mixed funding refused: ' + basis + '. No provider call was started.')
        self.funding = None  # No fabricated per-turn receipt before its request exists.


class _Admission:
    """Ephemeral capability; credentials and authority are never serialized."""
    def __init__(self, environment, receipt, model=None):
        self.environment = environment
        self.receipt = receipt
        self.durable = False
        self.used = False
        self.model = model
        self.wire_digest = None


def _issued(admission, model=None):
    if type(admission) is not _Admission or admission not in _ISSUED:
        raise ValueError('OpenAI execution requires the owner\'s persisted admission')
    issued = _ISSUED[admission]
    receipt = admission.receipt
    if (model is not None and model != issued['model']) or not isinstance(receipt, dict) or (
            set(receipt) != set(issued['receipt'])) or any(
            receipt[key] != value for key, value in issued['receipt'].items()
            if key != 'dispatch_outcome'):
        raise ValueError('API invocation differs from its owner admission')
    return issued


def check_issued(admission, model):
    with _ISSUANCE_LOCK:
        _issued(admission, model)


def bind_request(admission, raw):
    import hashlib
    with _ISSUANCE_LOCK:
        issued = _issued(admission)
        observed = hashlib.sha256(raw.encode()).hexdigest()
        if issued['wire_digest'] != observed:
            raise ValueError('API request differs from the owner-bound request')


def claim(admission, model, raw):
    import hashlib
    with _ISSUANCE_LOCK:
        issued = _issued(admission, model)
        if issued['used']:
            raise ValueError('Funding admission was already consumed')
        if issued['store']._lease_token is not issued['lease']:
            raise ValueError('Funding admission no longer has its owner lease')
        if issued['wire_digest'] != hashlib.sha256(raw.encode()).hexdigest():
            raise ValueError('API request differs from the owner-bound request')
        saved = _read_owner(issued['store'], issued['projection'])
        event = next((item for item in saved['events']
                      if item['event_id'] == issued['event']['event_id']), None)
        receipt = {**issued['receipt'], 'dispatch_outcome': 'unknown'}
        if (saved.get('status') != 'running' or event is None
                or event['phase'] != 'dispatching' or event['state'] != 'pending'
                or any(event.get(key) != value for key, value in issued['event'].items())
                or event.get('funding') != receipt):
            raise ValueError('API request requires its persisted owner dispatch boundary')
        if issued.get('plan'):
            from .plan_funding import context, verify_runtime
            selected = context(issued)
            with selected['store'].claim(selected['profile_id'], selected['generation'], selected['deadline']):
                verify_runtime(selected)
                issued['used'] = True
                admission.used = True
                return dict(issued['environment'])
        issued['used'] = True
        admission.used = True
        return dict(issued['environment'])


def plan_context(admission):
    from .plan_funding import context
    with _ISSUANCE_LOCK:
        return context(_issued(admission))


def release(admission):
    with _ISSUANCE_LOCK:
        if admission in _ISSUED:
            _ISSUED[admission]['environment'] = {}
            if _ISSUED[admission].get('plan'):
                _ISSUED[admission]['used'] = True
        admission.environment = {}


def _owner_store(cursor):
    from .review_store import RunStore
    from .task_policies import TaskExecutionStore
    from .work_runtime import PlanningStore
    from .work_build import BuildStore
    store = cursor.store
    projections = {TaskExecutionStore: 'execution', PlanningStore: 'planning', BuildStore: 'build'}
    if type(store) is RunStore:
        base, projection = store, None
    elif type(store) in projections and type(store.store) is RunStore:
        base, projection = store.store, projections[type(store)]
    else:
        raise ValueError('Funding admission requires a supported persisted owner')
    if base._lease_token is None:
        raise ValueError('Funding admission requires an active owner lease')
    return base, projection, base._lease_token


def _read_owner(store, projection):
    from .review_store import read_record
    saved = read_record(store.directory)
    if projection is not None:
        from .task_contract import read_task
        saved = read_task(store.directory)[projection]
    elif saved.get('profile') == 'model-consultation-v1':
        from .consultation import load
        saved = load(store.directory)
    elif saved.get('operation') == 'review':
        from .recovery import load_recovery
        saved = load_recovery(store, saved['checkpoint_digest'])
    else:
        raise ValueError('Funding admission has no supported owner contract')
    return saved


def _validate_persisted_owner(cursor, store, projection):
    from .review_store import PersistenceError
    from .review_contract import digest
    saved = _read_owner(store, projection)
    if saved.get('status') != 'running' or digest(saved) != digest(cursor.record):
        raise PersistenceError('Funding admission differs from its persisted owner')


def _owner_request(cursor, event, config, participant, attempt_id, turn):
    from .review_contract import digest
    record = cursor.record
    if not isinstance(turn, dict) or digest(turn) != event.get('request_digest'):
        raise ValueError('Funding request differs from its owner event')
    if event['kind'] == 'consultation_turn':
        from .consultation import model_attempt, owned_turn
        expected = owned_turn(record, event['operation_key'])
        if (turn != expected or config != record['contract']['configuration']['participants'][participant]
                or turn['participant'] != participant or turn['attempt_id'] != attempt_id):
            raise ValueError('Funding request differs from its owner assignment')
        return model_attempt(config, turn).request()
    if event['kind'] == 'participant_turn':
        from .review_participants import model_attempt
        if record.get('profile') not in ('feature-planning-v1', 'feature-build-v1'):
            from .task_runtime import funding_turn
            if turn != funding_turn(cursor, event):
                raise ValueError('Funding request differs from accepted owner inputs')
        if (turn['participant_id'] != participant or turn['turn_id'] != attempt_id
                or any(event.get(key) != turn[key]
                       for key in ('participant_id', 'attempt_id', 'turn_id'))):
            raise ValueError('Funding request differs from its owner assignment')
        request = {'schema_version': 1, 'request_digest': digest(turn), 'turn': turn}
        return model_attempt(config, request, record.get('profile') or 'harness-review-v1').request()
    raise ValueError('Funding admission requires a model operation')


def admit(cursor, event, config, participant, attempt_id, *, turn,
          allow_api_spend=False, allow_external=False):
    """Save the owner's admission before its prepared event can dispatch."""
    from .review_contract import digest
    from .recovery import RecoveryCursor
    if type(cursor) is not RecoveryCursor or cursor.events.get(event['operation_key']) is not event:
        raise ValueError('Funding admission requires the owning recovery cursor')
    store, projection, lease = _owner_store(cursor)
    if event['phase'] != 'prepared' or event['state'] != 'pending':
        raise ValueError('Funding admission requires a prepared owner operation')
    if type(allow_api_spend) is not bool:
        raise ValueError('API spending authority must be a boolean')
    if type(allow_external) is not bool or not allow_external:
        raise FeatureUnavailable('Explicit API funding also requires external execution authority')
    validate(config['adapter'], config['funding'])
    raw = _owner_request(cursor, event, config, participant, attempt_id, turn)
    report = inspect(config['adapter'], config['funding']) if config['adapter'] not in ('openai', 'openai-plan') else {
        'requested': 'api', 'observed': 'unknown', 'state': 'unknown',
        'basis': 'api_authority_required', 'cli_version': None}
    environment = None
    if config['adapter'] == 'openai' and allow_api_spend is True:
        try:
            environment = _environment(config['funding'])
            report.update(observed='api', state='matched', basis='scoped_api_request')
        except ValueError:
            report.update(state='missing_credential', basis='missing_credential')
    plan = None
    if config['adapter'] == 'openai-plan':
        from .plan_funding import prepare
        report, environment, plan = prepare(config, raw)
    receipt = {'profile': ('participant-funding-v2' if config['adapter'] == 'openai-plan' else 'participant-funding-v1'), **report,
               'api_authorized': allow_api_spend is True, 'dispatch_outcome': 'not_started',
               'participant_id': participant, 'configuration_digest': digest(config),
               'attempt_id': attempt_id, 'attempt': event['attempts'],
               'request_digest': event['request_digest']}
    if 'funding' in event:
        history = event.setdefault('funding_history', [])
        if len(history) >= 16:
            raise FeatureUnavailable('Funding admission history is full; retain this run and prepare new work')
        history.append(copy.deepcopy(event['funding']))
    event['funding'] = receipt
    cursor.store.save(cursor.record)
    _validate_persisted_owner(cursor, store, projection)
    if report['state'] != 'matched':
        raise FundingRefused(receipt)
    admission = _Admission(environment, receipt, config.get('model') or config['identity']['model'])
    admission.durable = True
    with _ISSUANCE_LOCK:
        import hashlib
        _ISSUED[admission] = {'model': admission.model, 'receipt': copy.deepcopy(receipt),
                              'environment': dict(environment), 'used': False, 'plan': plan,
                              'wire_digest': hashlib.sha256(raw.encode()).hexdigest(),
                              'store': store, 'lease': lease, 'projection': projection,
                              'event': {key: copy.deepcopy(value) for key, value in event.items()
                                        if key in ('event_id', 'operation_key', 'kind', 'effect_class',
                                                   'attempts', 'request_digest', 'participant_id',
                                                   'attempt_id', 'turn_id')}}
    return admission


def validate_evidence(value, *, config=None, participant=None, attempt_id=None,
                      attempt=None, request_digest=None):
    """Validate only optional new evidence; legacy records acquire no claims."""
    from .review_contract import digest, fields
    if isinstance(value, dict) and value.get('profile') == 'participant-funding-v2':
        from .plan_funding import validate as validate_plan
        return validate_plan(value, config=config, participant=participant, attempt_id=attempt_id,
                             attempt=attempt, request_digest=request_digest)
    if config is not None and config['adapter'] == 'openai-plan':
        raise ValueError('Plan adapter requires v2 funding evidence')
    fields(value, ('profile', 'requested', 'observed', 'state', 'basis', 'cli_version',
                   'api_authorized', 'dispatch_outcome', 'participant_id',
                   'configuration_digest', 'attempt_id', 'attempt', 'request_digest'))
    if (value['profile'] != 'participant-funding-v1'
            or value['requested'] not in ('api', 'subscription')
            or value['observed'] not in ('api', 'subscription', 'unknown')
            or value['state'] not in ('matched', 'missing_credential', 'unsupported', 'unknown')
            or value['basis'] not in ('scoped_api_request', 'missing_credential',
                                     'api_authority_required', 'unqualified_invocation')
            or value['cli_version'] is not None or type(value['api_authorized']) is not bool
            or value['dispatch_outcome'] not in ('not_started', 'started', 'completed', 'unknown')
            or type(value['attempt']) is not int or not 1 <= value['attempt'] <= 2
            or any(not isinstance(value[k], str) or not 1 <= len(value[k]) <= 200
                   for k in ('participant_id', 'attempt_id'))
            or any(not isinstance(value[k], str) or not re.fullmatch('[0-9a-f]{64}', value[k])
                   for k in ('configuration_digest', 'request_digest'))):
        raise ValueError('Invalid funding evidence')
    if value['state'] == 'matched' and (value['requested'] != 'api' or value['observed'] != 'api'
            or value['basis'] != 'scoped_api_request' or not value['api_authorized']):
        raise ValueError('Invalid matched funding evidence')
    if value['state'] != 'matched' and value['dispatch_outcome'] != 'not_started':
        raise ValueError('Refused funding cannot claim dispatch')
    if value['state'] == 'missing_credential' and (value['requested'] != 'api'
            or value['observed'] != 'unknown' or value['basis'] != 'missing_credential'
            or not value['api_authorized']):
        raise ValueError('Invalid missing-credential evidence')
    if value['state'] == 'unknown' and (value['requested'] != 'api'
            or value['observed'] != 'unknown' or value['basis'] != 'api_authority_required'
            or value['api_authorized']):
        raise ValueError('Invalid API-authority evidence')
    if value['state'] == 'unsupported' and (value['observed'] != 'unknown'
            or value['basis'] != 'unqualified_invocation'):
        raise ValueError('Invalid unsupported funding evidence')
    expected = {'participant_id': participant, 'attempt_id': attempt_id, 'attempt': attempt,
                'request_digest': request_digest}
    if config is not None:
        expected.update(configuration_digest=digest(config), requested=config['funding']['mode'])
    if any(value[key] != selected for key, selected in expected.items() if selected is not None):
        raise ValueError('Funding evidence differs from the accepted participant or attempt')
    return value


def validate_event(event, config, participant, attempt_id):
    """Bind optional funding and usage to the owner's reconstructed operation."""
    result = event.get('result') or {}
    identity = (result.get('identity') or {}) if isinstance(result, dict) else {}
    if not isinstance(identity, dict):
        if config.get('adapter') in ('openai', 'openai-plan'):
            raise ValueError('Invalid funded participant identity')
        identity = {}
    host_step = identity.get('adapter') == 'host-evidence'
    if host_step and config.get('adapter') in ('openai', 'openai-plan'):
        action = result.get('action')
        if (config.get('review_mode') != 'evidence'
                or set(identity) != {'adapter', 'native_adapter', 'model'}
                or identity['native_adapter'] != config['adapter'] or identity['model'] is not None
                or 'funding' in event or 'funding_history' in event
                or not isinstance(action, dict)
                or set(action) != {'kind', 'name', 'arguments'}
                or action['kind'] != 'tool' or action['name'] not in ('retrieve', 'verify')
                or not isinstance(action['arguments'], dict)):
            raise ValueError('Invalid API host evidence step')
        arguments = action['arguments']
        from .recovery import stable_id
        index = '0' if action['name'] == 'retrieve' else '1'
        if (event.get('kind') != 'participant_turn'
                or not isinstance(event.get('attempt_id'), str)
                or event.get('turn_id') != stable_id(event.get('attempt_id'), index)
                or event.get('operation_key') != f"{event.get('attempt_id')}:turn:{index}"):
            raise ValueError('Invalid API host evidence assignment')
        if ((action['name'] == 'verify' and arguments != {})
                or (action['name'] == 'retrieve' and (
                    set(arguments) != {'query', 'k'} or type(arguments['k']) is not int
                    or arguments['k'] != 3 or not isinstance(arguments['query'], str)
                    or not arguments['query'].strip()))):
            raise ValueError('Invalid API host evidence action')
    if 'funding' not in config and ('funding' in identity or 'usage' in identity):
        raise ValueError('Legacy identity invented funding or usage evidence')
    expected = {'config': config, 'participant': participant, 'attempt_id': attempt_id,
                'request_digest': event.get('request_digest')}
    if 'funding' in event:
        if 'funding' not in config:
            raise ValueError('Legacy operation invented funding evidence')
        validate_evidence(event['funding'], attempt=event['attempts'], **expected)
        if event['phase'] == 'prepared' and event['funding']['dispatch_outcome'] != 'not_started':
            raise ValueError('Prepared funding cannot claim a dispatch')
        for previous in event.get('funding_history', []):
            validate_evidence(previous, **expected)
    elif config.get('adapter') in ('openai', 'openai-plan') and event['phase'] != 'prepared' and not host_step:
        raise ValueError('API operation omitted funding admission')
    if config.get('adapter') in ('openai', 'openai-plan') and event['phase'] == 'completed' and not host_step:
        if identity.get('funding') != event.get('funding'):
            raise ValueError('Result funding differs from its admission')
        from .funding_usage import validate
        if identity.get('usage') is not None:
            validate(identity['usage'])


def validate_owned_event(record, event):
    from .review_contract import digest
    config = None
    if event.get('kind') == 'participant_turn' and 'registry' in record:
        participant, attempt = event.get('participant_id'), event.get('turn_id')
        config = record['registry']['participants'].get(participant)
    elif event.get('kind') == 'consultation_turn' and 'contract' in record:
        participant = event['operation_key'].partition(':')[2]
        config = record['contract']['configuration']['participants'].get(participant)
        attempt = digest([record['contract_digest'], event['operation_key']])
        if config is not None and 'funding' in config:
            from .consultation import owned_turn
            if event.get('request_digest') != digest(owned_turn(record, event['operation_key'])):
                raise ValueError('Funding request differs from its accepted consultation')
    else:
        return
    if config is not None:
        result = event.get('result') or {}
        identity = (result.get('identity') or {}) if isinstance(result, dict) else {}
        if (config['adapter'] in ('openai', 'openai-plan') and 'accepted' not in record
                and isinstance(identity, dict) and identity.get('adapter') == 'host-evidence'):
            raise ValueError('Invalid API host evidence owner')
        validate_event(event, config, participant, attempt)
        if (config['adapter'] in ('openai', 'openai-plan') and isinstance(identity, dict)
                and identity.get('adapter') == 'host-evidence'):
            _validate_host_context(record, event)
    elif 'funding' in event:
        raise ValueError('Unknown funded participant')


def _validate_host_context(record, event):
    """Compare the full host result with retained accepted inputs and tools."""
    from .recovery import stable_id
    from .review_participants import host_action
    from .task_runtime import _funding_assignments
    assignments = _funding_assignments(record)
    allowed = {(a['participant_id'], a['attempt_id']) for a in assignments.values()}
    allowed.update((t['from'], t['prior_attempt_id']) for t in record['recovery']['transfers'])
    pair = event.get('participant_id'), event.get('attempt_id')
    if pair not in allowed or (event['phase'], event['state']) != ('completed', 'completed'):
        raise ValueError('Invalid API host evidence assignment')
    indices = [index for index in (0, 1)
               if event['turn_id'] == stable_id(event['attempt_id'], str(index))]
    if len(indices) != 1:
        raise ValueError('Invalid API host evidence assignment')
    index = indices[0]
    expected = host_action(record['accepted']['submission']['answers']['query'], index)
    result = event['result']
    if set(result) != {'identity', 'action'} or result['action'] != expected:
        raise ValueError('Invalid API host evidence accepted action')
    key = f"{event['attempt_id']}:tool:{index}"
    following = [e for e in record['events'] if e.get('operation_key') == key]
    if following and (len(following) != 1 or following[0].get('kind') != 'tool'
                      or following[0].get('action') != expected
                      or any(following[0].get(k) != event.get(k)
                             for k in ('participant_id', 'attempt_id'))):
        raise ValueError('Invalid API host evidence tool history')
