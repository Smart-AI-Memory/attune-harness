"""Retained prototype checks; --output must name a new evidence directory."""
import json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_checks import prepare_check
r=Path(__file__).parent
preview_url, artifacts = prepare_check(r/'attune-workspace.html')
checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch();page=browser.new_page(viewport={'width':1080,'height':1050});page.set_default_timeout(6000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(preview_url);f=page.frame_locator('iframe')
 def click(name): f.get_by_role('button',name=name,exact=True).click()
 def nav(name): f.locator('aside').get_by_role('button',name=name,exact=True).click()
 def fit():
  for w in [320,736,1024]:
   page.set_viewport_size({'width':w,'height':1050})
   d=page.frames[1].evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');assert d['scroll']<=d['width'],d
 fit();page.set_viewport_size({'width':1080,'height':1050});page.screenshot(path=str(artifacts/'journeys-light.png'),full_page=True)
 click('Try fix a problem →');fit();click('Save fix brief');assert 'fix brief saved in this demo' in f.locator('main').inner_text().lower()
 f.get_by_label('Cause understood?').select_option('unknown');assert 'Clarification + spec' in f.locator('main').inner_text()
 click('Save investigation draft');assert 'required clarification' in f.get_by_role('alert').inner_text()
 f.get_by_label('What remains unknown?').fill('Whether the project switch loses the record or only hides it.')
 f.get_by_label('Next evidence-gathering action').fill('Compare the stored record and list projection before and after switching.')
 click('Save investigation draft');assert 'investigation draft saved in this demo' in f.locator('main').inner_text().lower()
 checks.append('Fix form adapts from short brief to required clarification; each saves the appropriate draft without execution')
 nav('Journeys');click('Try pick an opportunity →');fit();click('Work on this →')
 assert 'Make the next session' in f.get_by_label('Goal',exact=True).input_value()
 f.get_by_label('Your disposition').select_option('revise');f.get_by_label('Reason for the disposition').fill('Need narrower boundaries.')
 click('Record review');assert 'Resolve the review' in f.get_by_role('alert').inner_text()
 f.get_by_label('Your disposition').select_option('disagree');f.get_by_label('Reason for the disposition').fill('The scope explicitly keeps only key decisions, not full transcripts.')
 click('Record review');click('Accept revision 1')
 f.get_by_label('Goal',exact=True).fill('Continue a saved project with its key decisions')
 f.get_by_role('heading',name='Intent & boundaries').click()
 f.get_by_label('Included and excluded scope').fill('One project handoff with visible rationale; exclude transcript replay.')
 f.get_by_role('heading',name='Intent & boundaries').click()
 assert 'accepted r1' in f.locator('main').inner_text().lower()
 assert f.get_by_role('button',name='Accept revision 3',exact=True).is_disabled()
 assert f.locator('.pair').count()==2
 checks.append('Reasoned disagreement is supported; scope-revision disposition blocks acceptance; two edits are compared with the accepted baseline')
 click('Research this goal');click('Load sample findings');fit()
 f.get_by_label('Include this implication in the active spec').first.check()
 nav('Goals');assert 'Make the next action traceable' in f.locator('main').inner_text()
 nav('Research');f.get_by_label('Question to investigate').fill('How should a handoff preserve the reason for a decision?')
 f.get_by_role('heading',name='Research with a purpose.').click()
 assert f.get_by_label('Include this implication in the active spec').count()==0
 nav('Goals');assert 'Make the next action traceable' in f.locator('main').inner_text()
 checks.append('Research implication links to active spec; query edits clear staged findings without silently removing accepted planning evidence')
 nav('Opportunities');f.get_by_role('button',name='Opportunity Turn useful discoveries into chosen work',exact=False).click()
 click('Work on this →');assert f.get_by_label('Goal',exact=True).input_value()=='Turn useful discoveries into chosen work'
 f.get_by_label('Open goal').select_option('continuity');assert f.get_by_label('Goal',exact=True).input_value()=='Continue a saved project with its key decisions'
 checks.append('Different opportunities create coherent separate drafts; the goal picker restores edited content')
 click('Mine this session →');fit()
 f.get_by_label('Review opportunity').fill('Show the next decision beside each saved goal.')
 f.get_by_label('Retention for pushback').select_option('exclude')
 click('Review in Opportunities');assert 'Show the next decision beside each saved goal.' in f.locator('main').inner_text()
 click('Save for later');click('Dismiss');click('Restore')
 nav('Sessions');click('Save handoff & end session 1');fit()
 assert f.get_by_label('Use pushback in the next session').count()==0
 f.get_by_label('Current preference',exact=True).select_option('Terminal first')
 click('Open session 2 with this context');assert 'Reconcile' in f.get_by_role('alert').inner_text()
 f.get_by_label('Reconciliation',exact=True).select_option('adapt')
 f.get_by_label('Reconciliation reason').fill('I am working from the terminal for this slice.')
 click('Open session 2 with this context');assert 'session 2 · proposed next action' in f.locator('main').inner_text().lower()
 f.get_by_text('Inspect the original handoff',exact=True).click()
 assert 'Graphical first' in f.locator('main').inner_text()
 checks.append('Mined opportunities remain accessible across statuses; excluded context stays out; new preference requires reconciliation while sealed history is preserved')
 nav('Context');fit();nav('Now');fit();nav('Goals');fit();nav('Opportunities');fit()
 click('Hide guide');assert f.get_by_role('button',name='Hide guide').count()==0
 nav('Getting started');assert f.get_by_role('button',name='Hide guide').is_visible()
 page.reload();assert 'Show the next decision' in f.locator('main').inner_text()
 nav('Sessions');assert 'session 2 · proposed next action' in f.locator('main').inner_text().lower()
 checks.append('Guide can be hidden and resumed; reload retains drafts, discoveries and resumed session')
 page.set_viewport_size({'width':1080,'height':1050});nav('Opportunities');page.screenshot(path=str(artifacts/'opportunities-light.png'),full_page=True)
 page.emulate_media(color_scheme='dark');nav('Journeys');page.screenshot(path=str(artifacts/'journeys-dark.png'),full_page=True)
 click('Narrow fix');assert 'Short fix brief' in f.locator('main').inner_text()
 click('Uncertain fix');assert 'Clarification + spec' in f.locator('main').inner_text()
 f.get_by_text('Review notes for fix',exact=True).click()
 f.get_by_label('Your UI review notes').fill('Make the uncertainty explanation more concise.')
 click('User preview');assert f.get_by_role('button',name='Uncertain fix',exact=True).count()==0
 click('Author review');f.get_by_text('Review notes for fix',exact=True).click()
 assert f.get_by_label('Your UI review notes').input_value()=='Make the uncertainty explanation more concise.'
 click('Changed preference');assert f.get_by_label('Reconciliation',exact=True).is_visible()
 checks.append('Author state fixtures, UI inventory, per-view review notes and user-preview toggle work')
 assert not errors,errors
 checks.append('All major views fit 320, 736 and 1024 px; no JavaScript errors in exercised journeys')
 browser.close()
(artifacts/'verification.json').write_text(json.dumps({'result':'passed','sha256':hashlib.sha256((r/'attune-workspace.html').read_bytes()).hexdigest(),'checks':checks,'limits':['Authored scenario content, research and review prompts','No live memory, AI host, search or execution integration','No human usability or screen-reader qualification']},indent=2)+'\n')
print(json.dumps(checks,indent=2))
