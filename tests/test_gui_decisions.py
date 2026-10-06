# qualify: platform
"""Real owner journeys and the write boundary, without participants or paid calls."""
import copy
import http.client
import json
import socket
import time
from threading import Thread

import pytest

pytestmark = pytest.mark.usefixtures('gui_development_profile')

import test_work_contract as contracts
from attune_harness import gui, work_contract, work_decisions
from attune_harness.gui_decisions import Decisions
from attune_harness.task_contract import read_task
from test_gui import request

work = contracts.work


@pytest.fixture
def draft(work):
    work[2]['intent'].update(goal=None, acceptance=[])
    work[2]['choices'] = [contracts.choice()]
    contracts.make(work)
    with gui.CompanionServer([work[2]['directory']], edit=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server
        server.shutdown()
        thread.join(timeout=2)


def call(server, endpoint, payload, *, headers=None, token=True):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
    fields = {'Origin': server.origin, 'Content-Type': 'application/json'}
    if token:
        fields['X-Attune-Session'] = server.token
    fields.update(headers or {})
    connection.request('POST', endpoint, json.dumps(payload), fields)
    response = connection.getresponse()
    raw = response.read().decode()
    result = response.status, json.loads(raw) if response.status == 200 else raw
    connection.close()
    return result


def selected(server):
    status, _, raw = request(server, '/workspace')
    assert status == 200
    value = json.loads(raw)
    assert value['editable'] is True
    return value['tasks'][0]


def open_form(server):
    task = selected(server)
    status, form = call(server, '/decision/open', {k: task[k] for k in ('task', 'checkpoint')})
    assert status == 200, form
    return form


def submission(form, response):
    return {k: form[k] for k in ('task', 'checkpoint', 'decision')} | {'response': response}


def answer_all(server):
    form = open_form(server)
    fields = form['display']['definition']['fields']
    response = {'answers': {'answer_0': 'Export all findings', 'answer_1': 'Every finding survives export',
                            'answer_2': fields[2]['options'][0]}}
    assert call(server, '/decision/submit', submission(form, response))[0] == 200


def test_real_partial_intake_choices_acceptance_and_reload(draft):
    path = draft.tasks[0]
    before = (path / 'record.json').read_bytes()
    assert selected(draft)['available']
    assert selected(draft)['heading'] == 'Draft saved — more answers needed'
    assert (path / 'record.json').read_bytes() == before
    assert not (path / 'decision.json').exists()  # GET creates no decision.
    shown = open_form(draft)
    assert shown['display']['kind'] == 'questions'
    assert 'response_template' not in shown['display']
    answer = submission(shown, {'answers': {'answer_0': 'Export all findings'}})
    assert call(draft, '/decision/submit', answer)[0] == 200
    assert selected(draft)['heading'] == 'Draft saved — more answers needed'
    assert call(draft, '/decision/submit', answer)[0] == 409
    shown = open_form(draft)
    fields = shown['display']['definition']['fields']
    assert 'observable' in fields[0]['text']  # answer_0 now means acceptance.
    assert 'Counter-case' in fields[1]['options'][0]
    answers = {'answer_0': 'Every finding survives export', 'answer_1': fields[1]['options'][0]}
    assert call(draft, '/decision/submit', submission(shown, {'answers': answers}))[0] == 200
    record = read_task(path)
    assert record['request']['choices'][0]['selected'] == 'jsonl'
    assert record['status'] == 'draft'
    assert selected(draft)['heading'] == 'Draft saved — ready for review'
    shown = open_form(draft)
    assert shown['display']['kind'] == 'spec'
    assert any(a['id'] == 'approve_task' for a in shown['display']['actions'])
    payload = submission(shown, {'action': 'approve_task', 'confirmed': True})
    status, result = call(draft, '/decision/submit', payload)
    assert status == 200, result
    assert 'Intent accepted' in result['message']
    assert result['heading'] == 'Intent accepted'
    assert read_task(path)['status'] == 'accepted'
    assert call(draft, '/decision/submit', payload)[0] == 409
    assert selected(draft)['available'] is False
    assert selected(draft)['heading'] == 'Intent accepted'
    with gui.CompanionServer([path], edit=True) as restarted:
        assert restarted.decisions.inspect()[0]['status'] == 'accepted'
    assert 'planning' not in read_task(path) and 'build' not in read_task(path)


def test_two_tabs_replace_preview_and_restart_does_not_restore_authority(draft):
    first = open_form(draft)
    second = open_form(draft)
    payload = submission(first, {'answers': {'answer_0': 'Old tab'}})
    assert call(draft, '/decision/submit', payload)[0] == 409
    assert call(draft, '/decision/submit', submission(second, {'answers': {'answer_0': 'Current tab'}}))[0] == 200
    shown = open_form(draft)
    other = Decisions(draft.tasks)
    try:
        with pytest.raises(ValueError, match='Unknown registered task'):
            other.submit(**submission(shown, {'answers': {'answer_0': 'After restart'}}))
    finally:
        other.close()


@pytest.mark.parametrize('drift', ['source', 'config', 'revision', 'retained'])
def test_drift_refuses_submission_without_acceptance(draft, work, drift):
    answer_all(draft)
    shown = open_form(draft)
    if drift == 'source':
        (work[0] / 'source.py').write_text('changed')
    elif drift == 'config':
        work[1].write_text(work[1].read_text() + '\n')
    elif drift == 'revision':
        work_contract.revise_work(draft.tasks[0], checkpoint=shown['checkpoint'], changes={'intent': {'goal': 'Changed goal'}})
    else:
        saved = json.loads((draft.tasks[0] / 'decision.json').read_text())
        display = copy.deepcopy(saved['display'])
        display['title'] = 'Replaced by another collector'
        work_decisions.retain_decision(read_task(draft.tasks[0]), display)
    status, _ = call(draft, '/decision/submit', submission(shown, {'action': 'approve_task', 'confirmed': True}))
    assert status == 409
    assert read_task(draft.tasks[0])['status'] == 'draft'
    if drift in ('source', 'config'):
        card = selected(draft)
        assert not card['available']
        assert card['heading'] == 'Draft saved'


def test_failed_persistence_after_collection_is_not_replayed(draft, monkeypatch):
    answer_all(draft)
    shown = open_form(draft)
    def fail(*args, **kwargs):
        raise OSError('Disk full')
    monkeypatch.setattr(work_decisions, 'retain_decision', fail)
    payload = submission(shown, {'action': 'approve_task', 'confirmed': True})
    status, message = call(draft, '/decision/submit', payload)
    assert status == 409 and 'Disk full' in message
    assert call(draft, '/decision/submit', payload)[0] == 409
    assert read_task(draft.tasks[0])['status'] == 'draft'


@pytest.mark.parametrize('headers,token,code', [
    ({'Origin': 'https://foreign.example'}, True, 403),
    ({'Origin': 'null'}, True, 403),
    ({'Host': 'foreign.example'}, True, 403),
    ({}, False, 403),
    ({'Content-Type': 'text/plain'}, True, 415),
    ({'Transfer-Encoding': 'chunked'}, True, 413),
    ({'Content-Length': '65537'}, True, 413),
])
def test_write_boundary_refuses_before_mutation(draft, headers, token, code):
    task = selected(draft)
    status, _ = call(draft, '/decision/open', {k: task[k] for k in ('task', 'checkpoint')}, headers=headers, token=token)
    assert status == code
    assert not (draft.tasks[0] / 'decision.json').exists()


def test_missing_origin_and_duplicate_headers_refused(draft):
    task = selected(draft)
    payload = json.dumps({k: task[k] for k in ('task', 'checkpoint')})
    for duplicate in (None, 'Origin', 'Host', 'Content-Length', 'X-Attune-Session'):
        connection = http.client.HTTPConnection('127.0.0.1', draft.server_port)
        connection.putrequest('POST', '/decision/open')
        headers = {'Content-Length': str(len(payload)), 'Content-Type': 'application/json', 'X-Attune-Session': draft.token}
        if duplicate is not None:
            headers['Origin'] = draft.origin
        for key, value in headers.items():
            connection.putheader(key, value)
        if duplicate:
            connection.putheader(duplicate, headers.get(duplicate, draft.origin.removeprefix('http://')))
        connection.endheaders(payload.encode())
        response = connection.getresponse()
        assert response.status in (403, 413)
        response.read()
        connection.close()
    assert not (draft.tasks[0] / 'decision.json').exists()


@pytest.mark.parametrize('payload', [[], {}, {'task': '/etc/passwd', 'checkpoint': 'anything'},
                                     {'task': [], 'checkpoint': 'anything'},
                                     {'task': 'x', 'checkpoint': 'anything', 'path': '/tmp'}])
def test_browser_cannot_supply_paths_or_owner_bindings(draft, payload):
    assert call(draft, '/decision/open', payload)[0] == 409
    assert not (draft.tasks[0] / 'decision.json').exists()


def test_empty_answers_and_forged_action_consume_only_live_form(draft):
    shown = open_form(draft)
    assert call(draft, '/decision/submit', submission(shown, {'answers': {}}))[0] == 409
    assert call(draft, '/decision/submit', submission(shown, {'answers': {'answer_0': 'later'}}))[0] == 409
    answer_all(draft)
    shown = open_form(draft)
    assert call(draft, '/decision/submit', submission(shown, {'action': [], 'confirmed': True}))[0] == 409
    assert read_task(draft.tasks[0])['status'] == 'draft'


def test_owner_refusal_for_running_drafts_is_adapted(work):
    # Predicate test supplements actual owner journeys; no fabricated record is saved.
    record = contracts.make(work)
    for member in ('planning', 'build'):
        with pytest.raises(ValueError, match='Resolve or stage'):
            Decisions._draft({**record, member: {}})


def test_task_symlink_replacement_refused(draft, tmp_path):
    task = selected(draft)
    path = draft.tasks[0]
    moved = tmp_path / 'moved'
    path.rename(moved)
    try:
        path.symlink_to(moved, target_is_directory=True)
    except OSError:
        pytest.skip('Directory symlink privilege unavailable on this platform')
    assert call(draft, '/decision/open', {k: task[k] for k in ('task', 'checkpoint')})[0] == 409
    assert selected(draft)['available'] is False


def test_auto_run_is_not_a_gui_action(draft):
    answer_all(draft)
    shown = open_form(draft)
    assert {a['id'] for a in shown['display']['actions']} == {'approve_task', 'redo_task'}
    assert shown['summary']['intent']['goal'] == 'Export all findings'
    status, _ = call(draft, '/decision/submit', submission(shown, {'action': 'auto_run_remaining', 'confirmed': True}))
    assert status == 409
    assert read_task(draft.tasks[0])['status'] == 'draft'


def test_reconsideration_records_response_without_accepting(draft):
    answer_all(draft)
    shown = open_form(draft)
    status, value = call(draft, '/decision/submit', submission(shown, {'action': 'redo_task', 'confirmed': True}))
    assert status == 200 and 'remains unaccepted' in value['message']
    assert read_task(draft.tasks[0])['status'] == 'draft'
    assert json.loads((draft.tasks[0] / 'decision.json').read_text())['response']['action'] == 'redo_task'


def test_material_answer_survives_intake_review_and_acceptance(work):
    question = {'id': 'audience', 'question': 'Who consumes the export?',
                'answer': None, 'material': True}
    work[2]['intent']['questions'] = [question]
    contracts.make(work)
    with gui.CompanionServer([work[2]['directory']], edit=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            shown = open_form(server)
            assert shown['display']['kind'] == 'questions'
            assert call(server, '/decision/submit', submission(shown, {
                'answers': {'answer_0': 'CLI users <not HTML>'}}))[0] == 200
            shown = open_form(server)
            assert shown['display']['kind'] == 'spec'
            expected = question | {'answer': 'CLI users <not HTML>'}
            assert shown['summary']['intent']['questions'] == [expected]
            status, _ = call(server, '/decision/submit', submission(shown, {
                'action': 'approve_task', 'confirmed': True}))
            assert status == 200
            record = read_task(server.tasks[0])
            assert record['status'] == 'accepted'
            assert record['request']['intent']['questions'] == [expected]
        finally:
            server.shutdown()
            thread.join(timeout=2)


def test_early_refusal_delivers_response_before_delayed_body(draft):
    # Split headers/body like a slow client: rejection must arrive without
    # waiting for the body, yet permit the already-in-flight bytes to drain.
    with socket.create_connection(('127.0.0.1', draft.server_port), timeout=2) as client:
        client.sendall(b'POST /decision/open HTTP/1.1\r\nHost: foreign.example\r\nContent-Length: 4\r\n\r\n')
        response = http.client.HTTPResponse(client)
        response.begin()
        assert response.status == 403
        assert response.getheader('Connection') == 'close'
        assert b'Unrecognized local host' in response.read()
        client.sendall(b'null')
        client.shutdown(socket.SHUT_WR)
    assert not (draft.tasks[0] / 'decision.json').exists()
    assert selected(draft)['available']


def test_early_refusal_does_not_wait_indefinitely_for_body(draft):
    with socket.create_connection(('127.0.0.1', draft.server_port), timeout=2) as client:
        client.sendall(b'POST /decision/open HTTP/1.1\r\nHost: foreign.example\r\nContent-Length: 4\r\n\r\n')
        response = http.client.HTTPResponse(client)
        response.begin()
        assert response.status == 403
        response.read()
        start = time.monotonic()
        assert selected(draft)['available']
        assert time.monotonic() - start < 2
    assert not (draft.tasks[0] / 'decision.json').exists()
