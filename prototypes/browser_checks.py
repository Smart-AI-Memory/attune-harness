"""Local fixture host for retained prototype browser checks.

This implements only the presentation-state API used by these demonstrations.
It does not connect to an AI host, Harness authority, or private session records.
"""

import argparse
import atexit
import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def prepare_check(source: Path) -> tuple[str, Path]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="New directory for this run's JSON and screenshots"
    )
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError("Browser checks require assertions; disable -O and PYTHONOPTIMIZE")
    fragment = json.dumps(source.read_text(encoding="utf-8")).replace("<", "\\u003c")
    if args.output is None:
        output = Path(tempfile.mkdtemp(prefix="attune-prototype-check-"))
    else:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
    print(f"Browser check artifacts: {output}", file=sys.stderr, flush=True)

    document = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>:root{color-scheme:light dark}body{margin:0;padding:16px;box-sizing:border-box}
iframe{display:block;width:100%;border:0}</style></head><body>
<iframe sandbox="allow-scripts" referrerpolicy="no-referrer" title="Prototype check"></iframe>
<script>
const frame = document.querySelector('iframe');
const state = JSON.parse(sessionStorage.getItem('prototype-check-state') || 'null');
const shim = '<script>window.openai={widgetState:' +
  JSON.stringify(state).replace(/</g, '\\\\u003c') +
  ',setWidgetState:async function(state){parent.postMessage({state},"*");}};<\\/script>';
const resize = '<script>const report=()=>parent.postMessage({height:document.documentElement.scrollHeight},"*");' +
  'new MutationObserver(report).observe(document.body,{subtree:true,childList:true,attributes:true});' +
  'addEventListener("load",report);report();<\\/script>';
addEventListener('message', event => {
  if (event.source !== frame.contentWindow) return;
  if (event.data.state) sessionStorage.setItem('prototype-check-state', JSON.stringify(event.data.state));
  if (Number.isFinite(event.data.height)) frame.style.height = event.data.height + 'px';
});
frame.srcdoc = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">' +
  '<style>:root{color-scheme:light dark}body{margin:0}</style>' + shim + FRAGMENT + resize;
</script></body></html>
""".replace("FRAGMENT", fragment).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(document)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(document)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    atexit.register(server.server_close)
    atexit.register(server.shutdown)
    return f"http://127.0.0.1:{server.server_port}/", output
