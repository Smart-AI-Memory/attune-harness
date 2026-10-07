"""Retained prototype checks; --output must name a new evidence directory."""
import json, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_checks import prepare_check
root=Path(__file__).parent
preview_url, artifacts = prepare_check(root/'spec-studio.html')
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    page.set_default_timeout(5000)
    page.goto(preview_url)
    f=page.frame_locator('iframe')
    def click(n): f.get_by_role('button',name=n,exact=True).click()
    click('Shape this idea →')
    f.get_by_label('Goal',exact=True).fill('Create a searchable recipe collection')
    click('Continue to research →')
    click('Skip research →')
    f.get_by_role('button',name='Shared local task record',exact=False).click()
    f.get_by_role('button',name='Show a resume preview',exact=False).click()
    click('Compare approaches →')
    click('Create sample specification →')
    body=f.locator('main').inner_text()
    assert f.get_by_label('Goal',exact=True).input_value()=='Create a searchable recipe collection' and 'Build the navigator' in body
    results.append({'case':'Unrelated new goal','observed':'Edited recipe goal appears, but implementation tasks still build a saved-work navigator','verdict':'Fixed scenario only; arbitrary goal authoring unsupported'})
    f.get_by_role('button',name='Review this revision →',exact=True).first.click()
    click('Apply suggested requirement')
    click('Run sample review for r2')
    click('Inspect acceptance & handoff →')
    click('Accept revision 2 in this demo')
    f.locator('aside button[data-action="go:1"]').click()
    f.get_by_label('Questions to investigate').fill('What recipe search methods are suitable?')
    f.get_by_role('heading',name='Then look beyond the project').click()
    assert 'Review is required again' in f.get_by_role('status').inner_text()
    f.locator('aside button[data-action="go:6"]').click()
    assert 'Accepted r2' in f.locator('main').inner_text()
    results.append({'case':'Change research question after acceptance','observed':'Status says review required, but revision 2 stays accepted','verdict':'Inconsistent freshness messaging; questions are not versioned into spec/export'})
    f.locator('aside button[data-action="go:4"]').click()
    f.get_by_label('Goal',exact=True).fill('First edited outcome')
    f.get_by_role('heading',name='Outcome & boundaries').click()
    f.get_by_label('Included scope',exact=True).fill('Second edit to scope')
    f.get_by_role('heading',name='Outcome & boundaries').click()
    f.get_by_role('button',name='Review this revision →',exact=True).first.click()
    body=f.locator('main').inner_text()
    assert 'Second edit to scope' in body and 'First edited outcome' not in body
    results.append({'case':'Review multiple changes since accepted version','observed':'Review comparison displays only latest field change, not all changes since accepted revision','verdict':'Partial revision comparison; no accepted-baseline diff'})
    browser.close()
report={'prototype_sha256':hashlib.sha256((root/'spec-studio.html').read_bytes()).hexdigest(),'method':'Chromium interaction with local fixture host; observations, not production tests','results':results}
(artifacts/'use-case-review-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
