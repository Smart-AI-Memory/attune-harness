"""Installed Harness consumer for the independent arithmetic peer; no model calls."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from attune_harness import Check, Task
from attune_harness.a2a import A2AExchange, LocalPeer, inspect_exchange
from attune_harness.adapters import Attempt, JsonParticipant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--card-digest', required=True)
    parser.add_argument('--peer-name', default='independent-arithmetic-peer')
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--control', choices=('none', 'refresh', 'cancel', 'cancel-refresh'), default='none')
    args = parser.parse_args()
    task = Task('sum', 'Compute 2 + 2', ('Return the sum as a decimal integer',))
    attempt = Attempt(task, 'fixture-attempt', 'requirements-v1', 'independent-peer', 'worker', 'a2a-1.0-local')
    peer = LocalPeer(args.endpoint, args.card_digest, args.peer_name)
    exchange = A2AExchange(attempt, peer, args.run_dir, max_polls=0 if 'cancel' in args.control else 4)
    initial = JsonParticipant(attempt, exchange).execute(
        lambda task, output: Check(output.text == str(2 + 2), 'Independent arithmetic check: 2 + 2 = 4'))
    controls = []
    for operation in args.control.split('-') if args.control != 'none' else []:
        try:
            result = getattr(exchange, operation)()
            controls.append({'operation': operation, 'status': result['status']})
        except Exception as exc:
            controls.append({'operation': operation, 'error': f'{type(exc).__name__}: {exc}'})
    print(json.dumps({'initial_receipt': asdict(initial), 'controls': controls,
                      'exchange': inspect_exchange(args.run_dir), 'provider_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
