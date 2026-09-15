"""Characterize the example bridge against an installed Attune BasePlugin."""
import argparse
import importlib.util
import json
import tempfile
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from attune_harness.extensions import install, mutate
from attune_harness.features import FeatureUnavailable
import attune_harness

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('harness_evidence_bridge', root / 'examples/extensions/attune_bridge.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='harness-attune-bridge-') as scratch:
    work = Path(scratch)
    source = work / 'project'
    source.mkdir()
    (source / 'reference.md').write_text('Quartz policy reference', encoding='utf-8')
    directory = work / 'state'
    state = install(root / 'examples/extensions/plugin/src/attune_harness_evidence/extension.json', directory)
    state = mutate(directory, state['state_digest'], 'enable')
    binding = {'evidence': {'state_dir': str(directory), 'artifact_digest': state['artifact_digest']}}
    plugin = module.EvidencePlugin(binding, source)
    plugin.initialize()
    plugin.on_activate()
    assert plugin.list_workflows() == []
    result = plugin.search('quartz policy')
    assert result['status'] == 'retrieved' and result['extension']['artifact_digest'] == state['artifact_digest']
    mutate(directory, state['state_digest'], 'disable')
    try:
        plugin.search('quartz policy')
    except FeatureUnavailable:
        blocked = True
    else:
        raise AssertionError('Disabled plugin remained invocable')
    receipt = {'attune_ai': version('attune-ai'), 'attune_rag': version('attune-rag'),
               'harness_module': attune_harness.__file__, 'metadata': asdict(plugin.get_metadata()),
               'real_retrieval': result['status'], 'disabled_blocked': blocked, 'provider_calls': 0,
               'host_autodiscovery_qualified': False, 'host_mcp_registration_qualified': False,
               'scope': 'Public BasePlugin metadata/initialize/activation plus explicit bridge search; no host startup'}
(args.report or root / 'docs/receipts/extensions-attune-bridge.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('Installed Attune BasePlugin bridge: real retrieval passed; disabled call refused')
