"""Real owner snapshots behind a read-only loopback boundary; no model calls."""
import http.client
from threading import Thread

import pytest
import test_work_contract as contracts
from attune_harness import gui

work = contracts.work

@pytest.fixture
def companion(work):
    contracts.make(work)
    with gui.CompanionServer([work[2]['directory']]) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server
        server.shutdown()
        thread.join(timeout=2)

def request(server, path='/snapshot', *, token=True, headers=None, method='GET'):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
    fields = {'X-Attune-Session': server.token} if token else {}
    fields.update(headers or {})
    connection.request(method, path, headers=fields)
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read().decode()
    connection.close()
    return result

def test_read_only_snapshot_is_owner_rendered_and_records_unchanged(companion):
    record = companion.tasks[0] / 'record.json'
    before = record.read_bytes()
    status, headers, body = request(companion)
    assert status == 200
    assert 'Export every finding' in body
    assert 'work is not yet accepted' in body
    assert headers['Cache-Control'] == 'no-store'
    assert 'frame-ancestors' in headers['Content-Security-Policy']
    assert record.read_bytes() == before
    assert request(companion, method='POST')[0] == 405
    assert record.read_bytes() == before

@pytest.mark.parametrize('kwargs', [
    {'token': False},
    {'headers': {'X-Attune-Session': 'wrong'}},
    {'headers': {'X-Attune-Session': 'é'}},
    {'headers': {'Origin': 'https://foreign.example'}},
    {'headers': {'Host': 'foreign.example'}},
])
def test_foreign_or_unauthenticated_read_refused(companion, kwargs):
    status, _, body = request(companion, **kwargs)
    assert status == 403
    assert 'Export every finding' not in body

@pytest.mark.parametrize('path', ['/snapshot?path=/etc/passwd','/../../record.json','/unknown'])
def test_browser_cannot_select_files(companion, path):
    assert request(companion, path)[0] == 404

def test_refresh_reinspects_changed_owner(companion):
    record = companion.tasks[0] / 'record.json'
    record.write_text('{}')
    status, _, body = request(companion)
    assert status == 409
    assert 'Export every finding' not in body

def test_static_bootstrap_contains_no_task_or_token(companion):
    status, _, body = request(companion, '/', token=False)
    assert status == 200
    assert companion.token not in body
    assert 'Export every finding' not in body

def test_registration_bounds(work):
    with pytest.raises(ValueError):
        gui.CompanionServer([])
    with pytest.raises(ValueError):
        gui.CompanionServer(['relative'])
    contracts.make(work)
    with pytest.raises(ValueError):
        gui.CompanionServer([work[2]['directory']] * 2)


@pytest.mark.parametrize('mode', ['manual', 'browser-false', 'browser-error'])
def test_launcher_exposes_authenticated_fallback(companion, monkeypatch, capsys, mode):
    class ExistingServer:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            pass
        origin = companion.origin
        launch_url = companion.launch_url
        def serve_forever(self):
            raise KeyboardInterrupt
    monkeypatch.setattr(gui, 'CompanionServer', lambda *args, **kwargs: ExistingServer())
    def open_browser(url):
        assert mode != 'manual', 'Manual launch must not open a browser'
        assert url == companion.launch_url
        if mode == 'browser-error':
            raise gui.webbrowser.Error('No browser')
        return False
    monkeypatch.setattr(gui.webbrowser, 'open', open_browser)
    args = ['--task', str(companion.tasks[0])]
    if mode == 'manual':
        args.append('--no-open')
    assert gui.main(args) == 0
    output = capsys.readouterr()
    assert companion.launch_url in output.out
    if mode != 'manual':
        assert 'Browser did not open' in output.err
    assert request(companion)[0] == 200
