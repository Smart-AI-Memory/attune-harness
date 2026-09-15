"""Installed deterministic two-way transfer example; no provider invocation."""

import argparse
import json
from pathlib import Path

from attune_harness.review import review
from attune_harness.recovery import resume_review, transfer_lead

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-dir', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
request, config = root / 'request.json', root / 'participants.json'
registry = json.loads(config.read_text(encoding='utf-8'))
assert all(item['adapter'] == 'deterministic' for item in registry['participants'].values())
first = review(request, config, args.run_dir, max_operations=4)
assert first['status'] == 'paused', first.get('error')
moved = transfer_lead(args.run_dir, first['checkpoint_digest'], 'sample-alternate', 'Continue the same accepted review')
middle = resume_review(args.run_dir, request, config, moved['checkpoint_digest'], max_operations=2)
assert middle['status'] == 'paused', middle.get('error')
returned = transfer_lead(args.run_dir, middle['checkpoint_digest'], 'sample-lead', 'Return the local lead assignment')
final = resume_review(args.run_dir, request, config, returned['checkpoint_digest'])
assert final['status'] == 'completed', final.get('error')
assert final['accepted'] == first['accepted']
assert final['requirement_revision'] == first['requirement_revision']
print(json.dumps({'status': final['status'], 'document_outcome': final['document_outcome'],
                  'transfers': [{'from': item['from'], 'to': item['to']} for item in final['recovery']['transfers']],
                  'events': len(final['events']), 'record_path': final['record_path'], 'provider_calls': 0}, indent=2))
