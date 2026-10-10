"""Installed 1.3 browser forms boundary, without the development fixture.
# qualify: platform
"""
import json
import subprocess
import sys
from threading import Thread

import pytest
import test_work_contract as contracts
from test_gui import request
from test_gui_decisions import call, selected, open_form, submission, answer_all
from attune_harness import gui
from attune_harness.features import FeatureUnavailable
from attune_harness.task_contract import read_task

work = contracts.work

@pytest.fixture
def forms(work):
    work[2]['intent'].update(goal=None, acceptance=[])
    work[2]['choices'] = [contracts.choice()]
    contracts.make(work)
    with gui.CompanionServer([work[2]['directory']], edit=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server
        server.shutdown()
        thread.join(timeout=2)


def test_release_forms_real_intake_preview_accept_and_replay(forms):
    assert forms.forms_only and forms.builds is None
    path = forms.tasks[0]
    answer_all(forms)
    assert read_task(path)['status'] == 'draft'
    shown = open_form(forms)
    assert shown['display']['kind'] == 'spec'
    assert {a['id'] for a in shown['display']['actions']} <= {'approve_task', 'redo_task'}
    payload = submission(shown, {'action': 'approve_task', 'confirmed': True})
    assert call(forms, '/decision/submit', payload)[0] == 200
    assert read_task(path)['status'] == 'accepted'
    assert call(forms, '/decision/submit', payload)[0] == 409
    card = selected(forms)
    assert not card['available']
    assert card['heading'] == 'Intent accepted'
    assert card['note'] == 'Intake and intent review are complete. No further intent form is needed; execution remains separate.'
    assert 'Only feature-work drafts' not in card['note']
    assert not {'planning', 'build'} & read_task(path).keys()


@pytest.mark.parametrize('endpoint', ['/build/preview', '/build/start', '/build/resume', '/resume', '/grant', '/decision/submit?build=1'])
def test_direct_http_execution_routes_absent_before_and_after_accept(forms, endpoint):
    path = forms.tasks[0]
    before = (path / 'record.json').read_bytes()
    assert call(forms, endpoint, {'task': 'forged', 'checkpoint': 'forged', 'grant': 'forged', 'confirmed': True})[0] == 404
    assert (path / 'record.json').read_bytes() == before
    answer_all(forms)
    shown = open_form(forms)
    assert call(forms, '/decision/submit', submission(shown, {'action': 'approve_task', 'confirmed': True}))[0] == 200
    before = (path / 'record.json').read_bytes()
    assert call(forms, endpoint, {'task': shown['task'], 'checkpoint': read_task(path)['checkpoint_digest'], 'grant': 'forged', 'confirmed': True})[0] == 404
    assert (path / 'record.json').read_bytes() == before
    assert forms.builds is None and 'build' not in read_task(path)


def test_forms_assets_and_navigation_exclude_broader_gui(forms):
    assert request(forms, '/snapshot')[0] == 404
    assert request(forms, '/workspace')[0] == 200
    data = json.loads(request(forms, '/workspace')[2])
    assert all('build' not in item for item in data['tasks'])
    page = request(forms, '/', token=False)[2]
    script = request(forms, '/app.js', token=False)[2]
    stylesheet = request(forms, '/style.css', token=False)[2]
    assert '.task-card p{margin:8px 0;overflow-wrap:anywhere}' in stylesheet
    assert '#browser-tip:not([hidden]){flex-basis:100%;' in stylesheet
    assert '.saved-answers p,.saved-answers li,.approval-answers p,.approval-answers li,.saved-goal{white-space:pre-wrap}' in stylesheet
    assert '.technical-input,.owner-record{font-family:ui-monospace,' in stylesheet
    assert 'textarea,select{' in stylesheet and 'font:inherit' in stylesheet
    assert '<pre class="technical-input">' in page
    assert 'Intake and intent approval' in page and '<iframe' not in page
    assert '<h1 id="decision-heading">Saved work</h1>' in page
    for forbidden in ('/build/', '/snapshot', 'renderBuildGrant', 'watchBuild', 'auto_run_remaining'):
        assert forbidden not in script


@pytest.mark.parametrize('kwargs', [{'allow_build_commands': True}, {'edit': True, 'allow_build_commands': True}])
def test_imported_build_flag_refuses_before_effects(monkeypatch, kwargs):
    class Untouched:
        def __iter__(self):
            pytest.fail('Build refusal must precede task iteration')
    def forbidden(*args, **kw):
        pytest.fail('Build refusal must precede listener/owner effects')
    monkeypatch.setattr(gui.HTTPServer, '__init__', forbidden)
    monkeypatch.setattr(gui.task_view, 'inspect_saved_tasks', forbidden)
    with pytest.raises(FeatureUnavailable, match='deferred to 1.4.0'):
        gui.CompanionServer(Untouched(), **kwargs)


def test_installed_module_build_flag_refuses_without_task_state(tmp_path):
    task = tmp_path / 'absent-task'
    result = subprocess.run([sys.executable, '-I', '-m', 'attune_harness.gui', '--task', str(task), '--edit', '--allow-build-commands'], cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 2 and 'deferred to 1.4.0' in result.stderr
    assert not result.stdout and not task.exists()


def test_release_form_boundary_stale_foreign_origin_and_dispatch_choice(forms):
    shown = open_form(forms)
    payload = submission(shown, {'answers': {'answer_0': 'Safe local intent'}})
    assert call(forms, '/decision/submit', payload, headers={'Origin': 'https://foreign.example'})[0] == 403
    assert call(forms, '/decision/submit', payload, token=False)[0] == 403
    second = open_form(forms)
    assert call(forms, '/decision/submit', payload)[0] == 409
    assert call(forms, '/decision/submit', submission(second, {'answers': {'answer_0': 'Safe local intent'}}))[0] == 200
    intake = open_form(forms)
    answers = {f['id']: (f['options'][0] if f['type'] == 'single_select' else 'The value function is retained') for f in intake['display']['definition']['fields']}
    assert call(forms, '/decision/submit', submission(intake, {'answers': answers}))[0] == 200
    shown = open_form(forms)
    assert call(forms, '/decision/submit', submission(shown, {'action': 'auto_run_remaining', 'confirmed': True}))[0] == 409
    assert read_task(forms.tasks[0])['status'] == 'draft'


def test_read_only_release_lists_registered_draft_without_mutation(work):
    contracts.make(work)
    path = work[2]['directory']
    before = (path / 'record.json').read_bytes()
    with gui.CompanionServer([path]) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            data = json.loads(request(server, '/workspace')[2])
            assert not data['editable'] and len(data['tasks']) == 1
            assert data['tasks'][0]['status'] == 'draft'
            assert call(server, '/decision/open', {k: data['tasks'][0][k] for k in ('task', 'checkpoint')})[0] == 405
            assert call(server, '/decision/restore', {k: data['tasks'][0][k] for k in ('task', 'checkpoint')} | {
                'view': 'view-' + 'a' * 32, 'decision': 'unknown'})[0] == 405
            assert (path / 'record.json').read_bytes() == before
        finally:
            server.shutdown()
            thread.join(timeout=2)
