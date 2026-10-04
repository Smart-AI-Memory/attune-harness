"""DOM checks plus optional real sandboxed blob checks; no task actions or models.

# qualify: platform
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import test_work_contract as contracts
from attune_harness import gui, task_view
from test_task_view import Page, files_under, second_task

work = contracts.work


def chrome_dom(path, tmp_path):
    if os.environ.get('ATTUNE_BROWSER_TESTS') != '1':
        pytest.skip('Set ATTUNE_BROWSER_TESTS=1 for optional real Chrome checks')
    chrome = shutil.which('chromium') or shutil.which('google-chrome')
    mac_chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    if not chrome and mac_chrome.exists():
        chrome = str(mac_chrome)
    if not chrome:
        pytest.skip('Chrome/Chromium is required for the sandboxed blob browser check')
    result = subprocess.run([chrome, '--headless', '--no-first-run', '--disable-background-networking',
                             '--disable-extensions', '--disable-component-update',
                             '--user-data-dir=' + str(tmp_path / 'chrome-profile'),
                             '--virtual-time-budget=4000', '--dump-dom', path.as_uri()],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


def test_saved_navigation_targets_and_hashed_script_preserve_security(work):
    contracts.make(work)
    before = files_under(work[0].parent)
    entries = task_view.inspect_saved_tasks(work[2]['directory'], [])
    rendered = task_view.render_saved_tasks(entries, 'html')
    page = Page(); page.feed(rendered)
    targets = [a for tag, a in page.tags if tag == 'a' and 'data-saved-target' in a]
    ids = {a['id'] for _, a in page.tags if 'id' in a}
    assert len(targets) == 2
    assert all(a['href'] == '#' + a['data-saved-target'] for a in targets)
    assert all(a['data-saved-target'] in ids for a in targets)
    digest = base64.b64encode(hashlib.sha256(task_view._REPLY_SCRIPT.encode()).digest()).decode()
    csp = next(a['content'] for _, a in page.tags if a.get('http-equiv') == 'Content-Security-Policy')
    assert "script-src 'sha256-" + digest + "'" in csp
    assert "connect-src 'none'" in csp and "base-uri 'none'" in csp
    assert files_under(work[0].parent) == before


@pytest.mark.parametrize('initial_fragment', ['', '#missing', '#first'])
def test_navigation_in_chrome_sandboxed_blob_with_reload(work, tmp_path, initial_fragment):
    contracts.make(work)
    entries = task_view.inspect_saved_tasks(work[2]['directory'], [second_task(work)])
    snapshot = task_view.render_saved_tasks(entries, 'html')
    first = re.search(r'data-saved-target="(task-[^"]+)"', snapshot).group(1)
    fragment = initial_fragment.replace('first', first)
    # Test-only probe runs inside the opaque-origin iframe. Its sole extra effect
    # is reporting assertions to the outer test document via postMessage.
    probe = r"""
try {
 const home=document.getElementById('saved-tasks'),tasks=[...document.querySelectorAll('.saved-task')];
 const check=(ok,label)=>{if(!ok)throw Error(label);};
 const visible=()=>[home,...tasks].filter(p=>getComputedStyle(p).display!=='none');
 const start=location.hash.slice(1),expected=tasks.find(p=>p.id===start)||home;
 check(visible().length===1&&visible()[0]===expected,'initial selection');
 const initialHash=location.hash;
 for(const task of [tasks[0],tasks[1],tasks[0]]){
  const link=home.querySelector('[data-saved-target="'+task.id+'"]');
  const event=new MouseEvent('click',{bubbles:true,cancelable:true,button:0});
  check(!link.dispatchEvent(event),'default blob navigation cancelled');
  check(visible().length===1&&visible()[0]===task,'selected briefing visible');
  check(document.activeElement===task.querySelector('h1'),'briefing focus');
  check(location.hash===initialHash,'no fragment navigation');
  task.querySelector('[data-saved-target="saved-tasks"]').click();
  check(visible().length===1&&visible()[0]===home,'return to list');
  check(document.activeElement===home.querySelector('h1'),'list focus');
 }
 parent.postMessage({ok:true},'*');
}catch(error){parent.postMessage({ok:false,error:error.message},'*');}
"""
    original_hash = base64.b64encode(hashlib.sha256(task_view._REPLY_SCRIPT.encode()).digest()).decode()
    instrumented = task_view._REPLY_SCRIPT + probe
    probe_hash = base64.b64encode(hashlib.sha256(instrumented.encode()).digest()).decode()
    snapshot = snapshot.replace(original_hash, probe_hash).replace(
        '<script>' + task_view._REPLY_SCRIPT + '</script>', '<script>' + instrumented + '</script>')
    wrapper = """<!doctype html><iframe sandbox="allow-scripts"></iframe><pre id="result">PENDING</pre><script>
const frame=document.querySelector('iframe');
const url=URL.createObjectURL(new Blob([SNAPSHOT],{type:'text/html'}))+FRAGMENT;
let count=0;
window.addEventListener('message',event=>{
 if(event.source!==frame.contentWindow)return;
 if(!event.data.ok){document.querySelector('#result').textContent='FAIL '+event.data.error;return;}
 if(++count===2){document.querySelector('#result').textContent='PASS navigation and reload';return;}
 frame.src='about:blank';setTimeout(()=>{frame.src=url;},0);
});
frame.src=url;
</script>""".replace('SNAPSHOT', json.dumps(snapshot).replace('<', '\\u003c')).replace('FRAGMENT', json.dumps(fragment))
    path = tmp_path / 'navigation.html'; path.write_text(wrapper)
    dom = chrome_dom(path, tmp_path)
    assert '<pre id="result">PASS navigation and reload</pre>' in dom, dom[-3000:]


def test_refresh_click_identical_snapshot_failure_and_page_reload(tmp_path):
    # Exercise the actual launcher script with read-only fetch responses. This
    # verifies handlers/feedback, not an embedded browser's chrome reload control.
    stub = r"""
const calls=[];let refuse=false;
sessionStorage.setItem('attune-gui-token','offline-test');
window.fetch=async(path,options)=>{
 calls.push({path,options});
 if(options.method&&options.method!=='GET')throw Error('Unexpected task action');
 if(path==='/snapshot')return {ok:!refuse,text:async()=>refuse?'offline failure':'<!doctype html><h1>Unchanged saved task</h1>'};
 if(path==='/workspace')return {ok:true,json:async()=>({editable:false,tasks:[]})};
 throw Error('Unexpected resource '+path);
};
"""
    probe = r"""
(async()=>{
 const check=(ok,label)=>{if(!ok)throw Error(label);};
 const settle=async()=>{for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,10));if(!busy&&!document.querySelector('#refresh').disabled&&calls.some(c=>c.path==='/workspace'))return;}throw Error('refresh did not settle');};
 try{
  await settle();check(calls.filter(c=>c.path==='/snapshot').length===1,'initial snapshot request');
  check(status.textContent.includes('Snapshot refreshed'),'initial feedback');
  if(sessionStorage.getItem('reload-tested')){
   document.querySelector('#result').textContent='PASS refresh and full page reload';return;
  }
  const prior=frame.src;document.querySelector('#refresh').click();
  check(document.querySelector('#refresh').disabled,'refresh pending feedback');
  await settle();check(calls.filter(c=>c.path==='/snapshot').length===2,'refresh issued GET');
  check(frame.src!==prior,'identical snapshot replaced');check(status.textContent.includes('Snapshot refreshed'),'success feedback');
  refuse=true;document.querySelector('#refresh').click();await settle();
  check(status.textContent.includes('Refresh failed')&&status.textContent.includes('offline failure'),'failure feedback');
  check(!document.querySelector('#refresh').disabled,'retry remains available');
  refuse=false;document.querySelector('#refresh').click();await settle();
  check(status.textContent.includes('Snapshot refreshed'),'recovery feedback');
  check(calls.every(c=>!c.options.method||c.options.method==='GET'),'read only requests');
  sessionStorage.setItem('reload-tested','yes');location.reload();
 }catch(error){document.querySelector('#result').textContent='FAIL '+error.message;}
})();
"""
    page = gui.PAGE.replace('<script src="/app.js"></script>',
                            '<pre id="result">PENDING</pre><script>' + stub + gui.SCRIPT + probe + '</script>')
    path = tmp_path / 'refresh.html'; path.write_text(page)
    dom = chrome_dom(path, tmp_path)
    assert '<pre id="result">PASS refresh and full page reload</pre>' in dom, dom[-3000:]


def test_dom_briefing_selection_focus_repeat_and_fresh_document(work):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node with jsdom is required for the optional DOM regression')
    available = subprocess.run([node, '-e', "require('jsdom')"], capture_output=True)
    if available.returncode:
        pytest.skip('jsdom is not installed; run the browser regression separately')
    contracts.make(work)
    entries = task_view.inspect_saved_tasks(work[2]['directory'], [second_task(work)])
    snapshot = task_view.render_saved_tasks(entries, 'html')
    runner = r"""
const {JSDOM}=require('jsdom');const fs=require('fs'),html=fs.readFileSync(0,'utf8');
function check(ok,label){if(!ok)throw Error(label);}
for(const fragment of ['', '#missing', '#'+html.match(/data-saved-target="(task-[^"]+)"/)[1]]){
 for(let reload=0;reload<2;reload++){
  const dom=new JSDOM(html,{url:'http://127.0.0.1/snapshot'+fragment,runScripts:'dangerously',
    beforeParse(w){w.HTMLElement.prototype.scrollIntoView=function(){};}});
  const w=dom.window,d=w.document,home=d.getElementById('saved-tasks'),tasks=[...d.querySelectorAll('.saved-task')];
  const visible=()=>[home,...tasks].filter(p=>w.getComputedStyle(p).display!=='none');
  const expected=tasks.find(p=>'#'+p.id===fragment)||home;
  check(visible().length===1&&visible()[0]===expected,'initial or restored selection');
  for(const task of [tasks[0],tasks[1],tasks[0]]){
   const link=home.querySelector('[data-saved-target="'+task.id+'"]');
   check(!link.dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true,button:0})),'cancel native navigation');
   check(visible().length===1&&visible()[0]===task,'one selected briefing');
   check(d.activeElement===task.querySelector('h1'),'heading focus');
   check(w.location.hash===fragment,'blob fragment unchanged');
   task.querySelector('[data-saved-target="saved-tasks"]').click();
   check(visible().length===1&&visible()[0]===home,'return to list');
   check(d.activeElement===home.querySelector('h1'),'list focus');
  }
  dom.window.close();
 }
}
console.log('PASS DOM selection, focus, repeats and fresh document');
"""
    result = subprocess.run([node, '-e', runner], input=snapshot, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert 'PASS DOM selection' in result.stdout


def test_dom_refresh_handlers_identical_snapshot_and_failure_feedback():
    node = shutil.which('node')
    if not node or subprocess.run([node, '-e', "require('jsdom')"], capture_output=True).returncode:
        pytest.skip('Node with jsdom is required for the optional DOM regression')
    runner = r"""
const {JSDOM}=require('jsdom');const fs=require('fs'),input=JSON.parse(fs.readFileSync(0,'utf8'));
function check(ok,label){if(!ok)throw Error(label);}
(async()=>{
 for(let reload=0;reload<2;reload++){
  const dom=new JSDOM(input.page,{url:'http://127.0.0.1/',runScripts:'outside-only'});
  const w=dom.window,d=w.document,calls=[];let refuse=false,serial=0;const revoked=[];
  w.sessionStorage.setItem('attune-gui-token','offline-test');
  w.URL.createObjectURL=()=> 'blob:http://127.0.0.1/'+(++serial);
  w.URL.revokeObjectURL=url=>revoked.push(url);
  w.fetch=async(path,options)=>{
   calls.push({path,options});
   if(options.method&&options.method!=='GET')throw Error('Unexpected task action');
   if(path==='/snapshot')return {ok:!refuse,text:async()=>refuse?'offline failure':'<h1>Unchanged saved task</h1>'};
   if(path==='/workspace')return {ok:true,json:async()=>({editable:false,tasks:[]})};
   throw Error('Unexpected resource '+path);
  };
  w.eval(input.script);
  const settle=()=>new Promise(r=>setTimeout(r,5));await settle();
  const status=d.getElementById('status'),button=d.getElementById('refresh'),frame=d.querySelector('iframe');
  check(calls.filter(c=>c.path==='/snapshot').length===1,'fresh document request');
  check(status.textContent.includes('Snapshot refreshed'),'bootstrap feedback');
  const prior=frame.src;button.click();check(button.disabled,'pending feedback');await settle();
  check(calls.filter(c=>c.path==='/snapshot').length===2,'refresh GET');
  check(frame.src!==prior,'identical snapshot replaced');
  frame.dispatchEvent(new w.Event('load'));check(revoked.includes(prior),'obsolete blob released after load');
  check(status.textContent.includes('Snapshot refreshed'),'success feedback');
  const retained=frame.src;refuse=true;button.click();await settle();
  check(frame.src===retained,'failed refresh keeps prior snapshot');
  check(status.textContent.includes('Refresh failed')&&status.textContent.includes('offline failure'),'error feedback');
  check(!button.disabled,'retry available');
  refuse=false;button.click();await settle();check(status.textContent.includes('Snapshot refreshed'),'recovery feedback');
  check(calls.every(c=>!c.options.method||c.options.method==='GET'),'all requests read only');
  dom.window.close();
 }
 console.log('PASS DOM refresh, errors and fresh-document bootstrap');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run([node, '-e', runner], input=json.dumps({'page': gui.PAGE, 'script': gui.SCRIPT}),
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert 'PASS DOM refresh' in result.stdout
