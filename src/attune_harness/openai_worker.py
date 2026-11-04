"""One supervised HTTPS request; no ambient client configuration or retries."""

import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = 'https://api.openai.com/v1/responses'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    try:
        raw_input = sys.stdin.read(3_000_001)
        if len(raw_input) > 3_000_000:
            raise ValueError('request limit')
        value = json.loads(raw_input)
        body = json.dumps(value['body'], allow_nan=False).encode('utf-8')
        request = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
            'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'],
            'Content-Type': 'application/json'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=value['timeout']) as response:
            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise ValueError('response limit')
            sys.stdout.buffer.write(raw)
        return 0
    except urllib.error.HTTPError:
        # Never echo an HTTP body, headers, URL or credential in diagnostics.
        sys.stderr.write('openai_http_error')
    except Exception:
        sys.stderr.write('openai_transport_error')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
