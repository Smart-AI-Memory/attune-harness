"""Retained prototype checks; --output must name a new evidence directory."""
import json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_checks import prepare_check
r=Path(__file__).parent
preview_url, artifacts = prepare_check(r/'continuity.html')
checks=[]
with sync_playwright() as p:
 b=p.chromium.launch();page=b.new_page(viewport={'width':1080,'height':1000});page.set_default_timeout(5000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(preview_url);f=page.frame_locator('iframe')
 def click(t): f.get_by_role('button',name=t,exact=True).click()
 def fit():
  for w in [320,736,1024]:
   page.set_viewport_size({'width':w,'height':1000})
   d=page.frames[1].evaluate('({w:innerWidth,s:document.documentElement.scrollWidth})')
   assert d['s']<=d['w'],d
 click('Opportunities');assert f.get_by_role('heading',name='No opportunities mined yet').is_visible();click('Back to tutorial');fit()
 click('Use this context →');fit();click('Record decision & mine context →');fit()
 f.get_by_label('Candidate: Opportunity',exact=True).fill('Group saved work by the human decision it needs.')
 f.get_by_label('Carry forward: Opportunity',exact=True).select_option('exclude')
 click('Opportunities');assert 'Group saved work' in f.locator('main').inner_text();click('Work on this')
 assert f.get_by_label('Draft goal',exact=True).input_value().startswith('Group saved work')
 f.get_by_label('Draft done condition',exact=True).fill('I can pick the next decision from the list.')
 click('Save draft goal');assert 'Selected for follow-up' in f.locator('main').inner_text()
 click('Dismiss opportunity');assert 'Dismissed' in f.locator('main').inner_text();click('Save for later');fit()
 checks.append('Opportunity is discoverable, editable through mining, retained despite context exclusion, selectable into a linked draft, dismissible and recoverable')
 click('Back to tutorial');click('Review the handoff →');fit();click('End session 1 & open session 2');fit()
 assert f.locator('aside button[data-act="go:0"]').is_disabled()
 assert f.get_by_label('Use this opportunity in session 2').count()==0
 f.get_by_label('Use this pushback in session 2').uncheck()
 f.get_by_label('Current interface preference').select_option('graphical')
 click('Check context & changes →');fit()
 assert f.get_by_role('button',name='Prepare session 2 brief →').is_disabled()
 click('Choose adapt the presentation')
 f.get_by_label('Reason for this reconciliation').fill('I want to inspect the next decision visually today.')
 f.get_by_role('heading',name='A preference changed. Keep the reason visible.').click()
 click('Prepare session 2 brief →');fit()
 assert 'Excluded this session: Pushback' in f.locator('main').inner_text()
 assert 'Graphical first' in f.locator('main').inner_text()
 click('Finish tutorial');assert f.get_by_role('heading',name='You continued the work, not the setup.').is_visible()
 checks.append('Sealed handoff survives transition; excludes unselected context, preserves history, and requires reasoned reconciliation before resumption')
 page.reload();assert f.get_by_role('heading',name='You continued the work, not the setup.').is_visible()
 click('Opportunities');click('Open draft goal');assert f.get_by_label('Draft done condition').input_value()=='I can pick the next decision from the list.'
 checks.append('Reload retains completed tutorial, opportunity review state and edited linked draft')
 page.set_viewport_size({'width':1080,'height':1000});page.screenshot(path=str(artifacts/'opportunity-draft.png'),full_page=True)
 click('← Opportunities');page.emulate_media(color_scheme='dark');page.screenshot(path=str(artifacts/'opportunities-dark.png'),full_page=True)
 checks.append('Seven tutorial stages and opportunity list fit 320, 736 and 1024 pixels')
 assert not errors,errors
 checks.append('No JavaScript errors in exercised journeys')
 b.close()
(artifacts/'verification.json').write_text(json.dumps({'result':'passed','sha256':hashlib.sha256((r/'continuity.html').read_bytes()).hexdigest(),'checks':checks,'limits':['Simulated sessions and persistence','No real memory, research, host connection or execution','No human usability or screen-reader qualification']},indent=2)+'\n')
print(json.dumps(checks,indent=2))
