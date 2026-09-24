#!/usr/bin/env python3
"""Print, write or check the command line's surface, the compatibility list's machine twin.

    python scripts/compatibility_surface.py                     # the surface as JSON
    python scripts/compatibility_surface.py --write PATH        # rewrite the committed fixture
    python scripts/compatibility_surface.py --check PATH        # exit 1 if the fixture differs
    python scripts/compatibility_surface.py --rows              # the verb table's Markdown rows

Run from a checkout; it reads the parsers of the package under ``src/``.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attune_harness.cli_surface import rows, surface  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", type=Path)
    mode.add_argument("--check", type=Path)
    mode.add_argument("--rows", action="store_true")
    args = parser.parse_args()
    value = surface()
    text = json.dumps(value, indent=1, sort_keys=True) + "\n"
    if args.write:
        args.write.write_text(text, encoding="utf-8")
        print(f"wrote {args.write}")
    elif args.check:
        if json.loads(args.check.read_text(encoding="utf-8")) != value:
            print(f"the surface differs from {args.check}; rewrite it with --write if the change is deliberate")
            return 1
        print(f"the surface matches {args.check}")
    elif args.rows:
        print("\n".join(rows(value)))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
