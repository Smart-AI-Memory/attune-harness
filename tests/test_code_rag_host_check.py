"""Host qualification rejects bad boundary evidence even under Python optimization."""

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('optimization', [0, 1])
@pytest.mark.parametrize('bad', ['index', 'tool', 'status', 'sources', 'support', 'usage', 'session', 'event', None])
def test_host_qualification_runtime_checks(tmp_path, monkeypatch, optimization, bad):
    mcp = pytest.importorskip('mcp')
    from mcp.client import stdio
    path = Path(__file__).resolve().parents[1] / 'scripts/check_code_rag_host.py'
    namespace = {'__name__': 'host_qualification_probe', '__file__': str(path)}
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec', optimize=optimization), namespace)
    result = {'status': 'no_results', 'sources': [],
              'evidence_basis': {'answer_support': 'insufficient_evidence'},
              'usage': {'new_provider_calls': 0}}
    if bad == 'status':
        result['status'] = 'failed'
    if bad == 'sources':
        result['sources'] = ['unexpected source']
    if bad == 'support':
        result['evidence_basis']['answer_support'] = 'wrong'
    if bad == 'usage':
        result['usage']['new_provider_calls'] = 1

    class Client:
        def __init__(self, *args): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def initialize(self):
            return SimpleNamespace(serverInfo=SimpleNamespace(name='controlled-host-fixture'))
        async def list_tools(self):
            return SimpleNamespace(tools=[] if bad == 'tool' else [SimpleNamespace(name='code_evidence_query')])
        async def call_tool(self, *args):
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(result))])

    @asynccontextmanager
    async def transport(*args, **kwargs):
        yield None, None

    monkeypatch.setattr(mcp, 'ClientSession', Client)
    monkeypatch.setattr(stdio, 'stdio_client', transport)
    namespace.update(
        subprocess=SimpleNamespace(run=lambda *args, **kwargs: None),
        code_config=lambda *args: {},
        build_index=lambda cfg: {'generation': 'fixture', 'provider_calls': 1 if bad == 'index' else 0},
        task_template=lambda *args, **kwargs: {'accepted': False},
        read_record=lambda path: {'status': 'unresolved' if bad == 'session' else 'completed',
                                  'events': [{'state': 'failed' if bad == 'event' else 'completed'}]},
        version=lambda package: 'fixture',
    )
    if bad is None:
        receipt = asyncio.run(namespace['check'](tmp_path))
        assert receipt['status'] == 'passed' and receipt['provider_calls'] == 0
        assert receipt['result'] == result
    else:
        with pytest.raises((AssertionError, RuntimeError)):
            asyncio.run(namespace['check'](tmp_path))
