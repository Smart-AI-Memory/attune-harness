"""Import the frozen supervisor and v1 interfaces without changing their files."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'experiments/memory_routing'
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location('frozen_memory_campaign', DIRECTORY / 'campaign.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
sys.path.remove(str(DIRECTORY))
