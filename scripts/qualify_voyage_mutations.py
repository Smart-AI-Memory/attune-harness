"""Remove four specific guards in disposable copies and test observable failures."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('scope', 'voyage_sources.py', "passage['repo_id'] in scope['repo_ids']", 'True',
     'test_repository_and_path_filters_apply_before_rerank'),
    ('source_hash', 'voyage_index.py', "if manifest != metadata['manifest']:", 'if False:',
     'test_same_length_source_change_invalidates_generation'),
    ('replay', 'voyage_provider.py', "if record['status'] == 'completed':", 'if False:',
     'test_completed_embedding_reused_after_local_failure'),
    ('budget', 'voyage_provider.py', "if len(self.ledger['stages']) + 1 + reserve_calls > self.cfg['max_provider_calls']:", 'if False:',
     'test_provider_selection_explicit_and_budgeted'),
]


def main(output):
    output.mkdir(exist_ok=False)
    receipts = []
    for name, file, before, after, test in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='voyage-mutation-') as scratch:
            source = Path(scratch) / 'attune_harness'
            shutil.copytree(ROOT / 'src/attune_harness', source, ignore=shutil.ignore_patterns('__pycache__'))
            target = source / file
            original = target.read_text()
            if original.count(before) != 1:
                raise ValueError('Mutation no longer matches exactly once: ' + name)
            target.write_text(original.replace(before, after))
            environment = {**os.environ, 'PYTHONPATH': scratch}
            result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-o', 'pythonpath=', '--tb=short',
                                     str(ROOT / 'tests/test_voyage.py') + '::' + test],
                                    cwd=scratch, env=environment, capture_output=True, text=True, timeout=60)
            (output / (name + '.txt')).write_text(result.stdout + result.stderr)
            receipts.append({'guard': name, 'test': test, 'exit': result.returncode,
                             'detected': result.returncode == 1 and '1 failed' in result.stdout})
    (output / 'mutations.json').write_text(json.dumps(receipts, indent=2) + '\n')
    print(json.dumps(receipts, indent=2))
    return 0 if all(r['detected'] for r in receipts) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(main(parser.parse_args().output.absolute()))
