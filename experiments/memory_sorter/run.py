"""Freeze the disposable sorter campaign; explicit --run dispatches once."""
import argparse
import json
from pathlib import Path
import subprocess
from copy import deepcopy
import sorter
from transport import Transport,write

ROOT=sorter.ROOT;HERE=Path(__file__).resolve().parent
DEST=ROOT/'docs/receipts/memory-sorter-2026-09-16'
SAMPLED=('condition','forget','calculation')
MATCHED=('consolidate','chronology','calculation')


def data():
    return json.loads((HERE/'cases.json').read_text(encoding='utf-8'))


def schedule():
    order=[]
    for id in ('absent','capture','consolidate','distinct','condition','classify','choice','chronology','forget','untrusted','calculation','assigned'):
        if id in ('consolidate','calculation'): order.append(dict(case_id=id,arm='direct'))
        order.append(dict(case_id=id,arm='queue'))
        if id=='chronology': order.append(dict(case_id=id,arm='direct'))
    order.extend(dict(case_id=c['case_id'],arm='control',control_id=c['id']) for c in data()['controls'])
    return order


def protocol():
    sources=[HERE/name for name in ('DESIGN.md','make_cases.py','cases.json','sorter.py','transport.py','run.py','test_sorter.py')]
    sources += [ROOT/'experiments/memory_routing_v2/legacy.py',ROOT/'experiments/memory_routing/campaign.py',ROOT/'experiments/memory_routing/memory_contracts.py',sorter.previous.OLD,sorter.previous.PARSER,ROOT/'src/attune_harness/process.py']
    return dict(version=1,authorization='Patrick: proceed with the next experiment (mixed memory queue sorter).',
        models=sorter.previous.MODELS,order=schedule(),sampled=list(SAMPLED),matched=list(MATCHED),
        planned_calls=22,max_native_calls=33,per_call_timeout=180,campaign_timeout=1800,automatic_retries=0,
        route='existing Codex ChatGPT subscription',direct_api_spend=False,live_memory_writes=0,voyage_calls=0,
        cli_version=subprocess.run(['codex','--version'],capture_output=True,text=True,check=True).stdout.strip(),
        sources={str(p.relative_to(ROOT)):sorter.previous.sha(p) for p in sources},
        grading='Pre-dispatch source rubrics; unblinded lead grading separates operation, disposition, meaning, host enforcement, natural audits and injected controls.',
        limits='Synthetic queue, one observation per case/profile; no production effects, installed taxonomy qualification, workload distribution, active-lead comparison or dollar estimate.')


class Campaign(Transport):
    def run(self):
        fixtures=data();by_id={c['id']:c for c in fixtures['cases']};controls={c['id']:c for c in fixtures['controls']}
        for item in self.packet['order']:
            id=item.get('control_id',item['case_id']+'-'+item['arm'])
            job=dict(id=id,**item,state='started');self.ledger['jobs'].append(job);write(self.path,self.ledger)
            case=by_id[item['case_id']];call=lambda *args:self.call(id,*args)
            if item['arm']=='control':
                control=controls[item['control_id']];bound=sorter.capture(case)
                assessment=sorter.assess(bound,dict(value=control['proposal']),case['input'])
                if not assessment['accepted']: self.stop('Injected control failed structural checks')
                result=dict(binding=bound,first=assessment,final=assessment,action=sorter.action(assessment,'luna'),escalated=False,
                            initial_model=None,final_model=None,audit=None)
                result['audit']=sorter.audit(case,result,call)
            else:
                result=sorter.execute(case,call,model='astra' if item['arm']=='direct' else None)
                if item['arm']=='queue' and item['case_id'] in self.packet['sampled']:
                    result['audit']=sorter.audit(case,result,call)
            job.update(state='completed',result=result);write(self.path,self.ledger)
        self.ledger['status']='completed';write(self.path,self.ledger)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    packet=protocol();path=DEST/'protocol.json'
    if args.run:
        if json.loads(path.read_text())!=packet: raise ValueError('Frozen packet or sources changed')
        Campaign(packet,DEST).run()
    else:
        DEST.mkdir(parents=True,exist_ok=True)
        if path.exists() and json.loads(path.read_text())!=packet: raise ValueError('Refusing frozen packet replacement')
        write(path,packet);print(path)
