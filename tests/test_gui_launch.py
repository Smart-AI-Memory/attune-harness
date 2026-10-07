# qualify: platform
"""Structured opening authenticates to the real server without opening a browser."""
import http.client
import json
from threading import Thread
from urllib.parse import urlsplit

import pytest
import test_work_contract as contracts
from attune_harness import gui

work = contracts.work


@pytest.mark.parametrize('manual', [False, True])
@pytest.mark.parametrize('editable,builds', [(False, False), (True, False), (True, True)])
def test_structured_launcher_authenticates_without_opening_browser(
        work, monkeypatch, capsys, request, editable, manual, builds):
    if builds:
        # This test-only profile does not qualify release build availability.
        request.getfixturevalue('gui_development_profile')
        from attune_harness import work_build
        monkeypatch.setattr(work_build, 'build_work', lambda *_a, **_k:
                            pytest.fail('Opening forms must not dispatch work'))
    contracts.make(work)
    task = work[2]['directory']
    before = (task / 'record.json').read_bytes()
    launches = []

    def external_browser(*_args, **_kwargs):
        pytest.fail('Structured launch must not open an external browser')

    def serve_one_request(server):
        output = capsys.readouterr()
        assert output.err == ''
        assert len(output.out.splitlines()) == 1
        launch = json.loads(output.out)
        launches.append(launch)
        assert launch['type'] == 'attune-harness.browser-launch'
        assert launch['version'] == 1
        assert launch['editable'] is editable
        assert launch['task_count'] == 1
        assert launch['execution_enabled'] is builds
        url = urlsplit(launch['launch_url'])
        assert url.scheme == 'http'
        assert url.hostname == '127.0.0.1'
        assert launch['origin'] == server.origin
        assert url.port == server.server_port
        assert url.path == '/' and not url.query
        assert url.fragment == server.token

        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        try:
            connection.request('GET', '/workspace',
                               headers={'X-Attune-Session': url.fragment})
            response = connection.getresponse()
            assert response.status == 200
            workspace = json.loads(response.read())
            assert workspace['editable'] is editable
            assert all(('build' in item) is builds for item in workspace['tasks'])
            assert response.getheader('Cache-Control') == 'no-store'
            assert "frame-ancestors 'none'" in response.getheader(
                'Content-Security-Policy')
        finally:
            connection.close()
            thread.join(timeout=2)
        assert not thread.is_alive()
        raise KeyboardInterrupt

    monkeypatch.setattr(gui.webbrowser, 'open', external_browser)
    monkeypatch.setattr(gui.CompanionServer, 'serve_forever', serve_one_request)
    args = ['--task', str(task), '--launch-json']
    if editable:
        args.append('--edit')
    if manual:
        args.append('--no-open')
    if builds:
        args.append('--allow-build-commands')
    assert gui.main(args) == 0
    assert len(launches) == 1
    assert capsys.readouterr().out == ''
    assert (task / 'record.json').read_bytes() == before


def test_release_structured_build_flag_refuses_before_private_output(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail('Release build refusal must precede listener or browser effects')

    monkeypatch.setattr(gui.HTTPServer, '__init__', forbidden)
    monkeypatch.setattr(gui.task_view, 'inspect_saved_tasks', forbidden)
    monkeypatch.setattr(gui.webbrowser, 'open', forbidden)
    assert gui.main(['--task', '/not-a-registered-harness-task', '--edit',
                     '--allow-build-commands', '--launch-json']) == 2
    output = capsys.readouterr()
    assert not output.out and 'deferred to 1.4.0' in output.err


@pytest.mark.parametrize('task', ['relative', '/not-a-registered-harness-task'])
def test_invalid_task_emits_no_private_launch_record(task, capsys):
    with pytest.raises(ValueError):
        gui.main(['--task', task, '--launch-json'])
    assert capsys.readouterr().out == ''
