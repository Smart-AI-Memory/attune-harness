"""Trusted test wrapper: real SDK, in-memory HTTP only, no production switch."""

import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace


def main(options):
    entry_keys = sorted(os.environ)
    entry_values = {k: os.environ.get(k) for k in options['expected_environment']}
    # Install before importing the SDK. Both Python socket entry points and the
    # socket audit events fail closed; the synthetic responder needs neither.
    attempts = []
    cwd_reads = []
    cwd_guard_checks = []
    audit_cwd = options.get('audit_cwd')
    cwd_root = os.path.normcase(os.path.abspath(audit_cwd)) if audit_cwd else None

    def blocked(*args, **kwargs):
        attempts.append('socket')
        raise PermissionError('Offline native fixture forbids external networking')

    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname'):
            blocked()
        if event == 'open' and cwd_root and not isinstance(args[0], int):
            target = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
            try:
                within = os.path.commonpath((cwd_root, target)) == cwd_root
            except ValueError:  # Different Windows drives.
                within = False
            if within:
                cwd_reads.append('open')
                raise PermissionError('Offline fixture forbids opening cwd decoys')

    sys.addaudithook(audit)
    if audit_cwd:
        # Prove the content-open guard refuses a real decoy before clearing the
        # control observation. The SDK path must subsequently make no attempt.
        try:
            (Path(audit_cwd) / 'anthropic.py').read_bytes()
        except PermissionError:
            cwd_guard_checks.append('open')
        else:
            raise AssertionError('Cwd decoy guard did not refuse the control')
        cwd_reads.clear()
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
    socket.gethostbyname = blocked
    socket.gethostbyname_ex = blocked
    checks = []
    for name, probe in (
        ('connect', lambda: socket.socket().connect(('192.0.2.1', 443))),
        ('connect_ex', lambda: socket.socket().connect_ex(('192.0.2.1', 443))),
        ('create_connection', lambda: socket.create_connection(('192.0.2.1', 443))),
        ('dns', lambda: socket.getaddrinfo('offline.invalid', 443)),
    ):
        try:
            probe()
        except PermissionError:
            checks.append(name)
        else:
            raise AssertionError('External network guard did not refuse ' + name)
    attempts.clear()

    import httpx2
    from attune_harness import memory_native as native

    home_lookups = []
    guard_home = os.name == 'nt' or options.get('force_windows_client', False)
    if guard_home:
        def refuse_home(cls):
            home_lookups.append('home')
            raise RuntimeError('Offline fixture forbids home-directory discovery')
        Path.home = classmethod(refuse_home)
    if options.get('force_windows_client') and os.name != 'nt':
        # Structural control on POSIX; native Windows jobs exercise the branch
        # without this test-only platform selection.
        native.os = SimpleNamespace(name='nt', environ=os.environ)

    import anthropic
    sdk_root = Path(anthropic.__file__).parent
    sdk_sources = {name: hashlib.sha256((sdk_root / name).read_bytes()).hexdigest()
                   for name in ('_client.py', 'lib/credentials/_constants.py')}
    # Exercise the real connection-pool/TLS-context constructor under the same
    # finite map and socket/home guards. The request responder below remains
    # in-memory; no socket, TLS handshake, or provider authentication is tested.
    transport = httpx2.HTTPTransport(retries=0, trust_env=False)
    transport.close()

    observed = {
        'schema_version': 1, 'runtime': native.runtime_identity(),
        'interpreter_argv': sys.orig_argv,
        'base_executable': sys._base_executable,
        'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
        'environment_keys': entry_keys,
        # Never serialize unknown ambient values if an inheritance regression
        # occurs. The parent checks the full key set and every expected value.
        'environment_values': entry_values,
        'sdk_import_environment_keys': sorted(os.environ),
        'network_guard_checks': checks, 'external_network_attempts': 0,
        'offline_sdk_requests': 0, 'live_provider_model_calls': 0,
        'home_lookup_guard': guard_home, 'home_lookups': 0,
        'sdk_source_sha256': sdk_sources, 'http_transport_constructed_and_closed': True,
        'child_cwd': os.getcwd(), 'cwd_read_guard_checks': cwd_guard_checks,
        'cwd_file_open_attempts': 0,
        'helper_stdout_base64': '',
    }
    path = Path(options['receipt'])

    def retain():
        observed['external_network_attempts'] = len(attempts)
        observed['home_lookups'] = len(home_lookups)
        observed['cwd_file_open_attempts'] = len(cwd_reads)
        path.write_bytes((json.dumps(observed, ensure_ascii=True, sort_keys=True) + '\n').encode('utf-8'))

    retain()

    class Responder(httpx2.BaseTransport):
        def handle_request(self, request):
            observed['offline_sdk_requests'] += 1
            observed['dispatch_environment_keys'] = sorted(os.environ)
            observed['dispatch_environment_values'] = {
                k: os.environ.get(k) for k in options['expected_environment']}
            observed['explicit_key_header'] = request.headers['x-api-key'] == 'offline-native-test-key'
            observed['authorization_header_present'] = 'authorization' in request.headers
            observed['request'] = {
                'method': request.method, 'url': str(request.url),
                'body': json.loads(request.content.decode('utf-8')),
                'headers': {k: v for k, v in request.headers.items() if k.lower() != 'x-api-key'},
            }
            retain()
            if options.get('mode') == 'timeout':
                # A real descendant must die with the supervised helper, even
                # when it would otherwise outlive the provider timeout.
                marker = options['descendant_marker']
                gate = options['descendant_gate']
                started = options['descendant_started']
                import runpy
                tools = runpy.run_path(str(Path(__file__).with_name('native_memory_process_witness.py')))
                code = tools['descendant_code'](marker, gate, started)
                descendant = subprocess.Popen([sys.executable, '-I', '-B', '-c', code])
                observed['descendant_spawned'] = True
                deadline = time.monotonic() + 2
                while not Path(started).is_file() and descendant.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                observed['descendant_pid'] = descendant.pid
                observed['descendant_started'] = Path(started).read_bytes() == b'started'
                observed['descendant_alive_before_timeout'] = descendant.poll() is None
                assert observed['descendant_started'] and observed['descendant_alive_before_timeout']
                observed['descendant_reference'] = tools['process_reference'](descendant, options['observer_pid'])
                retain()
                time.sleep(30)
            class Stream(httpx2.SyncByteStream):
                def __iter__(self):
                    yield base64.b64decode(options['raw_base64'])

            return httpx2.Response(
                options.get('status', 200), request=request,
                headers={'content-type': 'application/json', 'request-id': 'req_offline'},
                stream=Stream(),
            )

    # A locale/text wrapper must not control protocol decoding or newline bytes.
    sys.stdin.reconfigure(encoding='ascii', errors='strict')
    sys.stdout.reconfigure(encoding='ascii', errors='strict', newline='\r\n')
    stdout = sys.stdout
    wire = bytearray()

    class BinaryOutput:
        def write(self, value):
            wire.extend(value)
            return stdout.buffer.write(value)

        def flush(self):
            stdout.buffer.flush()

    class Output:
        buffer = BinaryOutput()

        def __getattr__(self, name):
            return getattr(stdout, name)

    sys.stdout = Output()
    try:
        return native.helper_main(inner_transport=Responder())
    finally:
        sys.stdout = stdout
        observed['helper_stdout_base64'] = base64.b64encode(wire).decode('ascii')
        retain()
