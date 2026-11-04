"""Bounded authorization I/O. Secrets travel only through anonymous pipes."""
import http.client
import json
import ssl
import sys
import time
from urllib.parse import urlencode, urlsplit


def main():
    connection = None
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144: raise ValueError('input')
        value = json.loads(raw)
        parts = urlsplit(value['url'])
        if (parts.scheme != 'https' or parts.hostname != 'auth.openai.com'
                or parts.port not in (None, 443) or parts.username or parts.password
                or parts.query or parts.fragment): raise ValueError('endpoint')
        deadline = time.monotonic() + value['timeout']
        connection = http.client.HTTPSConnection('auth.openai.com', 443,
            timeout=value['timeout'], context=ssl.create_default_context(cafile=value['ca_file']))
        form = value['form']
        connection.request('GET' if form is None else 'POST', parts.path,
            body=None if form is None else urlencode(form).encode(),
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'})
        response = connection.getresponse()
        if response.status != 200: raise ValueError('status')
        output = bytearray()
        while True:
            seconds = deadline - time.monotonic()
            if seconds <= 0: raise TimeoutError('deadline')
            if connection.sock: connection.sock.settimeout(seconds)
            chunk = response.read1(min(16384, 131073 - len(output)))
            if not chunk: break
            output.extend(chunk)
            if len(output) > 131072: raise ValueError('response')
        sys.stdout.buffer.write(output or b'{}')
        return 0
    except Exception:
        sys.stderr.write('plan_authorization_failed')
        return 2
    finally:
        if connection: connection.close()


if __name__ == '__main__':
    raise SystemExit(main())
