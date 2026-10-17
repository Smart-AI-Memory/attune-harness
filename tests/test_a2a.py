import copy
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
import secrets
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from attune_harness import Check, Status, Task
from attune_harness.adapters import Attempt, JsonParticipant
from attune_harness.a2a import A2AExchange, LocalPeer, PeerError, ProtocolError, inspect_exchange
from attune_harness.review_contract import digest
from attune_harness.review_store import PersistenceError, read_record

ROOT = Path(__file__).resolve().parent.parent


def _peer_executable():
    """Bind an existing base interpreter; the Harness client stays in its venv."""
    base = Path(sys.base_prefix).resolve(strict=True)
    relative = 'python.exe' if os.name == 'nt' else f'bin/python{sys.version_info.major}.{sys.version_info.minor}'
    executable = (base / relative).resolve(strict=True)
    info = executable.stat()
    assert stat.S_ISREG(info.st_mode), 'Peer interpreter is not a regular file'
    profile = {
        'executable': os.path.normcase(str(executable)),
        'base': os.path.normcase(str(base)),
        'version': list(sys.version_info),
        'file': [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns],
        'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
    }
    after = executable.stat()
    assert profile['file'] == [after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns], 'Peer interpreter changed'
    return profile


_PEER_BOOT = r'''
import hashlib, json, os, runpy, socket, sys
from pathlib import Path

route, arguments = json.loads(sys.argv[1]), json.loads(sys.argv[2])
executable = Path(sys.executable).resolve(strict=True)
info = executable.stat()
profile = {
    'token': route['token'], 'pid': os.getpid(),
    'executable': os.path.normcase(str(executable)),
    'base': os.path.normcase(str(Path(sys.base_prefix).resolve(strict=True))),
    'prefix': os.path.normcase(str(Path(sys.prefix).resolve(strict=True))),
    'version': list(sys.version_info),
    'file': [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns],
    'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
}
channel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
channel_closed = False

def close_channel(primary=None):
    global channel_closed
    if channel_closed:
        return
    channel_closed = True
    try:
        channel.close()
    except BaseException as error:
        if primary is None:
            raise
        try:
            primary._a2a_cleanup_errors = (error,)
        except BaseException:
            pass

try:
    channel.settimeout(5)
    channel.connect(('127.0.0.1', route['port']))
    channel.sendall(json.dumps(profile).encode('utf-8') + b'\n')
except BaseException as error:
    close_channel(error)
    raise
original = sys.stdout

class Readiness:
    def __init__(self):
        self.pending = ''
        self.closed = False

    def write(self, value):
        if self.closed:
            return original.write(value)
        self.pending += value
        if '\n' in self.pending:
            line, rest = self.pending.split('\n', 1)
            self.closed = True
            try:
                channel.sendall((line + '\n').encode('utf-8'))
            except BaseException as error:
                close_channel(error)
                raise
            else:
                close_channel()
            sys.stdout = original
            if rest:
                original.write(rest)
        return len(value)

    def flush(self):
        if self.closed:
            original.flush()

readiness = Readiness()
sys.stdout = readiness
if route['deny_resolver']:
    def unavailable(*args, **kwargs):
        raise AssertionError("loopback fixture invoked hostname resolution")
    socket.getfqdn = unavailable
sys.argv = arguments
primary = None
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except BaseException as error:
    primary = error
    raise
finally:
    sys.stdout = original
    if not readiness.closed:
        readiness.closed = True
        close_channel(primary)
'''


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    assert remaining > 0, 'Peer did not start'
    return remaining


def _peer_line(connection, process, expected, token, deadline):
    """One bounded socket stream carries identity, then the peer's actual line."""
    raw = bytearray()
    while True:
        connection.settimeout(_remaining(deadline))
        part = connection.recv(4096)
        if not part:
            break
        raw.extend(part)
        assert len(raw) <= 65_536, 'Peer readiness exceeded its fixture bound'
    header, separator, line = bytes(raw).partition(b'\n')
    assert separator, 'Peer did not start'
    profile = json.loads(header)
    assert profile == {**expected, 'prefix': expected['base'], 'token': token,
                       'pid': process.pid}, 'Peer interpreter identity mismatch'
    _remaining(deadline)
    if not line:
        return ''
    assert line.endswith(b'\n') and line.count(b'\n') == 1, 'Peer did not start'
    decoded = line.decode('utf-8')
    _remaining(deadline)
    return decoded


def _dispose_peer(actions, primary=None):
    """Attempt each owned cleanup once without replacing an existing failure."""
    errors = []
    for action in actions:
        try:
            action()
        except BaseException as error:
            errors.append(error)
    if errors and primary is not None:
        # Keep the original exception and its cause, with honest cleanup detail.
        try:
            primary._a2a_cleanup_errors = getattr(primary, '_a2a_cleanup_errors', ()) + tuple(errors)
        except BaseException:
            pass
    elif errors:
        try:
            errors[0]._a2a_cleanup_errors = tuple(errors[1:])
        except BaseException:
            pass
        raise errors[0]


@contextmanager
def _running_peer(folder, arguments, *, deny_resolver=False, communicate=False):
    """Own one direct peer, its relay and the retained stderr diagnostic."""
    expected = _peer_executable()
    sockets = []
    error = process = None
    primary = None
    try:
        error = (folder / 'stderr.txt').open('w', encoding='utf-8')
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockets.append(listener)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        token = secrets.token_hex(32)
        route = {'port': listener.getsockname()[1], 'token': token,
                 'deny_resolver': deny_resolver}
        deadline = time.monotonic() + 5
        process = subprocess.Popen(
            [expected['executable'], '-I', '-c', _PEER_BOOT,
             json.dumps(route), json.dumps(arguments)],
            stdout=subprocess.PIPE, stderr=error, text=True)
        listener.settimeout(_remaining(deadline))
        connection, _ = listener.accept()
        sockets.append(connection)
        line = _peer_line(connection, process, expected, token, deadline)
        actions = [owned.close for owned in reversed(sockets)]
        sockets.clear()  # An attempted close is never blindly repeated.
        _dispose_peer(actions)
        _remaining(deadline)
        yield process, error, line
    except BaseException as failure:
        primary = failure
        raise
    finally:
        actions = []
        if process is not None:
            actions.append(process.terminate)
            if communicate:
                actions.append(lambda: process.communicate(timeout=5))
            else:
                actions.append(lambda: process.wait(timeout=5))
            actions.append(lambda: process.stdout.close() if not process.stdout.closed else None)
        actions.extend(owned.close for owned in reversed(sockets))
        sockets.clear()
        if error is not None:
            actions.append(error.close)
        _dispose_peer(actions, primary)


@pytest.fixture
def peer_factory(tmp_path):
    processes = []
    with ExitStack() as peers:
        def create(fault='none', hold=False, operations=None):
            folder = tmp_path / str(len(processes))
            folder.mkdir()
            log = folder / 'peer.json'
            process, error, line = peers.enter_context(_running_peer(
                folder, [str(ROOT / 'examples/a2a/peer.py'), '--log', str(log),
                         '--fault', fault, *(['--hold'] if hold else [])]))
            processes.append((process, error))
            assert line, f"Peer did not start; stderr retained at {folder / 'stderr.txt'}"
            ready = json.loads(line)
            peer = LocalPeer(ready['endpoint'], ready['card_digest'], ready['card']['name'],
                             **({'operations': operations} if operations is not None else {}))
            attempt = Attempt(Task('sum', 'Compute 2 + 2', ('Return the sum as a decimal integer',)),
                              'attempt-1', 'requirements-v1', 'independent-peer', 'worker', 'a2a-1.0-local')
            return peer, attempt, folder / 'run', log
        yield create


def start(case, **kwargs):
    peer, attempt, directory, _ = case
    exchange = A2AExchange(attempt, peer, directory, **kwargs)
    participant = JsonParticipant(attempt, exchange)
    receipt = participant.execute(lambda task, output: Check(output.text == '4', 'Independent integer sum equals 4'))
    return exchange, receipt.receipt


def events(case):
    return json.loads(case[3].read_text(encoding='utf-8'))['events']


def test_independent_peer_roundtrip_and_late_cancel(peer_factory):
    case = peer_factory()
    exchange, receipt = start(case)
    assert receipt.status == Status.VERIFIED and receipt.output.text == '4'
    saved = read_record(case[2])
    assert saved['status'] == 'completed' and saved['artifact_digest']
    assert saved['remote_task']['id'] != case[1].task.task_id
    assert [e['operation'] for e in saved['events']] == ['SendMessage', 'GetTask']
    assert all(e.get('version_header', '1.0') == '1.0' for e in events(case))
    before = events(case)
    assert exchange.cancel()['status'] == 'completed'
    assert events(case) == before
    with pytest.raises(RuntimeError, match='already attempted'):
        exchange(case[1].request())


def test_transport_completion_is_not_verified_answer(peer_factory):
    case = peer_factory('wrong_answer')
    _, receipt = start(case)
    assert receipt.status == Status.REJECTED
    assert read_record(case[2])['status'] == 'completed'


@pytest.mark.parametrize('fault', ['wrong_rpc', 'wrong_task', 'wrong_digest', 'unknown_state', 'bad_artifact', 'url_artifact'])
def test_uncorrelated_and_unsupported_results_never_complete(peer_factory, fault):
    case = peer_factory(fault)
    _, receipt = start(case)
    assert receipt.status == Status.FAILED
    saved = read_record(case[2])
    assert saved['status'] == 'unresolved' and 'response' not in saved
    assert saved['events'][-1]['state'] == 'pending'


@pytest.mark.parametrize('fault,code', [('denied', 403), ('auth_required', 401)])
def test_http_access_denial_has_no_fallback(peer_factory, fault, code):
    case = peer_factory(fault)
    _, receipt = start(case)
    assert receipt.status == Status.FAILED and f'HTTP {code}' in receipt.error
    assert len(events(case)) == 1


@pytest.mark.parametrize('fault', ['redirect', 'oversized', 'truncated', 'malformed', 'duplicate', 'nonfinite', 'wrong_type', 'rpc_error'])
def test_invalid_http_and_rpc_responses_stop_without_retry(peer_factory, fault):
    case = peer_factory(fault)
    exchange, receipt = start(case)
    assert receipt.status == Status.FAILED and len(events(case)) == 1
    assert read_record(case[2])['status'] == 'unresolved'
    with pytest.raises(RuntimeError):
        exchange.refresh()


def test_local_operation_denial_prevents_submission(peer_factory):
    case = peer_factory(operations=frozenset({'GetTask'}))
    _, receipt = start(case)
    assert 'not granted' in receipt.error and not case[3].exists()
    assert read_record(case[2])['events'] == []


def test_lost_submission_ack_is_not_retried(peer_factory):
    case = peer_factory('disconnect_send')
    exchange, receipt = start(case)
    assert receipt.status == Status.FAILED
    assert read_record(case[2])['remote_task'] is None
    with pytest.raises(RuntimeError, match='No acknowledged task ID'):
        exchange.refresh()
    with pytest.raises(RuntimeError, match='already attempted'):
        exchange(case[1].request())
    assert sum('created_task' in e for e in events(case)) == 1


def test_known_task_reconnect_reads_saved_result_without_resubmission(peer_factory):
    case = peer_factory('disconnect_get_once')
    exchange, receipt = start(case)
    assert receipt.status == Status.FAILED
    assert read_record(case[2])['status'] == 'unresolved'
    result = exchange.refresh()
    assert result['status'] == 'completed' and json.loads(result['response'])['text'] == '4'
    assert sum('created_task' in e for e in events(case)) == 1
    assert [e['operation'] for e in result['events']] == ['SendMessage', 'GetTask', 'GetTask']


def test_explicit_cancellation_and_read_only_inspection(peer_factory):
    case = peer_factory(hold=True)
    exchange, receipt = start(case, max_polls=0)
    assert receipt.status == Status.FAILED
    before = case[2].joinpath('record.json').read_bytes()
    assert inspect_exchange(case[2])['status'] == 'unresolved'
    assert case[2].joinpath('record.json').read_bytes() == before
    assert exchange.cancel()['status'] == 'cancelled'
    assert exchange.refresh()['status'] == 'cancelled'
    assert [e['operation'] for e in read_record(case[2])['events']] == ['SendMessage', 'CancelTask']


def test_lost_cancel_response_requires_refresh_not_repeated_cancel(peer_factory):
    case = peer_factory('disconnect_cancel', hold=True)
    exchange, _ = start(case, max_polls=0)
    with pytest.raises(Exception):
        exchange.cancel()
    with pytest.raises(RuntimeError, match='already attempted'):
        exchange.cancel()
    assert exchange.refresh()['status'] == 'cancelled'
    assert [e['operation'] for e in read_record(case[2])['events']].count('CancelTask') == 1


def test_cancel_completion_race_preserves_completed_artifact(peer_factory):
    case = peer_factory('cancel_race', hold=True)
    exchange, _ = start(case, max_polls=0)
    assert exchange.cancel()['status'] == 'completed'
    assert json.loads(read_record(case[2])['response'])['text'] == '4'


def test_remote_failed_state_is_preserved(peer_factory):
    case = peer_factory('failed')
    _, receipt = start(case)
    assert receipt.status == Status.FAILED and read_record(case[2])['status'] == 'failed'


def test_budget_and_denied_cancel_never_dispatch(peer_factory):
    case = peer_factory(hold=True, operations=frozenset({'SendMessage', 'GetTask'}))
    exchange, _ = start(case, max_polls=0, max_requests=1)
    with pytest.raises(PermissionError, match='not granted'):
        exchange.cancel()
    with pytest.raises(PermissionError, match='budget'):
        exchange.refresh()
    assert len(read_record(case[2])['events']) == 1


def test_persistence_failure_blocks_further_calls(peer_factory, monkeypatch):
    case = peer_factory(hold=True)
    exchange, _ = start(case, max_polls=0)
    before = events(case)
    calls = []
    def fail(record):
        calls.append(record)
        raise PersistenceError('disk full')
    monkeypatch.setattr(exchange.store, 'save', fail)
    with pytest.raises(PersistenceError):
        exchange.refresh()
    with pytest.raises(PersistenceError):
        exchange.cancel()
    assert len(calls) == 1 and events(case) == before


@pytest.mark.parametrize('endpoint', ['https://example.com/rpc', 'http://localhost:9000/rpc',
    'http://127.0.0.1:9000/rpc?token=x', 'http://user:pass@127.0.0.1:9000/rpc', 'http://127.0.0.1/rpc'])
def test_only_literal_credential_free_loopback_endpoints(endpoint):
    with pytest.raises(ValueError):
        LocalPeer(endpoint, '0' * 64, 'peer')


@pytest.mark.parametrize('change', ['name', 'version', 'interface', 'security', 'extension'])
def test_identity_version_and_unsupported_card_requirements(peer_factory, monkeypatch, change):
    case = peer_factory()
    card = case[0].check_card()
    altered = copy.deepcopy(card)
    if change == 'interface':
        altered['supportedInterfaces'][0]['protocolVersion'] = '0.3'
    elif change == 'security':
        altered['securityRequirements'] = [{'schemes': {'test': []}}]
    elif change == 'extension':
        altered['capabilities']['extensions'] = [{'uri': 'urn:test', 'required': True}]
    else:
        altered[change] = 'changed'
    # Pin a newly read but unsupported card, or detect changed bytes under the old pin.
    pin = case[0].card_digest if change in ('name', 'version') else digest(altered)
    peer = LocalPeer(case[0].endpoint, pin, case[0].name)
    monkeypatch.setattr(LocalPeer, '_http', lambda *a, **k: altered)
    with pytest.raises(ProtocolError):
        peer.check_card()


def test_card_change_between_submission_and_poll_blocks_dispatch(peer_factory, monkeypatch):
    case = peer_factory()
    original = LocalPeer.check_card
    calls = []
    def check(self):
        calls.append(1)
        if len(calls) > 1:
            raise ProtocolError('Card changed')
        return original(self)
    monkeypatch.setattr(LocalPeer, 'check_card', check)
    _, receipt = start(case)
    assert receipt.status == Status.FAILED
    assert len(read_record(case[2])['events']) == 1
