"""Run one authenticated native arithmetic probe and save raw evidence.

This invokes the selected installed CLI using its existing authentication.
Run only with authorization for that provider call. It does not change auth.
"""

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from attune_harness import Check, Task
from attune_harness.adapters import Attempt, JsonParticipant
from attune_harness.native import NativeExchange
from attune_harness.process import invoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['claude', 'codex'], required=True)
    parser.add_argument('--executable')
    parser.add_argument('--model')
    parser.add_argument('--receipt-dir', type=Path, required=True)
    args = parser.parse_args()
    executable = args.executable or args.provider
    with tempfile.TemporaryDirectory(prefix='harness-native-work-') as tmp:
        cwd = Path(tmp)
        version = invoke((executable, '--version'), '', cwd=cwd, timeout=5)
        if version.failure:
            raise SystemExit(f'CLI version probe failed: {version.failure}: {version.stderr}')
        attempt = Attempt(Task('native-arithmetic', 'Compute 2 + 2', ('Return exactly 4 as text',)),
                          str(uuid4()), 'arithmetic-v1', args.provider, 'worker', 'native-v1')
        exchange = NativeExchange(args.provider, cwd=cwd, executable=executable,
                                  model=args.model, timeout=60)
        result = JsonParticipant(attempt, exchange).execute(
            lambda task, output: Check(output.text == '4', 'Exact arithmetic comparison'))
        record = dict(result=asdict(result), cli_version=asdict(version),
                      requested_model=args.model,
                      identity=asdict(exchange.identity) if exchange.identity else None,
                      process=asdict(exchange.last_process) if exchange.last_process else None)
        args.receipt_dir.mkdir(parents=True, exist_ok=True)
        path = args.receipt_dir / f'{args.provider}-{attempt.attempt_id}.json'
        path.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
        print(f'{result.receipt.status.value}: {path}')
        return 0 if result.receipt.status == 'verified' else 1


if __name__ == '__main__':
    raise SystemExit(main())
