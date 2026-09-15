"""A separate, read-only CLI client for the disposable Guardian fixture."""
import json
from pathlib import Path
import subprocess
import sys

guardian = Path(__file__).with_name('guardian.py')
result = subprocess.run([sys.executable, '-I', str(guardian), 'inspect', sys.argv[1]],
                        capture_output=True, text=True, timeout=20)
if result.returncode:
    sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)
view = json.loads(result.stdout)
if view.get('schema') != 'guardian-client/1':
    raise SystemExit('Unsupported Guardian client schema')
print(json.dumps({'client': 'separate-cli-fixture', 'scope': view['scope'],
                  'work': [{'id': row['id'], 'state': row['state'], 'acceptance': row['acceptance'],
                            'verification': row['verification'], 'diagnostic': row['diagnostic']}
                           for row in view['work']], 'budget': view['budget']}, indent=2))
