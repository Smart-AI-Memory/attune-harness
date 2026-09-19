"""Freeze the paired citation trial; only explicit --run dispatches models."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from baseline import ROOT, Transport, old, write
import citation_contract as contract

HERE = Path(__file__).resolve().parent
DEST = ROOT / 'docs/receipts/memory-citations-2026-09-16'


def data():
    return json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))


def preflight(cases):
    ids = [c['id'] for c in cases]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Cases require unique IDs')
    for case in cases:
        contract.source_ids(old.capture(case))
        if case['input']['grants']['assigned_model'] != 'luna':
            raise ValueError('Paired comparison requires initial Luna assignment')


def schedule(cases):
    return [dict(case_id=case['id'], arm=arm)
            for i, case in enumerate(cases)
            for arm in (('legacy', 'repaired') if i % 2 == 0 else ('repaired', 'legacy'))]


def protocol():
    cases = data()
    preflight(cases)
    sources = [HERE / name for name in ('DESIGN.md', 'baseline.py', 'citation_contract.py',
                'make_cases.py', 'cases.json', 'regressions.json', 'run_citations.py', 'test_citations.py')]
    sources += [ROOT / name for name in ('experiments/memory_sorter/sorter.py',
        'experiments/memory_sorter/transport.py', 'experiments/memory_sorter/make_cases.py',
        'experiments/memory_routing_v2/legacy.py', 'experiments/memory_routing/campaign.py',
        'experiments/memory_routing/memory_contracts.py', 'src/attune_harness/process.py')]
    sources += [old.previous.OLD, old.previous.PARSER]
    return dict(version=1, authorization='Patrick: proceed with the recommendation (citation contract repair).',
        models=old.previous.MODELS, order=schedule(cases), sampled=['condition-repaired'],
        planned_calls=17, max_native_calls=33, per_call_timeout=180, campaign_timeout=1800,
        automatic_retries=0, route='existing Codex ChatGPT subscription', direct_api_spend=False,
        live_memory_writes=0, voyage_calls=0,
        cli_version=subprocess.run(['codex', '--version'], capture_output=True, text=True, check=True).stdout.strip(),
        sources={str(p.relative_to(ROOT)): old.previous.sha(p) for p in sources},
        grading='Frozen case rubrics; unblinded lead grades every initial and final response, separating meaning, citation relevance and host acceptance.',
        limits='Eight synthetic paired cases, one observation per arm; combined schema/instruction repair. No production, all-Astra comparison, workload savings or reliability estimate.')


def verify_frozen(packet, path):
    if json.loads(path.read_text(encoding='utf-8')) != packet:
        raise ValueError('Frozen packet or sources changed')


class Campaign(Transport):
    def __init__(self, packet, destination, cases=None):
        self.cases = deepcopy(data() if cases is None else cases)
        preflight(self.cases)  # All packets checked before ledger creation or dispatch.
        if packet['order'] != schedule(self.cases) or packet['sampled'] != ['condition-repaired']:
            raise ValueError('Unexpected comparison schedule')
        super().__init__(packet, destination)

    def run(self):
        by_id = {c['id']: c for c in self.cases}
        for item in self.packet['order']:
            id = item['case_id'] + '-' + item['arm']
            job = dict(id=id, **item, state='started')
            self.ledger['jobs'].append(job)
            write(self.path, self.ledger)
            case = by_id[item['case_id']]
            call = lambda *args: self.call(id, *args)
            result = contract.execute(case, item['arm'], call)
            if id in self.packet['sampled']:
                result['audit'] = contract.audit(case, result, call)
            job.update(state='completed', result=result)
            write(self.path, self.ledger)
        self.ledger['status'] = 'completed'
        write(self.path, self.ledger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    packet = protocol()
    path = DEST / 'protocol.json'
    if args.run:
        verify_frozen(packet, path)
        Campaign(packet, DEST).run()
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        if path.exists():
            verify_frozen(packet, path)
        else:
            write(path, packet)
        print(path)
