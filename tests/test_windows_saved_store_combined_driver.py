"""Pure proposal checks: never invoke driver.main, subprocesses or native code."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PureWindowsPath

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('t2_combined_review_only',ROOT/'experiments/platform/windows_saved_store_combined_driver_v1.py')
driver=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)

@pytest.mark.parametrize('payload,digest,path',[
 pytest.param(driver.ORIGINAL_PAYLOAD,driver.ORIGINAL_SHA,ROOT/'experiments/platform/windows_saved_store_proof.py',
              id='original-payload'),
 (driver.NAMESPACE_PAYLOAD,driver.NAMESPACE_SHA,ROOT/'experiments/platform/windows_saved_store_namespace_witness_v4.py'),
])
def test_exact_payload(payload,digest,path):
 raw=driver.payload_bytes(payload,digest)
 assert raw==path.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==digest
 compile(raw,str(path),'exec') # Compile as data; never execute the payload.

@pytest.mark.parametrize('payload,digest',[
 pytest.param(driver.ORIGINAL_PAYLOAD,'0'*64,id='original-payload-wrong-digest'),
 (b'!',driver.ORIGINAL_SHA)])
def test_refuse_changed_payload(payload,digest):
 with pytest.raises(ValueError):driver.payload_bytes(payload,digest)


def test_exact_two_command_plans():
 source=PureWindowsPath('C:/ProgramData/AttuneT2Proof-0123/combined-witness-sources')
 output=PureWindowsPath('C:/ProgramData/AttuneT2Proof-0123/observations')
 executable='C:/ProgramData/AttuneT2Proof-0123/runtime/Scripts/python.exe'
 plan=driver.command_plan(executable,source,output)
 assert plan==(
  ('namespace',[executable,'-I',str(source/'namespace_v4.py'),'--original',str(source/'original.py'),'--original-sha256',driver.ORIGINAL_SHA,'--expected-adapter-sha256',driver.NAMESPACE_SHA,'--output',str(output)]),
  ('primitive',[executable,'-I',str(source/'original.py'),'--current-standard','--output',str(output/'primitive')]),
 )
 assert '--current-standard' not in plan[0][1]
 assert '--expected-adapter-sha256' not in plan[1][1]
 assert '--worker' not in plan[0][1]

@pytest.mark.parametrize('now,expected',[(10,150),(159,1)])
def test_aggregate_budget(now,expected):assert driver.remaining_budget(10,now)==expected

@pytest.mark.parametrize('now',[160,161])
def test_deadline_refuses_more_dispatch(now):
 with pytest.raises(TimeoutError):driver.remaining_budget(10,now)


def test_ascii_diagnostics_preserve_unicode():
 target=io.StringIO()
 with contextlib.redirect_stdout(target):driver.emit({'path':'雪 / café'})
 assert json.loads(target.getvalue())=={'path':'雪 / café'}
 target.getvalue().encode('cp1252',errors='strict')
