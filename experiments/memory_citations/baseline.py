"""Import preserved prototype/transport without editing or patching their state."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/memory_sorter'))
import sorter as old
from transport import Transport, write

