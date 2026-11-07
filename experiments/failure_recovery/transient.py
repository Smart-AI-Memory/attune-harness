"""Owned local tamper control; the experiment's observer does not gate Harness."""

import json
import os
from pathlib import Path
import sys
import time

CHANGED = b'def test_weakened():\n    assert True\n'


def replace(path, data):
    staged = path.with_name(path.name + ".offline-staged")
    with staged.open("xb") as stream:
        stream.write(data)
    deadline = time.monotonic() + 2
    while True:
        try:
            os.replace(staged, path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.005)


def main():
    target, acknowledge = Path(sys.argv[1]), Path(sys.argv[2])
    if (not target.is_absolute() or target != target.resolve() or not acknowledge.is_absolute()
            or acknowledge != acknowledge.resolve() or target.is_symlink() or target.stat().st_nlink != 1
            or acknowledge.is_relative_to(target.parent.parent)):
        raise ValueError("Transient control paths must be regular and externally acknowledged")
    original = target.read_bytes()
    if len(original) > 32768:
        raise ValueError("Transient control target exceeds bound")
    try:
        replace(target, CHANGED)
        if sys.argv[3] == "acknowledged":
            deadline = time.monotonic() + 5
            while not acknowledge.exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Observer did not acknowledge retained changed bytes")
                time.sleep(0.005)
    finally:
        replace(target, original)
    print(json.dumps({"restored": True, "control": sys.argv[3]}))


if __name__ == "__main__":
    main()
