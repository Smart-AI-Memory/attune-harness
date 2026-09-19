"""Retain isolated controller/adapter evidence and verify preserved experiments."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from worker import ROOT
from replay_worker import demonstrate, fixtures
from probe_adapter import probe

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_prior():
    result = {}
    for name in ('luna-stage-contract', 'memory-routing', 'memory-routing-v2', 'memory-sorter', 'memory-citations'):
        directory = ROOT / 'docs/receipts' / (name + '-2026-09-16')
        protocol = read(directory/'protocol.json')
        analysis = read(directory/'analysis.json')
        for source,digest in protocol['sources'].items():
            assert sha(ROOT/source) == digest, source
        for part in ('protocol', 'ledger'):
            assert sha(directory/(part+'.json')) == analysis[part+'_sha256']
        if 'grades_sha256' in analysis:
            assert sha(directory/'grades.json') == analysis['grades_sha256']
        receipts = 0
        for row in analysis['rows']:
            hashes = row.get('receipt_hashes', row.get('receipts',
                {row['receipt']:row['receipt_sha256']} if 'receipt' in row else {}))
            for receipt,digest in hashes.items():
                assert sha(directory/receipt) == digest, receipt
                receipts += 1
        result[name] = dict(sources=len(protocol['sources']), native_receipts=receipts,
                           protocol_sha256=sha(directory/'protocol.json'), ledger_sha256=sha(directory/'ledger.json'))
    for case in fixtures()['cases']:
        for call in case['calls']:
            original = ROOT/call['source']
            assert sha(original) == call['source_sha256']
            receipt = read(original)
            assert (receipt['prompt'], receipt['schema'], receipt['value']) == (call['prompt'], call['schema'], call['reply']['value'])
            assert (receipt['attempt']['role'], receipt['attempt']['model']) == (call['role'], call['model'])
    return result


def collect(destination, suite_log):
    prior = verify_prior()
    replay = demonstrate()
    adapter = probe()
    raw_log = suite_log.read_text(encoding='utf-8')
    match = re.search(r'\b(\d+) passed in ([0-9.]+)s', raw_log)
    if not match or any(word in raw_log for word in ('FAILED', 'ERROR')):
        raise ValueError('A passing central suite log is required')
    sources = list(HERE.glob('*.py')) + [HERE/'DESIGN.md', HERE/'replay.json']
    sources += [ROOT/'src/attune_harness'/name for name in
                ('review_store.py','review_contract.py','features.py','adapters.py','windows.py')]
    memory_root = Path(adapter['source']).parent
    external = [memory_root/name for name in ('file_stash.py','atomic_io.py','personal.py',
                'session_stash.py','promotion.py','long_term_classification.py')]
    receipt = dict(created_at=datetime.now(timezone.utc).isoformat(),
        scope='Disposable proposal-only worker; no new model calls or production memory integration',
        suite=dict(passed=int(match[1]),seconds=float(match[2]),log_sha256=sha(suite_log)),
        native_calls=0, replayed_calls=replay['replayed_calls'],
        sources={str(p.relative_to(ROOT)):sha(p) for p in sources},
        external_sources={str(p):sha(p) for p in external}, prior_verified=prior,
        review=dict(receipt_type='evidence-chain',agent='luna_protocol_review',read_only=True,
            finding='Sampled terminal stronger needs_reasoning replies caused an unnecessary additional audit.',
            disposition='Excluded unresolved_reasoning from audit eligibility; sampled and unsampled direct/escalated stops verified centrally.'),
        limits='Stored proposals only. Replays are not new quality observations; audit fixtures do not establish detection probability. Adapter probe does not qualify live concurrency, taxonomy mappings, security, context refresh or economics.')
    destination.mkdir(parents=True, exist_ok=False)
    for name,value in (('verification.json',receipt),('worker-replay.json',replay),('adapter-probe.json',adapter)):
        (destination/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    (destination/'suite.txt').write_text(raw_log,encoding='utf-8')
    print(json.dumps(dict(receipt=str(destination),passed=receipt['suite']['passed'],
        replayed_calls=replay['replayed_calls'],native_calls=0,
        preserved_native_receipts=sum(v['native_receipts'] for v in prior.values())),indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--suite-log',type=Path,required=True)
    args=parser.parse_args()
    collect(args.destination,args.suite_log)
