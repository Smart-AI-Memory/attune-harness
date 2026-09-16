"""Plan or run one explicitly authorized installed-library Voyage smoke test."""

import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

from attune_harness.retrieval_task import task_template
from attune_harness.voyage_index import build_index, index_plan, write_json
from attune_harness.voyage_sources import load_config

QUERY = 'Which function rejects GitHub check results that belong to a different commit revision?'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-provider', action='store_true')
    args = parser.parse_args()
    cfg = load_config(args.config)
    plan = index_plan(cfg)
    if not args.allow_provider:
        print(json.dumps({'index_plan': plan, 'query': QUERY, 'searches': 1,
                          'additional_provider_calls': 2, 'status': 'planned_no_uploads'}, indent=2))
        return 0
    args.output.mkdir(exist_ok=False)
    write_json(args.output / 'plan.json', plan)
    receipt = {'schema_version': 1, 'kind': 'live-voyage-smoke', 'status': 'running',
               'package': importlib.metadata.version('attune-harness'), 'query': QUERY,
               'qualification_scope': 'Live provider compatibility and original source evidence; not general coding quality'}
    write_json(args.output / 'receipt.json', receipt)
    try:
        index = build_index(cfg, allow_provider=True)
        write_json(args.output / 'index.json', index)
        task = task_template(cfg, index['generation'], 'Locate source that enforces GitHub check revision identity', max_calls=1)
        task['accepted'] = True  # --allow-provider explicitly authorized this fixed smoke operation.
        request = args.output / 'request.json'
        write_json(request, task)
        command = [sys.executable, '-I', '-c', 'from attune_harness.cli import main; raise SystemExit(main())', 'retrieve', QUERY,
                   '--request', str(request.absolute()), '--session-dir', str((args.output / 'session').absolute()),
                   '--k', '5', '--allow-provider']
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180, cwd=args.output)
        (args.output / 'cli-stdout.json').write_text(completed.stdout, encoding='utf-8')
        (args.output / 'cli-stderr.txt').write_text(completed.stderr, encoding='utf-8')
        result = json.loads(completed.stdout)
        useful = any(p['path'] == 'src/attune_harness/github_checks.py' and
                     'different revision' in p['excerpt'] for p in result.get('sources', []))
        receipt.update(status='passed' if completed.returncode == 0 and useful else 'failed',
                       cli_exit=completed.returncode, expected_evidence_found=useful,
                       retrieval_usage=result.get('usage'), generation=index['generation'])
    except Exception as exc:
        receipt.update(status='failed', error={'type': type(exc).__name__, 'detail': str(exc)})
    write_json(args.output / 'receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
