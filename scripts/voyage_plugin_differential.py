"""Record an offline Voyage journal differential without invoking a provider.

This records stage semantics for a supplied pair of already completed or
interrupted host journals. It does not make a live comparison or qualify R6.
"""

import argparse
import json
from pathlib import Path
import re

from attune_harness.review_contract import digest
from attune_harness.review_store import read_record


def stages(directory: Path):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Voyage stage directory must be a real directory')
    ledger = read_record(directory)
    if (ledger.get('schema_version') != 1 or
            ledger.get('recovery') != {'profile': 'voyage-stage-ledger-v1'} or
            not isinstance(ledger.get('config_digest'), str) or
            not re.fullmatch('[a-f0-9]{64}', ledger['config_digest'])):
        raise ValueError('Unsupported Voyage stage ledger')
    ids = ledger.get('stages')
    if not isinstance(ids, list) or not 1 <= len(ids) <= 10_000 or len(set(map(str, ids))) != len(ids):
        raise ValueError('Voyage stage list is empty, duplicated or oversized')
    rows = []
    for stage_id in ids:
        if not isinstance(stage_id, str) or not re.fullmatch('[a-f0-9]{64}', stage_id):
            raise ValueError('Invalid Voyage stage path identity')
        stage_dir = directory / stage_id
        if stage_dir.is_symlink() or not stage_dir.is_dir():
            raise ValueError('Voyage stage path must be a real directory')
        record = read_record(stage_dir)
        if (record.get('schema_version') != 1 or
                record.get('recovery') != {'profile': 'voyage-paid-stage-v1'} or
                record.get('request_digest') != stage_id or
                record.get('kind') not in ('embed', 'rerank') or
                record.get('status') not in ('prepared', 'dispatching', 'completed', 'unresolved')):
            raise ValueError('Voyage stage identity changed')
        row = {'stage_id': stage_id, 'kind': record['kind'], 'status': record['status']}
        if record['status'] == 'completed':
            result = record['result']
            receipt = record['receipt']
            if not isinstance(result, dict) or not isinstance(receipt, dict):
                raise ValueError('Voyage completed stage needs result and receipt objects')
            tokens = result.get('total_tokens')
            if tokens is not None and (type(tokens) is not int or tokens < 0):
                raise ValueError('Voyage completed stage has invalid token usage')
            rates = receipt.get('rate_snapshot')
            if not isinstance(rates, dict):
                raise ValueError('Voyage completed stage needs its rate snapshot')
            rate = rates.get('embedding_per_million' if record['kind'] == 'embed' else 'rerank_per_million')
            if type(rate) not in (int, float) or not 0 <= rate < 1000:
                raise ValueError('Voyage completed stage has invalid rate')
            cost = None if tokens is None else tokens * rate / 1_000_000
            if (receipt.get('stage_id') != stage_id or receipt.get('kind') != record['kind'] or
                    receipt.get('replayed') is not False or
                    receipt.get('total_tokens') != tokens or receipt.get('new_tokens') != tokens or
                    receipt.get('usage_status') != ('unknown' if tokens is None else 'provider_reported') or
                    receipt.get('new_cost_usd') != cost):
                raise ValueError('Voyage completed stage receipt disagrees with its result')
            row.update(result_digest=digest(result), total_tokens=receipt['total_tokens'],
                       new_tokens=receipt['new_tokens'], usage_status=receipt['usage_status'],
                       rate_snapshot=rates, new_cost_usd=receipt['new_cost_usd'],
                       replayed=receipt['replayed'])
        rows.append(row)
    return rows


def compare(inprocess: Path, selected: Path, *, identical_responses=False):
    """Compare host-owned state; demand result equality only for recorded fixtures."""
    left, right = stages(inprocess), stages(selected)
    if len(left) != len(right):
        raise ValueError('Voyage stage counts differ')
    for number, (a, b) in enumerate(zip(left, right), 1):
        if (a['kind'], a['status']) != (b['kind'], b['status']):
            raise ValueError(f'Voyage stage {number} kind/status differs')
        # A live rerank may have different candidate documents after separate
        # embeddings. Identity equality is meaningful only for equal requests;
        # the digest alone cannot prove that two unequal requests were intended
        # to be equal. Recorded synthetic fixtures must be exactly identical.
        if identical_responses and a != b:
            raise ValueError(f'Recorded Voyage stage {number} differs')
    return {'schema_version': 1, 'status': 'synthetic_offline_compared' if identical_responses
            else 'offline_structure_compared', 'live_qualified': False,
            'inprocess': left, 'selected': right,
            'identical_recorded_responses': identical_responses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inprocess', required=True, type=Path)
    parser.add_argument('--selected', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--identical-recorded-responses', action='store_true')
    args = parser.parse_args()
    report = compare(args.inprocess, args.selected,
                     identical_responses=args.identical_recorded_responses)
    args.output.mkdir()  # Exclusive evidence: never overwrite a prior comparison.
    (args.output / 'comparison.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n',
                                                  encoding='utf-8')
    print(json.dumps({'status': report['status'], 'live_qualified': False,
                      'stage_count': len(report['selected'])}))


if __name__ == '__main__':
    main()
