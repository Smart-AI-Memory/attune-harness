"""New frozen campaign using the unchanged v1 native supervisor."""

import argparse
import json
from pathlib import Path
import subprocess

from jsonschema import ValidationError
from legacy import ROOT, previous
import contract_v2 as contract

HERE = Path(__file__).resolve().parent
DEST = ROOT / 'docs/receipts/memory-routing-v2-2026-09-16'
AUDIT_JOB = 'a_conditional-revised'


def cases():
    return json.loads((HERE / 'cases.json').read_text())


def schedule():
    result = []
    for index, case in enumerate(cases()):
        if case['experiment'] == 'A':
            arms = ('legacy', 'revised') if index % 2 == 0 else ('revised', 'legacy')
        else:
            arms = ('direct', 'coarse', 'typed')
            offset = (index - 4) % 3
            arms = arms[offset:] + arms[:offset]
        result.extend({'case_id': case['id'], 'arm': arm} for arm in arms)
    return result


def protocol():
    files = [HERE / name for name in ('DESIGN.md', 'cases.json', 'legacy.py', 'contract_v2.py', 'run_revised.py', 'test_revised.py')]
    files += [ROOT / 'experiments/memory_routing' / name for name in ('campaign.py', 'memory_contracts.py')]
    files += [previous.OLD, previous.PARSER, ROOT / 'src/attune_harness/process.py']
    return {
        'version': 2, 'models': previous.MODELS, 'order': schedule(), 'audit_job': AUDIT_JOB,
        'max_native_calls': 26, 'natural_maximum_calls': 24, 'per_call_timeout': 180,
        'campaign_timeout': 1800, 'automatic_retries': 0,
        'authorization': 'Patrick: proceed with the plan and routing experiments, after checking the three proposed changes.',
        'route': 'existing Codex ChatGPT subscription', 'direct_api_spend': False,
        'voyage_calls': 0, 'anthropic_calls': 0, 'live_memory_writes': 0,
        'cli_version': subprocess.run(['codex', '--version'], capture_output=True, text=True, check=True).stdout.strip(),
        'sources': {str(path.relative_to(ROOT)): previous.sha(path) for path in files},
        'grading': 'Frozen source-grounded rubrics; unblinded lead grading separate from fields, routing policy and one counted source-fidelity audit.',
        'limits': 'Complete contract/policy comparisons, tiny synthetic sample; legacy version ambiguity retained; no active-lead or installed-memory qualification.',
    }


def assess(bound, reply, flavor, current):
    try:
        if flavor == 'legacy':
            contract.check_current(bound, current['record'], current['sources'])
            candidate = previous.normalize(bound, reply['value'], 'rewrite', current['record'])
        else:
            candidate = contract.normalize(bound, reply['value'], flavor,
                current_record=current['record'], current_sources=current['sources'])
        return {'accepted': True, 'response': reply['value'], 'candidate': candidate}
    except (ValueError, ValidationError, KeyError, TypeError) as error:
        return {'accepted': False, 'response': reply.get('value'), 'raw_text': reply.get('text'),
                'error': str(error), 'failure_kind': 'stale' if isinstance(error, contract.StaleInput) else 'contract'}


def execute_job(case, arm, call, current=None):
    bound = contract.capture(case)
    current = current or (lambda: case['input'])
    if case['experiment'] == 'A':
        flavor = 'legacy' if arm == 'legacy' else 'typed'
        payload = previous.worker_prompt(bound, 'rewrite') if flavor == 'legacy' else contract.prompt(bound, flavor)
        schema = previous.REWRITE if flavor == 'legacy' else contract.TYPED
        reply = call('worker', 'luna', payload, schema)
        final = assess(bound, reply, flavor, current())
        action = ('legacy_result' if flavor == 'legacy' else contract.next_action(final, 'luna', flavor))
        return {'initial_model': 'luna', 'final_model': 'luna', 'escalated': False,
                'final': final, 'action': action, 'audit': None, 'binding': bound}
    flavor = 'coarse' if arm == 'coarse' else 'typed'
    model = 'astra' if arm == 'direct' else contract.initial_route(bound) if arm == 'typed' else 'luna'
    reply = call('worker', model, contract.prompt(bound, flavor), contract.COARSE if flavor == 'coarse' else contract.TYPED)
    first = assess(bound, reply, flavor, current())
    action = contract.next_action(first, model, flavor)
    result = {'initial_model': model, 'final_model': model, 'escalated': False,
              'first': first, 'final': first, 'action': action, 'audit': None, 'binding': bound}
    if action == 'escalate':
        reply = call('escalation', 'astra', contract.prompt(bound, 'typed', first), contract.TYPED)
        final = assess(bound, reply, 'typed', current())
        result.update(final_model='astra', escalated=True, final=final,
                      action=contract.next_action(final, 'astra', 'typed'))
    return result


def sampled_audit(case, result, call, current=None):
    if not result['final']['accepted'] or result['action'] != 'proposal_ready':
        return {'state': 'skipped_no_update_proposal'}
    bound = result['binding']
    current = current or (lambda: case['input'])
    try:
        state = current()
        contract.check_current(bound, state['record'], state['sources'])
    except contract.StaleInput as error:
        result['action'] = 'stale_stop'
        return {'state': 'stale', 'error': str(error)}
    reply = call('audit', 'astra', contract.audit_prompt(bound, result['final']), contract.AUDIT)
    try:
        state = current()
        contract.check_current(bound, state['record'], state['sources'])
        result['action'] = contract.audit_action(bound, reply['value'])
        return {'state': 'completed', 'response': reply['value'], 'receipt': reply.get('receipt')}
    except contract.StaleInput as error:
        result['action'] = 'stale_stop'
        return {'state': 'stale', 'response': reply.get('value'), 'error': str(error)}
    except (ValueError, ValidationError, KeyError, TypeError) as error:
        result['action'] = 'quarantined'
        return {'state': 'rejected', 'response': reply.get('value'), 'error': str(error)}


class Campaign(previous.Campaign):
    def run(self):
        by_id = {case['id']: case for case in cases()}
        for item in self.packet['order']:
            case = by_id[item['case_id']]
            job_id = item['case_id'] + '-' + item['arm']
            job = {'id': job_id, **item, 'state': 'started'}
            self.ledger['jobs'].append(job)
            previous.write(self.path, self.ledger)
            call = lambda *args: self.call(job_id, *args)
            result = execute_job(case, item['arm'], call)
            if job_id == self.packet['audit_job']:
                result['audit'] = sampled_audit(case, result, call)
            job.update(state='completed', result=result)
            previous.write(self.path, self.ledger)
        self.ledger['status'] = 'completed'
        previous.write(self.path, self.ledger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    packet = protocol()
    path = DEST / 'protocol.json'
    if args.run:
        if json.loads(path.read_text()) != packet:
            raise ValueError('Frozen source, settings or protocol changed')
        Campaign(packet, DEST).run()
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        if path.exists() and json.loads(path.read_text()) != packet:
            raise ValueError('Refusing to replace frozen protocol')
        previous.write(path, packet)
        print(str(path))
