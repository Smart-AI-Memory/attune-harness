"""Check new tests on changed existing paths against disposable source mutations."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
mutations = [
    ('review_tool_dispatch', 'review.py',
     'operation = lambda: invoke_tool(bindings, name, arguments, retrieve)',
     "operation = lambda: retrieve(arguments['query'], arguments['k'])",
     'test_real_review_binds_skill_and_artifact'),
    ('post_turn_lifecycle_check', 'review.py',
     "                stable_inputs()\n                extension_catalog()\n                action = response['action']",
     "                stable_inputs()\n                action = response['action']",
     'test_disable_during_participant_turn_stops_before_tool'),
    ('extension_recovery_profile', 'recovery.py', 'profile != expected', 'False',
     'test_extension_profile_marker_is_required_on_resume'),
    ('deterministic_tool_arguments', 'review_participants.py',
     "name == 'retrieve' or\n                    turn.get('tool_contracts', {}).get(name, {}).get('binding') == 'retrieve'",
     "name == 'retrieve'", 'test_real_review_binds_skill_and_artifact'),
    ('native_tool_protocol', 'review_participants.py', "turn.get('protocol', PROTOCOL)", 'PROTOCOL',
     'test_native_extension_protocol_is_carried_in_outer_contract'),
    ('final_lifecycle_check', 'review.py',
     "        extension_catalog()\n        if any(event['state'] != 'completed'", "        if any(event['state'] != 'completed'",
     'test_disabled_after_final_verification_is_not_completed'),
    ('extension_cli_dispatch', 'cli.py', "if args.command == 'extension':", 'if False:',
     'test_cli_lifecycle_routing'),
]
for name, test in (
    ('process_exit_race', 'test_exit_race_reaps_then_rechecks_group_without_losing_output'),
    ('process_living_denial_negative_pin', 'test_cleanup_denial_for_live_parent_is_bounded_and_propagated'),
    ('process_second_denial', 'test_second_group_denial_is_not_success_after_parent_exit'),
    ('process_descendant_cleanup', 'test_exit_race_still_stops_descendant_effect'),
):
    mutations.append((name, 'process.py', 'except PermissionError as error:\n            if attempt:',
                      'except PermissionError as error:\n            raise\n            if attempt:', test))
results = []
for name, filename, old, new, test in mutations:
    with tempfile.TemporaryDirectory(prefix='harness-extension-mutation-') as scratch:
        tmp = Path(scratch)
        shutil.copytree(root / 'src', tmp / 'src')
        shutil.copytree(root / 'tests', tmp / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(root / 'examples/extensions/plugin', tmp / 'examples/extensions/plugin')
        shutil.copyfile(root / 'pyproject.toml', tmp / 'pyproject.toml')
        path = tmp / 'src/attune_harness' / filename
        source = path.read_text(encoding='utf-8')
        assert source.count(old) == 1, name
        path.write_text(source.replace(old, new), encoding='utf-8')
        test_file = 'test_process.py' if filename == 'process.py' else 'test_extensions.py'
        completed = subprocess.run([sys.executable, '-m', 'pytest', f'tests/{test_file}::{test}', '-q'],
                                   cwd=tmp, capture_output=True, text=True, timeout=30)
        (root / f'docs/receipts/extensions-mutation-{name}.txt').write_text(completed.stdout + completed.stderr, encoding='utf-8')
        failed = name != 'process_living_denial_negative_pin'
        assert completed.returncode == int(failed), (name, completed.stdout, completed.stderr)
        assert ('1 failed' if failed else '1 passed') in completed.stdout, completed.stdout
        results.append({'guard': name, 'test': test, 'failed_with_guard_removed': failed})
receipt = {'failed': sum(r['failed_with_guard_removed'] for r in results), 'tested': len(results), 'mutations': results,
           'scope': 'New tests on changed existing paths; new extension modules are excluded'}
(root / 'docs/receipts/extensions-mutations.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(f"{receipt['failed']}/{receipt['tested']} mutation tests failed with guards removed; live-denial negative pin passed")
