"""Disposable Guardian experiment. Only the two built-in source fixtures may run."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys

SELF = Path(__file__).resolve()
BUGGY = 'def increment(value):\n    return value + 2\n'
CORRECT = 'def increment(value):\n    return value + 1\n'
EXPECTED = [[-1, 0], [0, 1], [1, 2], [100, 101]]
TERMINAL = {'healthy', 'verified', 'rejected', 'stale', 'blocked'}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(encode(value).encode())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    with temporary.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(encode(value) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_once(path, data):
    try:
        with path.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        require(path.read_bytes() == data, 'Existing snapshot differs: ' + str(path))


@contextmanager
def connect(root):
    require((root / 'ledger.sqlite').is_file(), 'Initialize a new experiment directory first')
    db = sqlite3.connect(str(root / 'ledger.sqlite'), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def history(db, work_id, kind, data):
    db.execute('INSERT INTO history(work_id,kind,data) VALUES (?,?,?)',
               (work_id, kind, encode(data)))


def initialize(root, correct=False, budget=1):
    require(type(budget) is int and budget >= 0, 'Budget must be a nonnegative integer')
    root.mkdir(parents=True, exist_ok=False)
    (root / 'workspace').mkdir()
    (root / 'jobs').mkdir()
    (root / 'workspace' / 'source.py').write_bytes((CORRECT if correct else BUGGY).encode('utf-8'))
    (root / 'workspace' / 'expected.json').write_bytes(encode(EXPECTED).encode('utf-8'))
    db = sqlite3.connect(str(root / 'ledger.sqlite'))
    db.execute('PRAGMA journal_mode=DELETE')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
        CREATE TABLE budget(id INTEGER PRIMARY KEY CHECK(id=1), cap INTEGER, used INTEGER);
        CREATE TABLE work(
            id TEXT PRIMARY KEY, contract TEXT NOT NULL, state TEXT NOT NULL,
            operation_id TEXT, request_digest TEXT, check_result TEXT,
            worker_result TEXT, verification TEXT, diagnostic TEXT NOT NULL DEFAULT '');
        CREATE TABLE deliveries(id TEXT PRIMARY KEY, revision TEXT NOT NULL,
            work_id TEXT NOT NULL REFERENCES work(id));
        CREATE TABLE history(seq INTEGER PRIMARY KEY, work_id TEXT NOT NULL,
            kind TEXT NOT NULL, data TEXT NOT NULL);
    ''')
    db.execute('INSERT INTO budget VALUES (1,?,0)', (budget,))
    db.commit()
    db.close()
    return inspect(root)


def current_contract(root):
    source = (root / 'workspace' / 'source.py').read_bytes()
    expected = (root / 'workspace' / 'expected.json').read_bytes()
    require(source.decode() in (BUGGY, CORRECT), 'Only built-in arithmetic fixtures are accepted')
    require(json.loads(expected) == EXPECTED, 'Only the fixed external oracle is accepted')
    contract = {'schema': 'guardian-fixture/1', 'recipe': 'increment-repair/1',
                'source_sha': sha(source), 'oracle_sha': sha(expected),
                'runtime_sha': sha(SELF.read_bytes()), 'check': 'increment-regression/v1'}
    return contract, source, expected


def observe(root, delivery):
    require(isinstance(delivery, str) and 0 < len(delivery) <= 100, 'Invalid delivery identity')
    contract, source, expected = current_contract(root)
    work_id = digest(contract)
    folder = root / 'jobs' / work_id
    with connect(root) as db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT * FROM deliveries WHERE id=?', (delivery,)).fetchone()
        if old:
            require(old['revision'] == work_id, 'Delivery identity reused with different input')
        else:
            folder.mkdir(exist_ok=True)
            write_once(folder / 'source.py', source)
            write_once(folder / 'expected.json', expected)
            inserted = db.execute('INSERT OR IGNORE INTO work(id,contract,state) VALUES (?,?,?)',
                                  (work_id, encode(contract), 'queued')).rowcount
            db.execute('INSERT INTO deliveries VALUES (?,?,?)', (delivery, work_id, work_id))
            history(db, work_id, 'admitted' if inserted else 'coalesced', {'delivery': delivery})
    return inspect(root)


def get_work(root, work_id):
    with connect(root) as db:
        row = db.execute('SELECT * FROM work WHERE id=?', (work_id,)).fetchone()
    require(row is not None, 'Unknown work identity')
    return dict(row)


def set_state(root, work_id, expected_states, state, diagnostic='', **values):
    require(set(values) <= {'check_result', 'worker_result', 'verification'}, 'Invalid update fields')
    with connect(root) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT state FROM work WHERE id=?', (work_id,)).fetchone()
        if row is None or row['state'] not in expected_states:
            return False
        columns = ['state=?', 'diagnostic=?'] + [name + '=?' for name in values]
        args = [state, diagnostic] + [encode(value) for value in values.values()] + [work_id]
        db.execute('UPDATE work SET ' + ','.join(columns) + ' WHERE id=?', args)
        history(db, work_id, state, {'diagnostic': diagnostic, **values})
    return True


def check_inputs(root, row):
    contract = json.loads(row['contract'])
    current, _, _ = current_contract(root)
    require(current == contract, 'Accepted input or runtime changed')
    require(digest(contract) == row['id'], 'Work contract identity changed')
    folder = root / 'jobs' / row['id']
    require(sha((folder / 'source.py').read_bytes()) == contract['source_sha'], 'Source snapshot changed')
    require(sha((folder / 'expected.json').read_bytes()) == contract['oracle_sha'], 'Oracle snapshot changed')
    return folder


def run_check(source, expected):
    payload = {'source': source.decode(), 'expected': json.loads(expected)}
    child = subprocess.run([sys.executable, '-I', str(SELF), '_check'], input=encode(payload),
                           text=True, capture_output=True, timeout=5)
    require(child.returncode == 0, 'Check process failed: ' + child.stderr)
    result = json.loads(child.stdout)
    require(set(result) == {'schema', 'passed', 'failed', 'cases'}, 'Malformed check report')
    require(result['schema'] == 'fixture-check/1' and result['cases'] == 4, 'Incomplete check report')
    require(type(result['passed']) is int and type(result['failed']) is int and
            result['passed'] >= 0 and result['failed'] >= 0 and
            result['passed'] + result['failed'] == 4, 'Invalid check totals')
    return result


def check_process():
    payload = json.loads(sys.stdin.read())
    require(payload['source'] in (BUGGY, CORRECT), 'Unrecognized fixture source')
    require(payload['expected'] == EXPECTED, 'Unrecognized oracle')
    namespace = {}
    exec(compile(payload['source'], 'accepted-fixture.py', 'exec'), namespace)
    passed = sum(namespace['increment'](value) == expected for value, expected in EXPECTED)
    return {'schema': 'fixture-check/1', 'passed': passed, 'failed': 4-passed, 'cases': 4}


def crash(point, selected):
    if point == selected:
        os._exit(77)


def fixture_worker(root, work_id):
    row = get_work(root, work_id)
    require(row['state'] == 'dispatching', 'Worker needs a persisted dispatch intent')
    folder = check_inputs(root, row)
    operation = folder / row['operation_id']
    operation.mkdir(exist_ok=True)
    # One fixture effect can be attempted per operation. An incomplete claim is not replayable.
    with (operation / 'claim').open('x') as handle:
        handle.write(row['request_digest'])
        handle.flush()
        os.fsync(handle.fileno())
    candidate = CORRECT.encode()
    write_once(operation / 'candidate.py', candidate)
    with (operation / 'effect.json').open('x') as handle:
        handle.write(encode({'operation_id': row['operation_id'], 'work_id': work_id}))
        handle.flush()
        os.fsync(handle.fileno())
    receipt = {'schema': 'fixture-completion/1', 'work_id': work_id,
               'operation_id': row['operation_id'], 'request_digest': row['request_digest'],
               'candidate_sha': sha(candidate), 'claimed_status': 'completed'}
    atomic_json(operation / 'completion.json', receipt)
    return receipt


def completion(root, row):
    folder = root / 'jobs' / row['id'] / row['operation_id']
    receipt = json.loads((folder / 'completion.json').read_text())
    require(set(receipt) == {'schema', 'work_id', 'operation_id', 'request_digest',
                             'candidate_sha', 'claimed_status'}, 'Malformed completion journal')
    require(receipt['schema'] == 'fixture-completion/1' and receipt['work_id'] == row['id'] and
            receipt['operation_id'] == row['operation_id'] and
            receipt['request_digest'] == row['request_digest'], 'Completion identity mismatch')
    require((folder / 'claim').read_text() == row['request_digest'], 'Worker claim mismatch')
    require(json.loads((folder / 'effect.json').read_text()) ==
            {'operation_id': row['operation_id'], 'work_id': row['id']}, 'Effect identity mismatch')
    require(sha((folder / 'candidate.py').read_bytes()) == receipt['candidate_sha'], 'Candidate changed')
    return receipt, folder / 'candidate.py'


def verify(root, work_id):
    row = get_work(root, work_id)
    if row['state'] != 'returned':
        return
    try:
        folder = check_inputs(root, row)
    except (ValueError, OSError) as exc:
        set_state(root, work_id, {'returned'}, 'stale', str(exc))
        return
    try:
        receipt, candidate = completion(root, row)
        require(receipt == json.loads(row['worker_result']), 'Acknowledged receipt changed')
        result = run_check(candidate.read_bytes(), (folder / 'expected.json').read_bytes())
        set_state(root, work_id, {'returned'}, 'verified' if result['failed'] == 0 else 'rejected',
                  verification=result)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        set_state(root, work_id, {'returned'}, 'rejected', str(exc))


def tick(root, fault=None):
    with connect(root) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT * FROM work WHERE state IN ('queued','ready') ORDER BY rowid LIMIT 1").fetchone()
        if row is None:
            return inspect(root)
        row = dict(row)
        if row['state'] == 'queued':
            db.execute("UPDATE work SET state='checking' WHERE id=?", (row['id'],))
            history(db, row['id'], 'checking', {})
    work_id = row['id']
    try:
        folder = check_inputs(root, row)
    except (ValueError, OSError) as exc:
        set_state(root, work_id, {'checking', 'ready'}, 'stale', str(exc))
        return inspect(root)
    if row['state'] == 'queued':
        try:
            result = run_check((folder / 'source.py').read_bytes(), (folder / 'expected.json').read_bytes())
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            set_state(root, work_id, {'checking'}, 'blocked', str(exc))
            return inspect(root)
        moved = set_state(root, work_id, {'checking'}, 'healthy' if result['failed'] == 0 else 'ready',
                          check_result=result)
        if not moved or result['failed'] == 0:
            return inspect(root)
    crash('before-dispatch', fault)
    operation_id = digest({'work_id': work_id, 'recipe': 'increment-repair/1', 'attempt': 1})
    request_digest = digest({'work_id': work_id, 'operation_id': operation_id, 'units': 1})
    with connect(root) as db:
        db.execute('BEGIN IMMEDIATE')
        latest = db.execute('SELECT state FROM work WHERE id=?', (work_id,)).fetchone()
        if latest['state'] != 'ready':
            return inspect(root)
        reserved = db.execute('UPDATE budget SET used=used+1 WHERE id=1 AND used+1<=cap').rowcount
        if not reserved:
            db.execute("UPDATE work SET state='blocked',diagnostic='Synthetic budget exhausted' WHERE id=?", (work_id,))
            history(db, work_id, 'blocked', {'reason': 'Synthetic budget exhausted'})
        else:
            db.execute("UPDATE work SET state='dispatching',operation_id=?,request_digest=? WHERE id=?",
                       (operation_id, request_digest, work_id))
            history(db, work_id, 'dispatching', {'operation_id': operation_id, 'units_reserved': 1})
    if not reserved:
        return inspect(root)
    crash('after-intent', fault)
    try:
        child = subprocess.run([sys.executable, '-I', str(SELF), '_worker', str(root), work_id],
                               text=True, capture_output=True, timeout=10)
        require(child.returncode == 0, 'Worker process failed: ' + child.stderr)
        crash('after-effect', fault)
        receipt, _ = completion(root, get_work(root, work_id))
        require(json.loads(child.stdout) == receipt, 'Acknowledgement differs from completion journal')
        set_state(root, work_id, {'dispatching'}, 'returned', worker_result=receipt)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        set_state(root, work_id, {'dispatching'}, 'unresolved', str(exc))
        return inspect(root)
    crash('after-acknowledgement', fault)
    verify(root, work_id)
    return inspect(root)


def recover(root):
    with connect(root) as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM work ORDER BY rowid')]
    for row in rows:
        work_id = row['id']
        if row['state'] == 'checking':
            # The built-in fixture check is read-only and can be repeated safely.
            set_state(root, work_id, {'checking'}, 'queued', 'Restarting a read-only fixture check')
        if row['state'] in ('dispatching', 'unresolved'):
            try:
                receipt, _ = completion(root, row)
                set_state(root, work_id, {'dispatching', 'unresolved'}, 'returned', worker_result=receipt)
            except (ValueError, OSError) as exc:
                set_state(root, work_id, {'dispatching', 'unresolved'}, 'unresolved',
                          'No reconcilable completion; worker was not replayed: ' + str(exc))
        verify(root, work_id)
    return tick(root)


def inspect(root):
    with connect(root) as db:
        budget = dict(db.execute('SELECT cap,used FROM budget WHERE id=1').fetchone())
        rows = [dict(row) for row in db.execute('SELECT * FROM work ORDER BY rowid')]
        events = [dict(row) for row in db.execute('SELECT * FROM deliveries ORDER BY id')]
        timeline = [dict(row) for row in db.execute('SELECT * FROM history ORDER BY seq')]
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    for row in rows:
        for key in ('contract', 'check_result', 'worker_result', 'verification'):
            row[key] = json.loads(row[key]) if row[key] else None
        row['acceptance'] = ('verified_fixture_repair' if row['state'] == 'verified' else
                             'verified_fixture_check' if row['state'] == 'healthy' else 'not_verified')
    for event in timeline:
        event['data'] = json.loads(event['data'])
    return {'schema': 'guardian-client/1', 'scope': 'disposable arithmetic fixture only',
            'platform': platform.system(), 'budget': budget, 'work': rows,
            'deliveries': events, 'timeline': timeline, 'integrity': integrity}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'observe', 'tick', 'recover', 'inspect', '_check', '_worker'))
    parser.add_argument('directory', nargs='?')
    parser.add_argument('work_id', nargs='?')
    parser.add_argument('--delivery', default='example-event-1')
    parser.add_argument('--correct', action='store_true')
    parser.add_argument('--budget', type=int, default=1)
    parser.add_argument('--fault', choices=('before-dispatch', 'after-intent', 'after-effect', 'after-acknowledgement'))
    args = parser.parse_args()
    try:
        if args.command == '_check':
            result = check_process()
        else:
            require(args.directory is not None, 'An experiment directory is required')
            root = Path(args.directory).absolute()
            if args.command == 'init':
                result = initialize(root, args.correct, args.budget)
            elif args.command == 'observe':
                result = observe(root, args.delivery)
            elif args.command == 'tick':
                result = tick(root, args.fault)
            elif args.command == 'recover':
                result = recover(root)
            elif args.command == '_worker':
                result = fixture_worker(root, args.work_id)
            else:
                result = inspect(root)
        print(encode(result))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(encode({'error': type(exc).__name__, 'message': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
