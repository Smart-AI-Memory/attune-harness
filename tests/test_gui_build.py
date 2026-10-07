# qualify: platform
"""Command grants exercise real subprocess builds and retained owner evidence."""
import json
import sys
import time
from threading import Thread

import pytest

pytestmark = pytest.mark.usefixtures('gui_development_profile')

import test_work_build as builds
import test_work_contract as contracts
from test_gui_decisions import call, selected
from attune_harness import gui, work_build
from attune_harness.task_contract import read_task

work = contracts.work


@pytest.fixture
def accepted(work):
    # Use the existing installed-journey peer, never a replacement exchange.
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('gui_install_fixture', Path(__file__).parents[1] / 'scripts/check_installed.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    peer = work[0].parent / 'peer.py'
    peer.write_text(fixture.PEER, encoding='utf-8')
    config = json.loads(work[1].read_text())
    for name in config['participants']:
        config['participants'][name] = {'adapter': 'command', 'command': [sys.executable, '-B', str(peer)],
            'timeout': 10, 'tools': [], 'max_turns': 1, 'max_tool_calls': 0}
    work[1].write_text(json.dumps(config))
    return builds.prepare(work)


@pytest.fixture
def server(accepted):
    with gui.CompanionServer([accepted[1]], edit=True, allow_build_commands=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server
        server.shutdown()
        thread.join(timeout=2)


def preview(server):
    task = selected(server)
    status, shown = call(server, '/build/preview', {k: task[k] for k in ('task', 'checkpoint')})
    assert status == 200, shown
    return shown


def start(server, shown):
    return call(server, '/build/start', {k: shown[k] for k in ('task', 'checkpoint', 'grant')} | {'confirmed': True})


def finish(server, task):
    server.builds.active[task].result(timeout=30)
    return selected(server)['build']


def test_browser_grant_real_build_and_evidence(server, accepted):
    shown = preview(server)
    assert shown['participants'][0]['configuration']['adapter'] == 'command'
    assert shown['effects']['allowed'] == read_task(accepted[1])['request']['effects']['allowed']
    assert 'build' not in read_task(accepted[1])
    assert start(server, shown)[0] == 200
    assert start(server, shown)[0] == 409
    outcome = finish(server, shown['task'])
    assert outcome['view']['status'] == 'completed'
    assert outcome['view']['completed'] == ['export', 'wire']
    assert outcome['reviews'][0]['notes'] == ['Synthetic command fixture']
    assert outcome['available'] is False
    assert 'return 42' in (accepted[0] / 'pkg/export.py').read_text()
    events = read_task(accepted[1])['build']['events']
    assert all(e['result']['passed'] for e in events if e['kind'] == 'acceptance_probe')


def test_replaced_and_restarted_preview_cannot_dispatch(server, accepted):
    old = preview(server)
    current = preview(server)
    assert start(server, old)[0] == 409
    assert 'build' not in read_task(accepted[1])
    # A failed stale attempt consumes the live grant too: explicitly reopen.
    assert start(server, current)[0] == 409
    with gui.CompanionServer([accepted[1]], edit=True, allow_build_commands=True) as restarted:
        with pytest.raises(ValueError, match='Unknown registered task'):
            restarted.builds.start(**{k: old[k] for k in ('task', 'checkpoint', 'grant')}, confirmed=True)
    assert 'build' not in read_task(accepted[1])


def test_source_drift_refuses_previewed_build(server, accepted):
    shown = preview(server)
    (accepted[0] / 'source.py').write_text('changed')
    assert start(server, shown)[0] == 409
    assert 'build' not in read_task(accepted[1])


def test_build_requires_launch_permission(accepted):
    with pytest.raises(ValueError, match='edit mode'):
        gui.CompanionServer([accepted[1]], allow_build_commands=True)
    with gui.CompanionServer([accepted[1]], edit=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True);thread.start()
        try:
            task = selected(server)
            assert call(server, '/build/preview', {k: task[k] for k in ('task', 'checkpoint')})[0] == 409
        finally:
            server.shutdown();thread.join(timeout=2)
    assert 'build' not in read_task(accepted[1])


def test_restart_inspects_paused_owner_and_explicitly_resumes(server, accepted):
    record = work_build.build_work(accepted[1], allow_external=True, max_operations=1)
    assert record['build']['status'] == 'paused'
    before = (accepted[1] / 'record.json').read_bytes()
    shown = preview(server)
    assert shown['resume'] is True
    assert (accepted[1] / 'record.json').read_bytes() == before
    prior = record['build']['events']
    assert start(server, shown)[0] == 200
    finish(server, shown['task'])
    assert read_task(accepted[1])['build']['events'][:len(prior)] == prior


@pytest.mark.parametrize('bad', [{'task': {}}, {'grant': []}, {'confirmed': False}, {'confirmed': 'true'}, {'command': ['echo', 'bad']}])
def test_malformed_grants_never_execute(server, accepted, bad):
    shown = preview(server)
    payload = {k: shown[k] for k in ('task', 'checkpoint', 'grant')} | {'confirmed': True} | bad
    assert call(server, '/build/start', payload)[0] == 409
    assert 'build' not in read_task(accepted[1])


def test_progress_http_remains_responsive_without_duplicate_dispatch(server, accepted, monkeypatch):
    from threading import Event
    entered, release = Event(), Event()
    real = work_build.build_work
    def wait(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return real(*args, **kwargs)
    monkeypatch.setattr(work_build, 'build_work', wait)
    shown = preview(server)
    try:
        assert start(server, shown)[0] == 200
        assert entered.wait(2)
        assert selected(server)['build']['running'] is True
        assert call(server, '/build/preview', {k: shown[k] for k in ('task', 'checkpoint')})[0] == 409
        assert 'build' not in read_task(accepted[1])
    finally:
        release.set()
    assert finish(server, shown['task'])['view']['status'] == 'completed'


@pytest.mark.parametrize('kind', ['file_effect', 'participant_turn', 'acceptance_probe'])
def test_uncertain_journal_stays_inspectable_and_refuses_restart(server, accepted, monkeypatch, kind):
    from attune_harness.review_store import RunStore, PersistenceError
    original = RunStore.save
    def lose(store, record):
        events = record.get('build', {}).get('events', [])
        if events and events[-1]['kind'] == kind and events[-1]['state'] == 'completed':
            raise PersistenceError('lost acknowledgement')
        return original(store, record)
    shown = preview(server)
    with monkeypatch.context() as m:
        m.setattr(RunStore, 'save', lose)
        assert start(server, shown)[0] == 200
        with pytest.raises(PersistenceError):
            server.builds.active[shown['task']].result(timeout=30)
    before = (accepted[1] / 'record.json').read_bytes()
    assert selected(server)['build']['available'] is False
    with gui.CompanionServer([accepted[1]], edit=True, allow_build_commands=True) as restarted:
        task = next(iter(restarted.decisions.tasks))
        inspected = restarted.builds.inspect(task)
        assert inspected['available'] is False
        assert inspected['view']['blocking'] is True
        with pytest.raises(ValueError):
            restarted.builds.preview(task, shown['checkpoint'])
    assert (accepted[1] / 'record.json').read_bytes() == before


def test_no_effect_manifest_and_deterministic_peers_are_not_executable(work):
    contracts.make(work)
    from attune_harness.gui_decisions import Decisions
    from attune_harness.gui_build import Builds
    owners = Decisions([work[2]['directory']]); adapter = Builds(owners)
    try:
        task = next(iter(owners.tasks))
        assert adapter.inspect(task)['available'] is False
    finally:
        adapter.close();owners.close()
    # Separate accepted build with deliberately unsupported deterministic peers.
    work[2]['directory'] = work[0].parent / 'other-task'
    case = builds.prepare(work)
    owners = Decisions([case[1]]);adapter = Builds(owners)
    try:
        task = next(iter(owners.tasks))
        with pytest.raises(ValueError, match='command worker/reviewer'):
            adapter.preview(task, case[2]['checkpoint_digest'])
    finally:
        adapter.close();owners.close()


def test_progress_and_findings_use_the_same_saved_revision(server, accepted, monkeypatch):
    from attune_harness import task_view
    real = task_view.inspect
    first = True
    def finish_between_reads(*args, **kwargs):
        nonlocal first
        if first:
            first = False
            work_build.build_work(accepted[1], allow_external=True)
        return real(*args, **kwargs)
    monkeypatch.setattr(task_view, 'inspect', finish_between_reads)
    task = next(iter(server.decisions.tasks))
    outcome = server.builds.inspect(task)
    assert outcome['view']['status'] == 'completed'
    assert outcome['reviews'][0]['notes'] == ['Synthetic command fixture']


def test_high_review_finding_is_visible_and_blocks_completion(server, accepted):
    from pathlib import Path
    record = read_task(accepted[1])
    peer = Path(record['request']['registry']['participants']['critic']['command'][-1])
    peer.write_text(peer.read_text().replace("'findings':[]", "'findings':[{'id':'missing','severity':'high','text':'Synthetic blocking finding','evidence':['source.py']}]") , encoding='utf-8')
    shown = preview(server)
    assert start(server, shown)[0] == 200
    outcome = finish(server, shown['task'])
    assert outcome['view']['status'] == 'needs_revision'
    assert outcome['reviews'][0]['findings'][0]['text'] == 'Synthetic blocking finding'
    assert outcome['available'] is False
    assert read_task(accepted[1])['status'] == 'accepted'


def test_finishing_before_future_sample_cannot_stop_on_old_evidence(server, accepted):
    task = next(iter(server.decisions.tasks))
    class FinishesOnInspection:
        finished = False
        def done(self):
            if not self.finished:
                self.finished = True
                work_build.build_work(accepted[1], allow_external=True)
            return True
        def result(self):
            return read_task(accepted[1])
    server.builds.active[task] = FinishesOnInspection()
    outcome = server.builds.inspect(task)
    assert outcome['running'] is False
    assert outcome['view']['status'] == 'completed'
    assert outcome['reviews'][0]['notes'] == ['Synthetic command fixture']
