"""Bounded A2A 1.0 JSON-RPC adapter for an explicitly pinned local peer.

No remote authentication, external artifact downloads or automatic effect retry.
"""
import copy
import hashlib
import http.client
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .adapters import Attempt
from .features import report
from .review_contract import bounded_text, canonical, digest, fields, parse_json
from .review_store import PersistenceError, RunStore, read_record

PROTOCOL = '1.0'
OPERATIONS = frozenset(('SendMessage', 'GetTask', 'CancelTask'))
STATES = {'TASK_STATE_' + state for state in (
    'UNSPECIFIED', 'SUBMITTED', 'WORKING', 'COMPLETED', 'FAILED', 'CANCELED',
    'INPUT_REQUIRED', 'REJECTED', 'AUTH_REQUIRED')}
TERMINAL = {'TASK_STATE_' + state for state in ('COMPLETED', 'FAILED', 'CANCELED', 'REJECTED')}


class ProtocolError(ValueError):
    """An unsupported or uncorrelated peer response; do not guess a result."""


class PeerError(RuntimeError):
    """HTTP or JSON-RPC failure, distinct from verified task completion."""


@dataclass(frozen=True)
class LocalPeer:
    endpoint: str
    card_digest: str
    name: str
    operations: frozenset[str] = OPERATIONS
    timeout: float = 5.0

    def __post_init__(self):
        url = urlsplit(self.endpoint)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port
                or url.username or url.password or url.query or url.fragment
                or not re.fullmatch(r'/[a-zA-Z0-9/_-]+', url.path)):
            raise ValueError('Local A2A profile requires an explicit http://127.0.0.1:PORT/path endpoint')
        if not re.fullmatch(r'[0-9a-f]{64}', self.card_digest):
            raise ValueError('An exact agent-card SHA-256 is required')
        bounded_text(self.name, 'peer name', 200)
        if not isinstance(self.operations, frozenset) or not self.operations <= OPERATIONS:
            raise ValueError('Unsupported local operation grants')
        if type(self.timeout) not in (int, float) or not 0 < self.timeout <= 30:
            raise ValueError('Socket inactivity timeout must be in (0, 30] seconds')

    def _http(self, method, path, value=None, limit=262_144):
        url = urlsplit(self.endpoint)
        body = None if value is None else canonical(value).encode('utf-8')
        if body is not None and len(body) > 65_536:
            raise ValueError('A2A request exceeds 64 KiB')
        connection = http.client.HTTPConnection('127.0.0.1', url.port, timeout=self.timeout)
        try:
            connection.request(method, path, body=body,
                               headers={'A2A-Version': PROTOCOL, 'Content-Type': 'application/json',
                                        'Accept': 'application/json'})
            response = connection.getresponse()
            if response.status != 200:
                raise PeerError(f'Peer returned HTTP {response.status}; no redirect or credential fallback')
            if response.getheader('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise ProtocolError('Expected application/json')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > limit):
                raise ProtocolError('Peer response exceeds byte limit or has invalid length')
            raw = response.read(limit + 1)
            if len(raw) > limit or (length is not None and len(raw) != int(length)):
                raise ProtocolError('Truncated or oversized response')
            return parse_json(raw.decode('utf-8'), limit)
        finally:
            connection.close()

    def check_card(self):
        card = self._http('GET', '/.well-known/agent-card.json', limit=16_384)
        if not isinstance(card, dict) or digest(card) != self.card_digest or card.get('name') != self.name:
            raise ProtocolError('Agent card identity changed or does not match the selected peer')
        interface = {'url': self.endpoint, 'protocolBinding': 'JSONRPC', 'protocolVersion': PROTOCOL}
        if interface not in card.get('supportedInterfaces', []):
            raise ProtocolError('Selected A2A 1.0 JSONRPC interface is unavailable')
        if not all(card.get(key) for key in ('description', 'version', 'skills')) or not isinstance(card.get('capabilities'), dict):
            raise ProtocolError('Required agent-card metadata is missing')
        if any(extension.get('required') for extension in card['capabilities'].get('extensions', [])):
            raise ProtocolError('Required A2A extensions are unsupported')
        if (card.get('securityRequirements') or card.get('securitySchemes')
                or any(skill.get('securityRequirements') for skill in card.get('skills', []))):
            raise ProtocolError('Authenticated peers are outside the local profile')
        if 'application/json' not in card.get('defaultInputModes', []) or 'application/json' not in card.get('defaultOutputModes', []):
            raise ProtocolError('Peer does not declare this data-artifact profile')
        return card

    def rpc(self, operation, params, request_id):
        if operation not in self.operations:
            raise PermissionError('A2A operation is not granted locally')
        response = self._http('POST', urlsplit(self.endpoint).path,
                              {'jsonrpc': '2.0', 'id': request_id, 'method': operation, 'params': params})
        if (not isinstance(response, dict) or response.get('jsonrpc') != '2.0'
                or response.get('id') != request_id or ('result' in response) == ('error' in response)):
            raise ProtocolError('Uncorrelated or invalid JSON-RPC response')
        if 'error' in response:
            error = response['error']
            if not isinstance(error, dict) or type(error.get('code')) is not int or not isinstance(error.get('message'), str):
                raise ProtocolError('Invalid JSON-RPC error')
            raise PeerError(f"JSON-RPC {error['code']}: {error['message']}")
        return response['result']


class A2AExchange:
    """Single submission with explicit read-only refresh and bounded cancellation.

    Use with JsonParticipant for correlated, independently verified output.
    Refresh/cancel are local-process controls; records support inspection only.
    """

    def __init__(self, attempt: Attempt, peer: LocalPeer, directory: Path, *, max_polls=4, max_requests=12):
        if not isinstance(attempt, Attempt) or not isinstance(peer, LocalPeer):
            raise TypeError('Attempt and LocalPeer are required')
        if type(max_polls) is not int or not 0 <= max_polls <= 8:
            raise ValueError('max_polls must be in 0..8')
        if type(max_requests) is not int or not 1 <= max_requests <= 32:
            raise ValueError('max_requests must be in 1..32')
        self.attempt, self.peer = attempt, peer
        self.max_polls, self.max_requests = max_polls, max_requests
        self.store = RunStore(directory)
        self.used = self.persistence_failed = False
        self.record = report('a2a-exchange', 'prepared',
            profile={'protocol': PROTOCOL, 'binding': 'JSONRPC', 'transport': 'loopback HTTP'},
            endpoint=peer.endpoint, peer_name=peer.name, card_digest=peer.card_digest,
            identity_scope='Local pin and operation policy; not authenticated remote identity',
            request=parse_json(attempt.request()), request_digest=hashlib.sha256(attempt.request().encode()).hexdigest(),
            operations=sorted(peer.operations), max_requests=max_requests, events=[], remote_task=None,
            completion_scope='Peer protocol state only; JsonParticipant supplies independent verification')

    def _save(self):
        if self.persistence_failed:
            raise PersistenceError('A2A persistence failed; further dispatch is stopped')
        try:
            self.store.save(self.record)
        except PersistenceError:
            self.persistence_failed = True
            raise

    def _task(self, value):
        if not isinstance(value, dict):
            raise ProtocolError('Expected a Task response')
        for key in ('id', 'contextId'):
            bounded_text(value.get(key), key, 200)
        state = value.get('status', {}).get('state')
        if state not in STATES:
            raise ProtocolError('Unknown A2A task state')
        previous = self.record['remote_task']
        if previous and any(value[key] != previous[key] for key in ('id', 'contextId')):
            raise ProtocolError('Peer changed task or context identity')
        if previous and previous['status']['state'] in TERMINAL and value != previous:
            raise ProtocolError('Peer changed an already terminal task')
        if state == 'TASK_STATE_COMPLETED':
            artifacts = value.get('artifacts')
            if not isinstance(artifacts, list) or len(artifacts) != 1 or not isinstance(artifacts[0], dict):
                raise ProtocolError('This profile requires exactly one completed data artifact')
            artifact = artifacts[0]
            bounded_text(artifact.get('artifactId'), 'artifactId', 200)
            parts = artifact.get('parts')
            if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
                raise ProtocolError('This profile requires one data part')
            part = parts[0]
            if set(part) & {'text', 'raw', 'url', 'data'} != {'data'} or part.get('mediaType', 'application/json') != 'application/json':
                raise ProtocolError('Unsupported artifact content; no URL downloads')
            result = part['data']
            fields(result, ('version', 'request_digest', 'text'))
            if type(result['version']) is not int or result['version'] != 1 or result['request_digest'] != self.record['request_digest']:
                raise ProtocolError('Artifact does not match the accepted request')
            bounded_text(result['text'], 'artifact text', 65_536)
            self.record['response'] = canonical(result)
            self.record['artifact_digest'] = digest(artifact)
        self.record['remote_task'] = copy.deepcopy(value)
        self.record['status'] = {
            'TASK_STATE_COMPLETED': 'completed', 'TASK_STATE_FAILED': 'failed',
            'TASK_STATE_CANCELED': 'cancelled', 'TASK_STATE_REJECTED': 'rejected',
            'TASK_STATE_INPUT_REQUIRED': 'paused', 'TASK_STATE_AUTH_REQUIRED': 'paused',
        }.get(state, 'unresolved' if state == 'TASK_STATE_UNSPECIFIED' else 'working')

    def _call(self, operation, params):
        if self.persistence_failed:
            raise PersistenceError('A2A persistence failed; further dispatch is stopped')
        if operation not in self.peer.operations:
            raise PermissionError('A2A operation is not granted locally')
        if len(self.record['events']) >= self.max_requests:
            raise PermissionError('A2A request budget exhausted')
        self.peer.check_card()
        event = {'id': str(uuid.uuid4()), 'operation': operation, 'params': copy.deepcopy(params), 'state': 'pending'}
        self.record['events'].append(event)
        self._save()
        result = self.peer.rpc(operation, params, event['id'])
        event['result'] = result
        if operation == 'SendMessage':
            if not isinstance(result, dict) or set(result) & {'task', 'message'} != {'task'}:
                raise ProtocolError('This profile requires SendMessage to return a task')
            result = result['task']
        self._task(result)
        event['state'] = 'completed'
        self.record.pop('error', None)
        self._save()

    def _failure(self, exc):
        if self.persistence_failed:
            return
        if not self.record['remote_task'] or any(e['state'] == 'pending' for e in self.record['events']):
            self.record['status'] = 'unresolved'
        self.record['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        self._save()

    def __call__(self, request):
        if request != self.attempt.request():
            raise ValueError('Request does not match bound attempt')
        with self.store.lease():
            if self.used:
                raise RuntimeError('A2A submission already attempted; never automatically resubmit')
            self.used = True
            try:
                self._call('SendMessage', {'message': {'messageId': self.attempt.attempt_id, 'role': 'ROLE_USER',
                           'parts': [{'data': self.record['request'], 'mediaType': 'application/json'}]},
                           'configuration': {'acceptedOutputModes': ['application/json'], 'returnImmediately': True}})
                for _ in range(self.max_polls):
                    if self.record['status'] != 'working':
                        break
                    self._call('GetTask', {'id': self.record['remote_task']['id']})
                if self.record['status'] != 'completed':
                    raise PeerError(f"Peer task is {self.record['status']}; inspect, refresh or cancel explicitly")
                return self.record['response']
            except BaseException as exc:
                self._failure(exc)
                raise

    def _control(self, operation):
        with self.store.lease():
            if self.persistence_failed:
                raise PersistenceError('A2A persistence failed; further dispatch is stopped')
            task = self.record['remote_task']
            if not task:
                raise RuntimeError('No acknowledged task ID; reconcile with peer owner without resubmitting')
            if task['status']['state'] in TERMINAL:
                return copy.deepcopy(self.record)
            if operation == 'CancelTask' and any(e['operation'] == operation for e in self.record['events']):
                raise RuntimeError('Cancellation was already attempted; use read-only refresh')
            try:
                self._call(operation, {'id': task['id']})
            except BaseException as exc:
                self._failure(exc)
                raise
            return copy.deepcopy(self.record)

    def refresh(self):
        return self._control('GetTask')

    def cancel(self):
        return self._control('CancelTask')


def inspect_exchange(directory: Path):
    record = read_record(directory)
    if record.get('operation') != 'a2a-exchange':
        raise ValueError('Not an A2A exchange record')
    if record.get('status') in ('prepared', 'working'):
        record['persisted_status'] = record['status']
        record['status'] = 'unresolved'
    record['inspection_note'] = 'Read-only inspection; no reconnect, retry or provider call'
    return record
