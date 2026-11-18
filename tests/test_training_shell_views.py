"""Check shell-specific course commands and preserve independent learner state."""

from html import escape
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"
COURSE = TRAINING / "reporting"


@pytest.fixture
def builder():
    spec = importlib.util.spec_from_file_location("training_shell_views", TRAINING / "build_course.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reading_projection_includes_both_shells_without_relabeling_prompts(builder):
    outputs = builder.project()
    variants = 0
    for slug in builder.SLUGS:
        lesson = json.loads(outputs[COURSE / slug / "lesson.json"])
        reading = outputs[COURSE / slug / "read.html"]
        expected = [copy for section in lesson["sections"] for copy in section.get("copies", [])]
        variant_count = sum("powershell" in copy for copy in expected)
        variants += variant_count
        assert reading.count('<h4>macOS/Linux — Bash or Zsh</h4>') == variant_count
        assert reading.count('<h4>Windows PowerShell 5.1 or 7</h4>') == variant_count
        assert "<script" not in reading
        for copy in expected:
            assert escape(copy["text"]) in reading
            if "powershell" in copy:
                assert escape(copy["powershell"]) in reading
            if copy.get("kind") == "prompt":
                assert reading.count(escape(copy["text"])) == 1
    assert variants, "Exercise at least one authored Windows command in the real course"


@pytest.mark.parametrize("variant", [None, 3, [], {}, "", " \n"])
def test_renderer_rejects_invalid_windows_variant(builder, variant):
    with pytest.raises(ValueError, match="Invalid PowerShell copy"):
        builder.reading_copy({"label": "Command", "text": "python run.py", "powershell": variant})


def test_renderer_keeps_prompts_neutral_and_escapes_both_variants(builder):
    prompt = {"label": "Goal", "text": "Keep my wording <exactly>.", "kind": "prompt"}
    assert builder.reading_copy(prompt).count("Keep my wording &lt;exactly&gt;.") == 1
    with pytest.raises(ValueError, match="Invalid PowerShell copy"):
        builder.reading_copy({**prompt, "powershell": "Changed wording"})
    text = builder.reading_copy({"label": "<Command>", "text": "echo '<unix>'", "powershell": "Write-Output '<windows>'"})
    assert "<unix>" not in text and "<windows>" not in text
    assert "&lt;unix&gt;" in text and "&lt;windows&gt;" in text


def test_browser_shell_selection_copy_fallback_and_storage_boundaries():
    node = shutil.which("node")
    if not node or subprocess.run([node, "-e", "require('jsdom')"], capture_output=True).returncode:
        pytest.skip("Node with jsdom is required for the optional DOM regression")
    lesson = {
        "title": "Shell views", "storageKey": "existing-lesson-key", "sections": [{
            "id": "section-1", "navTitle": "Commands", "phase": "Practice",
            "title": "Run a command", "intro": "Choose your shell.",
            "html": '<label for="unchanged-answer">Your notes</label><textarea id="unchanged-answer" data-save="answer"></textarea>',
            "copies": [
                {"label": "command", "text": "printf '%s' '$HOME'", "powershell": "Write-Output '$HOME'"},
                {"label": "prompt", "text": "Keep This Wording.", "kind": "prompt"},
                {"label": "neutral", "text": "python --version"},
            ],
        }],
    }
    payload = {
        "template": (TRAINING / "lesson-template.html").read_text(),
        "script": (COURSE / "assets/app.js").read_text(),
        "lesson": lesson,
    }
    runner = r"""
const {JSDOM} = require('jsdom');
const assert = require('node:assert/strict');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const key = 'attune-reporting-course-shell-v1';
const sleep = () => new Promise(resolve => setImmediate(resolve));
async function load({platform='Win32', saved, blocked=false, source=input.lesson}={}) {
  let finishWrite;
  const writes = [];
  const html = input.template.replace('<script src="../assets/app.js" defer></script>', '')
    .replace('</body>', '<script>'+input.script+'</script></body>');
  const dom = new JSDOM(html, {url:'https://course.test/reporting/02-build/', runScripts:'dangerously', beforeParse(w) {
    Object.defineProperty(w.navigator, 'platform', {value:platform});
    w.matchMedia = () => ({matches:false, addEventListener(){}});
    w.fetch = async () => ({ok:true, json:async () => JSON.parse(JSON.stringify(source))});
    w.localStorage.setItem('existing-lesson-key', JSON.stringify({currentId:'section-1',visited:['section-1'],notes:{answer:'My Saved Answer'}}));
    if(saved !== undefined) w.localStorage.setItem(key,saved);
    if(blocked) Object.defineProperty(w,'localStorage',{get(){throw new Error('Storage denied');}});
    w.Blob = Blob;
    w.ClipboardItem = class { constructor(data){this.data=data;} };
    Object.defineProperty(w.navigator, 'clipboard', {configurable:true,value:{write(items){
      writes.push(items[0]);
      return new Promise(resolve => {finishWrite=resolve;});
    }}});
    w.confirm = () => true;
  }});
  for(let i=0;i<20 && !dom.window.document.getElementById('loading-message').hidden;i++) await sleep();
  return {dom, w:dom.window,d:dom.window.document,writes,finish:()=>finishWrite()};
}
function change(w,value) {
  const select=w.document.getElementById('command-shell');
  select.value=value;select.dispatchEvent(new w.Event('change',{bubbles:true}));
}
function sameText(d,expected) {
  const group=d.querySelector('.copy-block');
  assert.equal(group.querySelector('code').textContent,expected);
  assert.equal(group.querySelector('.manual-copy textarea').value,expected);
}
(async()=>{
  const session=await load();const {w,d,writes}=session;
  const select=d.getElementById('command-shell'), group=d.querySelector('.copy-block');
  assert.equal(select.value,'powershell');assert.equal(select.disabled,false);
  sameText(d,input.lesson.sections[0].copies[0].powershell);
  assert.equal(group.querySelector('.copy-shell').textContent,'Windows PowerShell 5.1 or 7');
  const originalSaved=w.localStorage.getItem('existing-lesson-key');
  assert.equal(d.getElementById('unchanged-answer').value,'My Saved Answer');
  group.querySelector('.copy-actions button').click();
  assert.equal(select.disabled,true);
  change(w,'posix');assert.equal(select.value,'powershell');
  sameText(d,input.lesson.sections[0].copies[0].powershell);
  assert.equal(await writes[0].data['text/plain'].text(),group.querySelector('code').textContent);
  session.finish();await sleep();assert.equal(select.disabled,false);
  assert.match(group.querySelector('.copy-status').textContent,/Copied/);
  group.querySelectorAll('.copy-actions button')[1].click();
  assert.equal(group.querySelector('.manual-copy').hidden,false);
  change(w,'posix');sameText(d,input.lesson.sections[0].copies[0].text);
  assert.equal(group.querySelector('.copy-status').textContent,'');
  assert.equal(group.querySelector('.copy-shell').textContent,'macOS/Linux — Bash or Zsh');
  assert.equal(w.localStorage.getItem(key),'posix');
  assert.equal(w.localStorage.getItem('existing-lesson-key'),originalSaved);
  assert.equal(d.getElementById('unchanged-answer').value,'My Saved Answer');
  assert.equal(d.querySelector('[data-copy-kind="prompt"] code').textContent,'Keep This Wording.');
  assert.equal(d.querySelectorAll('.copy-block')[2].querySelector('code').textContent,'python --version');
  Object.defineProperty(w.navigator,'clipboard',{configurable:true,value:{write:async()=>{throw new Error('Denied');}}});
  group.querySelector('.copy-actions button').click();await sleep();
  assert.equal(group.querySelector('.manual-copy').hidden,false);
  sameText(d,input.lesson.sections[0].copies[0].text);
  group.querySelectorAll('.copy-actions button')[1].click();
  const field=group.querySelector('.manual-copy textarea');
  assert.equal(field.selectionStart,0);assert.equal(field.selectionEnd,field.value.length);
  w.localStorage.setItem('another-lesson','unchanged');
  d.getElementById('reset-progress').click();
  assert.equal(w.localStorage.getItem(key),'posix');
  assert.equal(w.localStorage.getItem('another-lesson'),'unchanged');
  assert.equal(d.getElementById('unchanged-answer').value,'');
  session.dom.window.close();

  for(const [platform,saved,expected] of [['Win32','posix','posix'],['MacIntel','powershell','powershell'],['Win32','invalid','powershell'],['',undefined,'posix']]) {
    const s=await load({platform,saved});assert.equal(s.d.getElementById('command-shell').value,expected);s.dom.window.close();
  }
  const blocked=await load({blocked:true});
  assert.equal(blocked.d.getElementById('load-error').hidden,true);
  assert.equal(blocked.d.getElementById('shell-storage-notice').hidden,false);
  change(blocked.w,'posix');sameText(blocked.d,input.lesson.sections[0].copies[0].text);
  assert.equal(blocked.d.getElementById('command-shell').disabled,false);
  blocked.dom.window.close();

  const writeDenied=await load({platform:'MacIntel'});
  writeDenied.w.Storage.prototype.setItem=function(){throw new Error('Write denied');};
  change(writeDenied.w,'powershell');sameText(writeDenied.d,input.lesson.sections[0].copies[0].powershell);
  assert.equal(writeDenied.d.getElementById('shell-storage-notice').hidden,false);
  assert.equal(writeDenied.d.getElementById('load-error').hidden,true);
  writeDenied.dom.window.close();

  for(const invalid of [null,3,[],{},'', '  ']) {
    const source=JSON.parse(JSON.stringify(input.lesson));source.sections[0].copies[0].powershell=invalid;
    const s=await load({source});assert.equal(s.d.getElementById('load-error').hidden,false);assert.equal(s.d.querySelectorAll('.copy-block').length,0);s.dom.window.close();
  }
  const source=JSON.parse(JSON.stringify(input.lesson));source.sections[0].copies[1].powershell='Do not rewrite a prompt';
  const badPrompt=await load({source});assert.equal(badPrompt.d.getElementById('load-error').hidden,false);badPrompt.dom.window.close();
  console.log('PASS shell selection, clipboard, manual copy, storage and refusal boundaries');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run([node, "-e", runner], input=json.dumps(payload), text=True,
                            encoding="utf-8", capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS shell selection" in result.stdout
