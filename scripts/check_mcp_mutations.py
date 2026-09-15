"""Run new CLI regression pins with routing guards removed in disposable copies."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
results = []
for command, test in (
    ('mcp-serve', 'test_cli_missing_mcp_keeps_stdout_clean'),
    ('mcp-inspect', 'test_cli_inspection_does_not_reexecute_running_record'),
):
    with tempfile.TemporaryDirectory(prefix='harness-mcp-mutation-') as directory:
        scratch = Path(directory)
        for source in ('src', 'tests', 'examples/extensions/plugin'):
            shutil.copytree(root / source, scratch / source, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(root / 'pyproject.toml', scratch / 'pyproject.toml')
        path = scratch / 'src/attune_harness/cli.py'
        original = path.read_text(encoding='utf-8')
        guard = f"if args.command == '{command}':"
        assert original.count(guard) == 1
        path.write_text(original.replace(guard, 'if False:'), encoding='utf-8')
        run = subprocess.run([sys.executable, '-m', 'pytest', f'tests/test_mcp.py::{test}', '-q'],
                             cwd=scratch, text=True, capture_output=True, timeout=30)
        (root / f'docs/receipts/mcp-mutation-{command}.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        assert run.returncode == 1 and '1 failed' in run.stdout, (run.stdout, run.stderr)
        results.append({'guard': command, 'test': test, 'failed_with_guard_removed': True})
receipt = {'failed': len(results), 'tested': len(results), 'mutations': results,
           'scope': 'New tests on existing CLI; new MCP module is excluded'}
(root / 'docs/receipts/mcp-mutations.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('2/2 new CLI tests failed with dispatch guards removed')
