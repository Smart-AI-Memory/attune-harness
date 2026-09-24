"""Assemble the Codex plugin from the canonical Harness skill, without installing it."""

import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def package(destination: Path) -> Path:
    """Create a new plugin directory; refuse to overwrite an existing destination."""
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / "plugins/attune-harness/.codex-plugin", destination / ".codex-plugin")
    shutil.copytree(ROOT / ".agents/skills/attune-harness", destination / "skills/attune-harness")
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New directory named attune-harness")
    args = parser.parse_args()
    if args.destination.name != "attune-harness":
        parser.error("destination must be named attune-harness")
    print(package(args.destination.expanduser().absolute()))
