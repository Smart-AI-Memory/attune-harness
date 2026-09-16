"""Real dedicated checkout effects and failure-sensitive repair guards."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from attune_harness import repair
from attune_harness.recovery import RecoveryCursor, ReviewPaused, UnresolvedOperation
from attune_harness.review_store import RunStore, PersistenceError, read_record

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='POSIX repair handle profile; Windows not qualified')


@pytest.fixture
def effect_case(tmp_path):
    root = tmp_path/'checkout'
    subprocess.run(['git','init','-q',str(root)],check=True)
    (root/'app.py').write_text('def add(a,b):\n    return a-b\n')
    (root/'other.py').write_text('VALUE = 1\n')
    (root/'probe.py').write_text('from app import add\nassert add(2,3)==5\nprint("accepted")\n')
    probe={'argv':[sys.executable,'probe.py'],'cwd':'.','timeout':10,'max_output_bytes':4096,
           'environment':{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'},
           'oracle_paths':['probe.py']}
    state=tmp_path/'state'
    plan=repair.freeze(root,['app.py','other.py'],probe,state)
    store=RunStore(state)
    record={'schema_version':1,'events':[],'recovery':{}}
    store.save(record)
    return root,plan,store,record


def patch(plan, text='def add(a,b):\n    return a+b\n', name='app.py'):
    return {'schema_version':1,'replacements':[{'path':name,'before_sha256':plan['before'][name]['sha256'],'text':text}]}


def test_real_failure_write_success_and_no_duplicate_write(effect_case,monkeypatch):
    root,plan,store,record=effect_case
    assert repair.run_probe(plan,plan['before'])['passed'] is False
    results=repair.apply_patch(plan,patch(plan),RecoveryCursor(record,store))
    assert results[0]['after_sha256']==repair.sha((root/'app.py').read_bytes())
    expected=repair.expected_snapshot(plan,record['events'])
    assert repair.run_probe(plan,expected)['passed'] is True
    monkeypatch.setattr(repair,'replace_file',lambda *_:pytest.fail('duplicate write'))
    assert repair.apply_patch(plan,patch(plan),RecoveryCursor(record,store))==results


def test_wrong_and_noop_repairs_do_not_pass(effect_case):
    _,plan,store,record=effect_case
    with pytest.raises(ValueError,match='No-op'):
        repair.decode_patch(json.dumps(patch(plan,'def add(a,b):\n    return a-b\n')),plan)
    repair.apply_patch(plan,patch(plan,'def add(a,b):\n    return 0\n'),RecoveryCursor(record,store))
    assert not repair.run_probe(plan,repair.expected_snapshot(plan,record['events']))['passed']


@pytest.mark.parametrize('path',['../outside','/tmp/outside','app.py/../other.py','./app.py','app.py//x','app.py\\x','.git/config','probe.py','new.py'])
def test_invalid_patch_paths_never_write(effect_case,path):
    root,plan,store,record=effect_case
    value=patch(plan);value['replacements'][0]['path']=path
    before=(root/'app.py').read_bytes()
    with pytest.raises((ValueError,KeyError)):
        repair.apply_patch(plan,value,RecoveryCursor(record,store))
    assert (root/'app.py').read_bytes()==before and not record['events']


def test_scope_guard_rejects_existing_unlisted_file(effect_case):
    _,plan,_,_=effect_case
    narrowed=copy.deepcopy(plan);narrowed['allowed']=['other.py']
    with pytest.raises(ValueError,match='scope'):
        repair.decode_patch(json.dumps(patch(plan)),narrowed)


def test_entire_patch_validated_before_first_write(effect_case):
    root,plan,store,record=effect_case
    value=patch(plan);value['replacements'].append({'path':'other.py','before_sha256':'wrong','text':'VALUE = 2\n'})
    with pytest.raises(ValueError,match='preimage'):
        repair.apply_patch(plan,value,RecoveryCursor(record,store))
    assert repair.snapshot(plan)==plan['before'] and record['events']==[]


@pytest.mark.parametrize('fault',['duplicate','encoding','size','extra-field'])
def test_patch_decoder_bounds(effect_case,fault):
    _,plan,_,_=effect_case
    value=patch(plan)
    if fault=='duplicate':value['replacements']*=2
    if fault=='encoding':value['replacements'][0]['text']='\ud800'
    if fault=='size':value['replacements'][0]['text']='x'*65537
    if fault=='extra-field':value['command']='rm -rf .'
    with pytest.raises((ValueError,UnicodeError)):
        repair.decode_patch(json.dumps(value),plan)


@pytest.mark.parametrize('attack',['symlink','hardlink','parent-link','metadata','oracle','state'])
def test_frozen_scope_rejects_unsafe_files_and_oracles(effect_case,attack,tmp_path):
    root,plan,store,_=effect_case
    allowed=['app.py'];state=store.directory;probe=copy.deepcopy(plan['probe'])
    if attack=='symlink':
        (root/'app.py').unlink();(root/'app.py').symlink_to(root/'other.py')
    elif attack=='hardlink':os.link(root/'app.py',root/'alias.py')
    elif attack=='parent-link':
        (root/'alias').symlink_to(root,target_is_directory=True);allowed=['alias/app.py']
    elif attack=='metadata':allowed=['.git/config']
    elif attack=='oracle':allowed=['probe.py']
    elif attack=='state':state=root/'state'
    with pytest.raises((ValueError,OSError)):
        repair.freeze(root,allowed,probe,state)


def test_changed_protected_state_and_stale_preimage_stop(effect_case):
    root,plan,store,record=effect_case
    (root/'probe.py').write_text('print("always passes")')
    with pytest.raises(UnresolvedOperation):repair.apply_patch(plan,patch(plan),RecoveryCursor(record,store))
    assert record['events']==[]


def test_partial_write_and_lost_ack_reconcile_without_second_write(effect_case,monkeypatch):
    root,plan,store,record=effect_case
    value=patch(plan);value['replacements'].extend(patch(plan,'VALUE = 2\n','other.py')['replacements'])
    original=store.save
    def lose(r):
        if r['events'] and r['events'][0]['state']=='completed':raise PersistenceError('lost ack')
        original(r)
    monkeypatch.setattr(store,'save',lose)
    with pytest.raises(PersistenceError):repair.apply_patch(plan,value,RecoveryCursor(record,store))
    saved=read_record(store.directory);event=saved['events'][0]
    assert event['phase']=='dispatching'
    assert 'a+b' in (root/'app.py').read_text() and (root/'other.py').read_text()=='VALUE = 1\n'
    repair.reconcile_replacement(plan,event)
    monkeypatch.setattr(store,'save',original)
    original(saved)
    first_inode=(root/'app.py').stat().st_ino
    repair.apply_patch(plan,value,RecoveryCursor(saved,store))
    assert (root/'app.py').stat().st_ino==first_inode
    assert (root/'other.py').read_text()=='VALUE = 2\n'


def test_before_retry_explicit_and_unexpected_content_unresolved(effect_case):
    root,plan,_,_=effect_case
    event={'kind':'replacement','phase':'dispatching','state':'pending','attempts':1,'patch':patch(plan)['replacements'][0]}
    with pytest.raises(UnresolvedOperation):repair.reconcile_replacement(plan,event)
    repair.reconcile_replacement(plan,event,retry_before=True)
    assert event['phase']=='prepared' and event['attempts']==2
    event.update(phase='dispatching',state='pending')
    with pytest.raises(UnresolvedOperation):repair.reconcile_replacement(plan,event,retry_before=True)
    (root/'app.py').write_text('unexpected')
    with pytest.raises(UnresolvedOperation):repair.reconcile_replacement(plan,event,retry_before=True)
    assert (root/'app.py').read_text()=='unexpected'


def test_post_write_guard_detects_corruption(effect_case,monkeypatch):
    root,plan,_,_=effect_case
    original=repair.os.replace
    def corrupt(*a,**kw):
        original(*a,**kw)
        (root/'app.py').write_text('corrupted after replace')
    monkeypatch.setattr(repair.os,'replace',corrupt)
    with pytest.raises(UnresolvedOperation,match='after-image'):
        repair.replace_file(plan,patch(plan)['replacements'][0])


def test_probe_explicit_environment_does_not_inherit_secret(effect_case,monkeypatch):
    root,plan,_,_=effect_case
    monkeypatch.setenv('HARNESS_PRIVATE_SENTINEL','must-not-inherit')
    (root/'probe.py').write_text('import os\nassert "HARNESS_PRIVATE_SENTINEL" not in os.environ\n')
    frozen=repair.freeze(root,plan['allowed'],plan['probe'],root.parent/'newstate')
    assert repair.run_probe(frozen,frozen['before'])['passed'] is True


def test_process_death_after_write_before_acknowledgement(effect_case):
    root,plan,store,record=effect_case
    payload=root.parent/'payload.json'
    payload.write_text(json.dumps({'plan':plan,'patch':patch(plan),'state':str(store.directory)}))
    code='''import json,os,sys
from pathlib import Path
from attune_harness.repair import apply_patch
from attune_harness.review_store import RunStore,read_record
from attune_harness.recovery import RecoveryCursor
v=json.loads(Path(sys.argv[1]).read_text());s=RunStore(Path(v['state']),existing=True);r=read_record(s.directory)
original=s.save
def save(record):
 if any(e['kind']=='replacement' and e['state']=='completed' for e in record['events']):os._exit(23)
 original(record)
s.save=save
with s.lease():apply_patch(v['plan'],v['patch'],RecoveryCursor(r,s))
'''
    source=str(Path(repair.__file__).resolve().parent.parent)
    result=subprocess.run([sys.executable,'-B','-c',code,str(payload)],env={**os.environ,'PYTHONPATH':source},capture_output=True,text=True,timeout=15)
    assert result.returncode==23,result.stderr
    persisted=read_record(store.directory)
    assert persisted['events'][0]['phase']=='dispatching'
    assert 'a+b' in (root/'app.py').read_text()
    before_inode=(root/'app.py').stat().st_ino
    with store.lease():
        repair.reconcile_replacement(plan,persisted['events'][0])
        store.save(persisted)
        repair.apply_patch(plan,patch(plan),RecoveryCursor(persisted,store))
    assert (root/'app.py').stat().st_ino==before_inode
