"""Local browser intake and intent approval forms for registered saved drafts.

Build grants, dispatch, resume and broader GUI navigation are deferred to 1.4.0.
"""

import argparse
import base64
import hashlib
import hmac
import json
import secrets
import socket
import time
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from . import task_view
from .features import FeatureUnavailable
from .review_contract import parse_json
from .gui_forms import FORM_SCRIPT, FORM_STYLE, FORM_PAGE
from .gui_forms_intake import INTAKE_SCRIPT, INTAKE_PAGE

SCRIPT = """let token=location.hash.slice(1)||sessionStorage.getItem('attune-gui-token');
if(location.hash){sessionStorage.setItem('attune-gui-token',token);history.replaceState(null,'',location.pathname);}
const status=document.querySelector('#status'),frame=document.querySelector('iframe');
let snapshotUrl=null;
async function refresh(){
 let fresh=false;
 const button=document.querySelector('#refresh');button.disabled=true;
 status.textContent='Inspecting saved tasks…';
 try{const res=await fetch('/snapshot',{headers:{'X-Attune-Session':token||''},cache:'no-store'});
 if(!res.ok)throw Error(await res.text());
 const prior=snapshotUrl;snapshotUrl=URL.createObjectURL(new Blob([await res.text()],{type:'text/html'}));
 frame.onload=()=>{if(prior)URL.revokeObjectURL(prior);};frame.src=snapshotUrl;fresh=true;status.textContent='Snapshot refreshed. Inspection makes no decisions or model calls.';
 }catch(e){status.textContent='Refresh failed. Any displayed snapshot is old. '+e.message;}
 finally{button.disabled=false;}
 return fresh;
}
document.querySelector('#refresh').addEventListener('click',()=>act(()=>refreshWorkspace()));
"""
SCRIPT += FORM_SCRIPT
STYLE = """body{margin:0;font:14px system-ui;background:#f5f6f2;color:#263c30}
header{padding:16px 24px;border-bottom:1px solid #dce4da;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
button{font:inherit;padding:9px 14px;background:#285e42;color:white;border:0;border-radius:7px}
iframe{display:block;width:100%;height:calc(100vh - 100px);border:0}p{margin:0}a{color:inherit}
"""
STYLE += FORM_STYLE
PAGE = ("<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Attune · Saved workspace</title><link rel="stylesheet" href="/style.css">'
        '</head><body><header><strong>ATTUNE / Saved workspace</strong>'
        '<button id="refresh" type="button">Refresh from Harness</button>'
        '<p id="status" role="status" aria-live="polite">Connecting…</p></header>'
         + FORM_PAGE + '<p class=\"snapshot-help\">If the snapshot pane below is blank, open the private launcher link in Chrome. Some embedded browsers do not display these snapshots.</p><iframe title="Saved task snapshots" sandbox="allow-scripts"></iframe>'
        '<script src="/app.js"></script></body></html>')


BUILD_UNAVAILABLE = ('Browser build controls are unavailable in 1.3.0; '
                     'delivery is deferred to 1.4.0. Use separately authorized CLI execution.')


def _development_profile():
    # Retained development tests substitute this function. The installed product
    # has no flag or environment override for deferred GUI execution.
    return False


INTAKE_BOOTSTRAP = """let token=location.hash.slice(1);
// Storage is optional: private-link access must survive a browser storage refusal.
if(location.hash){
 try{sessionStorage.setItem('attune-gui-token',token);}catch(e){}
 history.replaceState(null,'',location.pathname);
}else{
 try{token=sessionStorage.getItem('attune-gui-token')||'';}catch(e){}
}
const status=document.querySelector('#status');
document.querySelector('#refresh').addEventListener('click',()=>act(()=>refreshWorkspace()));
""" + INTAKE_SCRIPT
INTAKE_DOCUMENT = ('<!doctype html><html lang=en><head><meta charset=utf-8>'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Attune · Intake and intent approval</title><link rel="stylesheet" href="/style.css">'
    '</head><body><header><strong>ATTUNE / Intake and intent approval</strong>'
    '<button id="refresh" type="button">Refresh forms</button>'
    '<button id="browser-open" type="button" disabled>Open in browser</button>'
    '<p id="browser-tip" hidden><strong>Tip: </strong>This panel is narrow. '
    'Open in browser for more room. Copy any unsaved answers first.</p>'
    '<p id="status" role="status" aria-live="polite">Connecting…</p></header>'
    + INTAKE_PAGE + '<script src="/app.js"></script></body></html>')


class CompanionServer(HTTPServer):
    """A bounded local reader. No caller-supplied filesystem paths or commands."""

    def __init__(self, tasks, *, port=0, edit=False, allow_build_commands=False):
        self.forms_only = not _development_profile()
        if allow_build_commands and self.forms_only:
            raise FeatureUnavailable(BUILD_UNAVAILABLE)
        if allow_build_commands and not edit:
            raise ValueError("Command builds require explicit edit mode")
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
        self.editable = edit
        self.decisions = None
        self.builds = None
        self._browser_attempt = None
        if edit or self.forms_only:
            from .gui_decisions import Decisions
            self.decisions = Decisions(paths)
        if allow_build_commands:
            from .gui_build import Builds
            self.builds = Builds(self.decisions)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'

    def server_close(self):
        if self.builds is not None:
            self.builds.close()
        if self.decisions is not None:
            self.decisions.close()
        super().server_close()

    @property
    def launch_url(self):
        # Fragment is not sent in HTTP requests. Only display it to the launcher.
        return self.origin + '/#' + self.token

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def open_browser(self, confirmed):
        """Request the fixed private launch URL, never a caller-selected target."""
        if confirmed is not True:
            raise ValueError('Opening the browser requires an explicit click')
        now = time.monotonic()
        if self._browser_attempt is not None and now - self._browser_attempt[0] < 2:
            return self._browser_attempt[1]
        try:
            opened = webbrowser.open(self.launch_url, new=1)
        except (webbrowser.Error, OSError):
            opened = False
        result = {'requested': bool(opened), 'message': (
            'Browser opening requested. Continue in the new browser view. '
            'Unsaved answers stay here for copying.' if opened else
            'Browser opening could not be confirmed. Copy the private launcher link from '
            'Terminal into your browser. Unsaved answers stay here for copying.')}
        self._browser_attempt = (time.monotonic(), result)
        return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Avoid persisting user paths, request data or local capabilities.

    def finish(self):
        # Closing with unread POST bytes can reset the connection on Windows,
        # discarding the refusal response. Half-close first, then discard a
        # bounded amount without parsing it or invoking any task owner.
        if getattr(self, '_unread_post', False):
            try:
                self.wfile.flush()
                self.connection.shutdown(socket.SHUT_WR)
                deadline = time.monotonic() + 0.25
                remaining = 65536
                while remaining:
                    budget = deadline - time.monotonic()
                    if budget <= 0:
                        break
                    self.connection.settimeout(budget)
                    chunk = self.connection.recv(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except OSError:
                pass  # Disconnected clients cannot receive the refusal.
        super().finish()

    def send(self, status, body, content_type='text/plain; charset=utf-8'):
        raw = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Connection', 'close')
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
        static = {'/': (INTAKE_DOCUMENT if self.server.forms_only else PAGE, 'text/html; charset=utf-8'),
                  '/app.js': (INTAKE_BOOTSTRAP if self.server.forms_only else SCRIPT, 'text/javascript; charset=utf-8'),
                  '/style.css': (STYLE, 'text/css; charset=utf-8')}
        if self.path in static:
            body, kind = static[self.path]
            return self.send(200, body, kind)
        if self.server.forms_only and self.path != '/workspace':
            return self.send(404, 'No such forms resource')
        if self.path not in ('/snapshot', '/workspace'):
            return self.send(404, 'No such companion resource')
        if not self.authenticated():
            return
        if self.path == '/workspace':
            tasks = self.server.decisions.inspect() if self.server.decisions else []
            if self.server.builds is not None:
                for task in tasks:
                    try:
                        task['build'] = self.server.builds.inspect(task['task'])
                    except (ValueError, OSError, RuntimeError) as exc:
                        task['build'] = {'available': False, 'running': False, 'note': str(exc)}
            return self.send_json({'editable': self.server.editable, 'tasks': tasks})
        try:
            entries = task_view.inspect_saved_tasks(self.server.tasks[0], self.server.tasks[1:])
            body = task_view.render_saved_tasks(entries, 'html')
            if len(body.encode('utf-8')) > 8 * 1024 * 1024:
                raise ValueError('Rendered snapshot exceeds companion limit')
        except (ValueError, OSError) as exc:
            return self.send(409, str(exc))
        return self.send(200, body, 'text/html; charset=utf-8')

    def authenticated(self):
        tokens = self.headers.get_all('X-Attune-Session')
        if len(tokens or []) != 1 or not hmac.compare_digest(tokens[0].encode('utf-8'), self.server.token.encode('ascii')):
            self.send(403, 'Open this workspace using its local launcher link')
            return False
        return True

    def send_json(self, value):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(body.encode('utf-8')) > 8 * 1024 * 1024:
            return self.send(409, 'Decision exceeds companion display limit; inspect in the CLI')
        self.send(200, body, 'application/json; charset=utf-8')

    def do_POST(self):
        self._unread_post = True
        self.close_connection = True
        if self.server.forms_only and self.path not in ('/decision/open', '/decision/submit', '/browser/open'):
            return self.send(404, 'No such forms action; browser execution is deferred to 1.4.0')
        if not self.server.editable and self.path != '/browser/open':
            return self.send(405, 'This workspace is read-only; no action was performed')
        if not self.boundary() or not self.authenticated():
            return
        if self.headers.get_all('Origin') != [self.server.origin]:
            return self.send(403, 'Same-origin browser action required')
        if self.path not in ('/decision/open', '/decision/submit', '/build/preview', '/build/start', '/browser/open'):
            return self.send(404, 'No such companion action')
        lengths = self.headers.get_all('Content-Length')
        if (self.headers.get_all('Transfer-Encoding') or len(lengths or []) != 1
                or not lengths[0].isascii() or not lengths[0].isdigit()
                or len(lengths[0]) > 7 or not 0 < int(lengths[0]) <= 65536):
            return self.send(413, 'Use a bounded JSON request of at most 65536 bytes')
        if self.headers.get_all('Content-Type') != ['application/json']:
            return self.send(415, 'Expected application/json')
        try:
            size = int(lengths[0])
            raw = self.rfile.read(size)
            self._unread_post = False
            if len(raw) != size:
                raise ValueError('Incomplete request; inspect before retrying')
            payload = parse_json(raw.decode('utf-8'), 65536)
            expected = {'task', 'checkpoint'}
            if self.path == '/browser/open':
                expected = {'confirmed'}
            elif self.path == '/decision/submit':
                expected |= {'decision', 'response'}
            elif self.path == '/build/start':
                expected |= {'grant', 'confirmed'}
            if not isinstance(payload, dict) or set(payload) != expected:
                raise ValueError('Unsupported action fields')
            if self.path == '/browser/open':
                result = self.server.open_browser(**payload)
            elif self.path.startswith('/build/'):
                if self.server.builds is None:
                    raise ValueError('Relaunch with --edit --allow-build-commands to enable explicit command grants')
                owner = self.server.builds.preview if self.path == '/build/preview' else self.server.builds.start
                result = owner(**payload)
            elif self.path == '/decision/open':
                result = self.server.decisions.open(**payload)
            else:
                result = self.server.decisions.submit(**payload)
        except (ValueError, OSError, FeatureUnavailable, RecursionError) as exc:
            return self.send(409, str(exc) + ' Inspect saved state and reopen; do not replay a submission.')
        return self.send_json(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, action='append', required=True)
    parser.add_argument('--edit', action='store_true', help='Enable draft intake answers and explicit intent decisions only; no execution')
    parser.add_argument('--allow-build-commands', action='store_true', help='Unavailable in 1.3.0; browser build controls are deferred to 1.4.0')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args(argv)
    if args.allow_build_commands and not _development_profile():
        print(BUILD_UNAVAILABLE, file=sys.stderr)
        return 2
    with CompanionServer(args.task, port=args.port, edit=args.edit, allow_build_commands=args.allow_build_commands) as server:
        mode = 'Intake and intent approval' if args.edit else 'Read-only forms'
        print(f'{mode} companion at {server.origin}; Ctrl-C stops the listener.', flush=True)
        print(f'Private launcher link (grants access to this launch mode): {server.launch_url}', flush=True)
        if not args.no_open:
            try:
                opened = webbrowser.open(server.launch_url)
            except webbrowser.Error:
                opened = False
            if not opened:
                print('Browser did not open. Paste the private launcher link into your browser.', file=sys.stderr, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
