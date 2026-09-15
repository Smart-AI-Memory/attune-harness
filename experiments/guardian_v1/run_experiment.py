"""Freeze and exercise the disposable Guardian through independent CLI processes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
GUARDIAN = HERE / 'guardian.py'
CLIENT = HERE / 'host_client.py'
OUT = None
CORRECT = 'def increment(value):\n    return value + 1\n'
BUGGY = 'def increment(value):\n    return value + 2\n'


def saved_json(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8'))


class GuardianCases(unittest.TestCase):
    def setUp(self):
        self.root = OUT / self._testMethodName
        self.commands = []

    def tearDown(self):
        saved_json(OUT / (self._testMethodName + '-commands.json'), self.commands)

    def command(self, command, *args, expected=0):
        argv = [sys.executable, '-I', str(GUARDIAN), command, str(self.root), *map(str, args)]
        started = time.monotonic()
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=35, cwd=OUT)
        self.commands.append({'argv': argv, 'exit_code': completed.returncode,
                              'stdout': completed.stdout, 'stderr': completed.stderr,
                              'elapsed_seconds': time.monotonic()-started})
        self.assertEqual(completed.returncode, expected, completed.stderr)
        return json.loads(completed.stdout) if completed.stdout else None

    def setup_incident(self, *init_args):
        self.command('init', *init_args)
        return self.command('observe')

    def row(self, view=None):
        view = view or self.command('inspect')
        self.assertEqual(view['integrity'], 'ok')
        self.assertEqual(len(view['work']), 1)
        return view['work'][0]

    def effects(self):
        return list((self.root / 'jobs').glob('*/*/effect.json'))

    def operation(self):
        row = self.row()
        return self.root / 'jobs' / row['id'] / row['operation_id']

    def concurrent(self, count, command, *args):
        # Threads only launch and collect distinct OS processes; SQLite is shared by those processes.
        with ThreadPoolExecutor(max_workers=count) as pool:
            results = list(pool.map(lambda _: self.command(command, *args), range(count)))
        return results

    def test_01_repair_and_separate_host(self):
        self.setup_incident()
        view = self.command('tick')
        row = self.row(view)
        self.assertEqual(row['check_result']['failed'], 4)
        self.assertEqual(row['verification']['passed'], 4)
        self.assertEqual(row['state'], 'verified')
        self.assertEqual(view['budget'], {'cap': 1, 'used': 1})
        self.assertEqual(len(self.effects()), 1)
        process = subprocess.run([sys.executable, '-I', str(CLIENT), str(self.root)],
                                 capture_output=True, text=True, timeout=20, cwd=OUT)
        self.commands.append({'argv': [sys.executable, '-I', str(CLIENT), str(self.root)],
                              'exit_code': process.returncode, 'stdout': process.stdout,
                              'stderr': process.stderr})
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result['client'], 'separate-cli-fixture')
        self.assertEqual(result['work'][0]['acceptance'], 'verified_fixture_repair')

    def test_02_healthy_input_needs_no_worker(self):
        self.setup_incident('--correct')
        view = self.command('tick')
        self.assertEqual(self.row(view)['state'], 'healthy')
        self.assertEqual(view['budget']['used'], 0)
        self.assertEqual(self.effects(), [])

    def test_03_duplicate_and_related_deliveries(self):
        self.setup_incident()
        self.command('observe')
        self.command('observe', '--delivery', 'different-event-same-incident')
        self.command('tick')
        self.command('tick')
        view = self.command('inspect')
        self.assertEqual(self.row(view)['state'], 'verified')
        self.assertEqual(len(view['deliveries']), 2)
        self.assertEqual(len(self.effects()), 1)

    def test_04_concurrent_admission(self):
        self.command('init')
        self.concurrent(12, 'observe')
        view = self.command('inspect')
        self.assertEqual(self.row(view)['state'], 'queued')
        self.assertEqual(len(view['deliveries']), 1)
        self.command('tick')
        self.assertEqual(len(self.effects()), 1)

    def test_05_concurrent_ticks(self):
        self.setup_incident()
        self.concurrent(8, 'tick')
        view = self.command('inspect')
        self.assertEqual(self.row(view)['state'], 'verified')
        self.assertEqual(view['budget']['used'], 1)
        self.assertEqual(len(self.effects()), 1)
        self.assertEqual(sum(x['kind'] == 'dispatching' for x in view['timeline']), 1)

    def test_06_crash_before_dispatch(self):
        self.setup_incident()
        self.command('tick', '--fault', 'before-dispatch', expected=77)
        before = self.command('inspect')
        self.assertEqual(self.row(before)['state'], 'ready')
        self.assertEqual(before['budget']['used'], 0)
        after = self.command('recover')
        self.assertEqual(self.row(after)['state'], 'verified')
        self.assertEqual(len(self.effects()), 1)

    def test_07_crash_after_intent(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-intent', expected=77)
        self.assertEqual(self.row()['state'], 'dispatching')
        for _ in range(3):
            view = self.command('recover')
            self.assertEqual(self.row(view)['state'], 'unresolved')
            self.assertEqual(view['budget']['used'], 1)
        self.assertEqual(self.effects(), [])
        self.assertIsNone(self.row()['verification'])

    def test_08_crash_after_effect(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        self.assertEqual(self.row()['state'], 'dispatching')
        self.assertEqual(len(self.effects()), 1)
        self.assertEqual(self.row(self.command('recover'))['state'], 'verified')
        self.assertEqual(len(self.effects()), 1)

    def test_09_crash_after_acknowledgement(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-acknowledgement', expected=77)
        self.assertEqual(self.row()['state'], 'returned')
        self.assertEqual(self.row(self.command('recover'))['state'], 'verified')
        self.assertEqual(len(self.effects()), 1)

    def test_10_input_changes_before_dispatch(self):
        self.setup_incident()
        (self.root / 'workspace/source.py').write_bytes(CORRECT.encode('utf-8'))
        self.assertEqual(self.row(self.command('tick'))['state'], 'stale')
        self.assertEqual(self.effects(), [])

    def test_11_input_changes_after_effect(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        (self.root / 'workspace/source.py').write_bytes(CORRECT.encode('utf-8'))
        view = self.command('recover')
        row = self.row(view)
        self.assertEqual(row['state'], 'stale')
        self.assertIsNotNone(row['worker_result'])
        self.assertIsNone(row['verification'])
        self.assertEqual(len(self.effects()), 1)

    def test_12a_wrong_completion_identity(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        path = self.operation() / 'completion.json'
        receipt = json.loads(path.read_text())
        receipt['operation_id'] = 'wrong-operation'
        saved_json(path, receipt)
        self.assertEqual(self.row(self.command('recover'))['state'], 'unresolved')
        self.assertEqual(len(self.effects()), 1)

    def test_12b_malformed_completion(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        (self.operation() / 'completion.json').write_text('{broken')
        self.assertEqual(self.row(self.command('recover'))['state'], 'unresolved')
        self.assertEqual(len(self.effects()), 1)

    def test_13_false_worker_success_is_rejected(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        operation = self.operation()
        (operation / 'candidate.py').write_bytes(BUGGY.encode('utf-8'))
        path = operation / 'completion.json'
        receipt = json.loads(path.read_text())
        receipt['candidate_sha'] = hashlib.sha256((operation / 'candidate.py').read_bytes()).hexdigest()
        saved_json(path, receipt)
        row = self.row(self.command('recover'))
        self.assertEqual(row['worker_result']['claimed_status'], 'completed')
        self.assertEqual(row['state'], 'rejected')
        self.assertEqual(row['verification']['failed'], 4)

    def test_14a_candidate_tampered_after_ack(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-acknowledgement', expected=77)
        (self.operation() / 'candidate.py').write_bytes(BUGGY.encode('utf-8'))
        self.assertEqual(self.row(self.command('recover'))['state'], 'rejected')
        self.assertEqual(len(self.effects()), 1)

    def test_14b_oracle_snapshot_tampered(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        row = self.row()
        (self.root / 'jobs' / row['id'] / 'expected.json').write_text('[]')
        self.assertEqual(self.row(self.command('recover'))['state'], 'stale')
        self.assertIsNone(self.row()['verification'])

    def test_15_exhausted_budget(self):
        self.setup_incident('--budget', '0')
        view = self.command('tick')
        self.assertEqual(self.row(view)['state'], 'blocked')
        self.assertEqual(view['budget']['used'], 0)
        self.assertEqual(self.effects(), [])

    def test_16_conflicting_delivery_identity(self):
        self.setup_incident()
        (self.root / 'workspace/source.py').write_bytes(CORRECT.encode('utf-8'))
        self.command('observe', expected=2)
        view = self.command('inspect')
        self.assertEqual(len(view['deliveries']), 1)
        self.assertEqual(len(view['work']), 1)
        self.assertEqual(self.effects(), [])

    def test_17_repeated_recovery_and_inspection(self):
        self.setup_incident()
        self.command('tick', '--fault', 'after-effect', expected=77)
        first = self.command('recover')
        for _ in range(3):
            self.assertEqual(self.command('recover'), first)
            self.assertEqual(self.command('inspect'), first)
        self.assertEqual(len(self.effects()), 1)

    def test_18_path_with_spaces_and_unicode(self):
        self.root = self.root / 'workspace with spaces caf\u00e9'
        self.setup_incident()
        source = (self.root / 'workspace/source.py').read_bytes()
        self.assertEqual(source, BUGGY.encode('utf-8'))
        self.assertNotIn(b'\r', source)
        view = self.command('tick')
        self.assertEqual(self.row(view)['state'], 'verified')
        self.assertEqual(len(self.effects()), 1)


class RecordingResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.started = time.monotonic()

    def addSuccess(self, test):
        super().addSuccess(test)
        records.append({'case': test._testMethodName, 'result': 'passed',
                        'elapsed_seconds': time.monotonic()-self.started})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        records.append({'case': test._testMethodName, 'result': 'failed',
                        'traceback': self._exc_info_to_string(error, test)})

    def addError(self, test, error):
        super().addError(test, error)
        records.append({'case': test._testMethodName, 'result': 'error',
                        'traceback': self._exc_info_to_string(error, test)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    OUT = args.out.absolute()
    OUT.mkdir(parents=True, exist_ok=False)
    sources = {name: (HERE / name).read_bytes()
               for name in ('DESIGN.md', 'guardian.py', 'host_client.py', 'run_experiment.py')}
    files = {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}
    (OUT / 'source').mkdir()
    for name, data in sources.items():
        (OUT / 'source' / name).write_bytes(data)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardianCases)
    protocol = {'schema': 'guardian-experiment/1', 'source_directory': str(HERE),
                'files': files, 'created_at': datetime.now(timezone.utc).isoformat(),
                'cases': [test._testMethodName for test in suite],
                'acceptance': 'Every frozen behavioral case passes; zero false verified results or duplicate fixture effects.',
                'scope': 'built-in deterministic fixture; no model, service, network or authenticated host qualification'}
    saved_json(OUT / 'freeze.json', protocol)
    records = []
    stream = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult).run(suite)
    (OUT / 'test-output.txt').write_bytes(stream.getvalue().encode('utf-8'))
    saved_json(OUT / 'results.json', records)
    unchanged = all(hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected
                    for name, expected in files.items())
    summary = {'tests': result.testsRun, 'passed': len(result.successes) if hasattr(result, 'successes')
               else result.testsRun-len(result.failures)-len(result.errors),
               'failures': len(result.failures), 'errors': len(result.errors),
               'elapsed_seconds': time.monotonic()-started, 'freeze_matches': unchanged,
               'platform': platform.platform(), 'python': sys.version, 'sqlite': sqlite3.sqlite_version,
               'disposition': 'local cases pass' if result.wasSuccessful() and unchanged else 'revise',
               'native_windows': 'run' if platform.system() == 'Windows' else 'unrun',
               'native_linux': 'run' if platform.system() == 'Linux' else 'unrun'}
    saved_json(OUT / 'summary.json', summary)
    print(stream.getvalue())
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
