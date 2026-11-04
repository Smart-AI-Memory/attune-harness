"""Supervised native protected-store operation; never log its input or result."""
import json
from pathlib import Path
import sys
import types


def main():
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144: raise ValueError('input limit')
        value = json.loads(raw)
        package = types.ModuleType('attune_harness')
        package.__path__ = [str(Path(__file__).resolve().parent)]
        sys.modules['attune_harness'] = package
        from attune_harness.plan_keychain import _NativeKeychain
        backend = _NativeKeychain()
        operation = value['operation']
        if operation == 'probe':
            result = backend.probe()
        elif operation == 'get':
            result = backend.get(value['profile_id'])
        elif operation == 'put':
            backend.put(value['profile_id'], value['record']); result = None
        else:
            raise ValueError('unknown operation')
        output = json.dumps(result, allow_nan=False).encode()
        if len(output) > 262144: raise ValueError('output limit')
        sys.stdout.buffer.write(output)
        return 0
    except Exception:
        sys.stderr.write('protected_storage_failed')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
