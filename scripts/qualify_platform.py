"""Run installed-library platform checks and preserve actual OS qualification status."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
PLATFORM_MARKER='# qualify: platform'


def qualify(output):
    import attune_harness
    from attune_harness.process import invoke
    from attune_harness.review_store import RunStore
    from attune_harness.features import FeatureUnavailable
    output.mkdir(parents=True,exist_ok=False)
    source=Path(attune_harness.__file__).resolve().parent
    if source==ROOT/'src/attune_harness':raise ValueError('Install the wheel before qualification')
    receipt={'schema_version':1,'system':platform.system(),'machine':platform.machine(),
        'python':platform.python_version(),'package':importlib.metadata.version('attune-harness'),
        'installed_source':source.as_posix(),'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')},
        'native_process_and_recovery':'unrun','model_calls':0,'checks':[]}
    tests=['test_contract.py','test_adapters.py','test_operations.py','test_github_checks.py','test_native.py']
    # A carried module's tests declare themselves with PLATFORM_MARKER in their
    # first lines, so two steps landing in parallel never edit this line.
    tests += sorted(p.name for p in (ROOT/'tests').glob('test_*.py')
                    if PLATFORM_MARKER in p.read_text(encoding='utf-8')[:4000] and p.name not in tests)
    tests += ['test_voyage.py', 'test_voyage_integration.py', 'test_mcp.py', 'test_voyage_evaluation.py',
              'test_code_rag.py', 'test_code_rag_host_check.py']
    if os.name in ('posix','nt'):
        tests+=['test_review.py','test_review_boundaries.py','test_recovery.py',
                'test_astra_review.py','test_native_evidence_review.py','test_focused_native.py']
        tests += ['test_process.py'] if os.name=='posix' else ['test_windows_runtime.py']
    else:
        # Prove truthful rejection; do not disguise this as Windows qualification.
        with tempfile.TemporaryDirectory(prefix='harness-platform-') as directory:
            try:invoke((sys.executable,'-c','print(1)'),'',cwd=Path(directory))
            except NotImplementedError:receipt['checks'].append('native process explicitly unsupported')
            else:raise AssertionError('Update the Windows qualification suite before claiming support')
            store=RunStore(Path(directory)/'run')
            try:
                with store.lease():pass
            except FeatureUnavailable:receipt['checks'].append('native recovery explicitly unsupported')
            else:raise AssertionError('Update the Windows qualification suite before claiming support')
        receipt['native_process_and_recovery']='unsupported'
    argv=[sys.executable,'-m','pytest','-vv','-o','pythonpath=',
          '--junitxml='+str(output/'tests.xml'),*[str(ROOT/'tests'/t) for t in tests]]
    if os.name != 'posix':
        argv += ['-k', 'not actual_cli_process_through_full_adapter']
    # Keep progress even if the whole suite exhausts its orchestration budget.
    # Individual operation deadlines and test assertions are unchanged.
    with (output/'tests.txt').open('wb') as log:
        try:
            run=subprocess.run(argv,cwd=output,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        except subprocess.TimeoutExpired:
            run=subprocess.CompletedProcess(argv,124)
            receipt['failure']='suite_timeout'
    receipt['suite_timeout_seconds']=600
    receipt['exit']=run.returncode;receipt['command']=argv
    # The memory verbs from this installed wheel, with the redis extra present
    # and no server: the extra absent is the release gate's core check.
    memory=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/check_installed.py'),'--python',sys.executable,
                           '--mode','redis','--report',str(output/'memory-redis.json')],
                          cwd=output,capture_output=True,text=True)
    (output/'memory-redis.txt').write_text(memory.stdout+memory.stderr,encoding='utf-8')
    # The native memory reader read what this platform allows (Phase 2, D19): the receipt must say which.
    if memory.returncode==0:
        native=json.loads((output/'memory-redis.json').read_text(encoding='utf-8'))['memory']
        wanted=('available',['raw','personal','curated']) if os.name=='posix' else ('posix-only refusal',[])
        if (native.get('native_reader'),native.get('tiers_read'))!=wanted or native.get('reader_named')!='native':
            memory=subprocess.CompletedProcess(memory.args,1)
            receipt['checks'].append(f'native memory reader receipt unexpected: {native}')
        receipt['native_memory_reader']=native.get('native_reader')
        receipt['native_memory_tiers']=native.get('tiers_read')
    receipt['memory_redis']='passed' if memory.returncode==0 else 'failed'
    receipt['checks'].append('memory redis: extra present, server absent, unavailable; file scratch round trip; redis scratch never diverts'
                             if memory.returncode==0 else 'memory redis checks failed; see memory-redis.txt')
    if memory.returncode!=0 and run.returncode==0:
        run=subprocess.CompletedProcess(argv,memory.returncode)
    if os.name in ('posix','nt'):receipt['native_process_and_recovery']='passed' if run.returncode==0 else 'failed'
    receipt['status']='checks_passed' if run.returncode==0 else 'failed'
    (output/'platform.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('sources','command')},indent=2))
    return run.returncode


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    raise SystemExit(qualify(p.parse_args().output.absolute()))
