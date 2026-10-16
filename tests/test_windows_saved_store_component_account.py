"""Pure/data controls only: synthetic records never qualify native cleanup."""
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import re
from types import ModuleType, SimpleNamespace
import zipfile
import pytest

HERE = Path(__file__).absolute().parent
SOURCE = HERE if (HERE / 'windows_saved_store_ack_gate_v1.py').is_file() else HERE.parent / 'experiments/platform'
DATA = HERE if (HERE / 'synthetic-control-vector.json').is_file() else HERE / 'fixtures/windows_saved_store_component_account_v1'


def module(name):
    path = SOURCE / name
    value = ModuleType(name.removesuffix('.py'))
    value.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), value.__dict__)
    return value


GATE = module('windows_saved_store_ack_gate_v1.py')
PUBLISHER = module('windows_saved_store_anchor_setup_v1.py')


@pytest.fixture
def records():
    value = json.loads((DATA / 'synthetic-control-vector.json').read_bytes())
    assert value['SYNTHETIC_TEST_VECTOR_NOT_NATIVE_EVIDENCE'] is True
    with zipfile.ZipFile(DATA / 'frozen-validators.zip') as source:
        result = []
        for name, wanted in [('original.py', GATE.ORIGINAL_SHA), ('namespace.py', GATE.NAMESPACE_SHA)]:
            raw = source.read(name)
            assert hashlib.sha256(raw).hexdigest() == wanted
            item = ModuleType('synthetic_' + name.removesuffix('.py'))
            item.__file__ = '/synthetic/' + name
            exec(compile(raw, item.__file__, 'exec'), item.__dict__)
            result.append(item)
        manifest = json.loads(source.read('manifest.json'))
    return {**value, 'files': {k: v.encode('utf-8') for k, v in value['files'].items()},
            'original': result[0], 'namespace': result[1], 'manifest': manifest}


def consume(value):
    return GATE.consume(value['files'], value['fixture'], value['setup'], value['driver'],
                        value['original'], value['namespace'], value['manifest'])


def test_synthetic_complete12_not_D3_or_cleanup_evidence(records):
    result = consume(records)
    assert result['complete_ack_count'] == 12 and len(result['complete_ack_witnesses']) == 12
    assert result['true_writer_replays'] == 7 and result['raw_proof_flush_rows'] == 84
    assert result['t2_d3_passed'] is result['production_port_allowed'] is False
    assert result['primitive_enclosing_path_publication'].startswith('unqualified')
    assert result['unobserved_rename_io'] == ['lock_seed', 'concurrency_seeds', 'crash_seeds', 'crash_retries']


@pytest.mark.parametrize('field,value', [('flags', 1), ('flags', False), ('returned_ntstatus', 259),
    ('returned_ntstatus', False), ('io_status', 1), ('io_status', None), ('io_status', False)])
def test_normal_status_exact_int_zero_required(field, value):
    row = {'where': 'prepared_file', 'flags': 0, 'returned_ntstatus': 0, 'io_status': 0}
    row[field] = value
    with pytest.raises(ValueError): GATE.normal(row)


@pytest.mark.parametrize('field', ['flags', 'returned_ntstatus', 'io_status'])
def test_missing_status_refused(field):
    row = {'where': 'prepared_file', 'flags': 0, 'returned_ntstatus': 0, 'io_status': 0}
    del row[field]
    with pytest.raises(ValueError): GATE.normal(row)


@pytest.mark.parametrize('field,value', [('returned_ntstatus', 259), ('returned_ntstatus', False),
    ('io_status_block_status', 1), ('io_status_block_status', None), ('io_status_block_status', False)])
def test_ack_native_return_and_IO_both_required(records, field, value):
    row = copy.deepcopy(json.loads(records['files']['primitive/receipt.json'])['initial_commit'])
    row['rename'][field] = value
    with pytest.raises(ValueError): GATE.ack(row, ['first'])


@pytest.mark.parametrize('field,value', [('sha256', '0'*64), ('bytes', 237.0), ('bytes', 236)])
def test_ack_afterimage_checked(records, field, value):
    row = copy.deepcopy(json.loads(records['files']['primitive/receipt.json'])['initial_commit'])
    row[field] = value
    with pytest.raises(ValueError): GATE.ack(row, ['first'])


@pytest.mark.parametrize('field', ['private_cleanup_succeeded','proof_tree_disappearance_established',
    'cleanup_tree_disappearance_established','gui_tree_disappearance_established','gui_cleanup_succeeded',
    'credential_disposed','anchor_setup_tree_disappearance_established','runtime_admission_tree_disappearance_established'])
def test_unknown_cleanup_never_converted_to_success(records, field):
    records['fixture'][field] = None
    with pytest.raises(ValueError): consume(records)


@pytest.mark.parametrize('field', ['account_disable', 'account_remove', 'fixture_root_remove'])
def test_failed_or_unobserved_owned_removal_refused(records, field):
    records['fixture'][field] = 'unobserved'
    with pytest.raises(ValueError): consume(records)


def test_nonaggregate_raw_refusal_cannot_hide_behind_exit0(records):
    name = 'primitive/file_flushed-marker.json.native-flush-observations.jsonl'
    row = json.loads(records['files'][name]); row['io_status'] = 1
    records['files'][name] = (json.dumps(row)+'\n').encode()
    with pytest.raises(ValueError, match='normal_zero_flush'): consume(records)


def test_blocked_aggregate_with_process0_refused(records):
    row = json.loads(records['files']['primitive/receipt.json'])
    row['flush_observations'][0]['returned_ntstatus'] = 1
    row['durability_gate'] = records['original'].receipt_gate(row['flush_observations'])
    records['files']['primitive/receipt.json'] = json.dumps(row).encode()
    with pytest.raises(ValueError): consume(records)


@pytest.mark.parametrize('extra', [False, True])
def test_missing_or_extra_raw_stream_refused(records, extra):
    if extra: records['files']['primitive/unknown.jsonl'] = records['files']['primitive/native-flush-observations.jsonl']
    else: del records['files']['primitive/native-flush-observations.jsonl']
    with pytest.raises((ValueError, KeyError)): consume(records)


def test_replay_is_not_a_new_commit_or_renewed_barrier(records):
    name = next(name for name, raw in records['files'].items() if name.startswith('primitive/writer-Same request-')
                and name.endswith('.json') and json.loads(raw)['replayed'])
    row = json.loads(records['files'][name]); row['rename'] = {'returned_ntstatus': 0, 'io_status_block_status': 0}
    records['files'][name] = json.dumps(row).encode()
    with pytest.raises(ValueError, match='replay_new_barrier'): consume(records)


def test_actual_same_request_winner_selected_from_records(records):
    names = [f'primitive/writer-Same request-{i}.json' for i in range(8)]
    winner = next(name for name in names if not json.loads(records['files'][name])['replayed'])
    loser = next(name for name in names if name != winner)
    records['files'][winner], records['files'][loser] = records['files'][loser], records['files'][winner]
    log = winner + '.native-flush-observations.jsonl'
    records['files'][loser + '.native-flush-observations.jsonl'] = records['files'].pop(log)
    assert consume(records)['complete_ack_count'] == 12


def test_distinct_requests_cannot_share_operation_snapshot(records):
    name = 'primitive/writer-Distinct writers-1.json'
    row = json.loads(records['files'][name]);row['result']['request_id'] = 'writer-0'
    records['files'][name] = json.dumps(row).encode()
    with pytest.raises(ValueError): consume(records)


def test_anchor_identity_must_be_setup_child(records):
    records['setup']['child_identity'] = {'file_id':'a'*32,'volume':1}
    records['setup']['child_after'] = records['setup']['child_identity']
    records['fixture']['anchor_setup'] = copy.deepcopy(records['setup'])
    with pytest.raises(ValueError, match='anchor_binding'): consume(records)


def test_source_platform_and_full_installed_inventory_bound(records):
    records['fixture']['runtime_admission']['rows'][0]['sha256'] = '0'*64
    with pytest.raises(ValueError, match='installed118_identity'): consume(records)


class FakeNative:
    def __init__(self, *, status=0, close_failure=False):
        self.api = self; self.active=[]; self.events=[]; self.status=status; self.close_failure=close_failure
    @contextmanager
    def root(self, plan, check):
        self.active.append('parent');self.events.append('parent_open')
        try: yield 'parent'
        finally:self.events.append('parent_close');self.active.remove('parent')
    @contextmanager
    def owned(self, handle):
        self.active.append('child');self.events.append('child_open')
        try: yield handle
        finally:
            self.events.append('child_close');self.active.remove('child')
            if self.close_failure:raise OSError('synthetic_close_failure')
    def canonical_child(self, parent, leaf, **kwargs):return 'child'
    def metadata(self, handle):return ({'identity':{'file_id':('1' if handle=='parent' else '2')*32,'volume':1}},0,None)
    def names(self, parent):return ['AttuneT2Proof-'+'0'*32]
    def flush(self, handle, where):
        assert self.active==['parent','child'];self.events.append('flush_with_handles_retained')
        return {'where':where,'flags':0,'returned_ntstatus':0,'io_status':self.status}


def test_setup_retains_parent_child_until_flush_recheck_and_close():
    api=FakeNative();state={};snapshots=[]
    PUBLISHER.publish(api,Path('/synthetic/ProgramData'),'AttuneT2Proof-'+'0'*32,state,lambda:snapshots.append(copy.deepcopy(state)))
    assert api.events==['parent_open','child_open','flush_with_handles_retained','child_close','parent_close']
    assert state['handles_closed'] is True and state['status']=='anchor_published_requires_semantic_review'
    assert snapshots[-2]['phase']=='identities_rechecked_with_handles_retained'


@pytest.mark.parametrize('kind', ['status','close'])
def test_setup_refusal_or_close_error_cannot_publish_success(kind):
    api=FakeNative(status=1 if kind=='status' else 0,close_failure=kind=='close');state={'handles_closed':False}
    with pytest.raises((ValueError,OSError)):
        PUBLISHER.publish(api,Path('/synthetic/ProgramData'),'AttuneT2Proof-'+'0'*32,state,lambda:None)
    assert state['handles_closed'] is False and state.get('status')!='anchor_published_requires_semantic_review'
    assert not api.active


def test_fixture_preserves_two_compiled_literals_and_hook_order():
    old=(DATA/'fixture3b3-reference.ps1').read_text();new=(SOURCE/'windows_saved_store_standard_user_gui_proposal_v4.ps1').read_text()
    assert re.findall(r"Add-Type -TypeDefinition @'\n(.*?)\n'@",old,re.S)==re.findall(r"Add-Type -TypeDefinition @'\n(.*?)\n'@",new,re.S)
    assert new.index('Set-Acl -LiteralPath $fixtureRoot -AclObject $acl') < new.index("Invoke-ControllerCapture 'anchor_setup'") < new.index('& $BasePython -m venv')
    assert new.index("Invoke-ControllerCapture 'runtime_admission'") < new.index('$guiLease = [T2GuiLeaseController]')
    assert '-and $report.anchor_setup_tree_disappearance_established -and $report.runtime_admission_tree_disappearance_established' in new


def test_account_job_is_exact_guarded_event_or_literal_closed():
    path=HERE/'disabled-account-workflow.yml'
    if not path.is_file():path=HERE.parent/'.github/workflows/windows-saved-store-component-account-proposal.yml'
    raw=path.read_text()
    # Two finite reviewed source versions; runtime hashes still use raw bytes.
    # This structural text control does not execute GitHub or PowerShell.
    digest=hashlib.sha256(raw.encode('utf-8')).hexdigest()
    guarded='2809cd2e9a71450a060384db255b28d15432eaa6bc8448936c2dec5690ff2e4c'
    closed='2e4b9eb49b068884332174ebd60395446fa42c2abea5138dad9fea2a587693c8'
    assert digest in {guarded,closed}
    if digest==guarded:
        assert raw.count('if: ${{ false }}')==0
        assert "github.event.before == 'd38c7b8e904722c0526633940591d332a96c91e0'" in raw
        assert "github.event.action == 'synchronize'" in raw and "github.run_attempt == '1'" in raw
        assert "github.event.after == github.event.pull_request.head.sha" in raw
    else:assert raw.count('if: ${{ false }}')==1
    assert 'os: [windows-2022, windows-2025]' in raw and "python: ['3.10', '3.12']" in raw
    assert 'workflow_dispatch' not in raw and 'ref: codex/' not in raw
    assert raw.index('& $script -Repo') < raw.index('& $tail -Repo')
    assert raw.count(".github/workflows/windows-saved-store-component-account-proposal.yml'")==2


@pytest.mark.parametrize('kind', ['symlink','hardlink'])
def test_same_bytes_alias_refused_before_account(tmp_path,kind):
    import os
    target=tmp_path/'target';target.write_bytes(b'fixed input')
    alias=tmp_path/'alias'
    if kind=='symlink':
        try:alias.symlink_to(target)
        except OSError as error:
            if os.name=='nt' and getattr(error,'winerror',None)==1314:pytest.skip('Native symlink privilege absent')
            raise
    else:os.link(target,alias)
    wanted=hashlib.sha256(alias.read_bytes()).hexdigest()
    assert wanted==hashlib.sha256(b'fixed input').hexdigest()
    with pytest.raises(ValueError,match='entry_kind'):GATE.inspect_file(alias,wanted)


def test_source_drift_retains_preaccount_failure(tmp_path):
    target=tmp_path/'fixed.py';target.write_bytes(b'fixed source')
    with pytest.raises(ValueError,match='entry_hash'):GATE.inspect_file(target,'0'*64)
    assert target.read_bytes()==b'fixed source'


def test_entry_unknown_source_cardinality_refused_without_Git(tmp_path):
    with pytest.raises(ValueError,match='finite48'):GATE.admit(tmp_path,tmp_path,{},'0'*64)


def test_fixture_source_bindings_and_no_new_launcher_literals():
    fixture=(SOURCE/'windows_saved_store_standard_user_gui_proposal_v4.ps1').read_text()
    # Structural source control uses logical LF text on ordinary CRLF checkouts.
    # Runtime hashes remain raw bytes, enforced by the canonical49 materializer.
    publisher=hashlib.sha256((SOURCE/'windows_saved_store_anchor_setup_v1.py').read_text().encode('utf-8')).hexdigest()
    assert publisher in fixture
    tail=(SOURCE/'windows_saved_store_component_account_tail_v1.ps1').read_text()
    gate=hashlib.sha256((SOURCE/'windows_saved_store_ack_gate_v1.py').read_text().encode('utf-8')).hexdigest()
    assert gate in tail
    assert tail.index('Capture-Controller \'account-entry\'') < tail.index('& $fixture -ExecuteApprovedFixture')
    assert tail.index("Set-Location -LiteralPath $fixtureCwd") < tail.index('& $fixture -ExecuteApprovedFixture')
    assert '$env:PYTHONHOME = $null' in tail and '$env:PYTHONPATH = $null' in tail and '$env:PYTHONUSERBASE = $null' in tail
    assert "-Wheel $wheel" in tail and 'Get-ChildItem' not in tail[tail.index('& $fixture -ExecuteApprovedFixture'):]
