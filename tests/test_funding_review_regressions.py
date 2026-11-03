"""Independent-review regressions use synthetic keys and inert exchanges."""
# qualify: platform

import codecs
import copy
import hashlib
import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, ExitStack
from threading import Barrier
from types import SimpleNamespace

import pytest

from attune_harness import consultation
from attune_harness.openai_exchange import OpenAIExchange
from attune_harness.participant_funding import _Admission, admit, bind_request
from attune_harness.process import ProcessResult
from attune_harness.recovery import RecoveryCursor, load_recovery, reconcile_review, resume_review
from attune_harness.review_contract import canonical, digest
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import control_task, execute_task
from test_openai_funding import KEY, MODEL, api, prepare, provider_response, registry_participant
from test_review import case, change_config
from test_task_contract import draft, response


@contextmanager
def consultation_owner(tmp_path):
    """Keep a real prepared owner's writer lease active through the claim."""
    directory, _ = prepare(tmp_path)
    store = RunStore(directory, existing=True)
    with store.lease():
        record = consultation.load(directory)
        record['status'] = 'running'
        store.save(record)
        config = record['contract']['configuration']['participants']['reviewer']
        turn = consultation.owned_turn(record, '0:reviewer')
        yield RecoveryCursor(record, store), config, turn


def issue_capability(cursor, config, turn, *, dispatching=True, compare=True):
    """Use the dispatcher's shared builder, including every outer constraint."""
    raw = consultation.model_attempt(config, turn).request()
    issued = []

    def authorize(event):
        issued.append(admit(cursor, event, config, 'reviewer', turn['attempt_id'],
                            turn=turn, allow_api_spend=True))

    cursor.begin('0:reviewer', 'consultation_turn', admission=authorize,
                 prepare_only=True, effect_class='unknown', request_digest=digest(turn))
    if compare:
        bind_request(issued[0], raw)
    if dispatching:
        cursor.begin('0:reviewer', 'consultation_turn', effect_class='unknown', request_digest=digest(turn))
    return issued[0], raw


@contextmanager
def issued_capability(tmp_path, **options):
    with consultation_owner(tmp_path) as (cursor, config, turn):
        yield issue_capability(cursor, config, turn, **options)


@pytest.fixture
def capability(tmp_path):
    with ExitStack() as owners:
        yield lambda **options: owners.enter_context(issued_capability(tmp_path, **options))


def inert_runner(calls):
    def runner(argv, raw, **kwargs):
        body = json.loads(raw)['body']
        calls.append({'body': body, 'environment': dict(kwargs['environment'])})
        return ProcessResult(tuple(argv), 0, canonical(provider_response(MODEL, 'Synthetic capability response')), '')
    return runner


@pytest.mark.parametrize('forgery', ['constructed', 'shallow_copy', 'deep_copy'])
def test_public_admission_fields_cannot_forge_issued_authority(tmp_path, api, capability, forgery):
    legitimate, raw = capability()
    if forgery == 'constructed':
        forged = _Admission({'OPENAI_API_KEY': KEY}, copy.deepcopy(legitimate.receipt), MODEL)
    else:
        forged = copy.copy(legitimate) if forgery == 'shallow_copy' else copy.deepcopy(legitimate)
    forged.durable = True
    forged.used = False
    forged.model = MODEL
    forged.wire_digest = hashlib.sha256(raw.encode()).hexdigest()
    calls = []
    with pytest.raises(ValueError, match='persisted admission'):
        exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=forged, runner=inert_runner(calls))
        exchange(raw)
    assert calls == [] and api.calls == []


@pytest.mark.parametrize('field', ['environment_in_place', 'environment_replaced', 'model', 'wire_digest', 'used'])
def test_public_capability_mutation_cannot_change_private_model_key_or_wire(tmp_path, api, capability, field):
    admission, raw = capability()
    if field == 'environment_in_place':
        admission.environment['OPENAI_API_KEY'] = 'unapproved_synthetic_key_0123456789'
    elif field == 'environment_replaced':
        admission.environment = {'OPENAI_API_KEY': 'unapproved_synthetic_key_0123456789'}
    elif field == 'model':
        admission.model = 'fixture-unapproved-model'
    elif field == 'wire_digest':
        admission.wire_digest = '0' * 64
    else:
        admission.used = True
    calls = []
    exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    assert json.loads(exchange(raw))['text'] == 'Synthetic capability response'
    assert len(calls) == 1
    assert calls[0]['body']['model'] == MODEL
    assert calls[0]['body']['input'].endswith(raw)
    assert calls[0]['environment']['OPENAI_API_KEY'] == KEY
    assert admission.environment == {}


@pytest.mark.parametrize('binding', ['requirements', 'objective', 'participant', 'role', 'outer_field', 'serialization'])
def test_complete_owner_request_cannot_be_changed_or_rebound(tmp_path, api, capability, binding):
    admission, raw = capability()
    value = json.loads(raw)
    if binding == 'requirements':
        value['attempt']['task']['requirements'].append('Unapproved replacement constraint')
    elif binding == 'objective':
        value['attempt']['task']['objective'] = 'Unapproved replacement task'
    elif binding == 'participant':
        value['attempt']['participant_id'] = 'unapproved-participant'
    elif binding == 'role':
        value['attempt']['role'] = 'lead'
    elif binding == 'outer_field':
        value['unapproved'] = True
    changed = json.dumps(value, indent=2) if binding == 'serialization' else canonical(value)
    admission.wire_digest = hashlib.sha256(changed.encode()).hexdigest()
    calls = []
    exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    with pytest.raises(ValueError, match='owner-bound request'):
        bind_request(admission, changed)
    with pytest.raises(ValueError, match='owner-bound request'):
        exchange(changed)
    assert calls == []
    exchange(raw)
    assert len(calls) == 1 and calls[0]['body']['input'].endswith(raw)


def test_complete_request_is_bound_at_issuance_without_a_public_bind_call(tmp_path, api, capability):
    admission, raw = capability(compare=False)
    calls = []
    OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))(raw)
    assert len(calls) == 1


@pytest.mark.parametrize('context', ['configuration_digest', 'participant_id', 'attempt_id', 'request_digest'])
def test_issued_capability_context_cannot_change_after_exchange_construction(tmp_path, api, capability, context):
    admission, raw = capability()
    calls = []
    exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    admission.receipt[context] = '0' * 64 if context.endswith('digest') else 'unapproved-fixture-context'
    with pytest.raises(ValueError, match='owner admission'):
        exchange(raw)
    assert calls == []


def test_exchange_model_mutation_cannot_override_private_admission_model(tmp_path, api, capability):
    admission, raw = capability()
    calls = []
    exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    exchange.model = 'fixture-unapproved-model'
    with pytest.raises(ValueError, match='owner admission'):
        exchange(raw)
    assert calls == []


def test_public_used_flag_reset_cannot_reuse_consumed_authority(tmp_path, api, capability):
    admission, raw = capability()
    calls = []
    runner = inert_runner(calls)
    OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=runner)(raw)
    admission.used = False
    admission.environment = {'OPENAI_API_KEY': KEY}
    with pytest.raises(ValueError, match='already consumed'):
        OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=runner)(raw)
    assert len(calls) == 1


def test_concurrent_public_used_flag_resets_still_allow_only_one_claim(tmp_path, api, capability):
    admission, raw = capability()
    calls = []
    exchanges = [OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission,
                                runner=inert_runner(calls)) for _ in range(2)]
    barrier = Barrier(2)

    def invoke(exchange):
        admission.used = False
        barrier.wait(timeout=5)
        try:
            exchange(raw)
            return 'completed'
        except ValueError as exc:
            assert 'already consumed' in str(exc)
            return 'refused'

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, exchanges))
    assert sorted(results) == ['completed', 'refused']
    assert len(calls) == 1


@pytest.mark.parametrize('store_kind', ['fake', 'real_noop'])
def test_noop_store_cannot_issue_a_durable_capability(tmp_path, api, monkeypatch, store_kind):
    with consultation_owner(tmp_path) as (cursor, config, turn):
        before = cursor.store.path.read_bytes()
        if store_kind == 'fake':
            fake = SimpleNamespace(directory=cursor.store.directory, path=cursor.store.path,
                                   _lease_token=object(), save=lambda record: None)
            cursor = RecoveryCursor(cursor.record, fake)
            error, match = ValueError, 'supported persisted owner'
        else:
            monkeypatch.setattr(cursor.store, 'save', lambda record: None)
            error, match = PersistenceError, 'persisted owner'
        with pytest.raises(error, match=match):
            issue_capability(cursor, config, turn)
        assert cursor.store.path.read_bytes() == before
    assert api.calls == []


@pytest.mark.parametrize('new_lease', [False, True])
def test_expired_owner_lease_cannot_claim_even_after_the_owner_reacquires_it(tmp_path, api, new_lease):
    calls = []
    with consultation_owner(tmp_path) as (cursor, config, turn):
        admission, raw = issue_capability(cursor, config, turn)
        store = cursor.store
        exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    if new_lease:
        with store.lease(), pytest.raises(ValueError, match='owner lease'):
            exchange(raw)
    else:
        with pytest.raises(ValueError, match='owner lease'):
            exchange(raw)
    assert calls == []


def test_prepared_admission_cannot_claim_before_the_durable_dispatch_boundary(tmp_path, api, capability):
    admission, raw = capability(dispatching=False)
    calls = []
    exchange = OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    with pytest.raises(ValueError, match='persisted owner dispatch boundary'):
        exchange(raw)
    assert calls == []


def test_admission_refuses_an_altered_question_even_with_a_matching_caller_event_digest(tmp_path, api):
    with consultation_owner(tmp_path) as (cursor, config, turn):
        _, event = cursor.begin('0:reviewer', 'consultation_turn', prepare_only=True,
                                effect_class='unknown', request_digest=digest(turn))
        before = cursor.store.path.read_bytes()
        changed = copy.deepcopy(turn)
        changed['question'] = 'Unapproved replacement of the accepted question'
        event['request_digest'] = digest(changed)
        with pytest.raises(ValueError, match='owner assignment'):
            admit(cursor, event, config, 'reviewer', turn['attempt_id'],
                  turn=changed, allow_api_spend=True)
        assert cursor.store.path.read_bytes() == before
    assert api.calls == []


def test_issuance_cannot_escape_failed_admission_persistence(tmp_path, api, monkeypatch):
    directory, prepared = prepare(tmp_path)
    original = RunStore.save
    initialize = _Admission.__init__
    created = []

    def track(admission, *args, **kwargs):
        initialize(admission, *args, **kwargs)
        created.append(admission)

    def fail(store, record):
        if any(event.get('funding', {}).get('state') == 'matched' for event in record['events']):
            raise PersistenceError('Synthetic durable admission failure')
        return original(store, record)

    monkeypatch.setattr(RunStore, 'save', fail)
    monkeypatch.setattr(_Admission, '__init__', track)
    with pytest.raises(PersistenceError, match='Synthetic durable admission failure'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    calls = []
    for admission in created:
        # An allocation before persistence is harmless only while unissued.
        with pytest.raises(ValueError, match='persisted admission'):
            OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=inert_runner(calls))
    assert calls == []
    assert api.calls == []


def encoded_key(kind, layers):
    formats = {'unicode': '\\u%04x', 'unicode_long': '\\U%08x', 'hex': '\\x%02x', 'octal': '\\%03o'}
    text = ''.join(formats[kind] % ord(character) for character in KEY)
    for _ in range(layers - 1):
        text = text.replace('\\', '\\\\')
    return text


def assert_no_decoded_key(text):
    """Decode the observed prose independently of the production redactor."""
    for _ in range(16):
        assert KEY not in text
        decoded = codecs.decode(text.encode('ascii'), 'unicode_escape')
        if decoded == text:
            return
        text = decoded
    assert KEY not in text


@pytest.mark.parametrize('kind', ['unicode', 'unicode_long', 'hex', 'octal'])
@pytest.mark.parametrize('layers', [1, 2, 4])
def test_selected_key_encoded_inside_non_json_prose_is_never_retained(tmp_path, api, kind, layers):
    escaped = encoded_key(kind, layers)

    def transform(value):
        answer = {'verdict': 'uncertain', 'summary': 'prefix ' + escaped + ' suffix', 'evidence': []}
        value['output'][0]['content'][0]['text'] = canonical({'text': canonical(answer)})
        return value

    api.transform = transform
    directory, prepared = prepare(tmp_path)
    result = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert result['status'] in ('completed', 'failed')
    assert len(api.calls) == 1
    assert KEY not in canonical(result)
    saved = json.loads((directory / 'record.json').read_text(encoding='utf-8'))
    assert KEY not in canonical(saved)
    if result['status'] == 'completed':
        summary = result['answers'][0]['answer']['summary']
        assert_no_decoded_key(summary)
        assert_no_decoded_key(saved['answers'][0]['answer']['summary'])
        assert escaped not in summary


@pytest.mark.parametrize('kind', ['unicode', 'unicode_long', 'hex', 'octal'])
@pytest.mark.parametrize('layers', [1, 3])
def test_encoded_json_property_names_are_scrubbed_without_changing_benign_values(kind, layers):
    from attune_harness.openai_exchange import _redact

    escaped = encoded_key(kind, layers)
    cleaned = _redact({escaped: 'Retain this benign user value'}, KEY)
    assert len(cleaned) == 1
    name, value = next(iter(cleaned.items()))
    assert_no_decoded_key(name)
    assert name != escaped and value == 'Retain this benign user value'


@pytest.mark.parametrize('kind', ['unicode', 'hex', 'octal'])
def test_scrubbing_encoded_json_property_names_refuses_collisions(kind):
    from attune_harness.openai_exchange import _redact

    escaped = encoded_key(kind, 2)
    cleaned_name = next(iter(_redact({escaped: 'first'}, KEY)))
    assert cleaned_name != escaped
    with pytest.raises(ValueError, match='duplicate fields'):
        _redact({escaped: 'first', cleaned_name: 'second'}, KEY)


def test_provider_property_key_collision_fails_without_retaining_the_credential(tmp_path, api):
    from attune_harness.openai_exchange import _redact

    escaped = encoded_key('unicode', 2)
    cleaned_name = next(iter(_redact({escaped: 'first'}, KEY)))

    def transform(value):
        value[escaped] = 'first'
        value[cleaned_name] = 'second'
        return value

    api.transform = transform
    directory, prepared = prepare(tmp_path)
    result = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert result['status'] == 'failed' and len(api.calls) == 1
    assert KEY not in canonical(result)
    assert KEY not in (directory / 'record.json').read_text(encoding='utf-8')


def failed_owned_api(case, api, owner):
    review = importlib.import_module('attune_harness.review')
    change_config(case, lambda value: value['participants'].update(alpha=registry_participant()))
    api.stdout = 'synthetic invalid provider JSON'
    if owner == 'review':
        record = review.review(*case, allow_external=True, allow_api_spend=True)
        run = record
    else:
        draft(case)
        accepted = response(case[2])
        accepted['permissions']['external'] = True
        accept_task(case[2], accepted)
        record = execute_task(case[2], allow_api_spend=True)
        run = record['execution']
    assert record['status'] == 'failed'
    event = next(event for event in run['events'] if 'funding' in event)
    assert event['phase'] == 'dispatching' and len(api.calls) == 1
    return record, run, event


def read_owned(directory, record, owner):
    if owner == 'review':
        return load_recovery(RunStore(directory, existing=True), record['checkpoint_digest'])
    return read_task(directory)


@pytest.mark.parametrize('owner', ['review', 'assessment'])
@pytest.mark.parametrize('placement', ['run', 'event'])
def test_owned_readers_require_funding_on_historical_api_attempts(case, api, owner, placement):
    record, run, event = failed_owned_api(case, api, owner)
    previous = copy.deepcopy(event)
    event.update(phase='completed', state='completed', result={
        'action': {'kind': 'final', 'text': 'Historical synthetic recovered reply'},
        'identity': {'adapter': 'openai', 'funding': copy.deepcopy(event['funding']), 'usage': None}})
    event.pop('error', None)
    event.pop('effects', None)
    retained = {'event_id': event['event_id'], 'checkpoint': record['checkpoint_digest'],
                'previous': previous, 'evidence': {'kind': 'recovered_reply',
                    'identity': 'historical synthetic operator reply; not authenticated'}}
    if placement == 'run':
        run['recovery']['reconciliations'].append(retained)
    else:
        event['reconciliations'] = [retained]
    record['status'] = run['status'] = 'paused'
    record.pop('error', None)
    run.pop('error', None)
    store = RunStore(case[2], existing=True)
    with store.lease():
        store.save(record)
    read_owned(case[2], record, owner)  # The otherwise valid historical fixture loads.
    del previous['funding']
    with store.lease():
        store.save(record)
    with pytest.raises(ValueError, match='API operation omitted funding admission'):
        read_owned(case[2], record, owner)
    assert len(api.calls) == 1


@pytest.mark.parametrize('owner', ['review', 'assessment'])
@pytest.mark.parametrize('content', ['safe', 'credential'])
def test_api_recovered_reply_refuses_before_reading_or_mutating_any_file(case, api, monkeypatch, owner, content):
    record, _, event = failed_owned_api(case, api, owner)
    reply = case[0].parent / 'recovered-api.json'
    reply.write_text(canonical({'schema_version': 1, 'request_digest': event['request_digest'],
                                'action': {'kind': 'final', 'text': KEY if content == 'credential'
                                           else 'Safe synthetic recovered reply'}}), encoding='utf-8')
    input_before, record_before = reply.read_bytes(), (case[2] / 'record.json').read_bytes()
    recovery = importlib.import_module('attune_harness.recovery')
    original = recovery.read_text

    def refuse_read(path, *args):
        assert path != reply, 'API recovery read the reply before refusing'
        return original(path, *args)

    monkeypatch.setattr(recovery, 'read_text', refuse_read)
    with pytest.raises(ValueError, match='credential-redaction context'):
        if owner == 'review':
            reconcile_review(case[2], record['checkpoint_digest'], event['event_id'], reply_file=reply)
        else:
            control_task(case[2], 'reconcile', checkpoint=record['checkpoint_digest'],
                         event_id=event['event_id'], reply_file=reply)
    assert reply.read_bytes() == input_before
    assert (case[2] / 'record.json').read_bytes() == record_before
    assert len(api.calls) == 1


@pytest.mark.parametrize('owner', ['review', 'assessment'])
def test_legacy_recovered_reply_still_reconciles_and_resumes(case, api, owner):
    review = importlib.import_module('attune_harness.review')

    def factory(config, cwd):
        def fail(raw):
            raise RuntimeError('Synthetic legacy exchange failure')
        return fail

    if owner == 'review':
        failed = review.review(*case, exchange_factory=factory)
        run = failed
    else:
        draft(case)
        accept_task(case[2], response(case[2]))
        failed = execute_task(case[2], exchange_factory=factory)
        run = failed['execution']
    event = next(event for event in run['events'] if event['kind'] == 'participant_turn')
    assert failed['status'] == 'failed' and 'funding' not in event
    reply = case[0].parent / 'recovered-legacy.json'
    reply.write_text(canonical({'schema_version': 1, 'request_digest': event['request_digest'],
                                'action': {'kind': 'final', 'text': 'Legacy recovered assessment'}}), encoding='utf-8')
    original = reply.read_bytes()

    def continued_factory(config, cwd):
        # Keep the injected factory's unknown-effect contract on replay.
        exchange = ReviewExchange(config, cwd)
        return lambda raw: exchange(raw)

    if owner == 'review':
        reconciled = reconcile_review(case[2], failed['checkpoint_digest'], event['event_id'], reply_file=reply)
        completed = resume_review(case[2], case[0], case[1], reconciled['checkpoint_digest'],
                                  exchange_factory=continued_factory)
    else:
        control_task(case[2], 'reconcile', checkpoint=failed['checkpoint_digest'],
                     event_id=event['event_id'], reply_file=reply)
        completed = execute_task(case[2], exchange_factory=continued_factory)
    assert completed['status'] == 'completed', completed.get('execution', completed).get('error')
    assert reply.read_bytes() == original and api.calls == []
