# qualify: platform
"""Browser handoff retains the same local capability and never edits saved work."""
import http.client
from threading import Thread

import pytest
import test_work_contract as contracts
from test_gui import request
from test_gui_decisions import call
from test_gui_release import forms
from attune_harness import gui

work = contracts.work


def test_fixed_browser_target_duplicate_guard_and_no_task_effects(forms, monkeypatch):
    before = {p.name: p.read_bytes() for p in forms.tasks[0].iterdir() if p.is_file()}
    calls = []
    clock = [100.0]
    monkeypatch.setattr(gui.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(gui.webbrowser, 'open', lambda url, **kw: calls.append((url, kw)) or True)
    status, result = call(forms, '/browser/open', {'confirmed': True})
    assert status == 200 and result['requested'] is True
    assert calls == [(forms.launch_url, {'new': 1})]
    assert forms.token not in str(result) and forms.origin not in str(result)
    assert call(forms, '/browser/open', {'confirmed': True}) == (status, result)
    assert len(calls) == 1
    clock[0] += 2
    assert call(forms, '/browser/open', {'confirmed': True})[0] == 200
    assert len(calls) == 2
    assert {p.name: p.read_bytes() for p in forms.tasks[0].iterdir() if p.is_file()} == before
    assert forms.builds is None


@pytest.mark.parametrize('payload', [
    {}, {'confirmed': False}, {'confirmed': 1}, {'confirmed': 'true'},
    {'confirmed': None}, {'confirmed': True, 'url': 'https://foreign.example'},
    {'confirmed': True, 'command': 'echo forbidden'},
])
def test_browser_target_and_confirmation_cannot_be_supplied(forms, monkeypatch, payload):
    monkeypatch.setattr(gui.webbrowser, 'open', lambda *a, **kw: pytest.fail('Refusal must precede browser launch'))
    assert call(forms, '/browser/open', payload)[0] == 409


@pytest.mark.parametrize('headers,token,expected', [
    ({}, False, 403), ({'X-Attune-Session': 'wrong'}, True, 403),
    ({'Origin': 'https://foreign.example'}, True, 403),
    ({'Origin': ''}, True, 403), ({'Host': 'foreign.example'}, True, 403),
    ({'Content-Type': 'text/plain'}, True, 415),
    ({'Transfer-Encoding': 'chunked'}, True, 413),
])
def test_browser_launch_keeps_local_http_boundary(forms, monkeypatch, headers, token, expected):
    monkeypatch.setattr(gui.webbrowser, 'open', lambda *a, **kw: pytest.fail('Refusal must precede browser launch'))
    assert call(forms, '/browser/open', {'confirmed': True}, headers=headers, token=token)[0] == expected


@pytest.mark.parametrize('duplicate', ['Host', 'Origin', 'X-Attune-Session', 'Content-Length', 'Content-Type'])
def test_browser_launch_refuses_duplicate_boundary_headers(forms, monkeypatch, duplicate):
    monkeypatch.setattr(gui.webbrowser, 'open', lambda *a, **kw: pytest.fail('Duplicate header must refuse before launch'))
    body = b'{"confirmed":true}'
    values = {'Host': forms.origin[7:], 'Origin': forms.origin, 'X-Attune-Session': forms.token,
              'Content-Length': str(len(body)), 'Content-Type': 'application/json'}
    connection = http.client.HTTPConnection('127.0.0.1', forms.server_port, timeout=5)
    connection.putrequest('POST', '/browser/open', skip_host=True)
    for key, value in values.items():
        connection.putheader(key, value)
        if key == duplicate:
            connection.putheader(key, value)
    connection.endheaders(body)
    response = connection.getresponse()
    assert response.status in (403, 413, 415)
    response.read()
    connection.close()


@pytest.mark.parametrize('body', [b'{"confirmed":true,"confirmed":true}', b'[]', b'{', b'\xff'])
def test_browser_launch_refuses_malformed_json(forms, monkeypatch, body):
    monkeypatch.setattr(gui.webbrowser, 'open', lambda *a, **kw: pytest.fail('Malformed JSON must not launch browser'))
    connection = http.client.HTTPConnection('127.0.0.1', forms.server_port, timeout=5)
    connection.request('POST', '/browser/open', body, {'Origin': forms.origin,
                       'X-Attune-Session': forms.token, 'Content-Type': 'application/json'})
    response = connection.getresponse()
    assert response.status == 409
    response.read()
    connection.close()


def test_browser_launch_requires_origin_and_bounded_body(forms, monkeypatch):
    monkeypatch.setattr(gui.webbrowser, 'open', lambda *a, **kw: pytest.fail('Missing origin or oversized body must not launch browser'))
    for headers, body, expected in [
        ({'X-Attune-Session': forms.token, 'Content-Type': 'application/json'}, b'{"confirmed":true}', 403),
        ({'Origin': forms.origin, 'X-Attune-Session': forms.token, 'Content-Type': 'application/json'}, b' ' * 65537, 413),
    ]:
        connection = http.client.HTTPConnection('127.0.0.1', forms.server_port, timeout=5)
        connection.request('POST', '/browser/open', body, headers)
        response = connection.getresponse()
        assert response.status == expected
        response.read()
        connection.close()


@pytest.mark.parametrize('outcome', ['false', 'error', 'oserror'])
def test_browser_failure_offers_private_terminal_fallback(forms, monkeypatch, outcome):
    def refused(*args, **kwargs):
        if outcome == 'error':
            raise gui.webbrowser.Error(forms.launch_url)
        if outcome == 'oserror':
            raise OSError(forms.launch_url)
        return False
    monkeypatch.setattr(gui.webbrowser, 'open', refused)
    status, result = call(forms, '/browser/open', {'confirmed': True})
    assert status == 200 and result['requested'] is False
    assert 'Terminal' in result['message']
    assert forms.token not in str(result)


def test_read_only_browser_handoff_preserves_decision_refusal(work, monkeypatch):
    contracts.make(work)
    path = work[2]['directory']
    before = (path / 'record.json').read_bytes()
    calls = []
    monkeypatch.setattr(gui.webbrowser, 'open', lambda url, **kw: calls.append(url) or True)
    with gui.CompanionServer([path]) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            assert call(server, '/browser/open', {'confirmed': True})[0] == 200
            assert calls == [server.launch_url]
            assert call(server, '/decision/open', {'task': 'forged', 'checkpoint': 'forged'})[0] == 405
            assert request(server, '/browser/open')[0] == 404
            assert call(server, '/browser/open?url=forged', {'confirmed': True})[0] == 404
            assert (path / 'record.json').read_bytes() == before
        finally:
            server.shutdown()
            thread.join(timeout=2)
