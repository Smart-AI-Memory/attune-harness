"""Whole-tree capacity, authority preservation and saved-work round trips."""
# qualify: platform

import copy
import os
import time

import pytest

from attune_harness import repair, work_effects, windows_effects as windows
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import read_task
import test_work_contract as contracts
import test_work_build as builds
from test_windows_effects import _synthetic, _entry, _id

work = contracts.work


def checkout(tmp_path):
    root = tmp_path / 'checkout'
    root.mkdir()
    (root / '.git').mkdir()
    (root / '.git/config').write_text('metadata', encoding='utf-8')
    (root / 'source.py').write_text('old', encoding='utf-8')
    (root / 'oracle.txt').write_text('protected', encoding='utf-8')
    return root


def fill(root, count):
    current = len(list(root.rglob('*'))) + (os.name == 'nt')
    for n in range(count - current):
        # Mix empty directories and files so both are counted.
        path = root / f'entry-{n:04}'
        if n % 2:
            path.mkdir()
        else:
            path.write_bytes(b'')


def freeze(root, tmp_path):
    return work_effects.freeze(root, ['source.py'], [], ['oracle.txt'], [], tmp_path/'task')


def test_exact_entry_boundary_is_shared_by_capture_and_validation(tmp_path):
    root = checkout(tmp_path)
    fill(root, 2048)
    plan = freeze(root, tmp_path)
    assert len(plan['before']) == 2048
    work_effects.validate_manifest(plan)
    forged = copy.deepcopy(plan)
    forged['before']['one-more/'] = copy.deepcopy(plan['before']['.git/'])
    with pytest.raises(ValueError):
        work_effects.validate_manifest(forged)
    (root/'one-more').mkdir()
    with pytest.raises(ValueError, match='bounded'):
        freeze(root, tmp_path)
    assert (root/'source.py').read_text() == 'old'
    assert not (tmp_path/'task').exists()


def test_tree_bytes_remain_bounded(tmp_path):
    root = checkout(tmp_path)
    (root/'large-a').write_bytes(b'a' * (8 * 1024 * 1024))
    (root/'large-b').write_bytes(b'b' * (8 * 1024 * 1024))
    with pytest.raises(ValueError, match='byte budget|bounded repair profile'):
        freeze(root, tmp_path)


@pytest.mark.parametrize('target', ['.git/config', 'oracle.txt', 'unrelated.txt'])
def test_large_snapshot_still_detects_out_of_scope_edits(tmp_path, target):
    root = checkout(tmp_path)
    (root/'unrelated.txt').write_text('keep', encoding='utf-8')
    fill(root, 1394)
    plan = freeze(root, tmp_path)
    (root/target).write_text('changed', encoding='utf-8')
    with pytest.raises((ValueError, UnresolvedOperation)):
        repair.assert_snapshot(plan, plan['before'])
    assert (root/'source.py').read_text() == 'old'


def test_windows_saved_build_and_repair_count_root_entry():
    base = _synthetic()
    base['before']['oracle.txt'] = _entry(3, text='protected')
    for n in range(2048 - len(base['before'])):
        base['before'][f'file-{n}'] = _entry(n+4)
    plan = {**base, 'snapshot_version':1, 'root':'C:\\checkout',
            'root_identity':_id(1), 'allowed':['source.py'], 'parents':[],
            'protected':['oracle.txt'], 'checks':[]}
    work_effects.validate_manifest(plan)
    rp = {k:copy.deepcopy(v) for k,v in plan.items() if k not in ('parents','protected','checks')}
    rp.update(profile=windows.REPAIR_PROFILE, inputs={'source.py':'old'},
              executable_sha256='0'*64,
              probe={'argv':['C:\\python.exe'], 'cwd':'.', 'timeout':1,
                     'max_output_bytes':1,'environment':{},'oracle_paths':['oracle.txt']})
    repair.validate_scope(rp)
    for item, validator in ((plan,work_effects.validate_manifest),(rp,repair.validate_scope)):
        item['before']['one-more'] = _entry(3000)
        with pytest.raises(ValueError):
            validator(item)


@pytest.mark.skipif(os.name != 'nt', reason='native Windows directory enumeration')
def test_windows_directory_enumeration_boundary(tmp_path):
    root = checkout(tmp_path)
    # Native.names counts children, whereas the complete snapshot also counts root.
    for n in range(2048 - len(list(root.iterdir()))):
        (root/f'name-{n}').write_bytes(b'')
    api = windows.Native()
    plan = {'root':str(root),'root_identity':windows.root_identity(root)}
    with api.root(plan) as handle:
        assert len(api.names(handle)) == 2048
        (root/'overflow').write_bytes(b'')
        with pytest.raises(ValueError, match='Directory exceeds'):
            api.names(handle)


@pytest.mark.skipif(os.name != 'posix', reason='existing scripted POSIX build fixture')
def test_large_build_record_roundtrip_and_resume(work, record_property):
    root = work[0]
    for n in range(1300):
        (root/f'unchanged-{n}').write_bytes(b'')
    builds.Worker.seen = []
    builds.Worker.mutation = None
    started = time.monotonic()
    case = builds.prepare(work)
    assert len(case[2]['request']['effects']['before']) > 1000
    paused = builds.execute(case, max_operations=4)
    assert paused['build']['status'] == 'paused'
    assert read_task(case[1]) == paused
    result = builds.execute(case)
    assert result['build']['status'] == 'completed', result['build'].get('error')
    assert builds.execute(case) == result
    assert len(builds.Worker.seen) == 3
    size = (case[1]/'record.json').stat().st_size
    assert size < 8*1024*1024
    record_property('record_bytes', size)
    record_property('elapsed_seconds', time.monotonic()-started)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX saved repair scope')
def test_posix_repair_validator_enforces_snapshot_bound(tmp_path):
    import sys
    root = checkout(tmp_path)
    fill(root, 2048)
    probe = {'argv':[sys.executable, '-c', 'pass'], 'cwd':'.', 'timeout':1,
             'max_output_bytes':1024, 'environment':{'PYTHONDONTWRITEBYTECODE':'1',
             'PYTHONNOUSERSITE':'1'}, 'oracle_paths':['oracle.txt']}
    plan = repair.freeze(root, ['source.py'], probe, tmp_path/'task')
    repair.validate_scope(plan)
    plan['before']['one-more/'] = {'kind':'directory', 'mode':0o755}
    with pytest.raises(ValueError, match='Invalid effect snapshot'):
        repair.validate_scope(plan)
