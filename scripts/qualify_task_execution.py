"""Independent installed task consumers. No source-path injection or live providers."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def qualify(python, wheel, output):
    output.mkdir(parents=True, exist_ok=False)
    work = Path(tempfile.mkdtemp(prefix='harness-task-installed-')).resolve()
    rows = []
    def call(argv, *, expected=0, label=None):
        started=time.perf_counter_ns()
        proc=subprocess.run([str(python),'-I',*map(str,argv)],cwd=work,capture_output=True,text=True,timeout=60)
        row={'argv':list(map(str,argv)),'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,
             'elapsed_ms':(time.perf_counter_ns()-started)/1e6}
        rows.append(row)
        (output/f'{len(rows):03d}-{label or "command"}.json').write_text(json.dumps(row,indent=2))
        assert proc.returncode==expected,row
        return json.loads(proc.stdout)
    identity=call(['-c', 'import attune_harness,hashlib,json,pathlib,sys; p=pathlib.Path(attune_harness.__file__).parent; print(json.dumps({"location":str(p),"python":sys.version,"modules":{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in p.glob("*.py")}}))'],label='identity')
    assert not Path(identity['location']).is_relative_to(ROOT/'src')
    with zipfile.ZipFile(wheel) as z:
        packaged={Path(n).name:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('attune_harness/') and n.endswith('.py')}
    source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/attune_harness').glob('*.py')}
    assert identity['modules']==packaged==source,'Installed/wheel/source module mismatch'
    (work/'project').mkdir()
    (work/'project/guide.md').write_text('[Quartz policy](reference.md)')
    (work/'project/reference.md').write_text('Quartz retention policy is a fixture.')
    (work/'context.json').write_text(json.dumps({'schema_version':1,'project_root':'project'}))
    peer=work/'peer.py'
    peer.write_text('import json,sys,pathlib\nr=json.load(sys.stdin)\np=pathlib.Path("peer-calls.jsonl")\nwith p.open("a") as s:s.write(json.dumps(r)+"\\n")\nprint(json.dumps({"schema_version":1,"request_digest":r["request_digest"],"action":{"kind":"final","text":"Independent installed assessment; source reference.md. Interpretation unverified."}}))\n')
    config={'schema_version':1,'participants':{
        'alpha':{'adapter':'deterministic','tools':['retrieve','verify'],'max_turns':3,'max_tool_calls':2},
        'beta':{'adapter':'command','command':[str(python),'-I',str(peer)],'timeout':10,'tools':[],'max_turns':1,'max_tool_calls':0}}}
    registry=work/'participants.json';registry.write_text(json.dumps(config))
    ids=[]
    for plan in ('solo','independent-review'):
        task=work/plan
        argv=['-m','attune_harness','review','--goal','Check this guide','--criteria','Report evidence and uncertainty',
              '--project',work,'--config',registry,'--task-dir',task,'--plan',plan,'--query','quartz policy',
              '--document','project/guide.md','--context','context.json','--corpus','project','--assessor','alpha','--accept','--pause-after','2']
        if plan=='independent-review':argv+=['--reviewer','beta','--allow-external']
        paused=call(argv,expected=1,label=plan+'-paused');assert paused['status']=='paused'
        status=call(['-m','attune_harness','status',task],label='status');assert status==paused
        done=call(['-m','attune_harness','resume',task],label=plan+'-resume');assert done['status']=='completed'
        assert done['request']['task_id']==paused['request']['task_id']
        assert done['execution']['events'][:2]==paused['execution']['events']
        count=1 if plan=='solo' else 2
        assert len([e for e in done['execution']['events'] if e['kind']=='participant_turn'])==count
        assert done['execution']['integration']['semantic_verification'] is False
        again=call(['-m','attune_harness','resume',task],label='complete-replay');assert again==done
        ids.append(done['request']['task_id'])
    assert len(set(ids))==2
    peer_calls=[json.loads(line) for line in (work/'project/peer-calls.jsonl').read_text().splitlines()]
    assert len(peer_calls)==1
    assert 'Deterministic demonstration' not in json.dumps(peer_calls[0])
    # Installed in-process cache comparison on exactly the same accepted task.
    code='''import json,time,statistics
from attune_harness.task_cli import present_task,clear_template_cache
from pathlib import Path
p=Path('solo'); samples={k:[] for k in ('cold','warm','bypass')}
for i in range(30):
 for key in ('cold','warm','bypass'):
  if key=='cold':clear_template_cache()
  t=time.perf_counter_ns();v=present_task(p,bypass=key=='bypass')
  samples[key].append({'elapsed_ms':(time.perf_counter_ns()-t)/1e6,'metrics':v['intake_metrics']})
print(json.dumps(samples))'''
    samples=call(['-c',code],label='intake-comparison')
    fresh=[]
    for i in range(5):
        call(['-c',"import json;from attune_harness.task_cli import present_task;from pathlib import Path;print(json.dumps(present_task(Path('solo'))['intake_metrics']))"],label='fresh-intake')
        fresh.append(rows[-1]['elapsed_ms'])
    summary={'status':'passed','work_directory':str(work),'identity':identity,'wheel':str(wheel),
             'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'module_count':len(packaged),
             'cli_and_measurement_processes':len(rows),'native_provider_calls':0,'independent_command_calls':len(peer_calls),
             'host':platform.platform(),'supported_observation':'macOS Python3.10 installed assessment software only',
             'native_quality':'pending','other_platforms':'not run',
             'intake_median_ms':{k:statistics.median(x['elapsed_ms'] for x in v) for k,v in samples.items()},
             'fresh_process_median_ms':statistics.median(fresh),'cache_limit':16,'avoided_model_calls':0}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='identity'},indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python',type=Path,required=True);p.add_argument('--wheel',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();qualify(a.python.absolute(),a.wheel.absolute(),a.output.absolute())
