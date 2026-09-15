"""Installed-wheel A2A checks with an independent stdlib HTTP peer process."""
import argparse
import json
import select
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(python):
    cases = []
    matrix = [
        ('none', 'none', False, 'verified', 'completed'),
        ('wrong_answer', 'none', False, 'rejected', 'completed'),
        ('disconnect_send', 'refresh', False, 'failed', 'unresolved'),
        ('disconnect_get_once', 'refresh', False, 'failed', 'completed'),
        ('none', 'cancel', True, 'failed', 'cancelled'),
        ('disconnect_cancel', 'cancel-refresh', True, 'failed', 'cancelled'),
        ('cancel_race', 'cancel', True, 'failed', 'completed'),
        ('denied', 'none', False, 'failed', 'unresolved'),
        ('wrong_digest', 'none', False, 'failed', 'unresolved'),
        ('url_artifact', 'none', False, 'failed', 'unresolved'),
    ]
    with tempfile.TemporaryDirectory(prefix='harness-a2a-installed-') as directory:
        work = Path(directory)
        subprocess.run([str(python), '-I', '-c',
            'import importlib.util; assert all(importlib.util.find_spec(n) is None for n in ["attune", "anthropic", "openai", "mcp", "attune_forms", "attune_rag", "attune_verify"])'],
            cwd=work, check=True)
        for index, (fault, control, hold, expected_initial, expected_state) in enumerate(matrix):
            log = work / f'peer-{index}.json'
            with tempfile.TemporaryFile(mode='w+') as stderr:
                process = subprocess.Popen([sys.executable, '-I', str(ROOT / 'examples/a2a/peer.py'),
                    '--log', str(log), '--fault', fault, *(['--hold'] if hold else [])],
                    stdout=subprocess.PIPE, stderr=stderr, text=True, cwd=work)
                try:
                    assert select.select([process.stdout], [], [], 5)[0], 'Peer startup timed out'
                    line = process.stdout.readline()
                    if not line:
                        stderr.seek(0)
                        raise AssertionError(stderr.read())
                    ready = json.loads(line)
                    run = subprocess.run([str(python), '-I', str(ROOT / 'examples/a2a/client.py'),
                        '--endpoint', ready['endpoint'], '--card-digest', ready['card_digest'],
                        '--run-dir', str(work / f'run-{index}'), '--control', control],
                        cwd=work, capture_output=True, text=True, timeout=15)
                    assert run.returncode == 0, (run.stdout, run.stderr)
                    result = json.loads(run.stdout)
                    assert result['initial_receipt']['receipt']['status'] == expected_initial, result
                    assert result['exchange']['status'] == expected_state, result
                    peer_log = json.loads(log.read_text(encoding='utf-8'))
                    created = sum('created_task' in event for event in peer_log['events'])
                    assert created == (0 if fault == 'denied' else 1)
                    if expected_state == 'completed':
                        assert json.loads(result['exchange']['response'])['text'] == ('5' if fault == 'wrong_answer' else '4')
                    cases.append({'fault': fault, 'control': control, 'result': result, 'peer': peer_log, 'card': ready['card']})
                finally:
                    process.terminate()
                    process.wait(timeout=5)
                    process.stdout.close()
    return {'schema_version': 1, 'protocol': '1.0', 'binding': 'JSONRPC', 'transport': '127.0.0.1 HTTP',
            'cases': cases, 'provider_calls': 0, 'core_only_install': True,
            'remote_authentication_qualified': False, 'peer': 'Separate stdlib process, no Harness imports'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.python.absolute())
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"{len(result['cases'])} installed A2A cases passed; zero provider calls")
