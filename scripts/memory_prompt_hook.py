#!/usr/bin/env python3
"""UserPromptSubmit bridge to the installed Harness CLI; no shell interpolation.

Run with the Python interpreter that has Harness installed:
    /path/to/venv/bin/python /path/to/checkout/scripts/memory_prompt_hook.py --config /path/to/memory.json
The host supplies a JSON object on stdin. Only its prompt is used.
"""

import argparse
import json
import subprocess
import sys


INPUT_LIMIT = 65536


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
        if len(raw) > INPUT_LIMIT:
            raise ValueError('Hook input exceeds 65536 bytes')
        payload = json.loads(raw)
        prompt = payload.get('prompt') if isinstance(payload, dict) else None
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 512:
            raise ValueError('Hook prompt must contain 1 to 512 characters')
        result = subprocess.run([sys.executable, '-m', 'attune_harness', 'memory',
                                 '--config', args.config, 'serve', '--for=' + prompt],
                                capture_output=True, timeout=10, check=False)
        if result.returncode == 0 and result.stdout:
            sys.stdout.buffer.write(result.stdout)
        else:
            # A backend error can echo the query. Keep hook diagnostics payload-free.
            sys.stderr.write('[attune-harness memory] prompt hook skipped: no memory served\n')
    except (ValueError, OSError, RecursionError, subprocess.TimeoutExpired) as error:
        # Do not echo payloads or process arguments: they can contain the user's prompt.
        sys.stderr.write(f'[attune-harness memory] prompt hook skipped: {type(error).__name__}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
