"""Frozen comparison preparation, admitted execution and evidence audit; no implicit calls."""
import argparse
import copy
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
import random
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def read(path):
    from attune_harness.review_contract import parse_json
    return parse_json(Path(path).read_text(),8*1024*1024)


def write(path,value):
    path=Path(path)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        if os.name=='posix':
            fd=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    finally:
        if temporary is not None and temporary.exists():temporary.unlink()


def modules():
    import attune_harness
    folder=Path(attune_harness.__file__).parent
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')}


def cases():
    assessment=[]
    rows=[('clean','Maple retains logs for 14 days.','Maple retains logs for 14 days.','no_supported_defect'),
          ('critical-retention','Maple retains logs for 90 days.','Maple retains logs for 14 days.','critical_defect'),
          ('unknown-region','Maple stores logs in Europe.','Maple region placement is unspecified.','unknown'),
          ('unsupported-guarantee','Maple guarantees recovery with no data loss.','Maple recovery may lose the last minute of writes.','critical_defect'),
          ('qualified-exception','Maple deletes ordinary logs after 14 days; legal holds are exempt.','Maple ordinary logs last 14 days. Legal holds remain until release.','no_supported_defect'),
          ('interrupted','Maple encrypts every backup.','Maple encryption is optional and disabled by default.','critical_defect')]
    for name,claim,reference,key in rows:
        assessment.append({'id':name,'slice':'assessment','document':claim+'\n\n[Maple reference](references/maple-reference.md)\n',
                           'reference':'# Maple reference\n\n'+reference+'\n','expected':key,'interrupt':name=='interrupted'})
    repairs=[('arithmetic','def compute(a,b):\n    return a-b\n','from module import compute\nassert compute(4,3)==7\n'),
             ('lower-bound','def clamp(value):\n    return min(0,value)\n','from module import clamp\nassert clamp(-2)==0 and clamp(3)==3\n'),
             ('empty-default','def label(value):\n    return value if value is not None else "unknown"\n','from module import label\nassert label("")=="unknown" and label("ready")=="ready"\n'),
             ('interrupted-repair','def clean(text):\n    return text.rstrip()\n','from module import clean\nassert clean("  ready  ")=="ready"\n')]
    return assessment+[{'id':name,'slice':'repair','source':source,'probe':probe,'expected':'passing_repair','interrupt':name=='interrupted-repair'} for name,source,probe in repairs]


def prepare(output,wheel):
    output.mkdir(parents=True,exist_ok=False)
    astra=read(ROOT/'participants.json')['participants']['astra-lead']
    fable=read(ROOT/'participants.fable.json')['participants']['fable-lead']
    sol={**astra,'model':'gpt-5.6-sol'}
    profiles={'claude-lead':{'lead':fable,'reviewer':astra},'codex-lead':{'lead':astra,'reviewer':sol}}
    fixture=cases();trials=[]
    for case in fixture:
        arms=('legacy','solo','independent-review') if case['slice']=='assessment' else ('direct','solo','required-review')
        for profile in profiles:
            for arm in arms:
                calls=2 if arm in ('legacy','independent-review','required-review') else 1
                trials.append({'id':case['id']+'-'+profile+'-'+arm,'case':case['id'],'profile':profile,'arm':arm,'max_calls':calls})
    random.Random(16092026).shuffle(trials)
    protocol={'schema_version':1,'candidate_wheel':str(wheel),'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
        'module_hashes':modules(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':fixture,'profiles':profiles,'trials':trials,'repetitions':1,
        'max_participant_calls':sum(t['max_calls'] for t in trials),'max_claude_calls':30,'max_codex_calls':62,
        'estimated_billed_usd':None,'estimated_tokens':None,'approved_spend_usd':None,
        'cache':'Clear process-local template cache before each fresh trial; no cross-trial response reuse',
        'grading':'Human blind grading of retained raw outputs; key fixed before execution; correction seconds explicitly recorded or unknown',
        'quality_floor':'No reduction in completed-correct outcomes or additional critical misses relative to matched baseline',
        'limits':'Synthetic one-repetition screening; no population accuracy claim; configured models are not live-qualified',
        'no_automatic_retry':True,'authorization_required':True}
    write(output/'protocol.json',protocol)
    write(output/'freeze.json',{'protocol_sha256':digest(protocol)})
    return verify(output)


def verify(output):
    protocol=read(output/'protocol.json');frozen=read(output/'freeze.json')
    if frozen != {'protocol_sha256':digest(protocol)}:
        raise ValueError('Frozen protocol or key was changed')
    if hashlib.sha256(Path(protocol['candidate_wheel']).read_bytes()).hexdigest()!=protocol['wheel_sha256'] or modules()!=protocol['module_hashes']:
        raise ValueError('Candidate artifact/modules differ from frozen protocol')
    if protocol['runner_sha256']!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError('Campaign runner changed; prepare a new frozen packet')
    ids=[t['id'] for t in protocol['trials']]
    if len(ids)!=len(set(ids)) or len({c['id'] for c in protocol['cases']})!=len(protocol['cases']):
        raise ValueError('Duplicate trial/case identity')
    return protocol


def registry_for(protocol,trial):
    selected=copy.deepcopy(protocol['profiles'][trial['profile']])
    if trial['arm'] in ('direct','required-review') or next(c for c in protocol['cases'] if c['id']==trial['case'])['slice']=='repair':
        for config in selected.values():
            config.pop('review_mode',None)
            config.update(tools=[],max_turns=1,max_tool_calls=0)
    return {'schema_version':1,'participants':selected}


def trial_execution(protocol,trial,directory,exchange_factory):
    """Same frozen evidence and effects; direct repair omits task intake/orchestration."""
    from attune_harness.task_contract import create_task,create_repair_task,accept_task,clear_template_cache
    from attune_harness.task_cli import present_task
    from attune_harness.task_policies import execute_task
    case=next(c for c in protocol['cases'] if c['id']==trial['case'])
    directory.mkdir(parents=True,exist_ok=False)
    registry=registry_for(protocol,trial);config=directory/'participants.json';write(config,registry)
    clear_template_cache()
    if case['slice']=='assessment':
        project=directory/'project';project.mkdir()
        (project/'guide.md').write_text(case['document'])
        references=project/'references';references.mkdir()
        (references/'maple-reference.md').write_text(case['reference'])
        context=directory/'context.json';write(context,{'schema_version':1,'project_root':'project'})
        goal='Assess Maple policy against the supplied reference.'
        criteria='Cite concrete defects and retain uncertainty; no tool-certified semantic claims.'
        if trial['arm']=='legacy':
            from attune_harness.review_contract import review_form,load_registry
            from attune_harness.review import review
            from attune_harness.recovery import resume_review
            submission=review_form(load_registry(config))['submission']
            submission.update(accepted=True,answers={'objective':goal+'\nAcceptance criteria: '+criteria,
                'query':'Maple','document':'project/guide.md','context':'context.json','corpus':'project','lead':'lead','reviewer':'reviewer'})
            request=directory/'request.json';write(request,submission)
            result=review(request,config,directory/'run',allow_external=True,max_operations=2 if case['interrupt'] else None,exchange_factory=exchange_factory)
            if result['status']=='paused':
                result=resume_review(directory/'run',request,config,result['checkpoint_digest'],allow_external=True,exchange_factory=exchange_factory)
            return result
        plan=trial['arm']
        answers={'criteria':criteria,'query':'Maple','document':'project/guide.md','context':'context.json','corpus':'project','assessor':'lead'}
        if plan=='independent-review':answers['reviewer']='reviewer'
        create_task(directory,config,goal=goal,plan=plan,directory=directory/'run',answers=answers)
    else:
        import subprocess
        checkout=directory/'checkout';subprocess.run(['git','init','-q',str(checkout)],check=True)
        (checkout/'module.py').write_text(case['source']);(checkout/'probe.py').write_text(case['probe'])
        probe={'argv':[sys.executable,'probe.py'],'cwd':'.','timeout':30,'max_output_bytes':8192,
               'environment':{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'},'oracle_paths':['probe.py']}
        if trial['arm']=='direct':
            return direct_repair(checkout,probe,registry['participants']['lead'],directory/'run',exchange_factory,interrupt=case['interrupt'])
        create_repair_task(directory,config,goal='Repair the seeded implementation defect.',checkout=checkout,allowed=['module.py'],
            probe=probe,worker='lead',criteria='Pass the immutable probe without modifying its oracle.',
            reviewer='reviewer' if trial['arm']=='required-review' else None,
            review='required' if trial['arm']=='required-review' else 'none',directory=directory/'run')
    response=present_task(directory/'run')['submission'];response.update(accepted=True)
    response['permissions']['external']=True;accept_task(directory/'run',response)
    result=execute_task(directory/'run',max_operations=2 if case['interrupt'] else None,exchange_factory=exchange_factory)
    if result['status']=='paused':result=execute_task(directory/'run',exchange_factory=exchange_factory)
    return result


def direct_repair(checkout,probe,config,directory,exchange_factory,*,interrupt=False):
    from attune_harness.repair import freeze,decode_patch,apply_patch,expected_snapshot,assert_snapshot
    from attune_harness.review_store import RunStore
    from attune_harness.recovery import RecoveryCursor,stable_id
    from attune_harness.task_runtime import perform_probe,dispatch_assignment,guarded_execution
    from attune_harness.review_contract import canonical
    from attune_harness.review_participants import PROTOCOL
    scope=freeze(checkout,['module.py'],probe,directory);store=RunStore(directory)
    identity=str(uuid4());attempt=stable_id(identity,'direct')
    record={'schema_version':1,'operation':'direct-repair-baseline','status':'running','events':[],
            'participants':{},'recovery':{'profile':'direct-repair-v1'},'record_path':str(store.path)}
    cursor=RecoveryCursor(record,store,2 if interrupt else None)
    def steps():
        before=perform_probe(cursor,scope,'probe:before',expected=scope['before'])
        if before['failure']!='nonzero_exit' or before['returncode']<=0:raise ValueError('Baseline did not establish failure')
        payload={'before_files':scope['inputs'],'before_hashes':{n:scope['before'][n]['sha256'] for n in scope['allowed']},'probe':scope['probe'],'baseline_result':before}
        turn={'task_id':identity,'attempt_id':attempt,'turn_id':stable_id(attempt,'0'),'requirement_revision':digest(scope),
              'participant_id':'lead','role':'worker','objective':'Repair the seeded implementation defect.\nAcceptance criteria: Pass the immutable probe without modifying its oracle.',
              'query':'','document':{'path':scope['root'],'text':canonical(payload)},'initial_retrieval':None,'history':[],
              'tools':[],'remaining_tool_calls':0,'remaining_turns':1,'repair':payload,
              'protocol':PROTOCOL+' Return a final action whose text is JSON {"schema_version":1,"replacements":[{"path":"accepted relative path","before_sha256":"accepted hash","text":"complete replacement"}]}. Do not change the probe or claim acceptance.'}
        outcome={'status':'running'};record['participants']['worker']=outcome
        response=dispatch_assignment(cursor,attempt+':turn:0',turn,config,exchange_factory(config,checkout),outcome)
        if response['action']['kind']!='final':raise ValueError('Direct worker requested a tool')
        proposal=decode_patch(response['action']['text'],scope)
        record['patch']=proposal;record['before_probe']=before
        record['replacements']=apply_patch(scope,proposal,cursor)
        after=perform_probe(cursor,scope,'probe:after');record['after_probe']=after
        assert_snapshot(scope,expected_snapshot(scope,record['events']))
        if not after['passed']:raise ValueError('Direct repair probe failed')
        outcome.update(status='completed',text=response['action']['text'])
        record.update(status='completed',acceptance='verified_within_probe_scope')
    with store.lease():
        guarded_execution(record,store,steps)
        if record['status']=='paused':
            cursor=RecoveryCursor(record,store)
            record['status']='running';record.pop('error',None)
            guarded_execution(record,store,steps)
    return record


def native_usage(adapter,raw):
    """Observed metadata only; reasoning output is a subset, never added twice."""
    usage={};cost=None
    try:
        if adapter=='claude':
            value=json.loads(raw);usage=value.get('usage',{});cost=value.get('total_cost_usd')
        else:
            rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
            candidates=[v['usage'] for v in rows if v.get('type')=='turn.completed' and 'usage' in v]
            if len(candidates)==1:usage=candidates[0]
    except (ValueError,TypeError,KeyError):
        pass
    if not isinstance(usage,dict):usage={}
    keys=('input_tokens','output_tokens','reasoning_output_tokens','cached_input_tokens','cache_read_input_tokens','cache_creation_input_tokens')
    return {**{k:usage.get(k) if type(usage.get(k)) is int and usage[k]>=0 else None for k in keys},
            'reported_cost_usd':cost if type(cost) in (int,float) and math.isfinite(cost) and cost>=0 else None}


def measured_factory(output,trial,row,ledger):
    """Serial experiment instrumentation around the unchanged production transport."""
    from unittest.mock import patch
    from attune_harness import review_participants
    original=review_participants.NativeExchange
    class Measured(review_participants.ReviewExchange):
        def __call__(self,raw):
            captures=[]
            def capture(adapter,**kwargs):
                calls=row.setdefault('native_calls',[])
                if len(calls)>=trial['max_calls']:raise ValueError('Frozen participant-call ceiling exhausted')
                entry={'adapter':adapter,'requested_model':kwargs.get('model'),'state':'dispatching'}
                calls.append(entry);write(output/'ledger.json',ledger)
                instance=original(adapter,**kwargs);captures.append((instance,entry))
                return instance
            try:
                with patch.object(review_participants,'NativeExchange',capture):
                    return super().__call__(raw)
            finally:
                for instance,entry in captures:
                    process=instance.last_process
                    index=row['native_calls'].index(entry)
                    evidence={'adapter':entry['adapter'],'requested_model':entry['requested_model'],
                              'stdout':process.stdout if process else None,'stderr':process.stderr if process else None,
                              'failure':process.failure if process else 'no_process_receipt'}
                    path=output/'runs'/trial['id']/('native-'+str(index)+'.json')
                    write(path,evidence)
                    entry.update(state='observed' if process else 'unresolved',raw_sha256=digest(evidence),
                                 **native_usage(entry['adapter'],process.stdout if process else ''))
                    for metric in ('input_tokens','output_tokens','reasoning_output_tokens'):
                        values=[c.get(metric) for c in row['native_calls']]
                        row[metric]=sum(values) if all(v is not None for v in values) else None
                    write(output/'ledger.json',ledger)
    return Measured


def execute(output,authorization):
    protocol=verify(output);grant=read(authorization)
    from attune_harness.review_contract import fields
    fields(grant,('protocol_sha256','approved','max_calls','estimated_usd','budget_reviewed','native_profiles_confirmed'))
    if (grant['protocol_sha256']!=digest(protocol) or grant['approved'] is not True or
        grant['budget_reviewed'] is not True or grant['native_profiles_confirmed'] is not True or
        type(grant['max_calls']) is not int or grant['max_calls']<protocol['max_participant_calls'] or
        type(grant['estimated_usd']) not in (int,float) or not math.isfinite(grant['estimated_usd']) or grant['estimated_usd']<0):
        raise ValueError('Current explicit protocol/call/spend/profile admission required')
    # Admission records an operator decision; it is not authentication or a provider spending cap.
    from attune_harness.review_participants import ReviewExchange
    runs=output/'runs';runs.mkdir(exist_ok=False)
    ledger={'protocol_sha256':digest(protocol),'authorization':grant,'trials':[],'status':'running','billed_usd':None}
    write(output/'ledger.json',ledger)
    for trial in protocol['trials']:
        row={'trial_id':trial['id'],'state':'dispatching','result_sha256':None,'billed_usd':None,'human_correction_seconds':None,'input_tokens':None,'output_tokens':None,'reported_model_identities':None}
        ledger['trials'].append(row);write(output/'ledger.json',ledger)
        start=time.perf_counter()
        try:
            result=trial_execution(protocol,trial,runs/trial['id'],measured_factory(output,trial,row,ledger))
        except BaseException as exc:
            row.update(state='unresolved',error={'type':type(exc).__name__,'detail':str(exc)},elapsed_seconds=time.perf_counter()-start)
            ledger['status']='stopped';write(output/'ledger.json',ledger)
            raise
        path=runs/trial['id']/'result.json';write(path,result)
        row['reported_model_identities']={k:v.get('last_identity') for k,v in result.get('execution',result).get('participants',{}).items()}
        row.update(state=result['status'],elapsed_seconds=time.perf_counter()-start,result_sha256=digest(result))
        write(output/'ledger.json',ledger)
        saved_events=result.get('execution',result).get('events',[])
        if result['status'] in ('unresolved','unavailable') or any(e['state']!='completed' and e['phase']=='dispatching' for e in saved_events):
            ledger['status']='stopped';write(output/'ledger.json',ledger)
            return ledger
    ledger['status']='awaiting_blind_grades';write(output/'ledger.json',ledger)
    return ledger


def blind(output):
    protocol=verify(output);ledger=read(output/'ledger.json')
    if {r['trial_id'] for r in ledger['trials']}!={t['id'] for t in protocol['trials']}:
        raise ValueError('Retain the full trial set before blind grading')
    packet=[];mapping={}
    for row in ledger['trials']:
        result=read(output/'runs'/row['trial_id']/'result.json')
        if digest(result)!=row['result_sha256']:raise ValueError('Changed retained result')
        identifier=digest({'protocol':digest(protocol),'trial':row['trial_id']})[:20]
        mapping[identifier]=row['trial_id']
        run=result.get('execution',result)
        trial=next(t for t in protocol['trials'] if t['id']==row['trial_id'])
        case=next(c for c in protocol['cases'] if c['id']==trial['case'])
        def probe_view(probe):
            if probe is None:return None
            value={k:probe[k] for k in ('passed','returncode','failure','stdout','stderr')}
            for k in ('stdout','stderr'):
                value[k]=value[k].replace(str(output/'runs'/row['trial_id']),'<trial>')
            return value
        packet.append({'blind_id':identifier,'source':{k:v for k,v in case.items() if k not in ('expected','id','interrupt')},'status':result['status'],
            'narratives':[p.get('text') for p in run.get('participants',{}).values()],
            'patch':run.get('patch'),'before_probe':probe_view(run.get('before_probe')),'after_probe':probe_view(run.get('after_probe')),
            'document_outcome':run.get('document_outcome')})
    random.Random(418).shuffle(packet)
    write(output/'blind-packet.json',packet)
    write(output/'blind-key.json',{'protocol_sha256':digest(protocol),'packet_sha256':digest(packet),'mapping':mapping})
    return {'records':len(packet),'packet':'blind-packet.json','note':'Withhold blind-key.json and raw identity records from graders. Prose may still reveal a model.'}


def audit(output,grades):
    protocol=verify(output);ledger=read(output/'ledger.json');submitted=read(grades)
    if submitted and 'blind_id' in submitted[0]:
        key=read(output/'blind-key.json')
        if key['protocol_sha256']!=digest(protocol) or key['packet_sha256']!=digest(read(output/'blind-packet.json')):
            raise ValueError('Blind packet/key changed')
        expected_mapping={digest({'protocol':digest(protocol),'trial':t['id']})[:20]:t['id'] for t in protocol['trials']}
        if key['mapping']!=expected_mapping:raise ValueError('Blind mapping changed')
        submitted=[{'trial_id':key['mapping'][g['blind_id']],**{k:v for k,v in g.items() if k!='blind_id'}} for g in submitted]
    expected={t['id'] for t in protocol['trials']}
    rows=ledger['trials']
    if (ledger['protocol_sha256']!=digest(protocol) or {r['trial_id'] for r in rows}!=expected or len(rows)!=len(expected) or
            {g['trial_id'] for g in submitted}!=expected or len(submitted)!=len(expected)):
        raise ValueError('Incomplete, duplicate or foreign trials/grades; retain failures')
    for row in rows:
        result=read(output/'runs'/row['trial_id']/'result.json')
        if digest(result)!=row['result_sha256']:raise ValueError('Retained result changed after grading')
    from attune_harness.review_contract import fields
    for grade in submitted:
        fields(grade,('trial_id','completed_correct','critical_miss','unsupported_findings','human_correction_seconds'))
        if (type(grade['completed_correct']) is not bool or type(grade['critical_miss']) is not bool or
                type(grade['unsupported_findings']) is not int or grade['unsupported_findings']<0 or
                (grade['human_correction_seconds'] is not None and (type(grade['human_correction_seconds']) not in (int,float) or not math.isfinite(grade['human_correction_seconds']) or grade['human_correction_seconds']<0))):
            raise ValueError('Malformed grading evidence')
    row_by_id={r['trial_id']:r for r in rows}
    if any(g['completed_correct'] and row_by_id[g['trial_id']]['state']!='completed' for g in submitted):
        raise ValueError('An unfinished/failed execution cannot count as completed-correct')
    by_id={g['trial_id']:g for g in submitted};floor=True
    slice_floor={'assessment':True,'repair':True}
    for trial in protocol['trials']:
        case=next(c for c in protocol['cases'] if c['id']==trial['case'])
        baseline='legacy' if case['slice']=='assessment' else 'direct'
        original=by_id[trial['case']+'-'+trial['profile']+'-'+baseline];candidate=by_id[trial['id']]
        if (original['completed_correct'] and not candidate['completed_correct']) or (candidate['critical_miss'] and not original['critical_miss']):
            floor=False;slice_floor[case['slice']]=False
    return {'status':'quality_floor_passed' if floor else 'revise','quality_floor':floor,'slice_quality_floor':slice_floor,
            'completed_correct':sum(g['completed_correct'] for g in submitted),
            'critical_misses':sum(g['critical_miss'] for g in submitted),
            'unsupported_findings':sum(g['unsupported_findings'] for g in submitted),
            'billed_usd':None if any(r['billed_usd'] is None for r in rows) else sum(r['billed_usd'] for r in rows),
            'human_seconds':None if any(g['human_correction_seconds'] is None for g in submitted) else sum(g['human_correction_seconds'] for g in submitted),
            'cost_ranking':'unqualified; no token/billing inference from missing data'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('prepare','verify','execute','blind','audit'):
        q=sub.add_parser(name);q.add_argument('output',type=Path)
        if name=='prepare':q.add_argument('--wheel',type=Path,required=True)
        if name=='execute':q.add_argument('--authorization',type=Path,required=True)
        if name=='audit':q.add_argument('--grades',type=Path,required=True)
    a=p.parse_args();directory=a.output.absolute()
    if a.command=='prepare':result=prepare(directory,a.wheel.absolute())
    elif a.command=='verify':result=verify(directory)
    elif a.command=='execute':result=execute(directory,a.authorization)
    elif a.command=='blind':result=blind(directory)
    else:result=audit(directory,a.grades)
    print(json.dumps(result,indent=2,allow_nan=False))
