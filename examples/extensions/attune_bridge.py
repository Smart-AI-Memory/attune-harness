"""Explicit Attune BasePlugin bridge; never auto-registers with the host.

Run this only in an environment with attune-ai 16.4.0 and Harness installed.
The owning host must supply the accepted extension binding and corpus scope.
No private Attune MCP handler tables or copied retrieval implementation.
"""
from pathlib import Path

from attune.plugins.base import BasePlugin, PluginMetadata
from attune_harness.extensions import catalog, invoke_tool
from attune_harness.retrieval import retrieve_sources


class EvidencePlugin(BasePlugin):
    def __init__(self, bindings: dict, corpus: Path):
        self.bindings = bindings
        self.corpus = corpus.resolve()
        self.contribution = catalog(bindings)['evidence.search']
        super().__init__()

    def get_metadata(self):
        return PluginMetadata(name='harness-evidence', version=self.contribution['version'],
                              domain='harness_evidence', description='Scoped Harness evidence retrieval',
                              author='Smart AI Memory', license='Unspecified (local example)', requires_core_version='16.4.0')

    def register_workflows(self):
        return {}

    def on_activate(self):
        catalog(self.bindings, enabled=True)

    def search(self, query: str, k: int = 3):
        return invoke_tool(self.bindings, 'evidence.search', {'query': query, 'k': k},
                           lambda query, k: retrieve_sources(query, self.corpus, k=k))
