"""Plan/API owners use synthetic grants and inert transport; no live qualification."""
# qualify: platform

import copy
import importlib
import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from attune_harness import consultation, participant_funding as funding
from attune_harness.cli import main
from attune_harness.features import FeatureUnavailable
from attune_harness.plan_exchange import PlanExchange
from attune_harness.process import ProcessResult
from attune_harness.review_contract import canonical, digest
from attune_harness.review_store import RunStore
from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import execute_task
from test_openai_funding import InertAPI, provider_response
from test_review import case, change_config
from test_task_contract import draft, response
from test_work_contract import work, make
from test_work_planning import add_critic
from test_work_build import prepare as prepare_build, Worker
from test_task_repair_effects import effect_case
from test_task_repair import prepare as prepare_repair, proposal
from test_funding_review_regressions import consultation_owner, issue_capability

PID = 'plan_' + 'a' * 32
GEN = 'b' * 32
TOKEN = 'synthetic_plan_access_0123456789'
RUNTIME = {'ca_file': '/inert/ca.pem', 'ca_sha256': 'c' * 64, 'worker_profile': 'd' * 64}


def seat(model='fixture-plan-model'):
    return {'adapter': 'openai-plan', 'identity': {'provider': 'openai', 'model': model},
            'timeout': 10, 'funding': {'mode': 'subscription', 'profile_id': PID}}


def participant(model='fixture-plan-model', evidence=False):
    return {'adapter': 'openai-plan', 'model': model, 'timeout': 10,
            'tools': ['retrieve', 'verify'] if evidence else [], 'max_turns': 3 if evidence else 1,
            'max_tool_calls': 2 if evidence else 0, 'funding': {'mode': 'subscription', 'profile_id': PID},
            **({'review_mode': 'evidence'} if evidence else {})}


class Profiles:
    generation = GEN
    enabled = True
    resolutions = 0

    def resolve(self, pid, deadline):
        self.resolutions += 1
        if not self.enabled or pid != PID: raise FeatureUnavailable('Inert disabled profile')
        return {'token': TOKEN, 'generation': self.generation}

    @contextmanager
    def claim(self, pid, generation, deadline):
        if not self.current(pid, generation): raise FeatureUnavailable('Inert profile changed')
        yield

    def current(self, pid, generation):
        return self.enabled and pid == PID and generation == self.generation

    def inspect(self, pid):
        return {'state': 'available', 'profile_id': pid}


class PlanRunner:
    def __init__(self):
        self.calls, self.turns = [], []
        self.reply = None

    def __call__(self, argv, raw, **kwargs):
        packet = json.loads(raw)
        body = packet['body']
        assert set(body) <= {'model', 'instructions', 'input', 'store', 'stream', 'reasoning'}
        assert body['store'] is False and body['stream'] is True
        selected_token = getattr(self, 'tokens', {}).get(body['model'], TOKEN)
        assert kwargs['environment'] == {'ATTUNE_CHATGPT_ACCESS_TOKEN': selected_token}
        assert tuple(argv[1:3]) == ('-I', '-S')
        attempt = json.loads(body['input'][0]['content'])['attempt']
        turn = json.loads(attempt['task']['objective'])
        self.turns.append(copy.deepcopy(turn))
        self.calls.append(copy.deepcopy(body))
        if self.reply:
            text = self.reply(attempt, turn, kwargs)
        elif 'snapshot' in turn:
            text = canonical({'verdict': 'uncertain', 'summary': 'Inert source review only.',
                              'evidence': [{'path': 'x.py', 'line': 1, 'detail': 'Frozen input.'}]})
        elif 'request_digest' in turn:
            text = canonical({'schema_version': 1, 'request_digest': turn['request_digest'],
                              'action': {'kind': 'final', 'text': 'Inert accepted assessment.'}})
        else:
            text = 'The frozen source supports only this inert fixture claim; no live review occurred.'
        return ProcessResult(tuple(argv), 0, canonical(provider_response(body['model'], text)), '')


@pytest.fixture
def plan(monkeypatch):
    from attune_harness import plan_exchange, plan_profiles
    import test_openai_funding
    profiles, runner = Profiles(), PlanRunner()
    monkeypatch.setattr(plan_profiles, 'store', lambda: profiles)
    monkeypatch.setattr(plan_exchange, 'runtime', lambda: dict(RUNTIME))
    monkeypatch.setattr(plan_exchange, 'invoke', runner)
    monkeypatch.setattr(test_openai_funding, 'seat', lambda model='fixture-plan-model', credential=None: seat(model))
    monkeypatch.setenv('OPENAI_API_KEY', 'ambient_api_key_must_not_cross')
    monkeypatch.setenv('HTTP_PROXY', 'http://inert.invalid')
    monkeypatch.setenv('OPENAI_BASE_URL', 'http://inert.invalid')
    def forbidden(*a, **kw): pytest.fail('Unexpected native or live process')
    monkeypatch.setattr(consultation, 'NativeExchange', forbidden)
    monkeypatch.setattr(importlib.import_module('attune_harness.review_participants'), 'NativeExchange', forbidden)
    return SimpleNamespace(profiles=profiles, runner=runner)


def prepare_consultation(tmp_path, second=False, mixed=False):
    root = tmp_path / 'source'; root.mkdir(); (root/'x.py').write_text('x=1\n')
    config = {'schema_version': 1, 'question': 'Inspect frozen source',
              'author': {'provider': 'codex', 'model': 'inert-author'},
              'participants': {'reviewer': seat()}, 'rounds': 1}
    if second:
        config['participants']['critic'] = (dict(adapter='openai', identity=dict(provider='openai', model='inert-api'),
            timeout=10, funding=dict(mode='api', credential_env='PLAN_TEST_API_KEY')) if mixed else seat('inert-second'))
    directory = tmp_path/'run'
    record = consultation.prepare('roundtable' if second else 'source-review', root, ['x.py'], config, directory)
    return directory, record


def test_subscription_source_review_and_local_inspection(tmp_path, plan, capsys):
    directory, record = prepare_consultation(tmp_path)
    assert plan.profiles.resolutions == 0
    from attune_harness.consultation_preflight import preflight
    checked = preflight(record['contract']['configuration'])
    assert checked['reviewer']['binary'] is None and plan.profiles.resolutions == 0
    completed = consultation.run(directory, record['contract_digest'], allow_external=True)
    assert completed['status'] == 'completed', completed.get('error')
    assert len(plan.runner.calls) == 1
    event = completed['events'][0]
    assert event['funding']['profile'] == 'participant-funding-v2'
    assert event['funding']['observed'] == 'subscription' and not event['funding']['api_authorized']
    assert TOKEN not in canonical(completed) and 'ambient_api_key_must_not_cross' not in canonical(completed)
    assert main(['source-review', 'status', str(directory)]) == 0
    capsys.readouterr()


def test_roundtable_resume_only_resolves_pending_profiles(tmp_path, plan):
    directory, record = prepare_consultation(tmp_path, second=True)
    paused = consultation.run(directory, record['contract_digest'], allow_external=True, max_operations=1)
    assert paused['status'] == 'paused' and len(plan.runner.calls) == 1
    assert any(e['state'] == 'completed' for e in paused['events'])
    completed = consultation.run(directory, record['contract_digest'], allow_external=True)
    assert completed['status'] == 'completed' and len(plan.runner.calls) == 2
    assert plan.profiles.resolutions == 2


def test_missing_api_grant_prevents_plan_sibling_inference(tmp_path, plan, monkeypatch):
    directory, record = prepare_consultation(tmp_path, second=True, mixed=True)
    monkeypatch.setenv('PLAN_TEST_API_KEY', 'synthetic_api_key_0123456789abcdef')
    api = InertAPI()
    monkeypatch.setattr(importlib.import_module('attune_harness.openai_exchange'), 'invoke', api)
    with pytest.raises(funding.FundingRefused):
        consultation.run(directory, record['contract_digest'], allow_external=True)
    assert not plan.runner.calls and not api.calls and plan.profiles.resolutions == 0
    done = consultation.run(directory, record['contract_digest'], allow_external=True, allow_api_spend=True)
    assert done['status'] == 'completed', done.get('error')
    assert len(plan.runner.calls) == len(api.calls) == 1


@pytest.mark.parametrize('attack', ['rotate', 'disconnect', 'runtime', 'request', 'receipt', 'used', 'lease', 'forged'])
def test_one_use_owner_claim_refuses_changes(tmp_path, plan, monkeypatch, attack):
    with consultation_owner(tmp_path) as (cursor, config, turn):
        admission, raw = issue_capability(cursor, config, turn)
        if attack == 'rotate': plan.profiles.generation = 'e'*32
        elif attack == 'disconnect': plan.profiles.enabled = False
        elif attack == 'runtime':
            monkeypatch.setattr(importlib.import_module('attune_harness.plan_exchange'), 'runtime',
                                lambda: {**RUNTIME, 'worker_profile': 'f'*64})
        elif attack == 'request': raw += ' '
        elif attack == 'receipt': admission.receipt['generation'] = 'e'*32
        elif attack == 'lease': cursor.store._lease_token = object()
        elif attack == 'forged': admission = copy.copy(admission)
        elif attack == 'used':
            funding.claim(admission, config['identity']['model'], raw)
            admission.used = False
        with pytest.raises((ValueError, FeatureUnavailable)):
            PlanExchange(model=config['identity']['model'], cwd=tmp_path, admission=admission)(raw)
        assert plan.runner.calls == []


@pytest.mark.parametrize('evidence', [False, True])
def test_registry_review_owned_plan_and_host_steps(case, plan, evidence):
    from attune_harness.review import review
    change_config(case, lambda v: v['participants'].update(alpha=participant(evidence=evidence)))
    done = review(*case, allow_external=True)
    assert done['status'] == 'completed', done.get('error')
    assert len(plan.runner.calls) == 1
    assert len([e for e in done['events'] if e.get('funding')]) == 1


def test_assessment_pending_resume_and_terminal_replay(case, plan):
    change_config(case, lambda v: v['participants'].update(alpha=participant()))
    draft(case); accepted = response(case[2]); accepted['permissions']['external'] = True
    accept_task(case[2], accepted)
    paused = execute_task(case[2], max_operations=2)
    assert paused['status'] == 'paused' and not plan.runner.calls
    done = execute_task(case[2]); assert done['status'] == 'completed', done['execution'].get('error')
    count = len(plan.runner.calls); plan.profiles.enabled = False
    assert execute_task(case[2])['status'] == 'completed' and len(plan.runner.calls) == count


@pytest.mark.parametrize('phase', ['planning', 'build'])
def test_plan_build_real_owner_pause_resume(work, plan, phase, monkeypatch, capsys):
    if phase == "build" and __import__("os").name != "posix": pytest.skip("POSIX build fixture")
    from attune_harness.work_runtime import demonstration_reply, plan_work
    monkeypatch.setattr(Worker, 'mutation', None); monkeypatch.setattr(Worker, 'seen', [])
    registry = json.loads(work[1].read_text())
    for name in ('local', 'critic'): registry['participants'][name] = participant('inert-' + name)
    work[1].write_text(canonical(registry))
    if phase == 'planning':
        add_critic(work); make(work); directory = work[2]['directory']
        plan.runner.reply = lambda attempt, turn, kw: canonical(demonstration_reply(turn))
        budget = 1
    else:
        _, directory, _ = prepare_build(work)
        def reply(attempt, turn, kw):
            config = read_task(directory)['request']['registry']['participants'][turn['participant_id']]
            fixture = Worker(config, kw['cwd'], profile='feature-build-v1')
            payload = json.loads(json.loads(fixture(canonical({'turn': turn, 'request_digest': digest(turn)})))['action']['text'])
            if turn['role'] == 'worker': payload = {'schema_version': 2, 'files': payload['files']}
            return canonical(payload)
        plan.runner.reply = reply
        budget = 2
    def run(**kw):
        argv = (['plan', '--task-dir', str(directory), '--run'] if phase == 'planning' else ['build', str(directory)])
        argv += ['--allow-external']
        if 'max_operations' in kw: argv += ['--max-operations', str(kw['max_operations'])]
        expected = 1 if kw else 0
        assert main(argv) == expected, capsys.readouterr().out
        capsys.readouterr()
        return read_task(directory)
    paused = run(max_operations=budget)
    assert paused[phase]['status'] == 'paused' and len(plan.runner.calls) == 1
    done = run(); assert done[phase]['status'] == 'completed', done[phase].get('error')
    calls = len(plan.runner.calls); plan.profiles.enabled = False
    assert run()[phase]['status'] == 'completed' and len(plan.runner.calls) == calls


@pytest.mark.skipif(__import__('os').name != 'posix', reason='POSIX frozen repair fixture')
def test_fix_real_effects_and_resume(effect_case, plan):
    config = {'schema_version': 1, 'participants': {n: participant('inert-'+n) for n in ('worker', 'reviewer')}}
    directory = prepare_repair(effect_case, config=config)
    plan.runner.reply = lambda attempt, turn, kw: canonical({
        'schema_version': 1, 'request_digest': turn['request_digest'], 'action': proposal(turn)})
    paused = execute_task(directory, max_operations=2)
    assert paused['status'] == 'paused', paused.get('execution', {}).get('error')
    done = execute_task(directory)
    assert done['status'] == 'completed', done['execution'].get('error')
    assert (effect_case[0]/'app.py').read_text() == 'def add(a,b):\n    return a+b\n'
    count = len(plan.runner.calls); plan.profiles.enabled = False
    assert execute_task(directory)['status'] == 'completed' and len(plan.runner.calls) == count


def test_normalized_identity_and_strict_configuration():
    assert funding.model_key('openai-plan', 'm') == funding.model_key('codex', 'm')
    with pytest.raises(ValueError): funding.validate('openai-plan', {'mode': 'api', 'credential_env': 'KEY'})
    with pytest.raises(ValueError): funding.validate('openai-plan', {'mode': 'subscription'})
    with pytest.raises(ValueError): funding.distinct_api_models([participant('m'), {'adapter': 'codex', 'model': 'm'}])


@pytest.mark.parametrize('first', ['plan', 'api'])
@pytest.mark.parametrize('refusal', ['authority', 'credential'])
def test_registry_mixed_static_precheck_before_profiles_and_inference(case, plan, monkeypatch, first, refusal):
    from attune_harness.review import review
    api_seat = {'adapter': 'openai', 'model': 'inert-api-model', 'timeout': 10,
                'tools': [], 'max_turns': 1, 'max_tool_calls': 0,
                'funding': {'mode': 'api', 'credential_env': 'MIXED_INERT_API_KEY'}}
    selected = (participant(), api_seat) if first == 'plan' else (api_seat, participant())
    change_config(case, lambda v: v['participants'].update(alpha=selected[0], beta=selected[1]))
    api = InertAPI()
    monkeypatch.setattr(importlib.import_module('attune_harness.openai_exchange'), 'invoke', api)
    if refusal == 'authority': monkeypatch.setenv('MIXED_INERT_API_KEY', 'synthetic_mixed_key_0123456789')
    else: monkeypatch.delenv('MIXED_INERT_API_KEY', raising=False)
    refused = review(*case, allow_external=True, allow_api_spend=refusal == 'credential')
    assert refused['status'] == 'paused' and not plan.runner.calls and not api.calls
    assert plan.profiles.resolutions == 0
    assert 'FundingPrecheckRefused' == refused['error']['type']


def test_completed_api_final_replays_without_key_or_spend_while_plan_pending(case, plan, monkeypatch):
    from attune_harness.review import review
    from attune_harness.recovery import resume_review
    api_seat = {'adapter': 'openai', 'model': 'inert-api-model', 'timeout': 10,
                'tools': [], 'max_turns': 1, 'max_tool_calls': 0,
                'funding': {'mode': 'api', 'credential_env': 'MIXED_INERT_API_KEY'}}
    change_config(case, lambda v: v['participants'].update(alpha=api_seat, beta=participant()))
    api = InertAPI()
    monkeypatch.setenv('MIXED_INERT_API_KEY', 'synthetic_mixed_key_0123456789')
    monkeypatch.setattr(importlib.import_module('attune_harness.openai_exchange'), 'invoke', api)
    paused = review(*case, allow_external=True, allow_api_spend=True, max_operations=3)
    assert paused['status'] == 'paused' and len(api.calls) == 1 and not plan.runner.calls
    monkeypatch.delenv('MIXED_INERT_API_KEY')
    done = resume_review(case[2], case[0], case[1], paused['checkpoint_digest'], allow_external=True)
    assert done['status'] == 'completed', done.get('error')
    assert len(api.calls) == len(plan.runner.calls) == 1


@pytest.mark.parametrize('phase', ['planning', 'build'])
def test_mixed_feature_owners_precheck_before_plan(work, plan, phase):
    if phase == 'build' and __import__('os').name != 'posix': pytest.skip('POSIX build fixture')
    from attune_harness.work_runtime import plan_work
    config = json.loads(work[1].read_text())
    config['participants']['local'] = participant('inert-plan')
    config['participants']['critic'] = {'adapter': 'openai', 'model': 'inert-api-model', 'timeout': 10,
        'tools': [], 'max_turns': 1, 'max_tool_calls': 0,
        'funding': {'mode': 'api', 'credential_env': 'MIXED_INERT_API_KEY'}}
    work[1].write_text(canonical(config))
    if phase == 'planning':
        add_critic(work); make(work); directory = work[2]['directory']
        done = plan_work(directory, allow_external=True)
    else:
        _, directory, _ = prepare_build(work)
        done = execute_task(directory, allow_external=True)
    assert done[phase]['status'] == 'paused', done[phase].get('error')
    assert not plan.runner.calls and plan.profiles.resolutions == 0


@pytest.mark.skipif(__import__('os').name != 'posix', reason='POSIX frozen repair fixture')
def test_mixed_repair_prechecks_pending_reviewer(effect_case, plan):
    config = {'schema_version': 1, 'participants': {'worker': participant(), 'reviewer': {
        'adapter': 'openai', 'model': 'inert-api-model', 'timeout': 10, 'tools': [],
        'max_turns': 1, 'max_tool_calls': 0,
        'funding': {'mode': 'api', 'credential_env': 'MIXED_INERT_API_KEY'}}}}
    directory = prepare_repair(effect_case, config=config)
    result = execute_task(directory)
    assert result['status'] == 'paused' and not plan.runner.calls and plan.profiles.resolutions == 0


@pytest.mark.skipif(__import__('os').name != 'posix', reason='POSIX profile-lock doubles')
def test_concurrent_plan_profiles_keep_separate_tokens_and_receipts(tmp_path, plan, monkeypatch):
    import time
    from threading import Barrier
    from attune_harness import plan_profiles, plan_exchange
    from test_plan_profiles import store as private_store, credential
    private = tmp_path/'private'; private.mkdir(mode=0o700)
    profiles, backend, oauth = private_store(private)
    second, other_gen = 'plan_'+'c'*32, 'e'*32
    expiry = time.time()+600
    backend.put(PID, {**credential(), 'generation': GEN, 'expires_at': expiry, 'access_token': TOKEN})
    backend.put(second, {**credential(), 'generation': other_gen, 'expires_at': expiry,
                        'subject': 'other-subject', 'client_id': 'other-client', 'access_token': 'other-inert-token'})
    index = profiles._read(); index['profiles'][PID]['expires_at'] = expiry
    index['profiles'][second] = {**index['profiles'][PID], 'label': 'other', 'generation': other_gen}
    profiles._save(index)
    monkeypatch.setattr(plan_profiles, 'store', lambda: profiles)
    root = tmp_path/'source'; root.mkdir(); (root/'x.py').write_text('x=1\n')
    other = seat('inert-second'); other['funding']['profile_id'] = second
    config = {'schema_version': 1, 'question': 'Inspect frozen source',
        'author': {'provider': 'openai', 'model': 'inert-author'}, 'rounds': 1,
        'participants': {'reviewer': seat(), 'critic': other}}
    directory=tmp_path/'run'; prepared=consultation.prepare('roundtable',root,['x.py'],config,directory)
    plan.runner.tokens = {'inert-second': 'other-inert-token'}
    barrier = Barrier(2)
    def concurrent(*a, **kw):
        barrier.wait(timeout=2)
        return plan.runner(*a, **kw)
    monkeypatch.setattr(plan_exchange, 'invoke', concurrent)
    done=consultation.run(directory,prepared['contract_digest'],allow_external=True)
    assert done['status']=='completed',done.get('error')
    assert len(plan.runner.calls)==2
    assert {e['funding']['profile_id'] for e in done['events']}=={PID,second}
    assert TOKEN not in canonical(done) and 'other-inert-token' not in canonical(done)
