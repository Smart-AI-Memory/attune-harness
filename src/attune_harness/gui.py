"""Read-only loopback companion for explicitly registered saved tasks.

Run with ``python -m attune_harness.gui --task /absolute/task``. This first
increment has no execution or acceptance endpoint. Owners render fresh snapshots.
"""

import argparse
import base64
import hashlib
import hmac
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from . import task_view

SCRIPT = """let token=location.hash.slice(1)||sessionStorage.getItem('attune-gui-token');
if(location.hash){sessionStorage.setItem('attune-gui-token',token);history.replaceState(null,'',location.pathname);}
const status=document.querySelector('#status'),frame=document.querySelector('iframe');
let snapshotUrl=null;
async function refresh(){
 const button=document.querySelector('button');button.disabled=true;
 status.textContent='Inspecting saved tasks…';
 try{const res=await fetch('/snapshot',{headers:{'X-Attune-Session':token||''},cache:'no-store'});
 if(!res.ok)throw Error(await res.text());
 const prior=snapshotUrl;snapshotUrl=URL.createObjectURL(new Blob([await res.text()],{type:'text/html'}));
 frame.onload=()=>{if(prior)URL.revokeObjectURL(prior);};frame.src=snapshotUrl;status.textContent='Snapshot refreshed. Inspection makes no decisions or model calls.';
 }catch(e){status.textContent='Refresh failed. Any displayed snapshot is old. '+e.message;}
 finally{button.disabled=false;}
}
document.querySelector('button').addEventListener('click',refresh);refresh();
"""
STYLE = """body{margin:0;font:14px system-ui;background:#f5f6f2;color:#263c30}
header{padding:16px 24px;border-bottom:1px solid #dce4da;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
button{font:inherit;padding:9px 14px;background:#285e42;color:white;border:0;border-radius:7px}
iframe{display:block;width:100%;height:calc(100vh - 100px);border:0}p{margin:0}a{color:inherit}
"""
PAGE = ("<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Attune · Saved workspace</title><link rel="stylesheet" href="/style.css">'
        '</head><body><header><strong>ATTUNE / Saved workspace</strong>'
        '<button type="button">Refresh from Harness</button>'
        '<p id="status" role="status" aria-live="polite">Connecting…</p></header>'
        '<iframe title="Saved task snapshots" sandbox="allow-scripts"></iframe>'
        '<script src="/app.js"></script></body></html>')


class CompanionServer(HTTPServer):
    """A bounded local reader. No caller-supplied filesystem paths or commands."""

    def __init__(self, tasks, *, port=0):
        paths = tuple(Path(path) for path in tasks)
        if not paths or len(paths) > task_view.MAX_SAVED_TASKS:
            raise ValueError('Register between one and 20 saved tasks')
        if any(not p.is_absolute() or p.resolve() != p or not p.is_dir() for p in paths):
            raise ValueError('Task directories must exist at canonical absolute paths')
        if len(set(paths)) != len(paths):
            raise ValueError('Task directories must be distinct')
        # Validate the first authoritative task before exposing a listener.
        task_view.inspect_saved_tasks(paths[0], paths[1:])
        self.tasks = paths
        self.token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'

    @property
    def launch_url(self):
        # Fragment is not sent in HTTP requests. Never log the capability.
        return self.origin + '/#' + self.token

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Avoid persisting user paths, request data or local capabilities.

    def send(self, status, body, content_type='text/plain; charset=utf-8'):
        raw = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        # Inline styles/scripts in the owner snapshot carry their own hash policy.
        hashed = lambda value: base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        policy = (f"default-src 'none'; script-src 'self' 'sha256-{hashed(task_view._REPLY_SCRIPT)}'; "
                  f"style-src 'self' 'sha256-{hashed(task_view._CSS)}'; connect-src 'self'; "
                  "frame-src 'self' blob:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.send_header('Content-Security-Policy', policy)
        self.end_headers()
        self.wfile.write(raw)

    def boundary(self):
        expected = self.server.origin.removeprefix('http://')
        if self.headers.get_all('Host') != [expected]:
            self.send(403, 'Unrecognized local host')
            return False
        origins = self.headers.get_all('Origin')
        if origins is not None and origins != [self.server.origin]:
            self.send(403, 'Foreign origin refused')
            return False
        return True

    def do_GET(self):
        if not self.boundary():
            return
        static = {'/': (PAGE, 'text/html; charset=utf-8'),
                  '/app.js': (SCRIPT, 'text/javascript; charset=utf-8'),
                  '/style.css': (STYLE, 'text/css; charset=utf-8')}
        if self.path in static:
            body, kind = static[self.path]
            return self.send(200, body, kind)
        if self.path != '/snapshot':
            return self.send(404, 'No such companion resource')
        tokens = self.headers.get_all('X-Attune-Session')
        if len(tokens or []) != 1 or not hmac.compare_digest(tokens[0], self.server.token):
            return self.send(403, 'Open this workspace using its local launcher link')
        try:
            entries = task_view.inspect_saved_tasks(self.server.tasks[0], self.server.tasks[1:])
            body = task_view.render_saved_tasks(entries, 'html')
            if len(body.encode('utf-8')) > 8 * 1024 * 1024:
                raise ValueError('Rendered snapshot exceeds companion limit')
        except (ValueError, OSError) as exc:
            return self.send(409, str(exc))
        return self.send(200, body, 'text/html; charset=utf-8')

    def do_POST(self):
        self.close_connection = True
        self.send(405, 'This workspace is read-only; no action was performed')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, action='append', required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args(argv)
    with CompanionServer(args.task, port=args.port) as server:
        print(f'Read-only companion at {server.origin}; Ctrl-C stops the listener.', flush=True)
        if not args.no_open:
            webbrowser.open(server.launch_url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
