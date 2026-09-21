"""Real assessed-file writes preserve provenance across repair and recovery."""
import copy
import json
import os
from pathlib import Path
import sys

import pytest

from attune_harness import task_handoff
from attune_harness.recovery import UnresolvedOperation
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.task_contract import accept_task, check_fresh, create_repair_task, read_task
from attune_harness.task_policies import control_task, execute_task
from test_assessment_repair_handoff import complete_assessment
from test_review import case as review_case, change, scripted
from test_task_contract import response

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Qualified POSIX repair effects')


@pytest.fixture
def case(tmp_path):
    return review_case.__wrapped__(tmp_path)


def prepare(case, *, target='guide.md', complete=True, replacement=None, checkout=None):
    root = checkout or case[0].parent / 'project'
    (root / '.git').mkdir(exist_ok=True)
    fixed = replacement or 'Fixed quartz policy.\n'
    (root / 'probe.py').write_text(
        'from pathlib import Path\nassert Path(' + repr(target) + ').read_text() == ' + repr(fixed) + '\n'
    )
    if complete:
        complete_assessment(case)
    probe = dict(argv=[sys.executable, '-B', 'probe.py'], cwd='.', timeout=10,
                 max_output_bytes=4096,
                 environment={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'},
                 oracle_paths=['probe.py'])
    record = create_repair_task(
        root.parent, case[1], goal='Repair assessed source', checkout=root,
        allowed=[target], probe=probe, worker='alpha', reviewer='beta',
        criteria='Pass the protected probe', directory=root.parent/'repair',
        source_assessment=case[2], finding_ids=['quartz-source'])
    directory = Path(record['record_path']).parent
    submission = response(directory)
    submission['permissions']['external'] = True
    accept_task(directory, submission)
    calls = []

    def action(packet):
        turn = packet['turn']
        payload = turn['repair']
        if turn['role'] == 'worker':
            value = dict(schema_version=1, replacements=[dict(
                path=target, before_sha256=payload['before_hashes'][target], text=fixed)])
        else:
            value = dict(schema_version=1, artifact_digest=payload['artifact_digest'],
                         probe_digest=payload['probe_digest'], verdict='approve', findings=[])
        return dict(kind='final', text=json.dumps(value))

    return directory, scripted(action, lambda packet: calls.append(packet)), calls


@pytest.mark.parametrize('target', ['guide.md', 'reference.md'])
@pytest.mark.parametrize('boundary', [1, 2, 3, 4, 5])
def test_assessed_document_or_source_repairs_resume_every_boundary(case, target, boundary):
    directory, factory, calls = prepare(case, target=target)
    original = (case[2]/'record.json').read_bytes()
    paused = execute_task(directory, max_operations=boundary, exchange_factory=factory)
    assert paused['status'] == 'paused', paused['execution'].get('error')
    old_events = copy.deepcopy(paused['execution']['events'])
    done = execute_task(directory, exchange_factory=factory)
    assert done['status'] == 'completed', done['execution'].get('error')
    assert done['execution']['events'][:boundary] == old_events
    assert len(calls) == 2
    assert not done['execution']['before_probe']['passed']
    assert done['execution']['after_probe']['passed']
    assert (case[2]/'record.json').read_bytes() == original
    root, changed, binding = task_handoff.completed_repair(directory)
    assert changed == [target] and binding['kind'] == 'completed-repair-v1'
    with pytest.raises(ValueError, match='Stale source'):
        check_fresh(read_task(case[2]))


@pytest.mark.parametrize('outside', ['context.json', 'project/reference.md', 'project/foreign.txt'])
def test_foreign_evidence_change_stops_before_reviewer(case, outside):
    directory, factory, calls = prepare(case)
    paused = execute_task(directory, max_operations=3, exchange_factory=factory)
    assert paused['status'] == 'paused'
    path = case[0].parent/outside
    path.write_text((path.read_text() if path.exists() else '') + '\n')
    with pytest.raises((ValueError, UnresolvedOperation)):
        execute_task(directory, exchange_factory=factory)
    assert len(calls) == 1


@pytest.mark.parametrize('mutation', ['worker', 'patch', 'result', 'order', 'scope', 'owner'])
def test_tampered_projection_is_not_a_freshness_exception(case, mutation):
    directory, factory, calls = prepare(case)
    paused = execute_task(directory, max_operations=3, exchange_factory=factory)
    value = copy.deepcopy(paused)
    event = next(e for e in value['execution']['events'] if e['kind']=='replacement')
    if mutation == 'worker':
        worker = next(e for e in value['execution']['events'] if e['kind']=='participant_turn')
        worker['result']['action']['text'] = json.dumps({'schema_version':1,'replacements':[]})
    elif mutation == 'patch':
        event['patch']['text'] += 'forged'
    elif mutation == 'result':
        event['result']['after_sha256'] = '0'*64
    elif mutation == 'order':
        event['operation_key'] = 'replace:reference.md'
    elif mutation == 'scope':
        value['request']['repair']['source_assessment']['effect_scope_digest'] = '0'*64
    else:
        (case[2]/'record.json').unlink()
    RunStore(directory, existing=True).save(value)
    with pytest.raises((ValueError, FileNotFoundError, UnresolvedOperation)):
        execute_task(directory, exchange_factory=factory)
    assert len(calls) == 1


def test_lost_acknowledgement_requires_reconcile_then_reuses_write(case, monkeypatch):
    directory, factory, calls = prepare(case)
    original = RunStore.save
    def fail(store, record):
        if store.directory == directory and any(
                e['kind']=='replacement' and e['state']=='completed'
                for e in record.get('execution', {}).get('events', [])):
            raise PersistenceError('synthetic lost acknowledgement')
        return original(store, record)
    with monkeypatch.context() as patch:
        patch.setattr(RunStore, 'save', fail)
        with pytest.raises(PersistenceError):
            execute_task(directory, exchange_factory=factory)
    saved = read_task(directory)
    event = saved['execution']['events'][-1]
    assert event['phase'] == 'dispatching'
    path = case[0].parent/'project/guide.md'
    inode = path.stat().st_ino
    with pytest.raises(UnresolvedOperation):
        execute_task(directory, exchange_factory=factory)
    control_task(directory, 'reconcile', event_id=event['event_id'], observe_file=True)
    done = execute_task(directory, exchange_factory=factory)
    assert done['status']=='completed', done['execution'].get('error')
    assert path.stat().st_ino == inode and len(calls)==2


def test_legacy_binding_cannot_acquire_effect_exceptions(case):
    directory, _, _ = prepare(case)
    value = read_task(directory)
    binding = value['request']['repair']['source_assessment']
    binding['kind'] = 'completed-assessment-v1'
    binding.pop('index_identity')
    binding.pop('effect_scope_digest')
    with pytest.raises(ValueError, match='overlaps immutable'):
        task_handoff.check_assessment_handoff(value['request'])


def voyage_case(case, monkeypatch, *, overlay=False, mode_overlay=False, second_repo=False):
    from attune_harness import voyage_provider
    from attune_harness.voyage_index import build_index, selection
    from attune_harness.voyage_sources import config
    from test_voyage import FakeProvider, git
    root = case[0].parent/'project'
    git(root, 'init')
    if overlay:
        (root/'reference.md').write_text('Fixed quartz policy.\n')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
    if overlay:
        (root/'reference.md').write_text('Broken quartz policy.\n')
    if mode_overlay:
        (root/'reference.md').chmod(0o755)
    roots = [dict(repo_id='app', path=str(root))]
    if second_repo:
        other = root.parent/'secondary'
        other.mkdir()
        (other/'reference.md').write_text('Broken quartz policy.\n')
        (other/'unindexed.txt').write_text('Broken unrelated text.\n')
        git(other, 'init')
        git(other, 'add', '.')
        git(other, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
        roots.append(dict(repo_id='second', path=str(other)))
    cfg = config(dict(schema_version=1, roots=roots,
                      index_dir=str(root.parent/'index'), include=['**/*.md'],
                      allow_overlays=overlay), root.parent)
    provider = FakeProvider()
    built = build_index(cfg, allow_provider=True, provider=provider)
    selected = selection(cfg, built['generation'])
    selected['scope']['exclude_paths'] = [dict(repo_id='app', path='guide.md')]
    change(case[1], lambda value: value.update(retrieval=selected))
    monkeypatch.setattr(voyage_provider, 'VoyageProvider', lambda: provider)
    complete_assessment(case, provider=True)
    return selected, provider


@pytest.mark.parametrize('overlay,mode_overlay,second_repo', [
    (False, False, False), (True, False, False), (True, True, False), (False, False, True)])
def test_voyage_history_survives_repair_without_becoming_current(case, monkeypatch, overlay, mode_overlay, second_repo):
    from attune_harness.voyage_index import check_generation
    selected, provider = voyage_case(case, monkeypatch, overlay=overlay,
                                    mode_overlay=mode_overlay, second_repo=second_repo)
    checkout = case[0].parent/'secondary' if second_repo else None
    directory, factory, calls = prepare(case, target='reference.md', complete=False, checkout=checkout)
    original = (case[2]/'record.json').read_bytes()
    before_calls = len(provider.calls)
    assert execute_task(directory, max_operations=3, exchange_factory=factory)['status']=='paused'
    done = execute_task(directory, exchange_factory=factory)
    assert done['status']=='completed', done['execution'].get('error')
    task_handoff.completed_repair(directory)
    assert len(calls)==2 and len(provider.calls)==before_calls
    assert (case[2]/'record.json').read_bytes()==original
    with pytest.raises(ValueError):
        check_generation(selected['config'], selected['generation'])


def test_voyage_unindexed_second_root_preserves_legacy_binding(case, monkeypatch):
    from attune_harness.voyage_index import check_generation
    selected, _ = voyage_case(case, monkeypatch, second_repo=True)
    directory, factory, _ = prepare(case, target='unindexed.txt', complete=False,
                                     checkout=case[0].parent/'secondary')
    assert read_task(directory)['request']['repair']['source_assessment']['kind'] == 'completed-assessment-v1'
    done = execute_task(directory, exchange_factory=factory)
    assert done['status'] == 'completed', done['execution'].get('error')
    task_handoff.completed_repair(directory)
    check_generation(selected['config'], selected['generation'])


@pytest.mark.parametrize('mutation', ['publication', 'rows', 'source', 'registry'])
def test_voyage_index_and_unrelated_inputs_remain_bound(case, monkeypatch, mutation):
    from attune_harness.review_contract import digest
    from attune_harness.voyage_index import read_generation
    selected, _ = voyage_case(case, monkeypatch)
    directory, factory, calls = prepare(case, target='reference.md', complete=False)
    assert execute_task(directory, max_operations=3, exchange_factory=factory)['status']=='paused'
    index, metadata = read_generation(selected['config'], selected['generation'])
    if mutation == 'publication':
        receipt = json.loads((index/'build-receipt.json').read_text())
        receipt['changed'] = True
        (index/'build-receipt.json').write_text(json.dumps(receipt))
        publication = json.loads((index/'published.json').read_text())
        publication['receipt_digest'] = digest(receipt)
        (index/'published.json').write_text(json.dumps(publication))
        read_generation(selected['config'], selected['generation'])  # Still self-consistent.
    elif mutation == 'rows':
        from attune_harness.voyage_index import database
        table = database(index/'db').open_table('passages')
        rows = table.to_arrow().to_pylist()
        rows[0]['vector'][0] += 0.1
        table.delete('true')
        table.add(rows)
    elif mutation == 'source':
        path = case[0].parent/'project/guide.md'
        path.write_text(path.read_text()+'\n')
    else:
        change(case[1], lambda value: value['retrieval']['scope'].update(exclude_paths=[]))
    with pytest.raises((ValueError, UnresolvedOperation)):
        execute_task(directory, exchange_factory=factory)
    assert len(calls)==1
