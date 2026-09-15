"""Reproduce the opt-in local documentation review and extension recovery pilot."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'llama3.1:8b'
DIGEST = '46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e'
SERVER = '0.31.1'


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main(python, work, *, max_output_tokens=512, tokenizer_file=None):
    # Validate with the selected installed artifact before creating a workflow.
    subprocess.run([str(python), '-I', '-c',
                    'import sys; from attune_harness.ollama import validate_output_budget; '
                    'validate_output_budget(16384, int(sys.argv[1]))', str(max_output_tokens)], check=True)
    if tokenizer_file is not None:
        subprocess.run([str(python), '-I', '-c',
                        'import sys; from attune_harness.llama_tokens import LlamaTokenizer, PIN; '
                        'from attune_harness.ollama import ModelPin; LlamaTokenizer(sys.argv[1], ModelPin(**PIN))',
                        str(tokenizer_file)], check=True)
    work.mkdir(parents=True)
    (work/'commands').mkdir()
    (work/'generations').mkdir()
    records=[]
    def cli(args, code=0, status=None):
        started=time.monotonic()
        process=subprocess.run([str(python),'-I','-m','attune_harness',*map(str,args)],
                               cwd=work,capture_output=True,text=True,timeout=180)
        value=json.loads(process.stdout)
        entry={'argv':list(map(str,args)),'exit':process.returncode,'stderr':process.stderr,
               'elapsed_seconds':time.monotonic()-started,'response':value}
        records.append(entry);write(work/'commands'/f'{len(records):03}.json',entry)
        assert process.returncode==code,(args,value.get('error'),process.stderr)
        if status is not None:assert value['status']==status,value
        return value
    context=work/'context.json';write(context,{'schema_version':1,'project_root':str(ROOT)})
    document=ROOT/'docs/e2-revision-receipt.md'
    original_document=hashlib.sha256(document.read_bytes()).hexdigest()
    config,request=work/'participants.json',work/'request.json'
    command=[str(python),'-I','-m','attune_harness.ollama_review','--model',MODEL,'--digest',DIGEST,
             '--server-version',SERVER,'--receipts',str(work/'generations'),
             '--max-output-tokens',str(max_output_tokens)]
    if tokenizer_file is not None:
        command += ['--tokenizer-file', str(tokenizer_file)]
    local={'adapter':'command','tools':['retrieve','verify'],'max_turns':3,'max_tool_calls':2,'timeout':75}
    registry={'schema_version':1,'participants':{
        'local-lead':{**local,'command':command+['--seed','62001']},
        'local-reviewer':{**local,'command':command+['--seed','62002']}}}
    def accept(reg,config_path,request_path,lead,reviewer):
        write(config_path,reg)
        form=cli(['review-form','--config',config_path],status='ready')['submission']
        form.update(accepted=True,answers={'objective':'Review the E2 revision evidence and documentation. Identify unsupported claims and distinguish current results from historical evidence.',
            'query':'call-bound evidence availability revision','document':str(document),'context':str(context),
            'corpus':str(ROOT/'docs'),'lead':lead,'reviewer':reviewer})
        write(request_path,form)
    accept(registry,config,request,'local-lead','local-reviewer')
    directory=work/'review'
    paused=cli(['review',request,'--config',config,'--run-dir',directory,'--allow-external','--max-operations','7'],1,'paused')
    assert paused['events'][-1]['state']=='completed' and paused['events'][-1]['result']['action']['kind']=='final'
    prefix=copy.deepcopy(paused['events'])
    write(work/'first-result.json',paused)
    inspected=cli(['inspect-review',directory],1,'paused')
    complete=cli(['resume-review',directory,'--request',request,'--config',config,
                  '--checkpoint',inspected['checkpoint_digest'],'--allow-external'],1,'completed')
    assert complete['events'][:len(prefix)]==prefix
    assert complete['accepted']==paused['accepted']
    assert complete['document_outcome']=='unknown' and complete['verification']['result']['coverage']=={'total':34,'verified':9,'refuted':0,'unknown':25}
    assert all(v['tool_calls']==2 for v in complete['participants'].values())
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (work/'generations').glob('*/record.json')}
    assert len(before)==2
    assert cli(['resume-review',directory,'--request',request,'--config',config,
                '--checkpoint',complete['checkpoint_digest'],'--allow-external'],1,'completed')==complete
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
    # Lifecycle rehearsal uses real retrieval and verification, with no additional model calls.
    installed=subprocess.run([str(python),'-I','-c',
        'from importlib.metadata import distribution; print(distribution("attune-harness-evidence-example").locate_file("attune_harness_evidence"))'],
        cwd=work,capture_output=True,text=True,check=True)
    old=work/'bundle-0.1.0';shutil.copytree(Path(installed.stdout.strip()),old)
    new=work/'bundle-0.1.1';shutil.copytree(old,new)
    upgraded=json.loads((new/'extension.json').read_text());upgraded['version']='0.1.1';write(new/'extension.json',upgraded)
    bad=work/'incompatible-bundle';shutil.copytree(old,bad)
    invalid=copy.deepcopy(upgraded);invalid['tools']['search']='unsupported';write(bad/'extension.json',invalid)
    state_dir=work/'extension-state'
    state=cli(['extension','install',old/'extension.json','--state-dir',state_dir],status='disabled')
    def change(action,manifest=None,code=0,status=None):
        nonlocal state
        args=['extension',action,'--state-dir',state_dir,'--checkpoint',state['state_digest']]
        if manifest is not None:args+=['--manifest',manifest]
        value=cli(args,code,status)
        if code==0:state=value
        return value
    change('enable',status='enabled')
    (state_dir/'user-data.txt').write_text('Preserve Patrick pilot data.\n')
    ext_config,ext_request=work/'extension-participants.json',work/'extension-request.json'
    def accept_extension():
        reg={'schema_version':1,'extensions':{'evidence':{'state_dir':str(state_dir),'artifact_digest':state['artifact_digest']}},
             'participants':{name:{'adapter':'deterministic','tools':['evidence.search','verify'],'max_turns':3,'max_tool_calls':2}
                             for name in ('lead','reviewer')}}
        accept(reg,ext_config,ext_request,'lead','reviewer')
    accept_extension()
    ext_run=work/'extension-review'
    ext_paused=cli(['review',ext_request,'--config',ext_config,'--run-dir',ext_run,'--max-operations','4'],1,'paused')
    def ext_resume(saved,path=ext_run):
        return ['resume-review',path,'--request',ext_request,'--config',ext_config,'--checkpoint',saved['checkpoint_digest']]
    change('disable',status='disabled');disabled=copy.deepcopy(state)
    change('replace',bad/'extension.json',2,'unavailable')
    assert cli(['extension','inspect','--state-dir',state_dir])==disabled
    change('enable',status='enabled')
    first=cli(ext_resume(ext_paused),1,'completed')
    assert first['events'][:4]==ext_paused['events']
    held=work/'held-review'
    held_record=cli(['review',ext_request,'--config',ext_config,'--run-dir',held,'--max-operations','4'],1,'paused')
    # Keep the old accepted registry/request for rollback of held work.
    accepted_config=ext_config.read_bytes();accepted_request=ext_request.read_bytes()
    change('disable',status='disabled');change('replace',new/'extension.json',status='disabled');change('enable',status='enabled')
    cli(ext_resume(held_record,held),2,'unavailable')
    accept_extension()
    upgraded_run=cli(['review',ext_request,'--config',ext_config,'--run-dir',work/'upgraded-review'],1,'completed')
    assert any(e.get('result',{}).get('extension',{}).get('version')=='0.1.1' for e in upgraded_run['events'])
    change('disable',status='disabled');change('replace',old/'extension.json',status='disabled');change('enable',status='enabled')
    ext_config.write_bytes(accepted_config);ext_request.write_bytes(accepted_request)
    recovered=cli(ext_resume(held_record,held),1,'completed')
    assert recovered['events'][:4]==held_record['events']
    removed_run=work/'removed-review'
    removed_record=cli(['review',ext_request,'--config',ext_config,'--run-dir',removed_run,'--max-operations','4'],1,'paused')
    change('remove',status='removed')
    cli(ext_resume(removed_record,removed_run),2,'unavailable')
    assert (state_dir/'user-data.txt').read_text()=='Preserve Patrick pilot data.\n'
    assert hashlib.sha256(document.read_bytes()).hexdigest()==original_document
    summary={'status':'completed','commands':len(records),'document':str(document),'document_sha256':original_document,
        'review':str(directory/'record.json'),'model_generations':2,'max_output_tokens':max_output_tokens,
        'tokenizer_file':str(tokenizer_file) if tokenizer_file is not None else None,
        'paid_api_cost_usd':0,'document_outcome':'unknown',
        'accepted_inputs_preserved':True,'completed_events_replayed':True,'failed_upgrade_preserved_old_state':True,
        'upgraded_tool_invoked':True,'artifact_rollback_resumed_held_work':True,'removed_extension_blocks_resume':True,
        'user_data_preserved':True,'operator':'Codex acting on Patrick\u2019s selected workflow',
        'patrick_personally_operated':False,'preferred_path_accepted':False,'human_repair_seconds':None}
    write(work/'summary.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--work-dir',type=Path,required=True)
    parser.add_argument('--local-model',action='store_true',required=True,help='Explicitly enable exactly two local model generations; no paid APIs')
    parser.add_argument('--max-output-tokens',type=int,default=512,help='Token ceiling per narrative (default: 512)')
    parser.add_argument('--tokenizer-file',type=Path,help='Qualified local tokenizer for model-aware context accounting')
    args=parser.parse_args();main(args.python.absolute(),args.work_dir.absolute(),max_output_tokens=args.max_output_tokens,
                                tokenizer_file=args.tokenizer_file.absolute() if args.tokenizer_file else None)
