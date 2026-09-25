"""Independent stdlib A2A 1.0 fixture. No Harness imports or provider calls.

Computes integer addition, keeps actual task state, and injects selected faults.
This is a loopback test peer, not an authenticated production agent server.
"""
import argparse
import hashlib
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import TCPServer


class LoopbackHTTPServer(HTTPServer):
    def server_bind(self):
        # The peer advertises a numeric loopback endpoint; reverse DNS is unnecessary
        # and can block readiness on runners with an unavailable resolver.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, value, code=200):
        raw = encoded(value)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def save(self, event):
        self.server.events.append(event)
        self.server.log.write_text(json.dumps({'events': self.server.events, 'tasks': self.server.tasks}, indent=2), encoding='utf-8')

    def do_GET(self):
        self.reply(self.server.card if self.path == '/.well-known/agent-card.json' else {},
                   200 if self.path == '/.well-known/agent-card.json' else 404)

    def do_POST(self):
        fault = self.server.fault
        request = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        method, params = request.get('method'), request.get('params', {})
        self.save({'request': request, 'version_header': self.headers.get('A2A-Version')})
        def error(code, message):
            self.reply({'jsonrpc': '2.0', 'id': request.get('id'), 'error': {'code': code, 'message': message}})
        if self.path != '/rpc':
            self.reply({}, 404)
            return
        if self.headers.get('A2A-Version') != '1.0':
            error(-32009, 'Protocol version not supported')
            return
        if fault in ('denied', 'auth_required'):
            self.reply({}, 403 if fault == 'denied' else 401)
            return
        if fault in ('redirect', 'oversized', 'truncated', 'malformed', 'duplicate', 'nonfinite', 'wrong_type'):
            self.send_response(302 if fault == 'redirect' else 200)
            self.send_header('Content-Type', 'text/html' if fault == 'wrong_type' else 'application/json')
            raw = {'malformed': b'{', 'duplicate': b'{"id":1,"id":2}', 'nonfinite': b'{"value":NaN}'}.get(fault, b'{}')
            self.send_header('Content-Length', str(262_145 if fault == 'oversized' else 10 if fault == 'truncated' else len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if fault == 'rpc_error':
            error(-32004, 'Operation unsupported')
            return
        if method == 'SendMessage':
            message = params.get('message', {})
            if (message.get('role') != 'ROLE_USER' or not message.get('messageId')
                    or message.get('taskId') or params.get('configuration', {}).get('acceptedOutputModes') != ['application/json']):
                error(-32602, 'Unsupported fixture message profile')
                return
            data = message['parts'][0]['data']
            match = re.fullmatch(r'Compute (-?\d+) \+ (-?\d+)', data['attempt']['task']['objective'])
            if not match:
                error(-32602, 'Fixture supports integer addition only')
                return
            task_id, context = str(uuid.uuid4()), str(uuid.uuid4())
            answer = str(int(match[1]) + int(match[2]))
            if fault == 'wrong_answer':
                answer = str(int(answer) + 1)
            artifact = {'artifactId': str(uuid.uuid4()), 'name': 'Computed sum', 'parts': [{'mediaType': 'application/json',
                'data': {'version': 1, 'request_digest': hashlib.sha256(encoded(data)).hexdigest(), 'text': answer}}]}
            if fault == 'wrong_digest':
                artifact['parts'][0]['data']['request_digest'] = '0' * 64
            task = {'id': task_id, 'contextId': context, 'status': {'state': 'TASK_STATE_WORKING'}}
            self.server.tasks[task_id] = {'task': task, 'artifact': artifact}
            self.save({'created_task': task_id})
            if fault == 'disconnect_send':
                self.connection.close()
                return
            result = {'task': task}
        elif method in ('GetTask', 'CancelTask'):
            saved = self.server.tasks.get(params.get('id'))
            if saved is None:
                error(-32001, 'Task not found')
                return
            task = saved['task']
            if method == 'CancelTask' and task['status']['state'] == 'TASK_STATE_WORKING':
                task['status']['state'] = 'TASK_STATE_CANCELED'
            if ((method == 'GetTask' and not self.server.hold and task['status']['state'] == 'TASK_STATE_WORKING')
                    or (fault == 'cancel_race' and method == 'CancelTask')):
                task.update(status={'state': 'TASK_STATE_COMPLETED'}, artifacts=[saved['artifact']])
            if fault == 'failed':
                task.update(status={'state': 'TASK_STATE_FAILED'})
            if fault == 'bad_artifact':
                task['artifacts'] = []
            if fault == 'url_artifact':
                task['artifacts'] = [{'artifactId': 'outside', 'parts': [{'url': 'https://example.com/never-fetch'}]}]
            if fault == 'wrong_task':
                task['id'] = 'wrong-task'
            if fault == 'unknown_state':
                task['status']['state'] = 'TASK_STATE_FUTURE'
            self.save({'observed_task': task})
            if fault == 'disconnect_get_once' and method == 'GetTask' and not self.server.disconnected:
                self.server.disconnected = True
                self.connection.close()
                return
            if fault == 'disconnect_cancel' and method == 'CancelTask':
                self.connection.close()
                return
            result = task
        else:
            error(-32601, 'Method not found')
            return
        self.reply({'jsonrpc': '2.0', 'id': 'incorrect' if fault == 'wrong_rpc' else request['id'], 'result': result})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--fault', default='none')
    parser.add_argument('--hold', action='store_true')
    args = parser.parse_args()
    server = LoopbackHTTPServer(('127.0.0.1', 0), Handler)
    endpoint = f'http://127.0.0.1:{server.server_port}/rpc'
    server.card = {'name': 'independent-arithmetic-peer', 'description': 'Local deterministic addition fixture', 'version': '1.0.0',
                   'supportedInterfaces': [{'url': endpoint, 'protocolBinding': 'JSONRPC', 'protocolVersion': '1.0'}],
                   'capabilities': {}, 'defaultInputModes': ['application/json'], 'defaultOutputModes': ['application/json'],
                   'skills': [{'id': 'addition', 'name': 'Integer addition', 'description': 'Compute a bounded integer sum', 'tags': ['arithmetic']}]}
    server.tasks, server.events = {}, []
    server.fault, server.hold, server.log, server.disconnected = args.fault, args.hold, args.log, False
    print(json.dumps({'endpoint': endpoint, 'card': server.card, 'card_digest': hashlib.sha256(encoded(server.card)).hexdigest()}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
