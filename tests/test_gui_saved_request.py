# qualify: platform
"""Read-only saved intent, freshness, and reproducible tutorial preparation."""
import json
from pathlib import Path
import runpy
from threading import Thread

import pytest
from attune_harness import gui
from attune_harness.task_contract import read_task
from test_gui import request
from test_gui_decisions import call, open_form, submission
from test_work_contract import work


def prepare(tmp_path):
    example = Path(__file__).parents[1] / 'examples/browser-intake/prepare.py'
    record = runpy.run_path(str(example))['prepare'](tmp_path / 'training')
    return Path(record['record_path']).parent


def inspect(server):
    code, _, raw = request(server, '/workspace')
    assert code == 200
    return json.loads(raw)['tasks'][0]


def test_draft_save_accept_restart_inspection_has_no_write_or_dispatch(tmp_path):
    path = prepare(tmp_path)
    with gui.CompanionServer([path], edit=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            before = (path / 'record.json').read_bytes()
            saved = inspect(server)['saved_request']
            assert saved['intent']['goal'] is None and saved['intent']['scope'] == ['source.py']
            assert saved['fresh'] and not saved['accepted']
            assert (path / 'record.json').read_bytes() == before
            assert not (path / 'decision.json').exists() and not server.decisions.live
            form = open_form(server)
            assert call(server, '/decision/submit', submission(form, {'answers': {
                'answer_0': 'Group saved work by the decision it needs'}}))[0] == 200
            assert inspect(server)['saved_request']['intent']['goal'] == 'Group saved work by the decision it needs'
            form = open_form(server)
            assert len(form['display']['definition']['fields']) == 1
            assert call(server, '/decision/submit', submission(form, {'answers': {
                'answer_0': 'Each saved task shows its next decision'}}))[0] == 200
            form = open_form(server)
            assert call(server, '/decision/submit', submission(form, {'action': 'approve_task', 'confirmed': True}))[0] == 200
            before = (path / 'record.json').read_bytes()
            decision = (path / 'decision.json').read_bytes()
            saved = inspect(server)['saved_request']
            assert saved['accepted'] and saved['fresh']
            assert saved['revision'] == read_task(path)['request']['revision']
            assert saved['checkpoint'] == read_task(path)['checkpoint_digest']
            assert saved['intent']['acceptance'] == ['Each saved task shows its next decision']
            assert (path / 'record.json').read_bytes() == before
            assert (path / 'decision.json').read_bytes() == decision
            assert not server.decisions.live and server.builds is None
        finally:
            server.shutdown()
            thread.join(timeout=2)
    with gui.CompanionServer([path]) as reopened:
        assert reopened.decisions.inspect()[0]['saved_request'] == saved
        assert not reopened.decisions.live
    assert (path / 'record.json').read_bytes() == before
    assert not {'planning', 'build'} & read_task(path).keys()


def test_accepted_snapshot_is_retained_but_staleness_is_visible(tmp_path):
    path = prepare(tmp_path)
    from attune_harness.work_accept import WorkAcceptance
    import asyncio
    from attune_harness.work_runtime import answer_planning
    answer_planning(path, {'schema_version': 1, 'checkpoint_digest': read_task(path)['checkpoint_digest'],
                          'answers': {'answer_0': 'Sample goal', 'answer_1': 'Sample success'}})
    bridge = WorkAcceptance(path)
    async def accept():
        await bridge.open()
        await bridge.collect({**bridge.decision['display']['response_template'], 'action': 'approve_task', 'confirmed': True})
    asyncio.run(accept())
    before = (path / 'record.json').read_bytes()
    (tmp_path / 'training/project/source.py').write_text('changed input', encoding='utf-8')
    with gui.CompanionServer([path]) as server:
        item = server.decisions.inspect()[0]
        assert not item['saved_request']['fresh'] and item['saved_request']['freshness_note']
        assert item['saved_request']['accepted'] and item['saved_request']['intent']['goal'] == 'Sample goal'
        assert item['heading'] == 'Accepted intent — inputs changed'
        assert 'historical' in item['note'] and not item['available']
        assert not server.decisions.live
    assert (path / 'record.json').read_bytes() == before


def test_training_preparation_refuses_existing_directory(tmp_path):
    path = prepare(tmp_path)
    before = (path / 'record.json').read_bytes()
    example = Path(__file__).parents[1] / 'examples/browser-intake/prepare.py'
    with pytest.raises(FileExistsError):
        runpy.run_path(str(example))['prepare'](tmp_path / 'training')
    assert (path / 'record.json').read_bytes() == before


def test_draft_effects_drift_keeps_every_saved_request_readable(work, tmp_path):
    from test_work_build import prepare as prepare_effects
    prepare_effects(work, accept=False)
    path = work[2]['directory']
    other = prepare(tmp_path)
    before = (path / 'record.json').read_bytes()
    other_before = (other / 'record.json').read_bytes()
    (work[0] / 'unrelated.txt').write_text('Changed frozen input', encoding='utf-8')
    with gui.CompanionServer([path, other]) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            code, _, raw = request(server, '/workspace')
            assert code == 200
            stale, fresh = json.loads(raw)['tasks']
            assert stale['status'] == 'draft' and not stale['available']
            assert not stale['saved_request']['fresh']
            assert 'reconcile' in stale['saved_request']['freshness_note']
            assert stale['saved_request']['intent']['goal'] == 'Export every finding'
            assert fresh['saved_request']['fresh'] and fresh['available']
            assert not server.decisions.live
        finally:
            server.shutdown()
            thread.join(timeout=2)
    assert (path / 'record.json').read_bytes() == before
    assert (other / 'record.json').read_bytes() == other_before
